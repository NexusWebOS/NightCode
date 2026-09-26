"""Printable staff and fictional badge layouts for Netcon."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

SIZE = (1012, 638)  # CR80 card at 300 DPI (approximately 3.37 x 2.13 in)
NY_TEMPLATES = ('New York specimen · 16-bit', 'New York specimen · polished')
TEMPLATES = ('NightCode in-world', 'Allied Universal staff', 'State ID specimen') + NY_TEMPLATES


def is_specimen(template: str) -> bool:
    return template == 'State ID specimen' or template in NY_TEMPLATES


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
               'issued', 'expires', 'photo', 'height', 'weight', 'eyes', 'hire_date', 'dob', 'side')}
    if result['template'] not in TEMPLATES:
        raise ValueError('Select a badge template.')
    if not result['name']:
        raise ValueError('Enter the cardholder name.')
    if not is_specimen(result['template']) and not result['employee_id']:
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
    if result['template'] in NY_TEMPLATES:
        value = result['employee_id'].removeprefix('DEMO-NY-').removeprefix('DEMO-')
        result['employee_id'] = 'DEMO-NY-' + (value or '0000')[:12]
        if result['dob']:
            try:
                date.fromisoformat(result['dob'])
            except ValueError as exc:
                raise ValueError('Birth date must use YYYY-MM-DD.') from exc
    result['side'] = result['side'] or 'Front'
    if result['side'] not in ('Front', 'Back'):
        raise ValueError('Select Front or Back.')
    return result


def _aus_card(data: dict, assets: Path) -> Image.Image:
    """Landscape site badge based on the supplied white/blue clip-card layout."""
    with Image.open(assets / 'allied-staff-gpt-v2.png') as source:
        image = source.convert('RGB').resize(SIZE, Image.Resampling.NEAREST)
    d = ImageDraw.Draw(image)
    logo_path = assets / 'allied-universal-official-logo.png'
    if logo_path.is_file():
        with Image.open(logo_path) as src:
            logo = src.convert('RGBA')
            logo = logo.crop(logo.getbbox())
            logo.thumbnail((485, 104), Image.Resampling.LANCZOS)
            image.paste(logo, (478, 48), logo)
    else:
        d.text((505, 58), 'ALLIED UNIVERSAL', font=sans_font(42, True), fill='#006ca7')
    if data['photo'] and Path(data['photo']).is_file():
        try:
            with Image.open(data['photo']) as source:
                portrait = ImageOps.fit(source.convert('RGB'), (276, 365),
                                        method=Image.Resampling.LANCZOS, centering=(0.5, 0.3))
            image.paste(portrait, (62, 102))
        except (OSError, ValueError):
            pass
    d = ImageDraw.Draw(image)
    d.text((64, 518), 'Identification will void', font=sans_font(16), fill='#6d7880')
    d.text((64, 539), 'if removed or altered.', font=sans_font(16), fill='#6d7880')
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
    return image


def _nightcode_card(data: dict, assets: Path) -> Image.Image:
    """Layer editable badge data over GPT-generated 16-bit card artwork."""
    with Image.open(assets / 'nightcode-badge-gpt-v2.png') as source:
        image = source.convert('RGB').resize(SIZE, Image.Resampling.NEAREST)
    if data['photo'] and Path(data['photo']).is_file():
        try:
            with Image.open(data['photo']) as source:
                portrait = ImageOps.fit(source.convert('RGB'), (231, 308),
                                        method=Image.Resampling.LANCZOS, centering=(0.5, 0.3))
            portrait = portrait.resize((116, 154), Image.Resampling.BOX).resize(
                (232, 308), Image.Resampling.NEAREST)
            image.paste(portrait.crop((0, 0, 231, 308)), (47, 188))
        except (OSError, ValueError):
            pass
    # Text stays live so names and dates remain editable in Netcon.
    layer = Image.new('RGBA', (506, 319))
    d = ImageDraw.Draw(layer)
    d.text((192, 38), 'NIGHTCODE', font=font(29, True), fill='#e5fbff')
    d.text((193, 64), 'NODE ID  //  16-BIT', font=font(10, True), fill='#8ae9fb')
    d.text((171, 94), 'OPERATIVE RECORD', font=font(10, True), fill='#58e4fb')
    _text(d, (171, 114), data['name'].upper(), size=23, fill='#ffffff', bold=True, max_width=300)
    _text(d, (171, 146), (data['role'] or 'OPERATIVE').upper(), size=13,
          fill='#b993ff', bold=True, max_width=285)
    d.text((171, 181), 'NODE', font=font(10, True), fill='#69d9f0')
    _text(d, (248, 178), data['site'] or 'LOCAL', size=13, fill='#e5faff', max_width=235)
    d.text((171, 207), 'DIVISION', font=font(10, True), fill='#69d9f0')
    _text(d, (248, 204), data['department'] or 'FIELD', size=13, fill='#e5faff', max_width=235)
    d.text((171, 233), 'ID', font=font(10, True), fill='#69d9f0')
    _text(d, (248, 230), data['employee_id'], size=13, fill='#ffffff', bold=True, max_width=235)
    d.text((49, 241), 'PORTRAIT', font=font(9, True), fill='#79dfee')
    _text(d, (56, 278), f"ISSUED {data['issued'] or '--'}", size=10, fill='#c7f7ff')
    _text(d, (280, 278), f"EXPIRES {data['expires'] or '--'}", size=10, fill='#c7f7ff')
    overlay = layer.resize(SIZE, Image.Resampling.NEAREST)
    return Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')


def _ny_card(data: dict, assets: Path) -> Image.Image:
    pixel = data['template'] == NY_TEMPLATES[0]
    style = '16bit' if pixel else 'polished'
    side = data['side'].lower()
    with Image.open(assets / f'ny-specimen-{style}-{side}-gpt.png') as source:
        image = source.convert('RGB').resize(
            SIZE, Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS)
    boxes = {
        ('16bit', 'front'): (36, 211, 332, 530),
        ('16bit', 'back'): (101, 245, 236, 376),
        ('polished', 'front'): (38, 142, 326, 532),
        ('polished', 'back'): (40, 273, 218, 489),
    }
    if data['photo']:
        box = boxes[(style, side)]
        size = (box[2] - box[0], box[3] - box[1])
        try:
            with Image.open(data['photo']) as source:
                portrait = ImageOps.fit(source.convert('RGB'), size,
                                        method=Image.Resampling.LANCZOS, centering=(0.5, 0.3))
        except (OSError, ValueError) as exc:
            raise ValueError('The saved portrait could not be opened. Choose the photo again.') from exc
        if pixel:
            portrait = portrait.resize((size[0] // 2, size[1] // 2), Image.Resampling.BOX).resize(
                size, Image.Resampling.NEAREST)
        else:
            portrait = ImageOps.grayscale(portrait).convert('RGB')
        original = image.crop(box)
        if pixel and side == 'back':
            mask = Image.new('L', size)
            ImageDraw.Draw(mask).ellipse((0, 0, size[0] - 1, size[1] - 1), fill=255)
            image.paste(portrait, box[:2], mask)
        else:
            image.paste(portrait, box[:2])
        # Retain the generated burgundy specimen lettering above an inserted photo.
        red, green, blue = original.split()
        mark = ImageChops.multiply(
            ImageChops.subtract(red, green).point(lambda v: 255 if v > 35 else 0),
            ImageChops.subtract(red, blue).point(lambda v: 255 if v > 20 else 0))
        image.paste(original, box[:2], mark)

    scale = 2 if pixel else 1
    layer = Image.new('RGBA', (SIZE[0] // scale, SIZE[1] // scale))
    draw = ImageDraw.Draw(layer)

    def write(x, y, value, size=23, width=590, bold=False):
        face = (font if pixel else sans_font)(max(10, size // scale), bold)
        value = str(value)
        if draw.textlength(value, font=face) > width / scale:
            while value and draw.textlength(value + '…', font=face) > width / scale:
                value = value[:-1]
            value += '…'
        draw.text((x // scale, y // scale), value, font=face, fill='#09243f',
                  stroke_width=1, stroke_fill='#fff9e8')

    if side == 'front':
        x, y = (365, 222) if pixel else (356, 151)
        write(x, y, data['name'].upper(), 34, bold=True)
        write(x, y + 48, data['employee_id'], 25, bold=True)
        write(x, y + 89, 'ROLE / CLASS  ' + (data['role'] or 'SAMPLE'), 22)
        write(x, y + 127, 'LOCATION  ' + (data['site'] or 'DEMO LOCATION'), 21)
        write(x, y + 165, data['department'] or 'NIGHTCODE / NETCON', 21)
        write(x, y + 203, f"DOB {data['dob'] or '--'}  HT {data['height'] or '--'}  EYES {data['eyes'] or '--'}", 18)
        write(x, y + 242, f"ISS {data['issued'] or '--'}   EXP {data['expires'] or '--'}", 18)
    else:
        x, y = (280, 240) if pixel else (245, 268)
        write(x, y, data['name'].upper(), 30, width=670, bold=True)
        write(x, y + 42, data['employee_id'], 24, width=670, bold=True)
        write(x, y + 80, data['department'] or 'NIGHTCODE / NETCON', 21, width=670)
        write(x, y + 114, 'DESIGNER  ' + (data['issuer'] or 'LOCAL STUDIO'), 20, width=670)
        write(x, y + 149, f"ISS {data['issued'] or '--'}   EXP {data['expires'] or '--'}", 18, width=670)
    if scale != 1:
        layer = layer.resize(SIZE, Image.Resampling.NEAREST)
    return Image.alpha_composite(image.convert('RGBA'), layer).convert('RGB')


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
        image = _nightcode_card(data, assets)
    elif template in NY_TEMPLATES:
        image = _ny_card(data, assets)
    else:
        with Image.open(assets / 'demo-state-gpt-v2.png') as source:
            image = source.convert('RGB').resize(SIZE, Image.Resampling.NEAREST)
        if data['photo'] and Path(data['photo']).is_file():
            try:
                with Image.open(data['photo']) as source:
                    portrait = ImageOps.fit(source.convert('RGB'), (264, 316),
                                            method=Image.Resampling.LANCZOS, centering=(0.5, 0.3))
                image.paste(portrait, (40, 168))
            except (OSError, ValueError):
                pass
        d = ImageDraw.Draw(image)
        _text(d, (35, 24), 'DEMO STATE', size=54, fill='#ffffff', bold=True)
        _text(d, (662, 47), 'ID DESIGN STUDY', size=24, fill='#e7eee9', bold=True)
        _text(d, (334, 168), 'NAME', size=19, fill='#50656a', bold=True)
        _text(d, (334, 198), data['name'].upper(), size=40, fill='#1d363f', bold=True, max_width=620)
        _text(d, (334, 274), 'DESIGN REFERENCE', size=19, fill='#50656a', bold=True)
        _text(d, (334, 304), data['employee_id'], size=30, fill='#1d363f', bold=True)
        _text(d, (334, 383), f"ISSUED {data['issued'] or '—'}", size=23, fill='#29434a')
        _text(d, (334, 425), f"EXPIRES {data['expires'] or '—'}", size=23, fill='#29434a')
        _text(d, (83, 558), 'SPECIMEN · NOT VALID FOR IDENTIFICATION',
              size=31, fill='#ffffff', bold=True)
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


def save_pair(record: dict, assets: Path, target: Path):
    """Export a New York specimen's front and back as two PDF pages."""
    if record.get('template') not in NY_TEMPLATES:
        raise ValueError('Choose a New York specimen template for a front/back export.')
    if target.suffix.lower() != '.pdf':
        raise ValueError('Front/back export requires a PDF filename.')
    front = render(dict(record, side='Front'), assets)
    back = render(dict(record, side='Back'), assets)
    front.save(target, 'PDF', resolution=300.0, save_all=True, append_images=[back])
