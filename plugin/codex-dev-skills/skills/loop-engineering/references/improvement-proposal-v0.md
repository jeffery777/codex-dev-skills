# Improvement Proposal V0

Use this installed reference with `scripts/proposalctl.py`.

V3-A adds only the downstream `loop-improvement-proposal/v0` proposal-set
family. It reruns strict V2d-B lineage validation over complete V2d-A evidence;
never add proposal fields to V2d-A/B or trust caller validity flags.

The one-way composition order is `loop-operational-evidence/v0` →
`loop-improvement-lineage/v0` → `loop-improvement-proposal/v0`.

An eligible record has a proposed/evaluated/verified disposition, at least one
resolved source failure, complete baseline/candidate run/environment/artifact
lineage, evaluation artifacts, and four distinct declared roles. Rejected or
failure-incomplete records emit no proposal.

Scoring is fixed integer-only `loop-proposal-score/v0`. Hypotheses and output
intents are closed enums. Duplicate candidates are selected deterministically;
ties use exact record identity, and suppressed sources remain recorded.

Every output retains full validated source lineage, exact false-authority
fields, `proposal_only: true`, false action fields, and a required pending
independent human/platform promotion gate.

```bash
python3 <installed-loop-engineering>/scripts/proposalctl.py --help
python3 <installed-loop-engineering>/scripts/proposalctl.py generate \
  --record <record.json> --evidence <v2d-a-document.json>
python3 <installed-loop-engineering>/scripts/proposalctl.py validate \
  <proposal-set.json> \
  --record <record.json> --evidence <v2d-a-document.json>
```

Repeat the flags for multiple explicit files. Commands only read bounded
regular files and write canonical stdout/stderr. They do not apply a proposal,
write files, invoke Git or a platform, dereference artifacts, use a network,
run hooks/services, or approve/promote anything.

Keep real/private evidence and proposals outside public Git. Never include
credentials, PII, host/user identity, private paths/config, or raw logs. No
PlugMem, Mem0, or external-memory backend is installed or enabled.
