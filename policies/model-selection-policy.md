# Model Selection Policy

This repository does not hardcode provider-specific workflow assumptions.

Select model capability and reasoning effort by measured task need:

- repository scanning, summarization, and other read-heavy worker packets: favor
  a fast, efficient model profile;
- bounded implementation, routine review, and documentation: use a balanced
  coding and reasoning profile;
- orchestration, ambiguous multi-step work, deep review, security, migrations,
  or cross-module contracts: use a frontier reasoning profile when evals show a
  material quality gain;
- independent grading or final review: use a fresh context and, when practical,
  a separate reviewer profile from the implementer.

When migrating model families, preserve the current reasoning setting as the
baseline and compare it with at least one lower-cost setting on representative
workflow cases. Measure task success, false completion, route selection,
evidence completeness, latency, and token or cost use. Do not assume that the
highest available reasoning effort is the best default.

Model selection changes execution quality and cost; it does not change source
of truth, permissions, human gates, or completion rules.

## Main Agent And Escalation

For demanding project delivery, the optional main-agent recommendation is
Astra-high; it is separate from child-profile qualification and is not a global
product default. The repository provides a two-key example, not an installer
write into personal configuration. Select child profiles explicitly so small
tasks do not unintentionally inherit that main-agent setting.

Reassess task factors after a reasonable correction still fails the same core
check, unexplained root causes, or conflicting authoritative evidence. Use
higher reasoning for cross-system causality, interacting trust boundaries and
major architectural tradeoffs. Environment, data and permission failures are
not reasoning-effort triggers. Reclassification must retain class/tier minima,
fixed-profile digest binding, sandbox and authority. This guidance does not
implement automatic effort changes or add every model/effort combination to
the registry. See `docs/main-agent-and-subagent-settings.md` for locations,
supported profile defaults and the explicit-override boundary.

## V2a Capability Classification

Classify capability need from evidence about the work, not from its task name
alone. Record ambiguity, reasoning depth, code or context volume,
security/data/migration/public-contract risk, write blast radius, latency
sensitivity, cost or token sensitivity, independence or parallelizability, and
verification burden. Security, data, migration, public-contract, and broad-write
risks are non-compensatory: speed or cost preferences cannot average them down.

The minimum reusable capability classes are `fast-read-explorer`,
`balanced-worker`, `deep-reviewer`, and `security-reviewer`. The production
route must explain which factors selected the class and preserve the requested
scope, mutation authority, external-write authority, human gates, and
completion criteria unchanged.

Route contract version 2 keeps those workflow classes stable and adds a
separate ordered capability tier: `mechanical`, `efficient`, `everyday`,
`senior`, `advanced`, `deep`, and `exceptional`. The class owns sandbox and allowed work;
the tier owns the minimum model/reasoning requirement. Use an explicit workload
kind instead of inferring mechanical, exploration, implementation, review,
security-review, or research/orchestration work from a task title.

Select the lowest verified profile in the required class whose tier meets or
exceeds the requirement. A higher tier is a recorded cost-degraded fallback;
a lower tier cannot silently satisfy a higher-tier route. Reserve
`exceptional` for explicit quality-first research or orchestration with
multiple documented triggers. Use Terra-high `senior` for complex bounded work
that exceeds the routine Terra-medium profile, and retain Sol-medium
`advanced` for multi-trigger advanced work. Terra-xhigh and Luna-max are
eval-first candidates, not defaults: compare them against the adjacent
published profiles on representative quality, correction, latency, and usage
evidence before adding a permanent route. Do not build a complete
model-by-effort profile matrix.

## Runtime Mapping And Fallback

Custom-agent roles and concrete model/reasoning mappings are runtime profiles,
not shared workflow truth. Preflight the custom-agent surface, profile validity,
model mapping, reasoning setting, sandbox expectation, and collisions before
claiming the profile is usable. Require current parent-sandbox evidence for any
profile that is not intrinsically read-only, and reject a mapping that would
widen that sandbox. This technical check is separate from workflow write
authorization. Degrade in this order:

1. the lowest-cost available profile in the same class whose tier is sufficient;
2. the parent or default model when current facts prove the class and tier;
3. sequential execution when current facts prove the class and tier;
4. a human gate when high-risk work cannot degrade safely.

Unknown availability is not completion evidence and a recoverable mismatch does
not permanently fail the objective.

The parent owns routine qualification and runtime-input preparation. For V2
candidate routing, the shared workflow automatically loads an explicitly
approved user-level qualification store when current facts omit
`enabled_candidates`; it does not ask the user to repeat JSON or CLI options.
Match the actual task to reviewed scope before assigning its scope identifier.
Require matching runtime, current profile/evidence bytes and approval that is enabled and either
explicitly has no fixed deadline or has not expired;
never synthesize a quality claim from availability or a task label. Saved
qualification does not establish current model, effort, native role or sandbox
capability. CLI and Desktop observations remain separate. An invalid or
inapplicable record leaves baseline selection and existing human gates intact.

If a requested capability is unavailable, state the fallback and its risk. Do
not encode host-private aliases or a permanently current model name into public
skills. Runtime profiles may map the capability classes above to models whose
availability has been verified in that environment.

## Qualified Astra Candidates

Preserve the eight baseline roles. Astra medium for advanced bounded work and
Astra high for deep/security review are opt-in evaluation candidates, not proven
quality equivalents. Compare the same effort against the baseline and one lower
Astra effort before qualifying each class/tier independently. Astra xhigh/high
research comparisons remain a later batch; max/ultra are not defaults.

Version 2 may select a candidate only for its canonical baseline role, after
current caller facts explicitly enable its exact profile digest and reference
operator-verified real-model quality evidence. Record the runtime interface,
public source, and observation date separately from model/effort availability.
Missing qualification, failed quality, stale profile digest, unavailable model,
unsupported effort, or missing installed bytes cannot activate the candidate.
Remove failed candidates from enabled facts; never reduce the required tier.
Candidates are excluded from implicit fallback searches and from v1 selection.
The same-class sufficient-tier baseline, evidenced parent/default, evidenced
sequential, and human-gate order remains unchanged. Model names and opt-in facts
cannot override sandbox, allowed scope, authority, or high-risk hard triggers.

An evidence reference is a trusted operator assertion, not proof that the router
has fetched, graded, or authenticated a benchmark. Offline fixtures cannot supply
production qualification. Native direct custom-role invocation is outside the
router's qualification enforcement. See `docs/astra-routing.md` for the bounded
measurement plan and explicitly unverified claims.
