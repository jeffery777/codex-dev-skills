# app-server 工具註冊與設定對帳設計

原 Issue #316 N2 的工程清冊；後續驗收由
[Issue #323](https://github.com/jeffery777/codex-dev-skills/issues/323) 追蹤。
此文件用固定公開 source 定義待對帳的 contributor、
設定條件與收據欄位，不保存執行證據，不宣稱完整 registry 或 production 資格。
Runtime 收據與原始輸出留在 Git 外；重跑須重建等價 assertions。

範圍固定為 `openai/codex@01fc69f4026735edfdf6789820549727a4867b11`
的 `codex app-server --stdio`。Source 事實不推定 bundled CLI、Desktop 或其他版本。
相關隔離要求見[主設計](isolated-model-execution.md)，現行交付範圍見
[Issue #323](https://github.com/jeffery777/codex-dev-skills/issues/323)。

## 工具組裝與觀察界線

固定 source 的組裝順序為 core、MCP/cache 與 exposure policy、extension
`tools_for_step`、DynamicTools、hosted specs，最後 finalize。每個 contributor
的啟用條件、exposure、schema 與 dispatch 須分開記錄。
[組裝入口](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/spec_plan.rs#L150-L187)。

`omit_tools_from` 可令 MCP 工具成為 Hidden、CodeModeOnly、DeferredModelOnly 或
Deferred；Hidden 仍保留 dispatch。Extension tools 初始 exposure 預設 Direct，
仍須通過 host policy 與 finalization。不能把初始 advertisement、namespace
清單或 `environments: []` 當成完整 handler 封閉。
[exposure policy](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/spec_plan.rs#L197-L268)、
[extension exposure](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/tools/src/tool_executor.rs#L51-L115)。

公開 `config/read`、feature list 與 MCP status 各有自己的讀取範圍；它們不能
直接證明既有 thread／turn／step 的 immutable registry。清冊依欄位區分
`source-derived`、`observed`、`unknown`，未取得當次證據的欄位不得補成 false。
以下列出 source 的入口條件，並非建議部署設定。

## app-server extension contributors

下表覆蓋固定 source 的 `thread_extensions` 安裝入口；「安裝」與「工具註冊」
分開。`R` 表示須核對 effective config/layers、requirements 與 features；
`A` 表示 auth 類型與 provider；`M` 表示 MCP inventory；`U` 表示尚未找到
足以證明當前 thread／step registry 的公開讀回。本文件不執行這些 RPC。
[安裝入口](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/app-server/src/extensions.rs#L68-L119)。

| Contributor | 工具或行為及 source 條件 | 必要對帳／未知 |
| --- | --- | --- |
| turn admission | 無工具；由注入的 dependency 提供 admission。 | U；不能由 tools 清單推定不存在。 |
| queue | 無工具；有 queue service 時安裝 lifecycle 與 external-message watcher。 | U；service 狀態另核對。 |
| history-notes | `history.{list_windows,list_items,read_item,search_contents}`、`notes.{list_files_by_prefix,read_file,search_contents,append_to_file,write_file}`；DirectModelOnly；須 history-notes config、OpenAI provider、Codex-backend auth 及 agent identity。 | R+A+U；匿名未註冊不能沿用至登入後。 |
| agent-message-board | `<multi_agent_v2.tool_namespace>.{create_channel,get_channels,list_threads,search_posts,read_thread,read_post,subscribe,unsubscribe,post}`；須 `agent_message_board` 與 `multi_agent_v2` features；ephemeral 時另須 in-memory。 | R+U；須解析實際 namespace。 |
| goal | `get_goal/create_goal/update_goal`；須 state DB、goals feature 及 runtime tools-visible。 | R+U。 |
| git-attribution | 無工具；prompt contributor；Codex-backend auth 可觸發 settings HTTP。 | A+U；未找到一般關閉 flag，不由無工具推定無網路。 |
| guardian-v2 | 無直接工具；approval、skill/tool lifecycle 及內部 reviewer thread。Async 受 guardian feature、model policy、requirements 約束；sync reviewer 是另一條路。 | R+A+U；不能為了封閉而弱化審批。 |
| memories | `memories.{add_ad_hoc_note,list,read,search}`；須 memories feature、`memories.use_memories` 與 `memories.dedicated_tools`。 | R+U；不得只檢查一個 feature。 |
| mcp | 間接提供 `codex_apps` server 工具；apps feature 關閉只移除此 server。 | R+A+M；普通 configured MCP 不因此消失；names 依當次 catalog。 |
| plugins | 間接 MCP 工具；此入口為 executor provider、cloud=None。Plugins feature 關閉可清空 plugin MCP servers。 | R+selected roots+M；不能推定所有 metadata/discovery 已停止。 |
| web-search | `web.run`；provider/auth 能力、web mode，再經 standalone/provider/model 條件；另有 hosted web-search 分支。 | R+A+U；extension 與 hosted 路徑分列。 |
| image-generation | `image_gen.imagegen`；feature、非 Free、provider namespace/image 能力、image modality、actor 或 Codex-backend auth。 | R+A+U；登入類型是 guard 之一。 |
| skills | `skills.list/read`；此入口包含 Host 與 Executor、無 Cloud provider；工具須 resolved executor roots。Host 本身不提供這兩個工具，但參與 discovery/prompt。 | R+roots+U；工具與 discovery 分列。 |

逐項 source：

- [turn admission](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/extension-api/src/turn_admission.rs#L3-L11)、[queue](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/queue/src/lib.rs#L14-L20)。
- [history-notes guards](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/history-notes/src/extension.rs#L46-L65)、[tools](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/history-notes/src/tools.rs#L71-L81)。
- [message-board guards](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/agent_message_board.rs#L43-L64)、[goal](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/goal/src/runtime.rs#L126-L131)。
- [git-attribution](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/git-attribution/src/lib.rs#L98-L108)、[guardian async](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/guardian-v2/src/async_scorer/extension.rs#L47-L102)、[guardian sync](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/guardian-v2/src/sync_reviewer/mod.rs#L43-L100)。
- [memories](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/memories/src/extension.rs#L45-L52)、[mcp](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/mcp/src/lib.rs#L36-L67)、[plugins](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/mcp/src/plugin.rs#L155-L247)。
- [web-search](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/web-search/src/extension.rs#L42-L54)、[image guards](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/spec_plan.rs#L727-L762)、[skills sources](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/skills/src/sources.rs#L71-L107)。

工具名稱／provider 建構的直接錨點另列如下，guard 的引文不代替工具定義：

- [message-board tools](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/agent-message-board/src/tools/spec.rs#L10-L20)、[goal tools](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/goal/src/spec.rs#L9-L25)。
- [memories names](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/memories/src/lib.rs#L18-L22)、[memory tool construction](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/memories/src/tools/mod.rs#L28-L76)、[plugin provider](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/mcp/src/plugin_providers.rs#L15-L20)。
- [web tool name](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/web-search/src/tool.rs#L41-L56)、[web tool assembly](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/spec_plan.rs#L622-L650)、[skills tools](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/skills/src/tools/mod.rs#L68-L95)。
- [skills list](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/skills/src/tools/list.rs#L31-L73)、[skills read](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/skills/src/tools/read.rs#L34-L65)。

## Core handlers 與 generated contributors

下表覆蓋固定 source 的 core registration 分支，所有列仍有 U。`E` 表示 thread
environments／environment status，`L` 表示 model/list 與 provider capabilities；
L 不提供完整 tool_mode／experimental tools metadata，provider capabilities 也不
是不可變的 thread 快照。未另列 namespace 者是 `functions`；D＝Direct、
DM＝DirectModelOnly、DF＝Deferred。表列是初始 exposure，仍須經後續 policy。
[core registration](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/spec_plan.rs#L1016-L1420)。

| 工具 | Source registration／dispatch 條件 | 初始 exposure／對帳 |
| --- | --- | --- |
| `exec_command`, `write_stdin` | Environment、ShellTool、非 Disabled 的 model shell_type；UnifiedExec true 時兩者存在，false 時仍有 one-shot exec；ToolPolicy 要求 UnifiedExec 時可省略。 | D；R/E/L/U。 |
| `list_mcp_resources`, `list_mcp_resource_templates`, `read_mcp_resource` | MCP binding 有 servers；resource API 另受 `orchestrator.mcp.enabled` 的 codex_apps 限制。 | D；R/M/U。 |
| `update_plan` | `tools.update_plan.enabled`；handler 在 Plan mode 拒絕，其餘送 PlanUpdate。 | D；R/U。 |
| `wait_for_environment` | DeferredExecutor；只等待指定 ready/starting environment，未知／failed 拒絕。 | D；R/E/U。 |
| `request_user_input` | `tools.experimental_request_user_input.enabled`；dispatch 另核 root 與允許的 collaboration mode。 | DM；R/U。 |
| `request_user_input_async` | Root 且 model 宣告此名或舊名 `send_user_message_async`；送 async AgentMessage。 | DM；L/U。 |
| `send_message_to_user_async` | Root 且 feature **或** model 宣告；送 async AgentMessage。 | DM；R/L/U。 |
| `request_permissions` | Environment＋RequestPermissionsTool；正規化後進 permission request。 | D；R/E/U。 |
| `new_context`, `get_context_remaining` | TokenBudget；分別 request_new_context_window 與 token status。 | DM、D；R/U。 |
| `clock.curr_time`, `clock.sleep` | CurrTime 是 CurrentTimeReminder **或** model clock；sleep 是 SleepTool 且 AlwaysOn，或 ModelDriven 的 reminder/model 條件。 | D、DM；R/L/U。 |
| `list_available_plugins_to_install`, `request_plugin_install` | ToolSuggest＋Apps＋Plugins＋非空 candidates；list 另限 ListTool presentation；install dispatch 限 root、送 elicitation。 | D；R/M/U。 |
| `apply_patch` | Environment＋model apply_patch_tool_type；驗證 patch 後進 patch runtime。 | D/freeform；E/L/U。 |
| `test_sync_tool` | Model experimental_supported_tools 包含名稱；handler 執行 barrier/wait。 | D；L/U。 |
| `view_image` | Environment＋ViewImage；dispatch 再查 image modality/environment，經 sandbox filesystem 讀檔。 | D；R/E/L/U。 |
| `multi_agent_v1.{spawn_agent,send_input,resume_agent,wait_agent,close_agent}` | 有效版本 V1、未超 spawn depth；交給 agent_control。 | Search 可用時 DF，否則 D；R/L/U。 |
| V2 namespace 下的 `spawn_agent,send_message,followup_task,wait_agent,interrupt_agent,list_agents` | V2；子 agent 另須 model 宣告 V2；direct-message/wait flags 控制子集；交給 agent_control。 | non_code_mode_only 時 DM，否則 D；R/L/U。 |

V2 namespace 由 config 決定；provider 不支援 namespaces 時用 plain names。
MultiAgentV2 feature 優先於 `agents.enabled=false`，還須核對歷史／model 選擇。
UnifiedExec normalization 可重新啟用 user opt-out；managed requirement pin
可維持 false，但 false 仍保留 one-shot exec。Feature 值不能單獨證明工具已移除。
[agent config](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/config/mod.rs#L1578-L1604)、
[UnifiedExec normalization](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/config/managed_features.rs#L153-L167)。

Core tools 先受 ToolPolicy 的 managed-sandbox ceiling，registry registration
再核 allowed_tools。ToolPolicy 是 host 注入，resume 須重新提供；尚未找到
app-server 公開參數／完整讀回。不得虛構 allowlist flag 或修改管理者設定來放行。
[ToolPolicy](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/extension-api/src/tool_policy.rs#L6-L20)。

## CodeMode 與 DynamicTools

Requested mode 優先採 model tool_mode，再看 CodeModeOnly／CodeMode features。
Requested CodeMode 且 service unavailable、fallback 未禁用時才回 Direct；
CodeModeOnly 不回退。`CodeModeHost || disable_in_process_fallback` 選
ProcessOwned provider，因此「禁 fallback」true 本身可能選 host provider。
Availability 僅檢查 host program 是檔案，不能代替可執行或隔離證明。
[mode selection](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/mod.rs#L75-L96)、
[provider selection](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/thread_manager.rs#L557-L563)。

有效 CodeMode／Only 即使 nested set 為空仍註冊 D 的 `functions.exec/wait`。
Exec 經 service／broker 回當前 ToolCallRuntime；wait 管理該 session。
Nested selection 排除不參與的 exposure、設定 namespaces 與 exec/wait；
CodeModeOnly 可隱去 nested 工具的直接 advertisement，仍不是 dispatch 拒絕。
`tool_search` 依 model search、provider namespaces 與 deferred metadata 建 registry
索引，不增加授權；hosted WebSearch 是另一條 provider/model/web-mode spec。
[CodeMode assembly](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/spec_plan.rs#L794-L938)、
[search index](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/spec_plan.rs#L370-L404)。

DynamicTools 來自 experimental `thread/start.dynamicTools`；新 start 驗證
identifier、schema、duplicates 與 reserved namespace，deferred 須有 namespace。
Handler 為 D／DF，透過公開 `item/tool/call` 請 client 執行；callback 不是 sandbox。
工具存入 thread metadata；core 收到空集合時會回讀 Resumed／Forked SessionMeta。
公開 resume 沒有 replacement/clear 欄位，start/resume response 也不是完整
DynamicTools inventory。因此空輸入不能證明清除恢復中的既有工具。
[start validation](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/app-server/src/request_processors/thread_processor.rs#L1450-L1508)、
[restore](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/session/mod.rs#L745-L750)。

Registry 的 external 同名後到跳過；plain exec_command/shell_command 保留。
其餘 builtin 名稱在原 handler 缺席時可能由 dynamic 提供，所以必須核對
owner/source，不能只列 name。CodeMode 的正規化名稱也可能碰撞，例如合法
`a-b` 與 `a_b` 同映為 `a_b`，該分支 warning＋skip；碰撞旗標不是所有名稱路徑
的完整拒絕證明。Registry lookup 不按 advertisement/exposure 拒絕，找到 handler
後才核 payload、hooks 與 handler controls。Hidden/deferred 未顯示不能證明不可呼叫。
[external registration](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/registry.rs#L374-L411)、
[normalized collision](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/spec_plan.rs#L867-L879)、
[dispatch](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/registry.rs#L551-L603)。

## Skills 的額外自動行為

Host provider 設 `requires_host_skill_discovery=true`，因此單靠
`skip_host_skill_discovery` 不能停止 discovery。`skills.bundled.enabled=false`
只控制 bundled roots/install；預設可能在 service 建立或 roots 載入時安裝
system skills。這些行為須列入啟動設定、路徑及副作用控制。
[discovery](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/session/session.rs#L624-L637)、
[host service](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/ext/skills/src/host_service.rs#L222-L235)。

MCP dependency installation 另受 first-party originator、mentioned skills 與
`skill_mcp_dependency_install` feature 限制；approval helper 可以自動批准，
不能假定每次都由使用者確認。正式隔離須用獨立 OS enforcement，不能依賴
提示或 skill 設定維持唯一寫入者。
[dependency installation](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/mcp_skill_dependencies.rs#L47-L81)、
[approval](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/mcp_skill_dependencies.rs#L256-L271)。

## 對帳收據與放行條件

以下是待實作的最小收據 schema，不是目前 helper 已提供的 API：

```text
source_pin, binary_hash, entrypoint, thread/turn/step,
config_layers_hash, requirements, effective_features,
provider_capabilities, auth_category, model_metadata_hash,
environments, selected_roots, contributor,
canonical_namespace/name, schema_hash, exposure, carrier,
guard_values, public_readback, observed_advertisement,
forced_dispatch_result, unresolved
```

每欄須保留證據類型；hash 或來源名稱不能代替實際 guard/readback。
Auth 只記類別，不保存 token；provider、roots、config 與 outputs 不含 secrets，
無法排除敏感內容時停止保存／轉送。匿名與登入、fresh 與 resume、CLI 與
app-server 分別建立身分；不能把一次 RPC 的配置讀回綁定為另一 turn 的快照。

本文件只覆蓋固定 source 的入口與條件；完整 runtime registry、恢復後 dynamic
inventory、host/cell lifecycle 與 OS／授權強制仍 unknown。正式資格須補每項
允許工具正控制與排除工具的實際負控制、設定／resume 漂移、可信 observer
與 credential canary。未知 contributor 或無法證明模型不能繞過 worker 時拒絕
production adoption；有限 negative matrix 或無工具宣告不代替此條件。
自架來源端點恢復不會自行完成這些資格；清冊、匿名控制與可信接線可在不依賴自架服務的環境推進。
