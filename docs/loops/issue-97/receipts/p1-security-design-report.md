# P1 Defensive Security Design Report

Status: complete (read-only coordination evidence; main-agent verification required).

Route: `loop_v2a_security_reviewer`, tier `deep`, intended mapping
`gpt-5.6-sol` with high reasoning; runtime used same-tier parent/default
fallback (`degraded: true`, `cost_degraded: false`).

## MUST Controls

- Bind qualification to exact executable resolution/symlink policy, entrypoint
  and package bytes, version bytes, observed flags, metadata filename/schema/
  capabilities, and driver semantics. Same version alone is insufficient.
- Current qualified metadata is primary `gitnexus.json`, schema `5`, with legacy
  fallback only when primary is provably absent. Present corrupt primary or
  conflicting primary/legacy state fails closed. Schema `1` is incompatible.
- Declare `read_query` and every write/upsert/invalidate/tombstone/delete
  capability unsupported for this baseline. Human status/query output is not a
  stable production contract.
- Derive canonical Git root/HEAD/branch/remote and stable repository id from
  caller-owned evidence. Reject path-prefix tricks, unsafe symlinks, credential/
  local remotes, metadata identity mismatch, detached/unsupported state, and
  any Git/stat/read uncertainty.
- Snapshot complete porcelain/index/diff/tracked content and protected paths;
  dirty state is stale even when metadata `lastCommit` equals HEAD.
- Use fixed freshness precedence and reason codes for `missing`, `partial`,
  `corrupt`, `incompatible`, `unsupported`, `unknown`, `stale`, and `fresh`.
  Only exact clean identity/runtime/index evidence may be fresh.
- Refresh defaults disabled and requires caller control-plane opt-in bound to
  repository, expected HEAD, request/idempotency, and fingerprint. Memory,
  Goal, worker, or handshake data cannot authorize it.
- Execute exact structured argv with only `analyze --index-only` and bounded
  qualified options. No shell, force, skills, duplicate-name, setup, wiki,
  `@latest`, embeddings, PDG, or network-capable configuration.
- Build an isolated environment with explicit `GITNEXUS_HOME`, offline
  `GITNEXUS_LBUG_EXTENSION_INSTALL=never`, bounded temp/home, and no inherited
  proxy, credential, embedding, loader, npm, Node, or Git override variables.
- Require/preflight safe Git local-exclude state when analyze would otherwise
  write `.git/info/exclude`; compare exclude/config/HEAD before and after and do
  not modify them.
- Hold a controller lock outside the derived index, enforce timeout/process
  cleanup and bounded output, revalidate executable/root/HEAD/snapshot after
  the run, and compare complete tracked/protected and allowed side effects.
- Any nonzero/timeout/signal, identity/head drift, unsafe metadata, unexpected
  path or tracked/local-Git mutation rejects/quarantines the index and disables
  automatic capability. Preserve evidence; never restore/reset/stash/stage.
- Bind only bounded enums/counts/digests/redacted reasons into receipts. Never
  put raw paths, metadata, stdout/stderr, source, or command-like content into a
  prompt or repository artifact.

## Mandatory Negative Coverage

Executable missing/type/permission/symlink/parent/loop/swap/version/flag/schema/
runtime drift; remote normalization and wrong identity; root/subdir/prefix/path
escape; every dirty state; missing/partial/corrupt/conflicting metadata;
incremental dirty flag; unsafe file-hash paths/digests; timeout/lock/head race;
tracked/protected mutation even with exit zero; local exclude/config/HEAD
mutation; wrong registry home/alias; unsupported query/writes; V2b trust/fresh/
replay/principal/namespace/scope/provenance/injection/sensitivity/lifecycle and
no-backend cases.

## Residual Risk

Same-user executable replacement and concurrent edits cannot be eliminated
completely with path checks and a cooperative controller lock. GitNexus 1.6.9
does not provide a cryptographic graph-database-to-metadata binding. These
limits require exact postconditions, caller-owned digests, no-memory fallback,
and requalification after drift.
