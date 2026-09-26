"""Netcon's GPT-generated chrome, pixel UI textures and native cursors."""

import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk
from retro_skin import nine_slice


BG = '#050a14'
PANEL = '#0b1726'
CYAN = '#1ce5f2'
VIOLET = '#b480e1'
AMBER = '#f0af38'
SILVER = '#e5eff7'
MUTED = '#8fa9be'
EDGE = '#265c72'


def configure_netcon_style(root, assets=None):
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('TFrame', background=BG)
    style.configure('Panel.TFrame', background=PANEL)
    style.configure('Framed.Panel.TFrame', background=PANEL, bordercolor=EDGE,
                    relief='solid', borderwidth=1)
    style.configure('TLabel', background=BG, foreground=SILVER, font=('Consolas', 10))
    style.configure('Panel.TLabel', background=PANEL, foreground=SILVER, font=('Consolas', 10))
    style.configure('TNotebook', background=BG, borderwidth=0)
    style.configure('TNotebook.Tab', background='#101a2e', foreground=VIOLET,
                    padding=(24, 10), font=('Consolas', 10, 'bold'), borderwidth=1)
    style.map('TNotebook.Tab', background=[('selected', '#103544'), ('active', '#152d3d')],
              foreground=[('selected', CYAN), ('active', SILVER)])
    style.configure('TEntry', fieldbackground='#0b1b2c', foreground=SILVER,
                    insertcolor=CYAN, bordercolor=EDGE, padding=5)
    style.configure('TCombobox', fieldbackground='#0b1b2c', background=PANEL,
                    foreground=SILVER, arrowcolor=CYAN, bordercolor=EDGE, padding=4)
    style.map('TCombobox', fieldbackground=[('readonly', '#0b1b2c')],
              foreground=[('readonly', SILVER)])
    style.configure('TSeparator', background=EDGE)
    if assets is None:
        return
    photos = root._netcon_style_photos = {}
    for name, filename in (('Chrome.Panel.TFrame', 'standard'),
                           ('Focus.Panel.TFrame', 'focused'),
                           ('Framed.Panel.TFrame', 'standard'),
                           ('Dialog.Panel.TFrame', 'dialog')):
        with Image.open(assets / 'netcon-kit' / 'frames' / (filename + '.png')) as source:
            photos[name] = ImageTk.PhotoImage(source.convert('RGBA'), master=root)
        element = 'Netcon.' + name
        if element not in style.element_names():
            style.element_create(element, 'image', photos[name], border=30, padding=0, sticky='nswe')
        style.layout(name, [(element, {'sticky': 'nswe'})])
        style.configure(name, background=PANEL)
    for name in ('normal', 'hover', 'pressed'):
        with Image.open(assets / 'netcon-kit' / 'buttons' / (name + '.png')) as source:
            photos[name] = ImageTk.PhotoImage(source.convert('RGBA'), master=root)
    if 'Netcon.tab' not in style.element_names():
        style.element_create('Netcon.tab', 'image', photos['normal'],
                             ('selected', photos['hover']), ('active', photos['hover']),
                             border=16, padding=0, sticky='nswe')
    style.layout('TNotebook.Tab', [('Netcon.tab', {'sticky': 'nswe', 'children': [
        ('Notebook.padding', {'side': 'top', 'sticky': 'nswe', 'children': [
            ('Notebook.label', {'side': 'top', 'sticky': ''})]})]})])
    style.configure('TNotebook.Tab', padding=(22, 12))


def cursor_for(assets, name, fallback='arrow'):
    path = assets / 'netcon-kit' / 'cursors' / (name + '.cur')
    # A one-element Tcl list preserves spaces in Windows paths.
    return ('@' + str(path),) if os.name == 'nt' and path.is_file() else fallback


