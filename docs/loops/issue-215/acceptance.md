# Issue #215 — acceptance and delivery assessment

Source baseline: `368a0948cc0fac7d06bb760ef20357d0e0b3e753`.
Delivery branch: `codex/issue-215-astra-routing`.
This is a local pre-commit assessment, not a PR, merge, publication or installed
runtime attestation. The Issue's subject is optional Astra support and measured
routing guidance; it does not require enabling Astra everywhere.

## Acceptance mapping

| Issue requirement | Evidence and disposition |
| --- | --- |
| Parent, worker and reviewer configuration with baseline rationale | Optional Astra-high main-agent example; eight existing baseline roles preserved; Astra-medium advanced and Astra-high deep/security profiles; `docs/main-agent-and-subagent-settings.md` and model-selection policy distinguish advice from implemented routing. |
| Runtime model/effort differences and unknown states | Public CLI/Desktop observations and API documentation are separately identified in `docs/astra-routing.md`; availability is current caller evidence, never inferred from another surface. |
| Unavailable/unsupported/unknown candidate and sufficient fallback tests | `tests/test_agent_profiles.py`, `tests/test_loopctl.py`, and 30 production-backed offline routing cases cover rejection, exact installed bytes, non-widening sandbox, sufficient alternatives and safe gates. |
| Preserve scope, sandbox, authority and completion gates | Class/tier classification is retained; qualification is a digest-bound operator assertion, not permission. Candidates cannot enter implicit fallback or v1 routes. |
| Separate fixtures from actual measurements | `astra-benchmark.json` records ten completed subscription sessions across four case types and one prelaunch failure; pilot report includes raw usage, independent verification, counterexample gaps and unrun configurations. No exact-profile qualification or universal quality/cost advantage is claimed. |
| Pinned Python and relevant checks | All verification uses `scripts/project-python` with Python 3.12.9. Final focused run: 71 tests passed; 30 routing evals passed; plugin parity: 93 generated files; offline release-state and checks-only repository validation passed. |
| Source, registry/hash, docs and generated coherence | Package synchronization verified. Independent final code/docs review covers the current working-tree scope; reused security evidence is limited to unchanged bytes as described below. |
| Release impact and candidate preparation | Optional installable profiles and selection behavior justify a future feature-release candidate. The concrete preparation plan below is complete; numeric version selection and publication are not part of this local assessment. |
| PR exact-head review and external authority | Not yet applicable: no Issue #215 PR has been created in this work. Commit, push, PR, merge and publication remain stages requiring separate authorization. |

## Verification and review evidence

The previous complete twelve-shard test run passed. Later code guards were
covered by the 71-test focused rerun; subsequent changes are documentation,
measurement records and the inactive main-agent example. This assessment does
not claim that the old full-suite run included every subsequently added test.

Security Diff Scan `ac377af6-ce08-4081-8c10-a35af21e78c7` completed with zero
reportable findings for snapshot
`codex-security-snapshot/v1:sha256:3c312c0b803cede3ea55a6f9edc4b2c6fc7e1f5d875de157597318d302e51607`.
SHA-256 comparison against that snapshot's file manifest confirms unchanged
runtime scripts, profiles, registry, installer, tests and generated code. Changed
README/policy/adoption text, benchmark results, pilot/settings documentation and
the inactive two-key example are covered by the current independent review,
not represented as part of that older scan. No credentials, personal settings
or private runtime state were copied into the repository.

Final independent review: **PASS — pre-commit content gate** after final readback
of this acceptance record. This is not exact-head Merge Review, candidate
qualification, or authorization for external writes.
Finding `I215-DOC-01` (non-blocking): the pilot's first-case headings did not
clearly distinguish its four attempts from the later cumulative eleven.
Disposition: **Fixed** by labeling the first-case protocol, observations and
verification explicitly.
Finding `I215-DOC-02` (should-fix): next-stage wording could suggest commit/PR
authorization had already been granted. Disposition: **Fixed** by explicitly
requiring separate user authorization in the table and handoff paragraph.
Both findings were independently rechecked and closed. No unresolved MUST-FIX
or SHOULD-FIX remains in this pre-commit content review.

Re-runnable local checks:

```sh
./scripts/project-python -m unittest tests.test_agent_profiles tests.test_agent_routing tests.test_eval_agent_routing tests.test_loopctl.CliTests.test_astra_candidate_selection_and_safe_degradation
./scripts/project-python scripts/eval-agent-routing.py --output /tmp/issue215-routing-eval.json
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python scripts/validate-release-state.py
./scripts/validate-repo.sh --skip-unit-tests
git diff --check
```

## Release assessment

- **Source/package:** `catalog.yaml` remains 0.23.0 and matches installer/plugin
  metadata. This identifies local source structure only.
- **Candidate preparation:** recommend including this additive opt-in feature
  in the next feature-release candidate after merge readiness. No new numeric
  version or release note is selected here.
- **Publication truth:** not claimed or required for this pre-commit stage.
  Verify annotated tag and non-draft/non-prerelease Release metadata only at a
  separately authorized publication gate.
- **Active guidance:** optional installation, unqualified candidates, explicit
  main-agent adoption and runtime-specific checks remain true before and after
  any eventual release.
- **Historical records:** existing release notes are untouched.

Candidate preparation, once a maintainer selects the target version: update
catalog and installer versions together, regenerate plugin metadata, create the
new version's release note, document eleven opt-in profiles and unchanged
baseline behavior, and rerun source/package parity plus release-sensitive
review. Do not rewrite historical notes, install personal defaults, enable
candidates, create tags or publish Releases as part of that preparation.

## Explicit follow-ups and handoff

| Follow-up | Owner / target | Reason and remaining risk | Verification / promotion trigger |
| --- | --- | --- | --- |
| Exact-profile quality qualification | Adopting operator; before adding any production `enabled_candidates` reference | Screening did not activate exact custom profile instructions; blanket parity is unproven. | Run representative class/tier comparisons with exact profile bytes and independently review evidence. Becomes blocking when automatic production opt-in is proposed. |
| Unrun Astra-medium deep/security comparisons | Evaluation owner; any future lower-effort review recommendation | Two planned configurations were omitted to remain within the amended allowance. | Separately budget representative comparisons. Becomes blocking if equivalence or qualification at that effort is claimed. |
| Main-agent preset adoption | User/project maintainer; destination configuration | Example is inactive; actual client settings and availability may differ. | Merge only intended keys and verify effective destination model/effort. Becomes blocking if the preset is claimed active. |
| Feature candidate version and preparation | Release maintainer; next candidate planning | No new numeric version or publication state is asserted. | Follow the candidate plan and release-state contract before candidate readiness is claimed. |

After separate user authorization, the next delivery stage is commit/PR
preparation, followed by complete base-to-head exact-head Merge Review after a
PR exists. Content review evidence does not authorize those writes.
No additional benchmark is required merely to
deliver this explicitly unqualified opt-in design; qualifying or enabling a
candidate remains a separate decision.
