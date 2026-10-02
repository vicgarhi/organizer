import unittest, tempfile, tarfile, io, sys, subprocess, json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from storage import validate
from operations import load_bundle

class Deployment(unittest.TestCase):
    def archive(self,extra=None):
        buf=io.BytesIO()
        with tarfile.open(fileobj=buf,mode='w:gz') as t:
            for name in ['data','proxydata']:
                m=tarfile.TarInfo(name);m.type=tarfile.DIRTYPE;t.addfile(m)
            m=tarfile.TarInfo('data/organizer.sqlite3');m.size=3;t.addfile(m,io.BytesIO(b'db!'))
            if extra:t.addfile(extra,io.BytesIO(b'x') if extra.isfile() else None)
        return buf.getvalue()
    def test_volume_format(self):
        with tarfile.open(fileobj=io.BytesIO(self.archive()),mode='r:gz') as t:self.assertEqual(len(validate(t)),3)
    def test_no_traversal_links_or_unknown_roots(self):
        for name,kind in [('data/../../etc/passwd',tarfile.REGTYPE),('/data/a',tarfile.REGTYPE),('elsewhere/a',tarfile.REGTYPE),('data/link',tarfile.SYMTYPE),('data/hard',tarfile.LNKTYPE)]:
            m=tarfile.TarInfo(name);m.type=kind;m.size=1 if kind==tarfile.REGTYPE else 0;m.linkname='/etc'
            with tarfile.open(fileobj=io.BytesIO(self.archive(m)),mode='r:gz') as t:
                with self.assertRaises(ValueError):validate(t)
    def bundle(self,path,config):
        with tarfile.open(path,'w:gz') as t:
            contents={'manifest.json':json.dumps({'format':'enorden-physical-v1'}).encode(),'environment.env':config.encode(),'volumes.tar.gz':self.archive()}
            for name,blob in contents.items():
                m=tarfile.TarInfo(name);m.size=len(blob);t.addfile(m,io.BytesIO(blob))
    def test_bundle_preserves_config_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'backup.tar.gz';self.bundle(path,'COMPOSE_PROJECT_NAME=enorden\nCADDY_CONFIG=deploy/Caddyfile\nINSTALL_OFFLINE=true\n')
            config,blob=load_bundle(path);self.assertIn(b'INSTALL_OFFLINE=true',config);self.assertTrue(blob)
    def test_reject_unknown_settings_before_restore(self):
        for config in ['COMPOSE_PROJECT_NAME=other\n','CADDY_CONFIG=/etc/passwd\n','COMPOSE_FILE=evil.yaml\n','APP_ADDRESS=${HOME}\n']:
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'backup.tar.gz';self.bundle(path,config)
                with self.assertRaises(ValueError):load_bundle(path)
    def test_package_contains_no_data_or_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'release.tar.gz'
            subprocess.run([sys.executable,'scripts/package_release.py',str(path)],check=True,capture_output=True)
            with tarfile.open(path) as t:
                names=t.getnames()
                self.assertTrue('en-orden/deploy/wheels/.keep' in names)
                self.assertFalse(any('/.data/' in n or n.endswith('/.env') or '/backups/' in n or '/.venv/' in n for n in names))
            self.assertTrue(Path(str(path)+'.sha256').is_file())

if __name__=='__main__':unittest.main()
