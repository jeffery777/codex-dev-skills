# Subscription pilot — 2026-09-05

Four case types were screened on the ChatGPT subscription
using standalone CLI 0.153.4. This is screening evidence, not profile qualification
or a general model ranking. No benchmark patch was applied to the delivery tree.

## First case: runtime evidence — protocol

Three separate disposable checkouts started at
`368a0948cc0fac7d06bb760ef20357d0e0b3e753`, using an identical prompt and explicit
model/effort. Public `codex exec --ignore-user-config --ephemeral --json` retained
the workspace-write sandbox. Production registry/profile files remained unchanged.
The prompt required provenance, explicit operator qualification, digest binding,
class/tier/sandbox checks, safe baseline fallback and focused tests. Controlled
candidate fixtures were permitted. No subagents or extra model graders were used.

Four CLI attempts were made: one failed before emitting a thread/turn event due
to local runtime permissions; three subsequent sessions completed successfully
after tool approval of normal CLI runtime access. No API key, extra usage purchase,
personal configuration edit, commit, push or publication was performed.

The approved batch limits are twelve session attempts and 90 minutes. Provider
internal requests/retries are not bounded by that session count. All three completed
within the per-session 15-minute stop time. Elapsed times below are approximate,
measured from public output-file creation to final-message write, not benchmark
service-side timing.

## First case: observations

| Configuration | Approx. seconds | Input | Cached input | Output | Reasoning output |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sol medium | 330.6 | 1,367,165 | 1,282,688 | 9,163 | 2,393 |
| Astra medium | 382.1 | 856,612 | 790,528 | 9,368 | 1,506 |
| Astra low | 344.1 | 762,886 | 693,504 | 8,619 | 1,048 |

These are raw `turn.completed.usage` fields. Cache-write input was zero in all
three. Cached and reasoning fields are shown separately without adding them to
the totals or converting subscription usage to dollars. Repeated context reads,
cache state and differing tool use prevent a causal efficiency conclusion from
one sequential run.

## First case: independent verification

The delivery owner inspected the patches and ran the unmodified baseline versions
of `test_agent_profiles`, `test_agent_routing` and `test_loopctl` against each
candidate implementation: 148 tests per configuration. Tests were loaded from
the exact baseline commit with their file root pointing at the candidate checkout.
Traceback line text may therefore reflect the edited file; test names and assertions
come from the original test source.

All three rejected one legacy fixture that permits an unregistered alternative
profile. That difference is consistent with this task's canonical-registration
requirement and is not treated as a blocker.

- **Sol medium:** two original-test failures. The additional failure,
  `test_agent_route_v2_automatically_uses_installed_higher_tier`, is a regression:
  ordinary registered baseline alternatives now require experimental qualification.
  A separate malformed-input probe with `model_surface.runtime=[]` raised an
  unhandled `TypeError`. Its own 149 passing tests do not close these gaps.
- **Astra medium:** one original-test failure, the intentional legacy difference.
  Its 15 new candidate tests were independently rerun and passed. Bounded patch
  inspection found no additional blocker for this case's acceptance criteria.
- **Astra low:** one original-test failure, the same intentional difference.
  Its 11 new candidate tests were independently rerun and passed. The model did
  not run the full loopctl suite itself; the independent original-test run covers
  that gap. Bounded inspection found no additional blocker for this case.

No observed result justifies replacing the default baseline. Astra medium and low
remain candidates for further evaluation. Low effort is a comparison configuration,
not qualification of the medium-effort profile.

## Second case: fixture fidelity

The second case used three fresh checkouts at the same baseline, an identical
case-specific prompt, and the same explicit model/effort configurations. Scope
was restricted to the eval builder, suite and eval tests. A local supervisor
recorded monotonic elapsed time and enforced the original batch deadline plus a
12-minute per-session timeout; all sessions completed normally. The prompt asked
for at most ten minutes of implementation and verification.

| Configuration | Seconds | Input | Cached input | Output | Reasoning output |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sol medium | 142.55 | 306,235 | 260,096 | 5,120 | 1,439 |
| Astra medium | 176.58 | 237,477 | 192,640 | 4,450 | 355 |
| Astra low | 136.68 | 235,582 | 193,920 | 3,343 | 116 |

All three passed bounded acceptance. The delivery owner independently:

- Reran fixture and production routing tests: 46 for Sol medium, 49 for Astra
  medium, and 47 for Astra low, all passing.
- Checked twelve explicit false/null combinations for availability, sandbox,
  parent sandbox, non-widening and workflow-scope fields, plus input immutability.
  All three preserved them. The same probe failed all twelve combinations on
  the original builder.
