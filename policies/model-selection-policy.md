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

If a requested capability is unavailable, state the fallback and its risk. Do
not encode host-private aliases or a permanently current model name into public
skills. Runtime profiles may map the capability classes above to models whose
availability has been verified in that environment.
