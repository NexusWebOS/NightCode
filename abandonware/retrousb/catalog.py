"""What goes on the stick.

Only games whose owners let anyone copy them are listed here:

* "shareware": the original shareware episodes, which id Software, Apogee /
  3D Realms and Raven released for free copying.  File sizes and MD5s are the
  ones Debian's game-data-packager checks (the same table ColeForge uses), and
  a download that does not match is thrown away.
* "freeware": full games that their publishers later gave away for free.
  Their official download pages have moved over the years, so these are
  "manual": the builder opens the page (or tells you what to look for), you
  save the file into the downloads folder, and the builder finds it there by
  its name or by the files inside it.

Anything else you own (GOG, Steam, old CDs) goes in through ``mygames``.

Each entry:
    id        8.3-safe folder name on the stick (also the DOS menu name)
    title, year, genre, blurb
    kind      shareware | freeware
    file      archive name as distributed
    size/md5  known values (None = not checked)
    urls      download mirrors, tried in order
    manual    True: no automatic download
    page      where the file is offered / how to find it
    match     regexes for a dropped-in file name (case-insensitive)
    contains  file names that identify the archive by its contents
    exe       DOS command that starts the game, or a list of them (the first whose
              program exists wins); the program may sit in a sub-folder
    setup     sound/controls setup program, if the game has one
    installer DOS command for first-run install when the archive can't be unpacked here
    cd        True: a CD image; the first-run step mounts it as E:
    notes     shown before first run
    guide     guides/<file> on the stick
"""

IDSTUFF = [
    "https://ftp.fu-berlin.de/pc/msdos/games/idgames/idstuff/",
    "ftp://ftp.fu-berlin.de/pc/msdos/games/idgames/idstuff/",
    "https://mirrors.syringanetworks.net/idgames/idstuff/",
    "ftp://mirrors.syringanetworks.net/idgames/idstuff/",
]

APOGEE = ["http://ftp.funet.fi/pub/msdos/games/apogee/", "ftp://ftp.3drealms.com/share/"]
GDP = "https://game-data-packager.debian.net/"   # Debian's game-data-packager mirror


def apogee(fname):
    return [m + fname for m in APOGEE]


