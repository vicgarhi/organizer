import unittest, os, tempfile, io, zipfile, json
ROOT=tempfile.TemporaryDirectory()
os.environ['DATA_DIR']=ROOT.name
os.environ['APP_PASSWORD']='only-for-isolated-tests'
os.environ.pop('OPENAI_API_KEY',None)
from fastapi.testclient import TestClient
from app.main import app

class Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client=TestClient(app); cls.client.__enter__()
        cls.headers={'X-Requested-With':'EnOrden'}
        cls.client.post('/api/login',json={'password':'only-for-isolated-tests'},headers=cls.headers)
    @classmethod
    def tearDownClass(cls): cls.client.__exit__(None,None,None); ROOT.cleanup()
    def call(self,path,body={},method='POST'):
        r=self.client.request(method,'/api'+path,json=body,headers=self.headers)
        self.assertEqual(r.status_code,200,r.text);return r.json()
    def state(self): return self.client.get('/api/state').json()
    def test_01_security(self):
        with TestClient(app) as stranger:
            self.assertEqual(stranger.get('/api/state').status_code,401)
            self.assertEqual(stranger.post('/api/login',json={'password':'only-for-isolated-tests'}).status_code,403)
            self.assertEqual(stranger.post('/api/login',json={'password':'only-for-isolated-tests'},headers={**self.headers,'Origin':'https://attacker.example'}).status_code,403)
            self.assertEqual(stranger.get('/.data/organizer.sqlite3').status_code,404)
    def test_02_capture_review_context(self):
        note='He hecho las pruebas de conciliación de GB Foods. Quedan dos casos con errores. Necesito revisarlos antes de dar la actualización del lunes'
        cid=self.call('/captures',{'content':note,'origin':'Caso ficticio de prueba'})['id']
        s=self.state(); c=next(c for c in s['captures'] if c['id']==cid)
        self.assertEqual(c['content'],note);self.assertEqual(c['proposal']['matter_id'],'conciliation');self.assertEqual(c['engine'],'local')
        self.assertEqual(c['proposal']['tasks'][0]['title'],'Revisar los dos casos con errores');self.assertIsNone(c['proposal']['tasks'][0]['estimate'])
        first=self.call('/captures/'+cid+'/accept');self.assertEqual(len(first['created_tasks']),1)
        self.call('/captures/'+cid+'/accept');s=self.state()
        created=[t for t in s['tasks'] if t['source_id']==cid];self.assertEqual(len(created),1)
        initial=[t for t in s['tasks'] if t['matter_id']=='conciliation' and t['source_id']=='specification']
        self.assertTrue(all(t['status']=='open' for t in initial));self.assertIn('2026-10-05',[t['commitment'] for t in initial])
        self.assertTrue(any(e['entity_id']==cid and e['kind']=='accepted' for e in s['events']))
        self.call('/captures/'+cid+'/undo');self.assertFalse(any(t['source_id']==cid for t in self.state()['tasks']))
    def test_03_correct_discard(self):
        cid=self.call('/captures',{'content':'Un acuerdo que solo quiero guardar.'})['id']
        c=next(c for c in self.state()['captures'] if c['id']==cid)
        p={**c['proposal'],'matter_id':'factoring','tasks':[],'note':'Acuerdo por confirmar.'}
        self.call('/captures/'+cid+'/proposal',p,'PATCH');self.call('/captures/'+cid+'/discard');self.call('/captures/'+cid+'/undo');self.call('/captures/'+cid+'/accept')
        c=next(c for c in self.state()['captures'] if c['id']==cid)
        self.assertEqual(c['matter_id'],'factoring');self.assertEqual(c['content'],'Un acuerdo que solo quiero guardar.')
    def test_04_unknowns(self):
        tid=self.call('/tasks',{'title':'Organizar sesiones de requerimientos y lanzar convocatorias','status':'waiting'})['id']
        t=next(t for t in self.state()['tasks'] if t['id']==tid)
        for key in ['matter_id','person','commitment','estimate','followup']:self.assertIsNone(t[key])
        self.assertTrue(any(t['id']==tid for t in self.state()['plan']['waiting']))
    def test_05_manual_edit_undo_and_cycle(self):
        a=self.call('/tasks',{'title':'A'})['id'];b=self.call('/tasks',{'title':'B','blocked_by':a})['id']
        r=self.client.patch('/api/tasks/'+a,json={'blocked_by':b},headers=self.headers);self.assertEqual(r.status_code,422)
        self.call('/tasks/'+a,{'commitment':'2026-11-05','status':'done'},'PATCH');self.call('/tasks/'+a+'/undo')
        t=next(t for t in self.state()['tasks'] if t['id']==a);self.assertIsNone(t['commitment']);self.assertEqual(t['status'],'open')
    def test_06_plan_does_not_move_commitments(self):
        self.call('/settings',{'availability':30})
        s=self.state();self.assertEqual(s['plan']['capacity'],30)
        self.assertFalse(any(t['estimate'] and t['estimate']>30 for t in s['plan']['chosen']))
        tid=next(t['id'] for t in s['tasks'] if t['commitment']=='2026-10-05')
        self.call('/plan/accept',{'ids':[tid]});t=next(t for t in self.state()['tasks'] if t['id']==tid)
        self.assertEqual(t['commitment'],'2026-10-05');self.assertEqual(t['planned'],s['plan']['today']);self.assertEqual(t['status'],'open')
        self.call('/settings',{'availability':0});self.assertEqual(self.state()['plan']['chosen'],[])
    def test_07_attachment_backup_restore(self):
        cid=self.call('/captures',{'content':'Fichero de referencia'})['id']
        r=self.client.post('/api/captures/'+cid+'/attachments',files={'file':('note.txt',b'reference','text/plain')},headers=self.headers);self.assertEqual(r.status_code,200)
        aid=r.json()['id'];self.assertEqual(self.client.get('/api/attachments/'+aid).content,b'reference')
        backup=self.client.get('/api/backup');self.assertEqual(backup.status_code,200)
        with zipfile.ZipFile(io.BytesIO(backup.content)) as z:
            data=json.loads(z.read('data.json'));self.assertNotIn('sessions',data['tables']);self.assertNotIn('access.json',z.namelist());self.assertEqual(z.read('attachments/'+aid),b'reference')
        count=len(self.state()['clients']);self.call('/clients',{'name':'Temporary test client'})
        r=self.client.post('/api/restore',files={'file':('backup.zip',backup.content,'application/zip')},headers=self.headers);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(len(self.state()['clients']),count);self.assertEqual(self.client.get('/api/attachments/'+aid).content,b'reference')
        r=self.client.post('/api/restore',files={'file':('bad.zip',b'not zip','application/zip')},headers=self.headers);self.assertEqual(r.status_code,422,r.text);self.assertEqual(len(self.state()['clients']),count)
    def test_08_reminders(self):
        id=self.call('/reminders',{'title':'Reportar horas','due':'2026-10-02','recurrence':'weekdays'})['id']
        self.call('/reminders/'+id+'/ack');r=next(r for r in self.state()['reminders'] if r['id']==id)
        self.assertGreater(r['due'],'2026-10-02')
    def test_09_assistant_honest(self):
        r=self.call('/assistant',{'query':'¿Cómo está GB Foods?','matter_id':'conciliation'})
        self.assertEqual(r['engine'],'local');self.assertIn('sin IA',r['answer']);self.assertTrue(r['sources'])
        r=self.call('/assistant',{'query':'Cliente inexistente xyz'})
        self.assertEqual(r['sources'],[]);self.assertIn('No encuentro',r['answer'])
    def test_10_recover_creation(self):
        c=self.call('/clients',{'name':'Cliente de pruebas'})['id'];m=self.call('/matters',{'client_id':c,'name':'Asunto de pruebas'})['id'];self.call('/tasks',{'matter_id':m,'title':'Pendiente de pruebas'})
        self.assertTrue(any(t['matter_id']==m for t in self.state()['tasks']))
    def test_11_integrations_not_simulated(self):
        self.assertFalse(self.state()['integrations']['ai']);self.assertFalse(self.state()['integrations']['push'])
        r=self.client.post('/api/push/test',json={},headers=self.headers);self.assertEqual(r.status_code,503)
    def test_12_undo_preserves_subsequent_work(self):
        cid=self.call('/captures',{'content':'Tengo que preparar una revisión','matter_id':'support'})['id']
        tid=self.call('/captures/'+cid+'/accept')['created_tasks'][0]
        self.call('/tasks/'+tid,{'notes':'Nueva actividad'},'PATCH')
        r=self.client.post('/api/captures/'+cid+'/undo',json={},headers=self.headers);self.assertEqual(r.status_code,409)
        self.assertEqual(next(t for t in self.state()['tasks'] if t['id']==tid)['notes'],'Nueva actividad')

if __name__=='__main__':unittest.main(verbosity=2)
