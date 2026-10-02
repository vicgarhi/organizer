"""Interactive password rotation. Prints no credential values."""
import sys, getpass, json, secrets
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.main import password_hash
from app.store import DATA, connect, initialize
initialize()
a=getpass.getpass('Nueva contraseña (mínimo 12 caracteres): ')
b=getpass.getpass('Repite la contraseña: ')
if a!=b or len(a)<12: raise SystemExit('No se ha cambiado: contraseñas distintas o demasiado cortas.')
salt=secrets.token_hex(16)
p=DATA/'access.json';p.write_text(json.dumps({'salt':salt,'hash':password_hash(a,salt)}));p.chmod(0o600)
(DATA/'initial-password.txt').unlink(missing_ok=True)
with connect() as db:db.execute('DELETE FROM sessions')
print('Contraseña cambiada. Reinicia el servidor; todas las sesiones se han revocado. Si usas APP_PASSWORD, actualízala en el gestor de secretos o elimínala antes de reiniciar.')
