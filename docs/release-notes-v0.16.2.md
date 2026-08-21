# Release Notes: v0.16.2

Status: release candidate; commit, push, pull request creation, merge,
annotated tag creation, GitHub Release, and deployment require the separately
authorized exact-state delivery flow.

v0.16.2 is a backward-compatible Codex CLI/Desktop runtime-adapter patch over
v0.16.1. It implements Issue #161 without changing shared orchestration,
Memory M0/M1, GitNexus, review, gate, completion, or release authority.

## Codex CLI 0.149 Compatibility

- Records the public `codex agents` dashboard as an interactive CLI control
  plane whose selected mutations retain exact authorization requirements.
- Adds bounded manual `codex queue` guidance for an exact canonical session
  UUID and an argv-only message boundary that prevents arbitrary text from
  being interpolated into a shell command. Queue delivery is runtime
  mutation/wakeup evidence only; it does not prove processing, verification,
  or completion.
- Keeps the private-clone executor limited to `codex exec` start, resume, and
  fork because `queue` does not provide the same isolated workspace or JSONL
  terminal-turn contract.
- Records `codex doctor --json` as redacted diagnostic evidence rather than a
  replacement for active-schema checks or a reason to reactivate historical
  Desktop wrappers.
- Confirms that removed skill-level model delegation does not affect the
  repository's explicit opt-in custom-agent profile mapping.

## Desktop Thread Sharing

- Adds `share_thread` to the Desktop adapter as an explicit privacy-sensitive
  runtime mutation for the current or another exact accessible thread.
- Requires target and audience preview from current public product context plus
  user-confirmed complete-thread review before link creation. Recent,
  truncated, or paginated agent reads are insufficient. Runtime secret-pattern
  redaction is defense in depth rather than a guarantee that no sensitive
  content remains.
- Keeps immutable snapshot creation, link revocation through ChatGPT data controls,
  thread lifecycle, and repository completion as separate states.
- Preserves the independent Desktop adapter, CLI adapter, and shared workflow
  layers; no identifier or completion authority is merged across runtimes.

## Compatibility And Rollback

Existing skills, installer groups, CLI private-clone requests, Desktop task
creation/fork/handoff behavior, agent profiles, and shared workflow authority
remain compatible. The new CLI dashboard/queue and Desktop sharing guidance is
capability-detected and falls back to existing manual/sequential paths when the
runtime does not expose it. Rollback requires only reinstalling the previously
reviewed v0.16.1 package; it does not delete sessions, share links, or runtime
state. Existing share links must be reviewed or revoked separately through the
product data controls.

## Verification And Release Gate

```bash
./scripts/project-python -m unittest tests.test_cli_session_handoff
./scripts/project-python -m unittest tests.test_native_runtime_contract_docs
./scripts/project-python -m unittest tests.test_runtime_compatibility_release_docs
./scripts/project-python scripts/sync-plugin-package.py --write
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh
git diff --check
```

Formal code and documentation review plus exact-head merge readiness must be
current and finding-free. The annotated `v0.16.2` tag and non-draft,
non-prerelease GitHub Release must bind the exact reviewed merge commit only
after separate human approval.

## Traceability

- Issue #161: <https://github.com/jeffery777/codex-dev-skills/issues/161>
- Base release: <https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.16.1>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.16.1...v0.16.2>
