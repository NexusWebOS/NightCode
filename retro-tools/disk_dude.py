from __future__ import annotations

import ctypes
from functools import partial
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import urllib.parse
import urllib.request

from PIL import Image, ImageTk
from core import MEDIA_SUFFIXES, copy_disc, optical_drives, run_gh_upload, safe_source, scan, zip_folder
from retro_skin import BG, PANEL, ACCENT, TEXT, MUTED, RetroButton, RetroHeader, configure_style

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
ASSETS = BASE / 'assets'
DiskButton = partial(RetroButton, asset_root=ASSETS, app_name='disk-dude')
APPDATA = Path(os.getenv('LOCALAPPDATA', str(Path.home()))) / 'RetroTools'


def mci(command: str) -> str:
    buffer = ctypes.create_unicode_buffer(512)
    code = ctypes.windll.winmm.mciSendStringW(command, buffer, 512, 0)
    if code:
        error = ctypes.create_unicode_buffer(512)
        ctypes.windll.winmm.mciGetErrorStringW(code, error, 512)
        raise RuntimeError(error.value)
    return buffer.value


class DiskDude(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('DISK DUDE  |  Retro Tools')
        self.geometry('1120x760')
        self.minsize(920, 650)
        self.configure(bg=BG)
        self.events = queue.Queue()
        self.report = None
        self.source = None
        self.copied = None
        self.archive = None
        self.audio_open = False
        self.poll_job = None
        self._build()
        self.refresh_drives()
        self.poll_job = self.after(100, self.poll)
        self.protocol('WM_DELETE_WINDOW', self.close)

    def _build(self):
        configure_style(self)
        RetroHeader(self, ASSETS, 'disk-dude').pack(fill='x', padx=22, pady=(18, 3))
        self.status = tk.StringVar(value='Ready. Insert a disc, then scan.')
        tk.Label(self, textvariable=self.status, bg=BG, fg=MUTED,
                 anchor='w', font=('Consolas', 10)).pack(fill='x', padx=23)

        toolbar = tk.Frame(self, bg=BG)
        toolbar.pack(fill='x', padx=22, pady=8)
        self.drive = ttk.Combobox(toolbar, width=14, state='readonly')
        self.drive.pack(side='left')
        RetroButton(toolbar, text='Refresh drives', command=self.refresh_drives, asset_root=ASSETS, app_name='disk-dude').pack(side='left', padx=5)
        RetroButton(toolbar, text='Scan disc', command=self.scan_drive, asset_root=ASSETS, app_name='disk-dude').pack(side='left', padx=5)
        RetroButton(toolbar, text='Preview folder…', command=self.scan_folder, asset_root=ASSETS, app_name='disk-dude').pack(side='left', padx=5)
        RetroButton(toolbar, text='Open in Explorer', command=self.open_source, asset_root=ASSETS, app_name='disk-dude').pack(side='right')

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill='both', expand=True, padx=22, pady=10)
        self.disc_tab = ttk.Frame(self.tabs)
        self.archive_tab = ttk.Frame(self.tabs)
        self.player_tab = ttk.Frame(self.tabs)
        self.cloud_tab = ttk.Frame(self.tabs)
        for frame, name in [(self.disc_tab, 'DISC'), (self.archive_tab, 'RIP / BURN'),
                            (self.player_tab, 'PLAYER'), (self.cloud_tab, 'GITHUB / SUPABASE')]:
            self.tabs.add(frame, text=name)
        self._disc_ui()
        self._archive_ui()
        self._player_ui()
        self._cloud_ui()

    def _disc_ui(self):
        top = ttk.Frame(self.disc_tab)
        top.pack(fill='x', pady=12)
        self.disc_title = tk.StringVar(value='NO DISC SCANNED')
        self.disc_meta = tk.StringVar(value='Insert a disc or preview a folder.')
        ttk.Label(top, textvariable=self.disc_title, font=('Consolas', 19, 'bold')).pack(anchor='w')
        ttk.Label(top, textvariable=self.disc_meta, wraplength=950).pack(anchor='w', pady=5)
        body = tk.Frame(self.disc_tab, bg=BG)
        body.pack(fill='both', expand=True)
        preview = tk.Frame(body, bg=PANEL, width=210)
        preview.pack(side='left', fill='y', padx=(0, 10))
        preview.pack_propagate(False)
        self.cover_label = tk.Label(preview, bg=PANEL)
        self.cover_label.pack(padx=12, pady=12)
        self.cover_photo = ImageTk.PhotoImage(Image.open(BASE / 'assets' / 'disc-icon.png').resize((180, 180), Image.Resampling.NEAREST))
        self.cover_label.configure(image=self.cover_photo)
        tk.Label(preview, text='DISC ART / MEDIA', bg=PANEL, fg=MUTED, font=('Consolas', 9)).pack()
        self.file_list = tk.Listbox(body, bg=PANEL, fg=TEXT, selectbackground='#235d75',
                                    font=('Consolas', 10), border=0)
        self.file_list.pack(side='left', fill='both', expand=True)
        scroll = ttk.Scrollbar(body, command=self.file_list.yview)
        scroll.pack(side='right', fill='y')
        self.file_list.configure(yscrollcommand=scroll.set)
        self.file_list.bind('<Double-Button-1>', lambda _: self.open_selected())
        DiskButton(self.disc_tab, text='Open selected file', command=self.open_selected).pack(anchor='e', pady=8)

    def _archive_ui(self):
        frame = ttk.Frame(self.archive_tab)
        frame.pack(fill='both', expand=True, padx=14, pady=18)
        ttk.Label(frame, text='MAKE A VERIFIED DATA COPY', font=('Consolas', 17, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Copies readable files to a folder and writes a SHA-256 manifest. Audio CD tracks and hidden/raw sectors require a specialist ripper.', wraplength=820).pack(anchor='w', pady=10)
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=8)
        DiskButton(row, text='Copy disc to folder…', command=self.copy).pack(side='left')
        DiskButton(row, text='Copy & ZIP…', command=self.copy_zip).pack(side='left', padx=8)
        DiskButton(row, text='ZIP copied folder…', command=self.zip_existing).pack(side='left')
        ttk.Separator(frame).pack(fill='x', pady=20)
        ttk.Label(frame, text='BURN A DATA DISC', font=('Consolas', 17, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Stage the files in a local folder, then burn to a blank CD-R/CD-RW with Windows IMAPI2. This is data-disc authoring only.', wraplength=820).pack(anchor='w', pady=10)
        row2 = ttk.Frame(frame)
        row2.pack(fill='x', pady=8)
        DiskButton(row2, text='Choose burn folder…', command=self.choose_burn_folder).pack(side='left')
        self.burn_folder = tk.StringVar(value='No burn folder selected')
        ttk.Label(row2, textvariable=self.burn_folder, wraplength=560).pack(side='left', padx=12)
        DiskButton(frame, text='Burn to selected optical drive…', command=self.burn).pack(anchor='w', pady=14)

    def _player_ui(self):
        frame = ttk.Frame(self.player_tab)
        frame.pack(fill='both', expand=True, padx=14, pady=18)
        ttk.Label(frame, text='PLAY / EMULATE', font=('Consolas', 17, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Double-click a listed audio or video file to open the Windows default player. An inserted Audio CD can be controlled below.', wraplength=820).pack(anchor='w', pady=10)
        row = ttk.Frame(frame)
        row.pack(anchor='w', pady=10)
        for label, method in [('Play Audio CD', self.play_cd), ('Pause', self.pause_cd), ('Stop', self.stop_cd)]:
            DiskButton(row, text=label, command=method).pack(side='left', padx=(0, 8))
        ttk.Separator(frame).pack(fill='x', pady=20)
        ttk.Label(frame, text='EMULATOR PATH (OPTIONAL)', font=('Consolas', 14, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Select an emulator executable and launch it with the current drive path. Emulators differ in command-line support.', wraplength=820).pack(anchor='w', pady=8)
        self.emulator = tk.StringVar()
        ttk.Entry(frame, textvariable=self.emulator, width=75).pack(anchor='w', pady=5)
        DiskButton(frame, text='Browse emulator…', command=self.browse_emulator).pack(anchor='w', pady=5)
        DiskButton(frame, text='Launch emulator with disc path', command=self.launch_emulator).pack(anchor='w', pady=10)

    def _cloud_ui(self):
        frame = ttk.Frame(self.cloud_tab)
        frame.pack(fill='both', expand=True, padx=14, pady=18)
        ttk.Label(frame, text='EXPLICIT CLOUD TRANSFERS', font=('Consolas', 17, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Uploads use the ZIP archive you made. Review its contents before sharing. No automatic sync.', wraplength=840).pack(anchor='w', pady=7)
        self.cloud_file = tk.StringVar(value='No ZIP selected')
        ttk.Label(frame, textvariable=self.cloud_file, wraplength=850).pack(anchor='w', pady=5)
        DiskButton(frame, text='Select ZIP…', command=self.choose_zip).pack(anchor='w')
        ttk.Separator(frame).pack(fill='x', pady=14)
        self.repo = tk.StringVar()
        self.tag = tk.StringVar()
        self._entry(frame, 'GitHub repository (owner/name)', self.repo)
        self._entry(frame, 'Existing release tag', self.tag)
        row = ttk.Frame(frame); row.pack(anchor='w', pady=7)
        DiskButton(row, text='Upload ZIP to release', command=self.github_upload).pack(side='left')
        DiskButton(row, text='Download release asset…', command=self.github_download).pack(side='left', padx=8)
        ttk.Separator(frame).pack(fill='x', pady=14)
        self.supa_url, self.supa_bucket, self.supa_token = tk.StringVar(), tk.StringVar(), tk.StringVar()
        self._entry(frame, 'Supabase project URL', self.supa_url)
        self._entry(frame, 'Storage bucket', self.supa_bucket)
        self._entry(frame, 'Your access token (not saved)', self.supa_token, show='•')
        DiskButton(frame, text='Upload ZIP to Supabase Storage', command=self.supabase_upload).pack(anchor='w', pady=8)

    def _entry(self, parent, label, variable, show=None):
        line = ttk.Frame(parent); line.pack(fill='x', pady=3)
        ttk.Label(line, text=label, width=36).pack(side='left')
        ttk.Entry(line, textvariable=variable, width=65, show=show or '').pack(side='left')

    def task(self, label, callback):
        self.status.set(label)
        def work():
            try:
                value = callback()
                self.events.put(('done', value))
            except Exception as exc:
                self.events.put(('error', str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'error':
                    self.status.set('Operation failed')
                    messagebox.showerror('Disk Dude', value)
                elif kind == 'scan':
                    self.report = value
                    self.source = Path(value['root'])
                    self.disc_title.set(f"{value['label']}  //  {value['kind']}")
                    self.disc_meta.set(f"{value['reason']}  •  {value['count']} files  •  {value['bytes'] / 1048576:,.1f} MiB")
                    self.file_list.delete(0, 'end')
                    for file in value['files']:
                        self.file_list.insert('end', file)
                    self.update_cover()
                    self.status.set('Scan complete')
                elif kind == 'done':
                    if isinstance(value, tuple) and value[0] == 'archive':
                        self.cloud_file.set(value[2])
                        self.status.set(value[1])
                    else:
                        self.status.set(str(value))
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.poll_job = self.after(100, self.poll)

    def update_cover(self):
        if not self.source or not self.report: return
        names = ('cover.jpg', 'cover.jpeg', 'cover.png', 'folder.jpg', 'folder.png', 'albumart.jpg')
        match = next((p for p in self.report['files'] if Path(p).name.lower() in names), None)
        try:
            picture = Image.open(safe_source(self.source, match)).convert('RGBA') if match else Image.open(BASE / 'assets' / 'disc-icon.png').convert('RGBA')
            picture.thumbnail((180, 240), Image.Resampling.NEAREST if not match else Image.Resampling.LANCZOS)
            self.cover_photo = ImageTk.PhotoImage(picture)
            self.cover_label.configure(image=self.cover_photo)
        except Exception:
            pass

    def refresh_drives(self):
        drives = optical_drives()
        self.drive['values'] = drives
        if drives:
            self.drive.set(drives[0])
            self.status.set(f'{len(drives)} optical drive(s) found')
        else:
            self.status.set('No optical drive found. You can preview a folder.')

    def scan_drive(self):
        if not self.drive.get():
            return messagebox.showinfo('Disk Dude', 'Select an optical drive first.')
        root = Path(self.drive.get())
        self.status.set('Scanning disc…')
        def work():
            try:
                self.events.put(('scan', scan(root)))
            except Exception as original:
                try:
                    mci(f'open {self.drive.get()[:2]} type cdaudio alias diskdude_probe')
                    tracks = mci('status diskdude_probe number of tracks')
                    mci('close diskdude_probe')
                    self.events.put(('scan', {'root': str(root), 'label': 'AUDIO CD', 'kind': 'Audio CD',
                        'reason': f'{tracks} audio tracks detected', 'count': int(tracks), 'bytes': 0, 'files': []}))
                except Exception:
                    self.events.put(('error', str(original)))
        threading.Thread(target=work, daemon=True).start()

    def scan_folder(self):
        folder = filedialog.askdirectory(title='Preview a local folder')
        if folder:
            self._scan(Path(folder))

    def _scan(self, root):
        self.status.set('Scanning…')
        def work():
            try: self.events.put(('scan', scan(root)))
            except Exception as exc: self.events.put(('error', str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def open_selected(self):
        if not self.source or not self.file_list.curselection(): return
        try:
            path = safe_source(self.source, self.file_list.get(self.file_list.curselection()[0]))
            os.startfile(path)
        except Exception as exc: messagebox.showerror('Open file', str(exc))

    def open_source(self):
        if self.source: os.startfile(self.source)

    def _copy_to(self, destination, make_zip=False):
        if not self.source: return
        if self.report and self.report['kind'] == 'Audio CD':
            return messagebox.showinfo('Audio CD', 'Audio CD track ripping needs a dedicated audio ripper. Disk Dude copies readable data files.')
        self.copied = Path(destination)
        def work():
            manifest = copy_disc(self.source, self.copied)
            if make_zip:
                self.archive = self.copied.with_suffix('.zip')
                zip_folder(self.copied, self.archive)
                return ('archive', f'Copied and ZIP created: {self.archive}', str(self.archive))
            return f'Copy complete: {manifest}'
        self.task('Copying readable files…', work)

    def copy(self):
        if not self.source: return messagebox.showinfo('Disk Dude', 'Scan a disc or folder first.')
        path = filedialog.askdirectory(title='Choose an EMPTY destination folder')
        if path: self._copy_to(path)

    def copy_zip(self):
        if not self.source: return messagebox.showinfo('Disk Dude', 'Scan a disc or folder first.')
        path = filedialog.askdirectory(title='Choose an EMPTY destination folder')
        if path: self._copy_to(path, True)

    def zip_existing(self):
        folder_name = str(self.copied) if self.copied else filedialog.askdirectory(title='Choose copied folder')
        if not folder_name: return
        folder = Path(folder_name)
        if not folder.is_dir(): return
        path = filedialog.asksaveasfilename(defaultextension='.zip', filetypes=[('ZIP archive', '*.zip')])
        if not path: return
        self.archive = Path(path)
        def work():
            zip_folder(folder, self.archive)
            return ('archive', f'ZIP created: {self.archive}', str(self.archive))
        self.task('Compressing…', work)

    def choose_burn_folder(self):
        folder = filedialog.askdirectory(title='Select staged files for data CD')
        if folder: self.burn_folder.set(folder)

    def burn(self):
        folder = Path(self.burn_folder.get())
        drive = self.drive.get()
        if not folder.is_dir() or not drive:
            return messagebox.showinfo('Burn', 'Choose a burn folder and optical drive.')
        if not messagebox.askyesno('Burn data disc', f'Burn files from {folder} to {drive}?\n\nA CD-R write is irreversible. Confirm the correct blank disc is inserted.'):
            return
        script = BASE / 'burn-data-disc.ps1'
        self.task('Burning data disc…', lambda: self._run_burn(script, folder, drive))

    def _run_burn(self, script, folder, drive):
        result = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script), '-Source', str(folder), '-Drive', drive[:2]], capture_output=True, text=True)
        if result.returncode: raise RuntimeError((result.stderr or result.stdout).strip())
        return result.stdout.strip() or 'Burn complete'

    def _open_audio(self):
        if self.audio_open: return
        drive = self.drive.get()
        if not drive: raise RuntimeError('Select an optical drive.')
        mci(f'open {drive[:2]} type cdaudio alias diskdude')
        self.audio_open = True

    def play_cd(self):
        try:
            self._open_audio(); mci('play diskdude'); self.status.set('Playing Audio CD')
        except Exception as exc: messagebox.showerror('Audio CD', str(exc))

    def pause_cd(self):
        try: mci('pause diskdude'); self.status.set('Paused')
        except Exception as exc: messagebox.showerror('Audio CD', str(exc))

    def stop_cd(self):
        if self.audio_open:
            try: mci('stop diskdude'); self.status.set('Stopped')
            except Exception as exc: messagebox.showerror('Audio CD', str(exc))

    def browse_emulator(self):
        path = filedialog.askopenfilename(filetypes=[('Programs', '*.exe')])
        if path: self.emulator.set(path)

    def launch_emulator(self):
        exe = Path(self.emulator.get())
        if not exe.is_file() or not self.source:
            return messagebox.showinfo('Emulator', 'Choose an emulator executable and scan a disc.')
        try: subprocess.Popen([str(exe), str(self.source)])
        except Exception as exc: messagebox.showerror('Emulator', str(exc))

    def choose_zip(self):
        path = filedialog.askopenfilename(filetypes=[('ZIP archive', '*.zip')])
        if path: self.archive = Path(path); self.cloud_file.set(path)

    def github_upload(self):
        if not self.archive or not self.repo.get() or not self.tag.get():
            return messagebox.showinfo('GitHub', 'Select a ZIP and enter repository and release tag.')
        if not messagebox.askyesno('Upload to GitHub', f'Upload {self.archive.name} to {self.repo.get()} release {self.tag.get()}?'):
            return
        self.task('Uploading to GitHub…', lambda: run_gh_upload(self.repo.get(), self.archive, self.tag.get()))

    def github_download(self):
        if not self.repo.get() or not self.tag.get():
            return messagebox.showinfo('GitHub', 'Enter repository and release tag.')
        folder = filedialog.askdirectory(title='Download release assets into folder')
        if not folder: return
        def work():
            cmd = ['gh', 'release', 'download', self.tag.get(), '--repo', self.repo.get(), '--dir', folder]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode: raise RuntimeError((result.stderr or result.stdout).strip())
            return f'Release assets downloaded to {folder}'
        self.task('Downloading from GitHub…', work)

    def supabase_upload(self):
        if not self.archive or not self.archive.is_file() or not all([self.supa_url.get(), self.supa_bucket.get(), self.supa_token.get()]):
            return messagebox.showinfo('Supabase', 'Select a ZIP and fill in project URL, bucket, and token.')
        url = self.supa_url.get().rstrip('/')
        if not url.startswith('https://'):
            return messagebox.showerror('Supabase', 'Use an HTTPS Supabase project URL.')
        if not messagebox.askyesno('Upload to Supabase', f'Upload {self.archive.name} to bucket {self.supa_bucket.get()}?'):
            return
        def work():
            object_path = '/'.join(urllib.parse.quote(part, safe='') for part in [self.supa_bucket.get(), self.archive.name])
            request = urllib.request.Request(f'{url}/storage/v1/object/{object_path}', data=self.archive.read_bytes(), method='POST', headers={
                'Authorization': 'Bearer ' + self.supa_token.get(), 'Content-Type': 'application/zip'})
            with urllib.request.urlopen(request, timeout=180) as response:
                response.read()
            return f'Uploaded {self.archive.name} to Supabase bucket {self.supa_bucket.get()}'
        self.task('Uploading to Supabase…', work)

    def close(self):
        if self.audio_open:
            try: mci('close diskdude')
            except Exception: pass
        self.destroy()

    def destroy(self):
        if self.poll_job is not None:
            try: self.after_cancel(self.poll_job)
            except tk.TclError: pass
            self.poll_job = None
        super().destroy()


if __name__ == '__main__':
    DiskDude().mainloop()
