"""Retro USB builder: puts DOSBox, free DOS classics, your own DOS games and
strategy guides on a USB stick, ready to play on any Windows PC (and Linux,
with DOSBox installed there).

Layout written to the stick:

    START-HERE.bat / start-here.sh   game picker
    README.TXT
    DOSBOX/WIN/...                    DOSBox Staging (portable)
    DOSBOX/RETRO.CONF                 shared settings
    DOSBOX/CONF/<ID>.CONF             one per game (mounts + start command)
    GAMES/                            mounted as C: for the catalog games
        MENU.BAT, MENU/<ID>.BAT       DOS menu and per-game runners
        <ID>/                         the game
        _SETUP/<ID>/                  original installer files (first-run install)
        MY/<ID>/                      your own games (mounted as C: on their own)
    GUIDES/                           strategy guides (.TXT, mounted as D:) + INDEX.HTM
    RETROUSB.TXT                      what is installed (used when you run the builder again)

Nothing outside those names is touched, and nothing is ever deleted except
this builder's own folders for a game being reinstalled.
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import os
import re
import shutil
import sys
import tarfile
import time
import urllib.request
import zipfile
from typing import Callable, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from coleforge.desktop import archives  # noqa: E402  ZIP + LHA (incl. self-extracting .SHR) reader
from retrousb import catalog  # noqa: E402

GUIDES_SRC = os.path.join(HERE, "guides")
DEFAULT_DOWNLOADS = os.path.join(HERE, "downloads")
DEFAULT_MYGAMES = os.path.join(HERE, "mygames")
UA = "RetroUSB/1.0 (+ColeForge)"
MAX_DOWNLOAD = 2 * 1024 ** 3
CONTAINER_EXT = (".zip", ".shr", ".lzh", ".lha")


def say(*a) -> None:
    print(*a, flush=True)


# ------------------------------------------------------------------ helpers
def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def crlf(text: str) -> bytes:
    return text.replace("\r\n", "\n").replace("\n", "\r\n").encode("ascii", "replace")


class Writer:
    """Writes files onto the stick and reads every one back to check it.

    Cheap USB sticks that lie about their size, or a stick pulled out too
    early, show up here instead of as a game that crashes later.
    """

    def __init__(self, root: str):
        self.root = root
        self.bytes = 0
        self.files = 0

    def path(self, rel: str) -> str:
        return os.path.join(self.root, *rel.replace("\\", "/").split("/"))

    def write(self, rel: str, data: bytes) -> None:
        full = self.path(rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        if len(data) >= 4 * 1024 ** 3:
            raise IOError(f"{rel} is 4 GB or larger and will not fit on a FAT32 stick")
        tmp = full + ".part"
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, full)
        with open(full, "rb") as f:
            if hashlib.sha256(f.read()).digest() != hashlib.sha256(data).digest():
                raise IOError(f"{rel}: what was read back from the stick is not what was written (bad or fake-capacity stick?)")
        self.bytes += len(data)
        self.files += 1

    def text(self, rel: str, text: str) -> None:
        self.write(rel, crlf(text))

    def remove_tree(self, rel: str) -> None:
        full = self.path(rel)
        if os.path.isdir(full):
            shutil.rmtree(full)


# ------------------------------------------------------------------ 8.3 names
_BAD = re.compile(r"[^A-Z0-9_\-!#$%&'(){}@^~]")


def dos_name(name: str, taken: Optional[set] = None) -> str:
    """Upper-case 8.3 name for a file or folder (keeps names that already fit)."""
    up = name.upper()
    base, dot, ext = up.rpartition(".") if "." in up.strip(".") else (up, "", "")
    base = _BAD.sub("", base.replace(" ", "")) or "FILE"
    ext = _BAD.sub("", ext)[:3]
    short = base[:8]
    cand = short + ("." + ext if ext else "")
    if taken is None:
        return cand
    n = 1
    while cand in taken:
        tail = "~%d" % n
        cand = short[:8 - len(tail)] + tail + ("." + ext if ext else "")
        n += 1
    taken.add(cand)
    return cand


def dos_id(title: str, taken: set) -> str:
    base = _BAD.sub("", title.upper().replace(" ", ""))[:8] or "GAME"
    cand, n = base, 1
    while cand in taken:
        tail = str(n)
        cand = base[:8 - len(tail)] + tail
        n += 1
    taken.add(cand)
    return cand


# ------------------------------------------------------------------ download
def fetch(url: str, limit: int = MAX_DOWNLOAD, headers: Optional[dict] = None) -> bytes:
    req = urllib.request.Request(url, headers=dict({"User-Agent": UA}, **(headers or {})))
    with urllib.request.urlopen(req, timeout=60) as r:
        total = int(r.headers.get("Content-Length") or 0)
        buf = bytearray()
        last = 0.0
        while True:
            chunk = r.read(512 * 1024)
            if not chunk:
                break
            buf.extend(chunk)
            if len(buf) > limit:
                raise IOError("file is larger than expected")
            if time.time() - last > 1.0:
                last = time.time()
                pct = f" {len(buf) * 100 // total}%" if total else ""
                sys.stdout.write(f"\r      {len(buf) / 1048576:7.1f} MB{pct}   ")
                sys.stdout.flush()
        if last:
            sys.stdout.write("\r" + " " * 40 + "\r")
        return bytes(buf)


def archive_names(name: str, data: bytes) -> List[str]:
    """Upper-case base names of everything inside (two levels deep)."""
    try:
        return [f["path"].rsplit("/", 1)[-1].upper() for f in archives.expand({name: data}, depth=2)]
    except Exception:
        return []


def check(entry: dict, name: str, data: bytes) -> Tuple[bool, str]:
    """Is this file really the game?  Known size/MD5 first, else its contents."""
    if entry.get("size") and len(data) == entry["size"] and entry.get("md5") == md5(data):
        return True, "MD5 verified"
    if entry.get("md5") and name.lower() == entry["file"].lower():
        return False, f"MD5 {md5(data)} is not the known {entry['md5']}"
    if name.lower().endswith(".iso"):
        return (len(data) > 1024 * 1024, "disc image")
    inside = set(archive_names(name, data))
    want = [c.upper() for c in entry.get("contains", [])]
    if want and any(w in inside for w in want):
        return True, "contents match (" + ", ".join(w for w in want if w in inside) + ")"
    return False, "does not contain " + " / ".join(want)


def find_dropped(entry: dict, downloads: str) -> Optional[str]:
    if not os.path.isdir(downloads):
        return None
    pats = [re.compile(p, re.I) for p in entry.get("match", [])]
    names = sorted(os.listdir(downloads))
    for n in names:
        if n.lower() == entry["file"].lower() or any(p.search(n) for p in pats):
            return os.path.join(downloads, n)
    return None


def obtain(entry: dict, downloads: str, offline: bool, fetcher: Callable[[str], bytes] = fetch) -> Tuple[Optional[str], Optional[bytes], str]:
    """Returns (file name, bytes, how) or (None, None, reason)."""
    os.makedirs(downloads, exist_ok=True)
    path = find_dropped(entry, downloads)
    if path:
        name = os.path.basename(path)
        if os.path.getsize(path) >= MAX_DOWNLOAD:
            return None, None, f"{name} is too large"
        with open(path, "rb") as f:
            data = f.read()
        ok, why = check(entry, name, data)
        if ok:
            return name, data, f"{name} from the downloads folder ({why})"
        say(f"    {name} in the downloads folder is not usable: {why}")
    if entry.get("manual") or offline or not entry.get("urls"):
        return None, None, "manual"
    for url in entry["urls"]:
        say(f"    downloading {url}")
        try:
            data = fetcher(url)
        except Exception as e:  # noqa: BLE001 - any network error means "try the next mirror"
            say(f"      failed: {e}")
            continue
        ok, why = check(entry, entry["file"], data)
        if not ok:
            say(f"      rejected: {why}")
            continue
        with open(os.path.join(downloads, entry["file"]), "wb") as f:
            f.write(data)
        return entry["file"], data, f"downloaded ({why})"
    return None, None, "download failed"


# ------------------------------------------------------------------ unpack
def _join_parts(items: List[dict]) -> List[dict]:
    """NAME._1/._2 (ROTT) and NAME.1/.2 (DOOM) split archives -> one item when the joined bytes are an archive."""
    groups: Dict[str, List[Tuple[int, dict]]] = {}
    rest = []
    for it in items:
        m = re.match(r"^(.*)\.(_?)(\d)$", it["path"])
        if m:
            groups.setdefault(m.group(1) + "|" + m.group(2), []).append((int(m.group(3)), it))
        else:
            rest.append(it)
    for key, parts in groups.items():
        parts.sort(key=lambda p: p[0])
        if len(parts) > 1:
            joined = b"".join(p[1]["bytes"] for p in parts)
            if archives.detect(joined):
                rest.append({"path": key.split("|")[0] + ".ZIP" if key.endswith("|_") else key.split("|")[0] + ".LZH",
                             "bytes": joined, "container": True})
                continue
        rest.extend(p[1] for p in parts)
    return rest


def _is_container(it: dict) -> bool:
    name = it["path"].rsplit("/", 1)[-1].lower()
    if it.get("container"):
        return True
    return (name.endswith(CONTAINER_EXT) or name == "resource.1") and archives.detect(it["bytes"]) is not None


def _open(it: dict) -> Dict[str, bytes]:
    return archives.unzip_bytes(it["bytes"], skip_unsupported=True) if archives.detect(it["bytes"]) == "zip" \
        else archives.unlha_bytes(it["bytes"])


def unpack(name: str, data: bytes, depth: int = 5) -> Tuple[List[dict], List[dict], List[str]]:
    """Returns (leaves, first level, problems).

    Leaves are the files left after opening every archive inside (paths
    relative to the archive they came out of).  "First level" is just the
    outer archive's own contents, used when the game has to be installed by
    its own installer instead.
    """
    problems: List[str] = []
    if archives.detect(data) is None:
        return [{"path": name, "bytes": data}], [{"path": name, "bytes": data}], problems
    try:
        first = [{"path": archives._norm_path(k) or k, "bytes": v} for k, v in _open({"bytes": data}).items()]
    except archives.ArchiveError as e:
        return [], [], [f"{name}: {e}"]
    leaves: List[dict] = []
    queue = [(it, 0) for it in _join_parts([dict(i) for i in first])]
    while queue:
        it, d = queue.pop(0)
        if d < depth and _is_container(it):
            try:
                inner = _open(it)
            except archives.ArchiveError as e:
                problems.append(f"{it['path']}: {e}")
                leaves.append(it)
                continue
            for u in getattr(inner, "unsupported", []) or []:
                problems.append(f"{it['path']}: {u.get('name')} {u.get('reason')}")
            base = it["path"].rsplit("/", 1)[0] + "/" if "/" in it["path"] else ""
            kids = [{"path": base + (archives._norm_path(k) or k), "bytes": v} for k, v in inner.items()]
            queue.extend((k, d + 1) for k in _join_parts(kids))
        else:
            leaves.append(it)
    return leaves, first, problems


def _strip_common_folder(items: List[dict]) -> List[dict]:
    while items and all("/" in i["path"] for i in items):
        top = {i["path"].split("/", 1)[0] for i in items}
        if len(top) != 1:
            break
        items = [dict(i, path=i["path"].split("/", 1)[1]) for i in items]
    return items


def exe_list(entry: dict) -> List[str]:
    e = entry.get("exe") or []
    return [e] if isinstance(e, str) else list(e)


def locate(entry: dict, paths: List[str]) -> Optional[Tuple[str, str]]:
    """(folder inside the game dir, command) for the first start command whose program exists."""
    by_name: Dict[str, List[str]] = {}
    for p in paths:
        by_name.setdefault(p.rsplit("/", 1)[-1].upper(), []).append(p)
    for cmd in exe_list(entry):
        prog = cmd.split()[0].upper()
        if prog in by_name:
            p = sorted(by_name[prog], key=lambda s: s.count("/"))[0]
            return (p.rsplit("/", 1)[0] if "/" in p else ""), cmd
    return None


def dos_paths(items: List[dict]) -> List[dict]:
    """Give every path an 8.3 spelling (DOS can't see long names on a FAT stick)."""
    seen: Dict[str, set] = {}
    mapping: Dict[str, str] = {}
    out = []
    for it in items:
        parts = it["path"].split("/")
        cur = ""
        for i, part in enumerate(parts):
            key = cur + "/" + part.upper()
            if key not in mapping:
                mapping[key] = dos_name(part, seen.setdefault(cur, set()))
            cur = cur + "/" + mapping[key]
        out.append(dict(it, path=cur.lstrip("/")))
    return out


def install_game(entry: dict, name: str, data: bytes, w: Writer) -> dict:
    gid = entry["id"]
    w.remove_tree(f"GAMES/{gid}")
    w.remove_tree(f"GAMES/_SETUP/{gid}")
    if name.lower().endswith(".iso"):
        w.write(f"GAMES/_SETUP/{gid}/DISC.ISO", data)
        return {"mode": "installer", "cd": "DISC.ISO"}
    leaves, first, problems = unpack(name, data)
    for p in problems[:5]:
        say(f"      note: {p}")
    leaves = dos_paths(_strip_common_folder(leaves))
    iso = [i for i in leaves if i["path"].upper().endswith(".ISO")]
    if iso:
        w.write(f"GAMES/_SETUP/{gid}/DISC.ISO", iso[0]["bytes"])
        return {"mode": "installer", "cd": "DISC.ISO"}
    found = locate(entry, [i["path"] for i in leaves])
    if found:
        folder, cmd = found
        for it in leaves:
            w.write(f"GAMES/{gid}/{it['path']}", it["bytes"])
        return {"mode": "ready", "folder": folder.replace("/", "\\"), "cmd": cmd}
    # could not unpack it fully here: keep the original files, the game's own installer runs on first start
    first = dos_paths(_strip_common_folder(first))
    for it in first:
        w.write(f"GAMES/_SETUP/{gid}/{it['path']}", it["bytes"])
    inst = locate({"exe": [entry.get("installer") or "INSTALL.EXE", "INSTALL.BAT", "INSTALL.EXE", "SETUP.EXE"]},
                  [i["path"] for i in first])
    return {"mode": "installer", "installer": (inst[1] if inst else None),
            "installer_folder": (inst[0].replace("/", "\\") if inst else "")}


# ------------------------------------------------------------------ your own games
SKIP_MY = {"DOSBOX", "__SUPPORT", "__REDIST", "COMMONAPPDATA"}


def _gog_autoexec(folder: str) -> Optional[List[str]]:
    """The [autoexec] lines of a GOG game's own dosbox*.conf (the *_single one if there is one)."""
    confs = [n for n in os.listdir(folder) if n.lower().startswith("dosbox") and n.lower().endswith(".conf")]
    confs.sort(key=lambda n: (not n.lower().endswith("_single.conf"), n.lower() == "dosbox.conf", n))
    for n in confs:
        with open(os.path.join(folder, n), "r", encoding="latin-1") as f:
            text = f.read()
        m = re.search(r"^\[autoexec\]\s*$(.*?)(?=^\[|\Z)", text, re.M | re.S | re.I)
        if m:
            lines = [l.strip() for l in m.group(1).splitlines() if l.strip() and not l.strip().startswith("#")]
            if any(not re.match(r"(?i)^(@?echo|cls|exit|mount|imgmount)\b", l) for l in lines):
                return lines
    return None


def _translate_gog(lines: List[str], gid: str) -> List[str]:
    """GOG's confs run with the game's DOSBOX folder as the working directory: '..' is the game folder."""
    out = []
    for l in lines:
        m = re.match(r'(?i)^(mount|imgmount)\s+([a-z]):?\s+"([^"]*)"(.*)$', l) or \
            re.match(r"(?i)^(mount|imgmount)\s+([a-z]):?\s+(\S+)(.*)$", l)
        if m:
            cmd, drive, host, rest = m.groups()
            host = host.replace("\\", "/")
            rel = os.path.normpath(os.path.join("DOSBOX", host)).replace("\\", "/")
            if rel == ".":
                rel = ""
            if rel.startswith(".."):
                continue  # points outside the game folder (e.g. GOG cloud saves)
            parts = [dos_name(p) for p in rel.split("/") if p]
            target = "/".join(["GAMES/MY", gid] + parts)
            out.append(f'{cmd.lower()} {drive.upper()} "{target}"{rest}')
        elif re.match(r"(?i)^exit\b", l):
            continue
        else:
            out.append(l)
    return out


def _guess_start(paths: List[str]) -> Optional[str]:
    progs = [p for p in paths if "/" not in p and re.search(r"\.(exe|com|bat)$", p, re.I)
             and not re.match(r"(?i)^(setup|install|uninst|unins|config|readme|dos4gw|cwsdpmi|sound|goggame)", p)]
    progs.sort(key=lambda p: (not p.upper().endswith(".BAT"), len(p)))
    return progs[0] if progs else None


def import_mygames(src: str, w: Writer, taken: set) -> List[dict]:
    """Copy each folder in ``mygames`` onto the stick with a launcher.

    How it starts, in order: a PLAY.TXT you write (DOS commands, the game
    folder is C:), the game's own GOG dosbox conf, or the one obvious
    .BAT/.EXE in the folder.
    """
    out = []
    if not os.path.isdir(src):
        return out
    for name in sorted(os.listdir(src)):
        folder = os.path.join(src, name)
        if not os.path.isdir(folder):
            continue
        gid = dos_id(name, taken)
        items = []
        for dirpath, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if d.upper() not in SKIP_MY]
            for fn in files:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, folder).replace(os.sep, "/")
                if "/" not in rel and (fn.lower().startswith("dosbox") and fn.lower().endswith(".conf") or fn.upper() == "PLAY.TXT"):
                    continue
                items.append({"path": rel, "src": full})
        mapped = dos_paths([{"path": i["path"], "src": i["src"]} for i in items])
        play_txt = next((os.path.join(folder, n) for n in os.listdir(folder) if n.upper() == "PLAY.TXT"), None)
        if play_txt:
            with open(play_txt, "r", encoding="latin-1") as f:
                lines = [l.strip() for l in f if l.strip()]
            how = "PLAY.TXT"
        else:
            gog = _gog_autoexec(folder)
            if gog:
                lines, how = _translate_gog(gog, gid), "GOG config"
            else:
                start = _guess_start([m["path"] for m in mapped])
                lines, how = ([start] if start else []), "guessed"
        if not lines:
            say(f"  {name}: no way to start it found (add a PLAY.TXT with the DOS command) - skipped")
            continue
        say(f"  {name} -> GAMES\\MY\\{gid} ({len(mapped)} files, start: {how})")
        w.remove_tree(f"GAMES/MY/{gid}")
        for m in mapped:
            with open(m["src"], "rb") as f:
                w.write(f"GAMES/MY/{gid}/{m['path']}", f.read())
        if not any(re.match(r"(?i)^mount\s+c\b", l) for l in lines):
            lines = [f'mount C "GAMES/MY/{gid}"', "C:"] + lines
        out.append({"id": gid, "title": name, "lines": lines, "mode": "mine"})
    return out


