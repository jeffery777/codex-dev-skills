# Desktop Project Delivery Example

Use `desktop-project-delivery` in Codex Desktop for delegated bounded work:

```text
Use desktop-project-delivery to deliver this feature to PR readiness.
Review integrated output with code-review or docs-review, escalating high-risk code or mixed changes to code-review-deep.
Use code-review-gate or docs-review-gate only for formal commit readiness, PR readiness, merge readiness, or repo-policy blocking decisions.
Treat desktop-implementation-gate as a deprecated compatibility alias; do not add a separate Desktop integration decision.
Stop for product ambiguity, external writes such as commit, push, PR creation, platform comments, or review submissions; destructive actions; or final merge approval.
```

CLI fallback: use `project-delivery` and `project-orchestrator`, prepare prompts, task briefs, continuation prompts, or a sequential execution path, re-read handoff evidence before trusting it, and run formal gates only at commit readiness, PR readiness, merge readiness, or explicit repo-policy gates.

See [runtime compatibility](../docs/runtime-compatibility.md) for the Desktop-to-CLI fallback mapping.

目前任務的隔離工作範例：

```text
使用 desktop-project-delivery 完成這個有界修改；需要隔離時依 current-worktree
reference 在目前任務建立工作樹。先核對來源 HEAD，明確使用回傳目錄完成
repo 環境設定與驗證。若修改必須包含未提交內容，先釐清移轉方式；不要假設
create_worktree 已複製修改、切換 cwd 或取得寫入權限。
```

這個 prompt 不要求建立新任務或 history fork。若工作樹已建立但登錄失敗，
沿用已回傳並核對的目錄，不為附件登錄重複建立。
