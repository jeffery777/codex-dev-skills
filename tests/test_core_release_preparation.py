"""Fixed adoption preparation and historical-baseline regression tests; no models."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location("test_development_" + name, ROOT / "scripts" / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prep = script("verify-core-release-preparation.py")
candidate = script("eval-core-feedback-candidate.py")
formal = script("validate-core-contract-snapshot.py")


class ReleasePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir="/private/tmp", prefix="core-preparation-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("vendor/engineering-workflow-core", "tests/fixtures/core-feedback-baseline",
                     "tests/fixtures/core-feedback-candidate", "tests/fixtures/core-release-preparation"):
            shutil.copytree(ROOT / name, self.root / name)
        for name in ("vendor/engineering-workflow-core.lock.json", "tests/fixtures/core-feedback-baseline.lock.json",
                     "tests/fixtures/core-feedback-candidate.lock.json", "tests/fixtures/core-feedback-cases.json",
                     "tests/fixtures/core-release-preparation.lock.json", "scripts/verify-core-release-preparation.py",
                     "scripts/eval-core-feedback-candidate.py", "scripts/validate-core-contract-snapshot.py"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
            target.chmod(0o644)

    def rejected(self):
        with self.assertRaises((prep.PreparationError, OSError, ValueError)):
            prep.inspect(self.root)

    def test_exact_preparation_retains_publication_gate_and_formal_default(self):
        value = prep.inspect(self.root)
        self.assertEqual(value["files"], 20)
        self.assertEqual(value["status"], "prepared-publication-pending")
        self.assertIsNone(value["publication_revision"])
        self.assertIsNone(value["tag_object"])
        for key in ("formal_core_adopted", "runtime_qualified", "merge_authorized"):
            self.assertIs(value[key], False)
        self.assertEqual(formal.validate(self.root)["core_revision"], prep.BASELINE_REVISION)

    def test_historical_baseline_tamper_is_not_hidden_by_insert_only(self):
        path = self.root / "tests/fixtures/core-feedback-baseline/README.md"
        path.write_bytes(b"short corrupt baseline\n")
        self.rejected()

    def test_new_unknown_or_claimed_published_manifest_is_rejected(self):
        path = self.root / "tests/fixtures/core-release-preparation.lock.json"
        original = path.read_bytes()
        for field, value in (("reviewed_head", "0" * 40), ("formal_core_adopted", True),
                             ("publication_revision", "0" * 40), ("tag_object", "0" * 40)):
            changed = json.loads(original)
            changed[field] = value
            path.write_text(json.dumps(changed))
            self.rejected()
        path.write_bytes(original)

    def test_original_baseline_pin_cannot_be_replaced(self):
        path = self.root / "tests/fixtures/core-feedback-baseline.lock.json"
        path.write_bytes(path.read_bytes() + b" ")
        self.rejected()

    def test_tamper_missing_extra_and_empty_directory(self):
        fixture = self.root / "tests/fixtures/core-release-preparation"
        path = fixture / "LICENSE"
        original = path.read_bytes()
        path.write_bytes(original + b"changed")
        self.rejected()
        path.unlink()
        self.rejected()
        path.write_bytes(original)
        for name in ("extra.md", "empty"):
            extra = fixture / name
            extra.mkdir() if name == "empty" else extra.write_text("unexpected\n")
            self.rejected()
            extra.rmdir() if extra.is_dir() else extra.unlink()

    def test_unsafe_modes_symlink_hardlink_fifo_are_rejected(self):
        path = self.root / "tests/fixtures/core-feedback-baseline/LICENSE"
        original = path.read_bytes()
        path.chmod(0o755)
        self.rejected()
        path.unlink()
        path.symlink_to(ROOT / "LICENSE")
        self.rejected()
        path.unlink()
        os.link(self.root / "tests/fixtures/core-feedback-baseline/README.md", path)
        self.rejected()
        path.unlink()
        os.mkfifo(path, 0o644)
        self.rejected()
        path.unlink()
        path.write_bytes(original)

    def test_symlink_ancestor_is_rejected(self):
        path = self.root / "tests/fixtures/core-feedback-baseline"
        real = path.with_name("real-baseline")
        path.rename(real)
        path.symlink_to(real, target_is_directory=True)
        self.rejected()

    def test_historical_eval_survives_a_future_formal_vendor_advance(self):
        vendor = self.root / "vendor/engineering-workflow-core"
        shutil.rmtree(vendor)
        shutil.copytree(self.root / "tests/fixtures/core-release-preparation", vendor)
        # Only this unit boundary stubs a future formal-loader acceptance.
        # The real current loader is separately required to reject this tree.
        with self.assertRaises(formal.SnapshotError):
            formal.validate(self.root)
        original_spec = importlib.util.spec_from_file_location
        validations = []

        def selected_spec(name, path):
            spec = original_spec(name, path)
            if name == "formal_core_links":
                execute = spec.loader.exec_module

                def checked_module(module):
                    execute(module)
                    module.validate = lambda root: validations.append(root)
                spec.loader.exec_module = checked_module
            return spec

        with patch.object(candidate, "ROOT", self.root), patch.object(
                candidate.importlib.util, "spec_from_file_location", side_effect=selected_spec):
            _, _, cases = candidate.inspect(self.root / "tests/fixtures/core-feedback-candidate")
        self.assertEqual(len(cases), 9)
        self.assertEqual(validations, [self.root])
        self.assertNotEqual((vendor / "README.md").read_bytes(), prep.baseline(self.root)["README.md"])

    def test_preparation_cannot_be_an_ordinary_or_history_lock(self):
        value = json.loads((ROOT / "vendor/engineering-workflow-core.lock.json").read_text())
        value["source"]["revision"] = prep.REVIEWED_HEAD
        for history in (False, True):
            with self.assertRaises(formal.SnapshotError):
                formal.parse_lock(json.dumps(value).encode(), allow_reviewed_history=history)

    def test_cli_publication_requirement_fails_closed(self):
        command = [sys.executable, "-B", str(ROOT / "scripts/verify-core-release-preparation.py")]
        result = subprocess.run(command + ["--require-publication"], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIsNone(json.loads(result.stdout)["tag_object"])

    def test_bad_json_is_rejected_without_coercion(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'\xff'):
            with self.assertRaises(ValueError):
                prep.parse(raw)

    def test_supported_plain_python_entries_do_not_create_bytecode(self):
        env = dict(os.environ)
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        for name, options in (("verify-core-release-preparation.py", []),
                              ("eval-core-feedback-candidate.py", ["--prompt"])):
            result = subprocess.run([sys.executable, str(self.root / "scripts" / name), *options],
                                    cwd=self.root, env=env, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(list(self.root.rglob("__pycache__")))

    def test_developer_files_are_not_distributed(self):
        catalog = (ROOT / "catalog.yaml").read_text()
        generated = (ROOT / "scripts/sync-plugin-package.py").read_text()
        for name in ("verify-core-release-preparation.py", "core-release-preparation", "core-feedback-baseline"):
            self.assertNotIn(name, catalog)
            self.assertNotIn(name, generated)

    def test_provenance_exception_requires_fixed_preparation_and_keeps_active_checks(self):
        source = (ROOT / "scripts/validate-repo.sh").read_text()
        function = "check_no_provider_terms() {" + source.split(
            "check_no_provider_terms() {", 1)[1].split("\ncheck_sensitive_private_terms()", 1)[0]
        command = "set -euo pipefail\nfail() { exit 34; }\nok() { :; }\n" + function + "\ncheck_no_provider_terms\n"
        output = self.root / "output"
        output.mkdir()
        env = dict(os.environ, PROJECT_PYTHON=sys.executable, TMP_DIR=str(output))

        def run():
            return subprocess.run(["bash", "-c", command], cwd=self.root, env=env,
                                  capture_output=True, timeout=20).returncode

        self.assertEqual(run(), 0)
        active = self.root / "active.md"
        active.write_text("cl" + "aude active integration\n")
        self.assertNotEqual(run(), 0)
        active.unlink()
        provenance = self.root / "tests/fixtures/core-release-preparation/docs/provenance/source-map.md"
        provenance.write_bytes(provenance.read_bytes() + b"\nChanged fixed provenance.\n")
        self.assertNotEqual(run(), 0)


if __name__ == "__main__":
    unittest.main()