# ------------------------------------------------------------------ DOSBox
def _pick_asset(assets: List[dict], platform: str) -> Optional[dict]:
    if platform == "windows":
        cands = [a for a in assets if re.search(r"(?i)windows", a["name"]) and a["name"].lower().endswith(".zip")
                 and not re.search(r"(?i)debug|symbols|pdb|arm", a["name"])]
        cands.sort(key=lambda a: (not re.search(r"(?i)x64|x86_64|amd64", a["name"]), a["name"]))
    else:
        cands = [a for a in assets if re.search(r"(?i)linux", a["name"]) and re.search(r"\.tar\.(xz|gz)$", a["name"])
                 and not re.search(r"(?i)arm|aarch64", a["name"])]
    return cands[0] if cands else None


def _local_dosbox() -> Optional[str]:
    if os.name != "nt":
        return None
    for base in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", ""), os.environ.get("LocalAppData", "")):
        if not base:
            continue
        for sub in ("DOSBox Staging", "DOSBox-Staging", os.path.join("Programs", "DOSBox Staging"), "DOSBox-0.74-3", "DOSBox-0.74"):
            d = os.path.join(base, sub)
            for exe in ("dosbox.exe", "DOSBox.exe"):
                if os.path.isfile(os.path.join(d, exe)):
                    return d
    return None


