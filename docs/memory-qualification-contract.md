# Memory Qualification Contract V0

`loop-memory-qualification/v0` is the Memory M0 paired safety/conformance
wrapper. It exists because released V3-B has one fixed comparison and cannot
represent a paired memory-off/memory-on qualification without contract drift.

## Wrapper Boundary

The family has `qualification-input` and `qualification-result` kinds. Its
off arm binds an unchanged validated V3-B result/verification pair whose
context is `memory-off`. Its wrapper-only on arm binds another unchanged V3-B
pair plus one separately caller-accepted future M1 qualification receipt,
exact adapter/schema/capability/platform fingerprints, and bounded M1 safety
observations.

The on-arm safety observation requires at least one backend touch and one
execution-receipt digest. A zero-touch on arm fails closed instead of being
reported as conformant.

`memory-on` is not a new V3-B context mode. The wrapper cannot modify or claim
that V3-B evaluated a backend. Both arms must have identical proposal/source,
evaluation input, fixed policy, comparison, and canonical verifier-assignment
bindings.

The future M1 evidence is a strict provider-neutral
`m1-qualification-receipt` document, not a bare digest assertion. It binds the
qualification id, complete common V3-B tuple, adapter/schema/capability/platform
fingerprints, safety-observation digest, and execution-receipt digests. Its
digest must also appear in the caller-owned accepted set; reuse under any
changed binding fails closed.

Initial results are `conformant-awaiting-human-decision`, `not-conformant`, or
`memory-on-unavailable`. They cover safety/conformance only and always retain a
pending independent human/platform gate. Efficacy, quality, latency, and
resource-benefit claims are prohibited.

## Memory-Off Zero Touch

Memory-off is complete, default, and has zero backend/filesystem touch. It
accepts no backend handle, executable, state root, database path, or provider
config and performs no SQLite/FTS5
import/probe or backend/filesystem call. The production surface has no backend,
database, network, subprocess, or filesystem-mutation path.

## Offline CLI

```bash
./scripts/project-python skills/loop-engineering/scripts/qualificationctl.py evaluate \
  <qualification-input.json> <off-result.json> <off-verification.json> \
  --accepted-v3b-receipts <accepted-v3b.json> \
  [--on-result <result.json> --on-verification <verification.json> \
   --m1-qualification-receipt <m1-receipt.json> \
   --accepted-m1-qualification-receipts <accepted-m1.json>]
./scripts/project-python skills/loop-engineering/scripts/qualificationctl.py validate-result \
  <qualification-result.json> <qualification-input.json> \
  <off-result.json> <off-verification.json> \
  --accepted-v3b-receipts <accepted-v3b.json> \
  [--on-result <result.json> --on-verification <verification.json> \
   --m1-qualification-receipt <m1-receipt.json> \
   --accepted-m1-qualification-receipts <accepted-m1.json>]
```

Accepted V3-B evidence uses `{"receipt_digests":[...]}`. Future M1 admission
uses `{"qualification_receipt_digests":[...]}`. The CLI has no promote,
execute, database, provider, install, or activation route.
Result validation reconstructs the same complete caller-owned chain used by
evaluation; a standalone sealed input/result pair cannot prove conformance.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_memory_qualification tests.test_qualificationctl \
  tests.test_eval_memory_qualification
./scripts/project-python scripts/eval-memory-qualification.py
```

Passing does not implement or authorize SQLite/FTS5 M1. This contract is
included in **v0.14.0** as the unchanged qualification authority boundary.
