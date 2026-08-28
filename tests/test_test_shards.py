from __future__ import annotations

import io
import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "test-shards.py"
MANIFEST = ROOT / "tests" / "test-shards.yaml"


def load_subject():
    spec = importlib.util.spec_from_file_location("test_shards_subject", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load test-shards.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


subject = load_subject()


class TestShardManifestTests(unittest.TestCase):
    def write_fixture(
        self,
        root: pathlib.Path,
        *,
        shards: list[dict[str, object]] | None = None,
        extra: dict[str, object] | None = None,
    ) -> pathlib.Path:
        tests_dir = root / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_alpha.py").write_text(
            "import unittest\n\nclass Alpha(unittest.TestCase):\n    def test_ok(self): pass\n",
            encoding="utf-8",
        )
        (tests_dir / "test_beta.py").write_text(
            "import unittest\n\nclass Beta(unittest.TestCase):\n    def test_ok(self): pass\n",
            encoding="utf-8",
        )
        document: dict[str, object] = {
            "schema_version": 1,
            "test_root": "tests",
            "test_pattern": "test_*.py",
            "shards": shards
            if shards is not None
            else [
                {"id": "alpha", "modules": ["tests.test_alpha"]},
                {"id": "beta", "modules": ["tests.test_beta"]},
            ],
        }
        if extra:
            document.update(extra)
        manifest = tests_dir / "test-shards.yaml"
        manifest.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        return manifest

    def test_repository_manifest_is_an_exact_stable_partition(self) -> None:
        manifest = subject.load_manifest(MANIFEST, ROOT)

        self.assertEqual(tuple(sorted(manifest.shard_ids)), manifest.shard_ids)
        self.assertEqual(12, len(manifest.shards))
        self.assertIn("tests.test_test_shards", manifest.shards["repository-policy"])
        assigned = [module for modules in manifest.shards.values() for module in modules]
        discovered = {f"tests.{path.stem}" for path in (ROOT / "tests").glob("test_*.py")}
        self.assertEqual(discovered, set(assigned))
        self.assertEqual(len(discovered), len(assigned))

    def test_duplicate_unassigned_and_nonexistent_modules_fail_closed(self) -> None:
        cases = (
            (
                [
                    {"id": "alpha", "modules": ["tests.test_alpha"]},
                    {
                        "id": "beta",
                        "modules": ["tests.test_alpha", "tests.test_beta"],
                    },
                ],
                "duplicate module",
            ),
            ([{"id": "alpha", "modules": ["tests.test_alpha"]}], "unassigned"),
            (
                [
                    {
                        "id": "alpha",
                        "modules": ["tests.test_alpha", "tests.test_missing"],
                    },
                    {"id": "beta", "modules": ["tests.test_beta"]},
                ],
                "regular file",
            ),
        )
        for shards, message in cases:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temp:
                root = pathlib.Path(temp)
                manifest = self.write_fixture(root, shards=shards)
                with self.assertRaisesRegex(subject.ManifestError, message):
                    subject.load_manifest(manifest, root)

    def test_schema_order_and_empty_shards_fail_closed(self) -> None:
        cases = (
            (
                [
                    {"id": "beta", "modules": ["tests.test_beta"]},
                    {"id": "alpha", "modules": ["tests.test_alpha"]},
                ],
                None,
                "shard ids must be lexically sorted",
            ),
            (
                [
                    {
                        "id": "alpha",
                        "modules": ["tests.test_beta", "tests.test_alpha"],
                    }
                ],
                None,
                "modules must be lexically sorted",
            ),
            ([{"id": "alpha", "modules": []}], None, "must contain modules"),
            (None, {"unexpected": True}, "manifest keys differ"),
        )
        for shards, extra, message in cases:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temp:
                root = pathlib.Path(temp)
                manifest = self.write_fixture(root, shards=shards, extra=extra)
                with self.assertRaisesRegex(subject.ManifestError, message):
                    subject.load_manifest(manifest, root)

    def test_symlinked_test_entry_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            manifest = self.write_fixture(root)
            (root / "tests" / "test_link.py").symlink_to("test_alpha.py")
            with self.assertRaisesRegex(subject.ManifestError, "regular file"):
                subject.load_manifest(manifest, root)

    def test_nested_test_entry_requires_an_explicit_contract_update(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            manifest = self.write_fixture(root)
            nested = root / "tests" / "nested"
            nested.mkdir()
            (nested / "test_nested.py").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(subject.ManifestError, "nested test modules"):
                subject.load_manifest(manifest, root)

    def test_runner_uses_current_interpreter_and_explicit_modules(self) -> None:
        manifest = subject.ShardManifest(
            shards={"alpha": ("tests.test_alpha", "tests.test_beta")}
        )
        completed = subprocess.CompletedProcess([], 0)
        with mock.patch.object(subject.subprocess, "run", return_value=completed) as run:
            result = subject.run_shard(manifest, "alpha", ROOT)

        self.assertEqual(0, result)
        run.assert_called_once_with(
            [
                sys.executable,
                "-m",
                "unittest",
                "tests.test_alpha",
                "tests.test_beta",
            ],
            cwd=ROOT,
            check=False,
        )

    def test_run_all_runs_every_shard_in_manifest_order_after_failure(self) -> None:
        manifest = subject.ShardManifest(
            shards={"alpha": ("tests.test_alpha",), "beta": ("tests.test_beta",)}
        )
        with (
            mock.patch.object(subject, "run_shard", side_effect=(1, 0)) as run,
            mock.patch.object(subject.sys, "stderr", new_callable=io.StringIO) as stderr,
        ):
            result = subject.run_all(manifest, ROOT)

        self.assertEqual(1, result)
        self.assertEqual("[FAIL] Failed shards: alpha\n", stderr.getvalue())
        self.assertEqual(
            [mock.call(manifest, "alpha", ROOT), mock.call(manifest, "beta", ROOT)],
            run.call_args_list,
        )

    def test_run_all_returns_zero_when_every_shard_succeeds(self) -> None:
        manifest = subject.ShardManifest(
            shards={"alpha": ("tests.test_alpha",), "beta": ("tests.test_beta",)}
        )
        with mock.patch.object(subject, "run_shard", side_effect=(0, 0)) as run:
            result = subject.run_all(manifest, ROOT)

        self.assertEqual(0, result)
        self.assertEqual(2, run.call_count)


if __name__ == "__main__":
    unittest.main()
