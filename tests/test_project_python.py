from __future__ import annotations

import os
import pathlib
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "scripts" / "project-python"
VALIDATOR = ROOT / "scripts" / "validate-repo.sh"


class ProjectPythonTests(unittest.TestCase):
    def test_resolver_uses_exact_tracked_version(self) -> None:
        expected = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
        result = subprocess.run(
            [str(RESOLVER), "-c", "import platform; print(platform.python_version())"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.stdout.strip(), expected)

    def test_invalid_explicit_interpreter_fails_closed(self) -> None:
        environment = os.environ.copy()
        environment["CODEX_PROJECT_PYTHON"] = "/bin/sh"
        result = subprocess.run(
            [str(RESOLVER), "-c", "print('must not run')"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("could not report a Python version", result.stderr)
        self.assertNotIn("must not run", result.stdout)

    def test_repository_validator_uses_project_resolver(self) -> None:
        validator = VALIDATOR.read_text(encoding="utf-8")

        self.assertIn('PROJECT_PYTHON="$ROOT_DIR/scripts/project-python"', validator)
        self.assertNotRegex(validator, r"(?m)^\s*python3(?:\s|$)")

    def test_readme_source_checkout_commands_use_project_resolver(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertNotRegex(
            readme,
            r'(?m)^python3 (?:scripts/|skills/|"\$(?:ADAPTER|HOOK_RUNNER)")',
        )


if __name__ == "__main__":
    unittest.main()
