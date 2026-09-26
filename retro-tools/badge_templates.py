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


def sans_font(size: int, bold: bool = False):
    name = 'arialbd.ttf' if bold else 'arial.ttf'
    try:
        return ImageFont.truetype(str(Path('C:/Windows/Fonts') / name), size)
    except OSError:
        return font(size, bold)


def validate(record: dict) -> dict:
    result = {key: str(record.get(key, '')).strip() for key in
              ('template', 'name', 'role', 'department', 'site', 'employee_id', 'issuer',
               'issued', 'expires', 'photo', 'height', 'weight', 'eyes', 'hire_date')}
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


def _aus_card(data: dict, assets: Path) -> Image.Image:
    """Landscape site badge based on the supplied white/blue clip-card layout."""
    image = Image.new('RGB', SIZE, '#ffffff')
    d = ImageDraw.Draw(image)
    d.rectangle((12, 12, 999, 625), outline='#3278cc', width=9)
    d.rectangle((27, 27, 984, 610), outline='#9bc9ed', width=3)
    d.rectangle((34, 34, 977, 43), fill='#3278cc')
    logo_path = assets / 'allied-universal-official-logo.png'
    if logo_path.is_file():
        with Image.open(logo_path) as src:
            logo = src.convert('RGBA')
            logo = logo.crop(logo.getbbox())
            logo.thumbnail((485, 104), Image.Resampling.LANCZOS)
            image.paste(logo, (478, 48), logo)
    else:
        d.text((505, 58), 'ALLIED UNIVERSAL', font=sans_font(42, True), fill='#006ca7')
    _photo(image, data['photo'], (62, 101, 365, 477), '#edf4f7')
    d = ImageDraw.Draw(image)
    d.rectangle((62, 101, 365, 477), outline='#708997', width=3)
    d.text((64, 490), 'Identification will void', font=sans_font(17), fill='#6d7880')
    d.text((64, 513), 'if removed or altered.', font=sans_font(17), fill='#6d7880')
    x = 403
    words = data['name'].upper().split()
    lines = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if current and d.textlength(candidate, font=sans_font(46, True)) > 560:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    for i, line in enumerate(lines[:2]):
        _text(d, (x, 164 + i * 58), line, size=46, fill='#15222b', bold=True, max_width=560)
    title_y = 177 + min(len(lines), 2) * 58
    d.text((x, title_y), 'Title:', font=sans_font(25), fill='#697781')
    _text(d, (468, title_y - 1), (data['role'] or 'EMPLOYEE').upper(),
          size=27, fill='#2c353d', bold=True, max_width=490)
    y = title_y + 68
    for col, label, value in [
        (x, 'Ht:', data['height']), (647, 'Eyes:', data['eyes']),
        (x, 'Wt:', data['weight']), (647, 'DOH:', data['hire_date']),
    ]:
        row = y if label in ('Ht:', 'Eyes:') else y + 54
        d.text((col, row), label, font=sans_font(25), fill='#667882')
        _text(d, (col + (78 if label == 'Eyes:' else 70), row - 2), value or '—',
              size=29, fill='#283943', bold=True, max_width=230)
    d.line((390, 465, 958, 465), fill='#a9c7da', width=2)
    _text(d, (404, 480), f"ID  {data['employee_id']}", size=22, fill='#2e526f', bold=True, max_width=550)
    detail = ' / '.join(filter(None, (data['department'], data['site'])))
    _text(d, (404, 520), detail, size=19, fill='#4d6879', max_width=550)
    d.text((191, 575), 'ALLIED UNIVERSAL EMPLOYEE IDENTIFICATION',
           font=sans_font(19, True), fill='#6b7881')
    return image


