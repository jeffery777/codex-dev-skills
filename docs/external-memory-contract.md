# External Persistent Memory Contract

Loop Engineering V2b adds a backend-neutral safety contract for optional
external memory. It does not add an external memory backend.

## Authority Boundary

Explicit current instructions, repository policy, current repository/Git,
verification, review, protected authorization, and accepted platform state
remain authoritative. Goal, workers, threads, chat summaries, product Memories,
external adapters, indexes, knowledge graphs, caches, and coordination metadata
are context only.

External memory content is untrusted data. It cannot become a system/developer
instruction; authorize mutation, external write, merge, deploy, or destructive
action; satisfy a human gate; or prove task/objective completion. Confidence,
fresh timestamps, and adapter self-report do not raise authority.

## No-backend Default

With no backend, memory remains disabled and V1/V2a workflows operate normally.
Unavailable, timeout, partial, unsupported, incompatible, or untrusted adapters
also fall back to no memory. The workflow must not simulate an unsupported
capability or lower model/verification requirements because memory failed.

## Validate The Contract

```bash
python3 skills/loop-engineering/scripts/memoryctl.py --help
python3 skills/loop-engineering/scripts/memoryctl.py validate <document.json>
python3 skills/loop-engineering/scripts/memoryctl.py decide-retrieval <decision.json> \
  --trusted-conformance-receipts <current-session-trusted-receipts.json> \
  --trusted-source-digests <current-repository-source-digests.json>
python3 skills/loop-engineering/scripts/memoryctl.py decide-write <candidate.json> \
  --trusted-acceptance-receipt-digests <current-session-accepted-receipts.json>
python3 skills/loop-engineering/scripts/memoryctl.py conformance <transcript.json> \
  --trusted-source-digests <current-repository-source-digests.json> \
  --trusted-acceptance-receipt-digests <current-session-accepted-receipts.json>
python3 scripts/eval-memory-contract.py
```

Caller-owned evidence files have exact JSON shapes:

```json
{"<adapter-id>": {"receipt_digest": "<sha256>", "adapter_fingerprint": "<sha256>"}}
```

```json
{"<repository-relative-path>": "<sha256>"}
```

```json
{"receipt_digests": ["<sha256>"]}
```

The caller derives these values from current repository, verification, review,
and conformance evidence. They are not copied from the adapter transcript.

The exact field and lifecycle contract is installed with the skill at
`references/memory-contract-v1.md`. Input is strict, bounded JSON; duplicate
keys, unknown shared fields, unsafe paths, tampered digests, wrong identity,
stale or conflicted records, injection indicators, and sensitive candidates
fail safe.

Adapter trust is caller-bound: the handshake cannot claim trust or embed a
conformance digest. Retrieval is enabled only when current-session control-plane
input independently supplies an accepted conformance receipt digest for that
adapter plus the receipt's exact adapter-version/capability fingerprint through
the separate CLI argument. Any adapter version or capability drift requires
conformance again. Repository-artifact
provenance is likewise checked against a separate trusted source-digest map.
Write eligibility likewise requires complete accepted-evidence receipt bytes,
valid receipt digests, exact candidate-record digest and source-revision
binding, and a separate
current-session allowlist of those receipt digests.
Mandatory conformance cases and their oracle are
owned by V2b, not selected by the adapter. Record path scope, related
tombstones/invalidations from independently verified controllers, per-record
capability requirements, explicit handshake maximum age, future clock skew/TTL,
and deterministic
secret/credential/PII indicators are checked before adoption.

## Agent Memory Track

Issue #135 defines a future M0/M1/M2 roadmap without changing
`loop-memory/v1` or adding a backend.

Issue #145 owns the bounded M0-only qualification candidate. It adds separate
offline `loop-memory-operation/v0` and `loop-memory-qualification/v0`
families without changing this contract. Those families validate caller-owned
exact operation authority, authorized-request composition, atomic receipt
shapes, zero-touch memory-off, and safety/conformance-only pairing. They do not
implement or authorize M1.
The authority chain includes separately accepted trusted-time evidence and is
reconstructed when requests or receipts are consumed. Qualification includes
the verifier assignment and a strict M1 receipt bound to the exact
qualification/fingerprint/V3-B/safety/execution tuple.

Issue #147 owns the separately authorized bounded M1 SQLite/FTS5 reference
candidate. It is implemented only as additive `loop-memory-sqlite/v0`, remains
default-disabled and local/manual/CI-only, and does not alter this released
V2b contract or any V3/M0 production contract. Candidate safety/conformance
evidence does not accept, install, activate, or promote M1. Issue #147 / PR
#148 bind the reviewed default-disabled safety/conformance baseline to
**v0.14.0** without changing this V2b contract.

