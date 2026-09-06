---
name: loop-engineering
description: Run an explicitly requested durable loop, or continue an existing repo-owned loop contract, through routing, verification, review, and authorized continuation.
---

# loop-engineering

Runtime compatibility: shared

Code Mode tool orchestration: follow
`../../policies/code-mode-tool-orchestration-policy.md` relative to this skill in source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/code-mode-tool-orchestration-policy.md`
after filesystem installation.

Context continuity: follow
`../../policies/context-continuity-policy.md` relative to this skill in source
or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/context-continuity-policy.md`
after filesystem installation.

Exact-head content review: when a loop owns an existing change request or
merge-readiness decision, follow
`../../policies/exact-head-merge-review-contract.md` relative
to this skill in source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/exact-head-merge-review-contract.md`
after filesystem installation.

## Purpose

Use this skill for an explicitly requested durable loop workflow or an existing
repo-owned loop spec, ledger, or production decision contract. Ordinary bounded
delivery uses `project-delivery`; one clear task uses `implementation-slice`.
Autonomous progress or candidate delegation alone does not activate a durable
loop. If the user explicitly names this skill, use its production decision path.

This entrypoint selects existing workflows, integrates evidence, and preserves
loop authority. It does not replace planning, implementation, review, delivery,
continuation, subagents, or runtime adapters.

## Read Only The Triggered Reference

Load a reference before the matching action; do not preload the whole table.
Paths below are relative to this skill and ship in source/plugin/install copies.

| Trigger | Required reference |
| --- | --- |
| Existing ledger, protected history, any event write, or durable templates | `references/loop-state-and-authorization.md` |
| Heterogeneous profile routing or routed-worker acceptance | `references/agent-routing.md` |
| Candidate delegation, also callable directly from delivery/orchestrator | `references/agent-qualification.md` |
| Security scan continuation, recovery, or reporting | `references/security-scan-recovery.md` |
| Context-health threshold, context drift, or fresh rollover | `references/context-continuity.md` |
| Optional GitNexus hook/controller or index identity | `references/gitnexus-runtime.md` |
| Explicit V2b/V2d/V3-A/V3-B evidence, memory contract, or local pilot use | `references/optional-evidence-memory.md`, then its matching contract reference |

`memory-off` is the default complete path, with zero backend/filesystem touch.
Do not import or touch memory adapters just to route an ordinary task. Optional
evidence, projections, qualification, and memory remain advisory; none can
activate, promote, authorize, satisfy a gate, or prove completion.

## Loop Cycle And Evidence Freshness

1. Initially bootstrap repo instructions/policies, relevant specs/plans/task
   manifests, loop state/status, verification/review artifacts, and current Git
   state. Read only sources needed for the current objective and phase.
2. At each iteration, revalidate that baseline against current repository and
   worktree identity, branch/HEAD, tracked/untracked content, applicable policy,
   task/scope/ownership, phase, tool/environment, and evidence dependencies.
   Reuse inspected content only while those bindings remain valid. Re-read
   affected sources after drift; reground fully after a conflict, lost provenance,
   phase boundary introducing new requirements, or uncertain freshness. An
   unchanged SHA alone does not prove an unchanged worktree or valid evidence.
3. Treat chat, handoffs, runtime summaries, worker reports, and optional memory
   as locating/coordination context only. Validate the current ledger before
   selecting work when one exists; resolve conflicts from authoritative sources.
4. Classify the state as `single-clear-task`, `bounded-delivery-objective`,
   `review-closure-loop`, `milestone-continuation-loop`, `handoff-or-continuation`,
   `shared-subagent-delegation`, `desktop-delegation`, `human-gate`, or `complete`.
5. Run the production decision below and execute or prepare exactly its smallest
   safe routed workflow. Verify and inspect evidence before deciding again.
6. Report changed evidence, verification, uncertainty, next action, and iteration
   result. Continue while objective, permissions, risk, and verification are clear.

Reuse review evidence only when its source/content, worktree, scope, assumptions,
phase, policy and environment still match; otherwise rerun the affected review.
After two unfinished review/fix rounds by default (or another configured positive
threshold), load `references/context-continuity.md` and assess context health.
The threshold authorizes assessment only, never a runtime task mutation.

### Exact-Head Change-Request Closure

When a change request exists, the loop may not classify the objective as merge-ready or
complete from pre-commit code, docs, deep, or security review. Those results
are reusable input evidence only. Advance through `CHANGE_REQUEST_CREATED`,
`EXACT_HEAD_VERIFICATION_PASSED`, `EXACT_HEAD_CONTENT_REVIEW_PASSED`,
`CONTENT_READINESS_READY`, and the separate `HUMAN_MERGE_AUTHORIZED` state.

Bind content review to repository, change request when present, exact
base/head/merge-base revisions, diff identity, deterministic verification,
findings, dispositions, and code/documentation coherence. Any relevant drift
returns content review to `REVIEW_REQUIRED`; chat, worker, goal, ledger, or
provider state cannot repair that gap.

Report provider enforcement separately as `VERIFIED`, `UNVERIFIED`, `BLOCKED`,
or `NOT_CONFIGURED`. Apply GitHub App/check/receipt/ruleset requirements only
when repository policy selects the optional GitHub profile.

After a fix, select code review and Security Diff Scan scope from the affected
boundary and record why prior evidence remains applicable. Widen the rerun when
shared assumptions changed. Every changed change-request head still requires a
complete new base-to-head Merge Review. Repeat provider readback only when the
selected profile requires it.

Clean internal reviews and scans advance automatically to the next safe
read-only or already-authorized stage. Do not invent another human stop merely
because a phase ended; stop only for an actual decision, authority,
environment, permission, material-risk, destructive-action, or unauthorized
external-write boundary.

## Routing

The production decision function is the active routing authority. Before using
the table below, materialize the current decision input from
`../../templates/orchestration/loop-decision-input.template.yaml` relative to this skill or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/loop-decision-input.template.yaml` after filesystem installation and run:

