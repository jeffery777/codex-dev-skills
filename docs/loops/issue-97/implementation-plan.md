# Issue 97 Implementation Plan

## Baseline

- Repository: `jeffery777/codex-dev-skills`
- Default branch: `main`
- Accepted start: `a75728b15f5d15ba7bf1a7e6e3a2dd934915592e`
- Working branch: `codex/v2c-gitnexus-adapter`
- GitHub issue: `#97`
- Local CLI observation: GitNexus `1.6.9`; `analyze --help` exposes
  `--index-only`, `--skip-agents-md`, `--skip-skills`, `--branch`, and `--name`.
- Current isolated worktree is not indexed. The original checkout has a stale
  1.6.9 index at commit `1e73dbe`; it is read-only qualification context.

## Overall Complexity

| Factor | Classification | Reason |
| --- | --- | --- |
| Ambiguity | high | GitNexus 1.6.9 lacks public structured status/query flags; metadata stability must be qualified rather than assumed. |
| Reasoning depth | deep | Identity, freshness, provenance, replay, prompt injection, subprocess safety, and V2b lifecycle compose. |
| Context volume | large | Core contract, CLI, adapter, fixtures, tests, evals, docs, installer/catalog hygiene, and loop evidence. |
| Security/data/public-contract risk | security/public-contract | The change consumes untrusted metadata/output and invokes an external local executable across a memory trust boundary. |
| Write blast radius | broad but repo-bounded | New production code/tests/docs/loop artifacts; runtime refresh may mutate derived local state only. |
| Latency sensitivity | low | Correctness and defensive evidence take priority. |
| Cost/token sensitivity | medium | Use the lowest sufficient tier, but never downgrade below security or verification needs. |
| Independence | bounded | Inventory, security design review, implementation, docs, and formal reviews can be disjoint; integration remains coupled. |
| Verification burden | high | Adversarial matrices, actual Mac qualification, portability fixtures, full validation, formal reviews, and security scan. |
| Workload kind | research-orchestration + implementation + security-review | Different packets require different lowest sufficient classes. |

Production outer class is security-sensitive bounded delivery. Exceptional/xhigh
is not selected: although several risk factors are high, no packet is an
explicit quality-first exceptional research objective with competing hypotheses
that cannot be satisfied by advanced/deep profiles.

## Routing And Cost Matrix

| Packet | Ownership | Ambiguity / depth / context | Risk / blast radius | Independence / verification | Lowest sufficient profile | Mapping | Fallback and CP rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 inventory | V2b surfaces, validation matrix, packaging/docs references; read-only | low / shallow / medium | routine / none | independent / low | `loop_v2a_mechanical_reader` tier mechanical | Luna, low | Mechanical extraction has low ambiguity; current collaboration callable cannot bind a model, so route receipt must record parent/default fallback and cost degradation if profile selection is unavailable. |
| P1 security design | CLI qualification, identity/freshness/provenance, subprocess/path/TOCTOU/mutation threat analysis; read-only | high / deep / large | security / none | independent / high | `loop_v2a_security_reviewer` tier deep | Sol, high | Security hard trigger forbids lower-tier downgrade; parent sequential review is the only safe fallback. |
| P2 adapter core | New production adapter/controller and focused unit tests; bounded new-file ownership | moderate / deep / large | public-contract / bounded | bounded / high | `loop_v2a_advanced_worker` tier advanced | Sol, medium | Cross-file contract implementation needs advanced capability; main agent integrates and reruns all verification. |
| P3 conformance/docs | Mandatory oracle fixtures, negative tests, docs/runtime/rollout sync | moderate / balanced / large | routine/public-contract / bounded | bounded / high | `loop_v2a_balanced_worker` or advanced if cross-contract changes arise | Terra medium / Sol medium | Start at balanced; promote rather than silently lower requirements if contract coupling appears. |
| P4 formal code/docs review | Final validated diff, read-only | high / deep / large | security/public-contract / none | independent / high | `loop_v2a_deep_reviewer` and `loop_v2a_security_reviewer` | Sol, high | Fresh independent context and no write authority. |
| P5 publication | Main-agent integration, readiness, commit/push/PR | moderate / deep / large | publication / bounded external write | coupled / high | current-session parent | active runtime | No subagent may publish; exact authorized gates and accepted platform readback are required. |