def _nightcode_card(data: dict) -> Image.Image:
    """Draw at half resolution so every graphic edge lands on a 2-pixel grid."""
    image = Image.new('RGB', (506, 319), '#040d1c')
    d = ImageDraw.Draw(image)
    # Staggered circuit traces and a hard, stepped chrome border.
    for y in range(49, 273, 18):
        d.line((275, y, 495, y), fill='#0a2039', width=1)
        d.rectangle((474 - (y % 35), y - 1, 476 - (y % 35), y + 1), fill='#123960')
    d.rectangle((3, 3, 502, 315), outline='#0a568a', width=3)
    d.rectangle((7, 7, 498, 311), outline='#3ce3ff', width=1)
    d.rectangle((12, 12, 493, 58), fill='#091e3b')
    d.rectangle((12, 59, 493, 62), fill='#125cad')
    d.rectangle((12, 62, 493, 64), fill='#8d42ca')
    for x in range(16, 486, 8):
        d.rectangle((x, 69, x + 2, 70), fill='#18416a')
    # NightCode's pixel skull and crossed traces, echoing the site mark.
    mark = [(7, 0, 29, 4), (3, 4, 33, 8), (0, 9, 36, 24),
            (4, 24, 32, 30), (9, 30, 27, 34)]
    ox, oy = 22, 18
    for x0, y0, x1, y1 in mark:
        d.rectangle((ox + x0, oy + y0, ox + x1, oy + y1), fill='#42e6ff')
    d.rectangle((ox + 8, oy + 16, ox + 14, oy + 22), fill='#06182d')
    d.rectangle((ox + 22, oy + 16, ox + 28, oy + 22), fill='#06182d')
    d.rectangle((ox + 17, oy + 24, ox + 20, oy + 28), fill='#06182d')
    d.line((ox + 3, oy + 37, ox + 32, oy + 45), fill='#299bff', width=3)
    d.line((ox + 32, oy + 37, ox + 3, oy + 45), fill='#299bff', width=3)
    d.text((70, 19), 'NIGHTCODE', font=font(29, True), fill='#ebfaff')
    d.text((308, 38), 'NODE ID // 16-BIT', font=font(10, True), fill='#a172e8')
    # Recessed portrait panel with pixel corners.
    d.rectangle((19, 79, 157, 274), fill='#08182e', outline='#34cfff', width=2)
    d.rectangle((24, 84, 152, 269), outline='#15568e', width=1)
    if data['photo'] and Path(data['photo']).is_file():
        try:
            with Image.open(data['photo']) as src:
                portrait = ImageOps.fit(src.convert('RGB'), (124, 181),
                                        method=Image.Resampling.LANCZOS, centering=(0.5, 0.3))
            portrait = portrait.resize((62, 91), Image.Resampling.BOX).resize((124, 182), Image.Resampling.NEAREST)
            image.paste(portrait.crop((0, 0, 124, 181)), (26, 86))
        except (OSError, ValueError):
            pass
    else:
        d.rectangle((28, 88, 148, 263), fill='#0b2441')
        # Blocky silhouette, intentionally unlike the stock round avatar.
        d.rectangle((67, 111, 112, 148), fill='#23618b')
        d.rectangle((73, 103, 105, 115), fill='#367ba5')
        d.rectangle((54, 154, 124, 246), fill='#174566')
        d.polygon([(54, 166), (67, 148), (112, 148), (124, 166)], fill='#2a6288')
        d.rectangle((73, 181, 105, 188), fill='#287cbd')
    d.rectangle((19, 255, 157, 274), fill='#092844')
    d.text((26, 259), 'PORTRAIT / 01', font=font(9, True), fill='#53ddf1')
    # Legible operator data in a clear grid.
    x = 172
    d.text((x, 83), 'OPERATIVE RECORD', font=font(11, True), fill='#36d5f0')
    d.rectangle((x, 102, 486, 104), fill='#2d6ea5')
    _text(d, (x, 111), data['name'].upper(), size=23, fill='#f1f7ff', bold=True, max_width=312)
    d.text((x, 151), (data['role'] or 'OPERATIVE').upper(), font=font(13, True), fill='#ab7aef')
    d.text((x, 184), 'NODE', font=font(10, True), fill='#54abc4')
    _text(d, (x + 75, 180), data['site'] or 'LOCAL', size=13, fill='#d7e9f9', max_width=236)
    d.text((x, 208), 'DIVISION', font=font(10, True), fill='#54abc4')
    _text(d, (x + 75, 204), data['department'] or 'FIELD', size=13, fill='#d7e9f9', max_width=236)
    d.text((x, 236), 'ACCESS KEY', font=font(10, True), fill='#54abc4')
    _text(d, (x + 96, 232), data['employee_id'], size=13, fill='#f0f8ff', bold=True, max_width=218)
    d.rectangle((12, 281, 493, 305), fill='#0a2440')
    d.rectangle((12, 281, 493, 282), fill='#3759a9')
    _text(d, (24, 288), f"ISSUED {data['issued'] or '--'}", size=10, fill='#85daf2')
    _text(d, (262, 288), f"EXPIRES {data['expires'] or '--'}", size=10, fill='#85daf2')
    return image.resize(SIZE, Image.Resampling.NEAREST)


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
        image = _aus_card(data, assets)
    elif template == 'NightCode in-world':
        image = _nightcode_card(data)
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
