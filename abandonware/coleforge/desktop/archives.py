"""ColeForge archive installers for the desktop side.

Mirrors web/engines/common/archive.js (window.CFArchive):

    unzip_bytes(data, skip_unsupported=False) -> {path: bytes}
        ZIP reader (stored + deflate via Python's zipfile, CRC checked).
        Entries using other methods (implode, shrink, ...) raise ArchiveError
        naming the entry and method, unless skip_unsupported=True.
    unlha_bytes(data) -> {path: bytes}
        LHA/LZH reader implemented here: -lh0-, -lh5-, -lh6-, -lh7-
        (static-Huffman LZSS), header levels 0/1/2 (and 3), CRC-16 checked.
    install_shareware(game_id, paths_or_bytes, dest_dir) -> dict
        Recognises what the user supplied (quake106.zip, resource.1, pak0.pak;
        1wolf14.zip, WOLF.1, *.WL1), unpacks nested archives, verifies known
        sizes / MD5s from GAMES and writes the files (lower-case names) to
        dest_dir. Returns {"installed": [...], "missing": [...],
        "warnings": [...], "found": {name: info}}.

Python 3.8+, standard library only.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import struct
import zipfile
import zlib
from typing import Dict, Iterable, List, Mapping, Optional, Union

__all__ = [
    "ArchiveError", "unzip_bytes", "unlha_bytes", "install_shareware",
    "detect", "expand", "crc16", "GAMES",
]


class ArchiveError(Exception):
    """Raised for damaged or unsupported archives."""

    def __init__(self, message: str, unsupported: Optional[list] = None):
        super().__init__(message)
        self.unsupported = unsupported or []


def _norm_path(p: str) -> str:
    p = p.replace("\\", "/")
    parts = [s for s in p.split("/") if s and s not in (".", "..")]
    return "/".join(parts)


# ---------------------------------------------------------------------- CRC16
_CRC16_TABLE = []
for _n in range(256):
    _c = _n
    for _k in range(8):
        _c = (0xA001 ^ (_c >> 1)) if (_c & 1) else (_c >> 1)
    _CRC16_TABLE.append(_c)
del _n, _c, _k


def crc16(data: bytes) -> int:
    """CRC-16/ARC as used by LHA."""
    c = 0
    t = _CRC16_TABLE
    for b in data:
        c = t[(c ^ b) & 0xFF] ^ (c >> 8)
    return c


# ------------------------------------------------------------------------ ZIP
ZIP_METHODS = {0: "stored", 1: "shrink", 2: "reduce-1", 3: "reduce-2", 4: "reduce-3", 5: "reduce-4",
               6: "implode", 8: "deflate", 9: "deflate64", 12: "bzip2", 14: "lzma", 93: "zstd",
               95: "xz", 98: "ppmd", 99: "AES-encrypted"}


def unzip_bytes(data: bytes, skip_unsupported: bool = False) -> Dict[str, bytes]:
    """Unpack a ZIP archive held in memory. Supports stored and deflate."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(bytes(data)))
    except zipfile.BadZipFile as e:
        raise ArchiveError("not a ZIP archive (%s)" % e)
    out: Dict[str, bytes] = {}
    unsupported = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        path = _norm_path(info.filename)
        if not path:
            continue
        why = None
        if info.flag_bits & 1:
            why = "is encrypted"
        elif info.compress_type not in (0, 8):
            why = "uses compression method %d (%s)" % (
                info.compress_type, ZIP_METHODS.get(info.compress_type, "unknown"))
        if why:
            unsupported.append({"name": info.filename, "method": info.compress_type,
                                "methodName": ZIP_METHODS.get(info.compress_type, "unknown"), "reason": why})
            continue
        try:
            content = zf.read(info)  # zipfile verifies the CRC-32
        except (zipfile.BadZipFile, zlib.error) as e:
            raise ArchiveError("ZIP entry %s is damaged (%s)" % (info.filename, e))
        out[path] = content
    if unsupported and not skip_unsupported:
        u = unsupported[0]
        more = " (and %d more)" % (len(unsupported) - 1) if len(unsupported) > 1 else ""
        raise ArchiveError('ZIP entry "%s" %s, which ColeForge cannot unpack%s. Extract the archive with '
                           "another tool and install the files directly." % (u["name"], u["reason"], more),
                           unsupported)
    if unsupported:
        out_meta = _ZipResult(out)
        out_meta.unsupported = unsupported
        return out_meta
    return out


