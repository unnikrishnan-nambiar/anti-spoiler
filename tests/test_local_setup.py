"""Local installer credential safety and Docker command construction."""
import os,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class LocalSetupTests(unittest.TestCase):
    def test_initialization_preserves_existing_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'scripts').mkdir()
            for name in ('initialize_local.py','bootstrap.py'):shutil.copyfile(ROOT/'scripts'/name,root/'scripts'/name)
            shutil.copyfile(ROOT/'.env.example',root/'.env.example')
            script=root/'scripts/initialize_local.py'
            subprocess.run(['python',str(script)],check=True,capture_output=True)
            before=(root/'.env').read_text()
            values=dict(line.split('=',1) for line in before.splitlines() if '=' in line and not line.startswith('#'))
            for key in ('ADMIN_PASSWORD','JWT_SECRET','POSTGRES_PASSWORD','LAYA_SERVICE_TOKEN'):self.assertGreaterEqual(len(values[key]),32)
            self.assertEqual((root/'.env').stat().st_mode&0o777,0o600)
            subprocess.run(['python',str(script)],check=True,capture_output=True)
            self.assertEqual((root/'.env').read_text(),before)

    def test_native_launcher_uses_prepared_python_without_docker(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'scripts').mkdir()
            shutil.copyfile(ROOT/'scripts/start_extension.sh',root/'scripts/start_extension.sh')
            (root/'.venv/bin').mkdir(parents=True);(root/'.local/models/laya').mkdir(parents=True)
            (root/'.local/models/laya/provenance.json').write_text('{}')
            log=root/'commands';python=root/'.venv/bin/python'
            python.write_text('#!/bin/sh\nprintf "%s\\n" "$*" > "$SCENEGUARD_TEST_LOG"\n');python.chmod(0o755)
            subprocess.run(['bash',str(root/'scripts/start_extension.sh'),'--port','8123'],
                           env={**os.environ,'SCENEGUARD_TEST_LOG':str(log)},check=True)
            self.assertEqual(log.read_text().strip(),'scripts/run_extension.py --port 8123')

if __name__=='__main__':unittest.main()
