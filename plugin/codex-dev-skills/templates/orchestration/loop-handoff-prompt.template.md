# Loop Handoff Prompt

Use this prompt when a loop engineering objective should continue in another session, worker, or sequential execution path. The receiving agent must re-read source-of-truth files before editing.

```text
Use loop-engineering for <objective>.

Repository: <repo>
Branch: <branch>
Issue/source of truth: <url-or-path>

Before editing, read:
- <repo instructions>
- <loop spec>
- <project spec or implementation plan>
- <task manifest>
- <status or continuation report>
- <review or gate evidence>

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

Stop for product ambiguity, source-of-truth conflict, scope expansion, destructive action, external writes, commit/push/PR/merge/release/deploy/platform comments/review submissions without exact authorization, material risk, unsupported Desktop runtime behavior, or insufficient verification for high-risk changes.

At completion, report files changed, verification evidence, review/gate needs, residual risk, and whether the loop should continue, hand off, stop for a human gate, or be marked complete.
```
