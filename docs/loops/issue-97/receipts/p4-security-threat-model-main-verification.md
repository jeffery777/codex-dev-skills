# P4 Security Threat Model Main-Agent Verification

The main agent independently verified the two Phase 1 artifacts with `cmp`,
SHA-256, footer inspection, and a fresh repository status check.

- repository-scoped and per-scan threat models are byte-for-byte identical;
- SHA-256 is `503f94f1d34d27852b81592414040e6e851a2d121630272a54a46a499e42f8cb`;
- the cache footer binds repository target
  `target_sha256_a409ff64b9cef22b1ad14b6a00659e99606a3702f40f6e5eb81e4ae4da887bbd`
  and snapshot
  `codex-security-snapshot/v1:sha256:a01129b4c9e0d96064906114f4c904950e7c58544fb1f2b982a7806b81424131`;
- no repository file outside the already scoped Issue #97 working-tree diff
  changed during the phase;
- the artifact is repository-scoped and does not make findings about the
  current diff.

Disposition: accepted as Phase 1 context only. It is not scan completion or
finding evidence.
