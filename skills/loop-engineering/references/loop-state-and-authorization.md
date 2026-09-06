# Loop State And Protected Authorization

Read before routing from an existing ledger, validating protected history,
writing any ledger event, or preparing durable loop templates. Paths beginning
with `scripts/` below are relative to the loop-engineering skill directory.

## Repo-Owned Loop Ledger

When a target repository needs durable loop memory, use a repo-owned ledger
artifact such as `docs/loops/<objective-id>/loop-state-ledger.yaml`. The stable
objective and task definitions come from the loop spec and task manifest;
validated append-only events are the operational integrity record, and the
ledger task view is their reconstructable materialization. Event replay proves
internal consistency, not actor identity or external approval provenance.
Claim records are coordination authority only when their store provides atomic
acquisition and fencing.

Use the ledger to:

- locate the active objective and selected task;
- avoid duplicate worker or thread assignment through claim and lease fields;
- record source revision, verification evidence, review evidence, blocker
  reasons, handoff artifacts, and residual risk;
- decide whether the next result is `continue`, `handoff-prepared`,
  `blocked-by-human-gate`, or `complete`.

Do not treat external memory, worker self-reports, Desktop thread summaries,
runtime cache, or chat summaries as completion evidence unless current
repository artifacts, git state, verification, review evidence, or accepted
platform state confirm them.

### Protected Event Authorization

Treat `source_rebound`, `task_acceptance`, `task_completion`, `claim_revocation`,
`gate_satisfaction`, and `objective_completion` as protected live actions.
These are the complete `PROTECTED_EVENT_ACTIONS` set in `scripts/loop_core.py`.
Their durable event must bind
the action, actor/principal, exact task or gate scope, concrete evidence
artifact, objective identity, immutable source-revision digest, and canonical
digest of every protected payload field. Before writing the event:

1. Preview it with `loopctl.py apply-event` and inspect the returned
   `protected_action` and `authorization_receipt_sha256`.
2. Verify the approval or platform receipt against its authoritative source;
   do not infer approval from the event, ledger, task brief, or worker report.
3. Apply with `--write --authorize-action <exact-action>
   --authorization-receipt-sha256 <verified-digest>` only when the current
   session has exact authority for that action and receipt.

The live authorization arguments are current-session control-plane input. Do
not store or infer them in `loop-decision-input.yaml` or other repository data.
`replay_event` and semantic audit intentionally validate historical integrity
without authenticating origin; never use replay as the write boundary or as
completion authorization. Revalidate current external state before consuming
an accepted, satisfied, or complete ledger state for publication.

Historical protected events require the same distrust boundary. `audit`
reports `protected_history_sha256` as an integrity projection, not origin
authentication. Before `transition` consumes that state or `apply-event
--write` advances the ledger, verify every protected receipt against its
authoritative source and pass the exact digest through
`--protected-history-sha256`. Do not copy the digest blindly from repo output.
An idempotent protected replay is a no-op: it may use re-attested history but
must report `live_authorization_verified: false`.

`decide` also fails closed: every invocation must receive
`--protected-history-sha256` from current-session inspection. Pass the exact
verified audit digest, or the literal `none` only after independently verifying
that the routing state has no protected history. Required review completion is
a protected `task_completion` action. Its receipt binds the manifest-selected
review mode and concrete review artifact; a claimed worker may submit the event,
but the independent user or platform principal authorizes completion. A required
human gate is resolved only from the named, protected `gate_updated` state, never
from a task-transition payload assertion.

## Templates

Use these templates when a target repository needs durable loop artifacts:

- `../../../templates/orchestration/loop-engineering-spec.template.md` or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/loop-engineering-spec.template.md`
- `../../../templates/orchestration/loop-decision-input.template.yaml` or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/loop-decision-input.template.yaml`
- `../../../templates/orchestration/loop-event.template.yaml` or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/loop-event.template.yaml`
- `../../../templates/orchestration/loop-iteration-report.template.md` or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/loop-iteration-report.template.md`
- `../../../templates/orchestration/loop-handoff-prompt.template.md` or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/loop-handoff-prompt.template.md`
- `../../../templates/orchestration/loop-state-ledger.template.yaml` or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/loop-state-ledger.template.yaml`
- `../../../templates/orchestration/task-claim-lease.template.yaml` or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/task-claim-lease.template.yaml`
- `../../../templates/orchestration/context-continuity.template.yaml` or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/context-continuity.template.yaml`

Reuse existing project, task, and review templates whenever they are sufficient instead of creating loop-specific duplicates.
