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

    def test_mac_options_reach_build_and_model_preparation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'scripts').mkdir()
            shutil.copyfile(ROOT/'scripts/start_extension.sh',root/'scripts/start_extension.sh')
            binary=root/'bin';binary.mkdir();log=root/'commands'
            docker=binary/'docker'
            docker.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$SCENEGUARD_TEST_LOG"\nexit 0\n');docker.chmod(0o755)
            env={**os.environ,'PATH':str(binary)+':'+os.environ['PATH'],'SCENEGUARD_TEST_LOG':str(log),
                 'SCENEGUARD_PLATFORM':'linux/amd64','SCENEGUARD_COMPOSE_OVERRIDE':'compose.macos.yaml','SCENEGUARD_USE_DOCKER_PYTHON':'1'}
            subprocess.run(['bash',str(root/'scripts/start_extension.sh')],env=env,check=True,capture_output=True,timeout=10)
            lines=log.read_text().splitlines()
            self.assertTrue(any('run --rm --platform linux/amd64' in x and 'initialize_local.py' in x for x in lines))
            self.assertTrue(any('-f compose.macos.yaml build' in x for x in lines))
            self.assertTrue(any('run --rm --platform linux/amd64' in x and 'prepare_laya.py' in x for x in lines))
            self.assertTrue(any('-f compose.macos.yaml up --no-build -d' in x for x in lines))

if __name__=='__main__':unittest.main()
