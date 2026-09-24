"""Export small, editable-by-code 16-bit style logos and icons."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent / 'assets'
HERE.mkdir(exist_ok=True)


def font(size):
    for name in ['C:/Windows/Fonts/consolab.ttf', 'C:/Windows/Fonts/consola.ttf']:
        try: return ImageFont.truetype(name, size)
        except OSError: pass
    return ImageFont.load_default()


def logo(title, subtitle, filename):
    im = Image.new('RGBA', (680, 170), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 8, 672, 162), radius=10, fill='#0a1020', outline='#31d7e8', width=5)
    d.rectangle((18, 18, 29, 151), fill='#8665dc')
    d.text((50, 23), title, fill='#31d7e8', font=font(67), stroke_width=1, stroke_fill='#133047')
    d.text((52, 113), subtitle, fill='#a9c7d2', font=font(20))
    im.save(HERE / filename)


def icon(name, kind):
    im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    dark, cyan, silver, violet = '#0a1020', '#31d7e8', '#dceef4', '#8665dc'
    if kind == 'disc':
        d.ellipse((2, 2, 29, 29), fill=silver, outline=cyan, width=2)
        d.pieslice((4, 4, 27, 27), 35, 95, fill=violet)
        d.ellipse((11, 11, 20, 20), fill=dark, outline=cyan)
    elif kind == 'badge':
        d.rectangle((7, 5, 24, 28), fill=silver, outline=cyan, width=2)
        d.rectangle((11, 2, 20, 7), fill=dark, outline=violet, width=2)
        d.ellipse((11, 10, 17, 16), fill=violet)
        d.rectangle((11, 20, 21, 22), fill=dark)
    elif kind == 'folder':
        d.polygon([(2, 9), (11, 9), (14, 12), (29, 12), (29, 26), (2, 26)], fill=violet, outline=cyan)
        d.rectangle((4, 15, 27, 24), fill='#365d87')
    elif kind == 'lock':
        d.arc((8, 2, 24, 21), 180, 360, fill=cyan, width=4)
        d.rectangle((5, 15, 27, 29), fill=violet, outline=cyan, width=2)
        d.ellipse((14, 19, 18, 23), fill=dark)
    elif kind == 'game':
        d.rounded_rectangle((2, 9, 29, 25), radius=5, fill=violet, outline=cyan, width=2)
        d.rectangle((8, 13, 11, 21), fill=silver); d.rectangle((5, 16, 14, 18), fill=silver)
        d.ellipse((20, 14, 23, 17), fill=silver); d.ellipse((24, 18, 27, 21), fill=silver)
    im.resize((128, 128), Image.Resampling.NEAREST).save(HERE / name)


logo('DISK DUDE', 'OPTICAL MEDIA / ARCHIVE / PLAY', 'disk-dude-logo.png')
logo('NETCON', 'BADGES / ASSETS / SERVICE', 'netcon-logo.png')
for filename, kind in [('disc-icon.png', 'disc'), ('badge-icon.png', 'badge'),
                       ('folder-icon.png', 'folder'), ('lock-icon.png', 'lock'), ('game-icon.png', 'game')]:
    icon(filename, kind)

for app in ['disk-dude', 'netcon']:
    sprite = Image.open(HERE / f'{app}-mascot.png').convert('RGBA')
    sprite.thumbnail((500, 500), Image.Resampling.NEAREST)
    banner = Image.new('RGBA', (1200, 500), '#0a1020')
    banner.alpha_composite(sprite, (700 + (500 - sprite.width) // 2, (500 - sprite.height) // 2))
    mark = Image.open(HERE / f'{app}-logo.png').convert('RGBA')
    banner.alpha_composite(mark, (30, 75))
    banner.save(HERE / f'{app}-banner.png')
    thumb = Image.open(HERE / ('disc-icon.png' if app == 'disk-dude' else 'badge-icon.png'))
    thumb.save(HERE / f'{app}.ico', sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])

print('Exported logos, icons, and banners to', HERE)