def get_dosbox(downloads: str, offline: bool, platforms: List[str], w: Writer, fetcher=fetch) -> Dict[str, str]:
    """Puts DOSBox on the stick; returns {platform: path of the program relative to the stick}."""
    ddir = os.path.join(downloads, "dosbox")
    os.makedirs(ddir, exist_ok=True)
    result: Dict[str, str] = {}
    release = None
    for plat in platforms:
        pat = r"(?i)windows.*\.zip$" if plat == "windows" else r"(?i)linux.*\.tar\.(xz|gz)$"
        cached = [n for n in sorted(os.listdir(ddir)) if re.search(pat, n)]
        name = data = None
        if cached:
            name = cached[-1]
            with open(os.path.join(ddir, name), "rb") as f:
                data = f.read()
            say(f"  DOSBox ({plat}): {name} from the downloads folder")
        elif not offline:
            try:
                if release is None:
                    release = json.loads(fetcher(f"https://api.github.com/repos/{catalog.DOSBOX_REPO}/releases/latest").decode("utf-8"))
                asset = _pick_asset(release.get("assets", []), plat)
                if asset:
                    say(f"  DOSBox ({plat}): downloading {asset['name']} ({release.get('tag_name', '')})")
                    name, data = asset["name"], fetcher(asset["browser_download_url"])
                    with open(os.path.join(ddir, name), "wb") as f:
                        f.write(data)
            except Exception as e:  # noqa: BLE001
                say(f"  DOSBox ({plat}): download failed: {e}")
        target = "DOSBOX/WIN" if plat == "windows" else "DOSBOX/LINUX"
        if data is None and plat == "windows":
            local = _local_dosbox()
            if local:
                say(f"  DOSBox (windows): copying the installed one from {local}")
                w.remove_tree(target)
                for dirpath, _d, files in os.walk(local):
                    for fn in files:
                        full = os.path.join(dirpath, fn)
                        with open(full, "rb") as f:
                            w.write(target + "/" + os.path.relpath(full, local).replace(os.sep, "/"), f.read())
                exe = next((n for n in os.listdir(w.path(target)) if n.lower() == "dosbox.exe"), None)
                if exe:
                    result[plat] = target + "/" + exe
                continue
        if data is None:
            say(f"  DOSBox ({plat}): not available - put the DOSBox Staging {plat} "
                f"{'zip' if plat == 'windows' else 'tar.xz'} from {catalog.DOSBOX_PAGE} into {ddir} and run again")
            continue
        files: Dict[str, bytes] = {}
        modes: Dict[str, int] = {}
        if name.lower().endswith(".zip"):
            files = dict(archives.unzip_bytes(data, skip_unsupported=True))
        else:
            with tarfile.open(fileobj=io.BytesIO(data)) as t:
                for m in t.getmembers():
                    if m.isfile():
                        files[m.name] = t.extractfile(m).read()
                        modes[m.name] = m.mode
        items = _strip_common_folder([{"path": k, "bytes": v, "mode": modes.get(k)} for k, v in files.items()])
        w.remove_tree(target)
        exe = None
        for it in items:
            w.write(f"{target}/{it['path']}", it["bytes"])
            if it.get("mode") and it["mode"] & 0o111:
                os.chmod(w.path(f"{target}/{it['path']}"), 0o755)
            base = it["path"].rsplit("/", 1)[-1]
            if base.lower() in ("dosbox.exe", "dosbox") and (exe is None or it["path"].count("/") < exe.count("/")):
                exe = it["path"]
        if exe:
            result[plat] = f"{target}/{exe}"
        else:
            say(f"  DOSBox ({plat}): {name} has no dosbox program in it")
    return result


