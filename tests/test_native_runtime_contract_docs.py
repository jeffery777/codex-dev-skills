from __future__ import annotations

import pathlib
import re
import tempfile
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]

ACTIVE_CANONICAL_GUIDANCE_FILES = (
    "docs/desktop-runtime-wrapper-v1-deprecation.md",
    "docs/native-runtime-capabilities.md",
    "docs/release-readiness.md",
    "docs/roadmap.md",
    "docs/runtime-compatibility.md",
    "docs/skill-selection-guide.md",
    "docs/source-classification.md",
)

RETIRED_WRAPPER_RUNNABLE_REFERENCE = re.compile(
    r"(?:"
    r"(?:python(?:3)?|project-python)(?:[^\n]|\\\n){0,240}"
    r"(?:scripts[/\\.]?)?desktop[_-]?runtime[_-]"
    r"|(?:from|import)\s+(?:scripts\.)?desktop[_-]?runtime[_-]"
    r"|(?:\./)?scripts/desktop[_-]?runtime[_-]"
    r")",
    re.IGNORECASE,
)


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def read_scanned_guidance(path: pathlib.Path, root: pathlib.Path = ROOT) -> str:
    relative_path = path.relative_to(root).as_posix()
    if path.is_symlink():
        raise ValueError(f"active guidance must not be a symlink: {relative_path}")
    try:
        resolved_path = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError(f"active guidance path is missing: {relative_path}") from exc
    if not resolved_path.is_relative_to(root.resolve()):
        raise ValueError(
            f"active guidance must resolve inside the repository: {relative_path}"
        )
    return resolved_path.read_text(encoding="utf-8")


