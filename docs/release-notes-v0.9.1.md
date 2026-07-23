# Release Notes: v0.9.1

Release date: pending

v0.9.1 is a documentation, live-adoption, and repository-guardrail alignment
patch for the V2c-B baseline shipped in v0.9.0. It does not change the
GitNexus adapter, hook runner, controller, installer, or authority model.

## Changes

- Updated README's released Loop Engineering baseline from V2b to V2c-B.
- Added a durable program record that places
  `Loop Engineering V2d: Operational Evidence Contract V0` before
  `Loop Engineering V3-A: Evidence-Driven Self-Improvement`.
- Recorded the accepted authority, data-placement, projection, graph, candidate
  promotion, and automation boundaries for that program.
- Added a bounded continuation handoff so a later Codex task can open the next
  Issue and implement V2d-A without depending on chat history.
- Disposed of the supplied deep-research draft as non-authoritative research
  input and replaced its accepted conclusions with reviewable repository
  decision records.

## Repository Guardrails

Issue #109 adds two narrow maintainer controls:

- a tracked, strictly validated `.gitnexusrc` that makes direct GitNexus
  analysis index-only by default and prevents repository instruction/provider
  file generation; and
- a pull-request template plus least-privilege metadata-only CI validation
  requiring every ready pull request to close an open same-repository Issue.

The linkage check uses trusted base-branch code and read-only permissions; it
does not check out or execute pull-request head code. The PR that introduces
the workflow has a documented bootstrap limitation because GitHub loads
`pull_request_target` workflow code from the base branch. Later pull requests
are covered after the workflow reaches the default branch.

Both controls remain non-authoritative. They do not approve changes, satisfy
review gates, authorize merge or release, or prove completion.

## Live Notify-Only Adoption

Issue #107 also adopts the shipped V2c-B project hook in machine-local
`notify-only` mode. The active hook definition and configuration remain
untracked and are reviewed through the normal Codex trust flow.

The bounded adoption exercise recorded:

- a valid `notify-only` configuration with no refresh command;
- normal project-layer trust review for one active `SessionStart` hook and one
  active `PostToolUse` hook;
- actual lifecycle invocation of both supported events;
- one fail-safe SessionStart adapter-probe deadline followed by a clean,
  silent retry consistent with a fresh index;
- confirmation that no refresh or index adoption occurred;
- explicit runtime and coverage limits.

The receipt does not contain active configuration, credentials, secret values, private
paths, transcripts, raw logs, host/user identifiers, local databases, or
unredacted machine configuration.

Hook output and GitNexus metadata remain advisory. They cannot authorize
mutation or external writes, satisfy review or human gates, approve promotion,
or prove completion.

## Next Program

The accepted dependency order is:

1. V2d-A operational-evidence core contracts and fail-closed validators;
2. V2d-B improvement lineage and projection contracts;
3. private manual/CI proof of concept;
4. V3-A evidence-to-proposal workflow;
5. isolated candidate evaluation;
6. optional resident automation only after a later architecture and human
   gate.

V2d will not add private runtime data, an Obsidian runtime authority, a
scheduler, daemon, controller service, database, graph runtime, or automatic
candidate promotion.

## Verification

The release candidate must complete:

```bash
python3 --version
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_hook
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_adapter
python3 scripts/validate-gitnexus-config.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_gitnexus_config_guard \
  tests.test_pr_issue_link
./scripts/validate-repo.sh
git diff --check
```

The final verification report and review gate will be recorded under
`docs/loops/issue-107/receipts/`.

The sanitized live adoption receipt is
[docs/loops/issue-107/receipts/live-notify-only-adoption.md](loops/issue-107/receipts/live-notify-only-adoption.md).

## Rollback

Disable or remove the untracked project hook definition to stop notify-only
checks. Do not delete derived indexes or unrelated machine-local state as an
implicit rollback.

The tracked documentation patch can be reverted independently without changing
the V2c-B runtime implementation.

## Traceability

- Alignment issue:
  <https://github.com/jeffery777/codex-dev-skills/issues/107>
- Repository guardrails:
  <https://github.com/jeffery777/codex-dev-skills/issues/109>
- Program plan:
  [docs/programs/operational-evidence/README.md](programs/operational-evidence/README.md)
