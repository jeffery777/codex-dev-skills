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

## Runtime Mapping And Fallback

Custom-agent roles and concrete model/reasoning mappings are runtime profiles,
not shared workflow truth. Preflight the custom-agent surface, profile validity,
model mapping, reasoning setting, sandbox expectation, and collisions before
claiming the profile is usable. Require current parent-sandbox evidence for any
profile that is not intrinsically read-only, and reject a mapping that would
widen that sandbox. This technical check is separate from workflow write
authorization. Degrade in this order:

1. another available profile in the same capability class;
2. the parent or default model when it can satisfy the class safely;
3. sequential execution in the current session with the same workflow contract;
4. a human gate when high-risk work cannot degrade safely.

Unknown availability is not completion evidence and a recoverable mismatch does
not permanently fail the objective.

If a requested capability is unavailable, state the fallback and its risk. Do
not encode host-private aliases or a permanently current model name into public
skills. Runtime profiles may map the capability classes above to models whose
availability has been verified in that environment.
