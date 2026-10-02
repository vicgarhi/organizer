"""Offline physical volume backup/restore for the network-isolated storage container.
Contains private password hashes and the private Caddy CA. No secrets are printed.
"""
import sys, tarfile, io, shutil, os
from pathlib import Path, PurePosixPath
ROOTS={'data':Path('/data'),'proxydata':Path('/proxydata')}
MAX_COMPRESSED=128*1024*1024
MAX_EXPANDED=2*1024*1024*1024

def validate(archive):
    members=archive.getmembers();seen=set()
    if len(members)>100000 or sum(m.size for m in members)>MAX_EXPANDED:raise ValueError('Copia demasiado grande.')
    for m in members:
        p=PurePosixPath(m.name)
        if not p.parts or p.parts[0] not in ROOTS or p.is_absolute() or '..' in p.parts or '\\' in m.name or not (m.isdir() or m.isfile()):raise ValueError('Ruta o tipo de archivo no permitido.')
        if str(p) in seen:raise ValueError('Ruta duplicada.')
        seen.add(str(p))
    if not {'data','proxydata'}.issubset(seen):raise ValueError('Faltan los volúmenes esperados.')
    if 'data/organizer.sqlite3' not in seen:raise ValueError('Falta la base de datos.')
    return members

def restore(blob):
    with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as archive:
        members=validate(archive)
        for root in ROOTS.values():
            root.mkdir(exist_ok=True)
            for p in root.iterdir():
                if p.is_dir() and not p.is_symlink():shutil.rmtree(p)
                else:p.unlink()
        # All paths/types were validated before any deletion. No links/devices.
        for m in members:
            p=PurePosixPath(m.name);dest=ROOTS[p.parts[0]].joinpath(*p.parts[1:])
            if m.isdir():dest.mkdir(parents=True,exist_ok=True)
            else:
                dest.parent.mkdir(parents=True,exist_ok=True)
                with archive.extractfile(m) as src,dest.open('wb') as out:shutil.copyfileobj(src,out,1024*1024)
                dest.chmod(m.mode & 0o777)
        # Data volume belongs to the unprivileged application user, including root.
        for root in ROOTS.values():
            owner=10001 if root==ROOTS['data'] else 0
            os.chown(root,owner,owner)
            for p in root.rglob('*'):os.chown(p,owner,owner)
    print('Volúmenes recuperados.',file=sys.stderr)

if __name__=='__main__':
    command=sys.argv[1] if len(sys.argv)==2 else ''
    if command=='backup':
        if not (ROOTS['data']/'organizer.sqlite3').is_file():raise SystemExit('No hay base de datos; arranca la aplicación primero.')
        with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as archive:
            for name,path in ROOTS.items():archive.add(path,arcname=name)
    elif command=='restore':
        blob=sys.stdin.buffer.read(MAX_COMPRESSED+1)
        if len(blob)>MAX_COMPRESSED:raise SystemExit('Copia demasiado grande: límite comprimido de 128 MB.')
        restore(blob)
    else:raise SystemExit('Uso: storage.py backup | restore')
