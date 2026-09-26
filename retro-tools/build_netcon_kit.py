"""Slice GPT-generated atlases and package them as UI textures and Windows cursors.

This script crops and resizes supplied artwork; it does not draw replacement art.
"""
from pathlib import Path
import json
import struct

from PIL import Image

ASSETS = Path(__file__).resolve().parent / 'assets'
KIT = ASSETS / 'netcon-kit'
CURSORS = (
    ('pointer', (0.13, 0.04)), ('link', (0.33, 0.035)),
    ('text', (0.5, 0.5)), ('crosshair', (0.5, 0.5)),
    ('move', (0.5, 0.5)), ('resize-ew', (0.5, 0.5)),
    ('resize-ns', (0.5, 0.5)), ('resize-nwse', (0.5, 0.5)),
    ('resize-nesw', (0.5, 0.5)), ('busy', (0.5, 0.5)),
    ('unavailable', (0.5, 0.5)), ('help', (0.075, 0.06)),
)


def trim(sprite):
    # Ignore low-alpha glow when finding bounds, preserving all alpha inside them.
    box = sprite.getchannel('A').point(lambda a: 255 if a > 100 else 0).getbbox()
    if not box:
        raise ValueError('An atlas cell contains no sprite.')
    return sprite.crop(box), box


def cursor_image(sprite, size):
    scale = (size - 4) / max(sprite.size)
    image = sprite.resize((max(1, round(sprite.width * scale)),
                           max(1, round(sprite.height * scale))), Image.Resampling.NEAREST)
    result = Image.new('RGBA', (size, size))
    offset = ((size - image.width) // 2, (size - image.height) // 2)
    result.alpha_composite(image, offset)
    return result, offset, image.size


def write_cur(target, entries):
    """Write standard BGRA/DIB cursor resources with alpha and an AND mask."""
    resources = []
    for image, hotspot in entries:
        width, height = image.size
        pixels = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes('raw', 'BGRA')
        stride = ((width + 31) // 32) * 4
        mask = bytearray(stride * height)
        alpha = image.getchannel('A')
        for y in range(height):
            for x in range(width):
                if alpha.getpixel((x, height - y - 1)) == 0:
                    mask[y * stride + x // 8] |= 128 >> (x % 8)
        header = struct.pack('<IiiHHIIiiII', 40, width, height * 2, 1, 32, 0,
                             len(pixels) + len(mask), 0, 0, 0, 0)
        resources.append((image.size, hotspot, header + pixels + mask))
    offset = 6 + 16 * len(resources)
    directory = bytearray(struct.pack('<HHH', 0, 2, len(resources)))
    for (width, height), (hx, hy), payload in resources:
        directory.extend(struct.pack('<BBBBHHII', width, height, 0, 0, hx, hy, len(payload), offset))
        offset += len(payload)
    target.write_bytes(bytes(directory) + b''.join(item[2] for item in resources))


def main():
    for folder in ('frames', 'buttons', 'cursors'):
        (KIT / folder).mkdir(parents=True, exist_ok=True)
    metadata = {'source': 'GPT image generation', 'frames': {}, 'buttons': {}, 'cursors': {}}
    with Image.open(ASSETS / 'netcon-frames-gpt-v3.png') as source:
        atlas = source.convert('RGBA')
    for index, name in enumerate(('standard', 'focused', 'inactive', 'dialog')):
        col, row = index % 2, index // 2
        box = (col * atlas.width // 2, row * atlas.height // 2,
               (col + 1) * atlas.width // 2, (row + 1) * atlas.height // 2)
        sprite, bounds = trim(atlas.crop(box))
        sprite.resize((192, 120), Image.Resampling.NEAREST).save(KIT / 'frames' / (name + '.png'))
        metadata['frames'][name] = {'atlas_cell': box, 'trim': bounds, 'size': [192, 120],
                                    'nine_slice': [30, 30, 30, 30], 'content_padding': 22}
    with Image.open(ASSETS / 'netcon-buttons-gpt-v3.png') as source:
        atlas = source.convert('RGBA')
    # Generated rows have generous gutters but are not exactly equal-height cells.
    bands = ((0, 65, 1240, 339), (0, 340, 1240, 622),
             (0, 627, 1240, 908), (0, 914, 1240, 1190))
    if atlas.size != (1240, 1269):
        raise ValueError('Button source changed; review and update the atlas bounds.')
    for name, box in zip(('normal', 'hover', 'pressed', 'disabled'), bands):
        sprite, bounds = trim(atlas.crop(box))
        sprite.resize((220, 48), Image.Resampling.NEAREST).save(KIT / 'buttons' / (name + '.png'))
        metadata['buttons'][name] = {'atlas_cell': box, 'trim': bounds, 'size': [220, 48],
                                     'nine_slice': [16, 16, 16, 16]}
    with Image.open(ASSETS / 'netcon-cursors-gpt-v3.png') as source:
        atlas = source.convert('RGBA')
    for index, (name, hot) in enumerate(CURSORS):
        col, row = index % 4, index // 4
        box = (col * atlas.width // 4, row * atlas.height // 3,
               (col + 1) * atlas.width // 4, (row + 1) * atlas.height // 3)
        sprite, bounds = trim(atlas.crop(box))
        entries, hotspots = [], {}
        for size in (32, 48):
            image, offset, dimensions = cursor_image(sprite, size)
            hotspot = (offset[0] + round(hot[0] * (dimensions[0] - 1)),
                       offset[1] + round(hot[1] * (dimensions[1] - 1)))
            image.save(KIT / 'cursors' / f'{name}-{size}.png')
            entries.append((image, hotspot))
            hotspots[str(size)] = hotspot
        write_cur(KIT / 'cursors' / (name + '.cur'), entries)
        metadata['cursors'][name] = {'atlas_cell': box, 'trim': bounds, 'hotspots': hotspots}
    (KIT / 'manifest.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print('Exported 4 panel frames, 4 button states, 24 cursor PNGs, and 12 Windows cursors.')


if __name__ == '__main__':
    main()