# ------------------------------------------------------------------ menus and launchers
RETRO_CONF = """# Retro USB: settings shared by every game.
# Each game adds its own DOSBOX/CONF/<ID>.CONF (drives and start command).
# Paths are relative to the stick, so it works on any drive letter.

[sdl]
fullscreen = false

[dosbox]
memsize = 16
"""


def game_conf(lines: List[str]) -> str:
    return "[autoexec]\n@echo off\n" + "\n".join(lines) + "\nexit\n"


def _call(cmd: str) -> str:
    return ("call " + cmd) if cmd.split()[0].upper().endswith(".BAT") else cmd


def cmd_echo(text: str) -> str:
    """Escape text for a cmd.exe echo."""
    return re.sub(r"([&|<>^()])", r"^\1", text)


def dos_runner(entry: dict, info: dict) -> str:
    gid = entry["id"]
    t = ["@echo off", "cls", f"echo {entry['title']}", "echo."]
    if entry.get("notes"):
        t += [f"echo {entry['notes']}", "echo."]
    cmds = exe_list(entry)
    if info["mode"] == "ready":
        folder = f"\\{gid}" + (f"\\{info['folder']}" if info.get("folder") else "")
        prog = info["cmd"].split()[0]
        t += [f"cd {folder}", f"if not exist {prog} goto missing", f"{_call(info['cmd'])} %1 %2 %3 %4", "cd \\", "goto end"]
    else:
        # first run: the game's own installer; afterwards the installed program
        if info.get("cd"):  # the game reads its disc every time, not only when installing
            t += [f"imgmount e C:\\_SETUP\\{gid}\\{info['cd']} -t iso"]
        t += [f"if exist \\{gid}\\{cmds[0].split()[0]} goto run"]
        if info.get("cd"):
            t += ["e:",
                  "echo First run: the disc is drive E:. Its installer starts now.",
                  f"echo Install the game into C:\\{gid}", "pause",
                  f"if exist {entry.get('installer') or 'INSTALL.EXE'} {_call(entry.get('installer') or 'INSTALL.EXE')}",
                  "c:"]
        elif info.get("installer"):
            t += [f"cd \\_SETUP\\{gid}" + (f"\\{info['installer_folder']}" if info.get("installer_folder") else ""),
                  "echo First run: the game's original installer starts now.",
                  f"echo When it asks where to install, use C:\\{gid}", "pause",
                  _call(info["installer"]), "cd \\"]
        else:
            t += [f"echo The files for {gid} are in C:\\_SETUP\\{gid}. Install the game into C:\\{gid}.", "cd \\_SETUP", "goto end"]
        t += [f"if not exist \\{gid}\\{cmds[0].split()[0]} goto missing", ":run", f"cd \\{gid}", f"{_call(cmds[0])} %1 %2 %3 %4", "cd \\", "goto end"]
    t += [":missing", "echo.", f"echo The game program was not found in C:\\{gid}.",
          f"echo If you installed it somewhere else, start it from there.", "pause", "cd \\", ":end"]
    return "\n".join(t) + "\n"


