# Release Notes: v0.4.0

v0.4.0 adds repo-owned loop state and ledger support for `loop-engineering`.
This is the first release where a bounded loop objective can carry durable task
state, claim/lease context, verification evidence, review evidence, blockers,
and next-loop decisions through repository files without requiring an external
memory adapter.

## Highlights

- Added `docs/loop-state-ledger.md` as the repo-owned loop memory contract.
- Added `templates/orchestration/loop-state-ledger.template.yaml`.
- Updated `loop-engineering` guidance to bootstrap from repo-owned loop ledgers
  when a target repository uses them.
- Updated loop workflow docs, examples, and README usage guidance for ledger
  driven continuation and handoff.
- Expanded loop templates for source revision, task ledger updates, current task
  summaries, claim/lease context, and recovery evidence.
- Added `scripts/validate-loop-ledger.py` and validator tests.
- Wired loop ledger validation into `scripts/validate-repo.sh`.

## Compatibility

Existing skills remain independently usable. This release does not turn
`loop-engineering` into a scheduler, daemon, runtime adapter, platform writer,
or release bot.

The existing task manifest status enum remains unchanged. Richer loop state
lives in the optional repo-owned loop ledger template.

## External Memory

This release does not implement optional external memory adapters.

External memory systems may be evaluated later as cache, coordination, code
intelligence, or task-index layers. By default, task completion and acceptance
still require repo-owned ledger evidence, git state, verification evidence,
review evidence, or accepted platform state.

## Verification

Release prep should verify:

```bash
bash -n install.sh
bash -n scripts/validate-repo.sh
python3 scripts/validate-loop-ledger.py
PYTHONPYCACHEPREFIX=/tmp/codex-dev-skills-pycache python3 -m unittest tests/test_validate_loop_ledger.py
./install.sh manifest
CODEX_DEV_SKILLS_TARGET=agents ./install.sh manifest
./scripts/validate-repo.sh
git diff --check
```
