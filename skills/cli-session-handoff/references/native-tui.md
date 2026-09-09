# Native CLI/TUI Create And Fork

Runtime compatibility: cli

這是 callable-selected 的 CLI/TUI 分支，與 shell private-clone executor、
manual interactive fork 及 Desktop adapter 分開。先讀主檔指向的 Thread
Capability Discovery，取得當次完整 namespace、schema、回應與語意；
`codex_tui` 名稱、CLI 版本、OS 或 SSH 本身都不足以選取。沒有完整證據時
保留 unknown，回傳準備好的 prompt 或在原任務續行，不注入或模擬工具。

## Preconditions

- 使用者須明確授權確切的 create 或 fork，工具存在不授權操作。核對來源
  session、cwd、repository、Git HEAD、未提交內容、scope 與單一 writer。
- Create 會立即啟動子任務，且繼承來源 cwd；它不建立隔離 Git worktree。
  寫入任務須先確立 exclusive ownership；dirty worktree 只可用於已核對的
  同任務獨占續行。若要求新 worktree、另一 host/project 或 private clone，
  此 payload 不相容，回到編排，不靜默改用另一種 create/fork。
- 保留當次 sandbox/permission 邊界，不傳未支援的設定或擴權。未知的繼承
  語意須先釐清；無法滿足指定隔離要求時使用 current-session/manual fallback。
- Child prompt 必須要求重讀來源、遵守檔案 ownership、使用 repository 驗證
  環境、禁止 recursive session dispatch，並回報變更、驗證、問題及風險。
  dispatch 或 child summary 都不是 repository completion。

## Point-In-Time Payload Contract

以下為 [OpenAI rust-v0.153.4 公開來源](https://github.com/openai/codex/blob/rust-v0.153.4/codex-rs/tui/src/dynamic_tools.rs)
的查核基線，執行前以當次 callable 重驗，不能凍結為永久 schema。

| Operation | Required fields | Optional fields | Result / turn behavior |
| --- | --- | --- | --- |
| `codex_tui.create_thread` | `prompt` | `title`, `model` | `threadId`；繼承來源 cwd，立即啟動 turn |
| `codex_tui.fork_thread` | 無 | `threadId` | `threadId`、`sourceThreadId`、`environment`、`continuation`；省略輸入代表來源任務，fork 不啟動 turn |

實際完整工具名稱由 runtime 讀回，可能帶有 MCP 前綴；不可只看 basename。
未知欄位會被拒絕。Create 不接受 `target`、`projectId`、`environment`、
`thinking` 或 `hostId`；fork 不接受 Desktop 的 `environment`，也不接受
`prompt`。省略 model 以保留來源設定，除非使用者明確要求且當次支援。
Title 應簡短、不含敏感資訊，不作為身分證據。

Create 的 prompt 去除空白後必須非空，原文上限為 1,000 UTF-8 bytes，
這是必要而非充分條件，不能用字元數代替：
`len(prompt.encode("utf-8"))`。例如 `"中" * 333 + "a"` 為 1,000 bytes，
`"中" * 334` 為 1,002 bytes；後者不可送出。

該版本會將來源 ID 與 prompt 依序替換 `&` → `&amp;`、`<` → `&lt;`、
`>` → `&gt;`，再組成下列字串（換行皆為 LF），以 1,256 UTF-8 bytes 二次檢查：

```text
<codex_delegation>
  <source_thread_id>{escaped_source_thread_id}</source_thread_id>
  <input>{escaped_prompt}</input>
</codex_delegation>
```

計算最終字串 bytes，不能只預留固定字元數。36-byte canonical UUID 的 envelope
本身為 132 bytes；`"&" * 300` 原文 300 bytes、包裝後 1,632 bytes，必須拒絕。
相同來源 ID 下 `"&" * 224` 為 1,252 bytes、`"&" * 225` 為 1,257 bytes。
也須涵蓋 `<`、`>` 與多位元文字。此範例只用於離線長度檢查，不自行包裝
呼叫 payload：送入工具的仍是原始 prompt，envelope 由 runtime 處理。
執行前重驗當次原始與包裝後限制；若語意不可觀察就停止該操作並回報限制。

不得截斷掉 scope、authority、
驗證或完成條件。若需長 brief，先確認子任務可讀到同一份已檢視的 nonsensitive
檔案，再用短 prompt 引用其確切相對路徑與 revision；無法完整保留契約則 fallback。
不可自動拆成多次 send 來繞過上限或啟動不完整任務。

## Readback And Continuation

- 回應必須有 usable `threadId`；不發明 `clientThreadId` 或 `hostId`，不套用
  Desktop 的 queued lifecycle/UI directive。只有當次 callable 宣告的回應才有效。
- 該版本 fork 的 `environment` 為 `{"type":"same-directory"}`，`sourceThreadId`
  應匹配已核對的來源，`continuation` 說明僅複製已完成歷史與按需 follow-up。
  讀回這些欄位並核對來源/cwd 意圖；它們是回應欄位，不能倒灌成 fork 輸入。
  缺失或不符時標記未驗證/不相容，停止續行而不重複 fork。
- 用同一入口已發現的公開 read/list 工具讀回 ID、cwd 與來源關係（有提供時）；
  無法讀回就標記 unverified。失敗或逾時可能已建立任務，先確認狀態，不重複 create。
- Fork 複製已完成歷史；本輪未完成的工作不會因此自動交接。需要續行時，先
  確認來源停止寫入與子 ID，再依實際 `send_message_to_thread` 契約及已授權
  prompt 啟動。Create/fork 授權不自動包含額外 send；未授權則只準備 prompt。
- 保存入口/版本來源、搜尋查詢與覆蓋、完整 callable/schema、已授權 payload、
  結果、讀回與限制。Public repo 證據不含私人任務內容、機器路徑或私人 ID。
  離線 fixture PASS 只驗證技能契約，不能宣稱任何 runtime 的 live smoke 成功。
