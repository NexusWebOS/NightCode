"""Install the approved SpriteCook exports and record their source asset IDs."""
import hashlib
import json
from pathlib import Path
import shutil
from PIL import Image

HERE = Path(__file__).resolve().parent
ASSETS = HERE / 'assets'
SOURCE = ASSETS / 'spritecook'
EXPORTS = {
    'disk-dude-mascot.png': ('disk-dude-mascot-final.png', '8591acad-3ead-4527-8f6b-d513d1dae398'),
    'disk-dude-logo.png': ('disk-dude-logo-v2.png', '4054cffc-4add-43f7-81d4-32eb224fc98f'),
    'disk-dude-banner.png': ('disk-dude-banner-v2.png', 'c4a3c64d-727c-4ff7-9884-56fd0dd8e67d'),
    'netcon-mascot.png': ('netcon-mascot-final.png', '2ce97b2a-a29f-4bd5-8869-5239d5ff3ba2'),
    'netcon-logo.png': ('netcon-logo-v2.png', 'b1d0767f-befa-4779-8223-721ffeefbcb5'),
    'netcon-banner.png': ('netcon-banner-v2.png', '0f5105ae-6560-44b0-a5f8-1e96c6f4fbe8'),
    'disc-icon.png': ('disc-icon.png', 'a55b6600-1ec6-4a89-b27b-eec903ce8b74'),
    'badge-icon.png': ('badge-icon.png', 'a17ae90a-f998-4f44-be65-683aeca4e871'),
    'folder-icon.png': ('folder-icon.png', 'fa178d09-11e4-4593-930d-d212a4189769'),
    'lock-icon.png': ('lock-icon.png', '301d4361-7828-4afc-8256-97d535f4f556'),
    'game-icon.png': ('game-icon.png', '4f558a05-400e-4865-bc2a-7d1253a9cc0c'),
}
KIT_ASSETS = {
    'disk-dude-ui-concept.png': 'fdf19415-2c30-4eda-aa10-b57d342d1551',
    'disk-dude-ui-sheet.png': '0d4d9ae2-9eec-400b-a975-b93b65806d43',
    'netcon-ui-concept.png': '6aec625b-7f20-487a-b0e8-d86fad7e74a1',
    'netcon-ui-sheet.png': '481a6068-a5dd-4d2b-b875-bf0066eca82c',
    'disk-button-frame.png': '9c8fedc2-7a30-4107-b386-36ce7856a9b0',
    'disk-cyan-panel.png': 'e8abefb5-d4f3-478a-a941-2ae046f3c6a9',
    'disk-burn-icon.png': '43f9b627-4e9f-4226-b014-f4fec62eac86',
    'netcon-tab-frame.png': '56e024b3-4a81-45eb-b3a3-05cd9f2f8bc8',
    'netcon-button-frame.png': 'c9b1479b-0f60-4b5a-a1f7-97f3e46d6d61',
    'netcon-card-panel.png': '8da927da-c2d0-4450-96d5-867250c0e5bf',
}

def record(path, asset_id):
    return {'asset_id': asset_id, 'sha12': hashlib.sha256(path.read_bytes()).hexdigest()[:12]}

def main():
    manifest = {
        'project_id': 'ff85dc4d-f21b-4a90-bba9-a39ac17cca1e',
        'ui_kits': {'disk-dude': '3f01ed6e-3ddd-4f8c-a75f-9ef985b89e14',
                    'netcon': '6b2daff6-b423-4866-9bec-aecc03733085'},
        'assets': {},
    }
    for name, (source, asset_id) in EXPORTS.items():
        target = ASSETS / name
        shutil.copyfile(SOURCE / source, target)
        manifest['assets'][name] = record(target, asset_id)
    for app, icon in [('disk-dude', 'disc-icon.png'), ('netcon', 'badge-icon.png')]:
        Image.open(ASSETS / icon).convert('RGBA').save(ASSETS / f'{app}.ico',
            sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    shutil.copyfile(SOURCE / 'disk-button-frame.png', SOURCE / 'disk-dude-button-frame.png')
    KIT_ASSETS['disk-dude-button-frame.png'] = KIT_ASSETS['disk-button-frame.png']
    for name, asset_id in KIT_ASSETS.items():
        manifest['assets'][f'spritecook/{name}'] = record(SOURCE / name, asset_id)
    (HERE / 'spritecook-assets.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Installed {len(EXPORTS)} SpriteCook exports and documented {len(manifest["assets"])} sources')

if __name__ == '__main__':
    main()