def dos_setup(entry: dict, info: dict) -> Optional[str]:
    if not entry.get("setup"):
        return None
    folder = f"\\{entry['id']}" + (f"\\{info['folder']}" if info.get("folder") else "")
    return "\n".join(["@echo off", f"cd {folder}", "echo Sound Blaster: port 220, IRQ 7, DMA 1 (DOSBox's defaults).",
                      "echo Music: General MIDI or Sound Blaster/AdLib.", "pause",
                      f"if exist {entry['setup']} {entry['setup']}", "cd \\"]) + "\n"


KEYS = "123456789ABCDEFHIJKLMNOPQRTUVWYZ"  # no G (guides), S (setup) or X (exit)


def dos_menu(games: List[dict]) -> str:
    """C:\\MENU.BAT: the in-DOS game picker (only games on C:)."""
    gs = [g for g in games if g["mode"] != "mine"][:len(KEYS)]
    keys = KEYS[:len(gs)]
    t = ["@echo off", ":top", "cls", "echo  ======================================================",
         "echo   RETRO USB  -  pick a game", "echo  ======================================================", "echo."]
    for k, g in zip(keys, gs):
        t.append(f"echo   {k}  {g['title'][:60]}")
    t += ["echo.", "echo   S  sound/controls setup for a game", "echo   G  strategy guides - they are on drive D:",
          "echo   X  leave the menu (type MENU to come back, EXIT to quit)", "echo."]
    t.append(f"choice /c:{keys}SGX /n Your choice: ")
    labels = [("X", "quit"), ("G", "guides"), ("S", "setup")] + list(reversed([(k, "g" + k) for k in keys]))
    n = len(keys) + 3
    for k, lab in labels:
        t.append(f"if errorlevel {n} goto {lab}")
        n -= 1
    t.append("goto top")
    for k, g in zip(keys, gs):
        t += [f":g{k}", f"call \\MENU\\{g['id']}.BAT", "goto top"]
    setups = [g for g in gs if g.get("has_setup")]
    t += [":setup", "cls", "echo Setup for which game?"]
    skeys = KEYS[:len(setups)]
    for k, g in zip(skeys, setups):
        t.append(f"echo   {k}  {g['title'][:60]}")
    if setups:
        t.append(f"choice /c:{skeys}X /n (X = back) ")
        n = len(setups) + 1
        t.append(f"if errorlevel {n} goto top")
        for k, g in reversed(list(zip(skeys, setups))):
            n -= 1
            t.append(f"if errorlevel {n} goto s{k}")
        for k, g in zip(skeys, setups):
            t += [f":s{k}", f"call \\MENU\\{g['id']}S.BAT", "goto top"]
    t += ["goto top", ":guides", "cls", "dir /w D:\\*.TXT", "echo.", "echo Read one with:  MORE D:\\NAME.TXT",
          "echo or open GUIDES\\INDEX.HTM on the stick in a web browser.", "pause", "goto top", ":quit", "cls",
          "echo Type MENU to come back, EXIT to close DOSBox.", ":end"]
    return "\n".join(t) + "\n"


