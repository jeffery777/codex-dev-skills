import copy
import datetime as dt
import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "desktop_runtime_session_compatibility_cache.py"
SPEC = importlib.util.spec_from_file_location("desktop_runtime_session_compatibility_cache", SCRIPT)
cache = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cache)


def normalized_contract(**overrides):
    today = dt.date.today().isoformat()
    contract = {
        "action": "read-thread",
        "tool_or_api": "read_thread",
        "classification": "read-only",
        "required_request_fields": ["thread_id"],
        "minimum_response_fields": ["status", "thread_id"],
        "capability_source": "runtime-reported schema",
        "contract_version": "version unavailable",
        "last_verified": today,
    }
    contract.update(overrides)
    return contract


def valid_cache_parts(cache_file, **overrides):
    today = dt.date.today().isoformat()
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    contract = normalized_contract()
    contract_hash = cache._contract_hash(contract)
    session_identity = {
        "marker_type": "current-session",
        "marker": "current-session scoped",
    }
    compatibility_status = {
        "repo_commit": "ba6b974fbfa94e08d55e94a7a6a948b47dec200d",
        "helper_version": "0.1.0",
        "target_action": "read-thread",
        "tool_or_api": "read_thread",
        "runtime_reported_version": "version unavailable",
        "capability_source": "runtime-reported schema",
        "schema_hash": contract_hash,
        "comparison_result": "compatible",
        "last_verified": today,
        "session_identity": copy.deepcopy(session_identity),
    }
    envelope = {
        "repo_commit": "ba6b974fbfa94e08d55e94a7a6a948b47dec200d",
        "cache_helper_version": "0.1.0",
        "status_helper_version": "0.1.0",
        "target_action": "read-thread",
        "tool_or_api": "read_thread",
        "runtime_reported_version": "version unavailable",
        "capability_source": "runtime-reported schema",
        "schema_hash": contract_hash,
        "comparison_result": "compatible",
        "last_verified": today,
        "session_identity": copy.deepcopy(session_identity),
        "cache_scope": "same-session",
        "cache_lifecycle_marker": "same-session-only",
        "same_session_only": True,
        "created_at": now,
        "compatibility_status": compatibility_status,
    }
    request = {
        "requested_action": "write-session-compatibility-cache",
        "cache_file": str(cache_file),
        "expected": {
            "repo_commit": "ba6b974fbfa94e08d55e94a7a6a948b47dec200d",
            "cache_helper_version": "0.1.0",
            "status_helper_version": "0.1.0",
            "target_action": "read-thread",
            "tool_or_api": "read_thread",
            "schema_hash": contract_hash,
        },
        "current_session_identity": copy.deepcopy(session_identity),
        "cache_envelope": envelope,
    }
    for path, value in overrides.items():
        current = request
        parts = path.split("__")
        for part in parts[:-1]:
            current = current[int(part)] if isinstance(current, list) else current[part]
        if isinstance(current, list):
            current[int(parts[-1])] = value
        else:
            current[parts[-1]] = value
    return request


def read_request_from(write_request, **overrides):
    request = {
        "requested_action": "read-session-compatibility-cache",
        "cache_file": write_request["cache_file"],
        "expected": copy.deepcopy(write_request["expected"]),
        "current_session_identity": copy.deepcopy(write_request["current_session_identity"]),
    }
    for path, value in overrides.items():
        current = request
        parts = path.split("__")
        for part in parts[:-1]:
            current = current[int(part)] if isinstance(current, list) else current[part]
        if isinstance(current, list):
            current[int(parts[-1])] = value
        else:
            current[parts[-1]] = value
    return request