- **M0 Backend Readiness** defines the contract-to-runtime gap matrix,
  provider-neutral protocol, caller-owned operation authority, adapter
  execution receipt, data placement, lifecycle, retention, concurrency,
  recovery, security/privacy threat model, and V3-B memory-off/on evaluation
  design. This documentation is not M0 qualification evidence.
- **M1** began under the separate Issue #147 scope after the V3-B baseline and
  M0 evidence. Its candidate is a thin,
  deterministic, default-disabled, local/manual/CI-only SQLite/FTS5 reference
  adapter. It must behavior-probe FTS5 in an isolated temporary database and
  fail closed to no memory when the capability, SQLite/tokenizer fingerprint,
  schema, identity, provenance, transaction, or integrity evidence is missing
  or drifted. It isolates repository, principal, namespace, revision, and path
  scope; accepts only bounded structured query fields through parameterized
  SQL; disables extension loading; binds eligibility by digest; enforces
  idempotency; atomically commits state and a non-authoritative execution
  receipt; and implements only explicit lifecycle operations.
- **M2** may consider a second provider or MCP adapter only after M1
  qualification passes and a new human decision approves it.

V3-B may expose a provider-neutral optional context/evaluation seam so later
qualification can compare memory-off and memory-on under the same policy,
inputs, environment class, authority invariants, and acceptance thresholds.
Memory-off remains the default, and V3-B itself must not embed SQLite or
implement M1.

The V2b write-eligibility receipt and mutation candidate remain candidate-only.
A future executed operation additionally requires caller-owned current
authority bound to the exact operation, repository/principal/namespace,
record/target digest, idempotency key, expiry, and accepted adapter capability
fingerprint. A separate execution receipt binds that authority, the adapter and
schema fingerprint, and deterministic pre/post state. State and a successful
receipt must commit atomically; uncertainty or replay never produces a second
success. Neither artifact satisfies verification, review, completion,
promotion, merge, release, or deployment authority.

Database files, journals, locks, backups, runtime configuration, credentials,
and capability fingerprints remain machine-local and outside public Git. M1
stores no secrets, credentials, PII, private paths, raw chats/sessions/logs, or
unredacted machine configuration. Automatic recall/write, resident services,
schedulers/controllers, queues, cross-host coordination, PlugMem, and Mem0
remain excluded. See
[`docs/loops/issue-135/roadmap-spec.md`](loops/issue-135/roadmap-spec.md).

## GitNexus V2c-A Baseline

V2c-A adds a default-disabled local GitNexus driver and derived-index refresh
controller without changing the V2b authority boundary. The qualified runtime is
exactly GitNexus `1.6.9`, metadata schema `5`, and a runtime-produced driver fingerprint.
Before the CLI is executed, qualification now requires caller-owned accepted
digests for the entry, bound script interpreter, and a complete canonical
package tree under an explicit machine-local package root. Package symlinks are
accepted only when relative, lexically contained direct regular-file targets;
descriptor-bound no-follow reads bind both link and target identity. Accepted
digests must come from separately trusted package-install evidence or an
explicitly approved local measurement, never promotion of adapter self-report. The
runtime fingerprint binds those verified package bytes, CLI bytes, every qualified script-interpreter
byte identity, exact version, observed analyze flags, metadata
filenames/schema/capability policy, and separate CLI/runtime symlink policies.
GitNexus qualification requires an explicit absolute
machine-local CLI path and never falls back to ambient `PATH`; an env-node entry
also requires an explicit Node executable path. The
separate qualification evidence-bundle digest additionally binds captured
package and raw help/status/query observations. Version, bytes, flags, schema, or capability drift requires
qualification and conformance again.

GitNexus human `status` and `list` output is not a production interface. The
qualified runtime exposed JSON from a direct query command, but it also returned
volatile, degraded, and instruction-like content. This first baseline therefore
declares `read_query` unsupported. It also declares `write_upsert`, `invalidate`,
`tombstone`, and `delete` unsupported and never simulates success. Strict
metadata may describe repository identity, indexed revision, and freshness, but
cannot itself produce an adoptable V2b memory record.

Machine-local executable paths, `GITNEXUS_HOME`, registries, indexes, databases,
credentials, and raw local metadata stay in the runtime control plane. The
adapter derives identity from caller-owned Git and repository evidence, not a
display label or directory basename. Metadata is untrusted, strictly bounded,
and classified as `fresh`, `stale`, `missing`, `partial`, `unsupported`,
`incompatible`, `corrupt`, or `unknown`. Every state other than an exact clean
fresh match fails closed to no memory.

### Exact Index Identity v1

