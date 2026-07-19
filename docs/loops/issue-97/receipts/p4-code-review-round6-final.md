# P4 Formal Deep Code Gate — Final

Gate result: **PASS**.

Independent evidence:

- adapter focused tests: 38/38 passed;
- V2b contract/conformance: 46/46 passed;
- compile and `git diff --check`: passed;
- malformed `cacheKeys` dict/list/int/bool inputs returned
  `corrupt / metadata-cache-keys-invalid` without traceback, stderr output, or
  repository-path leakage.

Disposition: `MF-CODE-001` through `MF-CODE-010` and `SF-CODE-001` through
`SF-CODE-005` are fixed and re-reviewed. Open MF/SF/NIT: none.

Non-blocking residual risks:

- a cooperative deadline cannot hard-interrupt one synchronous filesystem
  syscall or `json.loads()` call;
- same-user TOCTOU can be rejected by postconditions but cannot undo a local
  side effect already performed by the external tool;
- a descendant that deliberately creates a new session can escape the original
  process-group cleanup boundary;
- Linux has portability fixtures, not live GitNexus qualification;
- `_safe_control_file()` is not chunk-deadline-aware, while the subsequent
  bounded Git probe still fails closed before adoption.

These residuals did not form a demonstrated unsafe-adoption path. Default
disabled behavior, unsupported structured query/writes, and no-backend fallback
remain intact.