def apply_netcon_cursors(root, assets):
    root.configure(cursor=cursor_for(assets, 'pointer'))
    def visit(widget):
        if isinstance(widget, (tk.Button, ttk.Button, ttk.Combobox)):
            widget.configure(cursor=cursor_for(assets, 'link', 'hand2'))
        elif isinstance(widget, (tk.Entry, ttk.Entry, tk.Text)):
            widget.configure(cursor=cursor_for(assets, 'text', 'xterm'))
        for child in widget.winfo_children():
            visit(child)
    visit(root)


class NetconButton(tk.Button):
    """Keep native button behavior and render the generated state artwork."""
    def __init__(self, master, *, text, command, asset_root, **kwargs):
        face = tkfont.Font(root=master, family='Consolas', size=10, weight='bold')
        width = max(122, face.measure(text) + 40)
        self._images = {}
        self._hover = self._pressed = self._focus = False
        for name in ('normal', 'hover', 'pressed', 'disabled'):
            with Image.open(asset_root / 'netcon-kit' / 'buttons' / (name + '.png')) as source:
                self._images[name] = ImageTk.PhotoImage(nine_slice(source, width, 48, 16), master=master)
        super().__init__(master, text=text, command=command, image=self._images['normal'],
                         compound='center', font=('Consolas', 10, 'bold'), fg=SILVER, bg=PANEL,
                         activeforeground=CYAN, activebackground=PANEL, disabledforeground=MUTED,
                         bd=0, relief='flat', highlightthickness=0, padx=0, pady=0,
                         cursor=cursor_for(asset_root, 'link', 'hand2'), **kwargs)
        for event, key, value in [('<Enter>', '_hover', True), ('<Leave>', '_hover', False),
                                  ('<FocusIn>', '_focus', True), ('<FocusOut>', '_focus', False),
                                  ('<ButtonPress-1>', '_pressed', True),
                                  ('<ButtonRelease-1>', '_pressed', False),
                                  ('<KeyPress-space>', '_pressed', True),
                                  ('<KeyRelease-space>', '_pressed', False)]:
            self.bind(event, lambda _event, key=key, value=value: self._set_visual(key, value), add='+')

    def _set_visual(self, key, value):
        setattr(self, key, value)
        self._sync_visual()

    def _sync_visual(self):
        state = 'disabled' if str(self.cget('state')) == 'disabled' else (
            'pressed' if self._pressed and (self._hover or self._focus) else
            'hover' if self._hover or self._focus else 'normal')
        super().configure(image=self._images[state])

    def configure(self, cnf=None, **kwargs):
        result = super().configure(cnf, **kwargs)
        if hasattr(self, '_images') and ('state' in kwargs or isinstance(cnf, dict) and 'state' in cnf):
            self._sync_visual()
        return result

    config = configure


def _font(size, bold=False):
    path = Path('C:/Windows/Fonts') / ('consolab.ttf' if bold else 'consola.ttf')
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def render_header(assets: Path, width: int, height: int = 228) -> Image.Image:
    width = max(width, 800)
    with Image.open(assets / 'netcon-banner-gpt-v3.png') as source:
        image = ImageOps.fit(source.convert('RGB'), (width, height),
                             method=Image.Resampling.NEAREST, centering=(0.5, 0.5))
    d = ImageDraw.Draw(image)
    status_x = round(width * 0.805)
    d.text((status_x, 61), 'NODE STATUS', fill=CYAN, font=_font(14, True))
    d.text((status_x, 90), 'LOCAL / READY', fill=SILVER, font=_font(16, True))
    d.text((status_x, 127), 'NETCON SYSTEM', fill=MUTED, font=_font(12))
    return image


class NetconHeader(tk.Canvas):
    def __init__(self, master, assets: Path):
        super().__init__(master, height=228, bg=BG, bd=0, highlightthickness=0)
        self.assets = assets
        self._photo = None
        self._job = None
        self.bind('<Configure>', self._resize)

    def _resize(self, _event):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(45, self._render)

    def _render(self):
        self._job = None
        self._photo = ImageTk.PhotoImage(render_header(self.assets, self.winfo_width()))
        self.delete('all')
        self.create_image(0, 0, anchor='nw', image=self._photo)
