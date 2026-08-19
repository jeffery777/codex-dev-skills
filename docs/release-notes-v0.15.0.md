# Release Notes: v0.15.0

Status: release candidate; merge, tag, GitHub Release, and deployment are not
created or authorized by this document.

v0.15.0 adds lower-overhead multi-agent coordination and a cost-aware
Terra-high implementation tier over v0.14.2. It does not change workflow
authority, completion evidence, security-review triggers, or the released
Memory M0/M1 contracts.

## Agent Coordination

- Delegates by disjoint ownership, artifact boundaries, independence, and
  useful parallelism instead of assigning one worker to every discipline.
- Keeps implementation, focused tests, and directly related documentation with
  one owner by default while preserving independent code review and
  risk-triggered security review.
- Dispatches a fixed independent worker set once, continues parent-owned work,
  and then uses a supported wait-for-any or mailbox wait. Unchanged status is
  not repeatedly listed, read, or polled.
- Limits worker progress reporting to blockers that require a parent decision
  plus one final structured receipt. Completed receipts can be integrated while
  unrelated workers continue, and bounded follow-up reuses the original worker
  when its assignment remains fresh.

## Cost-Aware Routing

- Adds the opt-in `loop_v2a_senior_worker` profile using `gpt-5.6-terra` with
  high reasoning for complex but bounded implementation.
- Extends route contract version 2 with the ordered `senior` tier between
  `everyday` and `advanced`. High ambiguity, deep reasoning, or high
  verification burden selects Terra-high `senior`; at least three total
  ambiguity, reasoning, verification, or context-volume triggers retain
  Sol-medium `advanced` routing.
- Keeps Terra-xhigh and Luna-max as eval-first candidates rather than installed
  defaults. This release does not create a model-by-effort profile matrix.
- Preserves all existing `loop_v2a_` profile identities. The namespace denotes
  the V2a heterogeneous-agent routing protocol, not the repository release or
  V3 improvement-program version; a future rename requires a separately
  reviewed compatibility migration.

## Compatibility And Installation

The `codex-agent-profiles` group remains explicit opt-in and excluded from
`--all`. Existing profiles retain their names; their instruction digests change
because they now use blocker-plus-final reporting and implementation profiles
own coupled tests and directly related docs by default. Update the delivery
workflow and profiles together so the tier registry, validator, routing code,
and installed TOML files remain aligned.

```bash
./install.sh diff codex-agent-profiles
./install.sh update codex-agent-profiles --force
./scripts/project-python scripts/validate-agent-profiles.py
```

Terra-high availability remains a current-runtime preflight fact. If the exact
model or reasoning effort is unavailable, routing follows the existing
same-class higher-tier, explicitly capable parent/default, sequential, or human
gate fallback contract; it does not guess an alias or silently use a lower
tier.

## Verification And Release Gate

```bash
./scripts/project-python scripts/validate-agent-profiles.py
./scripts/project-python scripts/eval-agent-routing.py
./scripts/project-python -m unittest discover -s tests -p 'test_*.py'
./scripts/validate-repo.sh
git diff --check
```

The release candidate requires profile, routing, installer, plugin parity,
documentation, code review, and merge-readiness evidence from the exact final
head. The annotated `v0.15.0` tag and GitHub Release must bind the reviewed
merge commit after separate human approval.

## Traceability

- Issue: <https://github.com/jeffery777/codex-dev-skills/issues/153>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.14.2...v0.15.0>
