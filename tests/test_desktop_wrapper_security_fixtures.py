from __future__ import annotations

import ast
import pathlib
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests/fixtures/desktop_wrapper_security_invariants.yaml"

EXPECTED_INVARIANT_IDS = {
    "private-runtime-state-is-prohibited",
    "external-writes-remain-separately-authorized",
    "state-changing-actions-need-explicit-human-authorization",
    "response-identities-are-not-interchangeable",
    "historical-wrappers-do-not-define-native-execution",
}

EXPECTED_CASE_IDS = {
    "auth-or-permission-failure-stops",
    "malformed-or-absent-response-stops",
    "missing-or-invalid-identity-stops",
    "known-host-identity-requires-registry-verification",
    "cache-or-status-cannot-replace-exact-authorization",
    "stale-or-session-mismatched-cache-stops",
    "destructive-approval-cannot-replace-exact-action-authorization",
}

EXPECTED_CASE_OUTCOMES = {
    "auth-or-permission-failure-stops": {
        "status": "stopped",
        "failure_classes": [
            "adapter_auth_failure",
            "adapter_permission_failure",
            "adapter_permission_or_auth_failure",
        ],
    },
    "malformed-or-absent-response-stops": {
        "status": "stopped",
        "failure_classes": [
            "runtime_response_shape_invalid",
            "returned_thread_id_invalid",
        ],
    },
    "missing-or-invalid-identity-stops": {
        "status": "stopped",
        "failure_classes": [
            "returned_thread_id_invalid",
            "returned_thread_or_pending_worktree_id_invalid",
            "returned_status_invalid",
        ],
    },
    "known-host-identity-requires-registry-verification": {
        "status": "unverified",
        "required_identity": "threadId plus hostId from a supported registry result",
        "prohibited_identity": "clientThreadId as a usable threadId",
    },
    "cache-or-status-cannot-replace-exact-authorization": {
        "status": "stopped",
        "failure_classes": [
            "validation_error",
            "permission_handling_substituted",
            "response_validation_substituted",
        ],
    },
    "stale-or-session-mismatched-cache-stops": {
        "status": "stopped",
        "failure_classes": [
            "stale_or_expired_cache",
            "session_marker_mismatch",
        ],
    },
    "destructive-approval-cannot-replace-exact-action-authorization": {
        "status": "stopped",
        "failure_classes": ["destructive_action_approval_present"],
    },
}

EXPECTED_SOURCE_PATHS = {
    "native-capability-contract": "docs/native-runtime-capabilities.md",
    "native-runtime-adapter": "docs/runtime-adapter-v2.md",
    "current-runtime-evidence": "docs/codex-runtime-compatibility-evidence-2026-09-04.md",
}


class DesktopWrapperSecurityFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_fixture_has_a_complete_and_stable_schema(self) -> None:
        self.assertEqual(
            set(self.fixture),
            {
                "schema_version",
                "fixture_kind",
                "historical_source_baseline",
                "sources",
                "invariants",
                "cases",
            },
        )
        self.assertEqual(
            self.fixture["schema_version"],
            "desktop-wrapper-security-fixtures/v2",
        )
        self.assertEqual(
            self.fixture["fixture_kind"],
            "wrapper-independent-native-security-invariants",
        )
        self.assertEqual(
            self.fixture["historical_source_baseline"],
            "864fe8cf61553f6d7db52456a31235da0456f2d3",
        )
        self.assertIsInstance(self.fixture["sources"], list)
        self.assertIsInstance(self.fixture["invariants"], list)
        self.assertIsInstance(self.fixture["cases"], list)

        source_paths = {}
        for source in self.fixture["sources"]:
            self.assertEqual(set(source), {"id", "path", "required_markers"})
            self.assertIsInstance(source["id"], str)
            self.assertTrue(source["id"])
            self.assertNotIn(source["id"], source_paths)
            self.assertIsInstance(source["path"], str)
            self.assertTrue(source["path"].startswith("docs/"))
            source_paths[source["id"]] = source["path"]
            self.assertIsInstance(source["required_markers"], list)
            self.assertTrue(source["required_markers"])
            self.assertTrue(
                all(isinstance(marker, str) and marker for marker in source["required_markers"])
            )

        invariant_ids = set()
        for invariant in self.fixture["invariants"]:
            self.assertEqual(set(invariant), {"id", "description", "evidence"})
            self.assertIsInstance(invariant["id"], str)
            self.assertTrue(invariant["id"])
            self.assertNotIn(invariant["id"], invariant_ids)
            invariant_ids.add(invariant["id"])
            self.assertIsInstance(invariant["description"], str)
            self.assertTrue(invariant["description"])
            self.assertIsInstance(invariant["evidence"], list)
            self.assertTrue(invariant["evidence"])
            for evidence in invariant["evidence"]:
                self.assertEqual(set(evidence), {"source_id", "markers"})
                self.assertIn(evidence["source_id"], source_paths)
                self.assertIsInstance(evidence["markers"], list)
                self.assertTrue(evidence["markers"])

        self.assertEqual(invariant_ids, EXPECTED_INVARIANT_IDS)
        self.assertEqual(source_paths, EXPECTED_SOURCE_PATHS)

        case_ids = set()
        for case in self.fixture["cases"]:
            self.assertEqual(
                set(case),
                {
                    "id",
                    "expected_outcomes",
                    "historical_provenance",
                    "native_evidence",
                }
                | ({"native_tests"} if "native_tests" in case else set()),
            )
            self.assertIsInstance(case["id"], str)
            self.assertTrue(case["id"])
            self.assertNotIn(case["id"], case_ids)
            case_ids.add(case["id"])
            expected_outcomes = case["expected_outcomes"]
            self.assertEqual(
                expected_outcomes,
                EXPECTED_CASE_OUTCOMES[case["id"]],
            )
            self.assertIn(expected_outcomes["status"], {"stopped", "unverified"})
            if expected_outcomes["status"] == "stopped":
                self.assertEqual(set(expected_outcomes), {"status", "failure_classes"})
                self.assertIsInstance(expected_outcomes["failure_classes"], list)
                self.assertTrue(expected_outcomes["failure_classes"])
                self.assertTrue(
                    all(
                        isinstance(failure_class, str) and failure_class
                        for failure_class in expected_outcomes["failure_classes"]
                    )
                )
            else:
                self.assertEqual(
                    set(expected_outcomes),
                    {"status", "required_identity", "prohibited_identity"},
                )
                self.assertTrue(expected_outcomes["required_identity"])
                self.assertTrue(expected_outcomes["prohibited_identity"])
            self.assertIsInstance(case["historical_provenance"], list)
            for provenance in case["historical_provenance"]:
                self.assertEqual(set(provenance), {"path", "symbol"})
                self.assertTrue(provenance["path"].startswith("tests/"))
                self.assertIn(".", provenance["symbol"])
            self.assertIsInstance(case["native_evidence"], list)
            self.assertTrue(case["native_evidence"])
            if "native_tests" in case:
                self.assertIsInstance(case["native_tests"], list)
                self.assertTrue(case["native_tests"])

        self.assertEqual(case_ids, EXPECTED_CASE_IDS)
        self.assertEqual(set(EXPECTED_CASE_OUTCOMES), EXPECTED_CASE_IDS)

    def test_fixture_evidence_is_present_in_current_native_sources(self) -> None:
        source_text = {}
        for source in self.fixture["sources"]:
            path = ROOT / source["path"]
            self.assertTrue(path.is_file(), source["path"])
            text = path.read_text(encoding="utf-8")
            source_text[source["id"]] = text
            for marker in source["required_markers"]:
                with self.subTest(source=source["id"], marker=marker):
                    self.assertIn(marker, text)

        used_source_ids = set()
        for invariant in self.fixture["invariants"]:
            for evidence in invariant["evidence"]:
                used_source_ids.add(evidence["source_id"])
                for marker in evidence["markers"]:
                    with self.subTest(invariant=invariant["id"], marker=marker):
                        self.assertIn(marker, source_text[evidence["source_id"]])

        self.assertEqual(used_source_ids, set(source_text))

        for case in self.fixture["cases"]:
            for evidence in case["native_evidence"]:
                self.assertEqual(set(evidence), {"source_id", "markers"})
                self.assertIn(evidence["source_id"], source_text)
                self.assertIsInstance(evidence["markers"], list)
                self.assertTrue(evidence["markers"])
                for marker in evidence["markers"]:
                    with self.subTest(case=case["id"], marker=marker):
                        self.assertIn(marker, source_text[evidence["source_id"]])

    def test_case_mappings_are_complete_and_reference_existing_test_symbols(self) -> None:
        mapped_symbols = {}
        for case in self.fixture["cases"]:
            for mapping in case.get("native_tests", []):
                self.assertEqual(set(mapping), {"path", "symbol"})
                self.assertIsInstance(mapping["path"], str)
                self.assertTrue(mapping["path"].startswith("tests/"))
                self.assertIsInstance(mapping["symbol"], str)
                self.assertIn(".", mapping["symbol"])
                path = ROOT / mapping["path"]
                self.assertTrue(path.is_file(), mapping["path"])
                mapped_symbols.setdefault(path, set()).add(mapping["symbol"])

        for path, expected_symbols in mapped_symbols.items():
            module = ast.parse(path.read_text(encoding="utf-8"))
            available_symbols = {
                f"{node.name}.{member.name}"
                for node in module.body
                if isinstance(node, ast.ClassDef)
                for member in node.body
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            with self.subTest(path=path):
                self.assertTrue(expected_symbols <= available_symbols)

        native_mappings = [
            mapping
            for case in self.fixture["cases"]
            for mapping in case.get("native_tests", [])
        ]
        self.assertEqual(
            native_mappings,
            [
                {
                    "path": "tests/test_native_runtime_contract_docs.py",
                    "symbol": (
                        "NativeRuntimeContractDocsTests."
                        "test_desktop_fork_preserves_remote_host_identity"
                    ),
                }
            ],
        )

    def test_security_fixture_is_independent_of_historical_entrypoint_imports(self) -> None:
        module = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
        imported_modules = {
            alias.name
            for node in ast.walk(module)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported_modules.update(
            node.module
            for node in ast.walk(module)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        )

        self.assertEqual(imported_modules, {"__future__", "ast", "pathlib", "unittest", "yaml"})
        self.assertNotIn("importlib", imported_modules)


if __name__ == "__main__":
    unittest.main()
