import os, sqlite3, json, uuid
from pathlib import Path
from datetime import datetime, timezone

DATA = Path(os.environ.get('DATA_DIR', Path(__file__).resolve().parents[1] / '.data'))
DATA.mkdir(parents=True, exist_ok=True)
(DATA / 'attachments').mkdir(exist_ok=True)
DB = DATA / 'organizer.sqlite3'

def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return uuid.uuid4().hex

def connect():
    db = sqlite3.connect(DB, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db

def rows(db, sql, args=()): return [dict(r) for r in db.execute(sql, args).fetchall()]
def event(db, kind, entity, entity_id, payload):
    db.execute('INSERT INTO events VALUES (?,?,?,?,?,?)', (uid(), now(), kind, entity, entity_id, json.dumps(payload, ensure_ascii=False)))

SCHEMA = '''
CREATE TABLE IF NOT EXISTS clients(id TEXT PRIMARY KEY,name TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS matters(id TEXT PRIMARY KEY,client_id TEXT REFERENCES clients(id),name TEXT NOT NULL,summary TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,matter_id TEXT REFERENCES matters(id),title TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open',commitment TEXT,planned TEXT,followup TEXT,estimate INTEGER,person TEXT,blocked_by TEXT REFERENCES tasks(id),notes TEXT NOT NULL DEFAULT '',source_id TEXT,created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS captures(id TEXT PRIMARY KEY,created TEXT NOT NULL,content TEXT NOT NULL,origin TEXT NOT NULL,matter_id TEXT REFERENCES matters(id),task_id TEXT REFERENCES tasks(id),state TEXT NOT NULL DEFAULT 'pending',proposal TEXT NOT NULL,engine TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS attachments(id TEXT PRIMARY KEY,capture_id TEXT NOT NULL REFERENCES captures(id),name TEXT NOT NULL,mime TEXT NOT NULL,size INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,created TEXT NOT NULL,kind TEXT NOT NULL,entity TEXT NOT NULL,entity_id TEXT NOT NULL,payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reminders(id TEXT PRIMARY KEY,title TEXT NOT NULL,due TEXT NOT NULL,recurrence TEXT NOT NULL DEFAULT 'none',last_sent TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS subscriptions(endpoint TEXT PRIMARY KEY,subscription TEXT NOT NULL);
'''

def initialize():
    with connect() as db:
        db.executescript(SCHEMA)
        db.execute('PRAGMA journal_mode=WAL')
        if not db.execute("SELECT 1 FROM settings WHERE key='initialized'").fetchone():
            clients = [('gb','GB Foods'),('vw','Volkswagen'),('bcn','Barcelona'),('kyr','Ofertas Kyriba'),('gon','Gonvarri'),('internal','Temas internos')]
            db.executemany('INSERT INTO clients VALUES (?,?)', clients)
            matters = [('conciliation','gb','Conciliación','Entrar en el sistema y hacer pruebas para confirmar que funciona. Dar una actualización el 5 de octubre de 2026. La validación sigue pendiente.'),('factoring','gb','Factoring','Analizar la solución de factoring.'),('credit','gb','Pólizas de crédito','Preparar una demo de la solución.'),('payroll','gb','Ficheros de nóminas','Tratar la integración de ficheros de nóminas.'),('vw-work','vw','Volkswagen','Frente de trabajo; alcance todavía no especificado.'),('bcn-work','bcn','Barcelona','Frente de trabajo; alcance todavía no especificado.'),('offers','kyr','Antecedentes y entregas','Reunir contexto para elaborar ofertas en el proyecto existente de Claude. No consta ninguna entrega concreta.'),('support','gon','Soporte','Frente de soporte; pendientes todavía no especificados.'),('hours','internal','Reporte de horas','Recordar reportar las horas. No se ha indicado periodicidad ni fecha.')]
            db.executemany('INSERT INTO matters VALUES (?,?,?,?)',matters)
            source='specification'
            db.execute('INSERT INTO captures VALUES (?,?,?,?,?,?,?,?,?)',(source,now(),'Datos aportados por el usuario en docs/ESPECIFICACION.md. Conciliación: entrar en el sistema, hacer pruebas (máximo 2 horas) y dar una actualización el lunes 5 de octubre de 2026. Otros asuntos sin fechas ni estimaciones.','Especificación del usuario',None,None,'accepted','{}','user'))
            for mid,title,deadline,estimate in [('conciliation','Probar la conciliación',None,120),('conciliation','Dar una actualización de la conciliación','2026-10-05',None),('factoring','Analizar la solución de factoring',None,None),('credit','Preparar una demo de pólizas de crédito',None,None),('payroll','Tratar la integración de ficheros de nóminas',None,None),('hours','Reportar las horas',None,None)]:
                db.execute('INSERT INTO tasks (id,matter_id,title,commitment,estimate,source_id,created) VALUES (?,?,?,?,?,?,?)',(uid(),mid,title,deadline,estimate,source,now()))
            db.execute("INSERT INTO settings VALUES ('initialized','true')")
            db.execute("INSERT INTO settings VALUES ('timezone','Europe/Madrid')")
