from __future__ import annotations

import os
import pathlib
import subprocess
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-repo.sh"


class ValidateRepositoryArgumentsTests(unittest.TestCase):
    def run_validator(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        # Parsing must reject invalid input before any validation preflight, including TMPDIR.
        environment["TMPDIR"] = "relative-temporary-directory"
        return subprocess.run(
            [str(VALIDATOR), *arguments],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_only_skip_unit_tests_is_accepted(self) -> None:
        script = VALIDATOR.read_text(encoding="utf-8")

        self.assertIn("SKIP_UNIT_TESTS=false", script)
        self.assertIn('parse_args "$@"', script)
        self.assertIn('run_unit_tests() {', script)
        self.assertIn("[SKIP] embedded unit-test group:", script)
        self.assertEqual(17, script.count("run_unit_tests "))
        self.assertEqual(12, script.count('scripts/eval-'))

    def test_invalid_arguments_fail_before_validation(self) -> None:
        cases = (
            (("--unexpected",), "unknown option: --unexpected"),
            (("--skip-unit-tests", "--skip-unit-tests"), "duplicate option: --skip-unit-tests"),
            (("--",), "unexpected option: --"),
            (("extra",), "unexpected positional argument: extra"),
        )
        for arguments, message in cases:
            with self.subTest(arguments=arguments):
                result = self.run_validator(*arguments)
                self.assertNotEqual(0, result.returncode)
                self.assertIn(message, result.stderr)
                self.assertNotIn("TMPDIR must be absolute", result.stderr)
                self.assertNotIn("[OK]", result.stdout)


if __name__ == "__main__":
    unittest.main()
