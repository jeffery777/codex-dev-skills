# Issue 223: Verification And Review

Prepared on 2026-09-06 against base
`43e50dd4280c580276f5bd2383c056bd47931e0d` on
`codex/issue-223-workflow-efficiency`. This is implementation evidence, not an
exact-head PR verdict or publication assertion.

## Verification

The repository resolver selected Python 3.12.9 with PyYAML 6.0.3. The complete
local shard run passed all 952 tests across 66 modules and 12 shards:

| Shard | Tests |
| --- | ---: |
| exact-head-merge | 78 |
| gitnexus | 138 |
| installer-agent-profiles | 60 |
| installer-runtime | 49 |
| loop-context | 100 |
| loop-control | 87 |
| memory-m0 | 67 |
| memory-m1-and-evaluation | 104 |
| native-runtime | 92 |
| operational-improvement | 87 |
| plugin-packaging | 14 |
| repository-policy | 76 |

The complete run preceded the 0.24.0 preparation and new release records.
After the release fixture fix below, all 104 tests in the affected Memory
shard and 24 release-state/package tests passed. The complete offline validator
with `--skip-unit-tests` also passed, including every eval. Hosted CI must test
the exact proposed PR head before merge. Structural checks,
all offline evals, the shard inventory, source/plugin parity (113 generated
files), and `git diff --check` passed on the implementation. Routing evals
passed 36/36 cases. Final release/PR checks bind their own head and results.

Installed-resource tests prove explicit-only alias metadata survives both
package forms and operation references resolve from a temporary installation.
CLI examples run from an empty target directory with a verified interpreter,
without relying on this repository's `scripts/project-python`. These checks
use help/example paths and do not claim live runtime capability.

Re-run:

```bash
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/test-shards.py run-all
./scripts/project-python scripts/validate-release-state.py
./scripts/project-python scripts/sync-plugin-package.py
git diff --check
```

## Independent Review And Dispositions

Independent routing, workflow/documentation and security reviewers inspected
their complete assigned scopes. All reported findings were closed and
rechecked against source; passing tests alone were not treated as closure.

| Finding | Disposition and evidence |
| --- | --- |
| RTR-MF-001: changed V2 semantics rejected old receipts | Fixed: revision-bound current receipts, private historical validator and frozen original-builder fixtures preserve historical digests and dispositions. |
| RTR-MF-002: quality preference could escalate an ordinary fallback | Fixed: every exceptional fallback additionally requires an exceptional classified task requirement. |
| LE-01: documented routes diverged from production | Fixed: the table matches all six production routes; milestone continuation remains an upper-layer owner and re-enters decision after packet selection. |
| LE-02: incomplete protected-action reference | Fixed: the reference includes all six production protected actions; a contract test compares the actual constant. |
| DOC-01: active docs retained broad durable-loop triggers | Fixed: README and workflow guidance distinguish ordinary delivery from explicitly selected or repository-required durable loops. |
| DOC-02: complete-list sidebar reorder implied a second approval | Fixed: exact scoped existing authorization is retained; changed membership or scope returns to a gate. |

Routing re-review passed 167 focused tests and 36 routing eval cases.
Workflow re-review passed eight focused checks and confirmed package parity
after the final source edits. A transient generated plugin bytecode cache was
removed from the package inventory before the final parity check; no runtime
state is included in the source/package change.

Forward scenarios covered a small bug fix, ordinary multi-file delivery,
milestone continuation, an installed read-only CLI example and an authorized
sidebar rename. The milestone and installed examples have local execution
evidence; task selection and sidebar behavior are source-based walkthroughs,
not live UI or model qualification.

Independent discovery for Security Diff Scan
`8632de75-004a-4514-891e-c555c6caaddb` found zero plausible candidates across
its 14 canonical source items. It used independent
architecture and source discovery, supporting boundary inspection, 60 focused
tests and byte-level mirror comparisons. The immutable working-tree snapshot
digest is
`codex-security-snapshot/v1:sha256:059aa0a65eafff51611d25b24ae0257f5e6fcbf963b2d28153f397fe2a31716c`.
Finalized artifact readback nevertheless reports `coverage.completeness=partial`
and retains two earlier in-progress deferred entries. Preserve that immutable
record and do not treat its completed workflow status as full coverage. This
limitation was found by release review (RC-MF-001).

Supplemental scan `37afb187-1154-4564-a935-abad24105204` covers the expanded
release patch. Its sealed readback confirms `status=completed`,
`coverage.completeness=complete`, `deferred=[]` and zero findings across all
18 canonical source items. All original 14 source hashes match the independent
review; the supplement reattested their controls and reviewed the new version
metadata and Memory eval fix. It also passed 13 Memory pilot tests, installer
shell syntax, version parity and 113-file package parity. RC-MF-001 is resolved
by this separate complete evidence and accurate disclosure of the original
partial record; the original scan is not overwritten or promoted to complete
coverage.

The supplemental snapshot is
`codex-security-snapshot/v1:sha256:2e33a005d5fb07c6a77afc76aba4cbc1c31dbb78b373cc11ec94ee5bbb3bdd74`.
Finalization detected a Git index-state change during review: files were staged
without changing their source bytes. Coverage remains bound to the original
snapshot; later evidence-only document edits receive release integration review.

Release preparation also exposed a pre-existing hardcoded 0.23.0 positive
fixture in the Memory pilot eval. The fixture now uses the repository-derived
baseline version, and its negative test guarantees a different version. The
task's conflict detection, metric thresholds and suite digest are unchanged.
The original full-suite run preceded this fix; its affected shard and offline
evals are repeated and hosted CI must cover the final head.

Receipt hashes remain consistency
checks, not caller authentication. External host interpretation of invocation
metadata and live model behavior were not validated.

## Static Instruction Footprint

Measurements compare UTF-8 source bytes and lines against the stated base.

| Entry | Before bytes / lines | After bytes / lines |
| --- | ---: | ---: |
| loop-engineering | 36,812 / 604 | 13,353 / 232 |
| cli-session-handoff | 15,650 / 271 | 4,519 / 74 |
| desktop-thread-delegation | 19,391 / 319 | 4,324 / 75 |
| All 25 Skill entries | 138,803 bytes | 93,493 bytes |

The largest three entries shrink 69.1%; all entry points shrink 32.6%.
Conditional references preserve detailed contracts, so this is not a package
size, tokenizer, cache-hit, latency, billing or model-quality measurement.
All eleven agent profiles and their model/effort defaults remain unchanged.
Routine review can still use its existing higher-tier read-only fallback.

The follow-up in `model-evaluation-follow-up.md` defines paired prompt usage,
cheaper-reviewer qualification and exact-profile candidate trials before any
cost claim, model default change or automatic adoption.

## Release-State Roles

- Source/package: catalog, installer and plugin manifest target 0.24.0.
- Candidate preparation: the new v0.24.0 note records only this Issue's scope.
- Publication truth: a GitHub annotated tag and non-draft/non-prerelease
  Release must bind the reviewed merge result; this report does not prove it.
- Active guidance: entry selection, runtime commands and cost limitations are
  aligned with implementation and remain true after publication.
- Historical records: existing release notes and original receipts remain
  point-in-time evidence; they are not rewritten into current-state claims.

The user authorized a justified release, including its necessary delivery
actions. Review receipts remain advisory and do not themselves grant that
authority. No personal configuration, paid live trial, provider-policy change
or deployment is included.
