# Release Readiness

Use this guide when maintainers prepare release or PR readiness evidence for this workflow pack or for a target repository using these skills.

This guide describes readiness checks only. It does not authorize commit, push, PR creation, publication, tag creation, merge, deploy, platform comments, or review submissions.

## When To Use

Use release readiness guidance when a bounded change is close to publication and the maintainer needs Codex to organize checks and handoff evidence before a human gate:

- a release notes draft or current release notes file needs to match the intended release scope;
- a tag or version candidate needs local verification before creation;
- a PR should be checked for docs, installer, catalog, and workflow alignment;
- a branch needs merge or release readiness evidence summarized for maintainers.

## Read First

Before preparing release readiness evidence, read the durable source of truth:

- `AGENTS.md`
- `README.md`
- `docs/roadmap.md`
- `docs/release-notes-v0.1.0.md` as historical release context, or the current release notes draft for an unreleased version
- `catalog.yaml`
- `install.sh`
- relevant `skills/`, `templates/`, `workflows/`, and `policies/` files for the changed scope

Also inspect git state:

```bash
git status --short --branch
git log --oneline -10
```

## Readiness Checklist

Check these items before asking a maintainer to approve external writes:

- Scope is clear: changed files match the release or PR objective.
- Roadmap is current: completed public roadmap items are removed or updated without unrelated rewriting.
- Release notes match their role: historical release notes remain a point-in-time record, while current release notes drafts match the intended release scope.
- Installer state is aligned: `catalog.yaml`, `install.sh`, skills, templates, workflows, and README install groups agree.
- Plugin state is aligned when present: the package-local
  `plugin/codex-dev-skills/.codex-plugin/plugin.json`, the
  repo-scoped marketplace, catalog, installer version, and README agree; the
  marketplace resolves only to the narrow generated package; exact inventory,
  package parity, cache exclusion of checkout-local state, skill-relative shared-resource
  resolution, and filesystem/plugin duplicate prevention are tested.
- Runtime compatibility is labeled: shared, CLI, Desktop, and plugin-dependent behavior is not blurred.
- Human gates are explicit: commit, push, PR creation, tag, publish, merge, release, deploy, platform comments, and review submissions require exact approval.
- Review evidence exists: ordinary review primitives or formal gates were run at the stage that needs them.
- Verification is re-runnable: commands and skipped checks are listed with enough context for another maintainer.

For the v0.14.1 candidate, also require the dated 2026-08-18 runtime evidence,
focused automation/thread/plugin/installer contract tests, plugin-validator
output, and confirmation that local Codex/ChatGPT memories or Computer History
were not adopted as repository evidence or Memory M1 state. Tag and GitHub
Release creation remain blocked until the exact reviewed merge commit is known.

When a change includes the GitNexus adapter, also require evidence that:

- the GitNexus qualification evidence-bundle digest separately binds captured
  package/help/status/query observations without recording machine-local paths;
- caller-owned accepted entry, interpreter, and complete package-tree digests
  originate outside adapter self-report, are compared through descriptor-bound
  no-follow reads before executing the qualified CLI, and package drift is
  checked again at every use;
- the production runtime fingerprint separately binds exact CLI/runtime bytes,
  version, observed analyze flags, schema/capability policy, and symlink policy;
- the handshake is disabled by default and honestly reports `read_query` and
  all backend mutations unsupported;
- stale, dirty, missing, partial, unsupported, incompatible, corrupt, unknown, wrong-repo,
  unsafe-path, symlink, timeout, lock, and capability/version drift cases fail
  closed;
- fixture refresh uses only `analyze --index-only`, isolated `GITNEXUS_HOME`,
  offline environment, expected HEAD, and a pre-existing local-exclude guard;
- every refresh first acquires the deterministic fixed-OS-temp per-user lock
  for the canonical repository root before any optional instance lock; this is
  cooperative same-UID coordination, not distributed or hostile-process isolation;
- complete worktree state (including untracked and ignored paths), protected
  state, the complete local `.git` administrative tree, metadata schema, and
  indexed revision are unchanged or exactly as qualified;
- Git probes and refresh descendants ignore replacement refs and lazy fetch,
  use isolated system/global configuration, disable hooks/fsmonitor/untracked
  cache, and enforce timeout/output bounds;
- macOS arm64 live qualification and Linux portability-only evidence are labeled accurately;
- rollback keeps the V2b no-backend path usable and does not delete or rewrite
  user repository state.

When a change includes V2c-B hooks, additionally require evidence that:

- only documented bounded `SessionStart` and `PostToolUse` `Bash` input is
  consumed; transcripts and shell command strings are not parsed;
- notify-only is the default and template installation performs no activation
  or config mutation;
- changed-HEAD notification remains honest about incomplete hook/tool coverage;
- auto-on-demand reaches only the existing V2c-A controller for a clean eligible
  state with exact identity, qualification, expected HEAD, secure fresh isolated
  home, and lock evidence;
- dirty, malformed, unavailable, unsafe, incompatible, and controller-failure
  cases preserve no-memory fallback and never claim a successful refresh;
