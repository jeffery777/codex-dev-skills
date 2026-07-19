# P4 Deep Code Review — Round 1

Gate result: **BLOCKED**. This is read-only review evidence, not completion
authority.

## MUST-FIX

- `MF-CODE-001`: an untracked working tree could be classified as fresh.
- `MF-CODE-002`: a pre-existing symlink inside the derived `.gitnexus` tree
  could redirect refresh writes outside the qualified root before postchecks.
- `MF-CODE-003`: timeout handling did not guarantee termination of subprocess
  descendants.
- `MF-CODE-004`: remote normalization collapsed distinct non-default ports.
- `MF-CODE-005`: Git evidence subprocesses lacked a shared timeout and hard
  output bound.

## SHOULD-FIX

- Revalidate the qualification/fingerprint at handshake time.
- Validate the effective Git ignore rule rather than only literal text.
- Keep adapter conformance claims limited to unsupported/fallback behavior.
- Remove unsafe caller-controlled temporary-directory environment values.

All findings were assigned to the main delivery agent for repair and mandatory
re-review. No files were modified by the reviewer.