def win_start(games: List[dict], dosbox: Optional[str]) -> str:
    exe = (dosbox or "DOSBOX/WIN/dosbox.exe").replace("/", "\\")
    t = ["@echo off", "setlocal", "cd /d \"%~dp0\"", "title Retro USB",
         f"if not exist \"{exe}\" (", f"  echo DOSBox is missing from this stick: {exe}",
         "  echo Run the Retro USB builder again, or install DOSBox Staging.", "  pause", "  exit /b 1", ")",
         ":menu", "cls", "echo  ======================================================", "echo    RETRO USB",
         "echo  ======================================================", "echo."]
    for i, g in enumerate(games, 1):
        t.append(f"echo   {i:2d}  {cmd_echo(g['title'][:62])}")
    t += ["echo.", "echo    D  DOS menu - the catalog games inside one DOSBox", "echo    G  strategy guides",
          "echo    Q  quit", "echo.", "set \"pick=\"", "set /p pick=Pick a game: ",
          "if /i \"%pick%\"==\"q\" exit /b 0",
          f"if /i \"%pick%\"==\"d\" start \"\" \"{exe}\" -conf DOSBOX\\RETRO.CONF -conf DOSBOX\\CONF\\MENU.CONF & goto menu",
          "if /i \"%pick%\"==\"g\" start \"\" \"GUIDES\\INDEX.HTM\" & goto menu"]
    for i, g in enumerate(games, 1):
        t.append(f"if \"%pick%\"==\"{i}\" start \"\" \"{exe}\" -conf DOSBOX\\RETRO.CONF -conf DOSBOX\\CONF\\{g['id']}.CONF & goto menu")
    t += ["goto menu"]
    return "\n".join(t) + "\n"