Every `decide` invocation requires current-session protected-history inspection.
Use the externally re-attested digest, or literal `none` only after independently
verifying there is no protected history. Follow the ledger/authorization
reference before consuming protected state; repository output cannot authorize it.

In this source repository use `./scripts/project-python` and
`<skill-dir>=skills/loop-engineering`. After filesystem installation use the
verified consumer Python interpreter and installed skill path; the source
resolver is not an installed dependency. Installed command shape:

```bash
python3 <skill-dir>/scripts/loopctl.py decide <decision-input.yaml> --protected-history-sha256 <verified-digest-or-none>
```

Route from the returned `decision`; do not independently reinterpret the prose
table when the executable result is available. If a CLI dependency is
missing, inspect the selected interpreter and the skill-local `requirements.txt`,
resolve it within existing environment/install authority, and rerun. If runtime facts
cannot be represented without guessing, stop at a human gate rather than
bypassing the production decision contract.

For an executable V1 migration preview, run
`loopctl.py migrate-v1 <ledger> --spec <spec> --manifest <manifest> --repo-root <repo>`.
Without all bind options the preview is inspection-only; do not hand-edit
contract digests because migrated active claims must be rebound atomically too.

The phase router emits the following ordinary routes after its authority,
source/ownership, scan-recovery, completion, and interruption guards. Guards
can instead return `human-gate`, `complete`, or `task-continuation`; inspect the
returned classification, execution mode, violations, and notices as well.

| Input selector | Emitted route | Meaning |
| --- | --- | --- |
| `implementation` | `implementation-slice` | One scoped implementation packet. |
| `docs` | `docs-update` | Documentation sync from verified sources. |
| `review:routine` | `code-review` | A review request with routine risk. |
| `review:high` | `code-review-deep` | A review request with high risk. |
| `delivery` | `project-delivery` | Bounded delivery; execution mode may use disjoint subagents. |
| `continuation` | `task-continuation` | Select or prepare the next bounded packet or handoff. |

Selectors use `request.kind`; review combines `kind: review` with `request.risk`.
There is no milestone request kind. The upper-layer `milestone-continuation`
owns repeated milestone progress. Within an existing durable loop, its
`continuation` decision selects `task-continuation` for the next packet; after
selection, materialize that packet's current input and run production `decide`
again before executing it. Scheduling changes the supported continuation
execution mode, not the route or task-selection authority.

`project-orchestrator`, docs-specific review, formal gates, and runtime adapters
remain owner/phase-specific workflows used when their requirements apply; they
are not additional outputs from this phase router.

## Runtime Boundaries

Subagent delegation is shared across supported Desktop, CLI, and IDE surfaces.
Goal creation requires an explicit request and an exposed capability. Goal,
worker, scheduler, and task status remain progress projections. A new or
background Desktop task requires an explicit user request; exact runtime
mutations require current documented capability, target, and authorization.

Hooks are optional guardrails and are not complete enforcement. Safe operation
must not depend on hooks or on intercepting every equivalent tool path. When a
runtime capability is absent, use current-session sequential work, a manual
invocation, task brief, or paste-ready continuation with the same gates.

Follow `../../docs/native-runtime-capabilities.md` in source/plugin checkouts or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/docs/native-runtime-capabilities.md`
after filesystem installation. Use documented callables after call-site validation.
A repository-local helper is not a native control path and must not be imported, executed, or
recommended. Runtime adapters retain exact-action gates, including ownership
and source stop-writing before any fresh rollover.

## Human Gates

Stop before continuing, delegating, mutating, or publishing when the next step involves:

- product ambiguity, unclear requirements, or unclear Definition of Done;
- source-of-truth conflict;
- scope expansion beyond the bounded objective;
- destructive action;
- external write without exact authorization;
- commit, push, PR creation, release, deploy, merge, platform comment, review submission, label/status mutation, or other platform-side mutation without exact authorization;
- material security, privacy, data, migration, payment, deployment, auth, permission, packaging, or public-contract risk;
- insufficient verification for a high-risk change;
- unclear worker ownership, task claim, lease state, or stale in-flight work;
- unsupported Desktop runtime behavior, unpublished Desktop internals, private runtime state, UI scraping, daemon, sidecar, app-server client, or unreviewed runtime adapter path.

## Completion Rules

Do not mark the loop objective complete from intent, chat memory, a summary, or passing tests alone. Completion requires source-of-truth evidence for every explicit requirement, named artifact, DoD item, verification command, review/gate requirement, and human-gate condition.

If evidence is incomplete, weak, indirect, or contradictory, continue gathering evidence, choose the next safe task, or stop at a human gate.

## Output

Report changes since the last verified baseline; link still-current evidence
instead of repeating its contents. Include enough evidence for the next decision.

- Loop objective and current classification
- Source-of-truth files inspected
- Facts, inferences, and uncertainty
- Selected route and execution mode
- Files changed, if any
- Verification run and result
- Review or formal gate evidence, if used
- Loop iteration result: `continue`, `handoff-prepared`, `blocked-by-human-gate`, or `complete`
- Next selected task or required human decision
- Residual risk
