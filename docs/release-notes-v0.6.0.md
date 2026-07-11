# Release Notes: v0.6.0

Release date: 2026-07-11

v0.6.0 publishes Loop Engineering V2a heterogeneous subagent routing as an
independently adoptable increment for Codex CLI, Codex Desktop, and supported
IDE surfaces. It adds auditable capability classification, role-based local
custom-agent profiles, runtime preflight and safe degradation, and receipts
that preserve main-agent verification and the V1 authority model.

## Highlights

- Added deterministic classification across ambiguity, reasoning and context
  depth, security/data/migration/public-contract risk, write blast radius,
  latency and token sensitivity, independence, and verification burden.
- Added replaceable fast explorer, balanced worker, deep reviewer, and security
  reviewer profiles using the documented Codex custom-agent configuration
  surface.
- Added source, registry, destination, model, reasoning, collision, and parent
  sandbox preflight without treating runtime availability as a permanent skill
  guarantee.
- Added same-class, parent/default, sequential, and stop-for-human-gate
  degradation paths that do not widen scope, permissions, external-write
  authority, completion criteria, or human gates.
- Added route, worker, verification, and integration receipts bound to exact Git
  identity, assigned scope, profile and artifact digests, and main-agent
  disposition.
- Added the opt-in `codex-agent-profiles` installer group for user-level or
  trusted project-scoped adoption with collision checks, root-isolated state,
  backups, update refusal, and rollback behavior.
- Added a production-backed routing eval matrix covering Desktop, CLI, IDE, no
  custom-agent surface, unavailable profiles/models, unsafe degradation, stale
  or conflicting receipts, worker failure, and false-completion resistance.

## Installation And Update

Update an existing v0.5.0 shared workflow installation:

```bash
./install.sh diff codex-delivery-workflow
./install.sh update codex-delivery-workflow
python3 -m pip install -r ~/.codex/skills/loop-engineering/requirements.txt
```

Install the V2a custom-agent profiles only after reviewing the target runtime
and profile mappings:

```bash
./install.sh install codex-agent-profiles
```

For a trusted project-scoped installation, set the documented
`CODEX_CUSTOM_AGENTS_DIR` and `CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES`
variables. The profile group remains opt-in and is excluded from `--all`.

Restart Codex or begin a new task after updating so the changed skills and
profiles are discovered. When `CODEX_DEV_SKILLS_TARGET=agents` is used, replace
`~/.codex/skills` with `~/.agents/skills` in the dependency command.

## Runtime And Authority Boundaries

Capability classes and routing semantics are shared. Concrete model IDs,
reasoning effort, and custom-agent availability remain runtime-owned mappings
that must pass current-host preflight. Current Codex documentation supports
custom agents under `~/.codex/agents/` and trusted project `.codex/agents/`, but
CLI, Desktop, and IDE availability may still differ by host and account.

Agent selection never grants mutation, external-write, scope, human-gate, or
completion authority. Worker reports are coordination evidence only. The main
agent must independently inspect repository state, Git identity, artifacts,
verification, review, and accepted platform state.

If custom-agent routing is unavailable, V1 shared/sequential execution remains
usable. Unsafe high-risk degradation stops at a human gate instead of silently
using a lower capability or wider-permission agent.

## Verification

Run from the repository root:

```bash
python3 --version
python3 -m pip install -r requirements.txt
bash -n install.sh
bash -n scripts/validate-repo.sh
python3 scripts/validate-agent-profiles.py
python3 scripts/eval-agent-routing.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
./install.sh list
./install.sh status
CODEX_DEV_SKILLS_TARGET=agents ./install.sh list
./scripts/validate-repo.sh
git diff --check
```

The V2a implementation was accepted before release preparation with:

- 464 full unit tests passing;
- 109 loop-contract, 32 profile/installer, and 31 routing/eval focused checks
  passing through repository validation;
- 17/17 routing eval cases passing with zero false-completion cases;
- no unresolved MUST-FIX, SHOULD-FIX, or NIT review findings;
- a finalized 17/17 Codex Security diff scan with zero reportable findings;
- a clean independent deep merge review and merge-readiness gate.

Release preparation must rerun current repository verification and formal
release gates against the exact v0.6.0 candidate.

## Compatibility And Rollback

Existing planning, implementation, documentation, review, gate, continuation,
Desktop, and Loop Engineering V1 sequential workflows remain independently
usable. Existing v0.5.0 installations should use installer `diff` before
`update`; modified destinations are refused unless the documented force and
backup path is intentionally selected.

For profile rollback, review installer diff, uninstall the same profile group
from the same selected root, or restore an adjacent `.toml.bak` after review.
Removing V2a profiles leaves V1 shared/sequential semantics available.

This release does not add V2b external memory, V2c memory backends, private
Desktop integration, a daemon, sidecar, scheduler, or provider-specific
orchestration service.
