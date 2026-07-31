# Codex Runtime Compatibility Evidence — 2026-07-31

This record compares the public and intentionally exposed Codex Desktop
contract used by this repository after the ChatGPT desktop app updated from
`26.721.81911` build `5973` to `26.727.40816` build `6067`. It is a
point-in-time snapshot, not a promise that a callable, request field, response
field, or UI behavior will remain available.

## Scope And Sources

The comparison used only:

- `/Applications/ChatGPT.app/Contents/Info.plist` bundle metadata;
- callable descriptions and schemas exposed to the current Desktop task;
- the current Desktop host instruction for rendering successful task creation;
- read-only `list_projects` and `list_threads` results exposed by those
  callables, recorded only as normalized response-shape evidence;
- the official [ChatGPT desktop app commands](https://learn.chatgpt.com/docs/reference/commands),
  [projects and chats](https://learn.chatgpt.com/docs/projects), and
  [troubleshooting](https://learn.chatgpt.com/docs/reference/troubleshooting)
  guidance;
- the official [Remote connections](https://learn.chatgpt.com/docs/remote-connections)
  guidance for connected-device and SSH-host project execution and cross-host
  handoff;
- the official [Codex developer commands](https://learn.chatgpt.com/docs/developer-commands#codex-fork);
- `codex --version`, public `--help`, including `resume` and `fork`, and
  `codex app-server generate-json-schema --out <temp-dir>`;
- the maintained
  [2026-07-30 compatibility evidence](codex-runtime-compatibility-evidence-2026-07-30.md)
  as the previous comparison point.

No Desktop database, session, log, authentication file, cache, application
state, unpublished endpoint, UI scraping, or reverse-engineered internal was
inspected. The initial compatibility inventory was read-only. A later,
separately authorized controlled `projectless` task creation was used only to
verify ready dispatch, exact-ID bounded wait, the required created-thread
directive, and user-observed sidebar registration. A second separately
authorized controlled same-directory fork verified source-host inheritance,
registry-based child-host resolution, and checkout continuity without creating
a worktree. Neither controlled task performed file/tool work or received a
follow-up; neither was handed off, renamed, pinned, archived, or navigated.

## Version Evidence

| Surface | 2026-07-30 evidence | 2026-07-31 evidence | Classification |
| --- | --- | --- | --- |
| Codex CLI | `0.146.0` | `0.146.0` | `no change` |
| Desktop bundle | `26.721.81911` build `5973` | `26.727.40816` build `6067` | `docs/test evidence refresh` |
| Desktop bundle ID | `com.openai.codex` | `com.openai.codex` | `no change` |
| App-server V2 schema files | 236 | 236 | `no change` |
| `ClientRequest` `oneOf` methods | 90 | 90 | `no change` |

The unchanged app-server counts do not prove that every schema byte is
unchanged. They do show that this refresh found no count-level expansion in
that separately generated contract.

App-server remains a separate JSON-RPC contract family. Its request, response,
error, authentication, and transport envelopes are not Desktop app-tool
envelopes.

## Desktop Callable Comparison

The callable contract version remains unavailable. The current active callable
schema and the read-only schema-version-2 results are the capability sources.

| Callable | Current minimum request and response evidence | Action class | Result |
| --- | --- | --- | --- |
| `list_projects` | No request fields. The observed response has `schemaVersion: 2` and project entries with `projectId`, `projectKind`, `hostId`, and `isGitRepository` where applicable. | read-only | `docs/test evidence refresh` |
| `create_thread` | Requires `prompt` and a `project`, `projectless`, or `chatgptWorkCloud` target. Project targets require `projectId` plus local/worktree `environment`; `title`, `model`, and `thinking` are optional. Ready creation returns `threadId` and `hostId`; queued worktree setup returns `clientThreadId`. | runtime-state-changing | `Desktop adapter change` |
| `fork_thread` | `threadId` and same-directory/worktree `environment` are optional; there is no caller-supplied `hostId`. Same-directory fork returns a child `threadId`; queued worktree setup returns `clientThreadId`. The current response does not guarantee `hostId`; the source task anchors the host and completed history only is copied. | runtime-state-changing | `Desktop adapter change` |
| `list_threads` | Optional `limit`. The observed response has `schemaVersion: 2`, an untrusted-data notice, `threads`, `unavailableHosts`, and `unavailableSources`; each observed thread carries backing `kind`, `id`, `hostId`, and lifecycle/display metadata. | read-only | `docs/test evidence refresh` |
| `read_thread` | Requires `threadId`; supports `hostId`, `cursor`, `turnLimit`, `includeOutputs`, and `maxOutputCharsPerItem`. | read-only | `no change` |
| `wait_threads` | Requires one to eight targets with `threadId`, optional `hostId` and `afterCursor`, plus optional `timeoutMs`. Commentary does not wake the wait; per-target failures are returned in `errors`. | read-only observation | `no change` |
| `send_message_to_thread` | Requires `threadId` and `prompt`; supports `hostId`, `model`, and `thinking`. | runtime-state-changing | `no change` |
| `handoff_thread` | Requires another `threadId`; supports `destinationHostId` and `followUpPrompt`. Returns `operationId` and revision; may interrupt a running task and does not support cloud handoff. | runtime-state-changing | `no change` |
| `get_handoff_status` | Requires `operationId`; supports `afterRevision` and `waitMs` from 0 to 60000. | read-only observation | `no change` |
| `set_thread_title` | Requires `title`; optional `threadId` defaults to the calling task. | runtime-state-changing | `no change` |
| `set_thread_pinned` | Requires `threadId` and `pinned`. | runtime-state-changing | `no change` |
| `set_thread_archived` | Requires `archived`; optional `threadId` and `hostId`. | runtime-state-changing | `no change` |
| `navigate_to_codex_page` | Requires `threadId`. The callable is for an explicit user request to open or show a task or chat. | Desktop UI-state-changing | `Desktop adapter change` |

Except for the identifiers and operation/status fields stated in the table,
the current callable descriptions do not publish stable structured success
envelopes. They also do not publish a stable structured error union for most
app tools or expose caller-supplied authentication fields. Callers must
validate and preserve runtime-provided results without inventing a portable
shape, treat host/source failures as capability or routing evidence, and apply
repository and runtime authorization to the exact action. Capability presence
is not authority.

Official Remote connections guidance confirms that a remote project chat runs
against the remote host's filesystem and shell, and that users may switch
between connected hosts. The Desktop adapter must therefore preserve host
identity even though `hostId` is optional in some follow-up request schemas.
For project creation, select the exact `list_projects` record together with its
host identity, pass that record's `projectId`, and preserve the ready result's
returned `hostId`. For a fork, retain a known source host and resolve the child
task's runtime-returned `hostId` through `list_threads` or another supported
registry result that explicitly exposes it before a host-sensitive follow-up.
Do not invent a local host when a remote child cannot be resolved. Moving a
task to another host remains a separately authorized `handoff_thread` action
using `destinationHostId`.

The earlier 2026-07-30 evidence said `list_threads` returned pinned threads
separately in UI order. The current callable description and observed
schema-version-2 result do not expose that as a stable response guarantee.
Current adapters must treat pinning as sidebar placement only and must not
depend on a pinned/non-pinned response partition.

## Creation, Registration, Navigation, And Visibility

The current Desktop task surface requires these states to remain distinct:

1. **Dispatch:** a ready creation returns `threadId` plus `hostId`; queued
   worktree setup returns `clientThreadId`.
2. **UI registration directive:** after a successful `create_thread`, the
   caller emits `::created-thread{threadId="..."}` for a ready task or
   `::created-thread{clientThreadId="..."}` for queued setup.
3. **Registry observation:** `list_threads`, `read_thread`, or a bounded
   `wait_threads` call can observe an exact ready `threadId`.
4. **Navigation:** only an explicit request to open or show the task authorizes
   `navigate_to_codex_page`. The directive does not itself navigate.
5. **Sidebar visibility:** registry observation, navigation, pinning, and the
   creation directive do not prove that the sidebar has rendered the task.
6. **Completion:** no Desktop lifecycle or UI state proves repository work
   complete.

A stale or unverified sidebar must never trigger duplicate creation. Pinning
only changes where a project or chat appears. Supported manual recovery is chat
search, the Chronological sidebar filter, and the Archived chats check. The
official `codex://threads/<threadId>` deep link is a fallback for a local chat;
it must not be generalized to remote or ChatGPT-backed tasks without current
evidence. No repository adapter may force a sidebar refresh through private
runtime state.

The controlled build-6067 live tests confirmed:

- the ready `create_thread`/exact-ID wait/directive/sidebar path for an
  explicitly `projectless` task, whose ungrouped sidebar placement was correct
  for that target; and
- a same-directory fork from the current project task, where `fork_thread`
  returned only the child `threadId`, `list_threads` resolved the child to the
  source task's `local` host and identical checkout path, and no new worktree or
  follow-up execution occurred.

They did not verify fresh same-project creation, remote/SSH execution, or
cross-host handoff. Current adapter selection must therefore distinguish:

- same-task continuation: `fork_thread` with `same-directory`, with the source
  task stopped before the child writes in the shared directory; the source
  task anchors the host, and the child's `hostId` must be retained or resolved
  from supported registry evidence before host-sensitive follow-up;
- fresh same-project checkout: exact `projectId` plus `local`;
- fresh isolated work: exact `projectId` plus `worktree`;
- intentionally non-project work: `projectless`.

No callable field automatically converts a projectless request into the
calling task's project.

## CLI Public Session Control

CLI remains `0.146.0`, so it is still the version control group. Independent
public help and official documentation nevertheless show an adapter-relevant
surface omitted from the earlier conclusion:

- `codex resume <SESSION_ID>` continues a saved interactive session;
- `codex fork <SESSION_ID>` creates a new interactive chat from a saved
  session;
- `tui.resume_cwd = "current" | "session"` selects the invocation or saved
  session directory when they differ, while an unset value prompts;
- public `-C <DIR>` selects an invocation working root.

The repo-owned non-interactive executor still supports only
`codex exec --json` start and `codex exec resume <SESSION_ID> --json` in its
private clone. The adapter change is a separately classified paste-ready
manual interactive-fork path using an exact UUID and explicit directory
choice. It does not automate the TUI, read private session state, or create a
Git worktree.

## Layering Decision

- Desktop skills remain thin adapters over the shared workflow contract.
- `Desktop adapter change`: add the creation directive, exact identifier
  handling, same-directory/same-project/worktree/projectless target selection,
  post-create registry/visibility separation, duplicate-creation guard, and
  explicit navigation plus public fallback behavior to
  `desktop-thread-delegation`.
- `docs/test evidence refresh`: update maintained Desktop capability,
  compatibility, example, README, and focused contract-test evidence.
- `shared contract candidate`: none. Task selection, implementation,
  verification, review, shared subagents, and completion do not change.
- `CLI adapter change`: CLI `0.146.0` is version-unchanged, but public
  `codex fork` and `tui.resume_cwd` evidence requires a bounded manual
  interactive-fork path in `cli-session-handoff`. No Desktop identifier or UI
  behavior moves into that adapter, and its non-interactive executor remains
  unchanged.
- `requires human decision`: any additional live Desktop runtime mutation and
  any further GitHub Issue update remain separate external-action gates.

## Re-runnable Checks

```bash
/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' \
  /Applications/ChatGPT.app/Contents/Info.plist
/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' \
  /Applications/ChatGPT.app/Contents/Info.plist
/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' \
  /Applications/ChatGPT.app/Contents/Info.plist
codex --version
codex exec --help
codex exec resume --help
codex resume --help
codex fork --help
codex app --help
codex app-server generate-json-schema --out <temp-dir>
find <temp-dir>/v2 -type f -name '*.json' | wc -l
jq '.oneOf | length' <temp-dir>/ClientRequest.json
```

Desktop callables must still be re-read at the actual call site. This evidence
does not authorize a live Desktop task action or a GitHub write.
