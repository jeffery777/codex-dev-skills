# Release Notes: v0.23.0

Status: release candidate prepared through Issue #209. Commit, merge, annotated
tag, and non-draft/non-prerelease publication are separate human gates.

## Memory M1 Thin Local Opt-In Pilot

- Adds a default-off `memory-m1-local-pilot/v1` façade and `memorypilotctl.py`
  explicit `remember`, `recall`, and logical-`invalidate` routes for
  local/manual/CI-only use.
- Reuses the qualified SQLite/FTS5 M1 adapter, V2b records/retrieval decision,
  and exact M0 authority chain without changing their schema or semantics.
- Allows only synthetic, advisory context classification for verified facts,
  decisions, constraints, and evidence references. Pilot input is limited to
  one trimmed 512-byte line and applies V2b sensitivity checks plus lexical
  rejection for chat/log markers, private paths, credentials, PII, and config
  assignments; this is not a general DLP guarantee.
- Pre-registers synthetic precision, stale rejection, false-authority,
  non-regression, and bounded-context criteria. The runner derives observations
  from isolated M1 remember/recall and cross-class supersession executions,
  compares the same repository-authoritative synthetic task on off/on arms,
  and measures the exact minimal context projection delivered to that task. A
  pass awaits an independent human decision and does not authorize activation,
  promotion, merge, release, or efficacy claims.

## Compatibility And Boundaries

`catalog.yaml`, `install.sh`, and the generated plugin manifest agree on
`0.23.0`. No external API, embedding model, vector database, provider/MCP,
daemon, service, scheduler, automatic recall/write, physical purge, migration,
or V3-C behavior is included.

## Verification And Release Gate

```bash
./scripts/project-python scripts/eval-memory-pilot.py
./scripts/project-python -m unittest tests.test_memory_pilot
./scripts/project-python scripts/validate-release-state.py
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh
git diff --check
```

Synthetic evidence is bounded to fixtures and must receive independent human
review before any commit, push, PR, tag, publication, activation, or promotion.

## Traceability

- Issue #209: <https://github.com/jeffery777/codex-dev-skills/issues/209>
