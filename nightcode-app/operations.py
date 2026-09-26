"""File and network operations for the NightCode desktop shell."""
from __future__ import annotations

import base64
import http.client
import json
import mimetypes
from pathlib import Path
import shutil
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4


def unique_path(parent: Path, name: str) -> Path:
    parent = parent.expanduser().resolve()
    candidate = parent / name
    if not candidate.exists():
        return candidate
    original = Path(name)
    for number in range(1, 10000):
        suffix = f" copy {number if number > 1 else ''}".rstrip()
        candidate = parent / f'{original.stem}{suffix}{original.suffix}'
        if not candidate.exists():
            return candidate
    raise FileExistsError('No available copy name.')


def copy_items(sources: list[Path], destination: Path) -> list[Path]:
    destination = destination.expanduser().resolve()
    if not destination.is_dir():
        raise NotADirectoryError(destination)
    results = []
    for source in sources:
        source = source.expanduser().resolve(strict=True)
        if source.is_dir() and (destination == source or source in destination.parents):
            raise ValueError('A folder cannot be copied into itself or a subfolder.')
        target = unique_path(destination, source.name)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
        results.append(target)
    return results


def duplicate_items(sources: list[Path]) -> list[Path]:
    return [copy_items([source], source.parent)[0] for source in sources]


def _web_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value.strip())
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError('Enter a complete HTTP or HTTPS URL without embedded credentials.')
    return urllib.parse.urlunsplit(parsed)


