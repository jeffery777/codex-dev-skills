# Project Agent Knowledge Policy

Use this policy when an agent discovers durable project knowledge during implementation or review.

## What To Keep

Keep only verified, reusable, non-sensitive lessons that will help future work in the same repository.

Examples:

- correct local verification command
- known generated-file workflow
- project-specific test fixture location
- documented release or migration convention

## What Not To Keep

Do not record credentials, private keys, local-only paths, local app state, runtime caches, temporary incidents, speculative root causes, or one-off debugging noise.

## Process

Workers may propose knowledge candidates. The main agent reviews them before adding anything to repo-owned docs or policy files.
