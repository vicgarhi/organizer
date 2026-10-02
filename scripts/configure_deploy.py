#!/usr/bin/env python3
"""Create a non-secret deployment configuration; never overwrite an existing .env."""
import argparse, re, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description='Configurar En orden para Docker en un LXC')
parser.add_argument('--mode',choices=['http','https','internal'],default='http')
parser.add_argument('--domain',help='Dominio DNS para HTTPS, sin protocolo ni ruta')
parser.add_argument('--http-port',type=int,default=80)
parser.add_argument('--https-port',type=int,default=443)
a=parser.parse_args()
if not all(1<=p<=65535 for p in [a.http_port,a.https_port]) or a.http_port==a.https_port:parser.error('Puertos distintos entre 1 y 65535.')
if a.mode!='http':
    domain=(a.domain or '').lower()
    if len(domain)>253 or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',domain):parser.error('Se necesita un dominio DNS válido (ejemplo: organizador.example.com).')
else:
    if a.domain:parser.error('--domain solo se usa con HTTPS.')
    domain=':80'
path=ROOT/'.env'
contents=(f'COMPOSE_PROJECT_NAME=enorden\nAPP_ADDRESS={domain}\nCADDY_CONFIG=deploy/Caddyfile'+('.internal' if a.mode=='internal' else '')+f'\nHTTP_PORT={a.http_port}\nHTTPS_PORT={a.https_port}\nCOOKIE_SECURE='+('false' if a.mode=='http' else 'true')+'\nAI_MODEL=gpt-4.1-mini\n# OPENAI_API_KEY=\n# VAPID_PRIVATE_KEY=\n# VAPID_PUBLIC_KEY=\n# VAPID_SUBJECT=mailto:you@example.com\n')
contents+='INSTALL_OFFLINE='+('true' if list((ROOT/'deploy/wheels').glob('*.whl')) else 'false')+'\n'
try:
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
except FileExistsError:raise SystemExit('Ya existe .env. No se ha sobrescrito. Edita ese fichero privado para cambiar el modo.')
with os.fdopen(fd,'w') as f:f.write(contents)
print(f'.env creado con permisos 0600. Modo: {a.mode}. No se ha generado ni mostrado ninguna contraseña.')
print('Siguiente paso: ./scripts/deploy.sh up')
