# Runtime Compatibility

This repository uses four compatibility labels.

In current product naming, the Desktop control surface runs inside the ChatGPT
desktop app. This repository keeps `Codex Desktop` and `desktop` as stable
compatibility labels for Codex task, thread, worktree, UI, and scheduling
controls. The labels do not imply that shared reasoning or subagent delegation
is Desktop-only.

[2026-10-17 compatibility evidence](codex-runtime-compatibility-evidence-2026-10-17.md)
分開查核新版 CLI、Desktop app 與 bundled CLI。兩個 CLI 的 parser／production
argv 檢查通過，沒有新增 live lifecycle 資格。GitNexus operator CLI 仍選 1.6.9；
新增獨立的 1.6.12 本機 library profile 與 controller 採用流程；A02 已驗收
接受的本機安裝之有限索引寫入整合，保留 worker baseline exception 紀錄。
A01 僅證明原有界初次建立；缺匹配證據時沿用原始碼／Git fallback。
The update audit preserves separate entrypoints and the shared layer. Its
help/schema evidence does not qualify sessions or activate optional integration.

[2026-10-14 compatibility evidence](codex-runtime-compatibility-evidence-2026-10-14.md)
修正 Desktop 排序別名／允許值及共享 sandbox 證據：custom agent 繼承 parent
權限，profile 的唯讀 expectation 不代表獨立技術隔離。CLI 入口與 Desktop
薄層控制面保持分開；同案評估不直接發行包含其他未發布候選的小版本。
[2026-10-01 compatibility evidence](codex-runtime-compatibility-evidence-2026-10-01.md)
補齊 Desktop sidebar 的 `orbit`（Your dot）heading 指引；CLI 獨立入口、
Desktop thread／worktree 入口與共享編排保持原契約。此文件補齊的發行評估
記錄於同一 Issue，未準備新版候選。
[2026-09-29 compatibility evidence](codex-runtime-compatibility-evidence-2026-09-29.md)
修正 Desktop local/worktree 選路、非同步工作樹建立與 fork 中斷回合語意；共享
編排依使用者偏好及隔離需求選擇 checkout，CLI private-clone 邊界保持不變。
先前的 [2026-09-25 compatibility evidence](codex-runtime-compatibility-evidence-2026-09-25.md)
補上 Desktop sidebar 排序偏好與單一 surface 分組的按需契約；CLI executor
及共享編排／完成語意維持不變。前次
[2026-09-24 compatibility evidence](codex-runtime-compatibility-evidence-2026-09-24.md)
補齊 Desktop 混合來源的 source／host 分流與指定其他任務面板的 queued 語意；
CLI／Desktop 入口及共享完成契約維持獨立分層。前次
[2026-09-19 compatibility evidence](codex-runtime-compatibility-evidence-2026-09-19.md)
記錄 sidebar 內建 headings 排序與目前任務 `create_worktree` 的契約補充；
CLI executor 及共享完成語意維持不變。
[2026-09-17 compatibility evidence](codex-runtime-compatibility-evidence-2026-09-17.md)
分開記錄 standalone CLI、Desktop application 與 Desktop-bundled CLI，核對
原生工具契約與唯讀 registry 回傳，沒有發現需要改動入口或共享架構的差異。
前次 [2026-09-16 紀錄](codex-runtime-compatibility-evidence-2026-09-16.md) 仍保留
其點時角色。The active
`desktop-sidebar-organization` skill implements a separate thin mutation
contract without collapsing the CLI and Desktop entry paths, and preserves the
distinction between the legacy
`codex mcp-server`, Codex's MCP client configuration, connectors, plugins, and
native Desktop task/thread tools. 在 9 月 17 日觀測的 standalone CLI 0.154.0
與 bundled CLI 0.155.0-alpha.2.6 中，該 server command 的 help 只回傳 root
usage，不能當作 subcommand 仍受支援。更早的 bundled 0.153.4 與 live session
結果保留於 2026-09-11 紀錄；本次 help／schema 檢查不代表 live qualification。

