# Contributing

Thanks for helping keep these Codex development workflows useful and public.

## Ground Rules

- Keep changes scoped to software development workflows.
- Mark runtime compatibility as `shared`, `cli`, `desktop`, or `plugin-dependent`.
- Prefer repository-owned policy files over runtime-local assumptions.
- Do not add credentials, private paths, local runtime files, logs, local databases, or machine-specific config.
- Do not add legacy provider-specific workflow references.
- Do not add unverified workflow packs as first-class public skills.

## Skill Changes

Every skill should include:

- frontmatter with a concise description
- a runtime compatibility line
- purpose and trigger guidance
- read-before-write expectations
- human gate and destructive action rules
- expected output
- verification or evidence expectations

## Review Expectations

Review changes as workflow contracts, not as prose only. Check whether a new rule can be followed by both Codex CLI and Codex Desktop, and whether runtime-specific behavior is clearly labeled.
