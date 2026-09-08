# 原生 Codex 記憶與 MG1 的共存邊界

[Issue #213](https://github.com/jeffery777/codex-dev-skills/issues/213) 的 G0
接受補充。本文是 repository 設計指引，不是記憶 adapter、設定工具或已啟用的功能。
既有 [G0 合成契約](memory-governance-g0-contract.md)的 schema、結果與零接觸語意不變。

## 官方行為與本專案判斷

2026-09-07 讀取的官方文件區分下列能力；可用性與實際開啟狀態須在使用時核對。

| 能力 | 官方已說明的行為 | 對本專案的限制 |
| --- | --- | --- |
| Local Codex Memories | 從符合條件的過往對話背景生成本機記憶，控制使用與生成；與 ChatGPT 網頁記憶分開。 | 是召回來源，不是本專案管理的 M1/MG1 儲存。 |
| 實驗性 context management | `features.context_management.experimental_mode` 使用筆記與可搜尋歷史保存累積細節，預設關閉；有登入方案限制。 | 不能據此推定每個執行環境可用、目前任務已啟用或召回完整無誤。 |
| `/compact` | 壓縮目前對話上下文的指令仍存在。 | 壓縮次數不證明遺失程度，也不單獨構成換任務的理由。 |

來源：[Memories](https://learn.chatgpt.com/docs/customization/memories)、
[設定參考](https://learn.chatgpt.com/docs/config-file/config-reference)、
[CLI 0.153.0 更新紀錄](https://learn.chatgpt.com/docs/changelog)、
[指令說明](https://learn.chatgpt.com/docs/developer-commands)。
官方 Memories 指引也要求必要團隊規則保留在 `AGENTS.md` 或 checked-in documentation。

本專案因此將通用召回視為可利用的原生能力，把 MG1 聚焦於人可盤點、修正、
停止使用與刪除的專案資料。這是設計判斷，尚無本專案實測可量化替代比例或成本節省。
G0 checker 比較呼叫者提供的合成聲明，不讀原生記憶，也不證明模型的回想行為。

## 三層責任

| 層 | 責任與來源 | 使用方式 |
| --- | --- | --- |
| 原生召回 | runtime 擁有的歷史、筆記與個人化記憶 | 提供查找線索；採用前核對目前來源、適用範圍及內容版本。 |
| 專案需求與交付證據 | spec、manifest、Git、驗證、review 及 accepted platform state | 定義任務與證明交付；ledger 的重建狀態仍依其證據契約。 |
| M1/MG1 管理資料 | 明確受管理的 principal/root/item 與版本 | 依本專案的來源、生命週期、授權及範圍契約處理。 |

原生記憶、舊 review 摘要或「先前已核准」的回憶不新增操作權限。
例如回想指出某 commit 已通過 review，應定位該 review 並比對目前 diff 與條件；
不能用它直接宣布新 head 可合併。來源不可得或互相矛盾時保留未知，不補造證據。
原生 recall 也不能自行填入 G0 的 accepted context 或提升為 G1 的可信授權來源。

## 管理目標、更新與刪除

MG1 的人類入口應明示它管理的是專案儲存。當「記住」「修改」「忘掉」未能確定
是 MG1 或原生記憶，且會改變資料目標時，先解析目標；不得對兩個系統都寫入。
在既有明確 MG1 操作流程內，可沿用已確認的儲存範圍，不必每一步重問。

- 不自動讀取或複製原生生成檔案、app history、私人對話或 runtime 資料庫進入 MG1。
- MG1 的 revision、stop、erase 與 proof 只描述其精確受管理範圍；不能控制原生記憶。
- 已知外部副本須在刪除預覽中揭露為範圍外資料；不能把未知副本數填成零。
  列舉外部副本也不提供存取或刪除它們的授權。
- 若舊內容曾出現在對話或工具輸出，即使 MG1 刪除成功，該內容仍可能被原生歷史召回。
  刪除結果應限定為 MG1 受管理內容與已完成階段，不能承諾「所有地方都已忘記」。
- 清除後的舊召回只可當作過時候選；採用仍要核對目前受管理狀態。
  找不到項目不能推定它從未被刪除；重新保存必須有新明確要求、來源驗證與新 identity。

這些是 G1/G2 入口與報告的接受要求，尚未實作自動跨儲存失效或全域去重。

[Issue #231 設計補充](memory-scope-lifecycle-design.md)將 global/project scope 與
managed/document/native backend 分開，並以獨立合成 oracle 驗證固定刪除集合、
逐儲存覆蓋、部分失敗及手動專案退場。它不查找真實記憶、不雙寫、不管理原生
generated state，也不改變 G0 schema。無原生查詢能力時明列 unavailable／unknown；
從 UI 移除、改名、離線或移除 worktree 均不是原生或 MG1 清除授權。

G0 的 `unmanaged_copies` 只校驗顯式合成清單，沒有未知／完整性欄位，不能拿空陣列
證明真實世界沒有副本。G1 的生產 preview 必須另行設計 known/unknown 與覆蓋率語意；
不在現有 v0 加欄位，也不把合成格式默認升為生產格式。

## memory-off 與全新上下文

本專案的 `memory-off` 僅關閉該呼叫的本專案記憶路徑。
G0 CLI 仍會讀取顯式 case 檔；off 不探測或讀取 context 路徑。
這不表示 Codex Memories、ChatGPT memory、history notes 或所有外部資訊均已關閉。
文件中的「零接觸」必須附上被驗證的元件與 I/O 邊界。

依 [context continuity](context-continuity.md)，fresh rollover 不複製來源對話，
且有 checkpoint、唯一寫入者與接手驗證。原生 `new_context` 不自行完成這些交接。
新 task 也可能仍取得既有 Local Memories；「未複製對話」與「沒有原生記憶影響」
須分開驗證。若實驗要求只從 checkpoint 開始，還須限制並確認目的端的記憶注入。
能力不可用或無法證明時使用目前任務重新查證／文件化 fallback，不能宣稱乾淨對照組。

## 後續效益評測的控制條件

此節是尚未執行的評測計畫。G0 合成 conformance 不跑模型，無須為它關閉使用者記憶。
只有要量測實際 agent 召回／token／時間效益時，才需以下控制。

每個 run 至少記錄下列**非內容**資料；真實對話與記憶本文不進公共 Git：

- 精確 repo revision、任務／fixture 身分、模型與推理設定、runtime surface 和版本。
- 原生 Memories 的使用與生成、實驗性 context management，以及本專案 backend
  各自的狀態：`enabled`、`disabled`、`unknown` 或 `unavailable`。
- 狀態的來源、觀察時間與作用範圍；區分使用者設定聲明、CLI feature 輸出與
  當次任務的有效行為。CLI 或 bundled CLI 觀察不自動代表 Desktop 目前任務。
- 記憶 seed／snapshot 的非敏感識別與是否重用、原生生成是否受控、task 是否重新建立，
  以及 warm/cold 條件。無法獨立控制或確認的部分明列為 unknown。

固定 context management 的狀態，再做以下四組；如要研究 context management，
另做一組配對，不混入 M1/MG1 的增益。沒有可用 MG1 runtime 時不得填入其 on 組。

| 組別 | 原生記憶使用 | 本專案 backend | 要回答的問題 |
| --- | --- | --- | --- |
| A | off | off | 無這兩層召回的基準。 |
| B | on | off | 原生召回的影響。 |
| C | off | on | 本專案 backend 的影響。 |
| D | on | on | 共存後的額外效益、重複與矛盾。 |

on 組也要記錄可用記憶的範圍；開關為 on 但沒有可用 seed，不等於測得召回效益。
A–D 全部 run 的原生記憶生成須經確認為 disabled，並固定可用 seed；
或為每個 run 使用經驗證、彼此隔離且不可變的 snapshot，確保背景生成無法改動
任何 run 的輸入。需記錄執行順序、有效 chat-level/global 設定及觀察時間。
各次 run 使用相同任務與可比 seed，避免後一次偷用前一次答案；
未能隔離的對照不得做因果或普遍節省主張。不能為建立對照擅自刪除使用者記憶。
同時量測正確性、條件／例外保留、來源重查、過時採用、重複召回、token、時間及
本專案可量測的儲存／建構成本；未取得的原生成本標示未知。
安全／生命週期驗證獨立通過，不能以更快抵銷錯誤採用或越界。

## G1/G2 應繼承的合成情境

| 情境 | 必須得到的處置 |
| --- | --- |
| 舊原生回憶與目前 repo 來源矛盾 | 重查來源；不以召回自信提升為有效事實。 |
| 原生回憶聲稱已核准或已完成 | 不新增 authority，不填入 accepted evidence。 |
| MG1 已停止／清除，舊對話仍含正文 | MG1 recall 不供應它；外部召回不使舊 identity 復活。 |
| 使用者只說「忘掉」且儲存／效果不清楚 | 不執行變更，先確定儲存與停止使用／刪除效果。 |
| 本專案 off、原生 on 或 unknown | 不稱為無記憶基準；G0 元件測試仍可獨立有效。 |
| 新 task 或 new_context 缺少目的端有效狀態 | 不宣稱原生記憶隔離或已完成寫入者交接。 |

這張表是後續驗收情境，**不是新增可執行測試或通過紀錄**。
目前證據及待接受事項見 [G0 接受資料](loops/issue-213/g0-acceptance.md)。
