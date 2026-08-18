# Release Notes: v0.14.1

Status: release candidate; tag and GitHub Release are not created by this
document.

v0.14.1 is a compatibility and packaging patch over v0.14.0. It does not
change the released Memory M0/M1 contracts or shared workflow completion
authority.

## Runtime Compatibility

- Refreshes dated Codex Desktop and CLI evidence for current automation,
  `create_thread.startingState`, archived-task discovery, Codex panels,
  terminal observation, universal plugins/imports, local memories, Computer
  History, and the Linux Desktop preview.
- Keeps CLI session control and Desktop task/thread/worktree control as
  independent thin adapters over the same shared delivery, evidence, review,
  and human-gate layer.
- Defines unavailable Desktop capabilities as explicit degradation to manual,
  CLI, prompt, or sequential paths rather than inferred private-runtime access.

## Plugin And Installer

- Adds a narrow, generated skills-only package under `plugin/codex-dev-skills/`
  and a repo-scoped local marketplace entry that points only to that package,
  preventing ignored or untracked checkout state from entering the plugin
  cache. An exact-inventory and parity validator rejects extra entries and keeps
  packaged files aligned with canonical tracked skills and allowlisted shared
  resources.
- Retains the filesystem installer as a separate supported distribution path.
- Refuses filesystem install/update when `codex plugin list --json` reports the
  `codex-dev-skills` plugin installed, unless the operator first removes one
  distribution path.
- Makes install preflight fail before mutation when an existing skill or
  template differs, while preserving byte-identical idempotent installs.
- Documents imported-skill and plugin duplicate review after Desktop or CLI
  import.

## Memory And Privacy Boundary

- Separates local Codex/ChatGPT memories and Computer History from the
  repository's default-disabled `loop-memory-sqlite/v0` Memory M1 adapter.
- Treats app-generated memory/history as sensitive, untrusted advisory context;
  it is never copied automatically into repository evidence or M1 and never
  becomes completion or operation authority.

## Verification And Release Gate

The release candidate requires plugin validation, focused runtime/installer
tests, full repository validation, diff inspection, code/deep/docs review, and
merge-readiness evidence. The annotated `v0.14.1` tag and GitHub Release must
bind the exact reviewed merge commit after the maintainer's release gate; this
draft does not authorize or claim either external write.

```bash
./scripts/project-python -m unittest \
  tests.test_plugin_packaging \
  tests.test_installer_runtime_groups \
  tests.test_installer_agent_profiles \
  tests.test_native_runtime_contract_docs
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python /path/to/plugin-creator/scripts/validate_plugin.py \
  plugin/codex-dev-skills
./scripts/validate-repo.sh
git diff --check
```

## Traceability

- Issue: <https://github.com/jeffery777/codex-dev-skills/issues/149>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.14.0...v0.14.1>
