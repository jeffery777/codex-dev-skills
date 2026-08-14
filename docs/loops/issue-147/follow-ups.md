# Issue #147 Deferred Follow-ups

## Purpose And Status

This ledger records risks and questions that do not block the bounded Memory
M1 safety/conformance candidate because they are outside its explicit
local/manual/CI-only, single-host, public/internal synthetic-data scope. An
entry is not accepted work, release scope, or permission to implement it.
Every entry requires a new Issue or other explicit maintainer decision before
mutation. The reviewed Memory M1 baseline is released in **v0.14.0**; every
deferred capability and stronger claim remains separately gated.

## Follow-up Ledger

| ID / priority | Deferred scope and residual risk | Why non-blocking for Issue #147 | Owner / target | Verification plan | Promotion trigger |
| --- | --- | --- | --- | --- | --- |
| M1-FU-01 / normal | Qualify additional OS, architecture, Python, SQLite build, and tokenizer tuples. Untested tuples may differ in FTS5, locking, or filesystem behavior. | M1 binds and reports one exact probed tuple and makes no portability claim. | Maintainer / separate Issue, target TBD | Run the complete synthetic suite and isolated behavior probe on each declared tuple; compare canonical qualification receipts. | Any support or release claim for a tuple not qualified by Issue #147. |
| M1-FU-02 / normal | Exercise process crash, power loss, disk-full, filesystem corruption, and recovery on selected real filesystems. Synthetic faults do not prove physical durability. | M1 claims logical atomicity and synthetic recovery conformance only. | Maintainer plus independent security reviewer / separate Issue | Define bounded disposable-host fault tests, recovery invariants, and negative evidence without retaining real records. | Any physical-durability, backup/restore, or stronger recovery claim. |
| M1-FU-03 / gated | Threat-model hostile same-UID access, shared hosts, multi-tenant databases, encryption, and confidential/restricted data. Local permissions do not provide those guarantees. | These trust models and data classes are explicitly excluded; M1 accepts public/internal non-sensitive data only. | Security owner / separate design and Issue | Select an explicit adversary and tenancy model, then review isolation, key management, placement, and deletion semantics before implementation. | Any shared-host, tenant-isolation, encryption, or confidential-data claim. |
| M1-FU-04 / gated | Observe efficacy separately from safety/conformance and decide activation or promotion. M1 does not establish that recall improves outcomes. | The v0.14.0 baseline remains default-disabled and cannot claim efficacy or activate itself. | Product/maintainer human gate / target TBD | Pre-register bounded efficacy criteria and independent observations without changing M0 authority. | Proposal to activate or promote the adapter. |
| M1-FU-05 / gated | Define physical purge/retention, provider or MCP adapters, cross-host operation, automatic recall/write, or V3-C automation. | Each item changes the data lifecycle, authority surface, or runtime topology and is excluded from M1. | Maintainer and security owner / separate roadmap Issues | Create independent contracts, threat models, destructive-action safeguards, and rollback evidence for the selected slice. | Any request for one of these capabilities. |
| GN-FU-01 / **high — next suitable maintenance window** | Define GitNexus index lifecycle and exact-evidence identity across `main`, issue branches, linked worktrees, dirty tracked files, and untracked files. HEAD-only freshness can label a dirty index "up-to-date", and current change detection can omit untracked files. | The user-authorized Issue #147 index is advisory development evidence; local static inspection, tests, and review remain authoritative for the dirty candidate. It is not a V2c-A conformance receipt. | Repository maintainer / open a dedicated Issue and `codex/<issue>-...` branch at the next suitable maintenance window; target TBD | Specify identity fields for repository, worktree, branch, HEAD, dirty state, complete working-tree content digest, timestamp, tool version, and config; add clean/dirty/untracked linked-worktree fixtures and compare base/head aliases. | Any workflow that treats a dirty-worktree index as exact evidence, refreshes it automatically, or uses it as completion authority. |

## GitNexus Development Index Evidence

For Issue #147, the user explicitly authorized a separate advisory index named
`codex-dev-skills-issue-147` for branch
`codex/147-memory-m1-sqlite-fts5`. The rebuild indexed the candidate working
tree and improved architecture/impact exploration, but the index status is
commit-based and therefore cannot by itself prove dirty or untracked content
freshness. Rebuilding produced no tracked repository artifact and granted no
completion, acceptance, release, or promotion authority.

Until GN-FU-01 is resolved, the following are provisional minimum-risk
recommendations, not accepted repository policy:

- rebuild the `main` alias from a clean, updated `main` checkout after merges;
- use a unique alias for a clean issue-branch/worktree baseline;
- treat dirty-worktree rebuilds as advisory snapshots and supplement them with
  `git status`, complete diff/untracked inspection, local call-site analysis,
  tests, and review;
- rebuild a branch alias after commit or rebase when exact committed-head
  exploration is needed;
- review pull requests from clean committed base/head identities; and
- never infer content freshness from `gitnexus status` alone when the worktree
  is dirty or contains untracked files.

The dedicated follow-up should decide whether these recommendations belong in
V2c-A contracts, repository policy, CLI guidance, or a new validation layer;
Issue #147 does not make that architectural decision.

## Current Classification

Verified for the bounded candidate: default-disabled integration, exact M0
authority reconstruction, structured bounded query, fixed schema, atomic
state-plus-receipt transaction, logical lifecycle, synthetic fault recovery,
generic privacy rejection, deterministic evaluation, and one exact local
SQLite/FTS5 qualification tuple.

Not verified and intentionally deferred: broader platform portability,
physical durability/purge, hostile shared-host or multi-tenant isolation,
encryption/confidential data, efficacy, cross-host/provider/automatic runtime
paths, and exact dirty-worktree GitNexus evidence identity.
