#!/usr/bin/env python3
"""Docker Compose operations. Never display resolved config or credential values."""
import argparse, subprocess, sys, tempfile, tarfile, io, json, os, shutil
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from storage import validate, MAX_COMPRESSED
COMPOSE=['docker','compose','--project-directory',str(ROOT),'-f',str(ROOT/'compose.yaml')]

def run(args,**kw):return subprocess.run(COMPOSE+args,check=True,**kw)
def up(build=False):run(['up','-d',*(['--build'] if build else []),'--wait','--wait-timeout','180'])
def backup():
    dest=ROOT/'backups';dest.mkdir(exist_ok=True,mode=0o700)
    name='enorden-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.tar.gz';path=dest/name
    with tempfile.TemporaryDirectory(prefix='enorden-backup-') as tmp:
        tmp=Path(tmp)
        stopped=False
        try:
            run(['stop','caddy','organizer']);stopped=True
            with (tmp/'volumes.tar.gz').open('wb') as out:run(['run','--rm','--no-deps','-T','storage','backup'],stdout=out)
            # Ensure a valid volume archive before keeping a recovery copy.
            with tarfile.open(tmp/'volumes.tar.gz','r:gz') as z:validate(z)
            shutil.copyfile(ROOT/'.env',tmp/'environment.env')
            (tmp/'manifest.json').write_text(json.dumps({'format':'enorden-physical-v1','created':datetime.now(timezone.utc).isoformat()}))
            fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            with os.fdopen(fd,'wb') as out,tarfile.open(fileobj=out,mode='w:gz') as z:
                for n in ['volumes.tar.gz','environment.env','manifest.json']:z.add(tmp/n,arcname=n)
        except Exception:
            path.unlink(missing_ok=True);raise
        finally:
            if stopped:up()
    print('Copia privada guardada:',path)
    print('Incluye credenciales de configuración y CA privada; guárdala cifrada fuera del LXC.')
    return path

def load_bundle(path):
    if path.stat().st_size>MAX_COMPRESSED:raise ValueError('Copia superior a 128 MB; usa una copia offline del volumen para conjuntos mayores.')
    with tarfile.open(path,'r:gz') as z:
        ms=z.getmembers()
        if {m.name for m in ms}!={'volumes.tar.gz','environment.env','manifest.json'} or len(ms)!=3 or any(not m.isfile() for m in ms) or sum(m.size for m in ms)>MAX_COMPRESSED:raise ValueError('Formato de copia no válido.')
        manifest=json.load(z.extractfile('manifest.json'))
        if manifest.get('format')!='enorden-physical-v1':raise ValueError('Versión no compatible.')
        config=z.extractfile('environment.env').read()
        if len(config)>65536:raise ValueError('Configuración demasiado grande.')
        # Recovery must not let an imported .env redirect mounts or load another file.
        allowed={'COMPOSE_PROJECT_NAME','APP_ADDRESS','CADDY_CONFIG','HTTP_PORT','HTTPS_PORT','COOKIE_SECURE','APP_PASSWORD','OPENAI_API_KEY','AI_MODEL','VAPID_PRIVATE_KEY','VAPID_PUBLIC_KEY','VAPID_SUBJECT','INSTALL_OFFLINE','CADDY_IMAGE'}
        for line in config.decode().splitlines():
            if line.strip() and not line.lstrip().startswith('#'):
                key,sep,value=line.partition('=')
                if not sep or key not in allowed:raise ValueError('Configuración no compatible.')
                if key=='COMPOSE_PROJECT_NAME' and value!='enorden':raise ValueError('Solo se recupera el proyecto enorden.')
                if key=='CADDY_CONFIG' and value not in ['deploy/Caddyfile','deploy/Caddyfile.internal']:raise ValueError('Ruta del proxy no válida.')
                if '${' in value or '\x00' in value:raise ValueError('Interpolación no permitida en la copia.')
        blob=z.extractfile('volumes.tar.gz').read()
        with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as volumes:validate(volumes)
    return config,blob

def restore(path):
    config,blob=load_bundle(path)  # Validate BEFORE stopping or changing anything.
    current=(ROOT/'.env').read_text()
    for line in current.splitlines():
        if line.startswith('COMPOSE_PROJECT_NAME=') and line!='COMPOSE_PROJECT_NAME=enorden':raise ValueError('Proyecto actual incompatible; no se han sustituido datos.')
    backup()  # Recovery copy of the current data and credentials, never discarded.
    run(['stop','caddy','organizer'])
    # Do not restore .env until data succeeds; use the currently configured volumes.
    # Both project names must be the default to prevent restoring a different volume.
    try:
        run(['run','--rm','--no-deps','-T','storage','restore'],input=blob)
        fd=os.open(ROOT/'.env',os.O_WRONLY|os.O_TRUNC,0o600)
        with os.fdopen(fd,'wb') as f:f.write(config)
        (ROOT/'.env').chmod(0o600)
        up()
    except Exception:
        print('Recuperación interrumpida. Conserva la copia previa en backups/ y revisa los servicios antes de arrancar.',file=sys.stderr);raise
    print('Copia recuperada. Se han restaurado datos, acceso, configuración y CA del proxy.')

def main():
    p=argparse.ArgumentParser(description='Operaciones de En orden en Docker')
    p.add_argument('action',choices=['up','status','logs','backup','restore','update','stop'])
    p.add_argument('archive',nargs='?',type=Path)
    p.add_argument('--confirm',action='store_true',help='Confirmar sustitución de datos al recuperar')
    a=p.parse_args()
    if not (ROOT/'.env').is_file():raise SystemExit('Configura primero: python3 scripts/configure_deploy.py --mode http')
    if a.action=='up':up(build=True)
    elif a.action=='status':run(['ps'])
    elif a.action=='logs':run(['logs','--tail','100'])
    elif a.action=='stop':run(['stop'])
    elif a.action=='backup':backup()
    elif a.action=='restore':
        if not a.archive or not a.confirm:p.error('Uso: restore copia.tar.gz --confirm. Sustituye los datos actuales; antes guarda una copia automática.')
        restore(a.archive.resolve())
    elif a.action=='update':
        run(['build','organizer'])  # Build first: a build failure does not stop the current app.
        backup();up();print('Actualización arrancada. La copia previa conserva datos/configuración; para volver al código anterior también debes conservar el paquete o ref anterior.')
if __name__=='__main__':
    try:main()
    except (ValueError,tarfile.TarError,OSError,subprocess.CalledProcessError) as e:print('Operación fallida: '+str(e),file=sys.stderr);sys.exit(1)
