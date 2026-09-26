"""Regression checks for editable front/back specimen records and exports."""
from pathlib import Path
from contextlib import contextmanager
import tkinter as tk
import unittest
from unittest.mock import patch
from uuid import uuid4

from PIL import Image, ImageChops, PdfParser

from badge_editor import BadgeEditor
from badge_templates import NY_TEMPLATES, TEMPLATES, SIZE, render, save_pair, validate

ASSETS = Path(__file__).parent / 'assets'


@contextmanager
def test_workspace():
    # Normal inherited Windows permissions also work under a restricted test runner.
    root = Path(__file__).resolve().parent
    directory = root / ('.badge-test-' + uuid4().hex)
    directory.mkdir()
    try:
        yield directory
    finally:
        assert directory.resolve().parent == root
        for item in directory.iterdir():
            item.unlink()
        directory.rmdir()


def record(template=NY_TEMPLATES[0], **changes):
    result = dict(template=template, name='Alex Rivers', employee_id='0042',
                  role='SAMPLE', department='NightCode', site='Demo Location',
                  issuer='Local Studio', issued='2026-09-26', expires='2027-09-26',
                  dob='1990-01-01', height='5 ft 6', eyes='BRN')
    result.update(changes)
    return result


class BadgeExportTests(unittest.TestCase):
    def test_existing_templates_accept_records_without_new_fields(self):
        for template in TEMPLATES:
            with self.subTest(template=template):
                self.assertEqual(render(record(template), ASSETS).size, SIZE)

    def test_fields_change_both_sides_and_preserve_footer(self):
        for template in NY_TEMPLATES:
            for side in ('Front', 'Back'):
                with self.subTest(template=template, side=side):
                    first = render(record(template, side=side), ASSETS)
                    second = render(record(template, side=side, name='Jordan Vale'), ASSETS)
                    self.assertIsNotNone(ImageChops.difference(first, second).getbbox())
                    self.assertIsNone(ImageChops.difference(
                        first.crop((0, 585, 1012, 638)), second.crop((0, 585, 1012, 638))).getbbox())

    def test_portrait_updates_both_sides_without_touching_warning_banner(self):
        with test_workspace() as directory:
            photo = Path(directory) / 'portrait.png'
            Image.new('RGB', (300, 420), '#567c8a').save(photo)
            for template in NY_TEMPLATES:
                for side in ('Front', 'Back'):
                    blank = render(record(template, side=side), ASSETS)
                    filled = render(record(template, side=side, photo=str(photo)), ASSETS)
                    self.assertIsNotNone(ImageChops.difference(blank, filled).getbbox())
                    self.assertIsNone(ImageChops.difference(
                        blank.crop((0, 585, 1012, 638)), filled.crop((0, 585, 1012, 638))).getbbox())

    def test_pdf_contains_front_and_back_pages(self):
        with test_workspace() as directory:
            target = Path(directory) / 'pair.pdf'
            for template in NY_TEMPLATES:
                save_pair(record(template, side='Back'), ASSETS, target)
                with PdfParser.PdfParser(filename=str(target)) as pdf:
                    self.assertEqual(len(pdf.pages), 2)
            with self.assertRaises(ValueError):
                save_pair(record(), ASSETS, target.with_suffix('.png'))

    def test_reference_and_dates_are_validated(self):
        saved = validate(record())
        self.assertEqual(saved['employee_id'], 'DEMO-NY-0042')
        self.assertEqual(validate(saved)['employee_id'], 'DEMO-NY-0042')
        with self.assertRaises(ValueError):
            validate(record(dob='not-a-date'))
        with self.assertRaises(ValueError):
            validate(record(expires='2025-01-01'))
        with self.assertRaises(ValueError):
            validate(record(side='Other'))


class BadgeEditorTests(unittest.TestCase):
    def setUp(self):
        self.error_dialog = patch('badge_editor.messagebox.showerror',
                                  side_effect=lambda title, message: self.fail(f'{title}: {message}'))
        self.error_dialog.start()
        self.addCleanup(self.error_dialog.stop)
        self.root = tk.Tk()
        self.root.withdraw()
        self.data = {'badges': []}
        self.persisted = []
        self.editor = BadgeEditor(self.root, self.data, self.persisted.append, ASSETS, tk.Button)

    def tearDown(self):
        self.root.destroy()

    def test_saved_back_view_restores_fields_and_exports(self):
        editor = self.editor
        editor.values['template'].set(NY_TEMPLATES[1])
        editor._apply_template()
        for key, value in record(NY_TEMPLATES[1], side='Back', role='Custom role').items():
            editor.values[key].set(value)
        with patch('badge_editor.messagebox.showinfo'):
            editor.save_record()
        self.assertEqual(len(self.persisted), 1)
        editor.new_record()
        editor.record_list.selection_set(0)
        editor.load_selected()
        self.assertEqual(editor.values['role'].get(), 'Custom role')
        self.assertEqual(editor.values['side'].get(), 'Back')
        self.assertEqual(str(editor.side_box.cget('state')), 'readonly')
        editor.draw_preview()
        self.assertEqual(editor.preview_error.cget('text'), '')
        with test_workspace() as directory:
            target = Path(directory) / 'editor.pdf'
            with patch('badge_editor.filedialog.asksaveasfilename', return_value=str(target)), \
                    patch('badge_editor.messagebox.showinfo'):
                editor.export_pair()
            with PdfParser.PdfParser(filename=str(target)) as pdf:
                self.assertEqual(len(pdf.pages), 2)
        editor.values['template'].set(TEMPLATES[0])
        editor._apply_template()
        self.assertEqual(editor.values['side'].get(), 'Front')
        self.assertEqual(str(editor.side_box.cget('state')), 'disabled')


if __name__ == '__main__':
    unittest.main()
