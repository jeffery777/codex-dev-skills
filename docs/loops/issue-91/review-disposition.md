# Issue 91 Review Disposition

This ledger records historical formal-review findings and the current
post-scan closure cycle. Findings are never treated as closed from chat alone;
their durable disposition and review receipts preserve the evidence.

| Finding | Severity | Disposition |
| --- | --- | --- |
| CR001 self-attested conformance | MF | Fixed with caller-owned conformance evidence and mandatory harness cases. |
| CR002 lifecycle dominance | MF | Fixed with order-independent tombstone/invalidation/supersession dominance. |
| CR003 missing path scope | MF | Fixed with record, query, repository, and provenance path containment. |
| CR004 future clock/TTL | MF | Fixed with bounded clock skew and exact verified-time-plus-TTL checks. |
| CR-SF001 bare accepted evidence | SF | Superseded by digest-bound receipt documents and control-plane allowlist. |
| CR-SF002 eval evidence overclaim | SF | Fixed with digest-bound rejection receipts and decision-specific evidence oracles. |
| CR-SF003 memory usage consistency | SF | Fixed with strict enabled/status/receipt/disposition invariants. |
| MF-DOC-01..03 | MF | Fixed: out-of-band trust inputs, fixed conformance oracle, sensitive-content checks. |
| MF-DOC-04 conformance circularity | MF | Fixed: handshake cannot self-claim trust; emitted receipt promotes only a later retrieval. |
| MF-DOC-05 JSON Schema overclaim | MF | Fixed: docs state versioned executable Python field contracts. |
| MF-DOC-06 harness classification | MF | Fixed: harness is offline production; fake adapters/fixtures are test-only. |
| MF-RR-001 conformance bootstrap/drift | MF | Fixed: receipt binds adapter version and capabilities fingerprint; drift falls back. |
| MF-RR-002 acceptance receipt reuse | MF | Fixed: receipt binds exact candidate record digest and source revision. |
| MF-RR-003 provenance revision | MF | Fixed: provenance commit equals the record repository source revision. |
| SF malformed memory dispositions | SF | Fixed: unhashable values produce a validation issue instead of an exception. |
| SF eval evidence completeness | SF | Fixed: metrics require decision-specific audit evidence; negative regression added. |
| Documentation stray character | NIT | Fixed. |
| CS91-MEMCORE-001 unverified lifecycle controller | SF | Fixed: only identity-, provenance-, revision-, scope-, conflict-, injection-, and sensitivity-validated controllers can dominate related records. |
| CS91-MEMCORE-002 conformance evidence separation | Low/P3 | Fixed: trusted source and acceptance evidence are required caller-owned API/CLI inputs and their canonical set digests are receipt-bound. |
| CS91-MEMCORE-003 record capability requirements | Low/P3 | Fixed: every record requirement is checked against the admitted handshake before adoption. |
| CS91-MEMCORE-004 deep JSON recursion | SF | Fixed: `RecursionError` becomes a deterministic contract rejection without traceback. |
| CS91-MEMCORE-005 handshake freshness | Low/P3 | Fixed: current state supplies explicit maximum handshake age; stale, future-skewed, and unknown-clock observations fall back safely. |
| CS91-ROUTING-001 structured backend status | SF | Fixed: non-string values produce a validation issue instead of set-membership `TypeError`. |
| V2B-EVAL-001 evidence and disposition coverage | SF | Fixed: receipt digest is recomputed, invariant maps and disposition authority are exact, and all dispositions influence the outcome. |
| V2B-EVAL-002 threshold fail-open | SF | Fixed: suite version, threshold inventory/value, case inventory, shape, and types fail closed. |
| C91-R01 incomplete controller eligibility | MF | Closed in targeted rereview after controller eligibility was aligned with full safe record prerequisites. |
| C91-R02 duplicate record order dependence | MF | Closed: all same-id/different-digest records reject independent of order. |
| C91-R03 malformed conformance case input | MF | Closed: non-object input yields structured contract rejection. |
| C91-R04 cross-runtime canonical number/key rules | MF | Closed: floats and non-interoperable values reject; integer/ASCII-key golden vector added. |
| C91-R05 invalid Unicode scalar | MF | Closed: lone surrogates reject without traceback. |
| Post-fix docs rollback and evidence shapes | SF | Closed in targeted docs rereview; final docs gate PASS. |
| V2B-R2-MEM-001 nested invalid Unicode scalar | SF | Fixed: every bounded string path converts invalid scalar encoding into `MemoryContractError`; CLI regression covers handshake validation. |
| V2B-R2-EVAL-001 reduced eval inventory | SF | Fixed: the runner owns and checks the exact 31-case scenario/outcome/fallback oracle before optional single-case execution. |
| CS91-INTEGRATION-001 unvalidated ledger metadata | NIT | Fixed in scope: `external_memory` is exact-field validated and its authority booleans must remain false. |
| QA-MEM-CONFORMANCE-001 freshness conformance coverage | SF | Fixed: stale, future, unknown-clock, and exact age-boundary cases are mandatory production conformance oracles. |
| QA-PACKAGING-001 catalog isolation coverage | SF | Fixed: the test parses the real `catalog.yaml` and checks every installable source plus installer inputs. |
| MF-DOC-FINAL-001 rollback wording ambiguity | MF | Closed: disabling adapter use and ignoring/quarantining receipts are separate imperative sentences; final docs rereview PASS. |
| SF-DOC-FINAL-001 ledger state combinations | SF | Closed: docs define each field and legal combination; validator and positive/negative tests enforce the same contract; final docs rereview PASS. |
| MF-MERGE-FINAL-001 lexical path aliases | MF | Fixed: root `.` is the only special case; every other path-bearing field must equal its `PurePosixPath` canonical spelling. Fresh review and scan pending. |
| Historical `memory-tests-integration.json` digests | NIT | Superseded: it records an earlier implementation snapshot and is excluded from final readiness evidence; current verification, formal reviews, and final scan artifacts own the accepted bytes. |

The first completed security diff scan reported three Low/P3 findings and five
additional in-scope corrective items. The table records their implementation
disposition; closure still requires post-fix verification, fresh formal review,
and a new scan of the updated snapshot. Earlier formal code and documentation
reviews were clean before these corrections and therefore do not satisfy the
post-fix gates.

The second completed scan finalized with zero reportable findings after policy
calibration, while preserving the five correctness/assurance dispositions
above. Because those gaps were safe and in scope, they were corrected rather
than silently dropped. Final readiness therefore requires verification, fresh
review, and a scan whose snapshot includes these last corrections.
