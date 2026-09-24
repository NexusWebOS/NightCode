"""Drive / volume detection for DataReach.

Detects storage devices on the local machine in a cross-platform way with a
heavy focus on Windows, where a power user may have 50+ USB drives mounted at
once.  Uses ``psutil`` when it is available for rich metadata, and falls back
to platform primitives (Windows drive-letter scan / ``os.statvfs``) so the app
still works on a stock Python install with no third-party packages.
"""

from __future__ import annotations

import ctypes
import os
import string
import sys
from dataclasses import dataclass, field
from typing import List, Optional

try:  # optional, gives us far better metadata when present
    import psutil  # type: ignore
except Exception:  # pragma: no cover - psutil is optional
    psutil = None  # type: ignore


IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    # Empty card-reader slots and ejected sticks must not pop up
    # "There is no disk in the drive" boxes while we poll every few seconds.
    try:
        _SEM_FAILCRITICALERRORS, _SEM_NOOPENFILEERRORBOX = 0x0001, 0x8000
        ctypes.windll.kernel32.SetErrorMode(  # type: ignore[attr-defined]
            _SEM_FAILCRITICALERRORS | _SEM_NOOPENFILEERRORBOX)
    except Exception:
        pass


# Windows GetDriveType return values.
_WIN_DRIVE_TYPES = {
    0: "unknown",
    1: "no_root",
    2: "removable",
    3: "fixed",
    4: "network",
    5: "cdrom",
    6: "ramdisk",
}


@dataclass
class Drive:
    """A single mounted volume."""

    path: str                       # root path, e.g. "D:\\" or "/media/usb0"
    label: str = ""                 # volume label, best-effort
    fstype: str = ""                # NTFS / exFAT / FAT32 / ext4 ...
    total: int = 0                  # bytes
    used: int = 0                   # bytes
    free: int = 0                   # bytes
    kind: str = "fixed"             # fixed / removable / network / cdrom / ramdisk
    ready: bool = True              # False for e.g. an empty card reader slot

    letter: str = field(default="", init=False)

    def __post_init__(self) -> None:
        if IS_WINDOWS and len(self.path) >= 2 and self.path[1] == ":":
            self.letter = self.path[:2].upper()
        else:
            self.letter = self.path

    @property
    def percent(self) -> float:
        if not self.total:
            return 0.0
        return round(self.used / self.total * 100.0, 1)

    @property
    def is_removable(self) -> bool:
        return self.kind in ("removable", "cdrom")

    @property
    def display_name(self) -> str:
        label = self.label or ("Removable" if self.is_removable else "Local Disk")
        return f"{self.letter}  {label}" if IS_WINDOWS else f"{label} ({self.path})"


def _win_volume_label_and_fs(root: str) -> tuple[str, str]:
    """Return (label, fstype) for a Windows volume root such as 'D:\\'."""
    if not IS_WINDOWS:
        return "", ""
    vol_buf = ctypes.create_unicode_buffer(261)
    fs_buf = ctypes.create_unicode_buffer(261)
    serial = ctypes.c_uint()
    max_len = ctypes.c_uint()
    flags = ctypes.c_uint()
    try:
        ok = ctypes.windll.kernel32.GetVolumeInformationW(  # type: ignore[attr-defined]
            ctypes.c_wchar_p(root),
            vol_buf,
            ctypes.sizeof(vol_buf),
            ctypes.byref(serial),
            ctypes.byref(max_len),
            ctypes.byref(flags),
            fs_buf,
            ctypes.sizeof(fs_buf),
        )
    except Exception:
        return "", ""
    if not ok:
        return "", ""
    return vol_buf.value, fs_buf.value


def _win_drive_type(root: str) -> str:
    try:
        t = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root))  # type: ignore[attr-defined]
    except Exception:
        return "unknown"
    return _WIN_DRIVE_TYPES.get(int(t), "unknown")


