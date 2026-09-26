"""Check the generated skin's real widget behavior and native cursor resources."""
import os
from pathlib import Path
import struct
import tkinter as tk
import unittest
from unittest.mock import patch

from netcon_skin import NetconButton, configure_netcon_style, cursor_for, render_header

ASSETS = Path(__file__).resolve().parent / 'assets'


class NetconSkinTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_cursor_hotspots_and_native_loading(self):
        files = list((ASSETS / 'netcon-kit' / 'cursors').glob('*.cur'))
        self.assertEqual(len(files), 12)
        for path in files:
            with self.subTest(cursor=path.name):
                data = path.read_bytes()
                self.assertEqual(struct.unpack_from('<HHH', data), (0, 2, 2))
                for index in range(2):
                    width, height, _, _, hx, hy, length, offset = struct.unpack_from('<BBBBHHII', data, 6 + 16 * index)
                    self.assertLess(hx, width)
                    self.assertLess(hy, height)
                    self.assertLessEqual(offset + length, len(data))
                if os.name == 'nt':
                    self.root.configure(cursor=cursor_for(ASSETS, path.stem))
                    self.assertIn('.cur', str(self.root.cget('cursor')))

    def test_button_states_preserve_native_commands(self):
        configure_netcon_style(self.root, ASSETS)
        invoked = []
        button = NetconButton(self.root, text='Export', command=lambda: invoked.append(True), asset_root=ASSETS)
        button._set_visual('_hover', True)
        self.assertEqual(str(button.cget('image')), str(button._images['hover']))
        button._set_visual('_pressed', True)
        self.assertEqual(str(button.cget('image')), str(button._images['pressed']))
        button.configure(state='disabled')
        self.assertEqual(str(button.cget('image')), str(button._images['disabled']))
        button.invoke()
        self.assertFalse(invoked)
        button.configure(state='normal')
        button.invoke()
        self.assertEqual(invoked, [True])

    def test_runtime_header_resizes(self):
        for width in (1124, 1244, 1564):
            self.assertEqual(render_header(ASSETS, width).size, (width, 228))


class NetconAppTests(unittest.TestCase):
    def test_complete_app_builds_and_new_york_editor_fits(self):
        from badge_editor import BadgeEditor
        from badge_templates import NY_TEMPLATES
        from netcon import Netcon
        with patch('netcon.load_data', return_value={'tags': [], 'locks': [], 'games': [], 'badges': []}):
            app = Netcon()
            app.withdraw()
            try:
                self.assertEqual(len(app.tabs.tabs()), 4)
                editor = next(child for child in app.badge.winfo_children() if isinstance(child, BadgeEditor))
                editor.values['template'].set(NY_TEMPLATES[0])
                editor._apply_template()
                editor.draw_preview()
                app.update_idletasks()
                self.assertEqual(editor.preview_error.cget('text'), '')
                self.assertLessEqual(app.winfo_reqheight(), 960)
                self.assertLessEqual(app.winfo_reqwidth(), 1280)
            finally:
                app.destroy()


if __name__ == '__main__':
    unittest.main()
