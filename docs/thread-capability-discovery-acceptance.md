# Thread 能力發現驗收紀錄

本紀錄對應 [Issue #239](https://github.com/jeffery777/codex-dev-skills/issues/239)，
查核日期為 2026-09-09。這是技能契約、候選版部署與點時環境證據，
不是平台功能已修復或 Issue 已合併的宣告。source/package version 維持 0.24.2。

## 原事件與驗收範圍

使用者透過 Rocky 上的 Codex TUI 要求更新至 v0.24.1，之後回到 MacBook
Desktop 要求自動建立新對話交辦任務。原事件的交辦入口是 Desktop；
TUI 是先前安裝指令的入口，不能把兩者合併成 TUI create/fork 故障。
本次另外查核 CLI/TUI 契約以避免同名工具誤用；使用者已接受互動 TUI
實測延後，未測項目不標記 PASS。

## 已實作的契約

- 共享 [Thread Capability Discovery](native-runtime-capabilities.md#thread-capability-discovery)
  區分初始可見、延後找到、正式查找無結果、不可觀察及不相容。
- Desktop 與 CLI/TUI 依當次完整 namespace/schema、cwd/target、ID 與 turn
  語意分流；保留精確操作授權、單一 writer、來源驗證及完成條件。
- [Native TUI reference](../skills/cli-session-handoff/references/native-tui.md)
  說明原始/escape 後 UTF-8 prompt 上限、未知欄位拒絕、完整 fork 回應及續行；shell executor 不變。
- references 隨 CLI group 的隔離 filesystem 安裝與 generated plugin 一同驗證。
  已更新 Rocky 的 Desktop／共享依賴並補裝 CLI adapter；本次未修改
  Linux installer 或備份策略。

## 當次可觀察證據

| 入口 | 版本與證據來源 | 已驗證結果 | 限制與未驗證項目 |
| --- | --- | --- | --- |
| Mac Desktop 本機 | 公開 app bundle metadata：26.901.51231，build 8109；正式 callable 宣告 | 在無專案隔離目錄 create 成功，唯讀任務完成；same-directory fork 回傳來源／子 ID、environment 與 continuation，公開讀回 cwd、idle 與已完成歷史 | fork 續行顯示 completed，但公開 readback 暫缺該輪 items；未驗證 Git worktree queued 分支 |
| Desktop 主控端操作 Rocky | 公開 task registry 與 fork 回應 | 對既有 playground 任務 fork 成功，讀回遠端 host、相同 cwd 與 idle；續行完成並寫出指定測試證據 | playground 未登錄為可供 create 選取的遠端 project，未測遠端 create；此結果不代表遠端任務內部有相同 callable |
| Rocky Desktop 任務內部 | 原任務新一輪 probe、隔離 fork 與部署後 probe | 正式 `functions.exec / ALL_TOOLS` 對全部 348 筆 metadata 的 name／description 查詢 `create_thread|fork_thread|send_message_to_thread|codex_tui`，無匹配；分類 `searched-no-result` | 只證明當輪查找範圍內未暴露工具，無法取得缺席工具的 schema；不能推論永久平台缺陷 |
| Mac CLI 與 Rocky CLI | 公開 `codex --version`：均 0.153.4；公開 exec JSON 事件與隔離 executor receipt | 各自 start／fork 均 exit 0、`turn.completed`、不同 session UUID、來源 HEAD 不變；Rocky 部署後直接使用新裝 executor 重跑亦通過 | `codex exec` 不等同互動 TUI；receipt 依契約省略 child summary，不能據此推定模型一定遵循新指引 |
| 互動 TUI | [公開 TUI 原始碼](https://github.com/openai/codex/blob/rust-v0.153.4/codex-rs/tui/src/dynamic_tools.rs) 與離線回歸案例 | 已查核 create／fork 不同輸入與 fork 不啟動語意 | 使用者接受實測延後；沒有當輪 TUI callable 或 live create/fork PASS |

原遠端事件的根因仍未確認。安裝 reference、讀取 reference 與 runtime deferred
搜尋是不同證據；本次修正不宣稱能替 runtime 注入工具。

## 離線驗證與重跑

全部 Python 使用 repository resolver，當次選取 Python 3.12.9、PyYAML 6.0.3。

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python -m unittest tests.test_native_runtime_contract_docs tests.test_plugin_packaging
./scripts/project-python -m unittest tests.test_cli_session_handoff
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python scripts/validate-release-state.py
./scripts/validate-repo.sh --skip-unit-tests
git diff --check
```

文件／封裝 54 tests 與 CLI 54 tests 完整重跑通過；plugin parity 驗證 121
個 generated files。repository 靜態驗證與離線 release-state 檢查通過。
CLI version-probe timeout 個案首次整組執行曾出現非預期 status；單項與整組
重跑均通過，尚未確定該次瞬時差異原因。沒有因此修改 executor 或放寬斷言。

這些測試驗證技能文字契約、操作 reference 可達性與封裝；不測試模型一定會
遵循指引，也不執行 live native tool。`--skip-unit-tests` 的靜態檢查不代表
全 repository unit suite 已跑；上列兩組測試才是本次實際範圍。

## Review 證據邊界

獨立 review 首輪指出 escape/envelope 二次上限及 fork 完整回應缺口；本次
修正已補齊並新增回歸案例。實際 review verdict 與 Security Diff Scan 結果
須以綁定最終 diff 的報告核對，本紀錄本身不取代正式審查證據。修正後必須
重驗受影響部分；初始 snapshot 的 scan 不能代表修改後的 working tree。

## Rocky 候選版部署

- 更新前缺少 CLI adapter；既有 Desktop adapter 與共享文件不同於本候選版。
- 使用 repository installer 維護既有 filesystem 安裝，更新 Desktop 與必要
  shared/delivery 依賴並補裝 CLI group；沒有變更 agent profiles 或正式專案。
- 安裝後兩組 `install.sh diff`（包含依賴）無差異；Desktop／CLI 主檔、
  create/fork 與 native-tui references、共享能力文件共五檔 SHA-256 與來源一致。
- 預設 state 的舊備份碰撞使第一輪 installer 在寫入前停止；改用支援的獨立
  `XDG_STATE_HOME` 完成部署並保留既有備份。此次紀錄不在預設 state ledger，
  後續維護須使用此次部署的 state root；這是操作紀錄，不是 installer 修正。
- 部署的是 #239 候選內容，不是新 Release；安裝版本字串 0.24.2 不能單獨
  證明包含本次未發布變更，須以來源比對及上述檔案 digest 核對。

## 驗收處置與後續

- 已完成原 Desktop 遠端任務 probe、可執行的隔離 Desktop／CLI smoke、
  Rocky 安裝後比對與 CLI 重測。正式專案內容未因測試變更。
- 平台未暴露工具時保留 `searched-no-result`，可使用已驗證的本機 Desktop
  主控 fork 或 CLI private-clone start/fork；仍須依各入口 scope 與授權選用。
- 互動 TUI 實測由使用者接受延後；owner 為專案維護者，追蹤於本紀錄與
  Issue #239。下次實際使用 TUI 或遇到相關問題時，先重讀當輪完整 callable，
  在隔離目錄執行 create/fork 並保存 payload、回應與啟動狀態後再宣稱可用。
- 遠端 Desktop create 與 queued worktree 路徑保持未驗證；追蹤 owner 同上，
  在取得已登錄且授權的隔離 project 後補測。本次不以正式專案代替測試目標。
- Pre-commit review／Security Diff Scan 不取代 PR 後完整 exact-head Merge
  Review、CI、receipt 與 dedicated App。合併與 Release 仍是分開的交付階段。
