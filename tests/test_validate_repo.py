from __future__ import annotations

import json
import os
import pathlib
import shlex
import tempfile
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
        self.assertEqual(18, script.count("run_unit_tests "))
        # Count the existing evals separately from the fixed-pin preflight.
        fixed_pin_eval = 'scripts/eval-core-feedback-candidate.py'
        self.assertEqual(1, script.count(fixed_pin_eval))
        self.assertEqual(13, script.count('scripts/eval-'))
        script = script.replace(fixed_pin_eval, '<fixed-pin-preflight>', 1)
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



class ValidateRepositoryPrivacyTests(unittest.TestCase):
    def run_private_check(
        self, content: str, account: str = "privacy-fixture-account", *,
        id_status: int = 0, search_status: int | None = None,
        review_status: int | None = None, search_output: str = "",
        diagnostics: str = "", rg_config: str | None = None,
        filename: str = "README.md", blocked_output: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        source = VALIDATOR.read_text(encoding="utf-8")
        function = "check_sensitive_private_terms() {\n" + source.split(
            "check_sensitive_private_terms() {\n", 1
        )[1].split("\ncheck_legacy_private_names()", 1)[0]
        with tempfile.TemporaryDirectory(prefix="privacy-check-") as directory:
            root = pathlib.Path(directory)
            work, output, tools = root / "work", root / "output", root / "bin"
            for path in (work, output, tools):
                path.mkdir()
            if blocked_output is not None:
                (output / blocked_output).mkdir()
            (work / filename).write_text(content, encoding="utf-8")
            fake_id = tools / "id"
            fake_id.write_text(
                "#!/bin/sh\n[ \"$1\" = -un ] || exit 2\nprintf '%s\\n' "
                + shlex.quote(account) + "\nprintf '%s' " + shlex.quote(diagnostics)
                + " >&2\nexit " + str(id_status) + "\n", encoding="utf-8",
            )
            fake_id.chmod(0o755)
            if search_status is not None or review_status is not None:
                fake_search = tools / "rg"
                first_status = 1 if search_status is None else search_status
                second_status = first_status if review_status is None else review_status
                fake_search.write_text(
                    "#!/bin/sh\ncase \"$*\" in\n*--json*) status="
                    + str(second_status) + ";;\n*) status=" + str(first_status) + ";;\nesac\n"
                    + "[ \"$1\" = --no-config ] || exit 99\n"
                    + "printf '%s' " + shlex.quote(search_output) + "\n"
                    + "printf '%s' " + shlex.quote(diagnostics) + " >&2\nexit \"$status\"\n",
                    encoding="utf-8",
                )
                fake_search.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = str(tools) + os.pathsep + environment["PATH"]
            if rg_config is not None:
                config = root / "search-config"
                config.write_text(rg_config, encoding="utf-8")
                environment["RIPGREP_CONFIG_PATH"] = str(config)
            harness = (
                "set -euo pipefail\nTMP_DIR=" + shlex.quote(str(output)) + "\n"
                + "PROJECT_PYTHON=" + shlex.quote(str(ROOT / "scripts/project-python")) + "\n"
                + "fail() { printf '[FAIL] %s\\n' \"$*\" >&2; exit 42; }\n"
                + "ok() { printf '[OK] %s\\n' \"$*\"; }\n"
                + function + "\ncheck_sensitive_private_terms\n"
            )
            return subprocess.run(
                ["bash", "-c", harness], cwd=work, env=environment,
                capture_output=True, text=True, check=False,
            )

    def test_clean_content_passes_with_a_local_account(self) -> None:
        result = self.run_private_check("Public workflow instructions.\n")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("private paths and local user identifiers absent", result.stdout)

    def test_local_account_match_is_case_insensitive_and_not_echoed(self) -> None:
        marker = "PRIVACY-Fixture-Account"
        result = self.run_private_check(marker + "\n")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("private path or user identifier found", result.stderr)
        self.assertNotIn(marker, result.stdout + result.stderr)

    def test_absolute_home_path_is_rejected_without_echoing(self) -> None:
        marker = "/" + "Users/private-fixture/project"
        result = self.run_private_check(marker + "\n", account="runner")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("private path or user identifier found", result.stderr)
        self.assertNotIn(marker, result.stdout + result.stderr)

    def test_account_regex_characters_are_literal(self) -> None:
        for content, expected in (("fixtureXaccount\n", 0), ("fixture.account\n", 42)):
            with self.subTest(expected=expected):
                result = self.run_private_check(content, account="fixture.account")
                self.assertEqual(expected, result.returncode, result.stderr)

    def test_generic_service_accounts_do_not_flag_public_words(self) -> None:
        for account in ("root", "runner"):
            with self.subTest(account=account):
                result = self.run_private_check("root and runner are public terms.\n", account)
                self.assertEqual(0, result.returncode, result.stderr)

    def test_missing_account_information_fails_closed(self) -> None:
        for account, status in (("", 0), ("privacy-fixture-account", 1)):
            with self.subTest(status=status):
                result = self.run_private_check("Public text.\n", account, id_status=status)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("local account lookup", result.stderr)
                self.assertNotIn("[OK]", result.stdout)

    def test_search_error_does_not_report_privacy_success(self) -> None:
        result = self.run_private_check("Public text.\n", search_status=2)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("private path/user identifier scan failed", result.stderr)
        self.assertNotIn("[OK]", result.stdout)

    def test_sensitive_term_review_prints_locations_only(self) -> None:
        marker = "synthetic-private-text-not-for-logs"
        result = self.run_private_check("token: " + marker + "\n")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('"./README.md":1', result.stdout)
        self.assertNotIn(marker, result.stdout + result.stderr)

    def test_user_search_display_configuration_cannot_expose_content(self) -> None:
        marker = "synthetic-private-text-not-for-logs"
        result = self.run_private_check(
            "token " + marker + "\n", rg_config="--heading\n--color=always\n",
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('"./README.md":1', result.stdout)
        self.assertNotIn(marker, result.stdout + result.stderr)
        self.assertNotIn("\x1b", result.stdout)

    def test_colon_and_newline_filename_has_unambiguous_escaped_location(self) -> None:
        marker = "synthetic-private-text-not-for-logs"
        result = self.run_private_check(
            "token " + marker + "\n", filename="note:part\nnext.txt",
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('"./note:part\\nnext.txt":1', result.stdout)
        self.assertNotIn(marker, result.stdout + result.stderr)

    def test_second_search_error_never_reports_no_hits_or_echoes_partial_data(self) -> None:
        marker = "synthetic-private-text-not-for-logs"
        result = self.run_private_check(
            "Public text.\n", review_status=2, search_output=marker, diagnostics=marker,
        )
        self.assertEqual(42, result.returncode)
        self.assertIn("sensitive-term review scan failed", result.stderr)
        self.assertNotIn("review produced no hits", result.stdout)
        self.assertNotIn(marker, result.stdout + result.stderr)

    def test_first_search_error_does_not_echo_partial_data_or_diagnostics(self) -> None:
        marker = "synthetic-private-text-not-for-logs"
        result = self.run_private_check(
            "Public text.\n", search_status=2, search_output=marker, diagnostics=marker,
        )
        self.assertEqual(42, result.returncode)
        self.assertIn("private path/user identifier scan failed", result.stderr)
        self.assertNotIn(marker, result.stdout + result.stderr)

    def test_failed_account_lookup_does_not_echo_diagnostics(self) -> None:
        marker = "synthetic-private-text-not-for-logs"
        result = self.run_private_check("Public text.\n", id_status=1, diagnostics=marker)
        self.assertEqual(42, result.returncode)
        self.assertNotIn(marker, result.stdout + result.stderr)

    def test_invalid_structured_output_fails_closed_without_echoing_it(self) -> None:
        marker = "synthetic-private-text-not-for-logs"
        result = self.run_private_check("Public text.\n", review_status=0, search_output=marker)
        self.assertEqual(42, result.returncode)
        self.assertIn("location parsing failed", result.stderr)
        self.assertNotIn(marker, result.stdout + result.stderr)

    def test_match_without_text_location_fails_closed(self) -> None:
        result = self.run_private_check(
            "Public text.\n", review_status=0,
            search_output='{"type":"match","data":{"path":{"bytes":"YWJj"},"line_number":1}}\n',
        )
        self.assertEqual(42, result.returncode)
        self.assertIn("location parsing failed", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_structured_matches_are_counted_and_limited(self) -> None:
        result = self.run_private_check("token public-example\n" * 21)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("21 policy/source hit(s)", result.stdout)
        self.assertEqual(20, result.stdout.count('"./README.md":'))
        self.assertIn("output truncated", result.stdout)

    def test_search_destination_open_failures_are_not_no_match(self) -> None:
        for destination, first_search in (
            ("private-hits.txt", True), ("private-search-error.txt", True),
            ("sensitive-review.jsonl", False), ("sensitive-search-error.txt", False),
        ):
            with self.subTest(destination=destination):
                result = self.run_private_check("Public text.\n", blocked_output=destination)
                self.assertEqual(42, result.returncode)
                self.assertIn("scan failed", result.stderr)
                self.assertNotIn("review produced no hits", result.stdout)
                if first_search:
                    self.assertNotIn("[OK]", result.stdout)
                self.assertNotIn("privacy-check-", result.stdout + result.stderr)
                self.assertNotIn("Is a directory", result.stdout + result.stderr)

    def test_account_and_parser_destination_failures_hide_diagnostics(self) -> None:
        for destination in (
            "private-account-error.txt", "sensitive-locations.txt", "sensitive-parser-error.txt",
        ):
            with self.subTest(destination=destination):
                result = self.run_private_check("token public-example\n", blocked_output=destination)
                self.assertEqual(42, result.returncode)
                self.assertNotIn("privacy-check-", result.stdout + result.stderr)
                self.assertNotIn("Is a directory", result.stdout + result.stderr)
                self.assertNotIn("review produced no hits", result.stdout)

    def test_unicode_separators_in_paths_and_match_content_are_supported(self) -> None:
        for separator in ("\u0085", "\u2028", "\u2029"):
            for in_filename in (False, True):
                with self.subTest(separator=ord(separator), in_filename=in_filename):
                    filename = "note" + separator + ".txt" if in_filename else "README.md"
                    content = "token public" + ("" if in_filename else separator) + "example\n"
                    result = self.run_private_check(content, filename=filename)
                    self.assertEqual(0, result.returncode, result.stderr)
                    self.assertIn(json.dumps("./" + filename, ensure_ascii=True) + ":1", result.stdout)
                    self.assertNotIn("public", result.stdout + result.stderr)

    def test_boolean_line_number_is_rejected(self) -> None:
        result = self.run_private_check(
            "Public text.\n", review_status=0,
            search_output='{"type":"match","data":{"path":{"text":"file.txt"},"line_number":true}}\n',
        )
        self.assertEqual(42, result.returncode)
        self.assertIn("location parsing failed", result.stderr)
        self.assertNotIn(":True", result.stdout)


if __name__ == "__main__":
    unittest.main()
