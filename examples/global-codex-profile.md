# Global Codex Profile Example

Use this example as a starting point for a user-level `~/.codex/AGENTS.md` profile.

This is an example, not an installer-managed file. Keep local paths, secrets, tokens, private workflow details, and team-only policy out of reusable global profiles.

## Purpose

Global rules should define cross-repository defaults that are safe for Codex CLI and Codex Desktop:

- output language and communication expectations
- read-before-write behavior
- git and platform safety
- destructive action safeguards
- review-mode behavior
- runtime compatibility expectations
- where project-specific rules should live

## Example Profile

```markdown
# Codex Global Instructions

## General

- Use the maintainer's requested prose language.
- Separate facts from inference.
- Prefer low-risk inspection before asking questions.
- Read before write.
- Verify target, scope, identity, environment, and current state before mutation.
- Use the smallest action that can prove or resolve the issue.
- Mark unverified claims explicitly when evidence is incomplete.

## Implementation Baseline

Before implementation:

- Read the requested scope, repo instructions, relevant files, and current git state.
- Prefer existing repo patterns over new abstractions.
- Stop before editing if scope, behavior, public contract, data, security, deployment, or blast radius is unclear.

During implementation:

- Keep changes scoped to the objective.
- Do not overwrite unrelated user changes.
- Avoid unrelated refactors unless required to finish safely.

After implementation:

- Inspect the diff.
- Run the smallest relevant verification available.
- Report verification, skipped checks, and residual risk.

## Review Baseline

- Review mode is read-only by default.
- Lead with bugs, regressions, missing tests, policy violations, or material risk.
- Align with repo-level DoD, plans, and formal gate requirements when they exist.

## Git And Platforms

- Read local repository state before mutation.
- Prefer local git for working-tree state.
- Prefer the installed platform plugin or native control plane for PRs, issues, comments, checks, and merge metadata.
- Treat force push, history rewrite, PR comments, review submission, merge, release, deploy, and broad label or status mutation as external writes.

## Runtime Compatibility

- Prefer repo-owned files and documented commands over transient UI state.
- Label Desktop-only or CLI-only behavior explicitly.
- Do not sync Desktop runtime state, local databases, logs, sessions, caches, app state, auth files, or machine-local config into reusable profiles or public repos.

## Project-Level Overrides

Project-specific workflows, branch rules, release rules, task manifests, review artifact paths, generated views, and team policy belong in repo-level `AGENTS.md`, project docs, or installed skills/templates.
```

## Adoption Notes

- Keep the global profile short enough to apply across unrelated repositories.
- Put project-specific release, merge, and review evidence requirements in the target repo.
- If a workflow depends on Desktop thread tools, document the Desktop boundary and provide a CLI-compatible fallback.
