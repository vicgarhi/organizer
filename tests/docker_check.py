"""Integration check for a disposable Compose installation ONLY.
Requires its default initial password and untouched seeded data.
Never run against a personal installation: backup/restore replaces test data.
"""
import subprocess,os,json,time,urllib.request,http.cookiejar,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if '--confirm-test-server' not in sys.argv:raise SystemExit('For an isolated test stack only: python3 tests/docker_check.py --confirm-test-server')
base=os.environ.get('TEST_BASE_URL','http://127.0.0.1:18080')
compose=['docker','compose','--project-directory',str(ROOT)]
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
password=subprocess.run(compose+['exec','-T','organizer','cat','/data/initial-password.txt'],check=True,capture_output=True,text=True).stdout.strip()
def call(path,body=None):
    req=urllib.request.Request(base+'/api'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json','X-Requested-With':'EnOrden'})
    return json.load(opener.open(req,timeout=10))
call('/login',{'password':password})
s=call('/state')
if len(s['captures'])!=1 or len(s['tasks'])!=6:raise SystemExit('Not a fresh test database. Refusing to modify data.')
cid=call('/captures',{'content':'Necesito comprobar el despliegue de prueba','origin':'Ficticio · prueba Docker','matter_id':'support'})['id']
call('/captures/'+cid+'/accept',{})
assert any(t['source_id']==cid for t in call('/state')['tasks'])
# Binary attachment via multipart, roundtrip through the proxy.
boundary='enorden-integration-boundary'
blob=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="test.txt"\r\nContent-Type: text/plain\r\n\r\n'.encode()+b'test attachment'+f'\r\n--{boundary}--\r\n'.encode())
req=urllib.request.Request(base+'/api/captures/'+cid+'/attachments',data=blob,headers={'Content-Type':'multipart/form-data; boundary='+boundary,'X-Requested-With':'EnOrden'})
aid=json.load(opener.open(req))['id']
assert opener.open(base+'/api/attachments/'+aid).read()==b'test attachment'
existing=set((ROOT/'backups').glob('*.tar.gz'))
subprocess.run([str(ROOT/'scripts/deploy.sh'),'backup'],cwd=ROOT,check=True)
backup=next(iter(set((ROOT/'backups').glob('*.tar.gz'))-existing))
call('/captures',{'content':'Este cambio se elimina al recuperar','origin':'Ficticio · prueba Docker'})
subprocess.run([str(ROOT/'scripts/deploy.sh'),'restore',str(backup),'--confirm'],cwd=ROOT,check=True)
s=call('/state')
assert len(s['captures'])==2
assert any(c['id']==cid and c['state']=='accepted' for c in s['captures'])
assert opener.open(base+'/api/attachments/'+aid).read()==b'test attachment'
assert next(t for t in s['tasks'] if t['title']=='Dar una actualización de la conciliación')['commitment']=='2026-10-05'
subprocess.run(compose+['restart','organizer'],check=True)
for _ in range(60):
    try:
        assert any(c['id']==cid for c in call('/state')['captures']);break
    except Exception:time.sleep(.25)
else:raise AssertionError('Application failed to restart with persistent data/session')
print('PASS: Docker proxy → private access → capture/review → attachment; physical backup/restore; data and session after restart.')
