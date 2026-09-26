"""Netcon's local badge design and issuance workspace."""

from __future__ import annotations

from datetime import date, datetime
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from uuid import uuid4

from PIL import Image, ImageTk

from badge_templates import TEMPLATES, NY_TEMPLATES, is_specimen, render, save, save_pair, validate
from netcon_skin import BG, CYAN, EDGE, MUTED, PANEL, SILVER as TEXT


class BadgeEditor(ttk.Frame):
    def __init__(self, parent, data: dict, persist, assets: Path, button):
        super().__init__(parent)
        self.data, self.persist, self.assets, self.button = data, persist, assets, button
        self.data.setdefault('badges', [])
        self.current_uid = None
        self._preview_job = None
        self.values = {key: tk.StringVar() for key in
                       ('template', 'name', 'role', 'department', 'site', 'employee_id', 'issuer',
                        'issued', 'expires', 'photo', 'height', 'weight', 'eyes', 'hire_date', 'dob', 'side')}
        self.values['template'].set(TEMPLATES[0])
        self.values['side'].set('Front')
        self.values['issued'].set(date.today().isoformat())
        self._build()
        for var in self.values.values():
            var.trace_add('write', self._schedule_preview)
        self._apply_template()

    def _build(self):
        ttk.Label(self, text='BADGE STUDIO', font=('Consolas', 17, 'bold')).pack(anchor='w')
        ttk.Label(self, text='Create staff cards, NightCode character IDs, or a visibly nonvalid state ID design specimen.',
                  wraplength=950).pack(anchor='w', pady=(3, 12))
        body = ttk.Frame(self)
        body.pack(fill='both', expand=True)
        left_border = tk.Frame(body, bg=CYAN, padx=1, pady=1)
        left_border.pack(side='left', fill='both', expand=True, padx=(0, 14))
        left = ttk.Frame(left_border, style='Panel.TFrame', padding=11)
        left.pack(fill='both', expand=True)
        right_border = tk.Frame(body, bg=EDGE, padx=1, pady=1)
        right_border.pack(side='right', fill='both', expand=True)
        right = ttk.Frame(right_border, style='Panel.TFrame', padding=11)
        right.pack(fill='both', expand=True)

        row = ttk.Frame(left, style='Panel.TFrame'); row.pack(fill='x', pady=3)
        ttk.Label(row, text='Template', width=17, style='Panel.TLabel').pack(side='left')
        self.template_box = ttk.Combobox(row, textvariable=self.values['template'],
                                         values=TEMPLATES, state='readonly', width=28)
        self.template_box.pack(side='left', fill='x', expand=True)
        self.template_box.bind('<<ComboboxSelected>>', lambda _event: self._apply_template())
        fields = ttk.Frame(left, style='Panel.TFrame')
        fields.pack(fill='x', pady=(2, 0))
        fields.columnconfigure(0, weight=1)
        fields.columnconfigure(1, weight=1)
        self.field_labels = {}
        for index, (key, label) in enumerate([
                ('name', 'Cardholder name'), ('role', 'Role / title'),
                ('department', 'Department'), ('site', 'Site / node'),
                ('employee_id', 'Employee / card ID'), ('issuer', 'Issued by'),
                ('issued', 'Issue date'), ('expires', 'Expiry date')]):
            cell = ttk.Frame(fields, style='Panel.TFrame')
            cell.grid(row=index // 2, column=index % 2, sticky='ew', padx=(0, 6), pady=(1, 2))
            self.field_labels[key] = ttk.Label(cell, text=label, style='Panel.TLabel')
            self.field_labels[key].pack(anchor='w')
            ttk.Entry(cell, textvariable=self.values[key], width=22).pack(fill='x')

        self.ny_details = ttk.Frame(left, style='Panel.TFrame')
        for column, (key, label) in enumerate([
                ('dob', 'Birth date (YYYY-MM-DD)'), ('height', 'Height'), ('eyes', 'Eye color')]):
            self.ny_details.columnconfigure(column, weight=1)
            cell = ttk.Frame(self.ny_details, style='Panel.TFrame')
            cell.grid(row=0, column=column, sticky='ew', padx=(0, 5))
            ttk.Label(cell, text=label, style='Panel.TLabel').pack(anchor='w')
            ttk.Entry(cell, textvariable=self.values[key], width=15).pack(fill='x')

        self.aus_details = ttk.Frame(left, style='Panel.TFrame')
        self.aus_details.columnconfigure(0, weight=1)
        self.aus_details.columnconfigure(1, weight=1)
        for index, (key, label) in enumerate([
                ('height', 'Height'), ('eyes', 'Eye color'),
                ('weight', 'Weight'), ('hire_date', 'Date of hire')]):
            cell = ttk.Frame(self.aus_details, style='Panel.TFrame')
            cell.grid(row=index // 2, column=index % 2, sticky='ew', padx=(0, 6), pady=(1, 2))
            ttk.Label(cell, text=label, style='Panel.TLabel').pack(anchor='w')
            ttk.Entry(cell, textvariable=self.values[key], width=22).pack(fill='x')

        photo_row = ttk.Frame(left, style='Panel.TFrame'); photo_row.pack(fill='x', pady=(5, 2))
        self.button(photo_row, text='Choose photo…', command=self.choose_photo).pack(side='left')
        self.photo_label = ttk.Label(photo_row, text='No photo selected', wraplength=260, style='Panel.TLabel')
        self.photo_label.pack(side='left', padx=8)
        actions = ttk.Frame(left, style='Panel.TFrame'); actions.pack(fill='x', pady=(8, 5))
        self.button(actions, text='Save record', command=self.save_record).pack(side='left')
        self.button(actions, text='Export PNG / PDF…', command=self.export_badge).pack(side='left', padx=5)
        self.button(actions, text='New', command=self.new_record).pack(side='left')
        ttk.Label(left, text='LOCAL BADGE RECORDS', foreground=CYAN, style='Panel.TLabel').pack(anchor='w', pady=(6, 2))
        self.record_list = tk.Listbox(left, height=3, bg=PANEL, fg=TEXT,
                                      selectbackground='#275261', font=('Consolas', 9), border=0)
        self.record_list.pack(fill='both', expand=True)
        self.record_list.bind('<<ListboxSelect>>', self.load_selected)
        self._refresh_list()

        ttk.Label(right, text='◈  300 DPI CARD PREVIEW', foreground=CYAN, style='Panel.TLabel').pack(anchor='w')
        side_row = ttk.Frame(right, style='Panel.TFrame')
        side_row.pack(fill='x', pady=(7, 3))
        ttk.Label(side_row, text='View', style='Panel.TLabel').pack(side='left', padx=(0, 8))
        self.side_box = ttk.Combobox(side_row, textvariable=self.values['side'],
                                    values=('Front', 'Back'), width=9, state='disabled')
        self.side_box.pack(side='left')
        self.preview = tk.Label(right, bg=PANEL)
        self.preview.pack(anchor='w', pady=(5, 7))
        self.pair_row = ttk.Frame(right, style='Panel.TFrame')
        self.button(self.pair_row, text='Export front + back PDF…', command=self.export_pair).pack(side='left')
        self.preview_error = ttk.Label(right, text='', wraplength=455, foreground='#f1ac83', style='Panel.TLabel')
        self.preview_error.pack(anchor='w')
        self.note = ttk.Label(right, text='', wraplength=455, style='Panel.TLabel')
        self.note.pack(anchor='w')

    def _record(self):
        return {key: var.get() for key, var in self.values.items()}

    def _schedule_preview(self, *_):
        if self._preview_job:
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(100, self.draw_preview)

    def draw_preview(self):
        self._preview_job = None
        record = self._record()
        record['name'] = record['name'] or 'YOUR NAME'
        record['employee_id'] = record['employee_id'] or '0000'
        try:
            image = render(record, self.assets)
            image.thumbnail((468, 294), Image.Resampling.NEAREST
                            if record['template'] == NY_TEMPLATES[0] else Image.Resampling.LANCZOS)
            self.preview_image = ImageTk.PhotoImage(image)
            self.preview.configure(image=self.preview_image)
            self.preview_error.configure(text='')
        except (ValueError, OSError) as exc:
            self.preview.configure(image='')
            self.preview_error.configure(text=str(exc))

    def _apply_template(self, reset_fields=True):
        choice = self.values['template'].get()
        ny = choice in NY_TEMPLATES
        if choice == 'Allied Universal staff':
            self.aus_details.pack(fill='x', pady=(2, 0), after=self.aus_details.master.winfo_children()[1])
        else:
            self.aus_details.pack_forget()
        if ny:
            self.ny_details.pack(fill='x', pady=(3, 0), after=self.ny_details.master.winfo_children()[1])
            self.side_box.configure(state='readonly')
            self.pair_row.pack(anchor='w', pady=(3, 8), before=self.preview_error)
        else:
            self.ny_details.pack_forget()
            self.pair_row.pack_forget()
            self.side_box.configure(state='disabled')
            self.values['side'].set('Front')
        if reset_fields or not self.values['side'].get():
            self.values['side'].set('Front')
        for key, label in {
            'role': 'Role / class' if ny else 'Role / title',
            'department': 'Collection' if ny else 'Department',
            'site': 'Fictional location' if ny else 'Site / node',
            'employee_id': 'Specimen reference' if ny else 'Employee / card ID',
            'issuer': 'Designer' if ny else 'Issued by',
        }.items():
            self.field_labels[key].configure(text=label)
        defaults = {
            'NightCode in-world': ('OPERATIVE', 'FIELD', 'LOCAL NODE', 'NC-0001'),
            'Allied Universal staff': ('Security Professional', 'Security', '', ''),
            'State ID specimen': ('', '', '', 'DEMO-0000'),
            NY_TEMPLATES[0]: ('GAME', 'NIGHTCODE / NETCON', 'DEMO LOCATION', 'DEMO-NY-0000'),
            NY_TEMPLATES[1]: ('SAMPLE', 'NIGHTCODE / NETCON', 'DEMO LOCATION', 'DEMO-NY-0000'),
        }
        role, department, site, card_id = defaults[choice]
        if reset_fields:
            for key, value in [('role', role), ('department', department), ('site', site), ('employee_id', card_id)]:
                self.values[key].set(value)
        self.note.configure(text={
            'NightCode in-world': 'Fictional NightCode identity card for your in-world roster.',
            'Allied Universal staff': 'Work badge design. Your employer or site must approve issuance and activate any access system.',
            'State ID specimen': 'Design specimen only. Uses DEMO STATE and prominent SPECIMEN markings; never valid identification.',
            NY_TEMPLATES[0]: 'New York design specimen with editable fields and pixel-art portraits. Switch sides or export a two-page PDF. Permanent specimen markings appear on both sides.',
            NY_TEMPLATES[1]: 'New York design specimen with formal typography and grayscale portraits. Switch sides or export a two-page PDF. Permanent specimen markings appear on both sides.',
        }[choice])
        self._schedule_preview()

    def choose_photo(self):
        path = filedialog.askopenfilename(filetypes=[('Images', '*.png *.jpg *.jpeg *.webp *.bmp')])
        if path:
            try:
                with Image.open(path) as image:
                    image.verify()
            except (OSError, ValueError):
                return messagebox.showerror('Netcon', 'The selected photo could not be opened.')
            self.values['photo'].set(path)
            self.photo_label.configure(text=Path(path).name)

    def save_record(self):
        try:
            record = validate(self._record())
        except ValueError as exc:
            return messagebox.showerror('Netcon', str(exc))
        if not is_specimen(record['template']):
            duplicate = next((item for item in self.data['badges']
                              if item.get('template') == record['template']
                              and item.get('employee_id', '').casefold() == record['employee_id'].casefold()
                              and item.get('uid') != self.current_uid), None)
            if duplicate:
                return messagebox.showerror('Netcon', 'This ID already exists in that template.')
        uid = self.current_uid or uuid4().hex
        if record['photo'] and Path(record['photo']).is_file():
            destination = Path(os.getenv('LOCALAPPDATA', str(Path.home()))) / 'RetroTools' / 'badge-photos'
            destination.mkdir(parents=True, exist_ok=True)
            target = destination / f'{uid}.png'
            try:
                with Image.open(record['photo']) as src:
                    src.convert('RGB').save(target, 'PNG')
                record['photo'] = str(target)
                self.values['photo'].set(str(target))
            except OSError as exc:
                return messagebox.showerror('Netcon', f'Could not save photo: {exc}')
        record.update(uid=uid, updated_at=datetime.now().isoformat(timespec='seconds'))
        existing = next((i for i, item in enumerate(self.data['badges']) if item.get('uid') == uid), None)
        if existing is None:
            self.data['badges'].append(record)
        else:
            self.data['badges'][existing] = record
        self.persist(self.data)
        self.current_uid = uid
        self._refresh_list()
        messagebox.showinfo('Netcon', 'Badge record saved locally.')

    def export_badge(self):
        try:
            image = render(self._record(), self.assets)
        except (ValueError, OSError) as exc:
            return messagebox.showerror('Netcon', str(exc))
        target = filedialog.asksaveasfilename(defaultextension='.png',
                    filetypes=[('PNG image', '*.png'), ('PDF card', '*.pdf')])
        if not target:
            return
        try:
            save(image, Path(target))
        except OSError as exc:
            return messagebox.showerror('Netcon', f'Export failed: {exc}')
        messagebox.showinfo('Netcon', f'Card exported: {target}')

    def export_pair(self):
        try:
            record = validate(self._record())
        except ValueError as exc:
            return messagebox.showerror('Netcon', str(exc))
        target = filedialog.asksaveasfilename(defaultextension='.pdf',
                    filetypes=[('Front and back PDF', '*.pdf')])
        if not target:
            return
        try:
            save_pair(record, self.assets, Path(target))
        except (OSError, ValueError) as exc:
            return messagebox.showerror('Netcon', f'Export failed: {exc}')
        messagebox.showinfo('Netcon', f'Front and back exported as two PDF pages: {target}')

    def new_record(self):
        self.current_uid = None
        for key in ('name', 'photo', 'expires', 'issuer', 'height', 'weight', 'eyes', 'hire_date', 'dob'):
            self.values[key].set('')
        self.values['issued'].set(date.today().isoformat())
        self.photo_label.configure(text='No photo selected')
        self._apply_template()
        self.record_list.selection_clear(0, 'end')

    def _refresh_list(self):
        self.record_list.delete(0, 'end')
        for item in self.data['badges']:
            self.record_list.insert('end', f"{item['template']}  |  {item['name']}  |  {item['employee_id']}")

    def load_selected(self, _event=None):
        selection = self.record_list.curselection()
        if not selection:
            return
        record = self.data['badges'][selection[0]]
        self.current_uid = record.get('uid')
        for key, var in self.values.items():
            var.set(record.get(key, ''))
        self._apply_template(reset_fields=False)
        self.photo_label.configure(text=Path(record.get('photo') or '').name or 'No photo selected')
        self._schedule_preview()
