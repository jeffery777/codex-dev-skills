from __future__ import annotations

import importlib.util
import pathlib
import json
import shutil
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("hermes_package", ROOT / "scripts/hermes-package.py")
package = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(package)


class HermesPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name).resolve()
        self.skills = self.base / "skills"
        self.skills.mkdir(mode=0o700)

    def test_install_readback_and_no_overwrite(self):
        files = package.package()
        target = self.skills / package.NAMESPACE
        package.install(target, files)
        self.assertEqual([], package.compare(target, files))
        with self.assertRaises(FileExistsError):
            package.install(target, files)
        self.assertEqual([], package.compare(target, files))

    def test_diff_detects_modified_missing_extra_and_incomplete(self):
        files = package.package()
        target = self.skills / package.NAMESPACE
        package.install(target, files)
        sample = next(iter(files))
        (target / sample).write_text("changed")
        (target / package.MARKER).write_text("incomplete")
        (target / "unexpected").mkdir()
        errors = package.compare(target, files)
        self.assertIn(f"different bytes: {sample}", errors)
        self.assertIn(f"unexpected file: {package.MARKER}", errors)
        self.assertIn("unexpected directory: unexpected", errors)
        (target / sample).unlink()
        self.assertIn(f"missing file: {sample}", package.compare(target, files))

    def test_symlink_source_and_destination_rejected(self):
        linked = self.base / "linked"
        linked.symlink_to(self.skills, target_is_directory=True)
        with self.assertRaises(package.PackageError):
            package.target_root(str(linked / "skills"))
        sample = self.skills / "SKILL.md"
        sample.symlink_to(ROOT / "README.md")
        with self.assertRaises(package.PackageError):
            package.collisions(self.skills)
        with self.assertRaises(package.PackageError):
            package.regular_bytes(sample)

    def test_unsafe_roots_rejected(self):
        for path in ("relative/skills", str(self.base), str(self.skills / "../skills"),
                     str(ROOT / "skills"), str(pathlib.Path.home() / ".agents/skills"),
                     str(pathlib.Path.home() / ".codex/skills")):
            with self.subTest(path=path), self.assertRaises(package.PackageError):
                package.target_root(path)
        self.skills.chmod(0o777)
        with self.assertRaises(package.PackageError):
            package.target_root(str(self.skills))

    def test_same_name_skill_collision_by_name_or_directory(self):
        existing = self.skills / "renamed"
        existing.mkdir()
        (existing / "SKILL.md").write_text("---\nname: hermes-project-delivery\n---\n")
        with self.assertRaises(package.PackageError):
            package.collisions(self.skills)
        (existing / "SKILL.md").write_text("---\nname: other\n---\n")
        package.collisions(self.skills)
        (self.skills / "hermes-review-gate").mkdir()
        (self.skills / "hermes-review-gate/SKILL.md").write_text("---\nname: other\n---\n")
        with self.assertRaises(package.PackageError):
            package.collisions(self.skills)

    def test_interrupted_install_retains_failure_marker(self):
        target = self.skills / package.NAMESPACE
        with mock.patch.object(pathlib.Path, "chmod", side_effect=OSError("write failure")):
            with self.assertRaises(OSError):
                package.install(target, {"skills/example/SKILL.md": b"example"})
        self.assertTrue((target / package.MARKER).is_file())
        self.assertTrue(package.compare(target, package.package()))

    def test_readback_mismatch_or_exception_retains_marker(self):
        for failure in (["different bytes"], OSError("readback failed")):
            with self.subTest(failure=failure):
                target = self.base / ("mismatch" if isinstance(failure, list) else "exception")
                options = {"return_value": failure} if isinstance(failure, list) else {"side_effect": failure}
                with mock.patch.object(package, "compare", **options):
                    with self.assertRaises((package.PackageError, OSError)):
                        package.install(target, {"skills/example/SKILL.md": b"example"})
                self.assertTrue((target / package.MARKER).is_file())

    def test_unlisted_skill_files_rejected_without_reading(self):
        root = self.base / "source"
        shutil.copytree(ROOT / "hermes", root / "hermes")
        catalog = root / "hermes/catalog.json"
        value = json.loads(catalog.read_text())
        value["resources"] = []
        catalog.write_text(json.dumps(value))
        directory = root / "hermes/skills/hermes-project-delivery"
        for name in (".env", "cache"):
            extra = directory / name
            if name == "cache":
                extra.mkdir()
            else:
                extra.write_text("SYNTHETIC=not-a-real-credential")
            with self.subTest(name=name), mock.patch.object(package, "regular_bytes", wraps=package.regular_bytes) as read:
                with self.assertRaisesRegex(package.PackageError, "unlisted skill entry"):
                    package.package(root)
                self.assertNotIn(mock.call(extra), read.call_args_list)
            if extra.is_dir():
                extra.rmdir()
            else:
                extra.unlink()

    def test_native_yaml_name_forms_and_malformed_yaml(self):
        directory = self.skills / "renamed"
        directory.mkdir()
        path = directory / "SKILL.md"
        for header in ("name: hermes-project-delivery # comment", "'name': 'hermes-project-delivery'",
                       '  name: "hermes-project-delivery"', "name: >-\n  hermes-project-delivery"):
            for prefix in ("", "\ufeff"):
                with self.subTest(header=header, prefix=prefix):
                    path.write_text(prefix + "---\n" + header + "\n---\nbody\n")
                    with self.assertRaisesRegex(package.PackageError, "same-name"):
                        package.collisions(self.skills)
        path.write_text("---\nname: [broken\n---\nbody\n")
        with self.assertRaisesRegex(package.PackageError, "unparseable"):
            package.collisions(self.skills)

    def test_writable_ancestor_and_custom_codex_root_rejected(self):
        self.base.chmod(0o777)
        with self.assertRaisesRegex(package.PackageError, "ancestor"):
            package.target_root(str(self.skills))
        self.base.chmod(0o700)
        with mock.patch.dict("os.environ", {"CODEX_HOME": str(self.base)}):
            with self.assertRaisesRegex(package.PackageError, "Codex"):
                package.target_root(str(self.skills))

    def test_duplicate_yaml_keys_cannot_hide_collision(self):
        directory = self.skills / "renamed"
        directory.mkdir()
        path = directory / "SKILL.md"
        path.write_text("---\nname: hermes-project-delivery\n'name': other\n---\nbody\n")
        with self.assertRaisesRegex(package.PackageError, "duplicate"):
            package.collisions(self.skills)
        path.write_text("---\nname: other\nmetadata:\n  value: a\n  value: b\n---\nbody\n")
        with self.assertRaisesRegex(package.PackageError, "duplicate"):
            package.collisions(self.skills)

    def test_installed_adapter_reference_closure(self):
        files = package.package()
        import re
        for skill in package.SKILLS:
            name = f"skills/{skill}/SKILL.md"
            for ref in re.findall(r"`(\.\./\.\./[^` ]+)`", files[name].decode()):
                resolved = (ROOT / "skills" / skill / ref).resolve().relative_to(ROOT).as_posix()
                self.assertIn(resolved, files, (skill, ref))

    def test_hermes_continuation_template_contract(self):
        files = package.package()
        name = "templates/hermes/next-session-prompt.template.md"
        template = files[name].decode()
        self.assertIn("Use `hermes-task-continuation`", template)
        self.assertNotIn("CODEX_TEMPLATES_DIR", template)
        self.assertNotIn("$HOME/.codex", template)
        self.assertIn("../../policies/reusable-workflow-contract.md", template)
        self.assertIn("policies/reusable-workflow-contract.md", files)
        self.assertNotIn("templates/orchestration/next-session-prompt.template.md", files)

    def test_resource_paths_cannot_escape(self):
        for path in ("../private", "/etc/passwd", "docs/../.env", "docs//private", "docs\\private"):
            with self.subTest(path=path), self.assertRaises(package.PackageError):
                package.safe_relative(path)

    def test_codex_package_excludes_hermes_adapters(self):
        source = (ROOT / "scripts/sync-plugin-package.py").read_text()
        self.assertNotIn('"hermes/"', source)
        self.assertTrue(all(name.startswith("hermes-") for name in package.SKILLS))


if __name__ == "__main__":
    unittest.main()
