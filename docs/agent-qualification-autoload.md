# User-owned qualification discovery

V2 `agent-route` reads `${CODEX_HOME:-~/.codex}/agent-qualifications.json`
on every invocation when current runtime facts omit `enabled_candidates`.
An explicitly supplied key, including `{}`, retains the existing explicit
qualification path and suppresses discovery. V1 never discovers qualifications.
The store is optional: absence or rejection leaves baseline routing in place.
No project-local store is discovered, and no installer creates or enables one.

The parent sets `task.qualification_scope` to an exact, nonempty string describing
the actual bounded task. It must match a qualified `task_scopes` entry exactly;
there are no wildcard scopes. Omission cannot enable a scoped candidate. Do not
choose a label merely to make a candidate eligible.

## Store contract

This example is synthetic and does not qualify any real model or profile:

```json
{
  "schema_version": 1,
  "enabled": true,
  "qualifications": [
    {
      "profile": "loop_v2a_astra_advanced_worker",
      "profile_sha256": "<64 lowercase hexadecimal characters>",
      "capability_class": "balanced-worker",
      "capability_tier": "advanced",
      "task_scopes": ["fixture-repair"],
      "runtimes": ["cli"],
      "quality_evidence": "qualification/fixture-report.md",
      "quality_evidence_sha256": "<64 lowercase hexadecimal characters>",
      "expires_on": null,
      "enabled": true
    }
  ]
}
```

All shown fields are required. Unknown fields, duplicate JSON keys, duplicate
profile records, nonfinite JSON values, invalid dates, and malformed records
reject the store. Lists contain unique, nonempty strings; runtimes are `cli`,
`desktop`, or `api`. Set `expires_on` explicitly to `null` for no fixed deadline;
the field remains required. An optional date uses `YYYY-MM-DD` and is inclusive
through that local calendar date. Existing dated approvals keep their deadline;
they are never silently converted to indefinite approvals. There is no automatic
expiry reminder or renewal prompt. Disabling the store revokes every candidate. Disabling a
record revokes that profile. Removal takes effect on the next route invocation.

A record without a fixed deadline still undergoes every integrity, scope,
runtime and current-capability check on each invocation. Changed profile or
evidence bytes invalidate its binding; an inapplicable task or runtime cannot
use it. These checks do not detect unobserved provider-side model behavior
changes: new quality concerns still require explicit revocation and revalidation.

A record must match the canonical candidate's baseline role, capability class,
tier, and profile digest. Its scope and runtime must match the current task and
current runtime facts. Its evidence file must match the recorded SHA-256. These
are integrity and applicability checks, not automated grading of model quality.
The user is responsible for approving valid evidence before enabling a record.
Evidence is read as bytes only; its text is never executed or treated as instructions.

## Trust boundary

This protected loader currently supports POSIX platforms with directory-relative,
non-following file operations. Other platforms report `unsupported-platform` and
retain baseline routing; the existing explicit qualification path remains available.

`CODEX_HOME` is a user/session environment choice, not a project configuration
field. It must be absolute, outside a Git repository, and contain no symlinks or
parent traversal. Root-owned system ancestors are accepted; the store directory,
store file, evidence files, and evidence subdirectories must belong to the current
user and must not be group/world writable. Root-owned sticky system ancestors
(such as the real temporary directory) are allowed, with the same protected-child
requirements. A symlinked temporary alias must be resolved by the caller.

Discovery uses directory-relative descriptors, non-following opens, regular-file
checks, and bounded nonblocking reads. It rejects FIFOs/devices, oversized files,
and files changed during reading. The JSON limit is 64 KiB; each evidence file
limit is 1 MiB. Evidence paths are relative beneath the store directory with no
empty, dot, parent, absolute, or backslash components. A rejected read clears all
candidates collected during that invocation. No network access is performed.

This protection does not defend against a compromised current-user account or
an environment deliberately controlled by that user. A checksum is not a signature
or independent attestation of successful model verification.

## Current-session runtime and receipts

Current-session runtime facts remain required via `--runtime-facts FILE` or
`--runtime-facts -` (JSON on standard input). The workflow parent supplies them
from the current callable surface; the user need not type qualification parameters.
The loader never reads saved model availability or private Desktop state. A CLI
qualification does not qualify Desktop unless the record explicitly includes it.
Existing model, effort, installed-profile-byte, collision, sandbox, and capability
fallback checks still run after qualification discovery.

`route_receipt.profile_selection.autoload` records `status`, reason codes,
`store_sha256` when a bounded store was read, and the requested scope. The existing
receipt digest binds this audit object. `qualified` means the data passed loader
checks; the candidate may still fail runtime or installed-profile preflight and
use baseline routing. `explicit-override` identifies the legacy explicit path.
Human-gate output also includes `profile_selection` for diagnostics, without
claiming a successful route receipt. No evidence contents or local store paths
are copied into receipts.
Autoload emits `qualification-evidence-sha256:<digest>` as the evidence reference;
the store digest binds the record that supplied it. The legacy explicit-input
interface retains caller-supplied references unchanged.
