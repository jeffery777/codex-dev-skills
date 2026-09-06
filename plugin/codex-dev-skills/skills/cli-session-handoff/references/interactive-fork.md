# Manual Interactive Fork

Use only after an explicitly requested same-task fork of an exact known
session. Return a paste-ready `codex fork <SESSION_ID>` command and the chosen
working-directory policy; the executor does not automate the TUI.

`tui.resume_cwd = "session"` selects the saved session directory; `"current"`
selects the invocation directory; an unset value prompts when they differ.
Choose deliberately from public context rather than private session files.


- Use only the documented `codex fork <SESSION_ID>` surface with an exact UUID.
- Record whether the selected working directory is the saved `session`
  directory or the invocation `current` directory; do not guess when they
  differ.
- Use public `-C <DIR>` and `tui.resume_cwd` behavior when needed; do not read
  private session files to recover a path.
- Treat a dirty existing checkout/worktree as eligible only for exclusive
  same-task continuation with no concurrent writer. It is not eligible for the
  automated private-clone executor.
- Do not create or select a new Git worktree when the intent is to reuse the
  existing one.
- Do not confuse automated `codex exec fork` with interactive `codex fork`;
  only the latter remains a manual interactive handoff.


A prepared interactive-fork command is a handoff artifact, not evidence that
a fork occurred. Only the public CLI result after manual execution proves
session dispatch. The originating session still owns integration and review.
