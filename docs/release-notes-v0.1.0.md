# Release Notes: v0.1.0

Release date: 2026-06-03

## Highlights

- Initial public release of Codex-focused software development skills and workflows.
- Shared workflows for planning, scoped implementation, documentation updates, code review, docs review, review follow-up, review gates, and merge readiness.
- Codex Desktop delivery and orchestration workflows with Desktop-only behavior clearly labeled.
- Public installer groups for shared review gates, CLI-compatible review workflows, CLI-compatible delivery workflows, and Desktop delivery workflows.
- Repository hygiene validation through `./scripts/validate-repo.sh`.

## Included Skill Groups

- `shared-review-gates`
- `codex-review-workflow`
- `codex-delivery-workflow`
- `desktop-delivery-workflow`

## Safety And Compatibility

- Review mode is read-only unless the user explicitly asks for fixes.
- Destructive actions, external writes, push, merge, and release steps require a human gate.
- Runtime compatibility labels distinguish shared, CLI-oriented, Desktop-only, and plugin-dependent behavior.
- Public hygiene checks are designed to keep private paths, credentials, local runtime state, and legacy provider references out of the repository.

## Suggested GitHub Topics

- `codex`
- `codex-cli`
- `codex-desktop`
- `ai-assisted-development`
- `code-review`
- `developer-tools`
- `open-source`

## Verification

Run:

```bash
./scripts/validate-repo.sh
git status --short --branch
git diff -- README.md docs/usage-model.md docs/roadmap.md docs/release-notes-v0.1.0.md scripts/validate-repo.sh
```

Also run a broad sensitive-string scan. It may produce policy-only hits; inspect each hit before release.
