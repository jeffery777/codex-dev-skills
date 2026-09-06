from __future__ import annotations

import pathlib
import re
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/loop-engineering/scripts"))

import loop_core  # noqa: E402


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class LoopStateRoadmapDocsTests(unittest.TestCase):
    def test_documented_phase_routes_match_production_outputs(self) -> None:
        skill = read("skills/loop-engineering/SKILL.md")
        table = skill.split("| Input selector | Emitted route | Meaning |", 1)[1]
        table = table.split("\n\n", 1)[0]
        documented = dict(re.findall(r"^\| `([^`]+)` \| `([^`]+)` \|", table, re.MULTILINE))
        self.assertEqual(loop_core.ROUTES, documented)
        for selector, expected in documented.items():
            kind, _, risk = selector.partition(":")
            with self.subTest(selector=selector):
                result = loop_core.evaluate_workflow_case(
                    {"id": selector, "input": {
                        "request": {"kind": kind, "risk": risk or "routine"},
                        "objective": {"clear": True},
                        "state": {"protected_history_sha256": "none"},
                    }},
                    trusted_authority={"protected_history_sha256": "none"},
                )
                self.assertEqual(expected, result["route"])
                self.assertEqual("continue", result["next_decision"])
        self.assertIn("upper-layer `milestone-continuation`", skill)
        self.assertIn("There is no milestone request kind", skill)

    def test_milestone_continuation_selects_packet_then_routes_its_phase(self) -> None:
        authority = {"protected_history_sha256": "none"}
        for surface, scheduler, expected_mode in (
            ("desktop", True, "desktop-scheduled"),
            ("cli", False, "sequential-fallback"),
        ):
            with self.subTest(surface=surface):
                current = {
                    "request": {"kind": "continuation", "scheduled": True},
                    "objective": {"clear": True},
                    "state": {"protected_history_sha256": "none"},
                    "runtime": {"surface": surface, "capabilities": {"scheduler": scheduler}},
                }
                continuation = loop_core.evaluate_workflow_case(
                    {"id": "milestone-next-packet", "input": current},
                    trusted_authority=authority,
                )
                self.assertEqual("task-continuation", continuation["route"])
                self.assertEqual(expected_mode, continuation["execution_mode"])
                self.assertFalse(continuation["complete"])
                # The upper-layer owner selected a ready implementation packet;
                # its phase is routed again, never inferred from the wakeup.
                current["request"] = {"kind": "implementation"}
                packet = loop_core.evaluate_workflow_case(
                    {"id": "selected-implementation-packet", "input": current},
                    trusted_authority=authority,
                )
                self.assertEqual("implementation-slice", packet["route"])
                self.assertEqual("current-session", packet["execution_mode"])
                current["request"] = {"kind": "milestone"}
                unsupported = loop_core.evaluate_workflow_case(
                    {"id": "unsupported-milestone-kind", "input": current},
                    trusted_authority=authority,
                )
                self.assertEqual("human-gate", unsupported["route"])
                self.assertIn("unsupported-request-kind", unsupported["violations"])

    def test_protected_action_inventory_matches_production(self) -> None:
        skill = read("skills/loop-engineering/SKILL.md")
        reference = "references/loop-state-and-authorization.md"
        self.assertIn(reference, skill)
        contract = read(f"skills/loop-engineering/{reference}")
        actions = contract.split("### Protected Event Authorization", 1)[1]
        actions = actions.split("as protected live actions", 1)[0]
        self.assertEqual(set(loop_core.PROTECTED_EVENT_ACTIONS), set(re.findall(r"`([^`]+)`", actions)))

    def test_loop_references_are_triggered_and_reachable(self) -> None:
        skill_root = ROOT / "skills/loop-engineering"
        skill = read("skills/loop-engineering/SKILL.md")
        self.assertIn("Load a reference before the matching action", skill)
        self.assertIn("do not preload the whole table", skill)
        references = set(re.findall(r"`(references/[a-z-]+\.md)`", skill))
        self.assertEqual(
            references,
            {
                "references/loop-state-and-authorization.md",
                "references/agent-routing.md",
                "references/agent-qualification.md",
                "references/security-scan-recovery.md",
                "references/context-continuity.md",
                "references/gitnexus-runtime.md",
                "references/optional-evidence-memory.md",
            },
        )
        for relative in sorted(references):
            with self.subTest(reference=relative):
                path = skill_root / relative
                self.assertTrue(path.is_file())
                content = path.read_text(encoding="utf-8")
                self.assertIn("Read", content)
                # Check distributed sibling contracts and source fallbacks;
                # installed template fallbacks are named separately in prose.
                for link in re.findall(r"`((?:\.\./){3}[^`]+\.md|[a-z-]+-v[01]\.md)`", content):
                    self.assertTrue((path.parent / link).is_file(), (relative, link))

    def test_ordinary_delegation_has_a_direct_qualification_path(self) -> None:
        relative = "../loop-engineering/references/agent-qualification.md"
        for name in ("project-delivery", "project-orchestrator"):
            with self.subTest(skill=name):
                path = ROOT / "skills" / name / "SKILL.md"
                content = path.read_text(encoding="utf-8")
                self.assertIn(relative, content)
                self.assertTrue((path.parent / relative).is_file())
                self.assertIn("ordinary", content.lower())
        qualification = read("skills/loop-engineering/references/agent-qualification.md")
        for phrase in (
            "no requirement to load the durable loop entrypoint",
            "agent-routing.md",
            "enabled_candidates",
            "an explicit `{}` disables candidates",
            "current native callable supports",
            "Missing, revoked or mismatched qualification",
        ):
            self.assertIn(phrase, qualification)

    def test_reuse_requires_content_worktree_and_phase_freshness(self) -> None:
        for relative in (
            "skills/loop-engineering/SKILL.md",
            "skills/project-delivery/SKILL.md",
            "skills/project-orchestrator/SKILL.md",
            "workflows/loop-engineering-workflow.md",
        ):
            content = read(relative)
            with self.subTest(path=relative):
                for phrase in (
                    "worktree", "tracked/untracked", "phase", "policy",
                    "environment", "provenance", "freshness",
                ):
                    self.assertIn(phrase, content)
        skill = read("skills/loop-engineering/SKILL.md")
        for phrase in (
            "production decision function is the active routing authority",
            "Every `decide` invocation requires current-session protected-history inspection",
            "`none` only after independently",
            "unchanged SHA alone does not prove",
            "complete new base-to-head Merge Review",
            "memory-off",
            "zero backend/filesystem touch",
        ):
            self.assertIn(phrase, skill)

    def test_completed_loop_state_baseline_is_not_future_work(self) -> None:
        roadmap = " ".join(read("docs/roadmap.md").split())
        for phrase in (
            "Issue #77 / PR #78 delivered repo-owned loop state and ledger support",
            "durable baseline, not a future task-selection target",
            "contract, templates, validator, tests, and v0.4.0 point-in-time release note",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, roadmap)

        self.assertNotIn(
            "Repo-owned loop state and ledger support is the next loop-engineering hardening step",
            roadmap,
        )


if __name__ == "__main__":
    unittest.main()
