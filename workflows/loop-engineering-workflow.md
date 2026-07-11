# Loop Engineering Workflow

Use this workflow when a maintainer wants Codex to keep a bounded objective moving through repeated plan, implementation, verification, review, continuation, and gate decisions.

The user-facing skill is `loop-engineering`. It is an entrypoint and router, not a new execution engine. The loop works by repeatedly choosing the smallest existing workflow that can advance the current state.

## Loop Cycle

1. **Bootstrap**
   - Read repo instructions, policies, specs, plans, task manifests, repo-owned loop ledgers, loop specs, status docs, review evidence, verification commands, templates, and git state.
   - Treat chat summaries and handoff prompts as context only.
2. **Classify**
   - Decide whether the next state is a single task, bounded delivery objective, review closure loop, milestone continuation, handoff, Desktop delegation, human gate, or completion audit.
3. **Route**
   - Use the production loop decision contract to select the smallest existing
     skill that fits the classified state.
   - When V2a characteristics are present, select an explainable capability
     class and preflight its runtime profile without changing authority.
4. **Act**
   - Implement, update docs, review, prepare handoff, or stop according to the routed workflow.
5. **Verify**
   - Run the smallest relevant verification, inspect the diff, and check evidence against the objective and DoD.
6. **Review Or Gate**
   - Use review primitives for ordinary feedback.
   - Use formal gates only for commit readiness, PR readiness, merge readiness, or explicit repo-policy blocking decisions.
7. **Decide Next**
   - Continue the loop, prepare a handoff, stop for human decision, or mark the objective complete only when evidence proves completion.

## Route Map

| Situation | Use |
| --- | --- |
| One clear coding task | `implementation-slice` |
| Documentation sync | `docs-update` |
| Task classification or bounded review closure | `project-orchestrator` |
| Bounded objective to PR readiness | `project-delivery` |
| Repeated milestone progress across invocations | `milestone-continuation` |
| Next-task selection or handoff artifact | `task-continuation` |
| Routine code or docs feedback | `code-review`, `docs-review`, or `code-review-deep` |
| Formal readiness decision | `code-review-gate`, `docs-review-gate`, or `merge-readiness-gate` |
| Shared bounded subagent packets | `project-orchestrator` or `project-delivery` |
| Desktop user-owned task/thread/worktree handoff | `desktop-project-delivery` or `desktop-thread-delegation` |

For heterogeneous subagent work, classify the nine V2a task factors and choose
among fast exploration, balanced implementation, deep review, and
security/high-risk review. Record the selected class/role, runtime mapping,
fallback, scope/ownership, worker receipt, and main-agent disposition. If no
profile in the required class is usable, fall back to a safe parent/default
mapping, then sequential execution; stop when the risk cannot safely degrade.
The current parent sandbox is part of preflight evidence: never activate a
profile whose `sandbox_mode` would widen it. Technical sandbox capability does
not grant workflow mutation authority.
The executable contract is `loopctl.py agent-route <decision-input.yaml>
--runtime-facts <current-runtime-facts.json>` using the `agent_route` section of
the installed decision-input template. Runtime facts are current-session CLI
evidence, not repository-controlled YAML, and the route registry must be the
canonical registry shipped with the installed skill. Main-agent integration
uses `agent-integrate` with explicit repository, worker-artifact, and
verification roots plus assignment freshness; it independently reads those
files, their SHA-256 digests, and exact branch/HEAD instead of trusting a
receipt's self-attested current state.

## State Model

A loop iteration should distinguish:

- **Durable source of truth**: repo instructions, specs, task manifests, loop specs, status docs, review evidence, git state, and PR state.
- **Repo-owned loop ledger**: validated append-only events plus a reconstructable view of task status, claim and lease state, iteration evidence, next decision, and human gates.
- **Working context**: chat summaries, current thread notes, task briefs, and previous assistant summaries.
- **In-flight state**: worker or thread status, claims, leases, and heartbeat artifacts.

The loop spec and task manifest control stable definitions; validated events
control internally consistent operational transitions. Event replay does not
authenticate actor identity or external approval. Git, verification, review, and accepted
platform state control completion. Working context can help locate files but
cannot prove completion. In-flight state can guide whether to wait, inspect,
recover, or stop, but it cannot replace those authorities.

Protected acceptance, gate, revocation, and completion writes require exact
current-session action and receipt-digest authorization after external evidence
verification. Never infer live authority from the repo ledger or decision YAML.
Before routing from historical protected state or advancing its ledger,
revalidate its external receipts and pass the exact protected-history digest;
semantic replay alone is not origin authentication.

## Security Scan Continuation

When the selected workflow is a Codex Security scan, treat scan-native status,
Goal status, and worker status as separate projections. A running scan remains
resumable when Goal is blocked or a report worker returns `safety_refused`.
Use a replacement worker or current session for the first refusal. After
repeated refusals, preserve the scan and stop for explicit parent-report
fallback authorization; only then continue reporting in the parent. Do not call
a terminal scan-failure operation for worker refusal, partial artifacts, Goal
projection conflict, or turn boundaries.

When a ledger exists, each iteration should read it before selecting work and
write or prepare a ledger update after verification. If ledger state conflicts
with git state, task manifests, review evidence, or platform state, re-bootstrap
and stop at a human gate when the conflict cannot be resolved cheaply.

## Desktop And CLI Boundary

Shared workflow behavior can run in Codex CLI or Codex Desktop using repository files, shell commands, git inspection, and durable artifacts.

Native goal and bounded subagent behavior are shared across supported Codex
clients. Creating a goal must be explicit, and neither goal nor subagent state
proves repository completion.

Desktop-only behavior includes Desktop task/thread/worktree UI actions and
Desktop-managed scheduling. CLI does not provide the Scheduled management
interface. Use runtime actions only through documented capabilities and the
authorization required by the action.

When goal, subagent, scheduler, or thread capabilities are unavailable, the
fallback is a current-session sequential path, paste-ready prompt, task brief,
or continuation prompt. The fallback must preserve the same source-of-truth,
verification, review, and human-gate rules.

## Stop Conditions

Stop before proceeding when the next action would cross product ambiguity, source-of-truth conflict, scope expansion, destructive action, external write, commit, push, PR creation, release, deploy, merge, platform comment, review submission, material risk, unsupported Desktop runtime behavior, or insufficient verification for a high-risk change.
