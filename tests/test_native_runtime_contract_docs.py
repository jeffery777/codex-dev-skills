from __future__ import annotations

import pathlib
import re
import unittest

import yaml


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
        example = read("examples/desktop-thread-delegation.md")
        combined = "\n".join((readme, guide, thread_skill, example))

        self.assertIn("already selected by shared orchestration", combined)
        self.assertNotIn(
            "desktop-thread-delegation to choose the next safe task",
            combined,
        )
        self.assertNotIn(
            "Desktop should choose the next safe task",
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

    def test_desktop_fork_preserves_remote_host_identity(self) -> None:
        contract = read("docs/native-runtime-capabilities.md")
        adapter = read("docs/runtime-adapter-v2.md")
        thread_skill = read("skills/desktop-thread-delegation/SKILL.md")
        example = read("examples/desktop-thread-delegation.md")
        evidence = read(
            "docs/codex-runtime-compatibility-evidence-2026-08-12.md"
        )
        combined = "\n".join(
            (contract, adapter, thread_skill, example, evidence)
        )

        for expected in (
            "source task anchors the host",
            "no caller-supplied `hostId`",
            "supported registry",
            "destinationHostId",
            "unresolved remote child",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, combined)

        self.assertRegex(
            combined,
            re.compile(
                r"(?:does not|doesn't)\s+guarantee\s+`hostId`",
                re.IGNORECASE,
            ),
        )

    def test_chatgpt_desktop_name_preserves_runtime_layers(self) -> None:
        readme = read("README.md")
        compatibility = read("docs/runtime-compatibility.md")
        evidence = read("docs/codex-runtime-compatibility-evidence-2026-07-31.md")
        contract = read("docs/native-runtime-capabilities.md")
        combined = "\n".join((readme, compatibility, evidence, contract))

        self.assertIn("ChatGPT desktop app", combined)
        self.assertIn("compatibility labels", combined)
        self.assertIn("shared reasoning or subagent delegation", combined)
        self.assertIn("thin adapters", evidence)
        self.assertIn("App-server remains a separate JSON-RPC contract family", evidence)

    def test_latest_runtime_evidence_records_current_versions_and_schemas(self) -> None:
        evidence = read("docs/codex-runtime-compatibility-evidence-2026-08-12.md")

        for expected in (
            "0.147.0",
            "schemaVersion: 2",
            "schemaVersion: 4",
            "pinnedThreads",
            "pinnedIndex",
            "version unavailable",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, evidence)

        self.assertTrue(
            (ROOT / "docs/codex-runtime-compatibility-evidence-2026-07-31.md").is_file()
        )

    def test_desktop_post_create_visibility_contract(self) -> None:
        contract = read("docs/native-runtime-capabilities.md")
        adapter = read("docs/runtime-adapter-v2.md")
        thread_skill = read("skills/desktop-thread-delegation/SKILL.md")
        example = read("examples/desktop-thread-delegation.md")
        boundary_example = read("examples/runtime-adapter-boundary.md")
        combined = "\n".join(
            (contract, adapter, thread_skill, example, boundary_example)
        )

        for expected in (
            '::created-thread{threadId="..."}',
            '::created-thread{clientThreadId="..."}',
            "navigate_to_codex_page",
            "Registry presence does not prove sidebar rendering",
            "must never trigger duplicate creation",
            "Pinning changes placement only",
            "codex://threads/<threadId>",
            "Chronological",
            "Archived chats",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, combined)

        self.assertRegex(
            thread_skill,
            re.compile(r"Do not navigate automatically after creation"),
        )
        self.assertRegex(
            combined,
            re.compile(r"local chat", re.IGNORECASE),
        )
        self.assertIn(
            '"required_request_fields": ["prompt", "target"]',
            boundary_example,
        )
        self.assertNotIn(
            '"required_request_fields": ["thread_id"]',
            boundary_example,
        )

    def test_desktop_target_selection_preserves_project_and_worktree_intent(self) -> None:
        contract = read("docs/native-runtime-capabilities.md")
        adapter = read("docs/runtime-adapter-v2.md")
        skill = read("skills/desktop-thread-delegation/SKILL.md")
        example = read("examples/desktop-thread-delegation.md")
        combined = "\n".join((contract, adapter, skill, example))

        for expected in (
            "same-directory",
            '"type": "local"',
            '"type": "worktree"',
            "projectless",
            "existing worktree",
            "Do not create a new worktree",
            "source task must stop writing",
            "default to project",
            "explicitly requests the saved project checkout",
            "non-Git projects",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, combined)

        self.assertRegex(
            combined,
            re.compile(
                r"(?:does not|doesn't|never)\s+imply\s+`?projectless`?",
                re.IGNORECASE,
            ),
        )

    def test_desktop_create_title_and_project_association_are_distinct(self) -> None:
        contract = read("docs/native-runtime-capabilities.md")
        adapter = read("docs/runtime-adapter-v2.md")
        skill = read("skills/desktop-thread-delegation/SKILL.md")
        example = read("examples/desktop-thread-delegation.md")
        boundary = read("examples/runtime-adapter-boundary.md")
        combined = "\n".join((contract, adapter, skill, example, boundary))

        for expected in (
            "concise non-empty safe `title`",
            "callable keeps `title` optional",
            "maintainer-approved nonsensitive task identifier",
            "never copy prompt text",
            "`Project task`",
            "preview",
            "display evidence only",
            "observed `projectId`",
            "selected project",
            "never create a duplicate",
            '"adapter_required_fields": ["title"]',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, combined)

        self.assertIn(
            '"required_request_fields": ["prompt", "target"]',
            boundary,
        )

        pipeline_section = boundary.split(
            "## End-To-End Evidence Pipeline Fixture", 1
        )[1].split("## Session Compatibility Status", 1)[0]
        self.assertNotIn(
            "python3 scripts/desktop_runtime_evidence_pipeline.py",
            pipeline_section,
        )
        self.assertEqual(
            4,
            pipeline_section.count(
                "./scripts/project-python "
                "scripts/desktop_runtime_evidence_pipeline.py"
            ),
        )

    def test_worktree_python_environment_contract_covers_desktop_and_cli(self) -> None:
        agents = read("AGENTS.md")
        readme = read("README.md")
        contract = read("docs/native-runtime-capabilities.md")
        compatibility = read("docs/runtime-compatibility.md")
        desktop = read("skills/desktop-thread-delegation/SKILL.md")
        cli = read("skills/cli-session-handoff/SKILL.md")
        evidence = read("docs/codex-runtime-compatibility-evidence-2026-08-12.md")
        combined = "\n".join(
            (agents, readme, contract, compatibility, desktop, cli, evidence)
        )

        for expected in (
            "scripts/project-python",
            ".python-version",
            "disposable private clone",
            "bare system Python",
            ".worktreeinclude",
            "Do not copy `.venv`",
            "shared, not Desktop-only",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, combined)

    def test_desktop_callable_contract_covers_new_boundaries(self) -> None:
        contract = read("docs/native-runtime-capabilities.md")
        adapter = read("docs/runtime-adapter-v2.md")
        policy = read("policies/runtime-compatibility-policy.md")
        combined = "\n".join((contract, adapter, policy))

        for expected in (
            "chatgptWorkCloud",
            "projectless.directoryName",
            "chatgptWorkCloud.projectId",
            "isGitRepository",
            "get_handoff_status",
            "Cloud handoff is unsupported",
            "heartbeat",
            "cron automation",
            "untrusted",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, combined)

        self.assertRegex(
            combined,
            re.compile(r"`clientThreadId` is not a `threadId`"),
        )
        self.assertRegex(
            combined,
            re.compile(
                r"cloud target(?:s)? may\s+carry\s+`chatgptWorkCloud\.projectId`",
                re.IGNORECASE,
            ),
        )
        self.assertRegex(
            combined,
            re.compile(
                r"cross-host\s+handoff requires\s+additional explicit authorization",
                re.IGNORECASE,
            ),
        )

    def test_cli_and_desktop_entry_paths_remain_distinct(self) -> None:
        readme = read("README.md")
        shared = read("skills/project-orchestrator/SKILL.md")
        cli = read("skills/cli-session-handoff/SKILL.md")
        desktop = read("skills/desktop-project-delivery/SKILL.md")

        self.assertIn("### CLI And Desktop Entry Paths", readme)
        self.assertIn("Codex CLI enters the shared layer directly", readme)
        self.assertIn("`/app`", readme)
        self.assertIn("Runtime compatibility: shared", shared)
        self.assertIn("Runtime compatibility: cli", cli)
        self.assertIn("Runtime compatibility: desktop", desktop)
        self.assertIn("thin CLI control-plane adapter", cli)
        self.assertIn("thin UX adapter", desktop)

    def test_cli_session_adapter_uses_stable_public_surface(self) -> None:
        contract = read("docs/native-runtime-capabilities.md")
        skill = read("skills/cli-session-handoff/SKILL.md")
        policy = read("policies/runtime-compatibility-policy.md")
        implementation = read(
            "skills/cli-session-handoff/scripts/cli_session_handoff.py"
        )
        combined = "\n".join((contract, skill, policy))

        for expected in (
            "codex exec --json",
            "codex exec resume",
            "parent integration",
            "permission widening",
            "private session",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, combined)

        self.assertIn('"codex-cli-session-handoff/v0"', implementation)
        self.assertIn("shell=False", implementation)
        self.assertIn('shell_environment_policy.inherit="core"', implementation)
        self.assertIn("ProcessTreeTracker", implementation)
        self.assertIn("_prepare_isolated_workspace", implementation)
        self.assertIn("_apply_isolated_patch", implementation)
        self.assertIn("OMITTED_FINAL_SUMMARY", implementation)
        self.assertIn("private clone", combined)
        self.assertNotIn("shell=True", implementation)
        self.assertNotIn("desktop_runtime_", implementation)
        self.assertNotIn("create_thread", implementation)

    def test_cli_interactive_fork_is_manual_and_reuses_selected_directory(self) -> None:
        contract = read("docs/native-runtime-capabilities.md")
        adapter = read("docs/runtime-adapter-v2.md")
        skill = read("skills/cli-session-handoff/SKILL.md")
        example = read("examples/cli-session-handoff.md")
        evidence = read("docs/codex-runtime-compatibility-evidence-2026-07-31.md")
        implementation = read(
            "skills/cli-session-handoff/scripts/cli_session_handoff.py"
        )
        combined = "\n".join((contract, adapter, skill, example, evidence))

        for expected in (
            "codex fork <SESSION_ID>",
            "tui.resume_cwd",
            '"current"',
            '"session"',
            "exact UUID",
            "manual interactive",
            "existing worktree",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, combined)

        self.assertRegex(
            combined,
            re.compile(r"does not create (?:a|another) Git worktree", re.IGNORECASE),
        )
        self.assertIn(
            "A prepared interactive-fork command is a handoff artifact",
            skill,
        )
        self.assertNotIn("codex fork", implementation)

    def test_cli_session_skill_group_separation(self) -> None:
        catalog = yaml.safe_load(read("catalog.yaml"))
        groups = catalog["groups"]

        def transitive_skill_sources(group_name: str) -> set[str]:
            pending = [group_name]
            visited: set[str] = set()
            sources: set[str] = set()
            while pending:
                current = pending.pop()
                if current in visited:
                    continue
                visited.add(current)
                group = groups[current]
                sources.update(entry["source"] for entry in group.get("skills", []))
                pending.extend(group.get("depends_on", []))
            return sources

        cli_sources = transitive_skill_sources("codex-cli-session-handoff")
        delivery_sources = transitive_skill_sources("codex-delivery-workflow")
        desktop_sources = transitive_skill_sources("desktop-delivery-workflow")

        self.assertEqual("cli", groups["codex-cli-session-handoff"]["runtime"])
        self.assertIn("codex-delivery-workflow", groups["codex-cli-session-handoff"]["depends_on"])
        self.assertIn("skills/cli-session-handoff", cli_sources)
        self.assertNotIn("skills/cli-session-handoff", delivery_sources)
        self.assertNotIn("skills/cli-session-handoff", desktop_sources)

    def test_legacy_desktop_gates_are_compatibility_aliases(self) -> None:
        routes = {
            "skills/desktop-spec-plan-gate/SKILL.md": "`planning`",
            "skills/desktop-implementation-gate/SKILL.md": "`code-review`",
            "skills/desktop-pr-merge-gate/SKILL.md": "`merge-readiness-gate`",
        }

        for path, route in routes.items():
            with self.subTest(path=path):
                skill = read(path)
                self.assertIn("Compatibility status: deprecated compatibility alias", skill)
                self.assertIn(route, skill)
                self.assertIn("does not use a Desktop callable", skill)

        workflow = read("workflows/desktop-delivery-workflow.md")
        self.assertIn("deprecated compatibility aliases", workflow)
        self.assertRegex(workflow, re.compile(r"do\s+not add Desktop callable behavior"))

    def test_catalog_alias_metadata_is_typed_and_resolvable(self) -> None:
        catalog = yaml.safe_load(read("catalog.yaml"))
        entries = [
            entry
            for group in catalog["groups"].values()
            for entry in group.get("skills", [])
        ]
        sources = {entry["source"] for entry in entries}
        aliases = [
            entry
            for entry in entries
            if entry.get("status") == "deprecated-compatibility-alias"
        ]

        self.assertEqual(3, len(aliases))
        for entry in aliases:
            with self.subTest(source=entry["source"]):
                self.assertIsInstance(entry.get("routes_to"), list)
                self.assertTrue(entry["routes_to"])
                self.assertLessEqual(set(entry["routes_to"]), sources)

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
