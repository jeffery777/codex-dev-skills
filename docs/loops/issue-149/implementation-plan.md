# Issue #149 Implementation Plan

## Objective

Publish one bounded v0.14.1 compatibility patch that aligns the independent
Codex CLI and Codex Desktop entrypoints with the current official runtime while
preserving their shared orchestration, authority, evidence, review, and
completion layers.

Tracking issue: <https://github.com/jeffery777/codex-dev-skills/issues/149>

## Source Of Truth

- `AGENTS.md`
- `README.md`
- `policies/runtime-compatibility-policy.md`
- `docs/native-runtime-capabilities.md`
- `docs/runtime-compatibility.md`
- `docs/runtime-adapter-v2.md`
- `skills/desktop-project-delivery/SKILL.md`
- `skills/desktop-thread-delegation/SKILL.md`
- `install.sh` and `catalog.yaml`
- the dated compatibility evidence created for this patch

## Repair Slices

1. Refresh official and active-schema evidence for Desktop automations,
   thread starting state, archived-task discovery, panel display, terminal
   observation, Linux preview, imports, plugins, memories, and Computer
   History.
2. Update the Desktop adapters without moving task selection, authority,
   verification, review, or completion semantics out of the shared layer.
3. Package a narrow generated allowlist of canonical tracked skills and their
   shared resources as one skills-only universal plugin. Point the repo-scoped
   marketplace only at that package, and enforce exact inventory plus
   byte-for-byte and file-mode source parity.
4. Make filesystem installation fail closed on differing existing artifacts
   and on a detected installed `codex-dev-skills` plugin, while preserving
   byte-identical idempotent installs and older-runtime fallback.
5. Align README, roadmap, release readiness, catalog, installer, tests, and a
   v0.14.1 release-notes draft.
6. Run focused plugin/installer/runtime tests, full repository validation, diff
   inspection, code/deep/docs review, and release-readiness review.

## Definition Of Done

- CLI and Desktop keep separate control-plane entrypoints over one shared
  authority and completion contract.
- Runtime claims are dated facts or explicitly labelled inference/preview.
- The plugin manifest and marketplace resolve only to a narrow package whose
  generated skills match canonical tracked sources and pass validation.
- Ignored or untracked checkout state cannot enter the plugin cache, and every
  packaged shared policy/template/doc reference resolves from its `SKILL.md`.
- Filesystem installation cannot overwrite a differing imported or local
  skill/template and cannot knowingly coexist with the installed plugin.
- App memories and Computer History remain advisory local runtime context and
  never become repository evidence or Memory M1 authority.
- `0.14.1` metadata and release notes agree, with tag and GitHub Release still
  gated on reviewed merge evidence.
- Focused and full validation pass with no unresolved MUST-FIX finding.

## Risks And Human Gates

- Plugin publication can expose all bundled skills at once; manifest and local
  marketplace validation are required before publication.
- An unavailable or older CLI cannot prove plugin absence. The installer must
  warn and preserve the documented single-distribution-path responsibility.
- Commit, push, pull request creation, tag creation, GitHub Release
  publication, merge, and installed-state mutation remain separate human
  gates.

## Verification

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python -m unittest \
  tests.test_plugin_packaging \
  tests.test_installer_runtime_groups \
  tests.test_installer_agent_profiles \
  tests.test_native_runtime_contract_docs
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python /path/to/plugin-creator/scripts/validate_plugin.py plugin/codex-dev-skills
bash -n install.sh scripts/validate-repo.sh scripts/project-python
git diff --check
./scripts/validate-repo.sh
```
