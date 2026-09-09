# Desktop 遠端 thread 工具可觀察性：Issue #242

查核日期：2026-09-09。對應 [Issue #242](https://github.com/jeffery777/codex-dev-skills/issues/242)。
交付三入口矩陣、可重跑查詢、精確缺口與未送出的上游草稿；**根因仍為 unknown**。
沒有 runtime 修正、工具注入、live create/fork/send、release 或部署。

## 基準與證據層級

- source 基準為 `4bfb67c2d62cfca2012ab3a0635676fa386eca4b`；`main` 與
  Issue 分支在編輯前以 `git ls-remote` 讀回相同 SHA。使用 Desktop 建立的
  獨立 project worktree，初始乾淨、detached
  `468929e7270fde2cee5b7829093ebd8a7821a09b`，取得最新 main 後建立並推送
  `codex/issue-242-thread-runtime-observability`，未修改原 main checkout。
- [#239 驗收紀錄](thread-capability-discovery-acceptance.md) 是歷史證據。
  其中 348 筆無匹配 probe 未在本輪取得原始 catalog；不當作本次重現。
- 本機當輪完整匹配 metadata/schema 保存於
  [原始查詢結果](evidence/issue-242-local-catalog.json)。它證明 callable
  契約可觀察，不代表 create/fork/send 操作成功。
- 公開 `read_thread` 是有界 turn/item 讀回，不是遠端 catalog。
  final answer 的自報不替代原始 tool output。以下只保存去識別化必要投影，
  不匯出完整任務內容、私有 UUID、機器路徑、完整 config 或秘密。

## 三入口矩陣

| 入口與 context | 時間、版本來源 | 介面、查詢、coverage | 結論與限制 |
| --- | --- | --- | --- |
| Desktop 本機 project／獨立 worktree | 2026-09-09 08:38 UTC 起；app bundle Info.plist：CFBundleShortVersionString=`26.901.51231`、CFBundleVersion=`8109`；本機 shell CLI=`0.153.4` | 初始 callable 與 ALL_TOOLS 完整 315 筆 name/description 查詢，15 筆匹配；完整 namespace/schema 見 JSON，陣列無分頁 | Desktop create/fork/send `initial-present`／available；未執行功能測試。Standalone CLI 版本不代表 app engine 版本 |
| Desktop 連線 Rocky，遠端 project 任務內部 | 08:39 UTC 左右讀回；兩輪歷史時間 06:54:20–06:55:05、07:02:11–07:02:38 UTC；當輪 engine 版本 unknown | read_thread：turnLimit=2、includeOutputs=true、maxOutputCharsPerItem=6000；hasMore=false、nextCursor=null；有讀新版 #239 指引的 commandExecution，沒有聲稱 ALL_TOOLS 查詢的原始輸出；部分文件 output truncated=true | `unobservable`／unknown。讀完 turn 分頁不等於取得完整工具事件。未向該任務 send 新 probe |
| Rocky 原生 TUI／projectless registry association、既有 playground cwd | 08:40 UTC 左右讀回歷史單輪 06:46:54–06:48:16 UTC；當輪 CLI 版本 unknown；另於 08:40:00 UTC SSH 查詢 CLI=`0.153.4` | read_thread：turnLimit=1、includeOutputs=true、maxOutputCharsPerItem=1800；hasMore=false、nextCursor=null；有 server=codex_tui 的 completed 事件，必要原始欄位見下方 | 歷史呼叫已觀察；完整 schema、原 create/fork response payload、catalog coverage 缺少。當前 TUI availability unknown；SSH 版本不能補足當輪版本 |

本機 list_projects() 與 list_threads(limit=12) 另確認 Desktop registry 可讀回
遠端 host，unavailableHosts/unavailableSources 為空。此清單不是全歷史盤點，
也不是遠端任務內部的工具清單；沒有已登錄的遠端 playground project，不能
擅用正式 project 代替隔離測試目標。所有時間均為 UTC、日期同上。

TUI 公開讀回必要欄位投影（省略識別碼、參數及其他內容；未合成缺少的結果）：

```json
[
  {"type":"mcpToolCall","server":"codex_tui","tool":"create_thread","status":"completed","durationMs":715},
  {"type":"mcpToolCall","server":"codex_tui","tool":"read_thread","status":"completed","durationMs":3},
  {"type":"mcpToolCall","server":"codex_tui","tool":"wait_threads","status":"completed","durationMs":4},
  {"type":"mcpToolCall","server":"codex_tui","tool":"fork_thread","status":"completed","durationMs":103},
  {"type":"mcpToolCall","server":"codex_tui","tool":"read_thread","status":"completed","durationMs":3},
  {"type":"mcpToolCall","server":"codex_tui","tool":"read_thread","status":"completed","durationMs":4}
]
```

## Source／installed 對照

Rocky 指定安裝檔於 08:40:00 UTC 以 SHA-256 比對，目前三檔符合 source。
本機 installed 兩個主檔較舊，仍可觀察工具；新指引不是工具註冊證據。
只涵蓋下列檔案，未做完整安裝稽核或更新。

| 檔案 | source SHA-256 | Rocky installed | 本機 installed |
| --- | --- | --- | --- |
| desktop-thread-delegation/SKILL.md | `11dd30189a1a21a1fed1c504909d22c7f170230cd313999be5e2a9df3b0b4117` | 相同 | `7623f00eb1dda9905e00ff4b26ee550d0eb3d1c396bb25a61c66baa52b325b93` |
| cli-session-handoff/SKILL.md | `95c483b87ba1c504dae2153741ace2c54aaab9392092546996a033d1dda03955` | 相同 | `c5352dfa86b2cf84811880fde12df17c0aed88ea7aff32ad6cb4d6451bfcf370` |
| docs/native-runtime-capabilities.md | `b7841000f3ee530bc818132940380c72f39973a56392fa222699a8814265e143` | 相同 | 本輪未做 digest 比對 |

已讀本機 installed 與 source 兩個主檔，並讀回遠端任務先前讀取新版指引的
command output；截斷部分不宣稱完整讀取。目前 Rocky digest 與完整已讀
source 相同，但不能反向證明歷史輪次載入位元組。

## 原因分類與公開來源

| 候選原因 | 判定 | 支持與限制 |
| --- | --- | --- |
| 初始清單漏看／deferred discovery 遺漏 | 遠端 unknown | 本機查詢成功；遠端缺原始輸出，不能確認是否真正執行或查找漏項 |
| 觀察介面不足 | 已確認本次缺口 | read_thread 沒有遠端當輪 catalog/schema/query output；hasMore=false 只描述 turn 分頁 |
| 安裝／設定／版本差異 | 安裝差異已確認；因果 unknown | Rocky 三檔符合 source、本機兩主檔較舊；未取得同輪 engine 版本與有效設定 |
| 預期平台限制 | unknown | 公開文件未承諾各入口 agent-callable 工具相同，也未宣告遠端禁止它們 |
| 可重現 runtime 問題 | 未證實 | 歷史無匹配紀錄與第二次自報不足以補上本次原始 probe 缺口 |

[官方 Remote connections](https://learn.chatgpt.com/docs/remote-connections#connect-to-an-ssh-host)
描述 Desktop 透過 SSH、遠端 login shell 啟動 app server。因此 TUI 與 Desktop
SSH 任務是不同控制入口；這是依文件與 namespace 的推論，不是工具缺席原因。
文件的使用者「建立聊天」能力不能推導出遠端 agent 必有 create_thread。

官方搜尋 `Codex Desktop remote SSH thread tools`（limit=5）與
`remote SSH tasks`（limit=3）後，實際讀取上述完整頁面及
[Config reference](https://learn.chatgpt.com/docs/config-file/config-reference)。
搜尋有後續 cursor，非全站窮舉；取得頁面未提供解釋本事件的工具暴露設定。
agents.enabled 的 multi-agent 設定不能直接視為 Desktop 使用者 task 工具
開關。本次未取得特定版本修復聲明，亦未修改設定或重啟。

本 repo 控制技能契約、references、封裝與 installer；上述證據沒有建立
repo 可控制 runtime callable 註冊的關係。#240 installer 修正不證明工具可用。
本次沒有受支援且因果已確認的 runtime 修正可做。

## 可重跑唯讀 probe

在**被調查入口內**先讀 [Thread Capability Discovery](native-runtime-capabilities.md#thread-capability-discovery)。
僅當正式提供 functions.exec／ALL_TOOLS 時執行下列 Code Mode JavaScript，
不是 shell 指令。保存 summary 與所有 matching metadata，不只保存 final answer。

```javascript
const query = /create_thread|fork_thread|send_message_to_thread|read_thread|wait_threads|list_threads|list_projects|codex_tui/i;
const matches = ALL_TOOLS.filter(x => query.test(x.name + " " + x.description));
text({query: query.source, total: ALL_TOOLS.length, matched: matches.length,
      coverage: "all array entries; name and description"});
for (const match of matches) text(match);
```

輸出過大時保存當輪 snapshot，依 runtime 支援的 continuation 分批輸出，
記錄 index／總數；不拼接未確認是否漂移的 catalog。本次 JSON 直接由同一
snapshot 保存全數 15 筆。只有名字而無 schema 時，需正式 discovery 取得
完整契約，否則 unknown。無匹配再以 thread/task 與已觀察 namespace 擴查，
讀完相關分頁。無正式介面不能用網頁、MCP resource list、SSH CLI help 或
另一任務清單替代。對照資料的版本與 context 必須同時保留。

版本旁證可重跑（操作者先選定 APP_BUNDLE 與已核對 SSH alias，公開報告
不記錄私人實際值；SSH 僅執行明列命令）：

```bash
date -u '+%Y-%m-%dT%H:%M:%SZ'
/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$APP_BUNDLE/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$APP_BUNDLE/Contents/Info.plist"
codex --version
ssh -x -o BatchMode=yes -o ConnectTimeout=10 "$VERIFIED_SSH_ALIAS" 'date -u +%Y-%m-%dT%H:%M:%SZ; codex --version'
shasum -a 256 skills/desktop-thread-delegation/SKILL.md skills/cli-session-handoff/SKILL.md docs/native-runtime-capabilities.md
```

SSH 版本不證明 Desktop app server 的 executable/version；公開入口無法
讀回時填 unknown，不啟動另一 app server 取代。

## 精確缺口與待授權 payload

現有 Desktop 遠端 project 任務缺 catalog、查詢原始輸出與當輪 schema。
補證需使用者指定並授權向該任務 **send 一次診斷 prompt**，或由使用者
自行貼入。不可把 TUI playground 當成 Desktop 遠端入口，也不繼承其他
任務歷史測試授權。具體 payload：

> 僅做 Issue #242 一輪唯讀能力診斷。保持目前 Desktop SSH 遠端入口，
> 不讀正式專案內容、不修改檔案或設定、不啟動服務、不建立或 fork 任務。
> 先讀已安裝 #239 Thread Capability Discovery 指引。記錄 UTC 時間、
> 入口與 project/projectless/cwd 類型、公開版本來源，未知明示。依上列
> 精確查詢查閱當輪正式 callable/deferred discovery，保存總數、coverage、
> 分頁／截斷狀態、全部匹配 namespace/schema 與原始 tool output；無匹配
> 再查 thread/task 與已觀察 namespace。缺完整介面或 schema 時填 unknown。
> 結果去識別化，不含私有 UUID、機器路徑、完整 config 或秘密。
> 禁止實際呼叫 create_thread、fork_thread、send_message_to_thread。

此 send 會新增一輪並消耗使用量；有新工作正在目標執行時須重查是否干擾。
CLI/TUI 的當前完整 catalog/schema 也需在其自身入口另行取證。這是精確
缺口，不是永久缺席或 runtime 修復宣告。

## 未送出的上游回報草稿

**標題：** Desktop SSH 遠端任務的 thread 工具暴露與公開診斷缺口

**環境：** macOS Desktop app 26.901.51231/build 8109；SSH 連線 Rocky；
shell CLI 另次唯讀查核為 0.153.4。Desktop 遠端當輪 engine 版本 unknown。
比較入口為本機 project worktree、遠端 project、遠端 TUI playground。

**觀察：** 本機完整 315 筆 metadata 查詢含 Desktop create/fork/send。
歷史遠端 probe 紀錄為 348 筆無匹配；第二個遠端任務讀過新指引，但公開
readback 缺搜尋原始輸出。TUI 歷史 codex_tui create/fork completed 事件
存在。後兩者不能證明當前 Desktop 遠端工具缺席。

**希望釐清：** 哪個公開介面可列出遠端任務當輪 callable、schema、實際
engine 版本與限制？此模式是否預期提供 Desktop thread 操作？若受版本、
設定或 rollout 影響，請提供受支援的判斷與修正方式。

**重現狀態：** 尚未取得新的遠端完整 probe。依上節同入口採集並完成隱私
審查後補齊原始結果；這不是已確認 defect 的回報。不可附完整任務紀錄或
私有 runtime state；送出仍需獨立授權。

## Fallback 與驗證邊界

- 本次實際使用 current-session fallback 完成 GitHub 讀回、公開遠端觀察
  與本 repo 文件工作；它不宣稱遠端任務建立或工具修復。
- 手動貼入上節 prompt 可補證，先核對正確 Desktop 遠端入口。
- #239 記錄本機 Desktop 主控 fork 與 CLI private-clone start/fork 成功；
  只作已測替代路徑的歷史線索。本次未重測，使用前重查 callable、target、
  隔離需求與精確授權，不自動改用其他入口派送。

文件驗證採 repository resolver，已先確認 Python 3.12.9、PyYAML 6.0.3。
可重跑命令：

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python -m json.tool docs/evidence/issue-242-local-catalog.json >/dev/null
./scripts/validate-repo.sh --skip-unit-tests
git diff --check
```

靜態檢查不證明遠端行為。正式 review、PR exact-head Merge Review、CI、
receipt 與 dedicated App 結果以各自 gate 證據為準，本文不預先宣告通過。
