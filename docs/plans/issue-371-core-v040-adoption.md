# Issue #371 — Core v0.4.0 adoption

## Target And Ownership

Base: `cc337f328704c12f1083333d90f964dbb6e1b51e`; branch:
`codex/issue-371-core-v040`. Issue and remote branch were read back before edits.
The existing local checkout was clean, the prior #369 branch was merged, and no
open same-scope Issue/PR or active second writer was found. One implementation
owner retains source, focused tests and directly related docs. Reviews are
independent and read-only. No GitNexus query or refresh is needed for this scope.

## Risk And Design

High risk: immutable source selection, installer history, generated resources
and safety-affecting workflow contracts cross trust and distribution boundaries.
Early independent deep design/security analysis found no design change required;
it identified the existing immutable installer mapping dependency, conditional
reviewer prose, provenance allowlist and old current-pin assertions as required
integration work. The source owner independently verified Git objects, full tree
inventory/modes, tag dereference and non-draft/non-prerelease Release metadata.
Digest equality is integrity evidence, not runtime qualification or authority.

Preserve all 26 upstream files exactly, retain v0.3.0 as explicit history, and
reuse the existing offline validator and transaction. Do not add a second
neutral contract, risk-acceptance store, universal publisher or enforcement
framework. Fix conflicting Codex navigation and keep the optional PR-text
helper's actual subset. This minimizes new execution and migration behavior.

Required reviewer controls apply to every selected required route. A tested
CLI read-only route with approvals disabled and apps/plugins disabled rejected
direct patch and shell writes before mutation. This bounded evidence does not
qualify ordinary writable Desktop workers or all indirect channels. Complete
current-route qualification and actual independent content review remain
separate requirements. No environment acceptance is inferred.

## Sequence And Acceptance

1. Pin published Core commit `4c8d35ad7c8e9d6a7c47331e5bd93eea2b45c535`,
   tag object `b0d04f75fd491adb200799ba89115e762b4011d1`, all 26 files,
   LICENSE/notices and the two distinct digest algorithms. Keep older snapshots
   and historical evals unchanged; ordinary loading rejects history.
2. Align catalog, installer list, generated plugin and existing Hermes closure.
   Correct reviewer/publication adapters and add no extra writing rules.
3. Prepare 0.38.0 source/package metadata, bilingual Changelog and candidate
   record. Preserve historical release notes. Do not infer publication.
4. Run targeted integrity/negative/history/docs checks, source/plugin parity,
   applicable independent review and Security Diff Scan. Test actual installer
   upgrade/downgrade/rollback in owned temporary clones/homes only.
5. Before a real commit, present exact content and metadata for its authority
   gate. After an authorized, reviewed payload commit, add its actual immutable
   source mapping, verify all earlier mappings unchanged, and rerun affected
   source/installer/review checks. Synthetic test commits are never formal pins.
6. Prepare concrete draft PR title/body and report before any PR creation or
   update. If authorized later, complete full exact-head Merge Review, current
   hosted CI and the repository's receipt/App gates. No merge/release/install
   authorization follows from preparation or a passing check.

## Writing Assessment

Core `wf-writing` is byte-identical to v0.3.0. Existing docs-update/docs-review
already require audience, purpose, explicit actors/actions, consistent terms,
step order, technical-information preservation and bilingual equivalence.
English uses ASD-STE100 as a basis; full conformity requires complete rule,
dictionary and applicable technical-term checks. Traditional Chinese uses plain
writing adaptation and must not claim STE conformity. Prefer reader-appropriate
wording while preserving required technical terms; no new rule is needed here.

English in this record follows ASD-STE100 principles; full conformance is
unverified. This assessment does not certify an artifact or add a checker.

## Evidence And Remaining Gates

Before edits: 51 applicable baseline unit tests passed with the tracked resolver
and pinned Python/PyYAML. Post-change outcomes, failures, coverage limits and
finding dispositions must be bound to the actual candidate before readiness.
Formal immutable mapping, commit/push/PR authority and any later publication or
installed adoption remain distinct. Preserve original failed attempts and all
matching current evidence; do not erase an unresolved result with an unrelated
PASS. Grok remains deferred and unverified; another consumer's acceptance record
is outside this change.
