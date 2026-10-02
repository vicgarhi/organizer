#!/usr/bin/env python3
"""Reproducible deployment bundle with an explicit allowlist; no data or secrets."""
import argparse, tarfile, hashlib, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--include-wheels',action='store_true');a=p.parse_args()
files=['Dockerfile','compose.yaml','.dockerignore','.env.example','.gitignore','README.md','requirements.txt','requirements.lock','requirements-dev.txt']
for directory in ['app','static','scripts','docs','deploy','tests']:
    files += [str(x.relative_to(ROOT)) for x in (ROOT/directory).rglob('*') if x.is_file() and '__pycache__' not in x.parts and x.suffix!='.pyc' and ('wheels' not in x.parts or x.name=='.keep' or a.include_wheels)]
a.output.parent.mkdir(parents=True,exist_ok=True)
with tarfile.open(a.output,'w:gz') as tar:
    for name in sorted(files):tar.add(ROOT/name,arcname='en-orden/'+name)
checksum=hashlib.sha256(a.output.read_bytes()).hexdigest()
a.output.with_suffix(a.output.suffix+'.sha256').write_text(checksum+'  '+a.output.name+'\n')
print('Paquete sin datos ni secretos:',a.output)
print('SHA256 guardado junto al paquete.')