class _ZipResult(dict):
    """dict of files that also carries the list of skipped entries."""
    unsupported: list = []


# ------------------------------------------------------------------------ LHA
NC = 510
NT = 19
TBIT = 5
CBIT = 9
THRESHOLD = 3
LHA_DICBITS = {b"-lh5-": 13, b"-lh6-": 15, b"-lh7-": 16}


class _Huff:
    """Canonical Huffman lookup table indexed by the next `bits` bits."""

    __slots__ = ("bits", "lens", "table", "single")

    def __init__(self, lens, n, single=-1):
        self.single = single
        self.lens = lens
        self.table = None
        if single >= 0:
            self.bits = 0
            return
        mx = max(lens[:n]) if n else 0
        if mx > 16:
            raise ArchiveError("LHA: bad Huffman table")
        self.bits = mx
        if mx == 0:
            self.single = 0
            return
        size = 1 << mx
        table = [-1] * size
        code = 0
        for ln in range(1, mx + 1):
            for sym in range(n):
                if lens[sym] != ln:
                    continue
                span = 1 << (mx - ln)
                start = code << (mx - ln)
                if start + span > size:
                    raise ArchiveError("LHA: bad Huffman table (over-subscribed)")
                table[start:start + span] = [sym] * span
                code += 1
            code <<= 1
        # pack (symbol, length) for fast decode: value = sym << 5 | len
        self.table = [(-1 if s < 0 else (s << 5) | lens[s]) for s in table]


class _Bits:
    """MSB-first bit reader with a big-int accumulator."""

    __slots__ = ("data", "pos", "end", "acc", "n")

    def __init__(self, data, start, end):
        self.data = data
        self.pos = start
        self.end = end
        self.acc = 0
        self.n = 0

    def refill(self):
        # make sure at least 32 bits are available (zero padding past the end)
        pos = self.pos
        chunk = self.data[pos:min(pos + 8, self.end)]
        k = len(chunk)
        if k < 8:
            chunk = bytes(chunk) + b"\0" * (8 - k)
        self.pos = pos + 8
        self.acc = ((self.acc & ((1 << self.n) - 1)) << 64) | int.from_bytes(chunk, "big")
        self.n += 64

    def peek16(self):
        if self.n < 16:
            self.refill()
        return (self.acc >> (self.n - 16)) & 0xFFFF

    def get(self, k):
        if k == 0:
            return 0
        if self.n < k:
            self.refill()
        self.n -= k
        return (self.acc >> self.n) & ((1 << k) - 1)

    def skip(self, k):
        if self.n < k:
            self.refill()
        self.n -= k


def _decode_sym(h: _Huff, br: _Bits) -> int:
    if h.single >= 0:
        return h.single
    if br.n < 16:
        br.refill()
    v = h.table[(br.acc >> (br.n - h.bits)) & ((1 << h.bits) - 1)]
    if v < 0:
        raise ArchiveError("LHA: invalid Huffman code (damaged data)")
    br.n -= v & 31
    return v >> 5