- Verified that all 25 original case objects and thresholds were unchanged,
  and the production classifier was byte-identical to the baseline.
- Replaced only the in-memory builder with the baseline implementation. The
  resulting eval failed three new rejection cases for Sol medium and thirteen
  for each Astra configuration, confirming the negatives detect the original
  bug. Positive controls and fixed-builder evals passed (29, 39 and 39 cases).
- Inspected each three-file patch and ran `git diff --check`.

The two Astra variants covered more rejection conditions in their submitted
suites. This coverage observation and the lower observed usage in this run do
not establish a general quality, cost or latency ranking. Sol medium passed this
case despite the blockers found in its first-case patch. No model grading calls
or correction prompts were added by the delivery owner.

Cumulative usage of the execution allowance is seven attempts: six completed
sessions and one first-case prelaunch environment failure. The original 90-minute
deadline remains in force and was not reset for the second case. Five attempt
slots remain subject to that deadline; they are not a promise that the remaining
full matrix can fit. Deep/security cases and exact-profile qualification remain
outstanding. No experimental patch was integrated or candidate enabled.

## Deep and security screening

The user selected Sol-high and Astra-high for each remaining case (four more
sessions), rather than the full three-configuration review matrix. Separate
baseline checkouts received byte-identical seeded diffs within each comparison.
The public CLI used read-only sandboxing and identical case prompts that asked
for findings and counterexamples without disclosing the expected finding.
Each session had a four-minute timeout and the original batch deadline; all four
completed normally. Git diff readback matched the original seed exactly and no
untracked checkout files were added. These deliberately defective patches were
never applied to the delivery checkout.

| Case / configuration | Seconds | Input | Cached input | Output | Reasoning output |
| --- | ---: | ---: | ---: | ---: | ---: |
| Deep / Sol high | 121.41 | 509,052 | 443,904 | 3,832 | 1,207 |
| Deep / Astra high | 113.33 | 259,294 | 209,920 | 2,406 | 176 |
| Security / Sol high | 129.86 | 393,516 | 345,216 | 3,754 | 1,317 |
| Security / Astra high | 105.34 | 272,789 | 227,584 | 2,367 | 108 |

All four identified their core seeded defect and avoided claiming a host sandbox
escape. This is not a blanket pass of every qualification criterion:

- **Deep:** both found the missing `required_tier` argument at
  `agent_routing.py:583`, supplied senior-to-everyday counterexamples and identified
  downstream `execution-mode-semantic-mismatch` rejection. Astra explicitly
  noted that the existing test's name says advanced while its factors classify
  as senior. Neither final report supplied the originally requested exact
  advanced-to-everyday counterexample. The delivery owner independently reproduced
  that variant with deep reasoning, large context and high verification factors;
  this additional proof is not credited as model-produced evidence.
- **Security:** both found that `_sandbox_evidence` falsely attests non-widening
  and lets preflight report ready. Both distinguished workflow evidence from
  host enforcement and recognized downstream sandbox checks. Astra explicitly
  compared HEAD and seeded behavior with a read-only parent, available Terra
  model and supported medium effort, and tested the downstream rejection.
  The delivery owner separately reproduced `preflight.state=ready` and
  `_valid_profile(...)=False` using those actual runtime facts.

Independent baseline tests reproduced one expected failure in each seeded
checkout: 42 routing tests with one lower-tier failure, and 23 profile tests with
one sandbox-widening failure. Sol's own broader test commands encountered
read-only temporary-directory errors; its reports disclosed them and did not
claim full-suite success. The findings were assessed against the diff and
counterexamples, not just test exit codes. No unrelated blocker was identified
in the four final reports.

The batch now totals **eleven attempts: ten completed sessions and one prelaunch
environment failure**. All completed before the original deadline. One attempt
slot remains subject to that same deadline. Astra-medium deep/security comparisons
remain unrun, and custom profile developer instructions were not activated.
No default change, quality qualification, merge or publication follows from these
results. Further work should first decide whether exact-profile qualification is
needed; this small screening sample cannot establish broad superiority.

## Evidence limits

The prompt and changed-file hashes, raw usage and dispositions are recorded in
`evals/agent-routing/astra-benchmark.json`. Raw CLI outputs and patch copies were
retained in the local pilot artifact directory, not checked into this public repo.
The model and effort are bound to invocation arguments; the public terminal usage
event does not independently attest the resolved model. Custom profile developer
instructions were not activated, so this pilot cannot qualify exact installed
profile bytes. Full matrix coverage, repeated runs and final evidence review are
still required before operator opt-in. No production quality reference was created.