GN-FU-01 adds `gitnexus-index-identity/v1` beside, rather than inside,
GitNexus schema-5 metadata. The Codex-owned sidecar is written below the ignored
derived-index root only after a qualified refresh passes native metadata and
repository postconditions. Its canonical digest binds canonical repository and
remote, repository/worktree identity digests, checkout-root digest, primary or
linked kind, branch/detached state, HEAD, tracked/status/worktree and portable
relevant-content digests, clean/dirty classification, lifecycle context and
alias, driver/GitNexus/schema/qualification identity, exact analyze
configuration, metadata digest, indexed time, and observation time.

Normal status and hooks require the complete sidecar to match recomputed live
evidence before returning `fresh/exact-clean-content`. Metadata with no v1
sidecar is explicitly stale/advisory. Dirty tracked, untracked, mixed, detached,
ignored-content-drifted, cross-worktree, cross-branch/HEAD, tool-drifted, or
configuration-drifted evidence is never exact. Primary `main`, primary issue
branches, linked worktrees, and clean PR base/head pairs use distinct aliases.
The library-only `build_pr_review_identity()` builder emits the separately
versioned `gitnexus-pr-review-identity/v1` document. It accepts two clean,
committed snapshots from the same canonical repository and binds each role's
HEAD, branch, alias, worktree identity, relevant-content digest, and derived
index-identity digest. There is no operator, persistence, or supplied-document
adoption path: a consumer must recompute the pair from live qualified inputs
and compare `pr_review_identity_digest`. The document does not prove that
review occurred. Every identity retains false authority invariants for
authorization, review, gates, and completion.

## Safe Derived-Index Refresh

Refresh is a separate, explicit local operation. It is disabled by default,
cannot be authorized by a memory payload, and may invoke only a qualified
executable with structured argv for `analyze --index-only`. Bare `analyze`,
`setup`, skills or instruction injection, wiki generation, `@latest`, eager
reindexing, and automatic scheduling are outside this baseline.

Before execution, the controller requires the exact repository root and a
verified commit-object HEAD (not only a 40-hex ref value), a direct
worktree boundary whose `.git/info/exclude` already excludes `.gitnexus/`, an
expected HEAD, a clean tracked tree with no tracked path below `.gitnexus/` or
filesystem case/normalization alias of that root, path confinement, an isolated
unique alias and `GITNEXUS_HOME`, an offline
extension policy, a minimal environment,
timeout, and a per-root lock. It does not inherit credentials, proxy settings,
embedding endpoints, or unrelated GitNexus configuration. Descendant Git
commands ignore replacement refs, system/global configuration and lazy-fetch
helpers; receive fixed `core.fsmonitor=false`, `core.hooksPath=/dev/null`, and
`core.untrackedCache=false` overrides; and cannot prompt for credentials.
Before any worktree-reading `status` or `diff`, the adapter uses bounded
`--local` and, when enabled, `--worktree` config probes. It rejects `filter.*`,
`include.path`, `includeIf.*.path`, and `core.attributesFile` selectors from
either scope. This prevents clean or process filters and external includes from
turning the qualified snapshot into command execution; unsupported local
configuration falls back without running the refresh child. Git probes are
output- and time-bounded. For
identity and status, the exact adapter root must contain a real local
non-symlink `.git` marker; linked-worktree markers require a bounded pointer
and reciprocal administrative back-reference. An enclosing repository cannot
use `core.worktree` or a forged marker to impersonate that root. Refresh is
narrower: this baseline requires a direct `.git` directory and rejects a
linked-worktree `.git` file before the runner executes.
`GIT_NO_LAZY_FETCH=1` prevents missing promisor objects from contacting a
configured remote or remote helper during identity checks.
The repository Git TCB is selected independently of ambient `PATH` and
executable-path environment variables: production callers use the operating
system default executable search path. A trusted library caller may instead
supply an explicit absolute path directly. The helper rejects any symlink
component or non-regular Git executable before use; script wrappers are
unsupported for Git itself. A GitNexus script entry is accepted only with a
bound native interpreter: exact env-node launchers require the explicitly
configured Node executable, and any other supported absolute-shebang
interpreter is independently resolved and fingerprinted. Unsupported script
launch syntax fails closed.
Tracked-path comparison applies conservative Unicode NFC normalization and
case folding before filesystem identity checks, so an alias that is absent
from the worktree cannot bypass preflight merely because `samefile()` has no
existing object to compare.

After execution, it rechecks the executable qualification, HEAD, repository
identity, the complete worktree including untracked and ignored paths,
protected paths, the complete local `.git` administrative tree, metadata
schema, indexed revision, and derived-index location. Filesystem identity and
timestamp fields are encoded as canonical strings before digesting so valid
Mac/Linux inode ranges cannot escape the V2b safe-integer boundary. Any
uncertainty, timeout, nonzero exit, drift, or unexpected mutation
rejects the index and disables automatic capability. Evidence is preserved; the
controller never resets, restores, stashes, stages, commits, or hides changes.
Only the qualified derived index and isolated registry may change. The
machine-local refresh lock is descriptor-bound and guarded with cross-process
`flock`. A deterministic fixed-OS-temp per-user lock for the canonical
repository root is always acquired before any optional configured-directory
lock, so per-process temp selectors and alternate lock directories cannot bypass
root serialization. Its directory/file ownership and link-count checks reduce accidental
same-host interference, but a hostile same-UID local process remains outside
this single-user control-plane threat model. A second device/inode-keyed lock
serializes the isolated home across repositories. Its directory descriptor is
held for the full refresh, with identity and emptiness checked under that lock
and immediately before tool execution.

