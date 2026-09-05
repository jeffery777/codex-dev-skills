# Astra routing and qualification — Issue #215

This document records the approved candidate design and outstanding measurement.
It does not claim a published release or a model quality/cost improvement.

Main-agent defaults, installed child-profile locations and escalation guidance
are covered in [main-agent and subagent settings](main-agent-and-subagent-settings.md).
The optional main-agent preset is separate from candidate qualification below.

## Contract

The canonical registry retains Luna-low mechanical, Terra-low exploration,
Terra-medium everyday, Terra-high senior, Sol-medium advanced, Sol-high
independent deep/security review, and Sol-xhigh exceptional research baselines.
Three separate Astra candidates target advanced/medium, deep/high and
security/high. Their tiers describe qualification targets, not measured parity.

Class owns work and sandbox; tier owns minimum capability. Risk hard triggers
remain non-compensatory. The deterministic role in a v2 route input remains the
baseline role; callers do not replace it with a candidate role. Candidate
selection runs after classification and canonical registry validation.

Current external runtime facts may include the following **illustrative shape**.
The placeholders are not usable evidence; no production qualification is supplied
by this repository:

```json
{
  "enabled_candidates": {
    "loop_v2a_astra_advanced_worker": {
      "profile_sha256": "<exact SHA-256 of qualified TOML>",
      "quality_evidence": "<operator-verified real-model comparison reference>"
    }
  },
  "model_surface": {
    "runtime": "desktop",
    "source": "<active public callable or authoritative CLI/API surface>",
    "observed_on": "2026-09-05"
  }
}
```

These augment the existing availability, effort and parent-sandbox facts. The
caller must verify the reference's class/tier, model/effort, profile digest,
representative cases and outcome before enabling it. The router validates the
shape and digest binding; it does not dereference the reference or grade quality.
Dates provide provenance and do not establish freshness: re-read the active
surface for each session. Never reuse Desktop evidence to assert CLI/API support.
Remove the entry if quality fails or becomes unverified. Do not add a lower-tier
qualification as a substitute. v1 rejects candidate opt-ins.

Absent opt-in leaves baseline selection unchanged, even if Astra is installed and
available. With qualification, model/effort support and matching installed bytes,
the candidate for the exact baseline role is selected. Otherwise the baseline
and existing sufficient-tier alternatives remain available. Unknown availability
never becomes true by default. Parent/default and sequential require current
class/tier evidence. No safe option means a human gate. A read-only parent cannot
activate an Astra workspace-write worker. The standalone preflight may report a
source adoptable; production routing additionally requires installed bytes.

The receipt binds `profile_selection` (policy, attempted candidate, qualification,
model surface, candidate state and installed status), alongside the actual
`runtime_mapping`, selected profile digest, classification and authority hashes.
Qualification is a trusted caller assertion; the receipt is coordination evidence,
not permission or completion. Coupled work still requires evidenced sequential
execution even when an eligible candidate exists.

The installer group remains explicit opt-in and now contains eleven files.
Installing sources does not enable routing. Direct native role invocation bypasses
this router; it must follow the same operator qualification policy. No personal
configuration is installed or changed by this Issue's implementation.

## Runtime evidence (2026-09-05)

| Surface | Evidence | Limits |
| --- | --- | --- |
| API documentation | https://developers.openai.com/api/docs/models/gpt-6-astra lists low, medium, high, xhigh, max | Documentation is not account access or task-quality evidence. |
| Local Desktop callable | Active public task/subagent model metadata lists Astra low through ultra | Only this observed surface; no Astra benchmark executed. |
| CLI | Standalone 0.153.4 and Desktop-bundled 0.153.3 each passed three public-help compatibility tests; public login status confirmed ChatGPT subscription auth | Actual model results and usage remain separate execution evidence. |

The official migration guidance at
https://developers.openai.com/api/docs/guides/latest-model recommends preserving
current effort before comparing alternatives. This does not establish
Astra-low >= Sol-high. `profile_preflight.py` already recognizes max and ultra;
actual support still requires the exact model/effort facts from the target runtime.

## Bounded real-model comparison

The planned matrix covers four fixed cases and three configurations per case,
subject to the session-attempt ceiling including retries and additional grading.
Compare Sol-medium,
Astra-medium and Astra-low on two advanced implementation cases; compare Sol-high,
Astra-high and Astra-medium on one deep review and one security review case.
The case definitions and acceptance criteria are in
`../evals/agent-routing/astra-benchmark.json`. No exhaustive model/effort matrix.

The user amended the execution budget on 2026-09-05 to use the existing ChatGPT
subscription: at most twelve session attempts including retries and additional
grading, with a 90-minute batch stop. Start with one case and three configurations,
executed sequentially. Stop on subscription limits and do not purchase additional
usage. The earlier 180,000-input-token, 36,000-output-token and US$20 hard ceilings
are superseded, not claimed enforceable through the subscription runtime.
Provider-internal requests/retries may not be observable and are not bounded by
the session-attempt count. Public usage is measurement only; missing fields remain
unknown. A wall timeout does not establish that remote processing has stopped.

Record success, false completion, evidence completeness, correction rounds,
wall time and actual usage/cost against immutable case/profile/source identities.
Use fixed inputs and acceptance criteria with an independent reviewer. No missed
seeded security/public-contract blocker, false completion or authority violation
is acceptable. A twelve-call pilot is screening evidence, not statistical proof
of general superiority. Qualify each class separately only after its evidence is
reviewed; leave defaults unchanged when evidence is insufficient.

**All four case types have subscription screening results; no candidate is qualified.**
The advanced cases used three configurations each; deep/security used Sol-high
and Astra-high only. The planned Astra-medium review comparisons remain unrun.
See [the pilot report](astra-subscription-pilot-2026-09-05.md) for observed results
and protocol limitations. The public
CLI supports explicit model/effort selection and documents `turn.completed.usage`
at https://learn.chatgpt.com/docs/non-interactive-mode. The existing handoff
adapter does not retain this usage and does not accept model overrides, so it
does not serve as the comparison runner. Benchmark invocations use the public
CLI directly in isolated baseline checkouts with explicit model/effort and
`--ignore-user-config --ephemeral --json`. CLI 0.153.4 changes the bundled default
to Astra when no model is explicitly configured; implicit defaults cannot serve
as a fixed comparison baseline. No personal configuration changes or API key are
required. The offline routing suite and unit fixtures prove code paths only.

## Release assessment and remaining gates

Adding optional installable roles and qualified routing changes installed behavior;
a feature candidate is warranted after verification and review. No version has
been selected or changed. `catalog.yaml` defines source/package version only;
publication requires separate annotated-tag and non-draft/non-prerelease Release
readback. Historical release notes remain unchanged.

Real-model qualification remains a separate incomplete acceptance item, even if
all offline checks pass. Before commit/PR, retain code/docs review and proportional
Security Diff Scan evidence for the final diff. A later PR requires complete
exact-head Merge Review and the selected GitHub enforcement profile. This design
does not authorize commit, push, PR creation, merge, tag or Release publication.