def _read_pt_len(br: _Bits, nn: int, nbit: int, special: int) -> _Huff:
    n = br.get(nbit)
    if n == 0:
        return _Huff([0] * nn, nn, single=br.get(nbit))
    lens = [0] * max(nn, n)
    i = 0
    while i < n:
        bb = br.peek16()
        c = bb >> 13
        if c == 7:
            mask = 1 << 12
            while mask & bb:
                mask >>= 1
                c += 1
            if c > 16:
                raise ArchiveError("LHA: bad code length")
        br.skip(3 if c < 7 else c - 3)
        lens[i] = c
        i += 1
        if i == special:
            z = br.get(2)
            while z > 0 and i < len(lens):
                lens[i] = 0
                i += 1
                z -= 1
    return _Huff(lens, nn)


def _read_c_len(br: _Bits, t: _Huff) -> _Huff:
    n = br.get(CBIT)
    if n == 0:
        return _Huff([0] * NC, NC, single=br.get(CBIT))
    lens = [0] * NC
    i = 0
    while i < n:
        c = _decode_sym(t, br)
        if c <= 2:
            if c == 0:
                c = 1
            elif c == 1:
                c = br.get(4) + 3
            else:
                c = br.get(CBIT) + 20
            while c > 0 and i < NC:
                lens[i] = 0
                i += 1
                c -= 1
        elif i < NC:
            lens[i] = c - 2
            i += 1
        else:
            raise ArchiveError("LHA: bad literal table")
    return _Huff(lens, NC)


def _decode_lzh(data: bytes, start: int, csize: int, osize: int, dicbit: int) -> bytes:
    out = bytearray()
    if osize == 0:
        return bytes(out)
    np_ = dicbit + 1
    pbit = 4 if dicbit <= 13 else 5
    br = _Bits(data, start, start + csize)
    blocksize = 0
    append = out.append
    while len(out) < osize:
        if blocksize == 0:
            blocksize = br.get(16)
            t = _read_pt_len(br, NT, TBIT, 3)
            ch = _read_c_len(br, t)
            ph = _read_pt_len(br, np_, pbit, -1)
            if blocksize == 0:
                blocksize = 0x10000
            # local copies for the hot loop
            c_single, c_bits, c_table = ch.single, ch.bits, ch.table
            p_single, p_bits, p_table = ph.single, ph.bits, ph.table
            c_mask = (1 << c_bits) - 1
            p_mask = (1 << p_bits) - 1
        # decode up to `blocksize` symbols
        remaining = blocksize
        while remaining:
            remaining -= 1
            # --- literal / length symbol
            if c_single >= 0:
                c = c_single
            else:
                if br.n < 32:
                    br.refill()
                v = c_table[(br.acc >> (br.n - c_bits)) & c_mask]
                if v < 0:
                    raise ArchiveError("LHA: invalid Huffman code (damaged data)")
                br.n -= v & 31
                c = v >> 5
            if c < 256:
                append(c)
                if len(out) >= osize:
                    break
                continue
            ln = c - (256 - THRESHOLD)
            # --- position
            if p_single >= 0:
                d = p_single
            else:
                if br.n < 32:
                    br.refill()
                v = p_table[(br.acc >> (br.n - p_bits)) & p_mask]
                if v < 0:
                    raise ArchiveError("LHA: invalid Huffman code (damaged data)")
                br.n -= v & 31
                d = v >> 5
            if d > 1:
                k = d - 1
                if br.n < k:
                    br.refill()
                br.n -= k
                d = (1 << k) + ((br.acc >> br.n) & ((1 << k) - 1))
            pos = len(out)
            frm = pos - d - 1
            if ln > osize - pos:
                ln = osize - pos
            if frm >= 0 and d + 1 >= ln:
                out += out[frm:frm + ln]
            elif frm >= 0:
                # overlapping copy: repeat the period
                period = out[frm:pos]
                while ln > 0:
                    piece = period[:ln]
                    out += piece
                    ln -= len(piece)
            else:
                for _ in range(ln):
                    append(0x20 if frm < 0 else out[frm])  # dictionary starts as spaces
                    frm += 1
            if len(out) >= osize:
                break
        blocksize = remaining
        # keep the accumulator small
        if br.n < 64:
            br.acc &= (1 << br.n) - 1
    return bytes(out[:osize])


