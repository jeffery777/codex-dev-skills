# Issue #219 — explicit qualification without a fixed deadline

Base: `abaac8bd2a9443fb0fa55d9e0577f6220531ff5c`.
Branch: `codex/qualification-no-expiry`.
Follow-up to merged Issue #217 / PR #218.

## Objective and acceptance

The operator explicitly chose condition-based qualification rather than an
arbitrary fixed expiry. Accept JSON `expires_on: null` as no fixed deadline.
Keep the field required and reject missing fields, wrong types, string `null`
and invalid dates. Preserve existing dated approvals and their inclusive
deadline; do not silently extend or migrate them.

Null skips only the date comparison. Record/store revocation, canonical
role/class/tier/profile binding, evidence digest, exact scope/runtime matching,
current capability, installed bytes, sandbox and fallback checks remain.
Document that unchanged hashes cannot detect unobserved provider-side model
behavior changes; quality concerns require revocation and revalidation.

## Verification and review

Focused tests cover no expiry far in the future, malformed input, retained
negative controls, inclusive dated deadlines and the complete installed-router
autoload path. Run repository validation and source/plugin parity checks.
Review the complete code/documentation diff and security boundary; complete
exact-head Merge Review after PR creation. Earlier content evidence is reusable
only when its scope and content match; it does not replace exact-head review.

## Adoption and process correction

The change was implemented on this separate branch and locally adopted with
operator authorization before this Issue was created. The personal store has
three bounded CLI-only approvals with explicit null expiry. Local discovery,
Desktop/scope rejection and controlled router smoke checks passed. These are
integration checks, not new model-quality or native-dispatch attestations.

This record corrects the missing Issue-first tracking. Personal data, paths,
qualification records and backup inventory stay outside the public repository.
Preserve existing Issue #217 history. Source/package version remains 0.23.0;
this change makes no release-publication claim. Local adoption does not itself
prove PR or merge readiness.
