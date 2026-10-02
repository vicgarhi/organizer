"""Writes private VAPID configuration locally; never prints private keys."""
import os, sys, base64
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.store import DATA
if len(sys.argv)!=2 or not sys.argv[1].startswith('mailto:') or not '@' in sys.argv[1]:raise SystemExit('Uso: .venv/bin/python scripts/generate_push.py mailto:tu-correo@example.com')
path=DATA/'push.env'
if path.exists():raise SystemExit('Ya existe .data/push.env. No se ha sustituido la identidad VAPID.')
key=ec.generate_private_key(ec.SECP256R1())
encode=lambda b:base64.urlsafe_b64encode(b).decode().rstrip('=')
private=encode(key.private_numbers().private_value.to_bytes(32,'big'))
public=encode(key.public_key().public_bytes(Encoding.X962,PublicFormat.UncompressedPoint))
subject=sys.argv[1]
if any(c in subject for c in "'\n\r\"`$;\\ "):raise SystemExit('Contacto no válido.')
path.write_text(f"VAPID_PRIVATE_KEY='{private}'\nVAPID_PUBLIC_KEY='{public}'\nVAPID_SUBJECT='{subject}'\n")
path.chmod(0o600)
print('Configuración guardada en .data/push.env. Cárgala en el servidor sin publicarla. Reinicia y activa cada dispositivo desde Ajustes.')
