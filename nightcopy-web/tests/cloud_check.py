"""Integration-test the deployed browser UI with mocked Google and Supabase APIs.
No real account sign-in, upload, or remote file changes are performed."""
import base64,json,time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
USER='12345678-1234-4234-8234-123456789012'
def jwt(data):
 encode=lambda x:base64.urlsafe_b64encode(json.dumps(x).encode()).decode().rstrip('=')
 return encode({'alg':'HS256','typ':'JWT'})+'.'+encode(data)+'.test-signature'
files=[{'id':'remote-file','name':'cloud.bin','mimeType':'application/octet-stream','size':'4'},
 {'id':'google-doc','name':'Archive notes','mimeType':'application/vnd.google-apps.document'}]
drive_uploads=[];copies=[];vault={};receipts=[];errors=[];request_errors=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True)
 page=browser.new_page(viewport={'width':1440,'height':1030},accept_downloads=True)
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script("""
 localStorage.setItem('nightcopy-settings',JSON.stringify({googleClientId:'123-test.apps.googleusercontent.com',driveAccount:'archive@example.com',supabaseUrl:'https://test-nightcopy.supabase.co',supabaseKey:'test-public-placeholder'}));
 window.google={accounts:{oauth2:{initTokenClient:cfg=>({requestAccessToken:()=>cfg.callback({access_token:'drive-test-only',expires_in:3600})})}}};
 """)
 def google(route):
  request=route.request;url=request.url
  if '/about?' in url:return route.fulfill(json={'user':{'emailAddress':'archive@example.com','displayName':'NightCode Archive'},'storageQuota':{'limit':'100000','usage':'4'}})
  if '/upload/' in url and 'uploadType=resumable' in url:
   meta=request.post_data_json;drive_uploads.append({'metadata':meta})
   return route.fulfill(status=200,headers={'Location':'https://www.googleapis.com/upload/nightcopy-test-session','Access-Control-Expose-Headers':'Location','Access-Control-Allow-Origin':'*'},json={})
  if url.endswith('nightcopy-test-session'):
   drive_uploads[-1]['bytes']=request.post_data_buffer
   return route.fulfill(json={'id':'uploaded-file','name':drive_uploads[-1]['metadata']['name'],'size':str(len(request.post_data_buffer or b''))})
  if '/copy?' in url:
   meta=request.post_data_json;copies.append(meta)
   return route.fulfill(json={'id':'copied-file','name':meta['name']})
  if '/export?' in url:return route.fulfill(body=b'%PDF-1.0\nMock document export',content_type='application/pdf')
  if 'alt=media' in url:return route.fulfill(body=bytes([0,255,5,128]),content_type='application/octet-stream')
  if '/files?' in url:return route.fulfill(json={'files':files})
  request_errors.append('Unexpected Google request '+url);return route.fulfill(status=500,json={'error':{'message':'Mock endpoint missing'}})
 page.route('https://www.googleapis.com/**',google)
 user={'id':USER,'email':'test@nightcopy.example','aud':'authenticated','role':'authenticated','app_metadata':{'provider':'email'},'user_metadata':{},'created_at':'2026-09-27T00:00:00Z'}
 def supabase(route):
  request=route.request;url=request.url
  if '/auth/v1/settings' in url:return route.fulfill(json={'external':{'email':True,'google':False}})
  if '/auth/v1/token?' in url:return route.fulfill(json={'access_token':jwt({'sub':USER,'aud':'authenticated','role':'authenticated','exp':int(time.time())+3600}), 'token_type':'bearer','expires_in':3600,'refresh_token':'supabase-test-only','user':user})
  if '/auth/v1/user' in url:return route.fulfill(json=user)
  if '/storage/v1/object/list/nightcopy' in url:
   assert request.post_data_json['prefix']==USER
   data=[{'id':'file-'+str(i),'name':name,'metadata':{'size':len(blob)},'updated_at':'2026-09-27T00:00:00Z'}for i,(name,blob)in enumerate(vault.items())]
   return route.fulfill(json=data)
  if '/storage/v1/object/nightcopy/' in url:
   assert '/'+USER+'/' in url
   from urllib.parse import unquote
   name=unquote(url.split('/'+USER+'/')[-1]);vault[name]=request.post_data_buffer
   return route.fulfill(json={'Key':'nightcopy/'+USER+'/'+name})
  if '/rest/v1/nightcopy_transfers' in url:receipts.append(request.post_data_json);return route.fulfill(status=201,json={})
  request_errors.append('Unexpected Supabase request '+url);return route.fulfill(status=500,json={'message':'Mock endpoint missing'})
 page.route('https://test-nightcopy.supabase.co/**',supabase)
 try:
  page.goto('https://nightcopy.coletechsystems.com')
  page.wait_for_selector('#sbStatus:text("SIGN IN")')
  page.locator('#filePicker').set_input_files([{'name':'test.bin','mimeType':'application/octet-stream','buffer':bytes([0,255,1,128])}])
  page.wait_for_selector('#count0:text("1 item")')
  page.locator('#connectDrive').click()
  page.wait_for_selector('#googleChip:text("CONNECTED")')
  page.locator('#all0').check();page.locator('#transferButton').click();page.locator('#reviewConfirm').click()
  page.wait_for_function("() => document.querySelector('#sessionSummary').textContent.includes('1 transfers complete')")
  assert drive_uploads[0]['bytes']==bytes([0,255,1,128])
  assert drive_uploads[0]['metadata']['parents']==['root']
  page.locator('#all0').uncheck()
  page.locator('#pane1 [data-check="remote-file"]').check()
  page.locator('#duplicateButton').click();page.locator('#reviewConfirm').click()
  page.wait_for_function("() => document.querySelector('#sessionSummary').textContent.includes('2 transfers complete')")
  assert copies[0]['name']=='cloud (copy).bin'
  with page.expect_download() as event:
   page.locator('#downloadButton').click();page.locator('#reviewConfirm').click()
  download=event.value
  assert Path(download.path()).read_bytes()==bytes([0,255,5,128])
  page.locator('#pane1 [data-check="remote-file"]').uncheck();page.locator('#pane1 [data-check="google-doc"]').check()
  with page.expect_download() as event:
   page.locator('#downloadButton').click();page.locator('#reviewConfirm').click()
  assert event.value.suggested_filename=='Archive notes.pdf'
  page.locator('[data-view="connections"]').first.click()
  page.locator('#loginEmail').fill('test@nightcopy.example');page.locator('#loginPassword').fill('fixture-only-password');page.locator('#sbLogin').click()
  page.wait_for_selector('#sbStatus:text("PRIVATE / READY")')
  page.locator('#all0').check();page.locator('#transferButton').click();page.locator('#reviewConfirm').click()
  page.wait_for_function("() => document.querySelector('#sessionSummary').textContent.includes('5 transfers complete')")
  assert vault['test.bin']==bytes([0,255,1,128])
  assert receipts[-1]['user_id']==USER
  assert receipts[-1]['bytes']==4
  assert not errors,errors
  assert not request_errors,request_errors
 except Exception:
  print(page.locator('#terminalLog').inner_text())
  print('Mock requests:',request_errors)
  raise
 browser.close()
print('PASS: live HTTPS/CSP UI, Drive upload bytes, Drive duplicate, binary download, native PDF export, Supabase auth, user-scoped vault upload and transfer receipt (mocked provider APIs).')
