# 隔離模型執行與可信接手

Issue #316 的 N1–N4 設計候選。此文件定義待實作及待資格化的邊界，
不代表 runtime adapter 已啟用；production 清冊仍須維持空，直到完整驗收。

## 控制面與寫入面

可信監督器持有 packet ledger、generation、已封存 checkpoint 與成果整合權。
模型服務與官方訂閱的登入由控制面處理；模型可呼叫的寫入工具只能作用於
當次 attempt 的隔離副本。官方訂閱入口不能改成付費 API fallback。

候選 bridge 使用固定 stdio MCP 協定接收工作操作，再交給本機 Docker 或
rootless Podman 的受限 worker。MCP 只是 transport，不提供隔離保證。
bridge 不接受模型指定 host command、engine socket、mount、credential path、
container flags 或動態工具清冊；shell 文字只在固定 worker 邊界內執行。
既有 packet ledger 與 generation 契約仍是唯一接手狀態，不另建重試狀態機。

Host client 的模型工具須受獨立的作業系統 enforcement 限制：來源副本僅唯讀，
控制面、登入資料與其他 attempt 不可由模型工具讀寫。預設 deny，再逐項給予
必要權限；不得把授權給 provider client 的登入能力同時給 worker。
這是待驗證要求，named profile 的設定值本身不能證明成立。

若無法證明上述控制面與工具隔離，bridge 只能進行無憑證的合成實驗，不能
接入真實 provider。另一候選是 provider client 本身也放在受隔離環境，並由
可信 credential broker 提供最小登入能力；其公開介面與訂閱支援須另行資格化。
此設計不預設未公開的訂閱 API 或任意 credential forwarding 可用。

## 公開 CLI 限制

以下呼叫鏈核對固定 `openai/codex@01fc69f4026735edfdf6789820549727a4867b11`
（0.159.3），不推定其他版本、bundled CLI 或 Desktop 同樣成立：

- `shell_tool=false` 阻止 shell handler 註冊；`unified_exec=false` 單獨使用
  不能證明所有 exec 停用。patch 的註冊另由 environment 與 model metadata
  控制，不能靠這兩個旗標排除。
  [工具註冊](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/spec_plan.rs#L1079-L1116)。
- `PreToolUse` 有效 deny 在 patch handler 之前執行；但 hook 的執行錯誤、
  無效 JSON、逾時等失敗不保證阻擋工具。hook 僅作額外防護，不能承擔唯一
  隔離邊界。必須測試 hook 失敗時 host sentinel 仍不變。
  [失敗語意](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/hooks/src/events/pre_tool_use.rs#L193-L290)、
  [工具呼叫順序](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/registry.rs#L603-L655)。
- `--ignore-user-config` 不會同時設為忽略 project configuration。Host client
  不以可寫 worker checkout 為配置探索根；啟動前核對固定 CWD、祖先配置、
  instructions、plugins、hooks 與有效設定層，漂移時拒絕啟動。
  [CLI overrides](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/exec/src/lib.rs#L364-L370)、
  [project layers](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/config/src/loader/mod.rs#L337-L407)。

不能只依送給模型的 tools schema 判定 handler 已移除；native metadata 未解析
時尤其不能建立完整工具清冊。須驗證 provider 強制回傳未宣告或已停用工具時，
runtime 仍拒絕副作用；未資格入口不能放行。

## 準備與啟動契約

1. 從核准 source／checkpoint 建立獨立副本；不以硬連結或共享 Git 可寫資料
   複製。核對 symlink、inode aliases、路徑與機密排除，不能只比較目錄名稱。
2. 在啟動前固定完整隔離條件及目標身分。關閉非必要 inherited FD，worker
   environment 不包含 provider 登入或 host ambient credentials。
3. Worker 不掛載 engine socket、控制面、其他副本或憑證；預設無網路、唯讀
   root filesystem、最小身分與 capabilities，並有可讀回的資源及生命週期限制。
4. Bridge 每次派工重新核對 packet、attempt、generation、target、隔離身分
   與撤銷狀態。回覆遺失或逾時保留 `unknown`，不推定未執行、不盲目重播。
5. 無法確認停止時，只能隔離舊 attempt 並拒收晚到結果；隔離及外部效果排除
   讀回合格後，新副本從上一個可信 checkpoint 接手，不讀舊環境即時半成品。
6. 封存、驗證及 review 後，由唯一整合器核對 source HEAD、scope、generation
   與 artifact digest，才採用成果。模型恢復不搶占目前工作單元。

## 最小資格矩陣

| 面向 | 必測案例與通過條件 |
| --- | --- |
| Hook 故障 | 有效 deny、runner error、timeout、invalid JSON；host 資料皆受 OS 邊界保護 |
| Handler | shell、exec、write_stdin、patch、Code Mode、agent、額外 MCP；禁止入口無副作用 |
| 配置 | 祖先及巢狀 `.codex`、AGENTS、symlink、plugins、額外 hooks；有效設定及輸入無漂移 |
| Bridge | path traversal、額外欄位、任意 mount／argv、動態工具；拒絕未知或超範圍請求 |
| Worker | nested CLI、socket、網路、FD、hardlink、background child；無 host 或 sibling 權限 |
| 恢復 | crash、lost reply、舊 generation、未停止 writer；不重播、不發布 stale 成果 |
| 登入與資料 | 先用合成 canary；worker env、stdio、logs、artifacts 不含登入資料；實際訂閱與 provider 另驗 |

先以合成 provider／canary 完成最小案例，再擴大到 N1–N4 正式資格。
每次變更只重驗受影響邊界，重用內容及假設未變的證據；不逐項重跑全量。
最終 latest head 的完整 base-to-head Merge Review 及專案 gate／CI 不省略。
原始證據與 review 收據不進 Git，位置與重建規則見
[工程計畫](../plans/issue-316-local-model-mapping.md)。
