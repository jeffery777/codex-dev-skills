# Release Notes: v0.5.0

Release date: 2026-07-11

v0.5.0 publishes Loop Engineering V1 as an executable, evidence-driven
workflow core shared by Codex CLI and Codex Desktop. It builds on the
repo-owned ledger introduced in v0.4.0 and adds one production decision and
transition implementation, strict structured validation, deterministic evals,
and explicit native capability boundaries.

## Highlights

- Added the production loop core, structured YAML loader, and `loopctl.py`
  command surface inside the installable `loop-engineering` skill.
- Added legal transition, revision, event-hash, idempotency, protected-event,
  live-authorization, claim-owner, lease, and fencing enforcement.
- Bound ledgers to the current Git branch, HEAD, loop spec, and task manifest,
  with repository path containment and immediate pre-replace source
  revalidation.
- Added deterministic workflow evals that execute the production router and
  cover routing, human gates, false completion, recovery, capability fallback,
  claim conflicts, and CLI/Desktop semantic equivalence.
- Documented native Goal and shared subagent semantics while keeping Desktop
  task, thread, worktree, scheduling, and hook behavior in thin runtime
  adapters.
- Added resilient Codex Security scan reporting contracts that keep scan-native
  state separate from Goal and worker projections and preserve resumable work.
- Aligned public documentation, templates, examples, installer contents,
  catalog metadata, and repository validation with the executable V1 contract.

## Installation

Install the shared delivery workflow:

```bash
./install.sh install codex-delivery-workflow
python3 -m pip install -r ~/.codex/skills/loop-engineering/requirements.txt
```

Update an existing installation:

```bash
./install.sh update codex-delivery-workflow
python3 -m pip install -r ~/.codex/skills/loop-engineering/requirements.txt
```

Restart Codex or begin a new task after installation so the updated skill is
discovered.

When `CODEX_DEV_SKILLS_TARGET=agents` is used, replace
`~/.codex/skills` with `~/.agents/skills` in the dependency command.

## Authority And Runtime Boundaries

Repository files, current Git state, verification, formal review, accepted
platform state, and exact current-session authorization remain the completion
and external-action authorities. Goal status, subagent summaries, Desktop task
or thread state, scheduler runs, hooks, chat summaries, code-intelligence
indexes, and caches remain progress or coordination context.

Loop Engineering V1 does not turn the skill pack into a scheduler, daemon,
platform writer, merge bot, distributed lock service, or private Desktop
runtime adapter. The historical `desktop_runtime_*` helper chain remains
isolated compatibility evidence and is not the active native path.

## External Memory

This release does not implement an external-memory adapter or a shared
cross-host coordination store. External memory and code-intelligence systems
remain optional advisory cache or coordination context unless a target
repository separately defines and reviews a stronger authority model.

Without an atomic shared claim store, work across clones, worktrees, or hosts
must use concurrency one or stop for a coordination decision.

## Verification

Run from the repository root:

```bash
python3 --version
python3 -m pip install -r requirements.txt
bash -n install.sh
bash -n scripts/validate-repo.sh
python3 scripts/validate-loop-ledger.py
python3 scripts/eval-loop-engineering.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
./install.sh list
./install.sh status
CODEX_DEV_SKILLS_TARGET=agents ./install.sh list
./scripts/validate-repo.sh
git diff --check
```

The Loop Engineering V1 implementation was accepted with:

- 397 full unit tests passing;
- 105 focused repository-validation tests passing;
- 20/20 workflow eval cases passing;
- no unresolved MUST-FIX, SHOULD-FIX, or NIT review findings;
- a complete 14/14 Codex Security diff-scan worklist with zero reportable
  findings.

Release preparation must rerun current repository verification and formal
release gates against the exact v0.5.0 candidate.

## Compatibility

Existing focused planning, implementation, documentation, review, gate,
continuation, and Desktop skills remain independently usable. The
`codex-delivery-workflow` group remains the installation entrypoint for
`loop-engineering`; users with an existing installation should use
`./install.sh update codex-delivery-workflow`.

Loop Engineering V1 is the feature generation name. The repository remains in
the v0.x release series while external-memory, distributed coordination, and
future V2 semantics remain separate follow-up work.
