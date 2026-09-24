"""python -m retrousb  - fill a USB stick with DOSBox, free DOS classics and guides.

    python -m retrousb                 pick the stick from a list, install everything
    python -m retrousb --target E:\\    use that drive (or any folder)
    python -m retrousb --list          show the catalog
    python -m retrousb --games DOOM,QUAKE,TYRIAN
    python -m retrousb --offline       only use what is already in the downloads folder
    python -m retrousb --linux         also put DOSBox for Linux on the stick
    python -m retrousb --download-only just download everything to Downloads\\RetroUSB
"""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from retrousb import builder, catalog  # noqa: E402


def pick_drive() -> str:
    from datareach.core import drives as dr
    sticks = [d for d in dr.list_drives() if d.kind == "removable" and d.ready and d.total]
    if not sticks:
        print("No USB stick found. Plug one in, or give a folder with --target.")
        sys.exit(1)
    print("USB drives:")
    for i, d in enumerate(sticks, 1):
        print(f"  {i}. {d.display_name:<28} {dr.human_bytes(d.total):>9}  {dr.human_bytes(d.free):>9} free  {d.fstype}")
    while True:
        a = input("Which one? (number, or Q to quit) ").strip().lower()
        if a == "q":
            sys.exit(0)
        if a.isdigit() and 1 <= int(a) <= len(sticks):
            return sticks[int(a) - 1].path


def open_pages(ids) -> None:
    for g in catalog.GAMES:
        if g.get("manual") and (not ids or g["id"] in ids) and g.get("page", "").startswith("http"):
            webbrowser.open(g["page"].split()[0])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="retrousb", description="Put DOSBox, free DOS classics and strategy guides on a USB stick.")
    ap.add_argument("--target", help="drive or folder to fill (default: choose a USB stick)")
    ap.add_argument("--games", help="comma-separated IDs from --list (default: all)")
    ap.add_argument("--downloads", default=builder.DEFAULT_DOWNLOADS, help="where downloads are kept and where you drop manual ones")
    ap.add_argument("--mygames", default=builder.DEFAULT_MYGAMES, help="folder with your own DOS games (one folder per game)")
    ap.add_argument("--offline", action="store_true", help="do not download anything")
    ap.add_argument("--linux", action="store_true", help="also put DOSBox for Linux on the stick")
    ap.add_argument("--open-pages", action="store_true", help="open the download pages of the manual games in your browser")
    ap.add_argument("--list", action="store_true", help="show the catalog and exit")
    ap.add_argument("--download-only", nargs="?", const="", metavar="FOLDER",
                    help="only download everything into FOLDER (default: your Downloads\\RetroUSB), no stick needed")
    ap.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")
    a = ap.parse_args(argv)

    if a.list:
        for g in catalog.GAMES:
            how = "manual download" if g.get("manual") else "automatic"
            print(f"{g['id']:<9} {g['year']}  {g['title']}\n          {g['genre']} - {g['kind']}, {how}\n          {g['blurb']}")
        return 0

    ids = [s.strip().upper() for s in a.games.split(",")] if a.games else None
    if ids:
        bad = [i for i in ids if i not in catalog.BY_ID]
        if bad:
            print("Unknown game IDs: " + ", ".join(bad) + " (see --list)")
            return 2
    if a.download_only is not None:
        dest = a.download_only or os.path.join(os.path.expanduser("~"), "Downloads", "RetroUSB")
        if a.open_pages:
            open_pages(ids)
        res = builder.download_only(os.path.abspath(dest), ids, ["windows"] + (["linux"] if a.linux else []))
        print(f"\nLater, build the stick from these files:  Build-RetroUSB.cmd --target D:\\ --downloads \"{os.path.abspath(dest)}\"")
        return 0 if res["got"] else 1

    target = a.target or pick_drive()
    target = os.path.abspath(target)
    if not a.yes:
        print(f"\nThis adds Retro USB folders to {target} (START-HERE.bat, README.TXT, DOSBOX, GAMES, GUIDES).")
        print("Other files on it are left alone. Nothing is formatted.")
        if input("Go ahead? (Y/N) ").strip().lower() not in ("y", "yes"):
            return 0
    if a.open_pages:
        open_pages(ids)
    os.makedirs(a.mygames, exist_ok=True)
    res = builder.build(target, ids, a.downloads, a.mygames, a.offline, ["windows"] + (["linux"] if a.linux else []))
    return 0 if res["games"] or res["mine"] else 1


if __name__ == "__main__":
    sys.exit(main())