def _is_lha_header_at(data: bytes, i: int) -> bool:
    if i + 22 > len(data):
        return False
    if data[i + 2] != 0x2D or data[i + 3] != 0x6C or data[i + 6] != 0x2D:
        return False
    a, b = data[i + 4], data[i + 5]
    if a not in (0x68, 0x7A):
        return False
    if not (0x30 <= b <= 0x39 or 0x61 <= b <= 0x7A):
        return False
    return data[i + 20] <= 3


def _find_lha_start(data: bytes) -> int:
    lim = min(len(data) - 22, 256 * 1024)
    for m in re.finditer(rb"-l[hz][0-9a-z]-", data[:lim + 7]):
        i = m.start() - 2
        if i >= 0 and _is_lha_header_at(data, i) and (data[i] > 0 or data[i + 20] in (2, 3)):
            return i
    return -1


def _parse_ext(data: bytes, p: int, size: int, size_bytes: int, info: dict):
    total = 0
    while size > 0:
        if p + size > len(data):
            raise ArchiveError("LHA: extended header runs past the end of the archive")
        typ = data[p]
        d0, d1 = p + 1, p + size - size_bytes
        if typ == 0x01:
            info["name"] = data[d0:d1].decode("latin-1")
        elif typ == 0x02:
            info["dir"] = data[d0:d1].decode("latin-1").replace("\xff", "/")
        total += size
        if size_bytes == 4:
            nxt = struct.unpack_from("<I", data, p + size - 4)[0]
        else:
            nxt = struct.unpack_from("<H", data, p + size - 2)[0]
        p += size
        size = nxt
    return p, total


def unlha_bytes(data: bytes) -> Dict[str, bytes]:
    """Unpack an LHA/LZH archive held in memory."""
    data = bytes(data)
    p = _find_lha_start(data)
    if p < 0:
        raise ArchiveError("not an LHA/LZH archive")
    out: Dict[str, bytes] = {}
    while p < len(data):
        if not _is_lha_header_at(data, p):
            if data[p] == 0:
                break
            raise ArchiveError("LHA: bad header at offset %d" % p)
        method = data[p + 2:p + 7]
        csize, osize = struct.unpack_from("<II", data, p + 7)
        level = data[p + 20]
        info = {"name": "", "dir": ""}
        if level in (0, 1):
            hsize = data[p]
            nlen = data[p + 21]
            info["name"] = data[p + 22:p + 22 + nlen].decode("latin-1")
            crc = struct.unpack_from("<H", data, p + 22 + nlen)[0]
            start = p + hsize + 2
            if level == 1:
                first = struct.unpack_from("<H", data, p + hsize)[0]
                start, total = _parse_ext(data, p + hsize + 2, first, 2, info)
                csize -= total
        elif level == 2:
            hsize = struct.unpack_from("<H", data, p)[0]
            crc = struct.unpack_from("<H", data, p + 21)[0]
            first = struct.unpack_from("<H", data, p + 24)[0]
            _parse_ext(data, p + 26, first, 2, info)
            start = p + hsize
        else:
            crc = struct.unpack_from("<H", data, p + 21)[0]
            hsize = struct.unpack_from("<I", data, p + 24)[0]
            first = struct.unpack_from("<I", data, p + 28)[0]
            _parse_ext(data, p + 32, first, 4, info)
            start = p + hsize
        if csize < 0 or start + csize > len(data):
            raise ArchiveError("LHA: archive is truncated (%s)" % (info["name"] or method.decode("latin-1")))
        full = info["name"].replace("\xff", "/")
        if info["dir"]:
            full = info["dir"].rstrip("/") + "/" + full
        path = _norm_path(full)
        if method != b"-lhd-":
            if method in (b"-lh0-", b"-lz4-"):
                content = data[start:start + csize]
            elif method in LHA_DICBITS:
                content = _decode_lzh(data, start, csize, osize, LHA_DICBITS[method])
            else:
                raise ArchiveError('LHA entry "%s" uses method %s, which ColeForge cannot unpack '
                                   "(supported: -lh0-, -lh5-, -lh6-, -lh7-)" % (path, method.decode("latin-1")))
            if len(content) != osize:
                raise ArchiveError("LHA entry %s has the wrong size" % path)
            if crc16(content) != crc:
                raise ArchiveError("LHA entry %s failed its CRC check (damaged archive?)" % path)
            if path:
                out[path] = content
        p = start + csize
    return out