def download_url(url: str, folder: Path, token: str = '') -> Path:
    url = _web_url(url)
    folder = folder.expanduser().resolve()
    if not folder.is_dir():
        raise NotADirectoryError(folder)
    name = Path(urllib.parse.unquote(urllib.parse.urlsplit(url).path)).name or 'download'
    target = unique_path(folder, name)
    headers = {'User-Agent': 'NightCode/1.0'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(_NoRedirect()) if token else urllib.request.build_opener()
    staged = target.with_name(f'.{target.name}.{uuid4().hex}.part')
    try:
        with opener.open(request, timeout=45) as response, staged.open('xb') as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        staged.replace(target)
    finally:
        staged.unlink(missing_ok=True)
    return target


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError('Authenticated download redirected; open the destination explicitly to avoid sharing the token.')


def _github_request(url: str, token: str, method='GET', payload: dict | None = None):
    if not token.strip():
        raise ValueError('A GitHub token with Contents permission is required.')
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {'Authorization': 'Bearer ' + token.strip(),
               'Accept': 'application/vnd.github+json',
               'User-Agent': 'NightCode/1.0',
               'X-GitHub-Api-Version': '2022-11-28'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read(350).decode('utf-8', 'replace')
        raise RuntimeError(f'GitHub returned HTTP {exc.code}: {detail}') from None


def github_upload(source: Path, repository: str, remote_path: str, token: str) -> str:
    source = source.expanduser().resolve(strict=True)
    if not source.is_file():
        raise ValueError('Select one file to upload.')
    if source.stat().st_size > 25 * 1024 * 1024:
        raise ValueError('This upload is limited to 25 MB; use a GitHub Release for larger files.')
    parts = repository.strip().split('/')
    if len(parts) != 2 or not all(part.replace('-', '').replace('_', '').isalnum() for part in parts):
        raise ValueError('Repository must be OWNER/REPO.')
    path = remote_path.strip().strip('/') or source.name
    if any(part in ('', '.', '..') for part in path.split('/')):
        raise ValueError('Enter a repository-relative file path.')
    url = 'https://api.github.com/repos/' + '/'.join(parts) + '/contents/' + urllib.parse.quote(path, safe='/')
    try:
        existing = _github_request(url, token)
        sha = existing.get('sha')
    except RuntimeError as exc:
        if 'HTTP 404' not in str(exc):
            raise
        sha = None
    payload = {'message': f'Upload {path} from NightCode',
               'content': base64.b64encode(source.read_bytes()).decode('ascii')}
    if sha:
        payload['sha'] = sha
    result = _github_request(url, token, 'PUT', payload)
    return result['content']['html_url']


def github_download(repository: str, remote_path: str, folder: Path, token: str = '') -> Path:
    """Download one repository file through the Contents API, without forwarding tokens on redirects."""
    parts = repository.strip().split('/')
    if len(parts) != 2 or not all(part.replace('-', '').replace('_', '').isalnum() for part in parts):
        raise ValueError('Repository must be OWNER/REPO.')
    path = remote_path.strip().strip('/')
    if not path or any(part in ('', '.', '..') for part in path.split('/')):
        raise ValueError('Enter a repository-relative file path.')
    folder = folder.expanduser().resolve()
    if not folder.is_dir():
        raise NotADirectoryError(folder)
    target = unique_path(folder, Path(path).name)
    staged = target.with_name(f'.{target.name}.{uuid4().hex}.part')
    endpoint = '/repos/' + '/'.join(parts) + '/contents/' + urllib.parse.quote(path, safe='/')
    connection = http.client.HTTPSConnection('api.github.com', timeout=90)
    headers = {'Accept': 'application/vnd.github.raw+json',
               'User-Agent': 'NightCode/1.0',
               'X-GitHub-Api-Version': '2022-11-28'}
    if token.strip():
        headers['Authorization'] = 'Bearer ' + token.strip()
    try:
        connection.request('GET', endpoint, headers=headers)
        response = connection.getresponse()
        if response.status in (301, 302, 303, 307, 308):
            redirect = response.getheader('Location', '')
            response.read()
            parsed = urllib.parse.urlsplit(_web_url(redirect))
            if parsed.scheme != 'https' or parsed.hostname not in ('raw.githubusercontent.com', 'objects.githubusercontent.com'):
                raise ValueError('GitHub redirected to an unexpected download host.')
            with urllib.request.urlopen(urllib.request.Request(redirect, headers={'User-Agent': 'NightCode/1.0'}), timeout=90) as stream, staged.open('xb') as output:
                shutil.copyfileobj(stream, output, length=1024 * 1024)
        elif response.status == 200:
            if response.getheader('Content-Type', '').startswith('application/json'):
                raise ValueError('GitHub returned metadata instead of file bytes.')
            with staged.open('xb') as output:
                shutil.copyfileobj(response, output, length=1024 * 1024)
        else:
            detail = response.read(350).decode('utf-8', 'replace')
            raise RuntimeError(f'GitHub returned HTTP {response.status}: {detail}')
        staged.replace(target)
    finally:
        connection.close()
        staged.unlink(missing_ok=True)
    return target


def supabase_upload(source: Path, project_url: str, bucket: str, object_path: str,
                    api_key: str, token: str) -> str:
    source = source.expanduser().resolve(strict=True)
    if not source.is_file():
        raise ValueError('Select one file to upload.')
    parsed = urllib.parse.urlsplit(_web_url(project_url))
    if parsed.scheme != 'https' or parsed.path not in ('', '/'):
        raise ValueError('Use the HTTPS project root URL, such as https://PROJECT.supabase.co.')
    if not api_key.strip() or not token.strip() or not bucket.strip():
        raise ValueError('Enter a bucket, project API key and access token.')
    path = object_path.strip().strip('/') or source.name
    if any(part in ('', '.', '..') for part in path.split('/')):
        raise ValueError('Enter a bucket-relative object path.')
    endpoint = '/storage/v1/object/' + urllib.parse.quote(bucket.strip(), safe='') + '/' + urllib.parse.quote(path, safe='/')
    content_type = mimetypes.guess_type(source.name)[0] or 'application/octet-stream'
    connection = http.client.HTTPSConnection(parsed.netloc, timeout=120)
    try:
        connection.putrequest('POST', endpoint)
        connection.putheader('Authorization', 'Bearer ' + token.strip())
        connection.putheader('apikey', api_key.strip())
        connection.putheader('Content-Type', content_type)
        connection.putheader('Content-Length', str(source.stat().st_size))
        connection.putheader('x-upsert', 'false')
        connection.endheaders()
        with source.open('rb') as stream:
            while block := stream.read(1024 * 1024):
                connection.send(block)
        response = connection.getresponse()
        detail = response.read(500)
        if response.status not in (200, 201):
            raise RuntimeError(f'Supabase returned HTTP {response.status}: {detail.decode("utf-8", "replace")}')
    finally:
        connection.close()
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, endpoint, '', ''))
