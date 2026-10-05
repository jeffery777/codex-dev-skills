# 原生模型接入、選模與執行中接手

Issue #316 的三層需求分別驗收，仍保留原自動切換目標。工程流程效率是每層
DoD：沿用原生能力及既有決策，先做廉價契約檢查，重用有效證據，避免以完整
恢復系統作為基本接入的前置。本文件是設計與交付邊界，不是 runtime 資格收據。

## 當前公開能力與限制

2026-10-05 查讀：standalone CLI 0.159.3、Desktop-bundled CLI 0.160.0，
Desktop 為 ChatGPT app 26.930.31730／build 12947。分別由實際 executable
產生 version-matched experimental JSON schema；未啟動 session、登入或推論。
版本、help 及 schema 只證明介面，不能證明 gateway、權限或工具生命週期。

| 責任 | Codex 原生能力 | 現有 workflow／技能 | 真正缺口與新增元件理由 |
| --- | --- | --- | --- |
| A：provider、登入、模型請求 | User-level `model_provider`／`model_providers`、CLI `--profile`／`--model`；官方端原生 ChatGPT 登入 | Mapping 綁 provider/model/context/profile 身分；default-off 與漂移拒絕 | 驗證所選入口與 gateway 協定即可；不需要自建 supervisor 或登入 broker |
| A：工具循環、串流、context | 原生 harness 執行工具、接收串流、維護 history／compaction 與 sandbox | 逐模型容量／scope 資格、驗收、獨立 review、context 交接規則 | Gateway 的實際回覆及模型容量／工具相容性；薄 adapter 不重新實作工具 loop |
| B：角色選模與返工 | Custom agents／當次公開模型選擇；CLI app-server 的下一 turn 可指定 model/effort | `agent_routing` classifier、preflight／qualification、返工政策、`model-failover-plan` | 自架候選的當前資格及可用性；既有 planner 已有服務／品質決策，不另建分類器 |
| B：目的地切換 | CLI app-server `thread/start`／`thread/resume` schema 有 `modelProvider`；`turn/start` 有 model/effort，沒有 provider 欄位 | 保留 acceptance／findings／correction lineage、目的地授權與秘密排除 | Provider 跨 session 接續需實測；欄位存在不證明既有對話熱切換，Desktop callable 不提供任意 provider 選擇 |
| C：中斷與背景程序 | `turn/interrupt`；experimental background-terminal list/terminate；session history/resume | 原生 CLI handoff adapter、目前實验 packet journal／containment／checkpoint | 中斷 turn 或終止已知 terminal 不證明所有 detached writer 已失去寫入權；只有需要執行中接手時才需額外可證明的 containment／撤權 |
| C：半成品與正式整合 | 原生檔案／Git／session 工具，不提供本專案的成果採認資格 | generation fence、unknown 不重播、可信 checkpoint、單一 integrator 的進階實验 | 失聯後隔離舊 writer、拒收遲到成果及採認一般來源；不得以 native resume 取代此契約 |

Standalone 與 bundled schema 各自有上述 start/resume/turn/background-terminal
欄位，尚未驗證執行語意。當前 Desktop `codex_app.create_thread`／
`send_message_to_thread` 的公開 schema 僅提供所列官方 model／thinking，沒有
custom provider 欄位；本入口的任意 LiteLLM 目標不相容，其他 UI 入口仍未驗證。
不使用 Desktop private internals，也不從 bundled CLI 推定 Desktop 可派自架模型。

