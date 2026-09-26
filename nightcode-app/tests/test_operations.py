from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from contextlib import contextmanager
from pathlib import Path
import shutil
import threading
import unittest
from uuid import uuid4

from operations import copy_items, download_url, duplicate_items

WORKSPACE = Path(__file__).resolve().parents[1]


@contextmanager
def workspace_directory():
    directory = WORKSPACE / f'operation-test-{uuid4().hex}'
    directory.mkdir()
    try:
        yield directory
    finally:
        assert directory.parent == WORKSPACE
        shutil.rmtree(directory)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'nightcode transfer test')

    def log_message(self, *_):
        pass


class OperationsTests(unittest.TestCase):
    def test_copy_and_duplicate_preserve_contents_and_avoid_collisions(self):
        with workspace_directory() as root:
            source = root / 'source.txt'
            source.write_text('NC-2047', encoding='utf-8')
            target = root / 'target'
            target.mkdir()
            first = copy_items([source], target)[0]
            second = copy_items([source], target)[0]
            duplicate = duplicate_items([source])[0]
            self.assertEqual([p.read_text() for p in (first, second, duplicate)], ['NC-2047'] * 3)
            self.assertEqual(len({first, second, duplicate}), 3)

    def test_folder_cannot_copy_into_own_child(self):
        with workspace_directory() as directory:
            root = directory / 'folder'
            child = root / 'child'
            child.mkdir(parents=True)
            with self.assertRaises(ValueError):
                copy_items([root], child)

    def test_real_http_download(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with workspace_directory() as directory:
                url = f'http://127.0.0.1:{server.server_port}/sample.txt'
                path = download_url(url, directory)
                self.assertEqual(path.read_bytes(), b'nightcode transfer test')
        finally:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