GAMES = [
    {
        "id": "DOOM", "title": "DOOM (shareware, Knee-Deep in the Dead)", "year": 1993, "genre": "First-person shooter",
        "blurb": "The one that started it all: 9 levels on Phobos.",
        "kind": "shareware", "file": "doom19s.zip", "size": None, "md5": None,
        "urls": [m + "doom/doom19s.zip" for m in IDSTUFF],
        "contains": ["DOOMS_19.1", "DOOM1.WAD"],
        "exe": "DOOM.EXE", "setup": "SETUP.EXE", "installer": "INSTALL.BAT",
        "guide": "DOOM.TXT",
    },
    {
        "id": "WOLF3D", "title": "Wolfenstein 3D (shareware, Escape from Wolfenstein)", "year": 1992, "genre": "First-person shooter",
        "blurb": "Break out of Castle Wolfenstein: 10 floors and Hans Grosse.",
        "kind": "shareware",
        "sources": [  # the Apogee and the 3D Realms repacks differ; both are the real 1.4 shareware
            {"file": "1wolf14.zip", "size": 728992, "md5": "b9cbb08d192d1e4bf00c5982ff4f3cbf", "urls": apogee("1wolf14.zip")[:1]},
            {"file": "1wolf14.zip", "size": 856401, "md5": "a29432cd4a5184d552d8e5da8f80a531", "urls": apogee("1wolf14.zip")[1:]},
        ],
        "contains": ["W3DSW14.SHR", "WOLF3D.EXE"],
        "exe": "WOLF3D.EXE", "installer": "INSTALL.EXE",
        "guide": "WOLF3D.TXT",
    },
    {
        "id": "HERETIC", "title": "Heretic (shareware, City of the Damned)", "year": 1994, "genre": "First-person shooter",
        "blurb": "Raven's dark-fantasy DOOM: tomes, artifacts and an elven wand.",
        "kind": "shareware", "file": "htic_v12.zip", "size": 2898794, "md5": "420b23b3d8f2cbd164c121369eaa2b09",
        "urls": [m + "heretic/htic_v12.zip" for m in IDSTUFF],
        "contains": ["HERETIC1.WAD"],
        "exe": "HERETIC.EXE", "setup": "SETUP.EXE", "installer": "INSTALL.BAT",
        "guide": "HERETIC.TXT",
    },
    {
        "id": "HEXEN", "title": "Hexen: Beyond Heretic (demo)", "year": 1995, "genre": "First-person action RPG",
        "blurb": "Three classes, hub worlds, puzzle items: the first hub's opening maps.",
        "kind": "shareware", "file": "hexndemo.zip", "size": None, "md5": None,
        "urls": [m + "hexen/hexndemo.zip" for m in IDSTUFF],
        "contains": ["HEXEN.WAD"],
        "exe": "HEXEN.EXE", "setup": "SETUP.EXE", "installer": "INSTALL.BAT",
        "guide": "HEXEN.TXT",
    },
    {
        "id": "QUAKE", "title": "Quake (shareware, Dimension of the Doomed)", "year": 1996, "genre": "First-person shooter",
        "blurb": "Full 3D, Trent Reznor's soundtrack, and Chthon waiting at the end.",
        "kind": "shareware", "file": "quake106.zip", "size": 9094045, "md5": "8cee4d03ee092909fdb6a4f84f0c1357",
        "urls": [m + "quake/quake106.zip" for m in IDSTUFF],
        "contains": ["RESOURCE.1", "PAK0.PAK"],
        "exe": "QUAKE.EXE", "installer": "INSTALL.BAT",
        "notes": "Quake needs a fast machine even in DOSBox. Lower the screen size with - if it is slow.",
        "guide": "QUAKE.TXT",
    },
    {
        "id": "ROTT", "title": "Rise of the Triad (shareware, The HUNT Begins)", "year": 1995, "genre": "First-person shooter",
        "blurb": "Five heroes, jump pads, God mode and dog mode. Completely unhinged.",
        "kind": "shareware",
        "sources": [
            {"file": "1rott13.zip", "size": 3741577, "md5": "6040bd5bcef010fad286852c5d6ac1b9", "urls": apogee("1rott13.zip")[:1]},
            {"file": "1rott13.zip", "size": 3668139, "md5": "0fafd6b629eab80278fc726e31f9cf41", "urls": apogee("1rott13.zip")[1:]},
        ],
        "contains": ["HUNTBGIN.WAD", "ROTTSW13.SHR"],
        "exe": "ROTT.EXE", "setup": "SETUP.EXE", "installer": "INSTALL.EXE",
        "guide": "ROTT.TXT",
    },
    {
        "id": "DUKE3D", "title": "Duke Nukem 3D (shareware, L.A. Meltdown)", "year": 1996, "genre": "First-person shooter",
        "blurb": "Come get some. Episode one: Hollywood to the Abyss.",
        "kind": "shareware", "file": "3dduke13.zip", "size": 5924374, "md5": "04e4ca70b8a2d59ed56c451c5c1d5d39",
        "urls": ["ftp://ftp.3drealms.com/share/3dduke13.zip"],
        "contains": ["DN3DSW13.SHR", "DUKE3D.GRP"],
        "exe": "DUKE3D.EXE", "setup": "SETUP.EXE", "installer": "INSTALL.EXE",
        "notes": "Run Setup once (S in the menu) to pick Sound Blaster and your controls.",
        "guide": "DUKE3D.TXT",
    },
    {
        "id": "SW", "title": "Shadow Warrior (shareware)", "year": 1997, "genre": "First-person shooter",
        "blurb": "Lo Wang, katanas, sticky bombs and a lot of bad puns.",
        "kind": "shareware", "file": "3dsw12.zip", "size": 13299147, "md5": "d77564e8764feeb1509dd0d534fb8952",
        "urls": ["ftp://ftp.3drealms.com/share/3dsw12.zip"],
        "contains": ["SWSW12.SHR", "SW.GRP"],
        "exe": "SW.EXE", "setup": "SETUP.EXE", "installer": "INSTALL.EXE",
        "notes": "Run Setup once (S in the menu) to pick Sound Blaster and your controls.",
        "guide": "SW.TXT",
    },
    {
        "id": "DUKE1", "title": "Duke Nukem (shareware, Shrapnel City)", "year": 1991, "genre": "Platformer",
        "blurb": "Duke's first outing: a 2D run-and-gun on EGA.",
        "kind": "shareware", "file": "1duke.zip", "size": 313109, "md5": "d97fadf59b7a951f66075bb5961320ed",
        "urls": apogee("1duke.zip"),
        "contains": ["DN1SW20.SHR", "DN1.EXE"],
        "exe": ["DN1.EXE"], "installer": "INSTALL.EXE",
        "guide": "APOGEE.TXT",
    },
    {
        "id": "DUKE2", "title": "Duke Nukem II (shareware)", "year": 1993, "genre": "Platformer",
        "blurb": "VGA, bigger guns, Rigelatin aliens.",
        "kind": "shareware", "file": "1duke2.zip",
        "index": {"mirrors": APOGEE[:1], "pattern": r"^(1duke2|duke2|dn2|nukem2).*\.zip$"},
        "page": "http://ftp.funet.fi/pub/msdos/games/apogee/ (the Duke Nukem II shareware zip)",
        "match": [r"(duke2|dn2|nukem2).*\.zip$"],
        "contains": ["NUKEM2.EXE", "NUKEM2.CMP", "*.SHR"],
        "exe": ["NUKEM2.EXE"], "installer": "INSTALL.EXE",
        "guide": "APOGEE.TXT",
    },
    {
        "id": "KEEN1", "title": "Commander Keen 1: Marooned on Mars (shareware)", "year": 1990, "genre": "Platformer",
        "blurb": "Billy Blaze, the pogo stick and the Vorticons. PC scrolling was born here.",
        "kind": "shareware", "file": "1keen.zip", "size": 244484, "md5": "7375d0452276388d52c35d0b3ad6ab82",
        "urls": apogee("1keen.zip"),
        "contains": ["CK1SW131.SHR", "KEEN1.EXE"],
        "exe": ["KEEN1.EXE"], "installer": "INSTALL.EXE",
        "guide": "APOGEE.TXT",
    },
    {
        "id": "KEEN4", "title": "Commander Keen 4: Secret of the Oracle (shareware)", "year": 1991, "genre": "Platformer",
        "blurb": "The best Keen: rescue the Council of Elders, meet the Dopefish.",
        "kind": "shareware",
        "sources": [
            {"file": "4keen.zip", "size": 729683, "md5": "29cf97c6e636cf167ba22d0b12af9d43", "urls": apogee("4keen.zip")},
            {"file": "4keen14.zip", "size": 592887, "md5": "1470ba6a18df1b315380b194b28a7a27", "urls": ["http://spatang.com/files/4keen14.zip"]},
        ],
        "contains": ["CK4SW14.SHR", "KEEN4E.EXE"],
        "exe": ["KEEN4E.EXE"], "installer": "INSTALL.EXE",
        "guide": "APOGEE.TXT",
    },
    {
        "id": "COSMO", "title": "Cosmo's Cosmic Adventure (shareware)", "year": 1992, "genre": "Platformer",
        "blurb": "A little green alien with suction-cup hands. Charming and hard.",
        "kind": "shareware", "file": "1cosmo.zip",
        "index": {"mirrors": APOGEE[:1], "pattern": r"^(1cosmo|cosmo).*\.zip$"},
        "page": "http://ftp.funet.fi/pub/msdos/games/apogee/ (the Cosmo shareware zip)",
        "match": [r"cosmo.*\.zip$"],
        "contains": ["COSMO1.EXE", "*.SHR"],
        "exe": ["COSMO1.EXE"], "installer": "INSTALL.EXE",
        "guide": "APOGEE.TXT",
    },
    {
        "id": "BMENACE", "title": "Bio Menace (full game, freeware)", "year": 1993, "genre": "Platformer",
        "blurb": "Snake Logan against mutants, on the Keen engine. Apogee made all three episodes free.",
        "kind": "freeware", "file": "bmenace.zip",
        "index": {"mirrors": APOGEE[:1], "pattern": r"^(bmenace|biomenace|bio_?menace|1bio).*\.zip$"},
        "page": "3D Realms released Bio Menace as freeware in 2005 (search: Bio Menace freeware 3D Realms)",
        "match": [r"(bmenace|bio.?menace).*\.zip$"],
        "contains": ["BMENACE1.EXE", "BMENACE2.EXE", "BMENACE3.EXE", "*.SHR"],
        "exe": ["BMENACE1.EXE", "BMENACE2.EXE", "BMENACE3.EXE"], "installer": "INSTALL.EXE",
        "guide": "APOGEE.TXT",
    },
    {
        "id": "BLAKE", "title": "Blake Stone: Aliens of Gold (shareware)", "year": 1993, "genre": "First-person shooter",
        "blurb": "Wolf3D engine, sci-fi setting, friendly informants and an automap.",
        "kind": "shareware", "file": "1blake.zip",
        "index": {"mirrors": APOGEE[:1], "pattern": r"^(1blake|blake|bs.?aog|bstone|1bs).*\.zip$"},
        "page": "http://ftp.funet.fi/pub/msdos/games/apogee/ (the Blake Stone: Aliens of Gold shareware zip)",
        "match": [r"(blake|bs.?aog|bstone).*\.zip$"],
        "contains": ["*.BS1", "BS-AOG.EXE", "*.SHR"],
        "exe": ["BS-AOG.EXE"], "installer": "INSTALL.EXE",
        "guide": "APOGEE.TXT",
    },
    {
        "id": "RAPTOR", "title": "Raptor: Call of the Shadows (shareware)", "year": 1994, "genre": "Vertical shoot-'em-up",
        "blurb": "Mercenary jet, weapon shop, and the loudest explosions of 1994.",
        "kind": "shareware", "file": "1raptor.zip",
        "index": {"mirrors": APOGEE[:1], "pattern": r"^(1raptor|raptor|rap).*\.zip$"},
        "page": "http://ftp.funet.fi/pub/msdos/games/apogee/ (the Raptor shareware zip)",
        "match": [r"raptor.*\.zip$"],
        "contains": ["RAP.EXE", "FILE0000.GLB", "*.SHR"],
        "exe": ["RAP.EXE"], "setup": "SETUP.EXE", "installer": "INSTALL.EXE",
        "guide": "APOGEE.TXT",
    },
    {
        "id": "SODEMO", "title": "Spear of Destiny (demo)", "year": 1992, "genre": "First-person shooter",
        "blurb": "Wolf3D's prequel: the first floors of the hunt for the Spear.",
        "kind": "shareware", "file": "sodemo.zip", "size": 702564, "md5": "e103c21eeea20329db10a9cb8f4db1db",
        "urls": [GDP + "spear-of-destiny/sodemo.zip"],
        "unpack": ["SODEMO.EXE"],
        "contains": ["SODEMO.EXE", "VSWAP.SDM"],
        "exe": ["SPEAR.EXE", "SOD.EXE"], "installer": "SODEMO.EXE",
        "guide": "WOLF3D.TXT",
    },
    {
        "id": "JAZZ", "title": "Jazz Jackrabbit: Holiday Hare '95", "year": 1995, "genre": "Platformer",
        "blurb": "Epic's speedy green rabbit in a free holiday special.",
        "kind": "freeware", "file": "jjxmas95.zip", "size": 1440508, "md5": "adbdf6d65ba4060fc3ff28a3355608e1",
        "urls": ["https://image.dosgamesarchive.com/games/jjxmas95.zip"],
        "contains": ["JAZZ.EXE", "FILE0001.EXE"],
        "exe": ["JAZZ.EXE"], "setup": "SETUP.EXE", "installer": "FILE0001.EXE",
        "guide": "DEMOS.TXT",
    },
    {
        "id": "THEMEHOS", "title": "Theme Hospital (demo)", "year": 1997, "genre": "Management",
        "blurb": "Bullfrog's hospital sim: one level of Bloaty Head and Slack Tongue.",
        "kind": "demo", "file": "Demo.zip", "size": 12878920, "md5": "d62f3be55a625b99b6a655e37bdb5df7",
        "urls": ["http://th.corsix.org/Demo.zip"],
        "contains": ["HOSPITAL.EXE"],
        "exe": ["HOSPITAL.EXE", "HOSPITAL.BAT"], "setup": "SETUP.EXE",
        "guide": "DEMOS.TXT",
    },
    {
        "id": "HEROES2", "title": "Heroes of Might and Magic II (demo)", "year": 1996, "genre": "Turn-based strategy",
        "blurb": "One scenario of the best Heroes. Dangerously addictive.",
        "kind": "demo", "file": "h2demo.zip", "size": 21848903, "md5": "2a67d3b21b4dbdb2694720b8e75eed99",
        "urls": ["https://archive.org/download/HeroesofMightandMagicIITheSuccessionWars_1020/h2demo.zip"],
        "contains": ["HEROES2.AGG", "BROKENA.MP2"],
        "exe": ["HEROES2.EXE", "HEROES2W.EXE"],
        "guide": "DEMOS.TXT",
    },
    {
        "id": "TYRIAN", "title": "Tyrian 2000", "year": 1999, "genre": "Vertical shoot-'em-up",
        "blurb": "The best DOS shmup: all five episodes, released as freeware by its authors.",
        "kind": "freeware",
        "sources": [
            {"file": "tyrian2000.zip", "size": None, "md5": None, "urls": ["https://camanis.net/tyrian/tyrian2000.zip"]},
            # Tyrian 2.1, the earlier freeware release (4 episodes), as Debian checks it
            {"file": "tyrian21.zip", "size": 4754048, "md5": "2a3b206a6de25ed4b771af073f8ca904",
             "urls": ["http://www.camanis.net/tyrian/tyrian21.zip"]},
        ],
        "page": "https://camanis.net/tyrian/ (the Tyrian 2000 freeware zip, also mirrored by OpenTyrian)",
        "match": [r"tyrian.*2000.*\.zip$", r"^tyrian2?1?\.zip$"],
        "contains": ["TYRIAN.HDT"],
        "exe": "TYRIAN.EXE", "setup": "SETUP.EXE",
        "guide": "TYRIAN.TXT",
    },
    {
        "id": "OMF", "title": "One Must Fall: 2097", "year": 1994, "genre": "Fighting",
        "blurb": "Giant robots, pilot upgrades and a tournament career. Freeware since 1999.",
        "kind": "freeware", "manual": True, "file": "omf2097.zip",
        "page": "https://www.omf2097.com/ (Downloads: the original freeware DOS version)",
        "match": [r"omf.*\.zip$"],
        "contains": ["FILE0001.EXE", "OMF.EXE", "SETUP.EXE"],
        "exe": ["OMF.BAT", "OMF.EXE", "FILE0001.EXE"], "setup": "SETUP.EXE",
        "guide": "OMF.TXT",
    },
    {
        "id": "ARENA", "title": "The Elder Scrolls: Arena", "year": 1994, "genre": "Role-playing",
        "blurb": "Where the Elder Scrolls began: all of Tamriel, the Staff of Chaos. Freeware since 2004.",
        "kind": "freeware", "manual": True, "file": "Arena106Setup.zip",
        "page": "https://en.uesp.net/wiki/Arena:Arena (UESP links the free Bethesda release)",
        "match": [r"arena.*\.zip$"],
        "contains": ["A.EXE", "ACD.EXE", "GLOBAL.BSA"],
        "exe": ["ARENA.BAT", "ACD.EXE", "A.EXE"],
        "installer": "INSTALL.EXE",
        "guide": "ARENA.TXT",
    },
    {
        "id": "DAGGER", "title": "The Elder Scrolls II: Daggerfall", "year": 1996, "genre": "Role-playing",
        "blurb": "A world the size of Britain and a class builder still unmatched. Freeware since 2009.",
        "kind": "freeware", "manual": True, "file": "DFInstall.zip",
        "page": "https://en.uesp.net/wiki/Daggerfall:Daggerfall (UESP links the free Bethesda release)",
        "match": [r"^df.*install.*\.zip$", r"dagger.*\.zip$"],
        "contains": ["DAGGER.EXE", "FALL.EXE", "INSTALL.EXE"],
        "exe": "DAGGER.EXE", "setup": "SETUP.EXE", "installer": "INSTALL.EXE",
        "notes": "The freeware zip holds the CD contents: the first run installs it (choose C:\\DAGGER).",
        "guide": "DAGGER.TXT",
    },
    {
        "id": "CNC", "title": "Command & Conquer (GDI and Nod discs)", "year": 1995, "genre": "Real-time strategy",
        "blurb": "The RTS that set the rules: tiberium, harvesters, the Obelisk. Freeware since 2007.",
        "kind": "freeware", "manual": True, "file": "(the GDI or Nod ISO, or a zip of it)",
        "page": "EA's 2007 freeware release (search: Command & Conquer Gold freeware DOS ISO)",
        "match": [r"(gdi|nod|cnc|c&c|command.*conquer).*\.(iso|zip)$"],
        "contains": ["C&C.EXE", "CONQUER.MIX", "INSTALL.EXE"],
        "exe": "C&C.EXE", "setup": "SETUP.EXE", "installer": "INSTALL.EXE", "cd": True,
        "notes": "The first run mounts the disc as E: and runs its installer. Install into C:\\CNC.",
        "guide": "CNC.TXT",
    },
    {
        "id": "REDALERT", "title": "Command & Conquer: Red Alert (Allied and Soviet discs)", "year": 1996, "genre": "Real-time strategy",
        "blurb": "Tesla coils, Tanya, chronospheres. Freeware since 2008.",
        "kind": "freeware", "manual": True, "file": "(the Allied or Soviet ISO, or a zip of it)",
        "page": "EA's 2008 freeware release (search: Red Alert freeware DOS ISO)",
        "match": [r"(allied|soviet|redalert|red.?alert|ra).*\.(iso|zip)$"],
        "contains": ["RA.EXE", "MAIN.MIX", "SETUP.EXE"],
        "exe": "RA.EXE", "setup": "SETUP.EXE", "installer": "INSTALL.EXE", "cd": True,
        "notes": "The first run mounts the disc as E: and runs its installer. Install into C:\\REDALERT.",
        "guide": "REDALERT.TXT",
    },
]

# Great DOS games that are still sold: for mygames (guides/BUYLIST.TXT lists them).
BY_ID = {g["id"]: g for g in GAMES}

DOSBOX_REPO = "dosbox-staging/dosbox-staging"
DOSBOX_PAGE = "https://www.dosbox-staging.org/releases/"