class SessionCompatibilityCacheTests(unittest.TestCase):
    def test_validated_compatible_session_status_writes_and_reads_ready_same_session_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_file = pathlib.Path(tmp) / "compatibility-evidence.json"
            write_request = valid_cache_parts(cache_file)

            write_response = cache.write_session_compatibility_cache(write_request)
            read_response = cache.read_session_compatibility_cache(read_request_from(write_request))

            self.assertEqual(write_response["status"], "ready")
            self.assertTrue(write_response["cache_write_performed"])
            self.assertEqual(read_response["status"], "ready")
            self.assertTrue(read_response["cache_read_performed"])
            self.assertFalse(read_response["runtime_call_performed"])
            self.assertFalse(read_response["private_runtime_state_read"])
            self.assertFalse(read_response["later_runtime_path_blocked"])
            self.assertIn("same-session cache evidence", read_response["readiness_meaning"])
            self.assertIn("does not authorize runtime calls", read_response["readiness_meaning"])

    def test_fallback_cached_status_blocks_later_runtime_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_file = pathlib.Path(tmp) / "fallback-evidence.json"
            request = valid_cache_parts(
                cache_file,
                cache_envelope__comparison_result="fallback",
                cache_envelope__compatibility_status__comparison_result="fallback",
            )

            write_response = cache.write_session_compatibility_cache(request)
            read_response = cache.read_session_compatibility_cache(read_request_from(request))

            self.assertEqual(write_response["status"], "fallback")
            self.assertTrue(write_response["later_runtime_path_blocked"])
            self.assertEqual(read_response["status"], "fallback")
            self.assertTrue(read_response["later_runtime_path_blocked"])

    def test_stopped_cached_status_blocks_later_runtime_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_file = pathlib.Path(tmp) / "stopped-evidence.json"
            request = valid_cache_parts(
                cache_file,
                cache_envelope__comparison_result="stopped",
                cache_envelope__compatibility_status__comparison_result="stopped",
            )

            write_response = cache.write_session_compatibility_cache(request)
            read_response = cache.read_session_compatibility_cache(read_request_from(request))

            self.assertEqual(write_response["status"], "stopped")
            self.assertEqual(write_response["failure_class"], "session_compatibility_stopped")
            self.assertEqual(read_response["status"], "stopped")
            self.assertTrue(read_response["later_runtime_path_blocked"])

    def test_cache_helper_version_mismatch_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = valid_cache_parts(
                pathlib.Path(tmp) / "version.json",
                cache_envelope__cache_helper_version="9.9.9",
            )

            response = cache.write_session_compatibility_cache(request)

            self.assertEqual(response["status"], "stopped")
            self.assertEqual(response["failure_class"], "wrapper_or_helper_version_mismatch")

    def test_status_helper_version_mismatch_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = valid_cache_parts(
                pathlib.Path(tmp) / "status-version.json",
                cache_envelope__status_helper_version="9.9.9",
            )

            response = cache.write_session_compatibility_cache(request)

            self.assertEqual(response["status"], "stopped")
            self.assertEqual(response["failure_class"], "wrapper_or_helper_version_mismatch")

    def test_wrapper_version_mismatch_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = valid_cache_parts(
                pathlib.Path(tmp) / "wrapper.json",
                cache_envelope__repo_commit="different",
            )

            response = cache.write_session_compatibility_cache(request)

            self.assertEqual(response["status"], "stopped")
            self.assertEqual(response["failure_class"], "wrapper_or_helper_version_mismatch")

    def test_schema_hash_mismatch_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = valid_cache_parts(
                pathlib.Path(tmp) / "schema.json",
                cache_envelope__schema_hash="sha256:wrong",
            )

            response = cache.write_session_compatibility_cache(request)

            self.assertEqual(response["status"], "stopped")
            self.assertEqual(response["failure_class"], "contract_evidence_mismatch")

    def test_normalized_contract_evidence_mismatch_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = valid_cache_parts(pathlib.Path(tmp) / "normalized.json")
            request["expected"].pop("schema_hash")
            request["cache_envelope"].pop("schema_hash")
            request["cache_envelope"]["compatibility_status"].pop("schema_hash")
            request["expected"]["normalized_contract_evidence"] = normalized_contract()
            request["cache_envelope"]["normalized_contract_evidence"] = normalized_contract(
                minimum_response_fields=["status", "thread_id", "title"]
            )
            request["cache_envelope"]["compatibility_status"]["normalized_contract_evidence"] = (
                normalized_contract()
            )

            response = cache.write_session_compatibility_cache(request)

            self.assertEqual(response["status"], "stopped")
            self.assertEqual(response["failure_class"], "contract_evidence_mismatch")

    def test_missing_session_marker_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = valid_cache_parts(
                pathlib.Path(tmp) / "missing-marker.json",
                cache_envelope__session_identity__marker="",
                cache_envelope__compatibility_status__session_identity__marker="",
            )

            response = cache.write_session_compatibility_cache(request)

            self.assertEqual(response["status"], "stopped")
            self.assertEqual(response["failure_class"], "missing_session_marker")

    def test_session_marker_mismatch_stops_on_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = valid_cache_parts(pathlib.Path(tmp) / "marker-mismatch.json")
            cache.write_session_compatibility_cache(request)

            read_response = cache.read_session_compatibility_cache(
                read_request_from(
                    request,
                    current_session_identity__marker="different-session",
                )
            )

            self.assertEqual(read_response["status"], "stopped")
            self.assertEqual(read_response["failure_class"], "session_marker_mismatch")

    def test_explicit_current_session_scoped_marker_requires_same_session_cache_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = valid_cache_parts(
                pathlib.Path(tmp) / "scope.json",
                cache_envelope__same_session_only=False,
            )

            response = cache.write_session_compatibility_cache(request)

            self.assertEqual(response["status"], "stopped")
            self.assertEqual(response["failure_class"], "cache_scope_mismatch")

    def test_explicit_current_session_scoped_marker_is_accepted_for_same_session_envelope(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = valid_cache_parts(pathlib.Path(tmp) / "same-session.json")

            response = cache.write_session_compatibility_cache(request)

            self.assertEqual(response["status"], "ready")
            self.assertEqual(response["cache_evidence"]["cache_scope"], "same-session")
            self.assertTrue(response["cache_evidence"]["same_session_only"])

    def test_expired_cache_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            expired = (
                dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=1)
            ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            request = valid_cache_parts(
                pathlib.Path(tmp) / "expired.json",
                cache_envelope__expires_at=expired,
            )

            response = cache.write_session_compatibility_cache(request)

            self.assertEqual(response["status"], "stopped")
            self.assertEqual(response["failure_class"], "stale_or_expired_cache")

    def test_cache_cannot_replace_authorization_target_permission_or_response_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = valid_cache_parts(pathlib.Path(tmp) / "auth.json")
            request["cache_envelope"]["compatibility_status"]["thread_action_authorized"] = True
            request["cache_envelope"]["compatibility_status"]["external_write_authorized"] = True
            request["cache_envelope"]["compatibility_status"]["target_validated"] = True
            request["cache_envelope"]["compatibility_status"]["permission_validated"] = True
            request["cache_envelope"]["compatibility_status"]["response_validated"] = True

            response = cache.write_session_compatibility_cache(request)

            self.assertEqual(response["status"], "stopped")
            self.assertEqual(response["failure_class"], "authorization_out_of_scope")
            self.assertIn("thread_action_authorized", response["result"]["stop_reason"])
            self.assertIn("external_write_authorized", response["result"]["stop_reason"])
            self.assertIn("target_validated", response["result"]["stop_reason"])
            self.assertIn("permission_validated", response["result"]["stop_reason"])
            self.assertIn("response_validated", response["result"]["stop_reason"])

    def test_rejects_desktop_private_runtime_looking_cache_paths(self):
        request = valid_cache_parts(
            pathlib.Path("/tmp/Codex Desktop/sessions/compatibility.json")
        )

        response = cache.write_session_compatibility_cache(request)

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_cache_path")
        self.assertFalse(response["cache_write_performed"])

    def test_rejects_private_runtime_source_hints(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = valid_cache_parts(
                pathlib.Path(tmp) / "source-hint.json",
                cache_envelope__notes="Derived from Desktop private runtime state.",
            )

            response = cache.write_session_compatibility_cache(request)

            self.assertEqual(response["status"], "stopped")
            self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_no_desktop_private_runtime_state_is_read(self):
        request = valid_cache_parts(pathlib.Path("/tmp/Codex Desktop/logs/state.json"))

        response = cache.read_session_compatibility_cache(read_request_from(request))

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_cache_path")
        self.assertFalse(response["cache_read_performed"])
        self.assertFalse(response["private_runtime_state_read"])

    def test_no_desktop_thread_tool_symbols_or_daemon_claims_are_introduced(self):
        with tempfile.TemporaryDirectory() as tmp:
            response = cache.write_session_compatibility_cache(
                valid_cache_parts(pathlib.Path(tmp) / "symbols.json")
            )

            self.assertFalse(hasattr(cache, "create_thread"))
            self.assertFalse(hasattr(cache, "fork_thread"))
            self.assertFalse(hasattr(cache, "send_message_to_thread"))
            self.assertFalse(hasattr(cache, "read_thread"))
            self.assertFalse(response["runtime_call_performed"])
            self.assertFalse(response["private_runtime_state_read"])
            self.assertIn(
                "Runtime-call authorization, external-write authorization, target validation, permission handling, and response validation remain separate.",
                response["result"]["residual_risk"],
            )

    def test_request_is_not_mutated(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = valid_cache_parts(pathlib.Path(tmp) / "immutable.json")
            original = copy.deepcopy(request)

            cache.write_session_compatibility_cache(request)

            self.assertEqual(request, original)

    def test_cli_process_dispatches_read_and_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = valid_cache_parts(pathlib.Path(tmp) / "dispatch.json")
            write_response = cache.process_session_compatibility_cache_request(request)
            read_response = cache.process_session_compatibility_cache_request(read_request_from(request))

            self.assertEqual(write_response["status"], "ready")
            self.assertEqual(read_response["status"], "ready")

    def test_written_file_is_explicit_cache_envelope_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_file = pathlib.Path(tmp) / "envelope.json"
            request = valid_cache_parts(cache_file)

            cache.write_session_compatibility_cache(request)

            stored = json.loads(cache_file.read_text(encoding="utf-8"))
            self.assertEqual(stored["cache_scope"], "same-session")
            self.assertEqual(stored["compatibility_status"]["comparison_result"], "compatible")


if __name__ == "__main__":
    unittest.main()
