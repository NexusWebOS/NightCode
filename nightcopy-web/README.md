# NightCopy v2 / ColeTech file console

Hosted edition of the NightCopy archive station, with a dark DOS-inspired shell,
two file panes, generated pixel-art branding and icons, a sequential transfer
queue, real progress, file previews, keyboard commands and responsive navigation.

## Run and build

```sh
npm ci
npm run dev
npm test
npm run build
python tests/browser_check.py
```

Netlify site: `nightcopy-coletech`. Custom domain: `nightcopy.coletechsystems.com`.
Deploy `dist/` with the supplied `netlify.toml`. The repository root contains the
earlier NightCode and NetCon tools; this app builds independently from this folder.

## Connections

`cloud-config.example.json` is a generic template. Copy it to
`public/runtime-config.json` and fill in your own public connection settings. The
deployment runtime file is git-ignored. The production project uses the ColeTech
Supabase connection and the requested archive account. No service-role key, OAuth
client secret, refresh token or Netlify credential ships in the app.

Apply `supabase/20260927_nightcopy.sql` in the project owner's SQL editor. The
private bucket scopes read/insert policies to the authenticated user's ID. Receipt
rows use the same user isolation. The script is transactional and may be rerun.
Then sign in using your Supabase email/password account.

Set a Google OAuth web client ID in Connections. Enable Drive API, configure the
consent audience, and allow the production/Netlify origins. Google tokens stay in
tab memory; the app confirms the authorized Google email before enabling Drive.
Supabase Google PKCE login is supported as an alternative if that provider has
been configured. The deployment does not automatically grant Google access.

The detailed setup is at `public/SETUP.html`, with a downloadable SQL script.

## Operations and limits

- Local staging accepts files, folder import and drag/drop. It is session memory.
- Desktop Chrome/Edge can mount a local writable folder with File System Access.
- Copy puts a selection on the app clipboard. Paste copies into the active pane;
  Transfer copies into the other pane. Duplicate copies in the same location.
- A review shows the source, items and destination before every transfer.
- Recursive folders and empty directories are included. Destination local/vault
  conflicts receive new names. Drive creates new objects. Sources remain in place.
- Drive server-side duplication supports native Docs. Downloads export supported
  Google-native documents. Shortcuts are rejected instead of followed.
- ZIP retains paths and adds a manifest. ZIP/buffer size limit: 256 MB. Supabase
  standard upload limit: 50 MB. Drive uses resumable sessions for direct file upload;
  byte progress is reported, but automatic session resumption is not implemented.
- Stop cooperatively cancels work. Finished files remain. Network failures can
  leave a completed or partial remote object; inspect before retrying.
- Directory enumeration: 10,000 entries, recursive depth: 48. Symlink traversal
  isn't available through mounted browser folder handles.
- No simulation, disk formatting, shell execution, or real account writes in tests.

## Shell

`help`, `dir`, `cd`, `use left|right`, `select "name"|*`, `copy`, `paste`,
`transfer`, `upload`, `xcopy`, `duplicate`, `download`, `zip`, `view`, `mkdir`,
`mount local|drive|supabase|staging`, `connect drive|vault`, `queue`, `stop`, `cls`, `ver`.
Arrow keys recall commands, Tab completes names, F3 previews, F5 copies and F6 transfers.

## Verification

Core tests check traversal rejection, quoted names, preservation of binary and
zero-byte files, conflict naming, aborted operations, buffer limits and Google
account rejection. Browser checks use disposable imported files and a mocked
local folder. They verify copy outputs, ZIP contents, preview, shell commands,
duplicate creation, navigation and overflow at 1440/1160/900/600/390 widths.
Cloud integration checks use mocked provider endpoints; production user sign-in
is required to validate actual Drive access and the provisioned private bucket.