依[官方配置](https://learn.chatgpt.com/docs/config-file/config-reference)，provider
與 profile 等 machine-local keys 不接受 project-local overrides；profiles 使用
user-owned `profile-name.config.toml`，不是共享 repo 設定。現行文件的
`wire_api` 僅列 `responses`。既有直接 Chat Completions、設定解析或連線成功
不能替代所選 Codex 版本的 Responses/tool-result/SSE 實測；gateway 翻譯屬 A
的薄協定邊界，不能順便取得 C 的任務控制權。

Codex 原生 request／stream retry 已有有界設定；B 只處理可查證的服務結果與
跨目標決策，不疊加透明無界重試。失敗、unknown 與原生重試可觀察性不足時
明示限制，不虛構底層 attempt 數量。

## 分層 DoD 與交付

| 層 | 最小 DoD／必要驗證 | 依賴、交付邊界與尚未支援 |
| --- | --- | --- |
| A 基本接入 | 一個具名 runtime／模型／scope 的原生入口：版本與配置身分、實際協定、至少一個工具結果回送後的 continuation、串流終結、獨立結果讀回；逐模型驗證完整 input＋output/reasoning reserve＋margin、正常 compaction，既有 workflow／角色約束不變 | 依賴 gateway 與容量／工具證據。可以有限 scope 獨立交付；短輸入不取得 long-context 資格，未驗證工具／Desktop 入口限制或停用。C 的全部 runtime／故障情境不是前置 |
| B 選模與升級 | 決策部分：既有 classifier 不降低 class/tier、default-off、internal-first、服務／品質分計、兩輪不收斂改診斷、升級 floor／lineage 保留、認證／context／unknown 拒絕；局部正負案例及獨立 review。執行部分另驗證已完成或確定靜止邊界上的合格目標與讀回 | 決策可獨立交付為 advisory，始終 `dispatched: false`。真正切換依賴 A 的各目標資格、授權／秘密排除與所選公開 adapter；尚無合格 executor 時保持未完成，不能稱完整自動切換。沒有背景 writer 的邊界不要求全部 C |
| C 執行中自動接手 | 可信半成品/checkpoint、實際 writer 隔離／撤權、單 owner/generation fence、遲到結果拒絕、unknown 不重播；新副本續作、唯一 integrator 採認及原驗收／獨立 review | 進階獨立範圍；一般來源 authority、登入／provider-client containment、可信時間／撤權、完整選定工具邊界及真實跨來源接手仍未資格。匿名 fixture 不能變成 production 證據；registry 保持空 |

A/B 的完成判定須寫明 runtime、scope 及「決策／執行」部分，不能把 advisory
成功包裝成 B 自動執行。原完整自動接手 DoD 仍未完成，與各層的有限交付分開。
所有既有未取得的 production/native/runtime/adapter/isolation/startup/N1–N4
資格保留 false；建立分層 DoD 不追認舊結果或刷新舊收據。

## 最小路徑與保留／縮減

1. A 先選 standalone CLI → 原生 provider/profile → LiteLLM 相容協定 →
   合成唯讀工具循環 → terminal/result 讀回。僅核准該入口、模型與有限 scope；
   不需要 Docker、supervisor、broker、observer 或成果 integrator。
2. B 先重用現有 mapping／classifier／planner 與局部契約；取得目的模型的 A
   證據後，才在確定靜止邊界驗證下一次公開 dispatch。官方端沿用原生訂閱，
   不新增 paid API，也不複製／抽取登入憑證給 gateway 或新 executor。
3. C 保留既有工程與證據，暫停新增恢復框架、probe 及驗收矩陣。現有
   `model-task-execute` 因 containment registry 為空而拒絕，屬該 advanced
   packet dispatch 路徑的相依；不解除 gate，也不把它套用到全部 A/B。

已證實的重複是「以 C 全量資格統一阻擋 A/B 局部交付」的流程耦合，予以
縮減。Journal／containment／checkpoint／integrator 對 C 有必要；本次有界
查讀未證實可安全刪除它們，不因未 qualification 就刪除 source 或持久狀態。
新 host-control 僅 C 的匿名實驗限制，不增加 A/B authority；HC-02 transcript
檔名碰撞已分開 coordinator/preflight 名稱，通過局部回歸及比例覆核。
尚未重跑實體路徑，不能採認 C pre-execution 通過。

PR #317 目前仍包含 A/B/C 與效率改善的累積工程，不能以 A/B 部分成功宣稱
整份 PR ready。先穩定有限交付範圍；任何 ready/merge/release 前仍審查最新
完整 base-to-head、未解 findings、適用 scan 與平台 gate。Source/package 版本
以 `catalog.yaml` 為準；原 candidate 準備紀錄保留，只證明準備，不證明發布。
發布狀態在 release gate 核對 annotated tag 與非 draft／非 prerelease Release。
有限 A/B 與
效率成果可獨立評估發行，不必等 C 全部完成，但須讓實際 package、PR scope、
active guidance 與 release claims 一致；本次尚未取得該完整 gate，沒有新發行。

113 個現有 mapping／failover 局部案例約 3.47 秒、19 個 workflow smoke 約
0.21 秒；均是本機合成契約，非真實模型資格。既有 review／scan 只重用其
未漂移範圍；新 source/schema／政策另檢查。全流程可比較時間、重讀成本及
節省百分比未知，不另外建立效率治理 ledger。

來源：[Advanced Config](https://learn.chatgpt.com/docs/config-file/config-advanced)、
[App Server](https://learn.chatgpt.com/docs/app-server)、
[Authentication](https://learn.chatgpt.com/docs/auth)。原始 schema、失敗與審查
證據留在 Git 排除位置，文件只保留可重建的查核方式與限制。