def sh_start(games: List[dict]) -> str:
    t = ["#!/bin/sh", "# Retro USB on Linux: uses DOSBOX/LINUX if it is on the stick, else dosbox-staging / dosbox from your system.",
         "cd \"$(dirname \"$0\")\" || exit 1",
         "DB=$(ls DOSBOX/LINUX/dosbox 2>/dev/null || command -v dosbox-staging || command -v dosbox)",
         "[ -n \"$DB\" ] || { echo 'Install DOSBox Staging (or dosbox) first.'; exit 1; }",
         "while :; do", "  echo; echo '  RETRO USB'; echo"]
    for i, g in enumerate(games, 1):
        t.append(f"  echo '  {i:2d}  {g['title'][:62].replace(chr(39), '')}'")
    t += ["  echo '   D  DOS menu'; echo '   Q  quit'", "  printf 'Pick a game: '; read -r pick || exit 0", "  case \"$pick\" in",
          "    q|Q) exit 0 ;;", "    d|D) \"$DB\" -conf DOSBOX/RETRO.CONF -conf DOSBOX/CONF/MENU.CONF ;;"]
    for i, g in enumerate(games, 1):
        t.append(f"    {i}) \"$DB\" -conf DOSBOX/RETRO.CONF -conf DOSBOX/CONF/{g['id']}.CONF ;;")
    t += ["  esac", "done"]
    return "\n".join(t) + "\n"


