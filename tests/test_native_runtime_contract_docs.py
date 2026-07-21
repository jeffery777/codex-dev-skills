from __future__ import annotations

import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class NativeRuntimeContractDocsTests(unittest.TestCase):
    def test_contract_covers_capability_families_and_authority(self) -> None:
        contract = read("docs/native-runtime-capabilities.md")

        for heading in (
            "## Authority Mapping",
            "### Native goal",
            "### Shared subagents",
            "### Scheduler",
            "### Desktop thread control plane",
            "### Hooks",
            "### Sequential fallback",
            "## Legacy Desktop Wrapper Boundary",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, contract)

        self.assertIn("completion authority", contract)
        self.assertIn("clientThreadId", contract)
        self.assertIn("explicit user request", contract)

    def test_subagent_delegation_is_cross_runtime(self) -> None:
        policy = read("policies/runtime-compatibility-policy.md")
        loop_skill = read("skills/loop-engineering/SKILL.md")
        desktop_delivery = read("skills/desktop-project-delivery/SKILL.md")
        combined = "\n".join((policy, loop_skill, desktop_delivery))

        self.assertIn("Subagent delegation is shared", combined)
        self.assertIn("Ordinary subagent delegation is not Desktop-only", desktop_delivery)
        self.assertNotRegex(
            combined,
            re.compile(r"Desktop-only behavior includes[^\n]*worker delegation", re.IGNORECASE),
        )

    def test_desktop_skills_are_thin_adapters(self) -> None:
        thread_skill = read("skills/desktop-thread-delegation/SKILL.md")
        delivery_skill = read("skills/desktop-project-delivery/SKILL.md")

        self.assertIn("thin Desktop UX adapter", thread_skill)
        self.assertIn("thin UX adapter", delivery_skill)
        self.assertRegex(thread_skill, re.compile(r"shared\s+subagent delegation"))
        self.assertIn("shared `project-delivery` workflow", delivery_skill)
        self.assertIn("Creating a new or background Desktop task requires an explicit user request", thread_skill)

    def test_desktop_thread_adapter_does_not_own_task_selection(self) -> None:
        readme = read("README.md")
        guide = read("docs/skill-selection-guide.md")
        thread_skill = read("skills/desktop-thread-delegation/SKILL.md")
        combined = "\n".join((readme, guide, thread_skill))

        self.assertIn("already selected by shared orchestration", combined)
        self.assertNotIn(
            "desktop-thread-delegation to choose the next safe task",
            combined,
        )
        self.assertNotIn("- Candidate tasks and statuses", thread_skill)
        self.assertNotIn("- Selected next safe task", thread_skill)

    def test_desktop_wait_observation_is_host_aware_and_non_authoritative(self) -> None:
        contract = read("docs/native-runtime-capabilities.md")
        adapter = read("docs/runtime-adapter-v2.md")
        thread_skill = read("skills/desktop-thread-delegation/SKILL.md")
        combined = "\n".join((contract, adapter, thread_skill))

        self.assertIn("wait_threads", combined)
        self.assertIn("hostId", combined)
        self.assertIn("afterCursor", combined)
        self.assertIn("one to eight", combined)
        self.assertIn("compact progress snapshots", combined)
        self.assertRegex(combined, re.compile(r"snapshot never proves\s+completion"))

    def test_chatgpt_desktop_name_preserves_runtime_layers(self) -> None:
        readme = read("README.md")
        compatibility = read("docs/runtime-compatibility.md")
        evidence = read("docs/codex-runtime-compatibility-evidence-2026-07-21.md")
        contract = read("docs/native-runtime-capabilities.md")
        combined = "\n".join((readme, compatibility, evidence, contract))

        self.assertIn("ChatGPT desktop app", combined)
        self.assertIn("compatibility labels", combined)
        self.assertIn("shared reasoning or subagent delegation", combined)
        self.assertIn("thin adapters", evidence)
        self.assertIn("App-server remains a separate JSON-RPC contract family", evidence)

    def test_hooks_are_optional_incomplete_guardrails(self) -> None:
        contract = read("docs/native-runtime-capabilities.md")
        loop_skill = read("skills/loop-engineering/SKILL.md")
        policy = read("policies/runtime-compatibility-policy.md")

        self.assertIn("Hooks are not a complete enforcement boundary", contract)
        self.assertIn("Hooks are optional guardrails and must not be described as complete enforcement", policy)
        self.assertIn("Hooks are optional guardrails and are not complete enforcement", loop_skill)

    def test_native_core_does_not_depend_on_legacy_desktop_helpers(self) -> None:
        loop_root = ROOT / "skills" / "loop-engineering"
        python_sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(loop_root.rglob("*.py"))
        )

        self.assertNotRegex(
            python_sources,
            re.compile(r"(?:^|\n)\s*(?:from|import)\s+desktop_runtime_", re.MULTILINE),
        )
        self.assertNotIn("desktop_runtime_", python_sources)
        self.assertNotIn("scripts.desktop_runtime_", python_sources)

        for relative_path in (
            "skills/loop-engineering/SKILL.md",
            "skills/desktop-thread-delegation/SKILL.md",
            "skills/desktop-project-delivery/SKILL.md",
        ):
            with self.subTest(relative_path=relative_path):
                self.assertIn("compatibility evidence only", read(relative_path))


if __name__ == "__main__":
    unittest.main()
