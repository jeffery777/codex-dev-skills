"""Synthetic qualification-store trust and selection tests (no model measurements)."""
import copy
import datetime as dt
import hashlib
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/loop-engineering/scripts"))
import agent_qualification as aq


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, CODEX_HOME=str(self.root)).start()
        self.name = "loop_v2a_astra_advanced_worker"
        self.role = "loop_v2a_advanced_worker"
        self.entries = {self.name: {"candidate_for": self.role, "capability_class": "balanced-worker", "capability_tier": "advanced", "_profile_digest": "a" * 64}}
        self.record = {"profile": self.name, "profile_sha256": "a" * 64, "capability_class": "balanced-worker", "capability_tier": "advanced", "task_scopes": ["fixture-repair"], "runtimes": ["cli", "desktop"], "quality_evidence": "evidence.md", "quality_evidence_sha256": hashlib.sha256(b"synthetic").hexdigest(), "expires_on": "2099-01-01", "enabled": True}
        self.store = {"schema_version": 1, "enabled": True, "qualifications": [self.record]}
        (self.root / "evidence.md").write_bytes(b"synthetic")
        self.save()

    def save(self):
        (self.root / "agent-qualifications.json").write_text(json.dumps(self.store))

    def run_load(self, facts=None, scope="fixture-repair"):
        return aq.discover(facts if facts is not None else {"model_surface": {"runtime": "cli"}}, role=self.role, entries=self.entries, scope=scope)

    def test_runtime_positive_scope_and_current_facts(self):
        for runtime in ("cli", "desktop"):
            facts = {"model_surface": {"runtime": runtime}}
            output, audit = self.run_load(facts)
            self.assertIn(self.name, output["enabled_candidates"])
            self.assertEqual("qualified", audit["status"])
            self.assertEqual(
                "qualification-evidence-sha256:" + self.record["quality_evidence_sha256"],
                output["enabled_candidates"][self.name]["quality_evidence"],
            )
            self.assertNotIn("evidence.md", json.dumps(output))
            self.assertNotIn("enabled_candidates", facts)
        for facts, scope in [({}, "fixture-repair"), ({"model_surface": {"runtime": "api"}}, "fixture-repair"), ({}, None), ({}, "different")]:
            self.assertFalse(self.run_load(facts, scope)[0]["enabled_candidates"])
        self.assertIn("scope-mismatch", self.run_load(scope="different")[1]["reasons"])

    def test_unsupported_platform_keeps_baseline_or_explicit_override(self):
        with patch.object(aq.os, "name", "nt"):
            output, audit = self.run_load()
            self.assertEqual({}, output["enabled_candidates"])
            self.assertIn("unsupported-platform", audit["reasons"])
            facts = {"enabled_candidates": {}}
            self.assertIs(facts, self.run_load(facts)[0])

    def test_explicit_empty_override_does_not_read(self):
        with patch.object(aq, "_directory", side_effect=AssertionError("must not read")):
            facts = {"enabled_candidates": {}}
            self.assertIs(facts, self.run_load(facts)[0])

    def test_revocation_integrity_and_expiry(self):
        original = copy.deepcopy(self.record)
        for field, value, reason in [("enabled", False, "record-disabled"), ("profile_sha256", "b" * 64, "profile-mismatch"), ("quality_evidence_sha256", "b" * 64, "evidence-mismatch"), ("expires_on", "2000-01-01", "expired"), ("capability_tier", "everyday", "profile-mismatch")]:
            self.store["qualifications"] = [{**original, field: value}]
            self.save()
            out, audit = self.run_load()
            self.assertEqual({}, out["enabled_candidates"])
            self.assertIn(reason, audit["reasons"])
        self.store["enabled"] = False
        self.save()
        self.assertIn("store-disabled", self.run_load()[1]["reasons"])

    def test_explicit_no_expiry_retains_all_other_checks(self):
        self.record["expires_on"] = None
        self.save()
        output, audit = aq.discover({"model_surface": {"runtime": "cli"}}, role=self.role, entries=self.entries, scope="fixture-repair", today=dt.date(9999, 12, 31))
        self.assertIn(self.name, output["enabled_candidates"])
        self.assertEqual("qualified", audit["status"])
        self.assertFalse(self.run_load(scope="unqualified")[0]["enabled_candidates"])
        self.assertFalse(self.run_load({"model_surface": {"runtime": "api"}})[0]["enabled_candidates"])
        for field, value, reason in [("enabled", False, "record-disabled"), ("profile_sha256", "b" * 64, "profile-mismatch"), ("quality_evidence_sha256", "b" * 64, "evidence-mismatch")]:
            with self.subTest(field=field):
                original = self.record[field]
                self.record[field] = value
                self.save()
                out, audit = self.run_load()
                self.assertFalse(out["enabled_candidates"])
                self.assertIn(reason, audit["reasons"])
                self.record[field] = original

    def test_expiry_requires_explicit_null_or_valid_date(self):
        for expiry in (False, True, 0, [], {}, "", "null", "2026-02-30"):
            with self.subTest(expiry=expiry):
                self.record["expires_on"] = expiry
                self.save()
                self.assertFalse(self.run_load()[0]["enabled_candidates"])
        del self.record["expires_on"]
        self.save()
        self.assertIn("invalid-record", self.run_load()[1]["reasons"])

    def test_dated_expiry_remains_inclusive(self):
        self.record["expires_on"] = "2026-09-05"
        self.save()
        for day, accepted in [(dt.date(2026, 9, 5), True), (dt.date(2026, 9, 6), False)]:
            output, _ = aq.discover({"model_surface": {"runtime": "cli"}}, role=self.role, entries=self.entries, scope="fixture-repair", today=day)
            self.assertEqual(accepted, bool(output["enabled_candidates"]))

    def test_strict_json_and_bounded_reads(self):
        path = self.root / "agent-qualifications.json"
        for raw in ['{"schema_version":1,"schema_version":1}', '{"value":NaN}', '[' * 2000, 'x' * (aq.MAX_STORE_BYTES + 1)]:
            path.write_text(raw)
            self.assertFalse(self.run_load()[0]["enabled_candidates"])
        self.store["qualifications"].append(copy.deepcopy(self.record))
        self.save()
        self.assertIn("duplicate-profile", self.run_load()[1]["reasons"])

    def test_unsafe_files_paths_and_missing(self):
        evidence = self.root / "evidence.md"
        evidence.chmod(0o666)
        self.assertIn("writable-path", self.run_load()[1]["reasons"])
        evidence.chmod(0o600)
        for unsafe in ("../evidence.md", "/evidence.md", "./evidence.md"):
            self.record["quality_evidence"] = unsafe
            self.save()
            self.assertFalse(self.run_load()[0]["enabled_candidates"])
        self.record["quality_evidence"] = "evidence.md"
        self.save()
        evidence.unlink()
        evidence.symlink_to(self.root / "agent-qualifications.json")
        self.assertFalse(self.run_load()[0]["enabled_candidates"])
        evidence.unlink()
        os.mkfifo(evidence)
        self.assertFalse(self.run_load()[0]["enabled_candidates"])
        evidence.unlink()
        self.assertIn("store-or-evidence-missing", self.run_load()[1]["reasons"])

    def test_store_and_component_special_files_and_schema(self):
        path = self.root / "agent-qualifications.json"
        for value in ({**self.store, "extra": True}, {**self.store, "schema_version": True}, {**self.store, "enabled": 1}):
            path.write_text(json.dumps(value))
            self.assertFalse(self.run_load()[0]["enabled_candidates"])
        self.save()
        path.chmod(0o666)
        self.assertIn("writable-path", self.run_load()[1]["reasons"])
        path.unlink()
        path.symlink_to(self.root / "evidence.md")
        self.assertFalse(self.run_load()[0]["enabled_candidates"])
        path.unlink()
        os.mkfifo(path)
        self.assertFalse(self.run_load()[0]["enabled_candidates"])
        path.unlink()
        self.save()
        self.root.chmod(0o777)
        try:
            self.assertIn("writable-path", self.run_load()[1]["reasons"])
        finally:
            self.root.chmod(0o700)
        (self.root / "evidence.md").write_bytes(b"x" * (aq.MAX_EVIDENCE_BYTES + 1))
        self.assertIn("oversize-file", self.run_load()[1]["reasons"])
        self.record["expires_on"] = "not-a-date"
        self.save()
        self.assertIn("invalid-record", self.run_load()[1]["reasons"])

    def test_repo_directory_symlink_and_unowned_store(self):
        (self.root / ".git").write_text("gitdir: synthetic")
        self.assertIn("repository-controlled-store", self.run_load()[1]["reasons"])
        (self.root / ".git").unlink()
        link = self.root / "linked"
        link.symlink_to(self.root, target_is_directory=True)
        with patch.dict(os.environ, CODEX_HOME=str(link)):
            self.assertFalse(self.run_load()[0]["enabled_candidates"])
        with patch.object(aq.os, "getuid", return_value=999999):
            self.assertFalse(self.run_load()[0]["enabled_candidates"])


if __name__ == "__main__":
    unittest.main()
