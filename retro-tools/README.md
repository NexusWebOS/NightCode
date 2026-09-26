# Retro Tools: Disk Dude + Netcon

Two local Windows desktop utilities in the NightCode family. Double-click `dist/DiskDude.exe` or `dist/Netcon.exe`. The `.ps1` launchers run from source and require Python 3.10+ and Pillow. No cloud account is needed to use local features. Rebuild the executables with `Build-Retro-Tools.ps1` (PyInstaller required).

## Disk Dude

- Detects optical drives and inserted data discs; identifies common PS1, PS2, Dreamcast, Xbox, DVD Video, VCD, music, and file layouts from visible files. It attempts a raw header check for Sega Saturn and Sega CD and labels those matches *possible*; some drives deny raw reads. Audio CDs are detected through Windows MCI.
- Shows a file list and embedded cover art when a disc contains `cover.jpg`, `cover.png`, `folder.jpg`, `folder.png`, or `albumart.jpg`. Otherwise it shows the disc icon. Opens selected files in the Windows default player. Audio CDs can play, pause, and stop through Windows MCI.
- Copies a data disc with path validation and a SHA-256 manifest, creates a ZIP of the copied files, and stages a folder for an optical burn.
- Burns a staged **data** folder to a blank CD-R/CD-RW using Windows IMAPI2. Burning is irreversible on CD-R. Read the confirmation dialog and select the correct drive. Disc images and audio tracks are not authored by this build.
- Opens installed emulator applications with a selected game disc path when configured. Emulator compatibility depends on the emulator and a lawful BIOS/firmware setup; no emulator is bundled.
- GitHub upload uses your installed `gh` login and a repository you enter. Supabase upload uses a project URL, bucket, and your own access token. Uploads are explicit actions and never happen during a scan.

## Netcon

- Creates three badge layouts: a blue/cyan 16-bit NightCode ID with a pixel skull mark, an Allied Universal staff card modeled on the supplied white/blue landscape badge, and visibly nonvalid **DEMO STATE / SPECIMEN** design studies. The staff layout takes a cardholder photo, name, title, height, weight, eye color, date of hire, department, site, and employee ID. It saves local records and exports 300 DPI CR80-sized PNG or PDF files; no badge printer is required.
- The Allied Universal layout uses the logo from the [official Allied Universal newsroom resource library](https://ausnewsroom.aus.com/resources/9xno8-dpke5-f75db-7y3vs-7jsed). Employer/site approval is still required for issuance or access activation. Netcon does not encode RFID credentials or grant door access.
- Keeps an inventory of RFID/NFC tag identifiers that you enter yourself; does not read, clone, jam, or emulate credentials.
- Records lock hardware, damage, and maintenance notes, with a simple 3D cylinder illustration for documentation. It does not produce picking or bypass instructions.
- Keeps a personal game ownership and compatibility catalog. It does not generate CD keys or remove copy protection.

Both apps store preferences in `%LOCALAPPDATA%\RetroTools`. Do not put secrets into GitHub repositories or ZIP archives. Use only media and systems you own or are authorized to manage.

## Artwork

The mascots, Genesis-era character portraits, Disk Dude branding, and disc/badge/folder/lock/game icons are SpriteCook exports in `assets/spritecook/`. The Netcon emblem and wide marquee are the user-supplied images in `assets/user-provided/`; they drive Netcon's window icon and live header. `make_assets.py` installs the approved files into `assets/`, makes Windows icons, and updates `spritecook-assets.json` with source IDs and hashes. Running it again preserves the supplied Netcon branding.

Disk Dude uses its dark SpriteCook banner, logo, portrait, and extracted button frame. Netcon uses the supplied chrome and neon branding with matching tabs, panels, footer, portrait, and generated controls. Text and interactive controls remain native for legibility. The `*-ui-concept.png` files are visual design references, not screenshots of currently implemented features. The complete extracted UI sheets are included for further expansion of the apps.
