# Loop Handoff Prompt

Use this prompt when a loop engineering objective should continue in another session, worker, or sequential execution path. The receiving agent must re-read source-of-truth files before editing.

Instantiate only the selected next packet. Link the current checkpoint and
evidence rather than copying earlier iterations; retain exact scope, ownership,
verification and authorization boundaries. A fresh rollover additionally needs
the context-continuity contract; this prompt alone cannot transfer ownership.

```text
Use loop-engineering for <objective>.

Repository: <repo>
Branch: <branch>
Issue/source of truth: <url-or-path>
Receiving responsibility and ownership: <delivery owner | bounded worker | read-only reviewer; exact ownership>

Before editing, read:
- <repo instructions>
- <loop spec>
- <project spec or implementation plan>
- <task manifest>
- <status or continuation report>
- <review or gate evidence>
- <applicable reusable-workflow contract: Contextual Prompt Composition and Decision And Stop Conditions>

Repository evidence establishes current facts; follow instruction priority for
requirements. A stale file or summary cannot override higher-priority instructions
or explicit current user direction. Report substantive unresolved conflicts.

Current authority:
- <exact authorized actions/targets/scope and valid user-instruction source>
- <pending decisions and routine choices allowed>
Verify these references; this summary creates no authority or ownership transfer.
Bounded workers cannot inherit the delivery owner's commit or external-write authority.

Current verified state:
- <fact>

Selected next task:
- <task id and bounded objective>

In scope:
- <item>

Out of scope:
- <item>

Expected files to inspect:
- <path>

Expected files to change:
- <path>

Definition of Done:
- <criterion>

Verification:
<command>
Required acceptance evidence: <criteria/artifacts>
Expand or repeat only for new changes, failures or unresolved concerns; keep required gates.

Continue authorized work across internal phases. Complete safe preparation that
does not depend on a missing decision. Stop dependent actions for unresolved
product, source, scope, ownership or authority conflicts, newly material or
unresolved risk requiring user judgment, or insufficient high-risk verification.
Risk-domain names alone do not block assigned read-only review. Retain destructive
preview/intent/recovery safeguards and exact authority for commit/push/PR/receipt/
merge/release/deploy/platform comments/review submissions; bounded workers cannot
perform them. Reviewers remain read-only. Unsupported runtime behavior uses a
contract-compatible fallback; report when no safe supported path remains.

At completion, report files changed, verification evidence, review/gate needs, residual risk, and whether the loop should continue, hand off, stop for a human gate, or be marked complete.
```