# ------------------------------------------------------------------ detection
def detect(data: bytes) -> Optional[str]:
    if len(data) >= 4 and data[:2] == b"PK" and data[2] in (3, 5) and data[3] in (4, 6):
        return "zip"
    if len(data) >= 22 and _is_lha_header_at(data, 0):
        return "lha"
    if len(data) > 64 and data[:2] == b"MZ":
        if _find_lha_start(data) > 0:
            return "lha"
        if zipfile.is_zipfile(io.BytesIO(data)):
            return "zip"
    return None


def expand(files: Mapping[str, bytes], depth: int = 4, log: Optional[list] = None) -> List[dict]:
    """Recursively unpack archives; returns [{'path', 'bytes', 'from'}]."""
    out = []
    queue = [{"path": _norm_path(k) or k, "bytes": bytes(v), "from": None, "depth": 0} for k, v in files.items()]
    while queue:
        f = queue.pop(0)
        out.append(f)
        if f["depth"] >= depth:
            continue
        kind = detect(f["bytes"])
        if not kind:
            continue
        try:
            inner = unzip_bytes(f["bytes"], skip_unsupported=True) if kind == "zip" else unlha_bytes(f["bytes"])
        except ArchiveError as e:
            if log is not None:
                log.append("%s: %s" % (f["path"], e))
            continue
        if log is not None:
            for u in getattr(inner, "unsupported", []) or []:
                log.append("%s: %s %s (skipped)" % (f["path"], u["name"], u["reason"]))
        for name, b in inner.items():
            queue.append({"path": f["path"] + "/" + name, "bytes": b, "from": f["path"], "depth": f["depth"] + 1})
    return out


# ------------------------------------------------------------ shareware table
def _wolf(name, size, md5):
    return {"name": name, "required": True, "versions": [{"size": size, "md5": md5, "label": "shareware 1.4"}]}


GAMES = {
    "quake": {
        "title": "Quake (shareware)",
        "files": [
            {"name": "pak0.pak", "required": True, "magic": b"PACK",
             "versions": [{"size": 18689235, "md5": "5906e5998fc3d896ddaf5e6a62e03abb", "label": "shareware 1.06"}]},
            # registered data: only installed when the user supplies it themselves
            {"name": "pak1.pak", "required": False, "magic": b"PACK", "versions": []},
        ],
        "hint": "quake106.zip, its resource.1, or id1/pak0.pak",
    },
    "wolf3d": {
        "title": "Wolfenstein 3D (shareware)",
        "files": [
            _wolf("audiohed.wl1", 1156, "58aa1b9892d5adfa725fab343d9446f8"),
            _wolf("audiot.wl1", 132613, "4b6109e957b584e4ad7f376961f3887e"),
            _wolf("gamemaps.wl1", 27425, "30fecd7cce6bc70402651ec922d2da3d"),
            _wolf("maphead.wl1", 402, "7b6dd4e55c33c33a41d1600be5df3228"),
            _wolf("vgadict.wl1", 1024, "76a6128f3c0dd9b77939ce8313992746"),
            _wolf("vgagraph.wl1", 326568, "74decb641b1a4faed173e10ab744bff0"),
            _wolf("vgahead.wl1", 471, "61bf1616e78367853c91f2c04e2c1cb7"),
            _wolf("vswap.wl1", 742912, "6efa079414b817c97db779cecfb081c9"),
        ],
        "hint": "1wolf14.zip, WOLF.1, or the *.WL1 files",
    },
}


