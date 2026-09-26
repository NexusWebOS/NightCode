"""Printable staff and fictional badge layouts for Netcon."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

SIZE = (1012, 638)  # CR80 card at 300 DPI (approximately 3.37 x 2.13 in)
TEMPLATES = ('NightCode in-world', 'Allied Universal staff', 'State ID specimen')


def font(size: int, bold: bool = False):
    name = 'consolab.ttf' if bold else 'consola.ttf'
    try:
        return ImageFont.truetype(str(Path('C:/Windows/Fonts') / name), size)
    except OSError:
        return ImageFont.load_default()


def validate(record: dict) -> dict:
    result = {key: str(record.get(key, '')).strip() for key in
              ('template', 'name', 'role', 'department', 'site', 'employee_id', 'issuer', 'issued', 'expires', 'photo')}
    if result['template'] not in TEMPLATES:
        raise ValueError('Select a badge template.')
    if not result['name']:
        raise ValueError('Enter the cardholder name.')
    if result['template'] != 'State ID specimen' and not result['employee_id']:
        raise ValueError('Enter an employee or NightCode ID.')
    if result['issued'] or result['expires']:
        try:
            issued = date.fromisoformat(result['issued']) if result['issued'] else None
            expires = date.fromisoformat(result['expires']) if result['expires'] else None
        except ValueError as exc:
            raise ValueError('Dates must use YYYY-MM-DD.') from exc
        if issued and expires and expires < issued:
            raise ValueError('Expiry must be on or after issue date.')
    if result['template'] == 'State ID specimen':
        result['employee_id'] = 'DEMO-' + (result['employee_id'].removeprefix('DEMO-') or '0000')[:12]
    return result


def _photo(canvas: Image.Image, photo_path: str, box: tuple[int, int, int, int], fill: str):
    draw = ImageDraw.Draw(canvas)
    draw.rectangle(box, fill=fill, outline='#58a5b2', width=3)
    if photo_path and Path(photo_path).is_file():
        try:
            with Image.open(photo_path) as src:
                fitted = ImageOps.fit(src.convert('RGB'), (box[2] - box[0] - 8, box[3] - box[1] - 8),
                                      method=Image.Resampling.LANCZOS, centering=(0.5, 0.3))
            canvas.paste(fitted, (box[0] + 4, box[1] + 4))
            return
        except (OSError, ValueError):
            pass
    cx = (box[0] + box[2]) // 2
    draw.ellipse((cx - 38, box[1] + 42, cx + 38, box[1] + 118), fill='#4c6977')
    draw.rounded_rectangle((cx - 78, box[1] + 128, cx + 78, box[3] - 28), radius=42, fill='#4c6977')
    draw.text((box[0] + 18, box[3] - 23), 'PHOTO', fill='#b1cbd3', font=font(17, True))


def _text(draw, xy, value, *, size, fill, bold=False, max_width=None):
    value = str(value)
    face = font(size, bold)
    if max_width:
        while value and draw.textbbox((0, 0), value, font=face)[2] > max_width:
            value = value[:-2] + '…'
    draw.text(xy, value, fill=fill, font=face)


def render(record: dict, assets: Path) -> Image.Image:
    data = validate(record)
    template = data['template']
    if template == 'Allied Universal staff':
        image = Image.new('RGB', SIZE, '#f8fbfc')
        d = ImageDraw.Draw(image)
        d.rectangle((0, 0, 1012, 27), fill='#0078b5')
        d.rectangle((0, 146, 20, 638), fill='#0078b5')
        logo_path = assets / 'allied-universal-official-logo.png'
        if logo_path.is_file():
            with Image.open(logo_path) as src:
                logo = src.convert('RGBA')
                logo = logo.crop(logo.getbbox())
                logo.thumbnail((540, 116), Image.Resampling.LANCZOS)
                image.paste(logo, (36, 29), logo)
        else:
            _text(d, (43, 62), 'ALLIED UNIVERSAL', size=55, fill='#006ea7', bold=True)
        _text(d, (704, 63), 'STAFF IDENTIFICATION', size=25, fill='#1b4157', bold=True)
        d.line((33, 143, 979, 143), fill='#a8c3ce', width=3)
        _photo(image, data['photo'], (44, 174, 310, 551), '#dfebee')
        _text(d, (348, 185), data['name'].upper(), size=45, fill='#122d42', bold=True, max_width=610)
        _text(d, (350, 254), data['role'] or 'EMPLOYEE', size=30, fill='#006eaa', bold=True, max_width=605)
        _text(d, (350, 316), 'EMPLOYEE ID', size=19, fill='#647e8e', bold=True)
        _text(d, (350, 345), data['employee_id'], size=31, fill='#132f43', bold=True)
        _text(d, (350, 404), 'DEPARTMENT / SITE', size=19, fill='#647e8e', bold=True)
        _text(d, (350, 431), ' / '.join(filter(None, (data['department'], data['site']))) or '—',
              size=25, fill='#1d4255', max_width=610)
        _text(d, (48, 579), f"ISSUED {data['issued'] or '—'}", size=21, fill='#28495b')
        _text(d, (390, 579), f"EXPIRES {data['expires'] or '—'}", size=21, fill='#28495b')
        _text(d, (745, 579), 'SITE APPROVAL REQUIRED', size=17, fill='#647e8e')
    elif template == 'NightCode in-world':
        image = Image.new('RGB', SIZE, '#08131f')
        d = ImageDraw.Draw(image)
        for x in range(12, 1012, 16):
            d.line((x, 0, x, 638), fill='#0b1b28', width=1)
        d.rectangle((8, 8, 1003, 629), outline='#62c9d1', width=5)
        d.rectangle((22, 22, 990, 126), fill='#0d2633')
        d.rectangle((22, 128, 990, 136), fill='#724c8d')
        _text(d, (52, 39), 'NIGHTCODE', size=66, fill='#8be1df', bold=True)
        _text(d, (721, 55), 'LOCAL NODE // ID', size=26, fill='#b299d3', bold=True)
        _photo(image, data['photo'], (45, 165, 304, 553), '#102c3d')
        _text(d, (338, 185), data['name'].upper(), size=48, fill='#ecf4f4', bold=True, max_width=615)
        _text(d, (340, 257), data['role'] or 'OPERATIVE', size=28, fill='#8be1df', bold=True)
        _text(d, (340, 321), f"NODE / {data['site'] or 'LOCAL'}", size=23, fill='#a9bccc')
        _text(d, (340, 364), f"DIVISION / {data['department'] or 'FIELD'}", size=23, fill='#a9bccc')
        _text(d, (340, 427), f"ID {data['employee_id']}", size=30, fill='#d6b7ea', bold=True)
        _text(d, (51, 582), f"ISSUED {data['issued'] or '—'}   EXPIRES {data['expires'] or '—'}",
              size=20, fill='#96b7c5')
    else:
        image = Image.new('RGB', SIZE, '#ecf0e8')
        d = ImageDraw.Draw(image)
        d.rectangle((0, 0, 1012, 102), fill='#354c56')
        d.rectangle((0, 102, 1012, 115), fill='#bb8b50')
        _text(d, (35, 24), 'DEMO STATE', size=54, fill='#ffffff', bold=True)
        _text(d, (662, 47), 'ID DESIGN STUDY', size=24, fill='#e7eee9', bold=True)
        _photo(image, data['photo'], (40, 143, 289, 516), '#cfdad6')
        _text(d, (326, 157), 'NAME', size=19, fill='#50656a', bold=True)
        _text(d, (326, 188), data['name'].upper(), size=42, fill='#1d363f', bold=True, max_width=637)
        _text(d, (326, 273), 'DESIGN REFERENCE', size=19, fill='#50656a', bold=True)
        _text(d, (326, 304), data['employee_id'], size=30, fill='#1d363f', bold=True)
        _text(d, (326, 386), f"ISSUED {data['issued'] or '—'}", size=23, fill='#29434a')
        _text(d, (326, 428), f"EXPIRES {data['expires'] or '—'}", size=23, fill='#29434a')
        d.rectangle((17, 541, 995, 623), fill='#492f38')
        _text(d, (96, 560), 'SPECIMEN · NOT VALID FOR IDENTIFICATION',
              size=32, fill='#ffffff', bold=True)
        overlay = Image.new('RGBA', SIZE)
        mark = ImageDraw.Draw(overlay)
        mark.text((190, 260), 'SPECIMEN', fill=(157, 44, 54, 83), font=font(103, True))
        image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
    return image


def save(image: Image.Image, target: Path):
    if target.suffix.lower() == '.pdf':
        image.save(target, 'PDF', resolution=300.0)
    else:
        image.save(target, 'PNG', dpi=(300, 300))
