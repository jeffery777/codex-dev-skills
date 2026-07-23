# Issue #107 Verification Report

Date: 2026-07-23

## Candidate Scope

The candidate contains README/roadmap/release-note alignment, Issue #107
planning records, the Operational Evidence program handoff, one sanitized live
adoption receipt, and an ignore rule for the active machine-local hook file.
It does not include the active hook configuration or the pre-existing local
`AGENTS.md` modification.

## Results

| Check | Result |
| --- | --- |
| V2c-B hook unit tests | Pass |
| V2c-A adapter unit tests | Pass |
| Repository validation in a clean Git-backed candidate copy | Pass |
| `git diff --check` | Pass |
| Candidate private-path/user/key-pattern scan | Pass; no hits |
| Active hook ignore rule | Pass; `.codex/hooks.json` is ignored |
| Active hook tracked-file check | Pass; no tracked result |
| Live configuration validation | Pass; valid `notify-only`, no refresh command |
| Live Codex lifecycle observation | Pass with the bounded limitation recorded in the adoption receipt |

## Workspace-Only Validation Limitation

Running `./scripts/validate-repo.sh` directly in the active working tree stops
at the provider-term check because the pre-existing local `AGENTS.md`
modification contains provider-specific GitNexus skill paths. Issue #107 does
not own that modification and does not stage, overwrite, or normalize it.

To isolate the candidate without mutating the user's working tree, the
repository was cloned locally at the current HEAD into an ephemeral directory,
the Issue #107 candidate files were overlaid while retaining the HEAD version
of `AGENTS.md`, and the repository validator was run there. All validator
stages passed, including:

- public-repository term and privacy hygiene;
- catalog and installer consistency;
- version consistency and skill metadata;
- loop-ledger and loop-contract validation;
- loop-engineering evaluation;
- custom-agent profile tests;
- agent-routing evaluation;
- external-memory contract tests and evaluation.

This isolation proves the Issue #107 candidate passes the repository checks;
it does not claim that the unrelated active-worktree `AGENTS.md` change is
valid or publication-ready.

## Residual Coverage

- The live hook exercise covers Codex CLI 0.144.6 on one macOS arm64
  environment.
- Codex CLI 0.145.0, Desktop hook execution, Linux, Windows,
  `auto-on-demand`, and changed-HEAD advisory behavior were not tested.
- No Operational Evidence V0 schema, validator, private PoC, controller,
  database, graph runtime, scheduler, or automatic promotion was implemented.
