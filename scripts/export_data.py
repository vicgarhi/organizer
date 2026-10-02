#!/usr/bin/env python3
"""Export the app ZIP format, including attachments but excluding authentication.
Run with the application stopped, or during a quiet migration window.
"""
import argparse, sys, json, zipfile, os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.store import DATA, DB, connect, rows, now
from app.main import BACKUP_TABLES
p=argparse.ArgumentParser(description='Exportar datos para migrarlos a otro servidor')
p.add_argument('output',type=Path);args=p.parse_args()
if not DB.is_file():raise SystemExit('No existe base de datos en DATA_DIR.')
if args.output.exists():raise SystemExit('La salida ya existe; no se ha sustituido.')
with connect() as db:
    db.execute('BEGIN')
    data={'version':1,'exported':now(),'tables':{t:rows(db,'SELECT * FROM '+t) for t in BACKUP_TABLES},'settings':rows(db,"SELECT * FROM settings WHERE key NOT LIKE 'push-%'")}
args.output.parent.mkdir(parents=True,exist_ok=True)
fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
try:
    with os.fdopen(fd,'wb') as out,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('data.json',json.dumps(data,ensure_ascii=False))
        for a in data['tables']['attachments']:
            if not (DATA/'attachments'/a['id']).is_file():raise ValueError('Falta un adjunto; no se ha completado la exportación.')
            z.write(DATA/'attachments'/a['id'],'attachments/'+a['id'])
except Exception:
    args.output.unlink(missing_ok=True);raise
print('Copia de migración guardada en:',args.output)
print('Contiene información privada, pero no contraseñas, sesiones, claves ni suscripciones.')
