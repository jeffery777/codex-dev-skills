# Desktop 遠端 thread 工具可觀察性：Issue #242

初始實測日期：2026-09-09；研究與接續狀態更新：2026-09-10。
對應 [Issue #242](https://github.com/jeffery777/codex-dev-skills/issues/242) 與
[PR #244](https://github.com/jeffery777/codex-dev-skills/pull/244)。

**目前分類：疑似上游 Desktop SSH 工具供應回歸，精確根因仍為 unknown，
功能尚未修復。** Issue 保持 open 作為上游依賴追蹤；PR 保留 draft，保存
診斷成果，不以文件交付完成代表遠端 agent 能自行派工。

初始查核沒有 live create/fork/send；後續已授權實測證明本機 Desktop 主控
可建立與 fork 遠端任務，並向原新任務送入 probe、讀回回覆。遠端任務自己
仍回報缺少三工具；完整結果、證據限制與接續條件見本文後半。
本輪沒有 runtime 修正、工具注入、release 或部署。

## 初始快照的閱讀範圍

以下「基準與證據層級」至「原因分類與公開來源」保存 2026-09-09 初始
查核狀態；其中「未測／未 send／未登錄」不是後續結果。請同時閱讀
「後續受授權測試」與「上游研究及追蹤判斷」，不要以初始快照覆蓋新證據。

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

## 初始三入口矩陣

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

## 初始缺口與 probe payload

初始 Desktop 遠端 project 任務缺 catalog、查詢原始輸出與當輪 schema。
補證時須確認向指定任務 send 的授權；本次後續已取得一次診斷授權並執行，
結果見文末。其他操作者可自行貼入下列 payload。不可把 TUI playground
當成 Desktop 遠端入口，也不繼承其他任務歷史測試授權。

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

**標題：** Desktop SSH 遠端呼叫者缺少 create/fork/send，本機主控可操作相同遠端目標

**環境：** macOS Desktop app 26.901.51231/build 8109；SSH 連線 Rocky；
shell CLI 另次唯讀查核為 0.153.4。Desktop 遠端當輪 engine 版本 unknown。
比較入口為本機 project worktree、遠端 project、遠端 TUI playground。

**觀察：** 本機初始完整 315 筆 metadata 查詢含 Desktop create/fork/send；
後續主控對已核對遠端 playground 的 create 與 same-directory fork 成功，
讀回目標 host/cwd、固定回覆及繼承歷史。新遠端任務經 send probe 回覆的
JSON 列出 23 項 codex_app，本機直接對照為 31 項；遠端缺 create/fork/send，
但仍列有 sidebar 修改、archive、rename 等工具。遠端 JSON 由 assistant
final 轉交，公開 read_thread 未呈現其 functions.exec 原始輸出。另有同日
TUI create/fork 完成歷史，但當輪 CLI 版本 unknown，不替代 Desktop 證據。

**希望釐清：** 哪個公開介面可列出遠端任務當輪 callable、schema、實際
engine 版本與限制？此模式是否預期提供 Desktop thread 操作？若受版本、
設定或 rollout 影響，請提供受支援的判斷與修正方式。

**相關上游：** OpenAI #42973 有同 build 的方向不對稱回報；#41248 有固定
遠端 runtime、回退 Desktop 後新任務恢復 create/send 的使用者對照。請確認
是否為同一工具供應問題、適用支援範圍及修復版本；這些不是本環境診斷。
直接來源及限制見「上游研究及追蹤判斷」。

**分開追蹤：** 部分 send 回合 completed 但 items=[]；對舊 TUI 來源 fork
曾回傳 no rollout found，而新 Desktop 遠端任務 fork 成功。不要預設兩者
與工具缺席同因。不可附完整任務紀錄或私有 runtime state；向 OpenAI 送出
仍需獨立授權，本稿尚未送出。

## Fallback 與驗證邊界

- 本機 Desktop 主控是已實測的替代路徑：對 saved SSH playground 建立、
  fork，及向原新任務 send probe 並讀回回覆。它不能恢復遠端任務自行
  create/fork/send；部分子任務 send 的空讀回仍未解釋，每次須核對結果。
- 手動貼入上節 prompt 可補證，先核對正確 Desktop 遠端入口。
- #239 記錄本機 Desktop 主控 fork 與 CLI private-clone start/fork 成功；
  只作已測替代路徑的歷史線索。本次未重測，使用前重查 callable、target、
  隔離需求與精確授權，不自動改用其他入口派送。

文件驗證採 repository resolver，已先確認 Python 3.12.9、PyYAML 6.0.3。
可重跑命令：

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python -m json.tool docs/evidence/issue-242-local-catalog.json >/dev/null
./scripts/project-python -m json.tool docs/evidence/issue-242-remote-catalog-report.json >/dev/null
./scripts/validate-repo.sh --skip-unit-tests
git diff --check
```

靜態檢查不證明遠端行為。正式 review、PR exact-head Merge Review、CI、
receipt 與 dedicated App 結果以各自 gate 證據為準，本文不預先宣告通過。

## 後續受授權測試：仍在調查

使用者明確要求查明根因，不能將診斷文件通過當成問題修復。PR #244 已轉
draft 並移除 closing keyword；Issue #242 保持 open。初始文件 review 只能
證明其當時內容品質，不代表以下新證據或 root-cause 調查完成。

1. **Desktop 遠端原任務診斷。** 使用者授權一次唯讀 send；主控端先讀回
   idle，送出禁止其他任務操作的完整 probe。公開 wait_threads 回報該輪
   08:58:01–08:59:20 UTC、completed、error=null。read_thread 指定
   turnLimit=1、includeOutputs=true、maxOutputCharsPerItem=16000，回傳
   該輪 items=[]；延後再次讀回仍相同。此為公開觀察缺口，不聲稱 probe 的
   catalog 查詢真正執行或沒有匹配。它比先前只有 final answer 自報更不足。
2. **Desktop 主控端 fork 遠端 playground。** 使用者另授權該目錄的簡單
   create/fork/send 測試。正式 read_thread 成功讀回來源 idle 與 playground
   cwd，Git 查核顯示此目錄不是 repository。主控端呼叫
   mcp__codex_app__fork_thread，payload 為已知來源 ID 及
   environment={type:same-directory}，得到 isError=true：
   `no rollout found for thread id <已去識別化來源>`。當輪 fork schema 無
   hostId 輸入，read_thread 則可指定 hostId。這是一次跨主機 fork 失敗，
   可能涉及目標 host lookup；尚無實作證據確認其內部原因，也不能以此
   代替遠端任務內部工具缺席的根因。
3. **Desktop 續行 TUI 來源的 playground 任務。** 已送出一輪有界測試，
   要求重新查當輪工具，再最多 create 一個只回固定文字的子任務、fork
   一次及 send 一次，禁止檔案／設定變更及遞迴派送。公開狀態曾為
   waitingOnApproval，之後回報 09:02:34–09:06:53 UTC、completed、
   error=null；read_thread 使用 includeOutputs=true 及每項 20000 字元
   上限，最新回合仍為 items=[]。沒有可驗證功能結果；近期任務清單也未
   列出本輪測試子任務，但不能據此斷言沒有建立。此入口必須標記 TUI
   lineage，不當作全新的 Desktop project 對照。
4. **全新 Desktop 遠端 project 的初始阻擋。** 當時公開 list_projects 未列 playground。
   create_thread 要求已讀回 projectId；沒有新增 project callable。
   Computer Use 對 Codex app 回報 safety restriction，未改用其他方式
   繞過。後續操作者已加入專案並使用獨立名稱區隔本機專案，測試見下節；
   名稱不替代 host/cwd 身分查核。

[官方 app-server 文件](https://learn.chatgpt.com/docs/app-server#dynamic-tool-calls-experimental)
說明 dynamicTools 由 client 提供，儲存在任務 metadata，resume 未提供新工具
時可恢復；動態工具呼叫由 app server 向 client 發送請求。本次只閱讀公開
文件，沒有啟動或直呼 app server。因此 client 註冊／resume 是有文件支持的
後續查核方向，但實際 Desktop 遠端 registration payload 尚不可觀察，
不能宣稱已定位根因。公開 config reference 與 CLI features list 亦不能
代替同輪有效工具註冊資料。

### 加入遠端 playground 後的實測

操作者加入後，list_projects 確認為同一 SSH host、指定 playground 路徑、
projectKind=remote、isGitRepository=false。使用讀回的 projectId 與
environment={type:local} 進行下列有界測試；local 在此表示直接使用該已存
專案目錄，不表示本機 host。所有測試禁止檔案與設定變更。

| 操作 | 公開讀回結果 | 可支持的結論 |
| --- | --- | --- |
| 本機 Desktop 主控 create 遠端任務 | 回傳 ready threadId 與遠端 hostId；09:14:38–09:14:49 UTC completed；讀回 cwd 正確及 `ISSUE242-CREATE-OK` | 遠端建立與首次回覆成功 |
| 主控 fork 該已完成的新任務 | status=created、synchronization=complete；讀回遠端 host/cwd 與原完整已完成回合 | 此新任務的 same-directory fork 成功；先前舊任務失敗不是所有跨 host fork 都失敗 |
| 主控 send 固定文字到 fork 子任務 | 09:15:21–09:15:27 UTC completed、error=null，但最新 items=[] | 傳訊已獲接收並回報完成；尚不能確認固定文字回覆成功 |
| 主控 send catalog probe 到原新任務 | 09:15:48–09:16:01 UTC completed，讀回 commentary 與 final；未呈現 functions.exec 工具輸出 | send 與回覆讀取不是全部失敗；需區分目標與回合 |

上述 probe 的 final 自報 ALL_TOOLS=371、名稱或描述匹配 13 項，工具名稱
包含 list_projects、list_threads、read_thread、read_thread_terminal、
wait_threads，但沒有 create_thread、fork_thread、send_message_to_thread、
codex_tui。這是新建 Desktop 遠端任務的症狀重現回報，不再只依賴舊 TUI
lineage；仍須明確標記 final 轉述與獨立工具輸出之差異。

後續 09:16:31–09:18:47 UTC 回合已將 JSON 放入 final，透過 read_thread
完整取得並成功解析。只對名稱比對的 matchingNames 為 6 項，其中一項是
Linear connector 的 list_projects；這與前輪「名稱或描述」匹配 13 項是
不同查詢。[遠端 catalog 轉述與本機直接對照](evidence/issue-242-remote-catalog-report.json)
保留六個匹配名稱；下列集合比較則只涵蓋 codex_app，排除其他 connector。
兩端 codex_app 名稱集合分別為 23 與 31 項；遠端仍有 sidebar 修改、archive、
rename 等工具，因此不能將差異概括成遠端僅提供唯讀操作。此 JSON 由遠端
assistant final 轉交，不冒充直接取得的 functions.exec 工具輸出或完整 schema。

目前證據將「本機主控可以建立／fork 遠端任務」與「遠端任務本身能否呼叫
這些工具」區分開來；前者成功不能證明後者可用。尚未確認造成兩端工具集
差異的產品規則、設定或缺陷，因此仍不將 Issue #242 視為修復完成。

### 操作者在另一遠端專案的人工重現

操作者另提供一個同 SSH host、不同正式專案的新任務，要求讀取其測試對話。
公開 read_thread 顯示該輪讀取 delegation skill 與專案流程文件，最終自報
工具清單及 deferred tools 沒有 create_thread，因而沒有建立任務。可見紀錄
沒有 create_thread 呼叫或 API 錯誤，也沒有 catalog 查詢原始輸出；此項應
分類為「agent 回報工具未提供」，不能描述為建立 API 執行失敗。正式專案
文件內容不轉載到本公開 artifact。

此觀察與 playground 遠端任務自報缺少 create/fork/send 相符。兩個遠端
專案的回報尚不能證明所有遠端入口都受同一規則影響，但目前沒有證據顯示
差異由專案名稱或正式專案流程造成。比較時應固定呼叫者：先前成功的是
本機主控呼叫遠端 target，並不是 playground 遠端任務自行呼叫 create。

後續可驗證方向是比較本機／遠端生效的受支援工具設定與註冊規則，而不是
繼續重複建立目標任務。若公開介面仍不能提供該資料，應將最小重現與
caller/target 矩陣提交產品端確認；未送出的上游草稿不代表已取得官方結論。

## 上游研究及追蹤判斷

2026-09-10 閱讀使用者提供的研究報告後，再透過 GitHub connector 直接
讀取以下 OpenAI issues 與留言。報告作為研究線索；以下結論引用實際核對
的公開來源，不公開私人研究對話連結或將外部診斷冒充本次實測。

| 公開來源 | 核對到的內容 | 證據限制 |
| --- | --- | --- |
| [OpenAI #42973](https://github.com/openai/codex/issues/42973) | headless SSH 任務缺 create/send/fork/handoff，本機呼叫者仍可操作遠端；讀回狀態 open | 回報者將問題描述為回歸；不是本環境的確定根因 |
| [#42973 同 build 補充](https://github.com/openai/codex/issues/42973#issuecomment-5578734586) | 作者回報 Desktop build 8109、各處 runtime 0.153.4；本機 send 到 SSH 成功，SSH 無 sender；其 bundle 分析指出非 local host 不注入 codex_app MCP | 外部使用者的程序／bundle 分析，未在本次環境檢查或重現該供應分支；並非官方支援契約 |
| [#41248 Desktop 回退對照](https://github.com/openai/codex/issues/41248#issuecomment-5448651039) | 作者固定 remote 0.150.1；Desktop 26.825.31414 缺工具，26.818.61809 的新任務 create/send 恢復；automation_update 仍缺 | 強化 Desktop 堆疊回歸假設；非本環境的受控實驗，不能斷言全部八項同因 |
| [#41248 新 runtime 重測](https://github.com/openai/codex/issues/41248#issuecomment-5476904686) | 另一作者回報實際 app-server 換成 0.151.0 後，新任務仍缺四項委派工具；Issue 讀回狀態 open | 削弱「只因殘留舊 server」的通用解釋，不證明本環境版本已對齊 |

優先假設是 Desktop 舊 dynamic 委派路徑退場後，SSH 呼叫者未取得替代
MCP 工具；也可能涉及其他 exposure／設定條件。不能直接定案為 CLI 與
Desktop 版本號不相容：同版本外部回報仍失敗，而固定遠端 runtime、只換
Desktop 的外部對照曾恢復。以上回報沒有建立本環境的精確供應決策、官方
預期限制或適用修復版本；Issue 的 bug 標籤亦不等於維護者確認根因。

目前應追蹤「上游疑似回歸與本地驗收」，而非以重裝 skills 或 installer
修改作為沒有因果證據的修法。公開 API 的 thread/start、thread/fork、
turn/start 存在，不代表遠端 agent 自動獲得對應 callable；本次也未觀察到
缺席工具發出請求後遭 server 拒絕。

## 分支保存與後續接續

- 保存分支：`codex/issue-242-thread-runtime-observability`。以 Git 最新提交
  與 PR head 為接續基準，不以本文初始 SHA 當作之後的 main 或最新版。
- Issue #242 保持 open；PR #244 保持 draft 並使用 Related to #242，不用
  closing keyword。文件保存與功能修復是不同完成條件。本輪不宣告內容或
  merge readiness；預期尚缺完整 changed-head exact-head 與 GitHub gate。
- 下一輪先讀 Issue、PR、本文、兩份 catalog JSON、當前 AGENTS 與 policies；
  核對本地 status、branch、upstream、遠端 refs 及其他人的修改。若 main
  已推進，先評估差異與衝突，再依當次授權選擇同步方式，不 force push。
- 重新讀取上游 #42973、#41248、相關修復與發布說明。上游關閉、標籤或
  文件更新只是重測線索，不能替代本環境驗收；本紀錄不建立自動監控排程。
- 最小補證優先序：同輪直接／deferred catalog 與 thread-scoped MCP
  工具狀態、Desktop 實際遠端 app-server 版本及受支援供應診斷。公開 UI
  不呈現時，請維護者提供去識別化診斷；不自行直呼 app-server 或讀私有 state。
- 新增診斷回合、版本切換、模型對照或 runtime 變更前，重查目標、目前
  工作與授權；過去有界測試不是未來任意派工或環境修改的持續授權。
- 後續其他開發項目使用其自己的 Issue／分支／worktree；不要把本分支未
  合併文件當成所有分支已具備的基線。原研究提示詞在忽略的 `.work/`，只作
  本地輔助；重要結論、直接來源與接續條件已保存在此 tracked 文件。

**修復驗收條件：** 在已核對版本及授權的隔離 SSH playground，由
Desktop SSH 遠端呼叫者自身查得正式 create/fork/send 契約，實際建立子任務、
fork、傳送固定文字並讀回正確 host/cwd／歷史／回覆。保存查詢覆蓋、原始
結果與限制；本機主控成功或工具名字重新出現都不替代這項驗收。

若 OpenAI 明確確認此情境不支援，記錄官方適用條件，由使用者決定是否接受
限制而結案；不得自動標記為 fixed。舊 TUI fork 與 items=[] 另保留為次要
未解症狀；接受修復或其他結案方式前須明確處置，不能在交付文件時消失。
