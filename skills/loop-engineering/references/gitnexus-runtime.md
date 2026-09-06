# Optional GitNexus Runtime Integration

Read only before using or assessing the optional GitNexus hook/controller
path. Hooks are optional guardrails and are not complete enforcement; the loop
must remain safe when they are absent or miss an equivalent tool path.

The optional V2c-B GitNexus runner uses only documented `SessionStart` and
`PostToolUse` events for `Bash` and `apply_patch`. It is notify-only by default,
never parses the shell command, patch, tool response, or transcript, and
treats those events as incomplete repository-change signals. Auto-on-demand
requires separate machine-local opt-in and delegates only a clean eligible
revision in the exact configured checkout to the qualified V2c-A controller.
Each primary checkout or linked worktree requires its own exact machine-local
root and worktree-bound index identity; a config for one checkout must reject
events from another. Linked-worktree automatic refresh remains unqualified and
fails closed without updating the primary checkout's index. After a merge, the
primary checkout must first advance locally; its next `SessionStart` or
completed `Bash`-matched shell/unified-exec event can then refresh that clean
HEAD. A remote PR/MR result
alone cannot update a local index. Controller failure installs a durable
repository-bound circuit breaker so later hook events cannot retry
automatically without operator clearance. Installing its templates does not
activate hooks or grant trust. The shipped runner stays synchronous because
background hook invocations may overlap and finish out of order.

The GN-FU-01 `gitnexus-index-identity/v1` sidecar makes exactness content-bound,
not HEAD-only. A qualified refresh writes it only after metadata postconditions;
later status/hook checks require an exact repository, checkout/worktree,
branch/HEAD, complete relevant content, tool/configuration, and freshness match.
Missing/old evidence plus dirty tracked, untracked, mixed, detached, ignored-
content-drifted, or cross-worktree state is advisory. PR base/head pair identity
binds two clean committed contents but proves no review or gate. These documents
remain non-authoritative and do not enable linked automatic refresh.
