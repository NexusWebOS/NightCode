"""Netcon's marquee-led chrome and neon interface styling."""

from pathlib import Path
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageDraw, ImageFont, ImageTk


BG = '#050a14'
PANEL = '#0b1726'
CYAN = '#1ce5f2'
VIOLET = '#b480e1'
AMBER = '#f0af38'
SILVER = '#e5eff7'
MUTED = '#8fa9be'
EDGE = '#265c72'


def configure_netcon_style(root):
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


def _font(size, bold=False):
    path = Path('C:/Windows/Fonts') / ('consolab.ttf' if bold else 'consola.ttf')
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def render_header(assets: Path, width: int, height: int = 184) -> Image.Image:
    width = max(width, 800)
    image = Image.new('RGB', (width, height), BG)
    d = ImageDraw.Draw(image)
    for x in range(0, width, 20):
        d.line((x, 0, x - 80, height), fill='#091421', width=1)
    d.rectangle((0, 0, width - 1, height - 1), outline=EDGE, width=2)
    d.line((6, 5, width - 6, 5), fill=CYAN, width=2)
    d.line((6, height - 7, width - 6, height - 7), fill=VIOLET, width=2)
    d.rectangle((10, 13, 177, height - 15), fill='#060d18', outline=CYAN, width=1)
    with Image.open(assets / 'netcon-logo.png') as src:
        emblem = src.convert('RGB')
        emblem.thumbnail((157, 157), Image.Resampling.LANCZOS)
    image.paste(emblem, (15 + (157 - emblem.width) // 2, 15 + (height - 30 - emblem.height) // 2))
    with Image.open(assets / 'netcon-banner.png') as src:
        marquee = src.convert('RGB')
        marquee.thumbnail((max(500, width - 415), height - 10), Image.Resampling.LANCZOS)
    image.paste(marquee, (187, (height - marquee.height) // 2))
    status_x = width - 206
    d.line((status_x - 12, 23, status_x - 12, height - 24), fill=EDGE, width=2)
    d.text((status_x, 39), 'NODE STATUS', fill=CYAN, font=_font(16, True))
    d.text((status_x, 70), 'LOCAL / READY', fill=SILVER, font=_font(18, True))
    d.text((status_x, 111), 'NETCON SYSTEM', fill=MUTED, font=_font(13))
    for i in range(5):
        d.rectangle((status_x + i * 20, 145, status_x + i * 20 + 10, 150), fill=AMBER if i < 3 else VIOLET)
    return image


class NetconHeader(tk.Canvas):
    def __init__(self, master, assets: Path):
        super().__init__(master, height=184, bg=BG, bd=0, highlightthickness=0)
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