- controller failure durably installs a repository-bound machine-local circuit
  breaker and subsequent hooks do not retry until explicit operator clearance;
- hook-created machine-local homes are not committed or automatically deleted,
  and rollback only disables/removes the hook definition;
- CLI/Desktop shared behavior and POSIX-only qualification limits are labeled.

When a change includes V2d-A operational evidence, additionally require
evidence that:

- every document has the exact `loop-operational-evidence/v0` envelope and the
  four false authority/completion/write/promotion invariants;
- duplicate keys, unknown fields, unsupported versions/enums, floats, size,
  depth, count, digest, identity, sequence, ownership, and reference failures
  reject offline;
- environment fields use the finite redacted allowlist and prohibited private
  values are omitted rather than hashed;
- typed artifact locators reject absolute/private paths, URLs, traversal, and
  kind/locator conflicts without dereferencing artifacts;
- secret, private-path, and raw-log rejections use generic non-echoing output;
- positive, negative, tamper, duplicate-key, unknown-field, synthetic
  assignment-secret, standalone-token, private-path, raw-log,
  invalid-reference, duplicate-document-id, and cross-record-mismatch
  fixtures remain synthetic and deterministic;
- references to ledger, route, worker, integration, memory, verification,
  review, Git, platform, or GitNexus artifacts cannot raise authority;
- no private PoC data, improvement lineage, projection runtime, hook,
  scheduler, controller, database, graph runtime, or automatic promotion was
  added.

When a change includes V2d-B improvement lineage or projections, additionally
require evidence that:

- V2d-A remains an exact independent five-kind contract with no migration or
  extension;
- every cross-family reference resolves by contract, kind, id, and digest;
- duplicate/conflicting improvement identity, missing or stale predecessors,
  cycle attempts, source/environment mismatch, and artifact mismatch reject;
- proposer, evaluator, independent verifier, and promoter ids remain
  structurally distinct without claiming identity authentication or authority;
- human and typed graph projections are byte-deterministic, source-derived,
  bounded, and reject mismatch/injection;
- the optional Obsidian profile is declarative, dependency-free, and
  non-mutating;
- all four false-authority invariants remain exact;
- no real records/projections, private store, vault sync, graph runtime,
  controller, or automatic promotion was added.

When a change includes V3-A evidence-to-proposal, also require evidence that:

- every proposal regenerates from complete validated V2d-A/B lineage;
- score components, ties, ranks, and duplicate suppression are deterministic;
- hypotheses and patch/branch/artifact/draft-PR intents are bounded
  description-only enums;
- proposal-only and false-authority/action fields remain exact;
- the independent human/platform promotion gate remains required and pending;
- the CLI performs no apply, Git, network, platform, artifact dereference, or
  external write;
- private evidence, host/user identity, credentials, PII, paths/config, and raw
  logs remain outside public Git;
- PlugMem, Mem0, external-memory adapters, V3-B execution, and V3-C automation
  are absent.

When a change includes V3-B isolated candidate evaluation, also require
evidence that:

- every result regenerates the selected V3-A proposal from complete validated
  V2d-A/B lineage;
- baseline/candidate observations use one fixed policy, identical scenarios,
  exact public environment equivalence, and bounded duration/resources;
- timeout, resource-bound, interruption, uncertainty, invalid baseline,
  mismatch, regression, and verifier failure cannot qualify;
- manual/CI and input-permutation replay produce identical canonical results;
- memory-off is complete by default and missing, partial, stale, untrusted,
  sensitive, conflicting, unsupported, or invalid context fails closed;
- optional accepted context comes only from the existing V2b production
  decision and cannot change policy, outcome, authority, completion, or
  promotion;
- packet-only and false-authority/action fields remain exact and the independent
  human/platform gate remains required and pending;
- the CLI performs no arbitrary candidate execution, apply, Git, network,
  platform, artifact dereference, external write, approval, or promotion;
- SQLite/FTS5, Memory M1/M2, PlugMem, Mem0, providers/MCP, automatic
  recall/write, V3-C, merge, release, deploy, and activation are absent;
- V3-B target release is v0.13.0 through Issue #143; Issue #147 / PR #148 bind
  the reviewed M0/M1 baseline to v0.14.0. M2 and V3-C targets remain TBD.

When a change includes Memory M0, also require evidence that:

- V2b/V2d/V3-A/V3-B production contracts and semantics are unchanged;
- caller-owned authority, eligibility, and trusted-time admission are separate
  from adapter/database/request/receipt data; standalone resealed requests and
  backdated time fail full-chain revalidation;
- applied/replay/failed receipts bind exact scope, idempotency, fingerprints,
  pre/post state, and atomicity without proving real M1 execution;
- V2b `delete` has only a logical-delete effect and physical purge is absent;
- memory-off is complete, default, and zero backend/filesystem touch;
- wrapper `memory-on` is not a new V3-B mode and compares safety/conformance
  only, with exact verifier assignment and a receipt bound to qualification id,
  fingerprints, V3-B tuple, safety, and execution evidence;
