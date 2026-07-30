# Issue #121 Final Security And Privacy Review

Date: 2026-07-29

Gate result: PASS

Authority: advisory read-only security/privacy evidence only

## Canonical Diff Scan

The formal Codex Security diff scan was sealed successfully:

- scan id: `f34b52df-af5f-4c49-ad74-413d3501e609`;
- discovery worklist receipts: 22/22;
- validation receipts: 7/7;
- attack-path receipts: 3/3;
- final reportable findings: 0.

The sealed scan is point-in-time evidence from before the last defensive
hardening edits. Current-tree focused security/privacy re-review therefore
rechecked each changed parser, file, error, fixture, and relationship boundary
after those fixes.

## Current-Tree Findings And Dispositions

| Finding | Disposition |
| --- | --- |
| Standalone access-token signatures were not rejected | Fixed; synthetic standalone-token fixture and test added |
| Eval suite/fixture input and duplicate keys lacked complete bounds | Fixed; bounded descriptor reads and duplicate-key rejection added |
| The privacy oracle accepted messages without an exact per-case contract | Fixed; exact generic non-echo messages are mandatory |
| Deep JSON could escape through `RecursionError` | Fixed; structured `invalid-json` rejection |
| Fixture resolution could escape through symlink-loop exceptions | Fixed; bounded eval configuration rejection |
| Internal final or parent symlinks could bypass the intended file contract | Fixed; both boundaries reject and have direct regressions |
| UTC timestamp normalization could raise an unstructured `OverflowError` | Fixed; API and CLI boundaries return generic `invalid-structure` without traceback or input echo |

Final focused re-review found no unresolved security/privacy MUST-FIX or
SHOULD-FIX.

## Controls Rechecked

- all four authority invariant values require exact JSON booleans equal to
  false;
- document and eval readers require stable regular non-symlink descriptors,
  use nonblocking open where supported, and read bounded bytes;
- each eval hashes and validates one byte snapshot;
- errors use stable codes and literal generic messages without rejected input;
- secret, private-path, raw-log, tamper, duplicate, and relationship fixtures
  fail closed;
- validation is offline, performs no artifact dereference, and grants no
  authorization, completion, external-write, or promotion authority.

## Residual Risk

- A same-identity local process can modify the same inode during a descriptor
  read. The current local-controlled-input threat model accepts this; a future
  untrusted ingestion surface must revisit atomic snapshot requirements.
- Credential detection is a finite defense-in-depth signature set, not full
  DLP. Persistence, remote ingestion, multi-user use, or publication pipelines
  require a fresh privacy review.
- No live secret, private PoC record, local runtime path, log, transcript,
  cache, database, or machine identifier was added.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_operational_evidence \
  tests.test_evidencectl \
  tests.test_eval_operational_evidence
python3 scripts/eval-operational-evidence.py
./scripts/validate-repo.sh
git diff --check
```
