# Issue #323：原生模型入口與建議式返工驗收

追蹤：[Issue #323](https://github.com/jeffery777/codex-dev-skills/issues/323)。
[#322](https://github.com/jeffery777/codex-dev-skills/pull/322) 已交付預設停用的角色映射與
`dispatched: false` 的 failover 建議器；本計畫不把它們視為實際派工。
[#317](https://github.com/jeffery777/codex-dev-skills/pull/317) 保持 draft，C 的原始
程式與證據繼續保留。先驗收 A/B 的公開原生入口，只有實測證明必要時才加入
有界接線；C 的失聯接手不作為普通模型選擇的前置條件。

2026-10-08 使用者選定的第一個交付切片是**同 provider 的原生主對話與
子代理有限能力**。官方↔本地跨 provider 不作為此切片的通過條件，也不能
因此宣稱已支援；C 保留在 #317 draft，暫緩。各專案主對話的 provider
須由使用者層級配置或當次公開入口明確選擇，不能靠專案配置或角色 TOML
暗中切換。B 的實際派工仍須通過下列獨立門檻，目前保持純建議。

## 當前公開契約與點時觀測

依[官方 subagent 文件](https://learn.chatgpt.com/docs/agent-configuration/subagents)，
custom-agent TOML 由 Codex 委派機制載入，仍是原生子代理；使用 LiteLLM 不改變
此身分。該文件描述模型與 effort 的角色覆寫，但 provider 須另核對：Codex
[已合併的角色限制變更](https://github.com/openai/codex/pull/39299)明定 role 不改變
父代理 provider；該次[固定版本的公開實作](https://github.com/openai/codex/blob/1a6e07a4febcc0ecfa04464f5e95cb47144cd746/codex-rs/core/src/agent/role.rs)
的有界覆寫欄位包含 `model`，不含 `model_provider`。CLI `-c` 另有最高設定
優先序，但它不是本次「模型名稱換了、provider 未換」的唯一解釋：官方父代理
的測試沒有以 `-c model_provider` 指定父 provider，仍在子代理啟動前被官方
模型支援檢查拒絕。

2026-10-08 合成唯讀短任務的點時觀測如下；真實紀錄與錯誤細節保留在私人
驗證位置，公開 repo 不保存 gateway alias、URL、credential 或 transcript。
此表不代表正式角色、容量或 Desktop 資格。

| 組合 | Standalone CLI `0.159.3` | Bundled CLI `0.162.0-alpha.2` |
| --- | --- | --- |
| 官方／本地主代理單輪工具循環 | 各自通過 | 各自通過 |
| 官方→官方子代理（父子配置同一模型） | 工具與結果讀回通過；子代理實際模型身分尚未獨立驗證 | 工具與結果讀回通過；子代理實際模型身分尚未獨立驗證 |
| 本地→本地子代理（父子配置同一模型） | 工具與結果讀回通過；子代理實際模型身分尚未獨立驗證 | 工具與結果讀回通過；子代理實際模型身分尚未獨立驗證 |
| 本地→本地子代理（不同模型） | gateway 單次短請求通過；原生子代理遭服務端錯誤，未完成工具循環 | 尚未實測 |
| 官方→本地子代理 | 子代理選到本地模型名，但官方帳戶路由拒絕；未執行工具 | 同類模型支援拒絕；未執行工具 |
| 本地→官方子代理 | 子代理選到官方模型名，但本地 gateway 拒絕；未執行工具 | 同類 gateway 拒絕；未執行工具 |

本地 gateway 的受限錯誤紀錄有兩次官方模型名的無效請求，與兩個
「本地→官方」失敗相符；這是請求實際到達本地 gateway 的佐證，不用模型
自述判定路由。「官方→本地」的帳戶拒絕與父 provider 保留相符，但未由
gateway 日誌缺席單獨證明所有可能配置。上述測試使用暫時的公開 CLI
`-c` 與 role TOML；不能推論未受測版本或所有使用者層級配置均不支援。
父子配置同模型的通過只證明子代理工具循環，不能由配置推定實際子代理
模型身分。不同本地模型的原生子代理試驗收到服務端錯誤，只能記為該組合未完成；
單次 API 請求成功不能替代 CLI 子代理工具循環，也不能由此歸咎 provider
繼承或推論整個模型家族失敗。

Desktop 與 bundled CLI 分開：官方[macOS gateway 指引](https://learn.chatgpt.com/docs/enterprise/connect-to-a-gateway)
說明 app 讀取同一使用者 `config.toml`，但需重啟、確認 credential 到達 app
程序，並在 app 中檢查選模與 gateway 實際路由。本輪沒有取得 Desktop
主／子代理的 live provider 路由證據，故標為尚未驗證；bundled CLI 的結果
不能代替 Desktop。

## A：逐入口驗收矩陣

以下是完整後續矩陣；本期只嘗試其中同 provider 的有限切片，跨 provider
與 Desktop 缺口保持可見，不作為本期通過聲明。每列以確切 CLI／Desktop
版本、入口、主／子代理、provider、模型、role、
scope、配置摘要與時間界定；一列成功不能推定另一列。從一個官方訂閱模型、
一個經授權的本地 gateway 模型、一個代表性角色與唯讀合成任務開始。

| 入口 | 必須分別驗證的路由 | 最小執行證據 |
| --- | --- | --- |
| Standalone CLI | 官方／本地主代理；官方→官方、本地→本地、官方→本地、本地→官方子代理 | 公開選模與角色載入、實際 provider／model 身分、工具呼叫→結果回送→續答、串流終結、子代理獨立工具事件 |
| Bundled CLI | 同上，使用 bundled executable 獨立執行 | 同上；不能沿用 standalone 結果 |
| Desktop | 公開模型選單、custom role 與 callable 所實際支援的組合 | 公開介面選定與當次執行／讀回；bundled CLI 成功不能代替 Desktop |

每個被採用的模型另需經實際部署證明 catalog 載入、input／output／合計限制、
推理 token 計算、長 context、壓縮後工具續答、取消與失敗後狀態；代表性同
scope 任務須完成品質評估與獨立審查。短檔案的工具循環只證明該入口的有界
傳輸，不資格化長 context、角色 tier 或完整工程交付。若事件不能讀回實際
provider／model 身分，將該欄標成「尚未驗證」，不得由配置值推定。
本輪本地 gateway 的 `/v1/models` 可列出兩個受測模型，但其回應未提供
`max_input_tokens`、`max_output_tokens` 或合計容量；不能以 alias 或短請求
填補正式 `context_policy`。在後端容量、逐模型 catalog 與代表性品質證據
取得前，受保護的正式角色 mapping 維持停用。

使用隔離的使用者層級配置與合成資料；不變更共享 provider 設定或將公司
alias、URL、credential、host 路徑、原始 transcript 放入此公開 repository。
真實執行紀錄留在受限且 Git 忽略的位置，公開文件只記錄可重跑條件、
去識別化的狀態與限制。憑證使用及資料目的地須在每次入口試驗前取得有效
授權；未授權或受執行環境限制時，標示未完成而不換私有介面。

## B：只在已驗證入口接線

先保持 `model-failover-plan` 純建議。若 A 的某個確切入口／role／scope
通過驗收，才考慮把**同 provider** 的一個 `planned` 目標接到該公開
原生 executor；既有 policy chain 的官方終點若需跨 provider，在本切片
必須停在建議狀態。接線前讀回
當前 provider、官方訂閱／gateway 計費身分、目的地授權、role 資格、
secret 排除、context 與原任務 sandbox；不能以 `planned` 當作派工收據。

首次只處理主代理仍存活、前一 attempt 已完成或已知靜止的單一唯讀任務。
依序驗證服務不可用的有界重試、已確認的品質不足與獨立返工診斷、
auth／permission／context／配置錯誤不 fallback、同任務 correction lineage
與冷卻。結果必須獨立讀回；任何副作用或上次 attempt 狀態不明即停止自動
重派，記錄 unknown，不猜測成功或重新執行。跨 provider 若公開子代理入口
不能選定目標，可標成有限或尚未支援；另開 CLI session 必須另列為獨立
executor 設計與驗收，不能聲稱它已滿足原生子代理的跨 provider 需求。

普通 A/B 不使用 #317 的 target、packet、supervisor 或 Git 自動套用器。
若後續決定啟用 #317 的直接 typed handoff／Git 整合，先處理其部分寫入
unknown 收據、啟動前 target 期限重查及實際 command schema 指引，並重做
完整 base-to-head 審查；C 的空 production registry 不會關閉直接路徑。

## 狀態與交付門檻

「完整支援」須具備該確切入口、路由、role 與 scope 的真實執行、容量、品質、
權限和結果讀回；「有限支援」須明列已通過的較窄邊界；未執行、無法觀察
身分或公開入口不支援時標「尚未支援／尚未驗證」。API、help、配置解析、
合成測試及其他入口的成功不能升級這些狀態。

程式接線若產生，需完成相應測試、套件同步、獨立審查、安全差異掃描、
完整 base-to-head Merge Review 與 hosted checks。完成任何 A/B 切片都不
表示 C、#317 或發行已完成；各自保持獨立 gate。
