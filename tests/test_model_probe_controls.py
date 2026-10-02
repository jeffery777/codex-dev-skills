"""Counterexamples for opt-in sandbox probe evidence, without a sandbox/model."""
import importlib.util
import pathlib
import shlex
import subprocess
import tempfile
import unittest


class ReaderControlTests(unittest.TestCase):
    def test_unavailable_reader_cannot_report_access_denied(self):
        for name in ['verify-model-permissions', 'verify-model-dispatch']:
            with self.subTest(probe=name), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                (root / 'reader-sentinel').write_text('reader-ok')
                (root / 'protected').write_text('synthetic')
                spec = importlib.util.spec_from_file_location(name, pathlib.Path(__file__).resolve().parents[1] / 'scripts' / (name + '.py'))
                probe = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(probe)
                missing = str(root / 'missing-reader')
                command = probe.reader_guard(missing) + 'if ' + shlex.quote(missing) + ' protected >/dev/null; then echo violation > violation; fi'
                result = subprocess.run(['/bin/sh', '-c', command], cwd=root, capture_output=True)
                self.assertEqual(result.returncode, 12)
                self.assertFalse((root / 'reader-verified').exists())
                self.assertFalse((root / 'violation').exists())
                # With a working reader and no isolation, the same probe must
                # observe the forbidden read, rather than falsely pass.
                result = subprocess.run(['/bin/sh', '-c', probe.reader_guard() + 'if /bin/cat protected >/dev/null; then echo violation > violation; fi'], cwd=root, capture_output=True)
                self.assertEqual(result.returncode, 0)
                self.assertTrue((root / 'reader-verified').exists())
                self.assertTrue((root / 'violation').exists())


class ContainerControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('isolation_probe', pathlib.Path(__file__).resolve().parents[1] / 'scripts/verify-model-isolation.py')
        cls.probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.probe)

    def test_image_cannot_supply_conflicting_or_unbounded_mounts(self):
        for volumes in [[], {str(i): {} for i in range(17)}, {'/': {}}, {'/workspace': {}},
                        {'/workspace/child': {}}, {'/tmp': {}}, {'/var/../workspace': {}},
                        {'/var:rw': {}}, {'relative': {}}, {42: {}}]:
            with self.subTest(volumes=volumes), self.assertRaises(ValueError):
                self.probe.validate_image_volumes(volumes)
        self.assertEqual(self.probe.validate_image_volumes(None), {})
        self.assertEqual(self.probe.validate_image_volumes({'/var/lib/postgresql/data': {}}), {'/var/lib/postgresql/data': {}})

    def test_mount_readback_rejects_other_writable_sources_and_image_volumes(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = pathlib.Path(directory).resolve()
            bind = {'Type': 'bind', 'Destination': '/workspace', 'Source': str(workspace)}
            self.probe.validate_mounts([bind], workspace)
            for mounts in [[], [bind, {'Type': 'volume'}], [bind, dict(bind)],
                           [dict(bind, Source='/')], [dict(bind, Destination='/control')]]:
                with self.subTest(mounts=mounts), self.assertRaises(ValueError):
                    self.probe.validate_mounts(mounts, workspace)


if __name__ == '__main__':
    unittest.main()