def collect_active_guidance(
    active_roots: tuple[pathlib.Path, ...],
    repo_root: pathlib.Path = ROOT,
) -> list[pathlib.Path]:
    collected: list[pathlib.Path] = []
    for active_root in active_roots:
        relative_root = active_root.relative_to(repo_root).as_posix()
        if active_root.is_symlink():
            raise ValueError(
                f"active guidance root must not be a symlink: {relative_root}"
            )
        if not active_root.exists():
            continue
        resolved_root = active_root.resolve(strict=True)
        if not resolved_root.is_relative_to(repo_root.resolve()):
            raise ValueError(
                "active guidance root must resolve inside the repository: "
                f"{relative_root}"
            )
        collected.extend(
            path
            for path in active_root.rglob("*")
            if path.is_file() or path.is_symlink()
        )
    return collected


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
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, contract)

        self.assertIn("completion authority", contract)
        self.assertIn("clientThreadId", contract)
        self.assertIn("explicit user request", contract)
        self.assertIn("callable schema", contract)
        self.assertIn("call-site validation", contract)
        self.assertIn("private-state boundaries", contract)
        self.assertIn("external-write authorization", contract)
        self.assertIn("fail-closed handling", contract)
        self.assertIn("default non-execution", contract)

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
        evidence = read("docs/codex-runtime-compatibility-evidence-2026-08-25.md")

        for expected in (
            "0.149.1",
            "codex mcp-server",
            "deprecated",
            "not removed",
            "Unknown",
            "Codex app server",
            "Codex SDK",
            "codex mcp add",
            "external MCP servers",
            "native thread tools",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, evidence)

        self.assertNotIn("all MCP server support is deprecated", evidence)
        self.assertIn("No Desktop callable schema was re-read", evidence)

        self.assertTrue(
            (ROOT / "docs/codex-runtime-compatibility-evidence-2026-07-31.md").is_file()
        )
        self.assertTrue(
            (ROOT / "docs/codex-runtime-compatibility-evidence-2026-08-12.md").is_file()
        )
        self.assertTrue(
            (ROOT / "docs/codex-runtime-compatibility-evidence-2026-08-18.md").is_file()
        )
        self.assertTrue(
            (ROOT / "docs/codex-runtime-compatibility-evidence-2026-08-19.md").is_file()
        )
        self.assertTrue(
            (ROOT / "docs/codex-runtime-compatibility-evidence-2026-08-25.md").is_file()
        )

    def test_cli_queue_and_desktop_share_preserve_runtime_layers(self) -> None:
        contract = read("docs/native-runtime-capabilities.md")
        compatibility = read("docs/runtime-compatibility.md")
        cli_skill = read("skills/cli-session-handoff/SKILL.md")
        desktop_skill = read("skills/desktop-thread-delegation/SKILL.md")
        human_gate = read("policies/human-gate-policy.md")
        combined = "\n".join(
            (contract, compatibility, cli_skill, desktop_skill, human_gate)
        )

        for expected in (
            "codex agents",
            "codex queue",
            "canonical UUID",
            "argv token",
            "dispatch/wakeup evidence",
            "share_thread",
            "immutable",
            "sensitive-content review",
            "data controls",
            "completion authority",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, combined)

        self.assertRegex(
            cli_skill,
            re.compile(r"private-clone executor\s+does not automate"),
        )
        self.assertIn("exposes no revoke operation", desktop_skill)
        self.assertIn(
            "user to confirm review of the complete thread",
            desktop_skill,
        )
        self.assertNotIn("CLI `share_thread`", combined)

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

        self.assertIn("private runtime state", combined)
        self.assertIn("external write", combined)
        self.assertIn("explicit user request", combined)

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
            "automation_update",
            "notificationPolicy",
            "startingState",
            "branchName",
            "create-branch",
            "list_archived_threads",
            "open_in_codex",
            "read_thread_terminal",
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

    def test_plugins_imports_and_runtime_memories_keep_separate_authority(self) -> None:
        readme = read("README.md")
        compatibility = read("docs/runtime-compatibility.md")
        contract = read("docs/native-runtime-capabilities.md")
        policy = read("policies/runtime-compatibility-policy.md")
        evidence = read("docs/codex-runtime-compatibility-evidence-2026-08-18.md")
        combined = "\n".join((readme, compatibility, contract, policy, evidence))

        for expected in (
            "/plugins",
            "/import",
            "/memories",
            "universal plugin",
            "Computer History",
            "loop-memory-sqlite/v0",
            "advisory context",
            "not `cli-session-handoff` operations",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, combined)

        self.assertRegex(
            combined,
            re.compile(r"(?:never|not).*completion authority", re.IGNORECASE),
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
            "codex exec fork",
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
        self.assertIn(
            'ALLOWED_OPERATIONS = {"start", "resume", "fork", "fresh-continuation"}',
            implementation,
        )
        self.assertIn("loop-context-continuity/v1", combined)
        self.assertIn("clean", combined)
        self.assertIn("non-interactive", combined)
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

    def test_desktop_worktree_fork_preserves_lineage_and_queued_identity(self) -> None:
        contract = read("docs/native-runtime-capabilities.md")
        adapter = read("docs/runtime-adapter-v2.md")
        skill = read("skills/desktop-thread-delegation/SKILL.md")
        example = read("examples/desktop-thread-delegation.md")
        combined = "\n".join((contract, adapter, skill, example))

        for expected in (
            "desktop-worktree-fork",
            '`environment: {"type": "worktree"}`',
            "completed history",
            "clientThreadId",
            "conversation lineage",
            "usable `threadId`",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, combined)

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
                skill = read(relative_path)
                self.assertIn("native-runtime-capabilities.md", skill)
                self.assertIn("call-site validation", skill)
                self.assertIn("must not be imported, executed, or", skill)
                self.assertIn("recommended", skill)
                self.assertNotIn("desktop_runtime_", skill)

    def test_retired_desktop_wrapper_cannot_be_reintroduced(self) -> None:
        retired_artifact_name = re.compile(
            r"^(?:test[_-])?desktop[_-]?runtime[_-]",
            re.IGNORECASE,
        )
        reintroduced_artifacts = [
            path.relative_to(ROOT).as_posix()
            for root in (ROOT / "scripts", ROOT / "tests")
            for path in root.rglob("*")
            if retired_artifact_name.match(path.name)
        ]
        self.assertEqual([], sorted(reintroduced_artifacts))

        active_guidance_files = (
            ROOT / "README.md",
            ROOT / "CONTRIBUTING.md",
            ROOT / "catalog.yaml",
            ROOT / "install.sh",
            ROOT / "plugin/codex-dev-skills/.codex-plugin/plugin.json",
            *(ROOT / path for path in ACTIVE_CANONICAL_GUIDANCE_FILES),
        )
        active_guidance_roots = (
            ROOT / ".agents",
            ROOT / ".codex",
            ROOT / "examples",
            ROOT / "policies",
            ROOT / "skills",
            ROOT / "templates/hooks",
            ROOT / "workflows",
            ROOT / "plugin/codex-dev-skills/docs",
            ROOT / "plugin/codex-dev-skills/skills",
        )
        active_guidance = list(active_guidance_files)
        active_guidance.extend(collect_active_guidance(active_guidance_roots))

        for path in active_guidance:
            relative_path = path.relative_to(ROOT).as_posix()
            with self.subTest(relative_path=relative_path):
                try:
                    guidance = read_scanned_guidance(path)
                except UnicodeDecodeError:
                    continue
                self.assertNotRegex(guidance, RETIRED_WRAPPER_RUNNABLE_REFERENCE)

    def test_active_canonical_docs_reject_runnable_wrapper_guidance(self) -> None:
        self.assertIn(
            "docs/runtime-compatibility.md",
            ACTIVE_CANONICAL_GUIDANCE_FILES,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = pathlib.Path(temp_dir)
            canonical_doc = repo_root / "docs/runtime-compatibility.md"
            canonical_doc.parent.mkdir()
            canonical_doc.write_text(
                "Run ./scripts/desktop_runtime_probe.py for compatibility.",
                encoding="utf-8",
            )

            guidance = read_scanned_guidance(canonical_doc, repo_root)
            self.assertRegex(guidance, RETIRED_WRAPPER_RUNNABLE_REFERENCE)

    def test_active_guidance_scan_rejects_out_of_repo_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = pathlib.Path(temp_dir)
            repo_root = temp_root / "repo"
            repo_root.mkdir()
            external = temp_root / "external.txt"
            external.write_text(
                "synthetic marker ./scripts/desktop_runtime_probe.py",
                encoding="utf-8",
            )
            guidance_link = repo_root / "guidance.md"
            guidance_link.symlink_to(external)

            with self.assertRaisesRegex(
                ValueError,
                r"must not be a symlink: guidance\.md",
            ) as raised:
                read_scanned_guidance(guidance_link, repo_root)

            self.assertNotIn("synthetic marker", str(raised.exception))

    def test_active_guidance_scan_rejects_symlink_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = pathlib.Path(temp_dir)
            repo_root = temp_root / "repo"
            repo_root.mkdir()
            external_root = temp_root / "external"
            external_root.mkdir()

            root_targets = (
                ("external-root", external_root),
                ("broken-root", temp_root / "missing"),
            )
            for name, target in root_targets:
                with self.subTest(name=name):
                    active_root = repo_root / name
                    active_root.symlink_to(target, target_is_directory=True)
                    with self.assertRaisesRegex(
                        ValueError,
                        rf"root must not be a symlink: {name}",
                    ) as raised:
                        collect_active_guidance((active_root,), repo_root)
                    self.assertNotIn(str(target), str(raised.exception))


if __name__ == "__main__":
    unittest.main()
