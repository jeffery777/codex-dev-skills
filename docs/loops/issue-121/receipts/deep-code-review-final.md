# Issue #121 Final Deep Code Review

Date: 2026-07-29

Review mode: `code-review-deep`

Gate result: PASS

Authority: advisory read-only review evidence only

## Findings

No MUST-FIX, SHOULD-FIX, or NIT finding remains.

| Finding | Disposition | Closure evidence |
| --- | --- | --- |
| `CR121-001` authority integers compared equal to false | Fixed | Exact key set plus `type(value) is bool` and `value is False`; tests cover `True`, `0`, `1`, `null`, and string substitution |
| `CR121-002` timestamp parser accepted broader separators than the public contract | Fixed | Exact grammar requires literal `T`, bounded fractional seconds, and explicit `Z` or offset; tests cover valid and invalid forms |
| `CR121-003` mandatory relationship fixtures were absent | Fixed | invalid-reference, duplicate-document-id, and cross-record-mismatch are mandatory cases in the 12-case suite |
| `CR121-004` pathname replacement with a FIFO could block before descriptor recheck | Fixed | Production and eval readers use nonblocking open, regular-file checks, no-follow where available, and lstat/fstat identity |
| `CR121-005` eval digest and validation could observe different file bytes | Fixed | One bounded immutable byte buffer supplies the digest and both deterministic observations; the test proves one fixture read |
| `CR121-006` fixture symlinks could be hidden by path resolution | Fixed | Final symlinks and symlink parents are rejected; self-loop, internal-final, and parent-symlink tests pass |
| `CR121-007` UTC normalization could escape as `OverflowError` | Fixed | Parse, offset, and UTC normalization share one structured error boundary; API and CLI upper/lower boundary tests prove no traceback or echo |

The run receipt and its referenced environment fingerprint now require the
same execution mode in the loop spec, portable reference, public contract,
validator, and tests.

## Verification Reviewed

- focused operational-evidence tests: 44 passed;
- operational-evidence eval: 12/12 passed with exact thresholds;
- full repository validation: passed;
- ledger validation: passed;
- shell syntax and diff hygiene: passed.

## Deep Risk Notes

- Descriptor identity checks cannot stop a same-identity local process from
  modifying the same inode during a read. Validation still consumes one
  bounded byte buffer; the current repository/local-controlled threat model
  does not treat this as a blocker.
- Privacy patterns are defense in depth rather than full DLP. Remote,
  multi-user, persistent, or automatic ingestion would require a new
  source-to-sink review.
- This pre-commit review binds a dirty working-tree snapshot. Any subsequent
  behavioral change requires affected review and verification to be rerun.

## Re-runnable Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_operational_evidence \
  tests.test_evidencectl \
  tests.test_eval_operational_evidence
python3 scripts/eval-operational-evidence.py
python3 scripts/validate-loop-ledger.py
./scripts/validate-repo.sh
bash -n install.sh scripts/validate-repo.sh
git diff --check
```
