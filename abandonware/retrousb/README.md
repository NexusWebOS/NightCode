# Retro USB

Fills a USB stick with:

- DOSBox Staging, portable;
- DOS classics that are free to copy;
- your own DOS games;
- strategy guides.

The stick then plays on any Windows PC, with nothing to install.

```
Build-RetroUSB.cmd --download-only  just download everything to Downloads\RetroUSB
Build-RetroUSB.cmd                  pick the stick from a list
Build-RetroUSB.cmd --target D:\     fill drive D:
Build-RetroUSB.cmd --list           what's in the catalog
Build-RetroUSB.cmd --games DOOM,QUAKE,TYRIAN --target D:\
```

It needs Python 3.8 or newer and nothing else.

## What goes on the stick

- **Downloaded automatically**, and checked by MD5 or by the files inside:
  - the shareware episodes of DOOM, Wolfenstein 3D, Heretic, Hexen (demo), Quake, Rise of the Triad, Duke Nukem 3D and Shadow Warrior;
  - Apogee's shareware: Duke Nukem 1 and 2, Commander Keen 1 and 4, Cosmo, Blake Stone, Raptor, and the freeware Bio Menace. Games without a known file name are found by scanning the Apogee mirror's file list;
  - the Spear of Destiny, Theme Hospital and Heroes of Might and Magic II demos, and Jazz Jackrabbit: Holiday Hare '95;
  - Tyrian 2000, released as freeware (Tyrian 2.1 as the fallback);
  - Freedoom Phase 1 and 2 (BSD licence), played natively on Windows with the Crispy Doom port; both come from their GitHub releases;
  - DOSBox Staging, the latest Windows build from its GitHub releases.
- **Freeware you download once yourself**, because their official pages have moved over the years:
  - One Must Fall 2097
  - The Elder Scrolls: Arena and Daggerfall
  - Command & Conquer and Red Alert

  `--open-pages` opens those pages in your browser. Save the file into `retrousb\downloads` and run the builder again; it recognises the file by its name or by what's inside.
- **Your own games:** put each game in its own folder in `retrousb\mygames`, then run the builder again.
  - GOG folders work as they are, because their DOSBox settings are read.
  - For any other game, add a `PLAY.TXT` with the DOS commands that start it.
- **Guides:** original strategy guides for every catalog game, plus a DOSBox survival guide and `BUYLIST.TXT`, a list of the best commercial DOS games that are still sold, cheaply, on GOG and Steam. On the stick they are plain text in `GUIDES\`, readable inside DOSBox as drive D:, with `GUIDES\INDEX.HTM` for a browser.

`--download-only` only saves the zips and ISOs (and DOSBox) into a folder, `Downloads\RetroUSB` by default, and writes a `DOWNLOADS.TXT` listing what was fetched and what to get by hand. Build the stick from that folder later with `--downloads "<folder>"`; nothing is downloaded twice.

Games still owned by someone are not in the catalog, however "abandoned" they look. Buy them and use `mygames`.

## How the stick is laid out

- `START-HERE.bat` is the game picker. `start-here.sh` does the same on Linux, using DOSBox from the stick or the system.
- `DOSBOX\WIN` holds DOSBox. `DOSBOX\RETRO.CONF` has the shared settings, and each game has its own `DOSBOX\CONF\<ID>.CONF`.
- `GAMES\` is drive C: inside DOSBox. `MENU.BAT` there is a DOS menu with `S` for each game's setup.
- `GAMES\_SETUP\<ID>` holds the original installer files. Some shareware uses DOS compressors this builder can't unpack, so the game's own installer runs the first time you start it.
- `GUIDES\`
- `README.TXT` and `RETROUSB.TXT` list what's installed. A second run keeps what's already on the stick.

Every file is read back after it's written, which catches fake-capacity sticks. Nothing outside these names is touched, and nothing is formatted.

## Tests

`python -m unittest retrousb.tests.test_retrousb`

The tests use fake downloads and a folder standing in for the stick. One of them builds a real LHA self-extractor with `lha` when it's installed.
