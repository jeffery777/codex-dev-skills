# Capability Routing And Integration

Read before heterogeneous profile routing or accepting a routed worker. This
procedure works independently of durable loop state. Before candidate selection,
also read `agent-qualification.md`; it does not invoke `decide` or create a ledger.

When the decision input contains V2a task characteristics and runtime profile
evidence, use the production capability classifier and route receipt. Version
1 retains the published nine-factor path. Version 2 also requires an explicit
workload kind and records a separate capability tier. Classify
ambiguity, reasoning depth, context volume, high-risk domains, write blast
radius, latency/cost sensitivity, independence, and verification burden; do not
select a capability from the task name alone. Model/profile routing never
changes permissions, scope, human gates, or completion criteria.

New V2 receipts bind `routing_policy_revision: "v2-2026-09-06"`. Production
routing always emits that revision. Historical V2 receipts without it retain
their original validation semantics; preserve their bytes and digests, and
construct new assignments from current facts. A legacy receipt is historical
evidence, not permission to request a new legacy-policy route. Unknown revisions
or mixed legacy/new fields are rejected; V1 remains unchanged.

Keep class and tier separate. Class binds sandbox and workflow scope; tier
binds the minimum model/reasoning need. Select the lowest verified same-class
profile that meets the tier. The legacy `cost_degraded` receipt field denotes
higher-tier selection, not measured token usage, expense, latency, or savings.
Never silently substitute a lower tier. Classify the required tier as exceptional
only for research/orchestration with at least three quality triggers and explicit
quality-first preference. Set V2 `task.quality_preference: quality-first` only
from the user's or applicable task instruction's explicit preference, not inferred
complexity. Exceptional profile or parent/current-session fallback is eligible
only when classification requires exceptional; preference alone cannot escalate
a lower required tier. Omission or `balanced` keeps the normal path; V1 does not accept
this field. Routine
read-only review can request the everyday tier while retaining the reviewer
class. If no qualified everyday reviewer is available, use the verified
sufficient same-class baseline; classification alone installs no new profile.
Use `senior` Terra-high for complex but bounded implementation before
escalating multi-trigger advanced work to Sol-medium. Terra-xhigh and Luna-max
remain eval-only candidates, not installed default profiles; add either only
after representative comparisons show a distinct quality/usage advantage.

Custom-agent `sandbox_mode` is a technical runtime constraint distinct from
workflow authorization. Preflight must compare it with current-session
`parent_sandbox_mode` evidence and reject or degrade any profile that would
widen the parent sandbox. A profile never authorizes writes merely because its
sandbox technically permits them.

Preflight role/profile availability before delegation. Use the lowest
sufficient same-class profile, then a parent/default mapping with explicit
class/tier evidence, then sequential current-session execution with the same
evidence.
Stop at a human gate when a security or high-risk class cannot safely degrade.
Record worker and main-agent integration receipts; worker self-report remains
coordination evidence.

The `loop_v2a_` profile namespace names the V2a heterogeneous-agent routing
contract, not the repository release or V3 improvement-program version. Do not
rename installed profiles as a cosmetic version sync; a namespace migration
requires aliases, collision handling, installer migration, and an explicit
compatibility window.

Security review stays defensive and local-first. Prefer static analysis, local
fixtures, negative tests, synthetic inputs, and minimal non-invasive
validation. When runtime policy rejects a validation path, use safer local
evidence or record the verification limit; never evade the policy, conceal
intent, or access or mutate external systems.

Materialize the `agent_route` section from
`../../../templates/orchestration/loop-decision-input.template.yaml` relative to this reference or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/loop-decision-input.template.yaml` after filesystem installation. Keep runtime facts
out of the repository document: obtain them from the active public runtime and
pass that current-session evidence separately. The registry path must resolve
to the canonical registry shipped beside the installed skill. In this source
repository, use `./scripts/project-python` with `skills/loop-engineering` as
`<skill-dir>`. After filesystem installation, use the verified consumer Python
interpreter with the installed `<skill-dir>`; the source resolver is not shipped
as a consumer dependency. The installed command shape is:

```bash
python3 <skill-dir>/scripts/loopctl.py agent-route <decision-input.yaml> \
  --runtime-facts <current-runtime-facts.json>
```

Use the emitted content-bound route receipt for assignment. Before accepting a
worker result, validate its artifact digests and compare the assignment to the
current source revision, selected profile digest, and ownership state.

Materialize `../../../templates/orchestration/agent-routing-integration.template.yaml` relative to this reference or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/agent-routing-integration.template.yaml` after filesystem installation
and run:

```bash
python3 <skill-dir>/scripts/loopctl.py agent-integrate <receipt.yaml> \
  --repo-root <current-git-root> \
  --artifact-root <worker-output-root> \
  --verification-root <main-agent-verification-root> \
  --assignment-fresh \
  [--profile-path <selected-custom-profile.toml>]
```

The command independently reads exact Git branch and HEAD, regular non-symlink
artifact and verification files with their declared SHA-256 digests, and the
selected custom profile. Omit `--profile-path`
only for a route that selected no custom profile. Do not embed those current
facts in the receipt document.
Only an `accepted` result is integration evidence, and even that result keeps
`completion_proven: false` until repository verification/review/acceptance proves
the objective's completion criteria.
