"""Offline tests only: never install tools, authenticate, or create resources."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ReferenceTests(unittest.TestCase):
    def run_script(self, name, destination, **environment):
        return subprocess.run(['bash', str(ROOT / 'scripts' / name), str(destination)],
                              env={**os.environ, **environment}, capture_output=True, text=True)

    def test_v2_render(self):
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_script('render-v2.sh', temp, IMAGE_REFERENCE='example.invalid/agent/runtime:local')
            self.assertEqual(result.returncode, 0, result.stderr)
            content = (Path(temp) / 'spec.yaml').read_text()
            self.assertIn('image: "example.invalid/agent/runtime:local"', content)
            self.assertNotIn('@IMAGE_REFERENCE@', content)

    def test_v2_rejects_injection(self):
        for reference in ['bad\nvalue', 'bad"value', 'bad|value', 'bad&value', 'bad value', '']:
            with self.subTest(reference=reference), tempfile.TemporaryDirectory() as temp:
                result = self.run_script('render-v2.sh', temp, IMAGE_REFERENCE=reference)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((Path(temp) / 'spec.yaml').exists())

    def test_v3_stages_exact_source(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(self.run_script('stage-v3.sh', temp).returncode, 0)
            expected = {'amp.yaml', 'amp.dockerfile', 'amp-context.md',
                        'scripts/install-toolchains.sh', 'scripts/refresh-node-lts.sh', 'scripts/verify-runtime.sh'}
            actual = {str(p.relative_to(temp)) for p in Path(temp).rglob('*') if p.is_file()}
            self.assertEqual(actual, expected)
            for name in expected:
                source = ROOT / (name if name.startswith('scripts/') else 'kits/v3/' + name)
                self.assertEqual((Path(temp) / name).read_bytes(), source.read_bytes())

    def test_nonroot_and_no_permission_bypass(self):
        for name in ['kits/v2/Dockerfile', 'kits/v3/amp.dockerfile']:
            content = (ROOT / name).read_text()
            self.assertIn('USER agent', content)
            self.assertIn('ENTRYPOINT ["amp"]', content)
            self.assertNotIn('--dangerously-allow-all', content)
        self.assertNotIn('--dangerously-allow-all', (ROOT / 'kits/v2/spec.yaml.in').read_text())

    def test_lts_and_shared_installer(self):
        self.assertIn('fnm list-remote --lts --latest', (ROOT / 'scripts/refresh-node-lts.sh').read_text())
        self.assertIn('process.release.lts', (ROOT / 'scripts/verify-runtime.sh').read_text())
        for name in ['kits/v2/Dockerfile', 'kits/v3/amp.dockerfile']:
            self.assertIn('COPY scripts/install-toolchains.sh', (ROOT / name).read_text())

    def test_ci_is_offline_and_read_only(self):
        workflows = list((ROOT / '.github/workflows').glob('*'))
        self.assertEqual(len(workflows), 1)
        content = workflows[0].read_text()
        for expected in ['contents: read', 'persist-credentials: false', 'runs-on: ubuntu-24.04', 'timeout-minutes: 5']:
            self.assertIn(expected, content)
        for forbidden in ['secrets.', 'self-hosted', 'pull_request_target', 'docker login', 'docker push', 'sbx ', '--privileged']:
            self.assertNotIn(forbidden, content)

if __name__ == '__main__':
    unittest.main()
