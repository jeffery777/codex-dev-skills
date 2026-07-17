# P4 Security Diff Scan — Final

## Scope

Codex Security plugin `0.1.11` reviewed the frozen working-tree diff against
`origin/main` at `a75728b15f5d15ba7bf1a7e6e3a2dd934915592e`. Source-like coverage included
the production GitNexus adapter, its V2b contract dependency, adapter security
tests, and mandatory V2b conformance fixtures. Non-executable documentation and
loop evidence were covered by the formal code/docs gates and excluded from the
source-like worklist; this receipt is generated after finalization and was not
recursively scanned.

The plugin helper used an isolated temporary Git index so untracked source was
visible. The real repository index digest remained unchanged. No machine-local
path, registry, index, credential, or database content is recorded here.

## First scan and engineering disposition

- Scan ID: `a75728b15f5d15ba7bf1a7e6e3a2dd934915592e_20260717T000604Z`
- Frozen snapshot: `codex-security-snapshot/v1:sha256:a01129b4c9e0d96064906114f4c904950e7c58544fb1f2b982a7806b81424131`
- Native status: `completed`; coverage: `complete`; reportable findings: `0`
- Candidate: `gnx-fifo-metadata-open-dos`
- Security-policy disposition: rejected because the path required same-user
  local write influence and did not meet reportability policy.
- Engineering disposition: MUST-FIX because blocking `open` violated Issue #97
  fail-closed and deadline requirements.

The adapter now performs `open(O_NONBLOCK | O_NOFOLLOW)`, descriptor-bound
`fstat`, regular-file rejection, and only then bounded reads. A runtime without
`O_NONBLOCK` fails closed before `open`. Real-FIFO and missing-constant
regressions passed, the adapter suite passed 40/40, and a formal post-fix deep
review reported no MUST-FIX, SHOULD-FIX, or NIT findings.

## Final post-fix scan

- Scan ID: `a75728b15f5d15ba7bf1a7e6e3a2dd934915592e_20260717T015027Z`
- Frozen snapshot: `codex-security-snapshot/v1:sha256:5c3edf9add7ffe2c326c789d1672ec8157578cd3948092c9a22d0960fda7d31d`
- Native status: `completed`; coverage: `complete`
- Worklist closure: `4/4`
- Surfaces: `3/3 no_issue_found`
- Findings: `0`
- Manifest SHA-256: `dfd335542b7b6fc01bbd107ccb8b8d2b39a8abb28ae842833ee20afc3048c77b`
- Findings SHA-256: `e7d0a8d0d221bea0a7428ece9348f97d252645cc1df276ca814b4d6fc12578d6`
- Coverage SHA-256: `a7b9be456f233d4e107be706602dfc8781d0b53587bc33f84e76fc358b41dd10`
- Report SHA-256: `4bcb30c60ff418875c1ce8fbe57c56ad0e18d6cf205ed8dacc5e1bf8785e75fe`
- Finalizer idempotency: PASS

A dedicated validation worker was refused by the runtime cybersecurity
classifier. Per the scan recovery contract this was not treated as native scan
failure; the coordinator did not evade or rephrase the refusal and instead used
static source/control/sink analysis, safe local fixtures, negative tests, and
formal defensive deep review. Linux was not live-tested; portability remains
fixture/contract evidence and is not represented as live qualification.

## Gate result

**PASS.** Codex Security native finalization succeeded for the corrected frozen
diff. Open security MF/SF/NIT: none.
