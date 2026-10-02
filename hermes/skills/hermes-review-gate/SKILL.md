---
name: hermes-review-gate
description: Hermes read-only review and evidence-bound formal gates.
metadata:
  hermes:
    requires_toolsets: [terminal]
---

# Hermes review gate

Runtime compatibility: Hermes CLI, limited baseline. This adapter translates
review procedure, not the Codex reviewer runtime or Security plugin.

## When to Use

For ordinary read-only review, or formal commit/PR/merge readiness when requested
or required by repo policy. Declare the mode and exact scope before starting.

## Procedure

1. Inspect repository identity, branch/head, complete diff and applicable DoD.
   Stay read-only; review does not authorize fixes. For merge inspect the full
   base-to-head range, current base/head/merge-base and diff identity.
2. Read `../../policies/security-review-escalation-policy.md` and
   `../../policies/review-artifact-policy.md`. Use deep review immediately for
   installers, credential/authorization, dependency, data, external integration
   or cross-runtime public contracts. Check producer/consumer boundaries,
   negative cases, failure/recovery, concurrency and unsupported claims.
3. Require an independent reviewer with verified sufficient model/effort,
   tool permissions and data scope. Hermes `delegate_task` availability and
   isolated conversation history do not establish OS read-only enforcement or
   reviewer quality. If unavailable, obtain a separately verified independent
   reviewer or block formal readiness; author self-review cannot replace it.
4. Record risks first using `../../templates/review/code-review-report.template.md`.
   Give every MUST-FIX/SHOULD-FIX/NIT a stable ID and Fixed/Deferred/Rejected/
   Needs Human Decision disposition. Deferral needs owner, durable target,
   reason, residual risk, verification plan and promotion trigger. Missing
   disposition or unresolved MUST-FIX/Human Decision blocks formal readiness.
5. Assess required Security Diff Scan. Use a qualified available scan service
   with exact diff/source evidence. A static review is not a Codex Security
   scan. If policy requires a scan and it is unavailable, record that limitation
   and block readiness. Do not change models or conceal output to bypass a
   rejected scan. Re-review fixes proportionally; reuse unchanged evidence only
   with matching scope, bytes, assumptions, policy and environment.
6. For merge read `../../policies/exact-head-merge-review-contract.md`. Use
   `../../templates/review/merge-review-report.template.md` and the offline
   `../../scripts/validate-exact-head-merge-review.py` (Python 3.10+ standard
   library) for the actual receipt. The script validates supplied evidence;
   it is not independent review or live platform collection. Missing platform
   evidence remains unknown. Always repeat full review for a changed PR head.
7. Use the repo-selected provider profile only. For GitHub read
   `../../policies/github-control-plane-policy.md` and
   `../../policies/github-exact-head-enforcement-profile.md`. Prefer an
   available authorized connector; documented CLI fallback requires recorded
   reason and authenticated same-target identity. Strict receipt publication/
   readback precedes dedicated App verdict. Content PASS alone cannot bypass
   hosted CI, threads, ruleset/App or exact-head merge checks.
8. Read `../../policies/human-gate-policy.md` and
   `../../policies/release-state-contract.md` before the corresponding action.
   Preserve separately authorized commit/push/PR/merge/release/deploy boundaries.

## Pitfalls

Toolsets and dangerous-command matching are not full containment. A scan
summary, child receipt or successful CI is not a complete formal gate. Shared
policies may name Codex-specific adapters; use only verified Hermes equivalents
described here, otherwise mark unavailable and keep the gate blocked.

## Verification

Return Review Mode, Gate Result (PASS/BLOCKED/NEEDS HUMAN DECISION when formal),
source/diff identity, findings, every disposition, verification/evidence paths,
deep risk notes, skipped checks and required follow-up. No finding may disappear
between rounds. Report content readiness and provider enforcement separately.
