# NightCode desktop

NightCode is a Windows desktop file workstation with a DOS-style command shell, a file preview window, and a live embedded internet browser. The browser uses Qt WebEngine, so typed addresses open inside NightCode and web page downloads use a Save dialog.

The `assets/nightcode-marquee-gpt-v2.png` header is GPT-generated 16-bit pixel artwork. NightCode paints its live title and status over that art. `previews/nightcode-banner-runtime.png` shows the header as it appears in the app.

## Run

Install Python 3.10+ and `pip install -r requirements.txt`, then run `Launch-NightCode.ps1` or `py -3 nightcode.py`. To make a Windows folder build, install PyInstaller and run `Build-NightCode.ps1`; launch `dist/NightCode/NightCode.exe`. Keep the built folder together because Qt WebEngine has runtime files.

## File and network tools

- Select files or folders and use **COPY TO** or **DUPLICATE**. Name collisions receive `copy`, `copy 2`, etc. Copying a folder into itself is rejected.
- Select a file to preview images, UTF-8 text, or the first 4 KiB as hex. Large text previews stop at 256 KiB.
- **DOWNLOAD URL** saves an HTTP(S) response into a chosen folder. The browser's own downloads also prompt for a destination.
- **GITHUB ↑** uploads a selected file through GitHub's repository Contents API. Supply `OWNER/REPO`, a repository path, and a token with Contents write permission. The current integration caps uploads at 25 MiB; use a GitHub Release for larger files.
- **GITHUB ↓** downloads a repository file through GitHub's Contents API. Public files need no token; private files need a token with Contents read permission.
- **SUPABASE ↑** uploads a selected file to an existing Storage bucket. Supply the HTTPS project root, bucket, object path, project API key, and a user access token authorized by the bucket's Storage policy. Existing objects are not overwritten.
- Tokens are used for one action and are not stored in NightCode settings or command history.

The shell accepts `HELP`, `DIR`, `CD`, `COPY`, `DUP`, `VIEW`, `WEB`, `DOWNLOAD`, and `CLS`. Quote paths containing spaces. The app is a local workstation; remote transfers need an internet connection and authorized accounts or endpoints.
