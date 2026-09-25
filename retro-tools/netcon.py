from __future__ import annotations

import json
from functools import partial
import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
from retro_skin import BG, PANEL, ACCENT, TEXT, MUTED, RetroButton, RetroHeader, configure_style

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
ASSETS = BASE / 'assets'
NetButton = partial(RetroButton, asset_root=ASSETS, app_name='netcon')
DATA = Path(os.getenv('LOCALAPPDATA', str(Path.home()))) / 'RetroTools' / 'netcon.json'


def load_data():
    try: return json.loads(DATA.read_text(encoding='utf-8'))
    except (OSError, ValueError): return {'tags': [], 'locks': [], 'games': []}


def save_data(data):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(data, indent=2), encoding='utf-8')


class Netcon(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('NETCON  |  Retro Tools')
        self.geometry('1100x750')
        self.minsize(900, 640)
        self.configure(bg=BG)
        self.data = load_data()
        self._style()
        self._build()

    def _style(self):
        configure_style(self)

    def _build(self):
        RetroHeader(self, ASSETS, 'netcon').pack(fill='x', padx=22, pady=(18, 10))
        self.tabs = ttk.Notebook(self); self.tabs.pack(fill='both', expand=True, padx=22, pady=10)
        self.badge, self.tags, self.locks, self.games = [ttk.Frame(self.tabs) for _ in range(4)]
        for frame, label in [(self.badge, 'BADGE MAKER'), (self.tags, 'RFID INVENTORY'),
                             (self.locks, 'LOCK SERVICE'), (self.games, 'GAME LIBRARY')]:
            self.tabs.add(frame, text=label)
        self._badge_ui(); self._tags_ui(); self._locks_ui(); self._games_ui()

    def field(self, parent, label, var, width=58):
        row = ttk.Frame(parent); row.pack(anchor='w', fill='x', pady=5)
        ttk.Label(row, text=label, width=28).pack(side='left')
        ttk.Entry(row, textvariable=var, width=width).pack(side='left')

    def _badge_ui(self):
        frame = ttk.Frame(self.badge); frame.pack(fill='both', expand=True, padx=16, pady=20)
        ttk.Label(frame, text='DESIGN A SAMPLE ID BADGE', font=('Consolas', 17, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Exports a printable PNG with a visible SAMPLE mark. Use only for a system you administer.', wraplength=800).pack(anchor='w', pady=8)
        self.badge_name, self.badge_role, self.badge_org, self.badge_id = [tk.StringVar() for _ in range(4)]
        for label, var in [('Name', self.badge_name), ('Role', self.badge_role), ('Organization', self.badge_org), ('ID / number', self.badge_id)]:
            self.field(frame, label, var)
        NetButton(frame, text='Export sample badge PNG…', command=self.export_badge).pack(anchor='w', pady=16)
        self.badge_preview = tk.Canvas(frame, width=550, height=220, bg=PANEL, highlightthickness=0)
        self.badge_preview.pack(anchor='w')
        for var in [self.badge_name, self.badge_role, self.badge_org, self.badge_id]:
            var.trace_add('write', lambda *_: self.draw_badge())
        self.draw_badge()

    def draw_badge(self):
        c = self.badge_preview; c.delete('all')
        c.create_rectangle(14, 14, 536, 206, fill='#132633', outline=ACCENT, width=3)
        c.create_rectangle(19, 19, 531, 58, fill='#09151f', outline='')
        c.create_rectangle(24, 67, 30, 193, fill='#9966a2', outline='')
        c.create_text(38, 38, text=(self.badge_org.get() or 'ORGANIZATION')[:26], anchor='w', fill=ACCENT, font=('Consolas', 17, 'bold'))
        c.create_text(44, 95, text=(self.badge_name.get() or 'YOUR NAME')[:30], anchor='w', fill=TEXT, font=('Consolas', 20, 'bold'))
        c.create_text(44, 132, text=(self.badge_role.get() or 'ROLE')[:36], anchor='w', fill=MUTED, font=('Consolas', 13))
        c.create_text(44, 176, text='ID: ' + (self.badge_id.get() or '0000')[:28], anchor='w', fill=ACCENT, font=('Consolas', 12))
        c.create_text(440, 160, text='SAMPLE', fill='#d86d75', font=('Consolas', 17, 'bold'))

    def export_badge(self):
        target = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG image', '*.png')])
        if not target: return
        image = Image.new('RGB', (1050, 390), '#132633'); draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 1049, 389), outline=ACCENT, width=6)
        draw.rectangle((8, 8, 1041, 88), fill='#09151f')
        draw.rectangle((22, 104, 33, 371), fill='#9966a2')
        font_path = 'C:/Windows/Fonts/consola.ttf'
        bold_path = 'C:/Windows/Fonts/consolab.ttf'
        def font(size, bold=False):
            try: return ImageFont.truetype(bold_path if bold else font_path, size)
            except OSError: return ImageFont.load_default()
        draw.text((46, 22), (self.badge_org.get() or 'ORGANIZATION')[:32], fill=ACCENT, font=font(46, True))
        draw.text((50, 130), (self.badge_name.get() or 'YOUR NAME')[:32], fill=TEXT, font=font(50, True))
        draw.text((50, 210), (self.badge_role.get() or 'ROLE')[:40], fill=MUTED, font=font(34))
        draw.text((50, 310), 'ID: ' + (self.badge_id.get() or '0000')[:30], fill=ACCENT, font=font(28))
        draw.text((720, 302), 'SAMPLE', fill='#d86d75', font=font(56, True))
        image.save(target)
        messagebox.showinfo('Netcon', f'Badge saved: {target}')

    def _tags_ui(self):
        frame = ttk.Frame(self.tags); frame.pack(fill='both', expand=True, padx=16, pady=20)
        ttk.Label(frame, text='RFID / NFC ASSET INVENTORY', font=('Consolas', 17, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Record printed IDs, device types, owners, and notes for credentials you manage. No radio transmission or credential cloning.', wraplength=850).pack(anchor='w', pady=8)
        self.tag_id, self.tag_type, self.tag_owner = [tk.StringVar() for _ in range(3)]
        for label, var in [('Printed tag ID', self.tag_id), ('Tag type / frequency', self.tag_type), ('Assigned owner', self.tag_owner)]: self.field(frame, label, var)
        NetButton(frame, text='Add inventory record', command=self.add_tag).pack(anchor='w', pady=8)
        self.tag_list = tk.Listbox(frame, bg=PANEL, fg=TEXT, font=('Consolas', 10), border=0)
        self.tag_list.pack(fill='both', expand=True)
        for item in self.data['tags']: self.tag_list.insert('end', self.tag_line(item))

    @staticmethod
    def tag_line(item): return f"{item['id']}  |  {item['type']}  |  {item['owner']}"

    def add_tag(self):
        if not self.tag_id.get().strip(): return messagebox.showinfo('Netcon', 'Enter a printed tag ID.')
        item = {'id': self.tag_id.get().strip(), 'type': self.tag_type.get().strip(), 'owner': self.tag_owner.get().strip()}
        self.data['tags'].append(item); save_data(self.data); self.tag_list.insert('end', self.tag_line(item))
        self.tag_id.set(''); self.tag_type.set(''); self.tag_owner.set('')

    def _locks_ui(self):
        frame = ttk.Frame(self.locks); frame.pack(fill='both', expand=True, padx=16, pady=20)
        ttk.Label(frame, text='LOCK SERVICE / DAMAGE DOCUMENTATION', font=('Consolas', 17, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Log damaged or malfunctioning hardware for repair. A schematic 3D-style cylinder view helps identify parts during maintenance.', wraplength=850).pack(anchor='w', pady=8)
        self.lock_site, self.lock_type, self.lock_note = [tk.StringVar() for _ in range(3)]
        for label, var in [('Site / asset number', self.lock_site), ('Lock type / model', self.lock_type), ('Damage / repair note', self.lock_note)]: self.field(frame, label, var)
        NetButton(frame, text='Save service note', command=self.add_lock).pack(anchor='w', pady=8)
        self.lock_canvas = tk.Canvas(frame, width=500, height=190, bg=PANEL, highlightthickness=0)
        self.lock_canvas.pack(anchor='w', pady=8)
        c = self.lock_canvas
        c.create_polygon(65, 52, 355, 52, 435, 82, 145, 82, fill='#213c49', outline=ACCENT, width=2)
        c.create_rectangle(65, 52, 355, 143, fill='#294652', outline=ACCENT, width=2)
        c.create_polygon(355, 52, 435, 82, 435, 171, 355, 143, fill='#162e3c', outline=ACCENT, width=2)
        c.create_oval(70, 69, 156, 152, fill='#7596a0', outline=ACCENT, width=3)
        c.create_oval(93, 91, 133, 131, fill='#13283d', outline='#d7eff2', width=2)
        c.create_text(247, 98, text='CYLINDER / HOUSING', fill=TEXT, font=('Consolas', 12, 'bold'))
        self.lock_list = tk.Listbox(frame, bg=PANEL, fg=TEXT, font=('Consolas', 10), border=0)
        self.lock_list.pack(fill='both', expand=True)
        for item in self.data['locks']: self.lock_list.insert('end', self.lock_line(item))

    @staticmethod
    def lock_line(item): return f"{item['site']}  |  {item['type']}  |  {item['note']}"

    def add_lock(self):
        if not self.lock_site.get().strip(): return messagebox.showinfo('Netcon', 'Enter a site or asset number.')
        item = {'site': self.lock_site.get().strip(), 'type': self.lock_type.get().strip(), 'note': self.lock_note.get().strip()}
        self.data['locks'].append(item); save_data(self.data); self.lock_list.insert('end', self.lock_line(item))
        self.lock_site.set(''); self.lock_type.set(''); self.lock_note.set('')

    def _games_ui(self):
        frame = ttk.Frame(self.games); frame.pack(fill='both', expand=True, padx=16, pady=20)
        ttk.Label(frame, text='PERSONAL GAME / LICENSE CATALOG', font=('Consolas', 17, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Keep an inventory of your discs and legitimate keys. Store only a short key hint; do not type full product keys here.', wraplength=850).pack(anchor='w', pady=8)
        self.game_name, self.game_platform, self.game_key_hint, self.game_note = [tk.StringVar() for _ in range(4)]
        for label, var in [('Game title', self.game_name), ('Platform / year', self.game_platform), ('Key hint (last 4 only)', self.game_key_hint), ('Compatibility note', self.game_note)]: self.field(frame, label, var)
        NetButton(frame, text='Add game', command=self.add_game).pack(anchor='w', pady=8)
        self.game_list = tk.Listbox(frame, bg=PANEL, fg=TEXT, font=('Consolas', 10), border=0)
        self.game_list.pack(fill='both', expand=True)
        for item in self.data['games']: self.game_list.insert('end', self.game_line(item))

    @staticmethod
    def game_line(item): return f"{item['name']}  |  {item['platform']}  |  key ••••{item['hint']}  |  {item['note']}"

    def add_game(self):
        if not self.game_name.get().strip(): return messagebox.showinfo('Netcon', 'Enter a game title.')
        item = {'name': self.game_name.get().strip(), 'platform': self.game_platform.get().strip(),
                'hint': self.game_key_hint.get().strip()[-4:], 'note': self.game_note.get().strip()}
        self.data['games'].append(item); save_data(self.data); self.game_list.insert('end', self.game_line(item))
        self.game_name.set(''); self.game_platform.set(''); self.game_key_hint.set(''); self.game_note.set('')


if __name__ == '__main__':
    Netcon().mainloop()
