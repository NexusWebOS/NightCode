"""SpriteCook artwork and dark pixel UI controls shared by the two desktop tools."""

from pathlib import Path
import tkinter as tk

from PIL import Image, ImageTk


BG = '#070d15'
PANEL = '#101c2a'
ACCENT = '#82cbd0'
TEXT = '#e3edf1'
MUTED = '#8da8b4'
EDGE = '#31505d'


def configure_style(root):
    from tkinter import ttk

    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('TFrame', background=BG)
    style.configure('Panel.TFrame', background=PANEL)
    style.configure('TLabel', background=BG, foreground=TEXT, font=('Consolas', 10))
    style.configure('Panel.TLabel', background=PANEL, foreground=TEXT, font=('Consolas', 10))
    style.configure('TNotebook', background=BG, borderwidth=0)
    style.configure('TNotebook.Tab', background=PANEL, foreground=MUTED,
                    padding=(18, 9), font=('Consolas', 10, 'bold'), borderwidth=1)
    style.map('TNotebook.Tab', background=[('selected', '#203541'), ('active', '#182b38')],
              foreground=[('selected', TEXT), ('active', ACCENT)])
    style.configure('TEntry', fieldbackground=PANEL, foreground=TEXT, insertcolor=TEXT,
                    bordercolor=EDGE, padding=5)
    style.configure('TCombobox', fieldbackground=PANEL, background=PANEL, foreground=TEXT,
                    arrowcolor=ACCENT, bordercolor=EDGE, padding=4)
    style.map('TCombobox', fieldbackground=[('readonly', PANEL)], foreground=[('readonly', TEXT)])
    style.configure('TScrollbar', background=PANEL, troughcolor=BG, arrowcolor=ACCENT)
    style.configure('TSeparator', background=EDGE)


def nine_slice(source: Image.Image, width: int, height: int, inset: int = 14) -> Image.Image:
    """Stretch only the middle of a SpriteCook frame; retain its pixel corners."""
    source = source.convert('RGBA')
    sx, sy = source.size
    x = min(inset, sx // 3, width // 3)
    y = min(inset, sy // 3, height // 3)
    out = Image.new('RGBA', (width, height))
    xs = (0, x, sx - x, sx)
    ys = (0, y, sy - y, sy)
    dx = (0, x, width - x, width)
    dy = (0, y, height - y, height)
    for row in range(3):
        for col in range(3):
            piece = source.crop((xs[col], ys[row], xs[col + 1], ys[row + 1]))
            target = (dx[col + 1] - dx[col], dy[row + 1] - dy[row])
            if piece.size != target:
                piece = piece.resize(target, Image.Resampling.NEAREST)
            out.alpha_composite(piece, (dx[col], dy[row]))
    return out


class RetroButton(tk.Button):
    def __init__(self, master, *, text, command, asset_root: Path, app_name: str, **kwargs):
        frame = Image.open(asset_root / 'spritecook' / f'{app_name}-button-frame.png')
        width = max(114, len(text) * 8 + 36)
        self._frame_image = ImageTk.PhotoImage(nine_slice(frame, width, 38))
        super().__init__(master, text=text, command=command, image=self._frame_image,
                         compound='center', font=('Consolas', 10, 'bold'), fg=TEXT, bg=BG,
                         activeforeground=ACCENT, activebackground=BG, bd=0, relief='flat',
                         highlightthickness=0, padx=0, pady=0, cursor='hand2', **kwargs)


class RetroHeader(tk.Canvas):
    def __init__(self, master, asset_root: Path, app_name: str):
        super().__init__(master, height=150, bg=BG, highlightthickness=0, bd=0)
        self.banner = Image.open(asset_root / f'{app_name}-banner.png').convert('RGBA')
        self.logo = Image.open(asset_root / f'{app_name}-logo.png').convert('RGBA')
        self.logo = self.logo.crop(self.logo.getbbox())
        self.mascot = Image.open(asset_root / f'{app_name}-mascot.png').convert('RGBA')
        portrait_path = asset_root / f'{app_name}-portrait.png'
        self.portrait = Image.open(portrait_path).convert('RGBA') if portrait_path.is_file() else None
        self._image = None
        self._render_job = None
        self.bind('<Configure>', self._on_resize)

    def _on_resize(self, _event):
        if self._render_job:
            self.after_cancel(self._render_job)
        self._render_job = self.after(35, self._render)

    def _render(self):
        self._render_job = None
        width, height = max(1, self.winfo_width()), 150
        background = self.banner.resize((width, height), Image.Resampling.NEAREST)
        shade = Image.new('RGBA', (width, height), (4, 9, 16, 0))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(shade)
        draw.rectangle((0, 0, min(width, 475), height), fill=(4, 9, 16, 175))
        draw.rectangle((0, height - 5, width, height), fill=(58, 117, 125, 255))
        background = Image.alpha_composite(background, shade)
        logo = self.logo.copy()
        logo.thumbnail((min(390, width - 170), 92), Image.Resampling.NEAREST)
        background.alpha_composite(logo, (26, (height - logo.height) // 2 - 3))
        if self.portrait:
            draw = ImageDraw.Draw(background)
            draw.rectangle((width - 148, 9, width - 9, 140), fill='#07131e', outline=ACCENT, width=2)
            portrait = self.portrait.resize((118, 118), Image.Resampling.NEAREST)
            background.alpha_composite(portrait, (width - 137, 16))
        else:
            mascot = self.mascot.copy()
            mascot.thumbnail((142, 142), Image.Resampling.NEAREST)
            background.alpha_composite(mascot, (width - mascot.width - 10, height - mascot.height - 5))
        self._image = ImageTk.PhotoImage(background)
        self.delete('all')
        self.create_image(0, 0, image=self._image, anchor='nw')