def _scan_windows() -> List[Drive]:
    drives: List[Drive] = []
    try:
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()  # type: ignore[attr-defined]
    except Exception:
        bitmask = 0
    for i, letter in enumerate(string.ascii_uppercase):
        if not (bitmask >> i) & 1:
            continue
        root = f"{letter}:\\"
        kind = _win_drive_type(root)
        label, fstype = _win_volume_label_and_fs(root)
        total = used = free = 0
        ready = True
        try:
            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            total_free = ctypes.c_ulonglong(0)
            ok = ctypes.windll.kernel32.GetDiskFreeSpaceExW(  # type: ignore[attr-defined]
                ctypes.c_wchar_p(root),
                ctypes.byref(free_bytes),
                ctypes.byref(total_bytes),
                ctypes.byref(total_free),
            )
            if ok:
                total = int(total_bytes.value)
                free = int(total_free.value)
                used = max(total - free, 0)
            else:
                ready = False
        except Exception:
            ready = False
        drives.append(
            Drive(
                path=root,
                label=label,
                fstype=fstype,
                total=total,
                used=used,
                free=free,
                kind=kind,
                ready=ready,
            )
        )
    return drives


def _scan_psutil() -> List[Drive]:
    drives: List[Drive] = []
    for part in psutil.disk_partitions(all=False):  # type: ignore[union-attr]
        opts = (part.opts or "").lower()
        kind = "removable" if "removable" in opts else "fixed"
        if "cdrom" in (part.fstype or "").lower() or part.device.startswith("/dev/sr"):
            kind = "cdrom"
        total = used = free = 0
        ready = True
        try:
            usage = psutil.disk_usage(part.mountpoint)  # type: ignore[union-attr]
            total, used, free = usage.total, usage.used, usage.free
        except Exception:
            ready = False
        drives.append(
            Drive(
                path=part.mountpoint,
                label=os.path.basename(part.mountpoint.rstrip("/\\")) or part.device,
                fstype=part.fstype,
                total=total,
                used=used,
                free=free,
                kind=kind,
                ready=ready,
            )
        )
    return drives


_PSEUDO_FS = {"proc", "sysfs", "devtmpfs", "devpts", "tmpfs", "cgroup", "cgroup2",
              "securityfs", "pstore", "debugfs", "tracefs", "configfs", "fusectl",
              "mqueue", "hugetlbfs", "binfmt_misc", "autofs", "bpf", "overlay",
              "squashfs", "nsfs", "ramfs", "efivarfs", "rpc_pipefs", "fuse.portal"}
_MEDIA_BASES = ("/media/", "/run/media/", "/mnt/", "/Volumes/")


def _sys_removable(device: str) -> bool:
    """True when /sys says the block device behind *device* is removable/USB."""
    name = os.path.basename(device)
    base = name.rstrip("0123456789")
    if base.startswith("nvme") or base.startswith("mmcblk"):
        base = name.split("p")[0] if "p" in name[4:] else name
    for cand in (name, base):
        flag = f"/sys/block/{cand}/removable"
        try:
            with open(flag) as f:
                if f.read().strip() == "1":
                    return True
        except OSError:
            pass
        try:
            if "/usb" in os.path.realpath(f"/sys/block/{cand}"):
                return True
        except OSError:
            pass
    return False


def _scan_posix() -> List[Drive]:
    drives: List[Drive] = []
    mounts = []
    try:
        with open("/proc/mounts", encoding="utf-8", errors="replace") as f:
            for line in f:
                bits = line.split()
                if len(bits) >= 3:
                    mounts.append((bits[0], bits[1].replace("\\040", " "), bits[2]))
    except OSError:
        mounts = [("", "/", "")]
        for base in _MEDIA_BASES:
            base = base.rstrip("/")
            if os.path.isdir(base):
                for e in os.listdir(base):
                    p = os.path.join(base, e)
                    if os.path.ismount(p):
                        mounts.append(("", p, ""))
    seen = set()
    for dev, mnt, fstype in mounts:
        if fstype in _PSEUDO_FS and mnt != "/":
            continue
        if mnt != "/" and not mnt.startswith(_MEDIA_BASES):
            continue
        if mnt in seen:
            continue
        seen.add(mnt)
        total = used = free = 0
        ready = True
        try:
            st = os.statvfs(mnt)
            total = st.f_blocks * st.f_frsize
            free = st.f_bavail * st.f_frsize
            used = max((st.f_blocks - st.f_bfree) * st.f_frsize, 0)
        except OSError:
            ready = False
        removable = mnt != "/" and (dev.startswith("/dev/") and _sys_removable(dev)
                                    or mnt.startswith(("/media/", "/run/media/", "/Volumes/")))
        drives.append(Drive(path=mnt,
                            label=os.path.basename(mnt.rstrip("/")) or "root",
                            fstype=fstype, total=total, used=used, free=free,
                            kind="removable" if removable else "fixed", ready=ready))
    return drives


