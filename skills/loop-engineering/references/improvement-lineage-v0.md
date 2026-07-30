# Improvement Lineage And Projection V0

Use this installed reference with `scripts/improvementctl.py`.

V2d-B keeps three independent families:

- `loop-operational-evidence/v0`: exact V2d-A run evidence;
- `loop-improvement-lineage/v0`: exact cross-run improvement records;
- `loop-evidence-projection/v0`: deterministic derived manifests.

Never add V2d-B fields or kinds to V2d-A documents. Resolve every V2d-A
reference by contract, kind, id, and digest.

An improvement record binds stable identity, repository/objective, baseline
and candidate evidence snapshots, source failures, typed evaluation artifacts,
four distinct declared roles, a non-promotional disposition, exact false
authority fields, and a canonical record digest.

Validation rejects duplicate/conflicting identity, missing or stale
predecessors, cycles or cycle attempts, baseline/candidate equality,
repository/objective/source/environment mismatch, unresolved artifacts,
unsorted references, self-verifier/promoter role collision, tamper, private
data, and false authority.

Human projection is deterministic Markdown without caller-supplied prose.
Typed graph projection is a deterministic node/edge manifest without a graph
database or runtime. The Obsidian reference profile is optional, declarative,
dependency-free, and non-mutating.

`validate-projection` validates a manifest against its complete source set; it
does not validate a separately stored Markdown file. Present the
`project-human` rendering from the same invocation or compare the displayed
UTF-8 bytes with `rendered_content_sha256`.

```bash
python3 <installed-loop-engineering>/scripts/improvementctl.py --help
python3 <installed-loop-engineering>/scripts/improvementctl.py validate-set \
  <record.json>... --evidence <v2d-a-document.json>...
python3 <installed-loop-engineering>/scripts/improvementctl.py project-human \
  <record.json>... --evidence <v2d-a-document.json>...
python3 <installed-loop-engineering>/scripts/improvementctl.py project-graph \
  <record.json>... --evidence <v2d-a-document.json>...
```

All outputs are advisory. They do not authenticate actors, prove completion,
satisfy gates, or authorize writes, promotion, merge, release, or deployment.
Keep real records and projections outside this public repository, and never
place credentials or tokens in record identifiers.