def _load_inputs(paths_or_bytes) -> Dict[str, bytes]:
    if isinstance(paths_or_bytes, (bytes, bytearray, memoryview)):
        return {"input": bytes(paths_or_bytes)}
    if isinstance(paths_or_bytes, (str, os.PathLike)):
        paths_or_bytes = [paths_or_bytes]
    if isinstance(paths_or_bytes, Mapping):
        out = {}
        for k, v in paths_or_bytes.items():
            if isinstance(v, (str, os.PathLike)):
                with open(v, "rb") as fh:
                    out[str(k)] = fh.read()
            else:
                out[str(k)] = bytes(v)
        return out
    out = {}
    for p in paths_or_bytes:
        p = os.fspath(p)
        if os.path.isdir(p):
            for dirpath, _dirs, names in os.walk(p):
                for n in names:
                    full = os.path.join(dirpath, n)
                    with open(full, "rb") as fh:
                        out[os.path.relpath(full, p).replace(os.sep, "/")] = fh.read()
        else:
            with open(p, "rb") as fh:
                out[os.path.basename(p)] = fh.read()
    return out


def install_shareware(game_id: str,
                      paths_or_bytes: Union[str, os.PathLike, bytes, Iterable, Mapping],
                      dest_dir: Union[str, os.PathLike]) -> dict:
    """Install shareware game data from user-supplied files into dest_dir."""
    game = GAMES.get(str(game_id).lower())
    if game is None:
        raise ArchiveError("no shareware installer for game '%s'" % game_id)
    inputs = _load_inputs(paths_or_bytes)
    warnings: List[str] = []
    files = expand(inputs, log=warnings)
    result = {"installed": [], "missing": [], "warnings": warnings, "found": {}}
    md5cache: Dict[int, str] = {}

    def md5(b: bytes) -> str:
        k = id(b)
        if k not in md5cache:
            md5cache[k] = hashlib.md5(b).hexdigest()
        return md5cache[k]

    os.makedirs(dest_dir, exist_ok=True)
    for spec in game["files"]:
        magic = spec.get("magic")
        cands = [f for f in files
                 if f["path"].rsplit("/", 1)[-1].lower() == spec["name"]
                 and (not magic or f["bytes"][:len(magic)] == magic)]
        if not cands:
            if spec["required"]:
                result["missing"].append(spec["name"])
            continue
        pick, version = None, None
        if spec["versions"]:
            for c in cands:
                for v in spec["versions"]:
                    if (v.get("size") is None or v["size"] == len(c["bytes"])) and \
                            (not v.get("md5") or v["md5"] == md5(c["bytes"])):
                        pick, version = c, v
                        break
                if pick:
                    break
            if not pick:
                pick = cands[0]
                warnings.append("%s: size/MD5 (%d, %s) does not match the known %s file; installing it anyway"
                                % (spec["name"], len(pick["bytes"]), md5(pick["bytes"]),
                                   " / ".join(v["label"] for v in spec["versions"])))
        else:
            pick = cands[0]
        target = os.path.join(os.fspath(dest_dir), spec["name"])
        tmp = target + ".part"
        with open(tmp, "wb") as fh:
            fh.write(pick["bytes"])
        os.replace(tmp, target)
        result["installed"].append(spec["name"])
        result["found"][spec["name"]] = {"from": pick["path"], "size": len(pick["bytes"]),
                                         "md5": md5(pick["bytes"]), "verified": version is not None,
                                         "version": version["label"] if version else None}
    return result


if __name__ == "__main__":  # pragma: no cover - small CLI for manual use
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Install shareware game data for ColeForge")
    ap.add_argument("game", choices=sorted(GAMES))
    ap.add_argument("dest")
    ap.add_argument("inputs", nargs="+")
    a = ap.parse_args()
    print(json.dumps(install_shareware(a.game, a.inputs, a.dest), indent=2))
