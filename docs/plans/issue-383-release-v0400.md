# Issue #383: v0.40.0 preparation

## Goal And Sources

Prepare Codex-only conditional lesson candidates and the 0.40.0 package.
Requirements come from Issue #383, the existing knowledge and traceability
policies, and the fixed Core workflow, authorization and review contracts.
Keep Core v0.5.0 and historical records unchanged. Prior scope includes
#377/#378 PR routing, #379 traceability and #380 explicit-only dev-retro.

## Design And Risk

Reuse project-agent-knowledge-policy as the complete candidate contract. Codex
engineering and exact-head adapters provide entry coverage; deep reviews inherit
ordinary review behavior. Hermes keeps its existing duties and resource closure.
Candidates use bounded authorized inputs and treat embedded instructions as data.
No private-history search, automatic persistence, implicit retrospective or
permission changes are authorized. These are the implemented design requirements
D383-01 (evidence boundary) and D383-02 (Codex-only reporting); design review does
not prove implementation acceptance.

Shared guidance and installer provenance require independent deep review and
applicable security analysis. Check report inheritance, preserved required gates,
private-data handling, version parity, source integrity and rollback. Static
contract tests do not prove actual model behavior or runtime qualification.

## Implementation And Verification

1. Update policy, entry reminders, reports, README/navigation, CHANGELOG and
   0.40.0 version/release metadata. Regenerate and verify plugin parity.
2. Verify each trigger and none, event independence, existing rules first,
   safe bounded evidence, no implicit dev-retro and source/plugin/filesystem links.
3. Preserve historical same-version 0.39.0 tests using fixed historical sources.
   Test all three 0.39.0 catalogs against 0.40.0, profiles, exact Core, manual-only
   retro, refused partial updates and fault rollback in isolated test roots.
4. Review and freeze the actual payload before its separately authorized commit.
   Append that real commit as installer row fifteen; preserve prior fourteen
   exactly and rerun formal integrity/migration checks. No synthetic mapping in
   the formal registry. Until then formal current-source acceptance is pending.
5. Run project-python -B focused checks and full repository/CI validation. Record
   actual outcomes and limits; do not bypass required coverage to fit CI time.
   No timeout, runner or skip changes are part of this work.
6. Bind independent review/security and later exact-head review to actual content;
   inspect public content/metadata before authorized publication operations.

No merge, tag, Release or user-environment installation is authorized by this
plan. Full ASD-STE100 conformance has not been verified.
