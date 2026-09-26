from __future__ import annotations

import json
from functools import partial
import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from badge_editor import BadgeEditor
from retro_skin import RetroButton
from netcon_skin import (AMBER, BG, CYAN as ACCENT, EDGE, MUTED, PANEL,
                         SILVER as TEXT, NetconHeader, configure_netcon_style)

BASE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
ASSETS = BASE / 'assets'
NetButton = partial(RetroButton, asset_root=ASSETS, app_name='netcon')
DATA = Path(os.getenv('LOCALAPPDATA', str(Path.home()))) / 'RetroTools' / 'netcon.json'


def load_data():
    try: data = json.loads(DATA.read_text(encoding='utf-8'))
    except (OSError, ValueError): data = {}
    for key in ('tags', 'locks', 'games', 'badges'):
        data.setdefault(key, [])
    return data


def save_data(data):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    staged = DATA.with_suffix('.tmp')
    staged.write_text(json.dumps(data, indent=2), encoding='utf-8')
    staged.replace(DATA)


class Netcon(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('NETCON  |  Retro Tools')
        self.geometry('1160x820')
        self.minsize(1060, 820)
        self.configure(bg=BG)
        self.data = load_data()
        self._style()
        self._build()

    def _style(self):
        configure_netcon_style(self)

    def _build(self):
        NetconHeader(self, ASSETS).pack(fill='x', padx=18, pady=(14, 8))
        footer = tk.Frame(self, bg='#091624', highlightbackground=EDGE, highlightthickness=1)
        footer.pack(side='bottom', fill='x', padx=18, pady=(3, 12))
        tk.Label(footer, text='◆  NETCON // LOCAL NODE', bg='#091624', fg=ACCENT,
                 font=('Consolas', 9, 'bold')).pack(side='left', padx=11, pady=5)
        self.active_section = tk.StringVar(value='BADGE STUDIO')
        tk.Label(footer, textvariable=self.active_section, bg='#091624', fg=MUTED,
                 font=('Consolas', 9)).pack(side='left', padx=20)
        tk.Label(footer, text='●  OFFLINE READY', bg='#091624', fg=AMBER,
                 font=('Consolas', 9, 'bold')).pack(side='right', padx=12)
        self.tabs = ttk.Notebook(self); self.tabs.pack(fill='both', expand=True, padx=18, pady=(0, 3))
        self.badge, self.tags, self.locks, self.games = [ttk.Frame(self.tabs) for _ in range(4)]
        for frame, label in [(self.badge, 'BADGE STUDIO'), (self.tags, 'RFID INVENTORY'),
                             (self.locks, 'LOCK SERVICE'), (self.games, 'GAME LIBRARY')]:
            self.tabs.add(frame, text=label)
        self.tabs.bind('<<NotebookTabChanged>>', lambda _event: self.active_section.set(
            self.tabs.tab(self.tabs.select(), 'text')))
        self._badge_ui(); self._tags_ui(); self._locks_ui(); self._games_ui()

    def field(self, parent, label, var, width=58):
        row = ttk.Frame(parent, style='Panel.TFrame'); row.pack(anchor='w', fill='x', pady=5)
        ttk.Label(row, text=label, width=28, style='Panel.TLabel').pack(side='left')
        ttk.Entry(row, textvariable=var, width=width).pack(side='left')

    def _badge_ui(self):
        BadgeEditor(self.badge, self.data, save_data, ASSETS, NetButton).pack(
            fill='both', expand=True, padx=16, pady=14)

    def _tags_ui(self):
        frame = ttk.Frame(self.tags, style='Framed.Panel.TFrame', padding=16); frame.pack(fill='both', expand=True, padx=16, pady=16)
        ttk.Label(frame, text='RFID / NFC ASSET INVENTORY', font=('Consolas', 17, 'bold'), style='Panel.TLabel').pack(anchor='w')
        ttk.Label(frame, text='Record printed IDs, device types, owners, and notes for credentials you manage. No radio transmission or credential cloning.', wraplength=850, style='Panel.TLabel').pack(anchor='w', pady=8)
        self.tag_id, self.tag_type, self.tag_owner = [tk.StringVar() for _ in range(3)]
        for label, var in [('Printed tag ID', self.tag_id), ('Tag type / frequency', self.tag_type), ('Assigned owner', self.tag_owner)]: self.field(frame, label, var)
        NetButton(frame, text='Add inventory record', command=self.add_tag).pack(anchor='w', pady=8)
        self.tag_list = tk.Listbox(frame, bg=PANEL, fg=TEXT, selectbackground='#18445b',
                                   font=('Consolas', 10), border=0)
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
        frame = ttk.Frame(self.locks, style='Framed.Panel.TFrame', padding=16); frame.pack(fill='both', expand=True, padx=16, pady=16)
        ttk.Label(frame, text='LOCK SERVICE / DAMAGE DOCUMENTATION', font=('Consolas', 17, 'bold'), style='Panel.TLabel').pack(anchor='w')
        ttk.Label(frame, text='Log damaged or malfunctioning hardware for repair. A schematic 3D-style cylinder view helps identify parts during maintenance.', wraplength=850, style='Panel.TLabel').pack(anchor='w', pady=8)
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
        c.create_rectangle(388, 127, 411, 142, fill=AMBER, outline='#f7d48d', width=1)
        c.create_line(55, 172, 449, 172, fill='#7c4da1', width=2)
        self.lock_list = tk.Listbox(frame, bg=PANEL, fg=TEXT, selectbackground='#18445b',
                                    font=('Consolas', 10), border=0)
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
        frame = ttk.Frame(self.games, style='Framed.Panel.TFrame', padding=16); frame.pack(fill='both', expand=True, padx=16, pady=16)
        ttk.Label(frame, text='PERSONAL GAME / LICENSE CATALOG', font=('Consolas', 17, 'bold'), style='Panel.TLabel').pack(anchor='w')
        ttk.Label(frame, text='Keep an inventory of your discs and legitimate keys. Store only a short key hint; do not type full product keys here.', wraplength=850, style='Panel.TLabel').pack(anchor='w', pady=8)
        self.game_name, self.game_platform, self.game_key_hint, self.game_note = [tk.StringVar() for _ in range(4)]
        for label, var in [('Game title', self.game_name), ('Platform / year', self.game_platform), ('Key hint (last 4 only)', self.game_key_hint), ('Compatibility note', self.game_note)]: self.field(frame, label, var)
        NetButton(frame, text='Add game', command=self.add_game).pack(anchor='w', pady=8)
        self.game_list = tk.Listbox(frame, bg=PANEL, fg=TEXT, selectbackground='#18445b',
                                    font=('Consolas', 10), border=0)
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
