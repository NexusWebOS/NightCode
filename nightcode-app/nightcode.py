"""NightCode: DOS-flavored file workstation with a real embedded web browser."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import shlex
import sys
import urllib.parse

from PySide6.QtCore import QDir, QObject, Qt, QUrl, Signal
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFileDialog, QFileSystemModel,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QSplitter, QTabWidget, QTreeView, QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView

from operations import copy_items, download_url, duplicate_items, github_download, github_upload, supabase_upload


STYLE = """
QWidget { background:#061326; color:#bdefff; font: 11pt Consolas; }
QMainWindow, QDialog { background:#030b1a; }
QLabel#masthead { color:#43eaff; font: bold 25pt Consolas; padding:6px; }
QLabel#subtitle { color:#9b7df4; font: bold 10pt Consolas; }
QPushButton { color:#c7f8ff; background:#0d2743; border:1px solid #3194b9;
              padding:7px 10px; }
QPushButton:hover { background:#174465; border-color:#54e9ff; }
QPushButton:pressed { background:#285d7d; }
QLineEdit, QPlainTextEdit, QTreeView { background:#05101f; color:#d7f7ff;
              border:1px solid #245475; selection-background-color:#1b6689; }
QLineEdit { padding:6px; }
QTreeView { alternate-background-color:#091b31; }
QHeaderView::section { background:#102944; color:#42dcf1; padding:5px; border:0; }
QTabWidget::pane { border:1px solid #2e6685; }
QTabBar::tab { background:#0a1d32; color:#85b8cd; padding:8px 16px;
               border:1px solid #245475; }
QTabBar::tab:selected { background:#15334d; color:#62efff; }
QStatusBar { color:#71ddeb; border-top:1px solid #216285; }
QSplitter::handle { background:#174c69; }
"""


class JobSignals(QObject):
    done = Signal(str)
    failed = Signal(str)


class BrowserView(QWebEngineView):
    def __init__(self, owner: 'NightCode'):
        super().__init__()
        self.owner = owner

    def createWindow(self, _kind):
        return self.owner.new_browser_tab()


class FieldsDialog(QDialog):
    def __init__(self, parent, title: str, fields: list[tuple[str, str, bool]]):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.entries = {}
        for key, label, secret in fields:
            entry = QLineEdit()
            if secret:
                entry.setEchoMode(QLineEdit.EchoMode.Password)
            form.addRow(label, entry)
            self.entries[key] = entry
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict[str, str]:
        return {key: entry.text().strip() for key, entry in self.entries.items()}


class NightCode(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('NIGHTCODE // FILE SYSTEM & NETWORK')
        self.resize(1380, 900)
        self.setMinimumSize(1030, 680)
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='nightcode')
        self.jobs = []
        self.current_dir = Path.home().resolve()
        self._build()
        self.show_directory(self.current_dir)
        self.log('SYSTEM READY  •  FILE OPERATIONS LOCAL  •  WEB ENGINE ONLINE')

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 8, 12, 8)
        title = QHBoxLayout()
        brand = QLabel('☠ NIGHTCODE')
        brand.setObjectName('masthead')
        title.addWidget(brand)
        title.addWidget(QLabel('NC:/  DATA TRANSFER / DUPLICATOR / WEB', objectName='subtitle'))
        title.addStretch()
        title.addWidget(QLabel('● LOCAL NODE', objectName='subtitle'))
        layout.addLayout(title)

        controls = QHBoxLayout()
        self.path_entry = QLineEdit()
        self.path_entry.returnPressed.connect(lambda: self.show_directory(Path(self.path_entry.text())))
        controls.addWidget(QLabel('PATH>'))
        controls.addWidget(self.path_entry, 1)
        for label, handler in [('UP', self.up_directory), ('FOLDER…', self.choose_directory),
                               ('COPY TO…', self.copy_selected), ('DUPLICATE', self.duplicate_selected),
                               ('DOWNLOAD URL', self.download_dialog), ('GITHUB ↓', self.github_download_dialog),
                               ('GITHUB ↑', self.github_dialog),
                               ('SUPABASE ↑', self.supabase_dialog)]:
            button = QPushButton(label)
            button.clicked.connect(handler)
            controls.addWidget(button)
        layout.addLayout(controls)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        explorer = QWidget()
        explore_layout = QHBoxLayout(explorer)
        explore_layout.setContentsMargins(4, 4, 4, 4)
        split = QSplitter(Qt.Orientation.Horizontal)
        explore_layout.addWidget(split)
        self.model = QFileSystemModel(self)
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)
        self.model.setRootPath(str(self.current_dir))
        self.files = QTreeView()
        self.files.setModel(self.model)
        self.files.setAlternatingRowColors(True)
        self.files.setSortingEnabled(True)
        self.files.setColumnWidth(0, 340)
        self.files.doubleClicked.connect(self.open_index)
        self.files.selectionModel().selectionChanged.connect(lambda *_: self.preview_selection())
        split.addWidget(self.files)
        self.viewer = QPlainTextEdit()
        self.viewer.setReadOnly(True)
        self.viewer.setPlainText('SELECT A FILE TO PREVIEW\n\nText, image and binary headers appear here.')
        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setMinimumWidth(330)
        self.image_preview.hide()
        viewer_panel = QWidget()
        viewer_layout = QVBoxLayout(viewer_panel)
        viewer_layout.addWidget(QLabel('▣ WINDOW VIEWER  /  FILE PREVIEW', objectName='subtitle'))
        viewer_layout.addWidget(self.viewer, 1)
        viewer_layout.addWidget(self.image_preview, 1)
        split.addWidget(viewer_panel)
        split.setSizes([760, 500])
        self.tabs.addTab(explorer, '▣ FILES / VIEWER')

        browser_page = QWidget()
        web_layout = QVBoxLayout(browser_page)
        nav = QHBoxLayout()
        for label, handler in [('←', lambda: self.browser().back()),
                               ('→', lambda: self.browser().forward()),
                               ('⟳', lambda: self.browser().reload()),
                               ('HOME', lambda: self.navigate('https://example.com'))]:
            button = QPushButton(label)
            button.clicked.connect(handler)
            nav.addWidget(button)
        self.address = QLineEdit()
        self.address.setPlaceholderText('https://example.com  or enter a search')
        self.address.returnPressed.connect(lambda: self.navigate(self.address.text()))
        nav.addWidget(self.address, 1)
        go = QPushButton('GO ONLINE →')
        go.clicked.connect(lambda: self.navigate(self.address.text()))
        nav.addWidget(go)
        web_layout.addLayout(nav)
        self.web_tabs = QTabWidget()
        self.web_tabs.setTabsClosable(True)
        self.web_tabs.tabCloseRequested.connect(self.close_browser_tab)
        self.web_tabs.currentChanged.connect(lambda _index: self.address.setText(
            self.browser().url().toString() if self.browser() else ''))
        web_layout.addWidget(self.web_tabs, 1)
        self.tabs.addTab(browser_page, '◎ INTERNET BROWSER')
        self.new_browser_tab().setHtml('<html style="background:#071629;color:#54eaff;font:20px monospace"><body><h1>NIGHTCODE // WEB</h1><p>Type an address above to open a live page.</p></body></html>')
        QWebEngineProfile.defaultProfile().downloadRequested.connect(self.browser_download)

        console = QWidget()
        console_layout = QVBoxLayout(console)
        console_layout.setContentsMargins(0, 0, 0, 0)
        console_layout.addWidget(QLabel('▣ NC:\\> COMMAND SHELL     HELP  DIR  CD  COPY  DUP  VIEW  WEB  DOWNLOAD  CLS', objectName='subtitle'))
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(500)
        self.output.setFixedHeight(145)
        console_layout.addWidget(self.output)
        command_row = QHBoxLayout()
        command_row.addWidget(QLabel('NC:\\>'))
        self.command = QLineEdit()
        self.command.returnPressed.connect(self.execute_command)
        command_row.addWidget(self.command)
        console_layout.addLayout(command_row)
        layout.addWidget(console)
        self.statusBar().showMessage('READY  |  Select a file or open the browser')

    def log(self, message: str):
        stamp = datetime.now().strftime('%H:%M:%S')
        self.output.appendPlainText(f'[{stamp}] {message}')
        self.statusBar().showMessage(message, 8000)

    def submit(self, label: str, action):
        signals = JobSignals(self)
        self.jobs.append(signals)
        signals.done.connect(lambda result: self._job_end(signals, f'{label}: {result}'))
        signals.failed.connect(lambda error: self._job_end(signals, f'{label} FAILED: {error}', True))
        self.log(f'{label} STARTED…')
        future = self.executor.submit(action)
        def finished(task):
            try:
                signals.done.emit(str(task.result()))
            except Exception as exc:
                signals.failed.emit(str(exc))
        future.add_done_callback(finished)

    def _job_end(self, signals, message: str, failed=False):
        self.log(message)
        if signals in self.jobs:
            self.jobs.remove(signals)
        if failed:
            QMessageBox.warning(self, 'NightCode', message)

    def show_directory(self, path: Path):
        try:
            path = path.expanduser().resolve(strict=True)
            if not path.is_dir():
                raise NotADirectoryError(path)
        except (OSError, ValueError) as exc:
            self.log(f'PATH ERROR: {exc}')
            return
        self.current_dir = path
        self.path_entry.setText(str(path))
        self.files.setRootIndex(self.model.setRootPath(str(path)))
        self.log(f'DIR {path}')

    def up_directory(self):
        self.show_directory(self.current_dir.parent)

    def choose_directory(self):
        selected = QFileDialog.getExistingDirectory(self, 'Open folder', str(self.current_dir))
        if selected:
            self.show_directory(Path(selected))

    def selected_paths(self) -> list[Path]:
        indexes = self.files.selectionModel().selectedRows(0)
        return [Path(self.model.filePath(index)) for index in indexes]

    def _one_file(self) -> Path | None:
        paths = self.selected_paths()
        if len(paths) != 1 or not paths[0].is_file():
            QMessageBox.information(self, 'NightCode', 'Select one file in the file viewer first.')
            return None
        return paths[0]

    def copy_selected(self):
        paths = self.selected_paths()
        if not paths:
            return self.log('COPY: SELECT FILES OR FOLDERS FIRST')
        folder = QFileDialog.getExistingDirectory(self, 'Copy to folder', str(self.current_dir))
        if folder:
            self.submit('COPY', lambda: ', '.join(map(str, copy_items(paths, Path(folder)))))

    def duplicate_selected(self):
        paths = self.selected_paths()
        if not paths:
            return self.log('DUP: SELECT FILES OR FOLDERS FIRST')
        self.submit('DUPLICATE', lambda: ', '.join(map(str, duplicate_items(paths))))

    def open_index(self, index):
        path = Path(self.model.filePath(index))
        if path.is_dir():
            self.show_directory(path)
        else:
            self.preview(path)

    def preview_selection(self):
        paths = self.selected_paths()
        if len(paths) == 1:
            self.preview(paths[0])

    def preview(self, path: Path):
        self.tabs.setCurrentIndex(0)
        self.image_preview.hide()
        self.viewer.show()
        if path.is_dir():
            self.viewer.setPlainText(f'DIRECTORY  {path}\n\nDouble-click to enter.')
            return
        info = f'FILE  {path.name}\nSIZE  {path.stat().st_size:,} bytes\nPATH  {path}\n' + '─' * 45 + '\n'
        if path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'):
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                self.viewer.hide()
                self.image_preview.setPixmap(pixmap.scaled(520, 520, Qt.AspectRatioMode.KeepAspectRatio,
                                                            Qt.TransformationMode.SmoothTransformation))
                self.image_preview.show()
                self.log(f'VIEW IMAGE {path.name}  {pixmap.width()}×{pixmap.height()}')
                return
        try:
            data = path.open('rb').read(256 * 1024)
            text = data.decode('utf-8-sig')
            if '\x00' in text:
                raise UnicodeError('binary')
            self.viewer.setPlainText(info + text + ('\n\n[PREVIEW TRUNCATED]' if path.stat().st_size > len(data) else ''))
        except UnicodeError:
            data = path.open('rb').read(4096)
            rows = [f'{offset:08X}  {data[offset:offset+16].hex(" ")}' for offset in range(0, len(data), 16)]
            self.viewer.setPlainText(info + '\n'.join(rows) + '\n\n[HEX HEADER: FIRST 4 KiB]')
        except OSError as exc:
            self.viewer.setPlainText(info + f'PREVIEW ERROR: {exc}')

    def browser(self) -> BrowserView:
        return self.web_tabs.currentWidget()

    def new_browser_tab(self) -> BrowserView:
        view = BrowserView(self)
        index = self.web_tabs.addTab(view, 'NEW TAB')
        self.web_tabs.setCurrentIndex(index)
        view.urlChanged.connect(lambda url, v=view: self._url_changed(v, url))
        view.titleChanged.connect(lambda title, v=view: self.web_tabs.setTabText(self.web_tabs.indexOf(v), (title or 'WEB')[:22]))
        view.loadFinished.connect(lambda ok, v=view: self.log(f'WEB {"LOADED" if ok else "FAILED"}: {v.url().toString()}'))
        return view

    def close_browser_tab(self, index: int):
        if self.web_tabs.count() <= 1:
            self.web_tabs.widget(index).setHtml('<html style="background:#071629;color:#54eaff;font:20px monospace"><body><h1>NIGHTCODE // WEB</h1></body></html>')
        else:
            widget = self.web_tabs.widget(index)
            self.web_tabs.removeTab(index)
            widget.deleteLater()

    def _url_changed(self, view, url):
        if view is self.browser():
            self.address.setText(url.toString())

    def navigate(self, value: str):
        value = value.strip()
        if not value:
            return
        if ' ' in value and '://' not in value:
            url = QUrl('https://www.google.com/search?q=' + urllib.parse.quote_plus(value))
        else:
            url = QUrl.fromUserInput(value)
        if url.scheme() not in ('http', 'https'):
            self.log('WEB: ONLY HTTP/HTTPS ADDRESSES ARE SUPPORTED')
            return
        self.tabs.setCurrentIndex(1)
        self.browser().load(url)

    def browser_download(self, download: QWebEngineDownloadRequest):
        name = Path(download.suggestedFileName()).name or 'download'
        target, _ = QFileDialog.getSaveFileName(self, 'Save browser download', str(self.current_dir / name))
        if not target:
            download.cancel()
            return
        destination = Path(target)
        download.setDownloadDirectory(str(destination.parent))
        download.setDownloadFileName(destination.name)
        download.stateChanged.connect(lambda state, d=download: self.log(
            f'BROWSER DOWNLOAD {state.name}: {d.downloadFileName()}'))
        download.accept()
        self.log(f'BROWSER DOWNLOAD STARTED: {destination}')

    def download_dialog(self):
        dialog = FieldsDialog(self, 'Download URL', [('url', 'HTTP(S) URL', False),
                                                      ('token', 'Bearer token (optional)', True)])
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        folder = QFileDialog.getExistingDirectory(self, 'Download into folder', str(self.current_dir))
        if folder:
            self.submit('DOWNLOAD', lambda: download_url(values['url'], Path(folder), values['token']))

    def github_dialog(self):
        source = self._one_file()
        if source is None:
            return
        dialog = FieldsDialog(self, 'Upload file to GitHub', [
            ('repo', 'Repository OWNER/REPO', False), ('path', 'Path in repository', False),
            ('token', 'GitHub token', True)])
        dialog.entries['repo'].setText('NexusWebOS/NightCode')
        dialog.entries['path'].setText(source.name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.values()
            self.submit('GITHUB UPLOAD', lambda: github_upload(source, values['repo'], values['path'], values['token']))

    def github_download_dialog(self):
        dialog = FieldsDialog(self, 'Download file from GitHub', [
            ('repo', 'Repository OWNER/REPO', False), ('path', 'Path in repository', False),
            ('token', 'Token for private repo (optional)', True)])
        dialog.entries['repo'].setText('NexusWebOS/NightCode')
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        folder = QFileDialog.getExistingDirectory(self, 'Download into folder', str(self.current_dir))
        if folder:
            self.submit('GITHUB DOWNLOAD', lambda: github_download(
                values['repo'], values['path'], Path(folder), values['token']))

    def supabase_dialog(self):
        source = self._one_file()
        if source is None:
            return
        dialog = FieldsDialog(self, 'Upload file to Supabase Storage', [
            ('url', 'Project URL', False), ('bucket', 'Storage bucket', False),
            ('path', 'Object path', False), ('api_key', 'Project API key', True),
            ('token', 'User access token', True)])
        dialog.entries['path'].setText(source.name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.values()
            self.submit('SUPABASE UPLOAD', lambda: supabase_upload(
                source, values['url'], values['bucket'], values['path'],
                values['api_key'], values['token']))

    def execute_command(self):
        command = self.command.text().strip()
        self.command.clear()
        if not command:
            return
        self.log('NC:\\> ' + command)
        try:
            args = shlex.split(command, posix=False)
            args = [arg.strip('"') for arg in args]
            verb = args[0].upper()
            if verb == 'HELP':
                self.log('DIR | CD <folder> | COPY <source> <destination folder> | DUP <path> | VIEW <path> | WEB <url> | DOWNLOAD <url> | CLS')
            elif verb == 'DIR':
                for path in sorted(self.current_dir.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))[:100]:
                    self.log(('<DIR> ' if path.is_dir() else '      ') + path.name)
            elif verb == 'CD' and len(args) >= 2:
                self.show_directory(self.current_dir / args[1])
            elif verb == 'COPY' and len(args) >= 3:
                self.submit('COPY', lambda: ', '.join(map(str, copy_items([self.current_dir / args[1]], self.current_dir / args[2]))))
            elif verb == 'DUP' and len(args) >= 2:
                self.submit('DUPLICATE', lambda: ', '.join(map(str, duplicate_items([self.current_dir / args[1]]))))
            elif verb == 'VIEW' and len(args) >= 2:
                self.preview((self.current_dir / args[1]).resolve(strict=True))
            elif verb in ('WEB', 'BROWSE') and len(args) >= 2:
                self.navigate(' '.join(args[1:]))
            elif verb == 'DOWNLOAD' and len(args) >= 2:
                self.submit('DOWNLOAD', lambda: download_url(args[1], self.current_dir))
            elif verb == 'CLS':
                self.output.clear()
            else:
                self.log('UNKNOWN COMMAND OR MISSING ARGUMENTS. TYPE HELP.')
        except (OSError, ValueError) as exc:
            self.log(f'ERROR: {exc}')

    def closeEvent(self, event):
        self.executor.shutdown(wait=False, cancel_futures=True)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = NightCode()
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