Thread 控制先依 [Thread Capability Discovery](native-runtime-capabilities.md#thread-capability-discovery)
辨識 Desktop 本機、Desktop 遠端、CLI/TUI 入口，完成正式清單與 deferred
搜尋，記錄完整 namespace/schema；不可觀察時保留 unknown。不能以 OS、SSH、
basename 或技能已安裝推定工具存在。

## `shared`

Works in Codex CLI, Codex Desktop, and supported IDE surfaces through repository
files, ordinary shell commands, git inspection, native Goal mode, and bounded
subagent delegation when those capabilities are available.

## `cli`

Designed primarily for Codex CLI. A Desktop user may still follow the workflow
manually, but the skill must document the fallback.

`cli-session-handoff` is the thin CLI control-plane adapter for one bounded,
explicitly authorized `codex exec --json` start, exact-UUID resume/fork, or
clean non-interactive fresh continuation. It is
separate from shared task selection/subagents and from Desktop task/thread
callables. Its redacted receipt is coordination evidence, not completion
authority. Its disposable private clone does not inherit the source checkout's
activated Python environment, so it must follow the repository's tracked
environment resolver when present and fail verification closed on a version or
dependency mismatch.

CLI source checkout 可依偏好及隔離需求選 local 或既有 worktree；新對話本身
不要求新增工作樹。這與子程序的 mandatory private clone 分開；Desktop
`create_thread` 的 worktree 意圖限制不套到 CLI payload 或一般 Git 操作。

Fresh continuation is not a fork: it starts without copied conversation
history and requires the shared durable checkpoint. Interactive or dirty CLI
rollover degrades to a manual/current-session prompt without claiming success.

CLI `/plugins`, `/import`, and `/memories` are runtime configuration and
personalization controls. They are not `cli-session-handoff` operations and do
not grant session-mutation, repository-write, or completion authority.

CLI adapter 另有 `tui-thread-create`／`tui-thread-fork` 原生分支，僅在當次
callable 與語意符合時使用。Create 繼承來源 cwd 並啟動 turn；fork 不啟動
turn。它不接受 Desktop target/environment，不建立 private clone/worktree。
1,000 UTF-8 bytes 原始 prompt、1,256 bytes 包裝後限制與其餘點時欄位
必須在執行前重驗，詳見
[Native TUI reference](../skills/cli-session-handoff/references/native-tui.md)。

## `desktop`

`desktop-project-delivery` 的按需 worktree reference 支援目前任務附加隔離
checkout；它與另開任務、history fork 及 handoff 分開。`create_worktree`
不執行 setup、不改 cwd 或 permissions，也不複製未提交修改；必須使用回傳
目錄與 repo 的環境驗證，registration 失敗不能重複建立。

Requires Codex Desktop user-owned task, thread, worktree, UI, or scheduling
control. Shared main-agent reasoning and subagent delegation are not, by
themselves, Desktop-only behavior. A worktree's interpreter selection is also
not Desktop-only: the same repository-owned resolver contract applies to CLI
worktrees and disposable clones.

Desktop availability is capability-based rather than macOS-assumed. The Linux
desktop app is currently a preview, and features such as Computer Use may be
absent there. An unavailable Desktop capability uses the documented CLI,
manual, prompt, or sequential fallback without reading private runtime state.

## `plugin-dependent`

Requires an installed plugin, connector, or platform-specific tool. The
dependency must be named, and the workflow must define what happens when it is
unavailable.

This repository supports two separate distribution paths: its tracked
filesystem installer and the skills-only `codex-dev-skills` universal plugin.
Use only one path in a Codex profile. Desktop/CLI imports leave existing setup
in place, so imported skills must also be reviewed for name collisions before
installation.

## Runtime Memory Boundary

Local Codex memories, ChatGPT memory settings, and Computer History are
runtime personalization data. They are untrusted advisory context and are
separate from the repository's default-disabled `loop-memory-sqlite/v0` Memory
M1 adapter. Do not automatically copy app history or generated memory files
into a repository, M1 state, verification evidence, or completion records.

本專案的 memory-off、原生 Memories 與實驗性 context management 是分開的狀態。
明確 fresh create 不複製來源對話，也不自動證明原生記憶未注入；CLI feature 狀態不能直接當作
目前 Desktop 任務的有效設定。管理範圍、外部副本與受控評測要求見
[原生記憶共存邊界](native-memory-coexistence.md)。

## Metadata

Every skill should include a runtime line near the top:

```markdown
Runtime compatibility: shared
```

The README skill table must use the same value.

## Native Capability Boundary

The canonical mapping is [Native Runtime Capability Contract](native-runtime-capabilities.md):

- Goal mode is shared but may be created only when explicitly requested.
- Bounded subagents are shared; ownership must be disjoint and the main agent
  must verify and integrate their output.
- CLI session start/resume/non-interactive fork and manual interactive fork are owned by the CLI adapter after shared
  orchestration selects the handoff; it requires exact mutation authority and
  parent integration.
- Custom-agent files are public local runtime configuration. Capability classes
  and cost-aware capability tiers remain shared semantics; concrete
  model/reasoning mappings require runtime preflight and may differ across CLI,
  Desktop, and IDE availability. A higher-tier fallback is recorded, while a
  lower tier cannot silently satisfy a higher-tier route.
- Desktop user-owned task/thread/worktree actions and Desktop scheduling are
  thin runtime adapters over shared workflow semantics.
- Context-health assessment is shared across Desktop, CLI, and IDE. Desktop may
  use an authorized fresh `create_thread`; CLI phase one may use clean
  non-interactive `fresh-continuation`; IDE assumes no independent task control
  plane and uses current-session or prompt fallback.
- Hooks are optional guardrails, not complete enforcement.
- Goal, subagent, scheduler, hook, and thread state are coordination evidence;
  they do not prove repository completion.

When a capability is unavailable, preserve the same objective, authority,
verification, review, and human-gate rules through the current session,
sequential execution, a task brief, or a paste-ready continuation prompt.

The complete five-outcome contract, capability matrix, migration notes, and
cost/quality comparison are in
[Context Continuity And Fresh-Context Rollover](context-continuity.md).

Absence of the custom-agent surface preserves V1 sequential/shared semantics.
It must not be reported as task completion or as a permanent Goal failure.

Absence of an external-memory adapter likewise preserves V1/V2a behavior. V2b
validation is shared and offline. A concrete adapter is plugin-dependent and
must declare its actual capabilities; unavailable or incompatible operations
are disabled rather than simulated.

## GitNexus Adapter Boundary

The V2c-A GitNexus driver is shared Python code around a machine-local external
CLI. Executable discovery/configuration must work in Codex Desktop on macOS and
Codex CLI on Linux without committing an executable path, `GITNEXUS_HOME`,
registry, index, database, credential, or other machine-local state. The adapter
is disabled until the runtime explicitly supplies and qualifies that local
configuration.

The shared operator surface is
`skills/loop-engineering/scripts/gitnexus_adapter.py`. Its `qualify`, `status`,
`refresh`, and `disable` subcommands use only machine-local arguments and emit
redacted JSON. The adapter stores no enable bit: `--enabled` is a per-invocation
opt-in, and refresh also requires `--confirm-explicit-refresh`. This identical
control boundary is intended for Desktop/macOS and CLI/Linux; only macOS arm64
has live GitNexus evidence in V2c-A.

The runtime control plane must also provide a canonical package root and
caller-owned accepted SHA-256 values for the entry, complete package tree, and
bound interpreter when present. The adapter checks them before invoking the
tool and rechecks the package tree at use time. These values are machine-local
configuration and must not be committed.

GitNexus 1.6.9 has live macOS arm64 qualification for executable discovery,
required flags, schema-5 metadata, isolated offline index-only refresh, and
tracked/Git-control postconditions. Linux has portability fixtures for POSIX
paths, regular-file/symlink policy, subprocess argv/environment, timeout/lock,
and metadata handling, but no live GitNexus qualification. Do not present those
fixtures as Linux runtime evidence.

The existing operator CLI still selects 1.6.9. For explicit local 1.6.12 writes,
`qualify_local_1612` is a separate library entry. It reuses caller-accepted
version/help receipts without launching probes, and binds entry, actual Node,
complete package tree, accepted runner identity, an independently read dependency
closure and an explicit caller-owned coverage set. Runtime packages must stay
inside the package tree; directory links, external dependency fallbacks and
changes to nearest-lockfile resolution are refused. No npm download or publisher
signature is required or claimed. Private accepted values must stay outside Git.

The existing controller can then perform an initial or revision-changing
`analyze --index-only --no-parse-cache --name <alias> <root>`. The fixed upstream
flag forces a full rebuild without trusting old parser output. A new private
HOME contains registry/tmp/identity cache. Exact coverage paths and source
hashes, metadata mirrors, local identity, registry, complete content/Git-control
postconditions and sidecar readback must pass before adoption. Same-HEAD refresh
and invalid existing metadata are refused. Any repository `.gitnexusrc` entry,
including ignored files and links, is refused before execution and rechecked
immediately before launch; its embeddings and other execution settings are
outside this profile. Keep the source stable throughout execution. The versioned metadata digest and
qualification fingerprint keep old sidecars separate; automatic eligibility is
false. Without this local profile, new metadata remains unsupported.

The local profile supports limited local index writes for the
accepted GitNexus 1.6.12/Node 25.9.0 installation on macOS arm64. A02 exercised
the actual controller once: a fixture commit made the old index stale; refresh
and metadata/registry/sidecar validation, including the controller's final
freshness check, succeeded. The outer worker stopped on an earlier Git index
stat-cache baseline mismatch; file-only reconciliation found only cached ctime
changes, with staged content unchanged. Its exception remains recorded and its
optional second freshness API was not run. This acceptance covers our adapter
usage, not upstream algorithm correctness. A01 covered the initial build with
no embeddings and unavailable offline FTS. The fixed-source DDL
fingerprint is `60fc01e4e4ed`, not an actual DB inspection. A03/same-HEAD and
A04/real forced timeout are deferred. Query, impact, read_query, MCP, Linux,
Grok and general concurrency remain unqualified. No RSS observation or RAM
hard cap is claimed. The single A02 authorization is spent: cumulative calls are
6/13, with no further live calls authorized. New tool/Node/package/dependency
bytes require renewed local acceptance and affected integration qualification.

既有 operator CLI 仍選 1.6.9；新版明確本機操作使用獨立的
`qualify_local_1612` library 入口，重用接受的 version/help 證據，不啟動 probes。
它綁 entry、實際 Node、完整 package tree、接受的 runner、獨立相依解析與
caller 明定 coverage；拒絕外部相依、目錄 links、外部 fallback 與較近 lockfile 漂移。
不下載 npm、不宣稱發行者簽章，私人接受值不進 Git。

既有 controller 使用 `--index-only --no-parse-cache` 完整重建，隔離新 HOME、
registry、tmp 與 identity cache；逐檔、metadata、registry、完整 Git/content
postconditions 及分版 sidecar 通過才採用。同 HEAD／損壞既有 metadata 會停止；
執行前及啟動前重驗並拒絕任何 `.gitnexusrc` entry（含 ignored 檔與 links），
其 embeddings 等執行設定不在本 profile 內；操作全程仍須維持來源穩定。
automatic eligibility 固定 false，無本機 profile 時新版仍 unsupported。
本候選已支援接受的 GitNexus 1.6.12／Node 25.9.0、macOS arm64 有限本機索引
寫入整合。A02 以單檔 commit 驗證舊索引失效，實際 controller 更新、檢核
metadata／registry／sidecar 與內部 final freshness。外層 worker 因較早的 Git
index stat-cache baseline 差異停止；離線讀回僅 cached ctime 變動，staged 內容
不變，原 exception 保留，外層第二次 freshness API 未執行。驗收對象是我方
adapter 的正確使用流程。A01 涵蓋初次建立；
A03／A04 延後，query／MCP／Linux／Grok／一般並行未資格化，沒有 RSS／RAM
硬上限保證。累計呼叫為 6/13，單次 A02 授權已用完，沒有追加 live 授權；
更新 tool／Node／package／相依 bytes 後須重新接受本機身分及驗證受影響整合。

The current orchestrator decides when to query/update and assigns one index
writer for the actual checkout and shared storage/cache boundary. Coordinate
stable source and reader ownership before refresh, then verify and hand off
identity, content freshness and coverage before queries resume. Codex/Grok
feature parity is the target; implementation may differ and Codex is not the
permanent index manager. Current evidence does not qualify read_query/MCP or
Grok entrypoints. The smallest follow-up is Grok's own bounded adapter/entry
qualification for the same index-write usage workflow; this is necessary for
cross-overlay parity and does not require upstream feature QA. A shared pure contract
is needed only if both overlays reveal a real common gap; keep platform-specific
GitNexus details outside Core. See [repository coordination](../CONTRIBUTING.md#索引協作與編排責任--index-coordination).

當次編排方決定查詢／更新時機與操作者，每個共享索引邊界只有一位 writer；
先協調穩定來源及 reader，再驗證並交接。Codex／Grok 功能對等是後續目標，
不是已完成資格，也不固定 Codex 為永久管理者。最小後續為 Grok 自身有界入口／
adapter 驗證；只有兩端 overlay 顯示實際共通缺口時才考慮 shared 純契約，
不把 GitNexus 平台細節寫入 Core。本次 Core 不改、不另啟跨平台 query 或新框架。

Refresh is supported only where the controller can prove the direct worktree
and Git administrative boundary, including a pre-existing `.git/info/exclude`
entry and stable `.git/info/exclude`, `.git/config`, and `.git/HEAD` digests.
Linked-worktree or ambiguous Git administrative layouts fail closed rather than
guessing a path. Human `status`/`list` output is never parsed. `read_query` and
all backend write operations remain unsupported in this baseline, regardless of
whether the executable exposes additional unqualified surfaces.

## GitNexus Hook Boundary

The V2c-B hook runner is shared Python code intended for the current Codex CLI
and desktop hook contract on POSIX hosts. It uses only documented
`SessionStart` and `PostToolUse` JSON fields for `Bash` and `apply_patch`. The
current live evidence does not provide a native `post-commit` event or complete
tool interception, so these paths are best-effort freshness signals and
`SessionStart` is the compensating check. Codex supports background command
hooks, but this runner remains synchronous because background invocations may
overlap, finish out of order, or be cancelled with the session.

Project hooks load only for trusted projects and non-managed command hooks must
be reviewed and trusted. Templates are installed inertly; neither CLI nor
Desktop installation activates a hook or writes runtime config. Hooks disabled,
unavailable, skipped, or unsupported leave V2c-A and the no-backend workflow
unchanged. Controller failure installs a repository-bound machine-local circuit
breaker so later events cannot retry automatically without operator clearance.
Windows command/runtime behavior is not qualified in this increment; the
runner fails safe outside POSIX rather than claiming portability.

## Desktop Thread And Task Actions

Use only the documented callable exposed by the active runtime. Before an
action, verify:

- exact action and target identity;
- request and response fields used by the call;
- whether the action is read-only or state-changing;
- runtime/tool contract version, or `version unavailable` plus the capability
  source and `last_verified` date;
- permission and authentication failure handling;
- the user authorization required for that exact action.

For example, current Desktop task creation returns a `threadId` for immediate
creation or a queued `clientThreadId`. Treat those as different lifecycle
signals and validate the actual response before relying on it. Do not infer a
callable from private Desktop state, UI scraping, local databases, logs,
sessions, or caches.

Creating, forking, messaging, archiving, pinning, or otherwise mutating a
user-owned Desktop task requires the authority specified by the active runtime
and repository policy. A CLI fallback may prepare the same prompt or task brief
but must not claim to control Desktop tasks.

Creating an immutable Desktop thread-share link is additionally a
privacy-sensitive disclosure. Require explicit user intent, exact thread and
audience preview from public product context, and user-confirmed review of the
complete thread before `share_thread`; recent, truncated, or paginated reads
are insufficient by themselves. Runtime
secret-pattern redaction is defense in depth rather than a confidentiality
guarantee. The current callable creates links but does not revoke them; use the
documented ChatGPT data-controls path for review or revocation and keep link
creation, revocation, and repository completion separate.

For the same Desktop task moving to a new conversation, a supported
`fork_thread` same-directory action reuses the source checkout or existing
worktree, copies conversation history that may include an interrupted active
turn, and remains anchored to the source host. Re-read operation results and
writer ownership before continuing; copied history is not completion evidence.
The fork request has no caller-supplied `hostId`, and its current response does
not guarantee one. Preserve a known source host, then obtain the child
`hostId` from supported registry evidence that explicitly exposes it before a
host-sensitive follow-up; never assume an unresolved remote child is local. A
fresh same-project task uses the exact `projectId` and its runtime-returned host
identity. Both Git and non-Git projects default to local. Shared orchestration
selects placement from preferences and isolation needs and explains a departure;
the current `create_thread` callable additionally requires an explicit worktree
request and a Git project for that target. This constraint does not apply to all
CLI/Desktop checkout choices. `projectless` is reserved for intentionally non-project
work. Cross-host continuation is a
separately authorized handoff with `destinationHostId`, not a fork option.

CLI `codex fork <SESSION_ID>` is the analogous CLI-only interactive control
for a new chat from a saved session. Use an exact UUID and an explicit
`tui.resume_cwd` current/session choice when directories differ. The
repo-owned `codex exec` handoff executor remains non-interactive and does not
automate this command.

CLI `codex agents` is a separate interactive session dashboard. Its observation
states do not prove repository completion, and each selected start/open/rename/
stop action retains its own mutation authority. CLI `codex queue` may be
prepared manually only for an exact canonical UUID and one bounded nonsensitive
message represented as one argv token without shell interpolation. Queue
acceptance is dispatch/wakeup evidence, not proof that the
destination processed the message. Neither command is routed through the
private-clone executor. `codex doctor --json` remains redacted diagnostics only.

After a successful `create_thread`, the Desktop adapter must emit the
runtime-provided created-task UI directive with the returned `threadId`, or
with `clientThreadId` while worktree setup is queued. The identifier types are
not interchangeable. Dispatch, the UI registration directive, exact-ID
registry observation, navigation, sidebar rendering, and repository completion
remain separate states.

Use an exposed navigation callable only when the user explicitly asks to open
or show the task. If it is unavailable or fails, provide the official chat
search and sidebar filter/archive checks; a `codex://threads/<threadId>` deep
link is limited to a local chat. Pinning changes sidebar placement rather than
task registration, and a stale sidebar must never cause duplicate creation or
private-state refresh attempts.

`list_threads`, `read_thread`, and `wait_threads` are observation and
coordination operations when the active callable schema classifies them that
way. A bounded wait may return compact progress for multiple tasks, but it is
not repository completion evidence and does not replace detailed reads,
integration checks, verification, or review.

Sidebar organization is a separate Desktop-only control plane. The
`desktop-sidebar-organization` skill uses fresh discovery from only the needed
`list_threads` or `list_projects` registry, exact runtime IDs, a dry-run plan,
action-specific authorization, response validation, and post-mutation
readback. It fails closed rather than guessing from display names, stale or
partial snapshots, or queued `clientThreadId` values. A concrete reversible
create/rename/move/reorder request remains authorized after unambiguous identity
resolution; complete-list membership must still match. Delete retains its
destructive gate, and changed scope or ambiguous effects require a decision.
CLI fallback is an exact manual plan, not a live
sidebar mutation.

## Evidence

Runtime evidence should record the command or callable, target, relevant input
shape, result or error classification, source runtime, and verification date.
Repository completion still requires current files, git state, verification,
review, and accepted platform state where applicable.

## Retired V1 Historical Context

Desktop Runtime Wrapper V1 is retired and is not an active compatibility
boundary. Its [retirement record](desktop-runtime-wrapper-v1-deprecation.md)
and [historical plan](desktop-runtime-wrapper-v1-plan.md) are non-executable
context only. They do not define a runnable or importable integration path.

Current callable schemas and call-site validation are authoritative. Historical
response shapes must not override validation of the requested action, target,
permission or authentication outcome, returned identity, or status. Native
runtime contracts retain the fail-closed, private-state, external-write, and
non-execution boundaries.

## Safety Boundary

No compatibility label authorizes commit, push, PR creation, merge, deploy,
platform comments, review submission, destructive action, or another external
write. Those actions remain behind exact user authority and the applicable
human gate.