def list_drives() -> List[Drive]:
    """Return all detected drives, sorted with removable media last.

    Ordering keeps the system disk first and groups the many USB sticks so the
    fan-out target list reads naturally top-to-bottom.
    """
    drives: List[Drive]
    if IS_WINDOWS:
        drives = _scan_windows()
    elif psutil is not None:
        drives = _scan_psutil()
    else:
        drives = _scan_posix()

    def sort_key(d: Drive):
        order = {"fixed": 0, "network": 1, "removable": 2, "cdrom": 3, "ramdisk": 4}
        return (order.get(d.kind, 5), d.letter)

    return sorted(drives, key=sort_key)


def volume_root(path: str) -> str:
    """Return the mount point / drive root that contains *path*."""
    path = os.path.abspath(path)
    if IS_WINDOWS:
        buf = ctypes.create_unicode_buffer(1024)
        try:
            if ctypes.windll.kernel32.GetVolumePathNameW(  # type: ignore[attr-defined]
                    ctypes.c_wchar_p(path), buf, 1024):
                return buf.value
        except Exception:
            pass
        drive, _ = os.path.splitdrive(path)
        return (drive + "\\") if drive else path
    p = path
    while not os.path.ismount(p):
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    return p


def fs_type_for(path: str) -> str:
    """Best-effort filesystem name (NTFS, exFAT, FAT32, ext4...) for *path*."""
    root = volume_root(path)
    if IS_WINDOWS:
        return _win_volume_label_and_fs(root)[1]
    if psutil is not None:
        best = ""
        fstype = ""
        for part in psutil.disk_partitions(all=True):  # type: ignore[union-attr]
            if root.startswith(part.mountpoint) and len(part.mountpoint) > len(best):
                best, fstype = part.mountpoint, part.fstype
        if fstype:
            return fstype
    try:
        with open("/proc/mounts", "r", encoding="utf-8", errors="replace") as f:
            best = ""
            fstype = ""
            for line in f:
                bits = line.split()
                if len(bits) >= 3 and root.startswith(bits[1]) and len(bits[1]) > len(best):
                    best, fstype = bits[1], bits[2]
            return fstype
    except OSError:
        return ""


def is_fat32(fstype: str) -> bool:
    return fstype.strip().lower() in ("fat32", "fat", "vfat", "msdos", "fat16")


def free_space_for(path: str) -> Optional[int]:
    """Free bytes on the volume that will hold *path* (walks up to an existing dir)."""
    p = os.path.abspath(path)
    while not os.path.exists(p):
        parent = os.path.dirname(p)
        if parent == p:
            return None
        p = parent
    try:
        import shutil
        return shutil.disk_usage(p).free
    except OSError:
        return None


def human_bytes(n: Optional[float]) -> str:
    """Format a byte count like '931.5 GB'."""
    if n is None:
        return "-"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(n) < 1024.0 or unit == "PB":
            if unit == "B":
                return f"{int(n)} {unit}"
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


if __name__ == "__main__":  # quick manual check
    for d in list_drives():
        print(
            f"{d.display_name:<28} {d.fstype:<6} "
            f"{human_bytes(d.total):>9} total  {human_bytes(d.free):>9} free  "
            f"{d.percent:>5}%  [{d.kind}]"
        )
    sys.exit(0)