The qualified complete-snapshot envelope is deliberately bounded to 250,000
filesystem entries, directory depth 256, 512 MiB per regular file, and the
configured total refresh deadline (120 seconds by default). Exceeding an entry,
depth, file-size, or time bound is an unsupported local-repository shape for
this baseline and fails closed; the controller never proceeds with a partial
snapshot. In particular, a normal Git packfile larger than 512 MiB requires a
future separately qualified driver envelope rather than an automatic override.

The live qualification was performed on macOS arm64. Linux behavior is covered
by POSIX process/path/metadata fixtures only and is not claimed as live-tested.

The mandatory backend-neutral V2b oracle remains unchanged and is rerun as a
contract regression. GitNexus-specific tests separately prove that unsupported
query/write capabilities degrade to no memory and never simulate success.
V2c-A does not emit a trusted conformance receipt authorizing GitNexus reads or
writes; any future supported capability requires its own current qualification
and adapter-specific conformance evidence.

## V2c-B Optional Freshness Hooks

V2c-B adds an optional hook runner without changing V2b authority or the V2c-A
refresh controller. The runner consumes at most 64 KiB of strict UTF-8 JSON,
rejects duplicate or unknown fields, ignores transcripts, and accepts only
documented `SessionStart` or `PostToolUse` events for `Bash` and `apply_patch`.
Its machine-local
configuration is an absolute current-user-owned regular file outside the
repository with no group/world write permission. Repository identity,
qualification digests, executable paths, isolated-home parent, and lock path
remain control-plane input and are not committed.

Codex does not currently expose a native `post-commit` lifecycle event.
`PostToolUse` therefore rechecks the configured repository after Bash or
apply-patch tool calls but does not parse or trust `tool_input.command` or
`tool_response`. It reports HEAD/index
revision drift and suppresses ordinary uncommitted-only noise. This is a useful
signal, not complete interception: other tools, processes, clients, and
unsupported hook paths can change Git state. `SessionStart` rechecks live state
for `startup`, `resume`, `clear`, and `compact` as the compensation path.

`notify-only` is the default. `auto-on-demand` is separately configured and may
refresh only a clean `stale` revision mismatch or clean `missing` index. The
runner creates one new `0700` empty child below an approved secure
machine-local parent and passes it to `RefreshController` with exact expected
HEAD and explicit opt-in. The controller remains solely responsible for argv,
environment, locking, qualification, repository preconditions, mutation
detection, and metadata postconditions. Dirty, partial, incompatible, corrupt,
unknown, identity-conflicted, or unsafe states never reach refresh.

The configured repository root is one exact checkout. Primary-directory and
linked-worktree configs therefore produce separate worktree identity digests
and index aliases; an event from another checkout is rejected. Automatic
refresh in a linked worktree is not qualified and cannot rewrite the primary
checkout's index. A remote PR/MR merge alone is not a local lifecycle event:
the primary checkout must advance before `SessionStart` or a completed
`Bash`-matched shell/unified-exec event can refresh its clean merged HEAD.

The runner does not automatically delete hook-created isolated homes. This
preserves failure evidence and avoids an implicit cleanup authority; later
cleanup is a separate exact operator action. A controller failure atomically
persists and fsyncs a repository-bound `0600` circuit-breaker marker in the
approved parent. Later hooks refuse automatic retry until an operator inspects
the failure and explicitly clears that exact marker. Hooks disabled, absent,
untrusted, skipped, timed out, malformed, or unsupported preserve the
V1/V2a/V2b/V2c-A no-memory path. Hook output is advisory context and cannot
authorize index adoption, repository mutation, an external write, review
acceptance, gate satisfaction, or completion.

## Disable And Roll Back

Leave the GitNexus adapter disabled, or remove its machine-local opt-in and
ignore/quarantine every adapter receipt while continuing with repository-owned
state. Rollback does not require deleting an index or rewriting repository
files; do not reset, restore, or clean a repository that may contain user work.
Source rollback may revert the reviewed V2c-A change independently. V1/V2a and
the V2b no-backend path remain usable throughout.

For V2c-B, disable or remove the materialized hook definition and stop
supplying its machine-local config. Template installation is inert, so no
uninstall is required to disable hooks. Rollback does not delete the derived
index or hook-created isolated homes.
