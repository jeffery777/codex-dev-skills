# Model Selection Policy

This repository does not hardcode provider-specific workflow assumptions.

Select model capability by task need:

- routine planning and docs: standard reasoning is usually enough
- implementation with moderate code context: use stronger code reasoning when available
- deep review, security, migrations, or cross-module contracts: use the strongest available reasoning profile

If a requested capability is unavailable, state the fallback and its risk. Do not encode private model aliases into public skills.