- valid reseal and cross-scope receipt replay cases reject, and security eval
  metrics are derived from observed outcomes rather than literals;
- schema/capability drift fails closed and no automatic migration/repair path
  exists;
- public/internal-only privacy and explicit state-root placement boundaries are
  preserved without encryption/shared-host claims;
- SQLite/FTS5 import/probe/backend, schema/database creation, persistence,
  providers/MCP, PlugMem/Mem0, automatic recall/write, and V3-C are absent;
- M0 is included in v0.14.0 without becoming a backend or activation path.

When a change includes the Issue #147 Memory M1 candidate, also require
evidence that:

- released V2b/V2d/V3/M0 production modules remain unchanged and memory-off
  performs zero adapter and filesystem touch;
- the only backend entrypoint is explicit local/manual/CI use and an explicit
  approved state root disjoint from the repository is mandatory;
- a fresh isolated temporary database proves the exact FTS5 tokenizer
  behavior and binds SQLite source/build, platform, schema, and adapter
  fingerprints before state adoption;
- existing schema and metadata match exactly; missing/drifted state rejects
  with no migration, repair, purge, backup, or restore route;
- queries are structured and bounded, SQL is parameterized, extension loading
  is disabled, and raw SQL/FTS/operator/tokenizer/ordering input rejects;
- repository, principal, namespace, revision, path, state-root, authority,
  eligibility, trusted time, idempotency, and receipt recovery are bound and
  independently revalidated;
- logical state and the original applied receipt commit atomically; exact
  replay is non-mutating; lock/timeout/fault/uncertainty never claims success;
- only public/internal non-sensitive synthetic data is used and no
  encryption, shared-host confidentiality, cross-host, or efficacy claim is
  made;
- deterministic evals claim safety/conformance only; Issue #147 / PR #148 bind
  the reviewed M1 baseline to v0.14.0 without authorizing activation or an
  efficacy claim.

## Suggested Verification

Run the repository hygiene check:

```bash
./scripts/validate-repo.sh
```

For docs-only release readiness work, also run:

```bash
git diff --check
```

When the changed scope includes Python helpers or tests, record the active Python runtime before running Python checks:

```bash
./scripts/project-python --version
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
```

This repository pins Python 3.12.9 with `.python-version`.

For the GitNexus adapter scope, run at least:

```bash
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest tests.test_gitnexus_adapter
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_memory_contract tests.test_memoryctl tests.test_eval_memory_contract
./scripts/project-python scripts/eval-memory-contract.py
./scripts/project-python scripts/eval-operational-evidence.py
./scripts/project-python scripts/eval-improvement-lineage.py
./scripts/project-python scripts/eval-improvement-proposal.py
./scripts/project-python scripts/eval-candidate-evaluation.py
./scripts/project-python scripts/eval-memory-operation.py
./scripts/project-python scripts/eval-memory-qualification.py
./scripts/validate-repo.sh
git diff --check
```

Exercise executable-origin regressions as part of the adapter/loop suites:
ambient `PATH` must not select Git, GitNexus qualification must reject an
omitted executable, and an env-node GitNexus entry must reject an omitted Node
runtime. Live qualification must supply absolute machine-local CLI and, when
applicable, Node paths; record their fingerprints but never the paths.

Record any live qualification separately from fixture tests. Running the test
suite does not prove that a local GitNexus executable, Linux runtime, or existing
index was qualified.

For release-sensitive branch readiness, use the review primitive that matches risk:

```text
Use merge-review for main..HEAD.
Use merge-review-deep for release-sensitive main..HEAD.
Use merge-readiness-gate only when a formal readiness decision is required before PR handoff, merge readiness, or final human approval.
```

## Release Notes Review

When updating release notes, verify each claim against repository files:

- skill group names match `catalog.yaml` and installer behavior;
- highlighted workflows exist under `skills/`, `workflows/`, `templates/`, or `policies/`;
- safety claims match `AGENTS.md`, `docs/usage-model.md`, and `policies/human-gate-policy.md`;
- verification commands are current and runnable from the repository root;
- no private paths, credentials, local runtime state, logs, caches, or machine-specific config are included.

Do not backfill post-release maintenance changes into historical release notes such as `docs/release-notes-v0.1.0.md` unless the file is explicitly converted to cumulative or current release notes.

## Tag And Publish Gate

Codex may prepare tag or release readiness evidence, but it should stop before creating tags or publishing releases unless the maintainer explicitly authorizes the exact action.

Before tag or release publication, report:

- target branch and HEAD SHA;
- proposed tag or release name;
- release notes path and summary;
- verification commands run and results;
- review or gate evidence used;
- skipped checks and residual risk;
- whether the action is reversible or requires manual recovery.

## PR Readiness Summary

A release or PR readiness handoff should include:

- changed files and why they are in scope;
- roadmap or release note updates;
- validation and review evidence;
- unresolved questions or skipped checks;
- human gate required for commit, push, PR creation, merge, tag, release publication, platform comments, or review submissions.

Stop and ask before any external write if the target, permissions, release version, tag name, source of truth, or verification evidence is unclear.
