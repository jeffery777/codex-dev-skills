# Review Artifact Policy

Review artifacts are evidence, not source-of-truth replacements.

## Locations

Use repo policy when it names an artifact root. Otherwise, `.work/review/` is the default convention.

## Current And Historical Artifacts

- Current pointers may summarize the latest status.
- Historical artifacts should remain available while they are referenced by open work.
- Cleanup must run dry-run first.

## Cleanup Classes

- SAFE_TO_DELETE: obsolete, unreferenced, and superseded.
- KEEP: current, referenced, unresolved, or required by policy.
- NEEDS_EXPLICIT_OVERRIDE: ambiguous or high-value evidence that requires exact user confirmation.