def guides_index(guides: List[Tuple[str, str]]) -> str:
    rows = "\n".join(f'<li><a href="{html.escape(f)}">{html.escape(t)}</a></li>' for f, t in guides)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Retro USB guides</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{ background:#0b0b12; color:#d7d7e0; font:16px/1.5 "Consolas","Courier New",monospace; margin:0 auto; max-width:760px; padding:24px 16px; }}
h1 {{ color:#ff8a3d; font-size:22px; }} a {{ color:#7fd1ff; }} li {{ margin:6px 0; }} p {{ color:#9a9ab0; }}
</style></head><body>
<h1>Retro USB strategy guides</h1>
<p>Plain text, so they also open inside DOSBox: TYPE D:\\DOOM.TXT | MORE</p>
<ul>
{rows}
</ul>
</body></html>
"""


README = """RETRO USB
=========

Windows:  double-click START-HERE.bat and pick a game.
Linux:    run ./start-here.sh (uses DOSBox from the stick, or your system's).

In DOSBox
  Alt+Enter      full screen on/off
  Ctrl+F10       let go of the mouse
  EXIT           close DOSBox (or close its window)

Drives inside DOSBox
  C:  the GAMES folder (MY\\... games mount their own folder as C:)
  D:  the GUIDES folder: TYPE D:\\DOOM.TXT | MORE
  E:  a game's CD image, when it has one

Sound: DOSBox emulates a Sound Blaster 16 at port 220, IRQ 7, DMA 1 and
General MIDI. Pick those in a game's SETUP program.

Games marked "first run installs" start the game's own installer the first
time. When it asks for a folder, use the one it shows (C:\\<NAME>).

Saved games stay on the stick, inside each game's folder.

Everything here is free to copy: the id / Apogee / 3D Realms / Raven
shareware episodes, games their publishers released as freeware, DOSBox
Staging (GPL). Your own games in GAMES\\MY are yours: keep this stick to
yourself if it has any.

Installed on this stick:
"""


# ------------------------------------------------------------------ main build
def build(target: str, ids: Optional[List[str]] = None, downloads: str = DEFAULT_DOWNLOADS,
          mygames: str = DEFAULT_MYGAMES, offline: bool = False, dosbox_platforms: Optional[List[str]] = None,
          fetcher=fetch) -> dict:
    w = Writer(target)
    os.makedirs(target, exist_ok=True)
    say(f"Retro USB -> {target}")
    manifest_path = w.path("RETROUSB.TXT")
    old: Dict[str, dict] = {}
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, "r", encoding="ascii", errors="replace") as f:
                blob = f.read().split("--json--", 1)
            old = {g["id"]: g for g in json.loads(blob[1])["games"]} if len(blob) == 2 else {}
        except (ValueError, KeyError):
            old = {}

    say("\n[1/4] DOSBox")
    dosbox = get_dosbox(downloads, offline, dosbox_platforms or ["windows"], w, fetcher)

    say("\n[2/4] Games")
    wanted = [g for g in catalog.GAMES if not ids or g["id"] in ids]
    games: List[dict] = []
    missing: List[dict] = []
    for entry in wanted:
        say(f"  {entry['title']}")
        name, data, how = obtain(entry, downloads, offline, fetcher)
        if data is None:
            prev = old.get(entry["id"])
            if prev and os.path.isdir(w.path(f"GAMES/{entry['id']}")) or prev and os.path.isdir(w.path(f"GAMES/_SETUP/{entry['id']}")):
                say("    already on the stick - kept")
                games.append(dict(prev, title=entry["title"]))
                continue
            say("    not installed: " + ("save it into " + downloads + " from " + entry.get("page", entry["urls"][0] if entry.get("urls") else "?")
                                        if how == "manual" else how))
            missing.append(entry)
            continue
        say(f"    {how}")
        info = install_game(entry, name, data, w)
        say("    installed" + (" (first run installs it)" if info["mode"] == "installer" else ""))
        games.append(dict(info, id=entry["id"], title=entry["title"], has_setup=bool(entry.get("setup")) and info["mode"] == "ready"))

    say("\n[3/4] Your own games (" + mygames + ")")
    taken = {g["id"] for g in catalog.GAMES} | {"MENU", "MY", "_SETUP"}
    mine = import_mygames(mygames, w, taken)
    if not mine:
        say("  none (put game folders in there, e.g. from GOG)")

    say("\n[4/4] Menus, launchers and guides")
    allg = games + mine
    w.text("DOSBOX/RETRO.CONF", RETRO_CONF)
    base = ['mount C "GAMES"', 'mount D "GUIDES"']
    w.text("DOSBOX/CONF/MENU.CONF", game_conf(base + ["C:", "call MENU.BAT"]).replace("\nexit\n", "\n"))
    for g in games:
        entry = catalog.BY_ID[g["id"]]
        w.text(f"GAMES/MENU/{g['id']}.BAT", dos_runner(entry, g))
        s = dos_setup(entry, g) if g.get("mode") == "ready" else None
        if s:
            w.text(f"GAMES/MENU/{g['id']}S.BAT", s)
        w.text(f"DOSBOX/CONF/{g['id']}.CONF", game_conf(base + ["C:", f"call \\MENU\\{g['id']}.BAT"]))
    for g in mine:
        uses_d = any(re.match(r"(?i)^(img)?mount\s+d\b", l) for l in g["lines"])
        w.text(f"DOSBOX/CONF/{g['id']}.CONF", game_conf(([] if uses_d else ['mount D "GUIDES"']) + g["lines"]))
    w.text("GAMES/MENU.BAT", dos_menu(games))
    w.text("START-HERE.bat", win_start(allg, dosbox.get("windows")))
    w.write("start-here.sh", sh_start(allg).encode("ascii", "replace"))
    try:
        os.chmod(w.path("start-here.sh"), 0o755)
    except OSError:
        pass

    guides: List[Tuple[str, str]] = []
    for fn in sorted(os.listdir(GUIDES_SRC)):
        if not fn.upper().endswith(".TXT"):
            continue
        with open(os.path.join(GUIDES_SRC, fn), "r", encoding="ascii") as f:
            text = f.read()
        w.text(f"GUIDES/{fn.upper()}", text)
        guides.append((fn.upper(), text.splitlines()[0].strip() if text else fn))
    w.text("GUIDES/INDEX.HTM", guides_index(guides))

    lines = [README]
    for g in allg:
        tag = {"ready": "ready", "installer": "first run installs", "mine": "your game"}[g["mode"]]
        lines.append(f"  {g['id']:<9} {g['title']}  [{tag}]")
    if missing:
        lines.append("\nNot on the stick yet (see the builder's messages):")
        lines += [f"  {m['id']:<9} {m['title']}" for m in missing]
    lines.append("\n--json--\n" + json.dumps({"games": [{k: v for k, v in g.items() if k != "lines"} for g in games]}, indent=1))
    w.text("README.TXT", "\n".join(lines[:-1]) + "\n")
    w.text("RETROUSB.TXT", "\n".join(lines) + "\n")

    say(f"\nDone: {len(games)} catalog games, {len(mine)} of yours, {len(guides)} guides, "
        f"{w.files} files / {w.bytes / 1048576:.1f} MB written and read back OK.")
    if not dosbox.get("windows"):
        say("DOSBox for Windows is NOT on the stick yet - see the message in step 1.")
    if missing:
        say("Missing: " + ", ".join(m["id"] for m in missing) + " (download them into " + downloads + " and run again)")
    return {"games": games, "mine": mine, "missing": missing, "dosbox": dosbox, "guides": guides}
