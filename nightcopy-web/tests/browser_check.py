"""Browser integration checks using disposable files, a mocked local destination,
and mocked cloud APIs. No real cloud account uploads or disk transfers."""
import base64, functools, json, threading, zipfile, io
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'_shots';OUT.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args): pass
handler=functools.partial(Quiet,directory=str(ROOT/'dist'))
server=ThreadingHTTPServer(('127.0.0.1',0),handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
local_fixture="""
localStorage.setItem('nightcopy-settings',JSON.stringify({supabaseUrl:'https://test-nightcopy.supabase.co',supabaseKey:'test-public-placeholder',driveAccount:'archive@example.com'}));
window._writes={};
function dir(prefix=''){
 return {name:prefix||'Test destination',kind:'directory',isSameEntry:async()=>false,
 entries:async function*(){},
 getDirectoryHandle:async(name,opt={})=>{if(!opt.create)throw new DOMException('Missing','NotFoundError');return dir(prefix+'/'+name)},
 getFileHandle:async(name,opt={})=>{if(!opt.create)throw new DOMException('Missing','NotFoundError');return {createWritable:async()=>{const chunks=[];return {write:async b=>chunks.push(b),abort:async()=>{},close:async()=>{const b=new Blob(chunks);window._writes[prefix+'/'+name]=Array.from(new Uint8Array(await b.arrayBuffer()))}}}}}
 };}
window.showDirectoryPicker=async()=>dir();
"""
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True)
 page=browser.new_page(viewport={'width':1440,'height':1030},accept_downloads=True)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script(local_fixture)
 page.route('https://test-nightcopy.supabase.co/auth/v1/settings',lambda r:r.fulfill(json={'external':{'email':True,'google':False}}))
 page.goto(f'http://127.0.0.1:{server.server_port}')
 page.wait_for_selector('#sbStatus:text("SIGN IN")')
 page.screenshot(path=str(OUT/'nightcopy-desktop.png'),full_page=True)
 page.locator('#filePicker').set_input_files([
  {'name':'NightCopy readme.txt','mimeType':'text/plain','buffer':b'NightCopy binary-safe file transfer test\n'},
  {'name':'archive.bin','mimeType':'application/octet-stream','buffer':bytes([0,255,1,128])},
  {'name':'empty.txt','mimeType':'text/plain','buffer':b''}])
 page.wait_for_selector('#count0:text("3 items")')
 page.locator('#provider1').select_option('local')
 page.wait_for_selector('#provider1:has(option[value="local"]:checked)')
 page.locator('#all0').check()
 page.locator('#transferButton').click()
 assert page.locator('#reviewDialog').is_visible()
 page.locator('#reviewConfirm').click()
 page.wait_for_function("document.querySelector('#sessionSummary').textContent.includes('1 transfers complete')")
 writes=page.evaluate('window._writes')
 assert writes['/archive.bin']==[0,255,1,128]
 assert writes['/empty.txt']==[]
 page.locator('#commandInput').fill('select "NightCopy readme.txt"')
 page.locator('#commandInput').press('Enter')
 page.locator('#commandInput').fill('view');page.locator('#commandInput').press('Enter')
 # Select only one file for preview.
 page.wait_for_timeout(100)
 page.locator('#all0').uncheck()
 page.locator('#pane0 [data-check="NightCopy readme.txt"]').check()
 page.locator('#commandInput').fill('view');page.locator('#commandInput').press('Enter')
 page.wait_for_selector('#previewDialog[open]')
 assert 'binary-safe' in page.locator('#previewContent').inner_text()
 page.locator('#closePreview').click()
 page.locator('#duplicateButton').click();page.locator('#reviewConfirm').click()
 page.wait_for_selector('#count0:text("4 items")')
 assert page.locator('#list0').get_by_text('NightCopy readme (copy).txt',exact=True).is_visible()
 page.locator('#all0').check();page.locator('#zipButton').click();page.locator('#reviewConfirm').click()
 page.wait_for_function("document.querySelector('#sessionSummary').textContent.includes('3 transfers complete')")
 writes=page.evaluate('window._writes');zipname=next(n for n in writes if n.endswith('.zip'))
 z=zipfile.ZipFile(io.BytesIO(bytes(writes[zipname])))
 assert z.read('archive.bin')==bytes([0,255,1,128])
 assert z.read('empty.txt')==b''
 assert 'nightcopy-manifest.json' in z.namelist()
 page.locator('#commandInput').fill('dir');page.locator('#commandInput').press('Enter')
 page.wait_for_function("document.querySelector('#terminalLog').textContent.includes('archive.bin')")
 page.screenshot(path=str(OUT/'nightcopy-files.png'),full_page=True)
 # Responsive navigation and layout without horizontal document overflow.
 for width in [1160,900,600,390]:
  page.set_viewport_size({'width':width,'height':950})
  assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'),f'Overflow at {width}px'
 page.locator('.mobile-nav [data-view="queue"]').click()
 assert page.locator('#queueView').is_visible()
 page.screenshot(path=str(OUT/'nightcopy-mobile-queue.png'),full_page=True)
 page.locator('.mobile-nav [data-view="connections"]').click()
 assert page.locator('#connectionsView').is_visible()
 assert '@' in page.locator('#driveAccount').inner_text()
 assert not errors,errors
 browser.close()
server.shutdown()
print('PASS: binary/zero-byte transfer, duplicate, ZIP contents, preview, quoted shell commands, account display and responsive layout.')
