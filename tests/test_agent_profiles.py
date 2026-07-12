from __future__ import annotations

import importlib.util
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-agent-profiles.py"
PROFILE_DIR = ROOT / "agent-profiles"
CANONICAL_SCRIPT = ROOT / "skills" / "loop-engineering" / "scripts" / "profile_preflight.py"
REGISTRY = ROOT / "skills" / "loop-engineering" / "references" / "agent-profile-registry.json"

SPEC = importlib.util.spec_from_file_location("validate_agent_profiles", CANONICAL_SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class AgentProfileValidationTests(unittest.TestCase):
    def copy_profiles(self, root: pathlib.Path) -> pathlib.Path:
        destination = root / "agent-profiles"
        shutil.copytree(PROFILE_DIR, destination)
        return destination

    def test_repo_profiles_and_registry_are_valid_and_exact(self) -> None:
        registry, entries = VALIDATOR.validate(PROFILE_DIR, REGISTRY)

        self.assertEqual(2, registry["schema_version"])
        self.assertEqual(
            {
                "loop_v2a_fast_explorer",
                "loop_v2a_mechanical_reader",
                "loop_v2a_balanced_worker",
                "loop_v2a_advanced_worker",
                "loop_v2a_deep_reviewer",
                "loop_v2a_exceptional_researcher",
                "loop_v2a_security_reviewer",
            },
            set(entries),
        )
        self.assertEqual(
            {path.name for path in PROFILE_DIR.glob("*.toml")},
            {entry["file"] for entry in entries.values()},
        )
        for name, entry in entries.items():
            with self.subTest(name=name):
                profile = VALIDATOR.load_profile(PROFILE_DIR / entry["file"])
                self.assertTrue(name.startswith("loop_v2a_"))
                self.assertEqual(entry["sandbox_expectation"], profile["sandbox_mode"])
                self.assertEqual(entry["runtime_mapping"]["model"], profile["model"])
                self.assertEqual("runtime-dependent", entry["runtime_mapping"]["availability"])
                self.assertTrue(entry["runtime_mapping"]["replaceable"])
                self.assertIn("last_verified", entry["runtime_mapping"])
                self.assertEqual(
                    VALIDATOR.TIER_RANK[entry["capability_tier"]],
                    entry["tier_rank"],
                )
                self.assertNotIn("mcp_servers", profile)
                self.assertNotIn("skills", profile)

    def test_cli_default_validation_is_dependency_free(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("valid", json.loads(result.stdout)["status"])

    def test_runtime_facts_reject_non_string_enum_shapes(self) -> None:
        malformed_facts = (
            {"custom_agent_surface": []},
            {"parent_sandbox_mode": {}},
            {"available_models": [[]]},
            {"reasoning_efforts": {"gpt-5.6-sol": [[]]}},
            {
                "parent_default": {
                    "available": True,
                    "capability_classes": ["balanced-worker"],
                    "capability_tiers": {"balanced-worker": [[]]},
                }
            },
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "facts.json"
            for facts in malformed_facts:
                with self.subTest(facts=facts):
                    path.write_text(json.dumps(facts), encoding="utf-8")
                    with self.assertRaises(VALIDATOR.ProfileValidationError):
                        VALIDATOR.runtime_facts(path)

    def test_unknown_profile_key_and_unsafe_sandbox_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile_dir = self.copy_profiles(pathlib.Path(temporary))
            profile = profile_dir / "loop_v2a_fast_explorer.toml"
            original = profile.read_text(encoding="utf-8")
            profile.write_text(original + '\nmcp_servers = {}\n', encoding="utf-8")
            with self.assertRaisesRegex(VALIDATOR.ProfileValidationError, "unsupported key"):
                VALIDATOR.validate(profile_dir, REGISTRY)

            profile.write_text(original.replace('sandbox_mode = "read-only"', 'sandbox_mode = "danger-full-access"'), encoding="utf-8")
            with self.assertRaisesRegex(VALIDATOR.ProfileValidationError, "unsafe sandbox"):
                VALIDATOR.validate(profile_dir, REGISTRY)

    def test_machine_local_paths_and_credentials_fail_closed(self) -> None:
        cases = (
            'developer_instructions = "Read /' + 'Users/example/private.txt"',
            'developer_instructions = "api_key = unsafe-example"',
            'developer_instructions = "Read the Codex Desktop session database"',
        )
        with tempfile.TemporaryDirectory() as temporary:
            profile_dir = self.copy_profiles(pathlib.Path(temporary))
            profile = profile_dir / "loop_v2a_fast_explorer.toml"
            original = profile.read_text(encoding="utf-8")
            start = original.index('developer_instructions = """')
            for replacement in cases:
                mutated = original[:start] + replacement + "\n"
                profile.write_text(mutated, encoding="utf-8")
                with self.subTest(replacement=replacement), self.assertRaisesRegex(
                    VALIDATOR.ProfileValidationError, "machine-local, credential, or private-runtime"
                ):
                    VALIDATOR.validate(profile_dir, REGISTRY)

    def test_registry_requires_exact_coverage_and_replaceable_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            profile_dir = self.copy_profiles(pathlib.Path(temporary))
            registry_path = pathlib.Path(temporary) / "registry.json"
            shutil.copy2(REGISTRY, registry_path)
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["profiles"][0]["runtime_mapping"]["replaceable"] = False
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            with self.assertRaisesRegex(VALIDATOR.ProfileValidationError, "must be replaceable"):
                VALIDATOR.validate(profile_dir, registry_path)

            registry["profiles"] = registry["profiles"][1:]
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            with self.assertRaisesRegex(VALIDATOR.ProfileValidationError, "coverage must exactly match"):
                VALIDATOR.validate(profile_dir, registry_path)

    def test_destination_identical_instance_is_expected_not_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = pathlib.Path(temporary) / "agents"
            shutil.copytree(PROFILE_DIR, destination)
            report = VALIDATOR.detect_collisions(PROFILE_DIR, [destination], destination)
            self.assertEqual([], report["conflicts"])
            self.assertEqual(7, len(report["expected_instances"]))

    def test_destination_modified_instance_and_cross_root_match_are_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            destination = root / "destination"
            other = root / "other"
            shutil.copytree(PROFILE_DIR, destination)
            shutil.copytree(PROFILE_DIR, other)
            target = destination / "loop_v2a_fast_explorer.toml"
            target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            report = VALIDATOR.detect_collisions(PROFILE_DIR, [destination, other], destination)
            reasons = {item["reason"] for item in report["conflicts"]}
            self.assertIn("destination-content-conflict", reasons)
            self.assertIn("cross-root-name-collision", reasons)

    def test_installed_skill_layout_can_validate_installed_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            installed_skill = root / "skills" / "loop-engineering"
            installed_profiles = root / "agents"
            shutil.copytree(ROOT / "skills" / "loop-engineering", installed_skill)
            shutil.copytree(PROFILE_DIR, installed_profiles)
            result = subprocess.run(
                [
                    sys.executable,
                    str(installed_skill / "scripts" / "profile_preflight.py"),
                    "--profile-dir",
                    str(installed_profiles),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("valid", json.loads(result.stdout)["status"])
            facts = root / "runtime-facts.json"
            facts.write_text(
                json.dumps({
                    "custom_agent_surface": "available",
                    "available_models": ["gpt-5.6-terra"],
                    "reasoning_efforts": {"gpt-5.6-terra": ["low"]},
                }),
                encoding="utf-8",
            )
            preflight = subprocess.run(
                [
                    sys.executable,
                    str(installed_skill / "scripts" / "profile_preflight.py"),
                    "preflight",
                    "--profile-dir",
                    str(installed_profiles),
                    "--role",
                    "loop_v2a_fast_explorer",
                    "--runtime-facts",
                    str(facts),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, preflight.returncode, preflight.stderr)
            rendered = json.loads(preflight.stdout)
            self.assertEqual("ready", rendered["decision"])
            self.assertEqual(
                hashlib.sha256((installed_profiles / "loop_v2a_fast_explorer.toml").read_bytes()).hexdigest(),
                rendered["route_profile_evidence"]["profile_digest"],
            )

    def test_installed_mixed_agent_directory_ignores_unrelated_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = pathlib.Path(temporary) / "agents"
            shutil.copytree(PROFILE_DIR, destination)
            (destination / "my_other_agent.toml").write_text(
                'name = "my_other_agent"\n'
                'description = "Unrelated valid custom agent."\n'
                'developer_instructions = "Stay in scope."\n',
                encoding="utf-8",
            )
            _, entries = VALIDATOR.validate(destination, REGISTRY)
            self.assertEqual(7, len(entries))
            changed = destination / "loop_v2a_balanced_worker.toml"
            changed.write_text(
                changed.read_text(encoding="utf-8").replace(
                    "Implement only the bounded file ownership",
                    "Edit every file regardless of bounded ownership",
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                VALIDATOR.ProfileValidationError, "differs from its TOML source"
            ):
                VALIDATOR.validate(destination, REGISTRY)


class AgentProfilePreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _, cls.entries = VALIDATOR.validate(PROFILE_DIR, REGISTRY)

    def check(self, role: str, facts: dict[str, object], collisions=None):
        return VALIDATOR.preflight(
            self.entries[role],
            facts,
            collisions or [],
            trusted_profiles=self.entries,
        )

    def ready_facts(self, model: str, effort: str) -> dict[str, object]:
        return {
            "custom_agent_surface": "available",
            "available_models": [model],
            "reasoning_efforts": {model: [effort]},
        }

    @staticmethod
    def capability_evidence(capability_class: str, tier: str, *, available=True):
        return {
            "available": available,
            "capability_classes": [capability_class],
            "capability_tiers": {capability_class: [tier]},
        }

    def test_ready_when_profile_mapping_is_available(self) -> None:
        result = self.check(
            "loop_v2a_fast_explorer", self.ready_facts("gpt-5.6-terra", "low")
        )
        self.assertEqual(("ready", "ready"), (result["state"], result["decision"]))

    def test_workspace_write_profile_requires_non_widening_parent_sandbox(self) -> None:
        role = "loop_v2a_balanced_worker"
        base = {
            "custom_agent_surface": "available",
            "available_models": ["gpt-5.6-terra"],
            "reasoning_efforts": {"gpt-5.6-terra": ["medium"]},
            "parent_default": self.capability_evidence("balanced-worker", "everyday"),
        }
        unknown = self.check(role, base)
        self.assertEqual("sandbox-constraint-unknown-or-widening", unknown["state"])
        self.assertEqual("parent-default", unknown["fallback_tier"])
        widening = self.check(role, {**base, "parent_sandbox_mode": "read-only"})
        self.assertEqual("sandbox-constraint-unknown-or-widening", widening["state"])
        ready = self.check(role, {**base, "parent_sandbox_mode": "workspace-write"})
        self.assertEqual("ready", ready["decision"])
        self.assertTrue(ready["route_profile_evidence"]["sandbox_non_widening"])

    def test_runtime_model_id_must_match_exactly(self) -> None:
        result = self.check(
            "loop_v2a_balanced_worker",
            {
                "custom_agent_surface": "available",
                "parent_sandbox_mode": "workspace-write",
                "available_models": ["gpt-5.6"],
                "reasoning_efforts": {"gpt-5.6": ["medium"]},
                "parent_default": {
                    "available": True,
                    "capability_classes": ["balanced-worker"],
                    "capability_tiers": {"balanced-worker": ["everyday"]},
                },
            },
        )
        self.assertEqual("unavailable", result["state"])
        self.assertEqual("fallback-safe", result["decision"])
        self.assertEqual("parent-default", result["fallback_tier"])

    def test_unknown_mapping_uses_parent_without_claiming_ready(self) -> None:
        result = self.check(
            "loop_v2a_balanced_worker",
            {
                "custom_agent_surface": "available",
                "parent_default": self.capability_evidence(
                    "balanced-worker", "everyday"
                ),
            },
        )
        self.assertEqual("unknown", result["state"])
        self.assertEqual("fallback-safe", result["decision"])
        self.assertEqual("parent-default", result["fallback_tier"])

    def test_unavailable_mapping_prefers_same_capability_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidates = []
            for suffix in ("2", "1"):
                name = f"loop_v2a_fast_alt_{suffix}"
                path = pathlib.Path(temporary) / f"candidate-{suffix}.toml"
                path.write_text(
                    f'name = "{name}"\n'
                    'description = "Validated fast fallback."\n'
                    'developer_instructions = "Read only."\n'
                    'model = "runtime-fast"\n'
                    'model_reasoning_effort = "low"\n'
                    'sandbox_mode = "read-only"\n',
                    encoding="utf-8",
                )
                candidates.append({
                    "name": name,
                    "profile_path": str(path),
                    "capability_class": "fast-read-explorer",
                    "capability_tier": "efficient",
                    "config_valid": True,
                    "model_available": True,
                    "reasoning_available": True,
                    "sandbox": "read-only",
                    "allowed_workflow_scope": ["read", "search", "summarize", "report-receipt"],
                    "profile_digest": hashlib.sha256(path.read_bytes()).hexdigest(),
                })
            result = self.check(
                "loop_v2a_fast_explorer",
                {
                    "custom_agent_surface": "available",
                    "available_models": ["runtime-fast"],
                    "reasoning_efforts": {"runtime-fast": ["low"]},
                    "compatible_profiles": {"fast-read-explorer": candidates},
                    "parent_default": self.capability_evidence(
                        "fast-read-explorer", "efficient"
                    ),
                },
            )
            self.assertEqual("unavailable", result["state"])
            self.assertEqual("fallback-safe", result["decision"])
            self.assertEqual("parent-default", result["fallback_tier"])
            legacy = VALIDATOR.preflight(
                self.entries["loop_v2a_fast_explorer"],
                {
                    "custom_agent_surface": "available",
                    "available_models": ["runtime-fast"],
                    "reasoning_efforts": {"runtime-fast": ["low"]},
                    "compatible_profiles": {"fast-read-explorer": candidates},
                    "parent_default": self.capability_evidence(
                        "fast-read-explorer", "efficient"
                    ),
                },
                [],
                enforce_tier=False,
                trusted_profiles=self.entries,
            )
            self.assertEqual("same-capability-profile", legacy["fallback_tier"])
            self.assertEqual("loop_v2a_fast_alt_1", legacy["selected"])
            unavailable = self.check(
                "loop_v2a_fast_explorer",
                {
                    "custom_agent_surface": "available",
                    "available_models": [],
                    "reasoning_efforts": {},
                    "compatible_profiles": {"fast-read-explorer": candidates},
                    "parent_default": self.capability_evidence(
                        "fast-read-explorer", "efficient"
                    ),
                },
            )
            self.assertEqual("parent-default", unavailable["fallback_tier"])

    def test_missing_custom_surface_can_degrade_sequentially(self) -> None:
        result = self.check(
            "loop_v2a_balanced_worker",
            {
                "custom_agent_surface": "unavailable",
                "parent_default": {"available": False},
                "sequential": self.capability_evidence(
                    "balanced-worker", "everyday"
                ),
            },
        )
        self.assertEqual("custom-surface-unavailable", result["state"])
        self.assertEqual("fallback-safe", result["decision"])
        self.assertEqual("sequential-current-session", result["fallback_tier"])

    def test_missing_custom_surface_never_selects_same_class_profile(self) -> None:
        result = self.check(
            "loop_v2a_fast_explorer",
            {
                "custom_agent_surface": "unavailable",
                "compatible_profiles": {
                    "fast-read-explorer": [{
                        "name": "cannot_run_without_surface",
                        "capability_class": "fast-read-explorer",
                        "capability_tier": "efficient",
                        "profile_path": "/unusable-without-surface.toml",
                        "config_valid": True,
                        "model_available": True,
                        "reasoning_available": True,
                        "sandbox": "read-only",
                        "allowed_workflow_scope": ["read", "search", "summarize", "report-receipt"],
                        "profile_digest": "a" * 64,
                    }]
                },
                "parent_default": self.capability_evidence(
                    "fast-read-explorer", "efficient"
                ),
            },
        )
        self.assertEqual("parent-default", result["fallback_tier"])
        self.assertNotEqual("cannot_run_without_surface", result["selected"])

    def test_string_or_incomplete_same_class_evidence_is_rejected(self) -> None:
        for evidence in (["unvalidated_name"], [{"name": "missing_receipts"}]):
            with self.subTest(evidence=evidence), self.assertRaises(
                VALIDATOR.ProfileValidationError
            ):
                self.check(
                    "loop_v2a_fast_explorer",
                    {
                        "custom_agent_surface": "available",
                        "available_models": [],
                        "reasoning_efforts": {},
                        "compatible_profiles": {"fast-read-explorer": evidence},
                    },
                )

    def test_high_risk_role_stops_when_no_safe_degradation_exists(self) -> None:
        result = self.check(
            "loop_v2a_security_reviewer",
            {
                "custom_agent_surface": "unavailable",
                "parent_default": {"available": True},
                "sequential": {"available": True},
            },
        )
        self.assertEqual("custom-surface-unavailable", result["state"])
        self.assertEqual("human-gate", result["decision"])
        self.assertEqual("stop-for-human-gate", result["fallback_tier"])

    def test_deep_role_requires_explicit_parent_capability_match(self) -> None:
        role = "loop_v2a_deep_reviewer"
        unavailable = {
            "custom_agent_surface": "available",
            "available_models": [],
            "reasoning_efforts": {},
            "parent_default": {
                "available": True,
                "capability_classes": ["deep-reviewer"],
                "capability_tiers": {"deep-reviewer": ["deep"]},
            },
        }
        result = self.check(role, unavailable)
        self.assertEqual("fallback-safe", result["decision"])
        self.assertEqual("parent-default", result["fallback_tier"])

    def test_security_role_allows_only_explicit_compatible_parent_or_sequential(self) -> None:
        base = {
            "custom_agent_surface": "unavailable",
            "parent_default": {"available": True},
            "sequential": {"available": True},
        }
        self.assertEqual("human-gate", self.check("loop_v2a_security_reviewer", base)["decision"])
        compatible = {
            **base,
            "parent_default": self.capability_evidence(
                "security-reviewer", "deep"
            ),
        }
        result = self.check("loop_v2a_security_reviewer", compatible)
        self.assertEqual("fallback-safe", result["decision"])
        self.assertEqual("parent-default", result["fallback_tier"])
        sequential = {
            **base,
            "parent_default": {"available": False},
            "sequential": self.capability_evidence("security-reviewer", "deep"),
        }
        result = self.check("loop_v2a_security_reviewer", sequential)
        self.assertEqual("fallback-safe", result["decision"])
        self.assertEqual("sequential-current-session", result["fallback_tier"])

    def test_collision_is_a_human_gate(self) -> None:
        result = self.check(
            "loop_v2a_fast_explorer",
            self.ready_facts("gpt-5.6-terra", "low"),
            [{"name": "loop_v2a_fast_explorer", "path": "/redacted/agent.toml"}],
        )
        self.assertEqual(("human-gate", "human-gate"), (result["state"], result["decision"]))
        self.assertEqual("profile-name-collision", result["reason"])

    def test_security_profile_is_defensive_and_local_first(self) -> None:
        profile = VALIDATOR.load_profile(
            PROFILE_DIR / "loop_v2a_security_reviewer.toml"
        )
        instructions = profile["developer_instructions"]
        for phrase in (
            "defensive, local-first validation",
            "local fixtures",
            "do not evade the classifier",
            "do not edit, publish, interact with",
        ):
            self.assertIn(phrase, instructions)


if __name__ == "__main__":
    unittest.main()
