"""Retro USB builder tests: fake downloads, a folder standing in for the stick."""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from retrousb import builder, catalog  # noqa: E402


def mkzip(files):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in files.items():
            z.writestr(n, d)
    return b.getvalue()


WOLF_INNER = mkzip({"WOLF3D.EXE": b"MZwolf", "VSWAP.WL1": b"v" * 100, "GAMEMAPS.WL1": b"m"})
WOLF = mkzip({"W3DSW14.SHR": WOLF_INNER, "INSTALL.EXE": b"MZinst", "README.TXT": b"hi"})
DOOM_LZH = mkzip({"DOOM.EXE": b"MZdoom", "DOOM1.WAD": b"IWAD"})       # stands in for the DEICE archive
DOOM = mkzip({"DOOMS_19.1": DOOM_LZH[:40], "DOOMS_19.2": DOOM_LZH[40:], "INSTALL.BAT": b"deice"})
ROTT = mkzip({"HUNTBGIN.WAD": b"x", "OTHER.DAT": b"y", "INSTALL.EXE": b"MZ"})   # no ROTT.EXE -> installer
TYRIAN = mkzip({"Tyrian 2000/TYRIAN.EXE": b"MZ", "Tyrian 2000/TYRIAN.HDT": b"h", "Tyrian 2000/Long Name Folder/FILE.DAT": b"f"})
DOSBOX = mkzip({"dosbox-staging-windows-x64-v9/dosbox.exe": b"MZdb", "dosbox-staging-windows-x64-v9/SDL2.dll": b"dll"})
RELEASE = json.dumps({"tag_name": "v9", "assets": [
    {"name": "dosbox-staging-windows-x64-v9-setup.exe", "browser_download_url": "https://x/setup.exe"},
    {"name": "dosbox-staging-windows-x64-v9.zip", "browser_download_url": "https://x/db.zip"},
    {"name": "dosbox-staging-linux-x86_64-v9.tar.xz", "browser_download_url": "https://x/db.tar.xz"},
]}).encode()


class Fake:
    def __init__(self, table):
        self.table, self.calls = table, []

    def __call__(self, url):
        self.calls.append(url)
        for k, v in self.table.items():
            if url.endswith(k):
                return v
        raise IOError("404 " + url)


class RetroUSBTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.stick = os.path.join(self.tmp, "stick")
        self.dl = os.path.join(self.tmp, "dl")
        self.my = os.path.join(self.tmp, "my")
        os.makedirs(self.dl)
        os.makedirs(self.my)
        self.fake = Fake({"1wolf14.zip": WOLF, "doom19s.zip": DOOM, "1rott13.zip": ROTT,
                          "htic_v12.zip": b"PK not really heretic", "quake106.zip": b"PK junk", "releases/latest": RELEASE, "db.zip": DOSBOX})

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def read(self, rel):
        with open(os.path.join(self.stick, *rel.split("/")), "rb") as f:
            return f.read()

    def build(self, ids, **kw):
        return builder.build(self.stick, ids, self.dl, self.my, fetcher=self.fake, **kw)

    def test_full_build(self):
        with open(os.path.join(self.dl, "tyrian2000.zip"), "wb") as f:
            f.write(TYRIAN)
        # a GOG-style game of the user's own
        g = os.path.join(self.my, "X-COM UFO Defense")
        os.makedirs(os.path.join(g, "XCOM"))
        os.makedirs(os.path.join(g, "DOSBOX"))
        open(os.path.join(g, "XCOM", "GO.BAT"), "w").write("ufo")
        open(os.path.join(g, "DOSBOX", "dosbox.exe"), "w").write("gog's own")
        open(os.path.join(g, "dosboxXCOM.conf"), "w").write("[sdl]\nx=1\n[autoexec]\n@echo off\nmount C \"..\"\nimgmount d \"..\\game.ins\" -t iso\nc:\ncd XCOM\ngo.bat\nexit\n")
        open(os.path.join(g, "game.ins"), "w").write("cue")
        res = self.build(["WOLF3D", "DOOM", "ROTT", "HERETIC", "TYRIAN", "ARENA"])

        ids = {x["id"]: x for x in res["games"]}
        self.assertEqual(ids["WOLF3D"]["mode"], "ready")
        self.assertEqual(self.read("GAMES/WOLF3D/WOLF3D.EXE"), b"MZwolf")
        self.assertEqual(ids["DOOM"]["mode"], "ready", "split DOOMS_19.1/.2 joined and unpacked")
        self.assertEqual(self.read("GAMES/DOOM/DOOM1.WAD"), b"IWAD")
        self.assertEqual(ids["ROTT"]["mode"], "installer")
        self.assertEqual(ids["ROTT"]["installer"], "INSTALL.EXE")
        self.assertTrue(os.path.isfile(os.path.join(self.stick, "GAMES", "_SETUP", "ROTT", "HUNTBGIN.WAD")))
        self.assertEqual(ids["TYRIAN"]["mode"], "ready")
        self.assertEqual(self.read("GAMES/TYRIAN/TYRIAN.EXE"), b"MZ", "common top folder stripped")
        self.assertTrue(os.path.isfile(os.path.join(self.stick, "GAMES", "TYRIAN", "LONGNAME", "FILE.DAT")), "8.3 folder names")
        self.assertEqual({m["id"] for m in res["missing"]}, {"HERETIC", "ARENA"})
        self.assertNotIn("https://x/setup.exe", self.fake.calls)
        self.assertEqual(res["dosbox"]["windows"], "DOSBOX/WIN/dosbox.exe")
        self.assertEqual(self.read("DOSBOX/WIN/dosbox.exe"), b"MZdb")

        # own game: GOG's DOSBox folder left out, its autoexec translated
        self.assertEqual(res["mine"][0]["id"], "X-COMUFO")
        self.assertFalse(os.path.exists(os.path.join(self.stick, "GAMES", "MY", "X-COMUFO", "DOSBOX")))
        conf = self.read("DOSBOX/CONF/X-COMUFO.CONF").decode()
        self.assertIn('mount C "GAMES/MY/X-COMUFO"', conf)
        self.assertIn('imgmount D "GAMES/MY/X-COMUFO/GAME.INS" -t iso', conf)
        self.assertNotIn('mount D "GUIDES"', conf, "the game uses D: itself")
        self.assertTrue(conf.rstrip().endswith("exit"))

        # launchers and menus
        start = self.read("START-HERE.bat").decode()
        self.assertIn("\r\n", start)
        self.assertIn("DOSBOX\\CONF\\WOLF3D.CONF", start)
        self.assertIn("DOSBOX\\CONF\\X-COMUFO.CONF", start)
        menu = self.read("GAMES/MENU.BAT").decode()
        self.assertIn("call \\MENU\\WOLF3D.BAT", menu)
        self.assertNotIn("|", menu)
        run = self.read("GAMES/MENU/ROTT.BAT").decode()
        self.assertIn("\nINSTALL.EXE", run.replace("\r", ""))
        self.assertIn("cd \\ROTT", run)
        self.assertIn("ROTT.EXE", self.read("GAMES/MENU/ROTT.BAT").decode())
        self.assertIn('mount C "GAMES"', self.read("DOSBOX/CONF/DOOM.CONF").decode())
        self.assertIn(b"DOSBOX SURVIVAL GUIDE", self.read("GUIDES/DOSBOX.TXT"))
        self.assertIn(b"DOSBOX.TXT", self.read("GUIDES/INDEX.HTM"))

        # second run offline keeps what is there, downloads nothing
        self.fake.calls.clear()
        res2 = builder.build(self.stick, ["WOLF3D", "ROTT"], os.path.join(self.tmp, "empty"), self.my, offline=True, fetcher=self.fake)
        self.assertEqual({g["id"] for g in res2["games"]}, {"WOLF3D", "ROTT"})
        self.assertEqual(self.fake.calls, [])

    def test_real_lha_self_extractor(self):
        """3D Realms ship an LHA self-extractor (.SHR) inside the zip; unpack it like the real thing."""
        import subprocess
        lha = shutil.which("lha")
        if not lha:
            self.skipTest("lha not installed")
        src = os.path.join(self.tmp, "lzsrc")
        os.makedirs(src)
        for n, d in {"DUKE3D.EXE": b"MZduke" * 500, "DUKE3D.GRP": b"KenSilverman" * 4000, "SETUP.EXE": b"MZsetup"}.items():
            open(os.path.join(src, n), "wb").write(d)
        subprocess.run([lha, "-aq", "../x.lzh", "DUKE3D.EXE", "DUKE3D.GRP", "SETUP.EXE"], cwd=src, check=True)
        sfx = b"MZ" + b"\0" * 1998 + open(os.path.join(self.tmp, "x.lzh"), "rb").read()   # an exe stub, then the archive
        with open(os.path.join(self.dl, "3dduke13.zip"), "wb") as f:
            f.write(mkzip({"DN3DSW13.SHR": sfx, "INSTALL.EXE": b"MZ", "LICENSE.DOC": b"x"}))
        from unittest import mock
        with mock.patch.dict(catalog.BY_ID["DUKE3D"], {"md5": None, "size": None}):   # our stand-in isn't the real zip
            res = self.build(["DUKE3D"])
        self.assertEqual(res["games"][0]["mode"], "ready")
        self.assertEqual(self.read("GAMES/DUKE3D/DUKE3D.GRP"), b"KenSilverman" * 4000)
        self.assertIn("call \\MENU\\DUKE3DS.BAT", self.read("GAMES/MENU.BAT").decode())

    def test_md5_mismatch_rejected(self):
        res = self.build(["QUAKE"])
        self.assertEqual(res["games"], [])
        self.assertFalse(os.path.exists(os.path.join(self.dl, "quake106.zip")))

    def test_dropped_wrong_file_ignored(self):
        with open(os.path.join(self.dl, "omf2097.zip"), "wb") as f:
            f.write(mkzip({"SOMETHING.EXE": b"MZ"}))
        res = self.build(["OMF"])
        self.assertEqual([m["id"] for m in res["missing"]], ["OMF"])

    def test_cd_image(self):
        with open(os.path.join(self.dl, "GDI95.iso"), "wb") as f:
            f.write(b"\0" * (2 * 1024 * 1024))
        res = self.build(["CNC"])
        self.assertEqual(res["games"][0]["cd"], "DISC.ISO")
        run = self.read("GAMES/MENU/CNC.BAT").decode()
        self.assertLess(run.index("imgmount e C:\\_SETUP\\CNC\\DISC.ISO -t iso"), run.index("goto run"), "disc mounted on every start")

    def test_dos_names(self):
        taken = set()
        self.assertEqual(builder.dos_name("Long File Name.data", taken), "LONGFILE.DAT")
        self.assertEqual(builder.dos_name("longfilenameX.dat", taken), "LONGFI~1.DAT")
        self.assertEqual(builder.dos_name("DOOM.EXE"), "DOOM.EXE")
        self.assertEqual(builder.cmd_echo("Command & Conquer (GDI)"), "Command ^& Conquer ^(GDI^)")

    def test_catalog(self):
        ids = [g["id"] for g in catalog.GAMES]
        self.assertEqual(len(ids), len(set(ids)))
        for g in catalog.GAMES:
            self.assertLessEqual(len(g["id"]), 8)
            self.assertTrue(os.path.isfile(os.path.join(builder.GUIDES_SRC, g["guide"])), g["guide"])
            self.assertTrue(g.get("urls") or g.get("manual") or g.get("page"), g["id"])


if __name__ == "__main__":
    unittest.main()
