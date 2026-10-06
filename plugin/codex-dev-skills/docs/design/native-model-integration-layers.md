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
| Hermes：接續 | 本機已安裝 source `af8839df10` 的 CLI 有 session ID／`--resume`／`--continue` 及 cwd 恢復；未執行登入或推論 | 已部署 shared workflow 與薄 Hermes adapter；H-04 仍限手動新 session＋repo checkpoint | 原生 history 可重用，不等於 OS writer 隔離、撤權或一般成果採認；本輪不新增 Hermes 自動接手資格 |

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

責任鏈是 dots 派工／協調 → Desktop 建立本地任務 → 本地 agent 使用技能與
工具 → 受管執行器。可靠恢復與安全接手是本地工具能力，人工或 dots 發起
皆適用，仍在 Issue #316 實作範圍。先完成一條最小 C 恢復路徑，再逐步擴充；不把完整 dots
排程、loop、graphic engineering 或 memory 系統拉入本輪。驗收核心是可信
進度、有效 writer 控制、失效成果拒收與安全續作，不承諾任意 detached 程序
全部停止。Codex／Hermes 的 session 接續不能代替檔案隔離與成果 fence。

最小 C 切片先限定：監督端仍健康，執行器在可信 checkpoint 持久化後、釋放
owner 前失聯。監督端記錄實際 wait／EOF；接手端重新讀回原 journal、checkpoint、
owner 與受管 runtime 身分及 writer 狀態，再用既有 lifecycle 釋放／取得 owner，
從 checkpoint 建立新隔離副本續作。舊 generation 的新成果必須拒收，且不能
造成 journal 或工具副作用；原失敗與 unknown 不重播。這個切片解除現有
「有序 quality rework 被當成失聯恢復」的整合證據缺口，不新增恢復框架。

必要驗證是廉價輸入／回覆契約、局部正負案例、一次受控 native 端到端實測、
獨立前置安全審查及穩定工程包的適用 scan。尚不涵蓋監督端自身失聯、任意
失聯位置、一般來源 authority、真實跨 provider／登入 client。
這些相依繼續在同一 Issue 追蹤；局部成功不取得 production qualification。

1. A 先選 standalone CLI → 原生 provider/profile → LiteLLM 相容協定 →
   合成唯讀工具循環 → terminal/result 讀回。僅核准該入口、模型與有限 scope；
   不需要 Docker、supervisor、broker、observer 或成果 integrator。
2. B 先重用現有 mapping／classifier／planner 與局部契約；取得目的模型的 A
   證據後，才在確定靜止邊界驗證下一次公開 dispatch。官方端沿用原生訂閱，
   不新增 paid API，也不複製／抽取登入憑證給 gateway 或新 executor。
3. C 優先完成上述最小失聯恢復切片，重用既有工程與證據；不新增完整恢復
   框架或全 runtime 驗收矩陣。現有
   `model-task-execute` 因 containment registry 為空而拒絕，屬該 advanced
   packet dispatch 路徑的相依；不解除 gate，也不把它套用到全部 A/B。

已證實的重複是「以 C 全量資格統一阻擋 A/B 局部交付」的流程耦合，予以
縮減。Journal／containment／checkpoint／integrator 對 C 有必要；本次有界
查讀未證實可安全刪除它們，不因未 qualification 就刪除 source 或持久狀態。
新 host-control 僅 C 的匿名實驗限制，不增加 A/B authority；HC-02 transcript
檔名碰撞已分開 coordinator/preflight 名稱，通過局部回歸及比例覆核。
2026-10-06 已完成這條受控失聯路徑：producer 在原生 writer 確認停止並封存 C
後、釋放 owner 前退出；fresh consumer 重新核對原證據、取得 generation 2，
於不同隔離副本完成 C2。舊 generation export 與原封存的遲到 publish 均遭拒絕，
未新增 journal／工具效果。這是匿名 fixture 的實體整合證據，不是一般執行器
失聯或 production 資格；正式工程包 gate 與整份 PR readiness 另行判定。

範圍收斂後，只沿用此一受控本地路徑繼續驗收，不為其他 runtime、工具或
失聯時點預建恢復平台。新增的 fixture 把失聯點提前到 C 持久化後、producer
寫交接檔前；存活 coordinator 完成 wait／EOF，fresh consumer 從原 ledger
與不可變 request／execution 重建，重核 writer 停止後才釋放 owner、取得
generation 2。實體路徑驗證舊 generation export 拒收；遲到 publish 拒收仍由
既有局部測試支撐。沒有重用舊 attempt 或增加服務。這不證明任意失聯、
coordinator 重啟、真實 task admission 或 production C。

首輪 consumer 等待逾時，原 attempt 保留 unknown／export-intent，不重播或
追認。依原始 transport 與來源核對耗時，僅調整 verifier 的有界 stage 預算為
producer 140 秒、consumer 220 秒，session 400 秒；保留完整 capture hash、
physical readback、撤銷及 expiry gate。局部契約與比例重審後，以新 fixture
重跑一次，263.35 秒完成。這是一次診斷收斂紀錄，不能推算效率節省百分比。

dots 入口不屬本地工具完成 blocker，也不建立本專案的直接 dots 工具入口。
未來派工若實際改變本地 runtime、權限、授權或工具可用性，再對差異整合
驗證。外部排程或 cloud 配置限制不替代下面的本地 C 缺口；外部 ruleset 不改。

