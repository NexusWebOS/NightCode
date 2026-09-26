"""Local, side-effect-free disc inspection and bounded file operations."""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import zipfile

DRIVE_CDROM = 5
MEDIA_SUFFIXES = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.wma', '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.jpg', '.jpeg', '.png'}


def optical_drives() -> list[str]:
    if os.name != 'nt':
        return []
    kernel = ctypes.windll.kernel32
    return [f'{letter}:\\' for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            if kernel.GetDriveTypeW(f'{letter}:\\') == DRIVE_CDROM]


def volume_label(root: Path) -> str:
    if os.name != 'nt':
        return root.name
    if not root.drive or ctypes.windll.kernel32.GetDriveTypeW(root.drive + '\\') != DRIVE_CDROM:
        return root.name or str(root)
    name = ctypes.create_unicode_buffer(261)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(str(root), name, 261, None, None, None, None, 0)
    return name.value if ok else 'DISC'


def visible_files(root: Path, limit: int = 10000) -> list[Path]:
    root = root.resolve()
    result = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not (Path(base) / d).is_symlink()]
        for filename in files:
            path = Path(base) / filename
            if path.is_symlink():
                continue
            result.append(path)
            if len(result) >= limit:
                return result
    return result


def classify(root: Path, files: list[Path]) -> tuple[str, str]:
    rel = {str(p.relative_to(root)).replace('\\', '/').upper() for p in files}
    names = {p.name.upper() for p in files}
    cnf = next((p for p in files if p.name.upper() == 'SYSTEM.CNF'), None)
    if cnf:
        try:
            data = cnf.read_bytes()[:4096].decode('latin-1', 'ignore').upper()
            if 'BOOT2' in data:
                return 'PlayStation 2', 'PS2 boot configuration found'
            if 'BOOT' in data:
                return 'PlayStation 1', 'PS1 boot configuration found'
        except OSError:
            pass
    if 'DEFAULT.XBE' in names:
        return 'Original Xbox', 'Xbox executable found'
    if 'IP.BIN' in names or '1ST_READ.BIN' in names:
        return 'Dreamcast (possible)', 'Dreamcast file marker found; raw session layout not verified'
    if any(s.startswith('VIDEO_TS/') for s in rel):
        return 'DVD Video', 'VIDEO_TS directory found'
    if any(s.startswith('MPEGAV/') for s in rel):
        return 'Video CD', 'MPEGAV directory found'
    if 'SEGASATURN' in names:
        return 'Sega Saturn (possible)', 'Sega Saturn marker found; raw header not verified'
    raw = raw_disc_markers(root)
    if b'SEGA SEGASATURN' in raw:
        return 'Sega Saturn (possible)', 'Sega Saturn signature found near disc start'
    if b'SEGADISCSYSTEM' in raw:
        return 'Sega CD (possible)', 'Sega CD signature found near disc start'
    if any(p.suffix.lower() in {'.mp3', '.wav', '.flac', '.ogg', '.m4a'} for p in files):
        return 'Music data disc', 'Audio files found'
    if any(p.suffix.lower() in {'.mp4', '.mkv', '.avi', '.mov'} for p in files):
        return 'Video data disc', 'Video files found'
    return 'Data disc', 'Readable files found' if files else 'No readable filesystem files'


def raw_disc_markers(root: Path) -> bytes:
    """Best-effort raw header sniff. Some Windows drives deny this access."""
    if os.name != 'nt' or not root.drive or ctypes.windll.kernel32.GetDriveTypeW(root.drive + '\\') != DRIVE_CDROM:
        return b''
    try:
        with open('\\\\.\\' + root.drive, 'rb', buffering=0) as device:
            return device.read(65536).upper()
    except OSError:
        return b''


def scan(root: Path) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError('No readable disc or folder at this location.')
    files = visible_files(root)
    kind, reason = classify(root, files)
    total = sum(p.stat().st_size for p in files)
    return {'root': str(root), 'label': volume_label(root), 'kind': kind,
            'reason': reason, 'count': len(files), 'bytes': total,
            'files': [str(p.relative_to(root)).replace('\\', '/') for p in files]}


def safe_source(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file() or path.is_symlink():
        raise ValueError(f'Unsafe or missing file: {relative}')
    return path


def copy_disc(root: Path, target: Path, progress=None) -> Path:
    root, target = root.resolve(), target.resolve()
    if target == root or target.is_relative_to(root):
        raise ValueError('Destination must be outside the source.')
    if target.exists() and any(target.iterdir()):
        raise ValueError('Choose an empty destination folder to avoid overwriting files.')
    target.mkdir(parents=True, exist_ok=True)
    files = visible_files(root)
    manifest = {'source': str(root), 'created': time.strftime('%Y-%m-%dT%H:%M:%S'), 'files': []}
    for i, source in enumerate(files, 1):
        rel = source.relative_to(root)
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        with source.open('rb') as inp, dest.open('wb') as out:
            for chunk in iter(lambda: inp.read(1024 * 1024), b''):
                out.write(chunk)
                digest.update(chunk)
        manifest['files'].append({'path': rel.as_posix(), 'bytes': dest.stat().st_size, 'sha256': digest.hexdigest()})
        if progress:
            progress(i, len(files), rel.as_posix())
    manifest_path = target / 'disk-dude-manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest_path


def zip_folder(folder: Path, destination: Path) -> None:
    folder, destination = folder.resolve(), destination.resolve()
    if destination.is_relative_to(folder):
        raise ValueError('ZIP destination must be outside the source folder.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        for path in visible_files(folder):
            archive.write(path, path.relative_to(folder).as_posix())


def run_gh_upload(repo: str, source: Path, release_tag: str) -> str:
    if not shutil.which('gh'):
        raise RuntimeError('GitHub CLI (gh) is not installed.')
    if not source.is_file():
        raise ValueError('Choose an existing archive first.')
    check = subprocess.run(['gh', 'auth', 'status'], capture_output=True, text=True)
    if check.returncode:
        raise RuntimeError('Sign in with gh auth login first.')
    cmd = ['gh', 'release', 'upload', release_tag, str(source), '--repo', repo, '--clobber']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip())
    return f'Uploaded {source.name} to {repo} release {release_tag}.'
