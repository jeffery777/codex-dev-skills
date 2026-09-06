# Security Scan Recovery

Read whenever the selected workflow invokes an installed Codex Security scan,
before phase continuation, recovery, or reporting. The active security skill
retains its phase and completion authority.

When a routed workflow invokes an installed Codex Security scan skill, keep
three state projections separate:

- scan-native status and phase are authoritative for whether the scan is
  running, complete, failed, or cancelled;
- Goal status is runtime progress projection only;
- phase worker status is capability evidence only.

If scan-native status is `running`, a blocked Goal or a worker
`safety_refused` result must not fail or abandon the scan. Route through
`task-continuation`, preserve scan-local artifacts, and continue as follows:

1. On the first refusal in any scan phase, use one replacement worker when
   supported or continue in the current session.
2. After two refusals in the same phase, stop at a human gate unless the
   current session has exact authorization for parent scan-phase fallback.
3. Only after that authorization, pass `loopctl.py decide <decision-input.yaml>
   --parent-security-scan-fallback-authorized --protected-history-sha256
   <verified-digest-or-none>` and let the parent produce the required scan-local
   artifacts under the active scan skill's phase contract. The legacy
   `--parent-security-report-fallback-authorized` spelling remains an alias for
   reporting-only compatibility.

Never read fallback authorization from the repo decision YAML. Never call a
terminal scan-failure operation merely because a worker refused, a Goal was
blocked, artifacts are partial, or a turn ended. Use the active security skill
as authority for phase updates, canonical artifacts, recovery exhaustion,
completion, and the rare truly unrecoverable failure. If Goal projection is
blocked while the scan remains running, resume the Goal when the runtime
requires user action, then continue from scan-native context instead of
restarting the scan.

If the visible commentary channel suppresses a detailed progress message, do
not treat the display failure as task or scan failure and do not retry the same
payload with disguised wording. Persist details in repo-owned or scan-owned
artifacts and switch visible updates to a fixed neutral heartbeat such as
`running | phase 3/5 | completed 7/7`. Emit a heartbeat at meaningful phase
changes and at least once per 60 seconds while actively working, use bounded
polling, and continue through the current-session path when that remains safe.
The host remains responsible for exposing a structured suppression reason and
resume/control API; repository artifacts remain completion authority.

During reporting, keep canonical JSON bytes and semantics aligned. Before the
active scan completion call, serialize `scan-manifest.json` with the active
security workflow's canonical writer; for the current JSON contract this is
sorted keys, two-space indentation, and one trailing newline. If `report.md`
was projected but scan-native status remains `running` with a sealed-manifest
CAS error, do not restart or fail the scan. Compare the manifest to canonical
JSON bytes, canonicalize it without changing semantics, verify sealed artifact
hashes, and retry completion once on the same scan id.
