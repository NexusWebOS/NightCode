# Retro Tools: Disk Dude + Netcon

Two local Windows desktop utilities in the NightCode family. Download the Windows executables from the repository's releases when available, or use the `.ps1` launchers from source with Python 3.10+ and Pillow. No cloud account is needed to use local features. Rebuild the executables with `Build-Retro-Tools.ps1` (PyInstaller required).

## Disk Dude

- Detects optical drives and inserted data discs; identifies common PS1, PS2, Dreamcast, Xbox, DVD Video, VCD, music, and file layouts from visible files. It attempts a raw header check for Sega Saturn and Sega CD and labels those matches *possible*; some drives deny raw reads. Audio CDs are detected through Windows MCI.
- Shows a file list and embedded cover art when a disc contains `cover.jpg`, `cover.png`, `folder.jpg`, `folder.png`, or `albumart.jpg`. Otherwise it shows the disc icon. Opens selected files in the Windows default player. Audio CDs can play, pause, and stop through Windows MCI.
- Copies a data disc with path validation and a SHA-256 manifest, creates a ZIP of the copied files, and stages a folder for an optical burn.
- Burns a staged **data** folder to a blank CD-R/CD-RW using Windows IMAPI2. Burning is irreversible on CD-R. Read the confirmation dialog and select the correct drive. Disc images and audio tracks are not authored by this build.
- Opens installed emulator applications with a selected game disc path when configured. Emulator compatibility depends on the emulator and a lawful BIOS/firmware setup; no emulator is bundled.
- GitHub upload uses your installed `gh` login and a repository you enter. Supabase upload uses a project URL, bucket, and your own access token. Uploads are explicit actions and never happen during a scan.

## Netcon

- Makes printable, clearly marked **sample** ID badges for local design and event use.
- Keeps an inventory of RFID/NFC tag identifiers that you enter yourself; does not read, clone, jam, or emulate credentials.
- Records lock hardware, damage, and maintenance notes, with a simple 3D cylinder illustration for documentation. It does not produce picking or bypass instructions.
- Keeps a personal game ownership and compatibility catalog. It does not generate CD keys or remove copy protection.

Both apps store preferences in `%LOCALAPPDATA%\RetroTools`. Do not put secrets into GitHub repositories or ZIP archives. Use only media and systems you own or are authorized to manage.

## Artwork

The two mascot PNGs in `assets/` were generated with the built-in image generation tool from these prompts:

- Disk Dude: 16-bit transparent pixel-art friendly hacker holding a CD-R in a jewel case; navy, teal, cyan, violet palette.
- Netcon: 16-bit transparent pixel-art friendly tech specialist holding a blank badge and diagnostic circuit board; matching palette.

The logo PNGs, banners, disc, badge, folder, lock, and game icons in `assets/` are built with `make_assets.py`. UI labels remain code-rendered so they stay sharp.