The installed profile registry and exact TOML digests are preflight inputs.
Current runtime/model facts stay outside repository artifacts. Route receipts
record selected class/tier/profile, reasoning effort, degradation, source
revision, ownership, and unchanged authority criteria.

## Task Slices

### P0 — Contract Inventory And Qualification Matrix

- Map V2b handshake, capability fingerprint, retrieval receipt, conformance,
  caller-owned evidence, and no-backend extension points.
- Capture exact GitNexus discovery/version/help/status/list/doctor facts without
  parsing human output as a production contract.
- Define structured metadata qualification and redaction rules.

### P1 — Production Adapter And Identity/Freshness

- Add a stdlib-only production module with strict schemas, bounds, canonical
  digests, executable resolution, remote normalization, Git identity, complete
  tracked-state snapshot, metadata validation, freshness classification, and
  V2b handshake/receipt construction.
- Restrict GitNexus 1.6.9 capabilities honestly; unsupported writes remain
  unsupported and query/status human text is not parsed.

### P2 — Safe Refresh Controller

- Default disabled and explicit opt-in.
- Exact argv uses only qualified executable plus `analyze --index-only` and a
  confined target root/isolated alias policy.
- Minimal allowlisted environment, timeout, per-root lock, expected HEAD,
  before/after tracked/protected state and indexed revision postcondition.
- Fail closed and preserve evidence on any tracked mutation or uncertainty.

### P3 — Conformance, Tests, Fixtures, And Documentation

- Add unit/integration/negative/portability fixtures for all Issue #97 cases.
- Extend the mandatory V2b conformance transcript without weakening its oracle.
- Keep local absolute paths/index/registry/database values out of golden files.
- Update README, roadmap, usage, external memory, Loop Engineering reference,
  runtime compatibility, and readiness guidance.

### P4 — Verification And Finding Closure

- Run focused adapter tests, V2b tests/eval, Loop/V2a regressions, Python compile,
  shell checks, installer/catalog/metadata/public-hygiene checks, full unittest,
  repository validation, and `git diff --check`.
- Run actual Mac qualification using the lowest-risk isolated fixture if an
  index build is needed. Record Linux as portability-contract evidence unless
  a real Linux runtime is available.
- Perform deep code review, formal code gate, docs review/gate, Codex Security
  diff scan, merge review, and readiness gate. Fix/review findings within two
  rounds; persist any safe out-of-scope SF/NIT disposition with owner/reason/trigger.

### P5 — Publish To Human Gate

- Revalidate branch/HEAD/diff/identity and absence of machine-local state.
- Commit and push the accepted diff, create a ready-for-review PR linked to
  Issue #97, and read back platform state.
- Stop without merge, tag, release, deploy, or global-profile modification.

## Verification Matrix

```bash
python3 --version
python3 -m unittest tests.test_gitnexus_adapter
python3 -m unittest tests.test_memory_contract tests.test_memoryctl tests.test_eval_memory_contract
python3 scripts/eval-memory-contract.py
python3 scripts/eval-loop-engineering.py
python3 scripts/eval-agent-routing.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
bash -n install.sh
bash -n scripts/validate-repo.sh
python3 scripts/validate-agent-profiles.py
./scripts/validate-repo.sh
git diff --check
```

Additional receipts must cover exact GitNexus CLI fingerprint, executable
symlink policy, stale original index, isolated fixture refresh, complete tracked
state/protected paths before and after, timeout/lock/head mismatch, wrong repo,
unsafe paths, partial/corrupt metadata, version/capability drift, and unexpected
tracked mutation.

## Rollout, Rollback, And Residual Risk

Rollout is opt-in after qualification; default/no-backend behavior is unchanged.
Disable the adapter or revert the V2c-A commit to roll back. Do not delete or
rewrite user repository files or machine-local indexes as part of rollback.

GitNexus `.gitnexus/gitnexus.json` (with a strictly checked legacy mirror) is
treated as a version-gated 1.6.9 driver input,
not a general stable interface. Any exact version, flag, schema, capability, or
fingerprint drift forces incompatible/no-memory fallback pending requalification.
Linux execution remains unverified unless a Linux runtime becomes available;
portable fixtures prove path/process contracts but are not mislabeled as live Linux evidence.