## 本地 C 尚缺能力與下一工程包

原始 C 需求仍是受管執行器失聯後無人值守、安全自動接手。已通過的匿名
路徑只覆蓋健康 coordinator、固定任務／reader、特定退出點及已確認停止的
writer。尚缺能力須在選定本地 scope 補足，不能用未驗證 dots 代替。

| 本地缺口 | 現有可重用能力與缺少的證據 |
| --- | --- |
| 真實 task／source admission | `FixedReader`／固定 grants 不是真實任務授權；需由可信本地 host 綁定一個具名任務的原 acceptance、source 身分、scope、目的地授權與秘密排除，並由既有完整 gates 讀回。一般 JSON／模型自述不能授權 |
| 一般失聯與可信進度讀回 | 現有 actual Popen wait／EOF、immutable journal／C 與原始執行身分可重用；固定 checkpoint 後退出已能不靠 producer 的 handoff 文件續作。其他失聯位置仍須從可信持久狀態判定可續作或 blocked，不能要求失聯執行器最後補文件 |
| 仍存活或未知 writer 的控制 | 新副本與 generation fence 可重用；目前 finish 只接受 stopped，尚須證明舊受管環境無法影響新副本或正式成果，隔離缺證不得釋放 owner／派 successor。不能以 PID 消失代替 writer 控制 |
| 新鮮資格、撤權與服務預算 | Host permit 已有實際 clock、held session 與 sticky revoke；journal reader 的 `now=110`／合成 qualification 仍未證明真實 service elapsed、目標資格或授權撤銷。不得刷新歷史證據補成新資格 |
| 安全續作及成果採認 | C→C2／stale refusal 與既有唯一 integrator 可重用；目前任務、patch、來源 authority 與選模均固定，需驗證所選本地任務的成果與原驗收／review、一般 source integration、必要 provider/context／工具邊界。其餘未用工具保持停用 |

checkpoint 後仍依賴 producer 交接檔的 blocker 已由上述路徑解除。下一個
最小工程包先解除第一項：重用既有 native admission／source readback
與 host-control，在一個具名本地任務建立 host-owned task/source 薄接點；不
新增 supervisor、broker、observer、container 或 integrator。先檢查實際
consumer 型別、原 authority／source 綁定與秘密排除，再驗證撤銷、來源漂移、
偽造 input、未知效果及資格不足拒絕。缺真實 runtime authority／目標資格時
仍不得 dispatch。這只補 task ingress，不宣稱其餘四項或完整 C 已完成。

薄接點先拆成「原始 operator 輸入／來源 consumer 契約」及「真實 authority／
qualification admission」。前者以 `model_task_ingress.py` 唯讀載入 protected
原 request／驗收內容，核對具名任務、目的地及 actual Git／指定內容，接入
`model_task_execution` 與既有 CLI packet 的 claim／launch／seal 邊界。它
與受保護目標在各邊界共同重查，最後以同一個當前時間核對兩者的有效期；
只能增加限制，不能授權。後者仍為本地 C blocker；`NativeLifecycle.admit`
原本即要求完整 authority／qualification，不能將 granted／qualified 寫入
一般 JSON 就視為完成。固定 native source／scope／patch 維持不變。

2026-10-06 已核准預設關閉的受信任本機 host 簽發者作為可用的權限邊界。
每個具名任務先經受信任本機介面核准一次，核准內容固定原驗收／來源、
允許目的地、action、sandbox ceiling 與 grant 最長期限；限期內可自動
接手，不可由 agent 自行擴權或延長原核准。第一包只建 fixture domain 的
發證／讀回／撤權契約，綁原始 task/source、CLI target、action、短期時效
與 sticky revoke。fixture 中 task grant 與每次 session permit 分離，
同一 grant 可涵蓋其允許範圍內的 successor；這仍不證明真實人工核准。
受信任的注入 reader 須在
發證及讀回時重讀受保護 target 原件；失效及時鐘歧義須持久封鎖舊許可。
沒有 production reader 時
不產生正式 grant。原始人工授權須由可信 host 取回，CLI 資格須查回獨立
原證據；`model_execution_target` 的摘要只驗結構與狀態，不能當成來源。
目前公開 app-server 可處理 thread／turn 與核准互動，但此設計不宣稱它會
向技能提供 Desktop 原對話的可驗證授權憑證，也不仰賴未公開 internals。
終端 TTY／同 UID 可寫檔案無法獨立證明核准者；真正簽發者需有 agent
無法自行偽造的本機授權邊界。macOS 與 Linux 各自驗證其公開、可部署的
OS 身分／權限機制及實際安裝條件；未驗證前維持預設關閉。目標 CLI
資格仍須從獨立原證據讀回，不能由授權介面代替。
本輪先不安裝管理員簽發工具；先核對 Codex 本地任務的既有授權與明確 scope
是否足以支撐選定路徑。若需改變原 authority／信任邊界，再以具體差異與
失敗證據決策，不能把 fixture grant 或同 UID 檔案升格為正式許可。
既有 synthetic-only Native guard、固定來源／patch、空 production
containment registry 都保留；fixture permit 不進入正式 admission。

此包仍在 Issue #316；先完成當前工程包的比例重審、適用 SDS 與 draft 保存，
保留全部 unknown／持久狀態，再接續。完整 dots、loop、graphic engineering
及 memory 系統不納入。

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
