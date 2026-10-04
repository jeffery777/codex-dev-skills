# Issue #316 本機角色模型映射工程計畫

## 需求與範圍

提供 default-off、provider-neutral 的本機角色模型映射。只有受保護的使用者
配置可以替換模型與 effort；保留 canonical class/tier、指令、sandbox、scope、
獨立 review、操作授權與完成契約。配置不進共享 Git 或套件。

CLI 與 Desktop 分別依公開 runtime 介面驗證；不依賴 private API，不從傳輸
成功推定正式角色資格。操作與 schema 見[指南](../guides/local-model-mapping.md)。

## 自動路由擴充需求

本 Issue 後續範圍包含自架與官方模型同時可用的 internal-first 路由，以及
服務失敗與品質返工兩條獨立升級路徑。以下是待實作與驗證的目標，現有
schema 1 mapping 不具備這些自動切換能力，不得以原有測試通過宣稱完成。

沿用既有 `agent_routing.classify_task`、profile preflight／qualification 及
`model-selection-policy.md` 的返工重評規則。官方單一 provider 的既有選模
流程繼續適用；自架目標是新增候選及執行入口，不另建部署者專屬選模腦或另訂
修補門檻。新增 helper 只處理供應商順序、服務預算與返工 lineage 的下一步意圖，
由既有 V2 classifier 綁定當前 class/tier/scope，不得以自填較低要求繞過分類。

| 情境 | 目標行為 |
| --- | --- |
| 自架與官方均可用 | 優先使用適合角色與工作範圍、已取得資格的自架模型。 |
| 已取得新鮮證據確認自架服務不可達 | 略過自架來源重試，選擇已核准且可用的官方模型；不能只憑位置或網路名稱判斷。 |
| 可重試服務錯誤 | 在有界次數及總時間內重試，持續失敗後轉官方；冷卻期間不逐請求重走失敗鏈。 |
| 合理修補後同一核心驗收仍失敗 | 重新分類並補足診斷；能力不足時先升到同角色／scope 已資格的自架來源最高能力目標。 |
| 同工作包兩輪修補陸續出現不同缺陷 | 保留 correction lineage，檢查完整工作流及契約；能力不足時依相同鏈升級，不因 A 變 B 清零。 |
| 自架來源最高能力目標仍無法修復 | 以原驗收與診斷證據轉到已核准的官方目標；重新驗證及獨立 review。 |

「最高能力」由實際角色品質與 class/tier 資格決定，不能由名稱、供應商、
effort 或可連線狀態推定。官方階段仍失敗時改變診斷／方法並持續已授權工作；
不無限升級、循環切模，亦不因達門檻直接停止或放寬驗收。

服務重試與品質修補分別計數。一輪品質修補必須含修正假設、修改與指定驗收；
review finding 本身不等於已完成一輪修補。Scope 真正新增須明確分類，舊失敗
仍保留。環境／權限／資料缺口、context 超限、認證／配置錯誤及外部寫入結果
不明不能直接算作能力不足或通用服務 fallback；外部結果先獨立讀回。

採用者可以預先核准所有本機開發任務使用官方目標，但仍排除憑證與機密。
授權保存在受保護的本機 policy，綁定目標、scope 與可撤銷狀態，不成為套件
對所有使用者的預設授權。送出前須核對輸入、工具結果、歷史與交接包的排除
條件；未知或無法排除的內容不可跨目的地轉送。不得把敏感全文留在證據中。

任務重新分類而提高 tier 時，下一個目的地須符合最新 V2 requirements；已完成
的歷史來源則須核對原 dispatch 當時的合法分類，不能因舊 tier 低於新需求而
阻擋升級。例外須由可信 host 讀回原 request／route receipt、實際 attempt 與
完整 correction lineage，綁定現有 ledger；歷史摘要或可自填的舊 tier 不足以
放行。原 route 的 hash 正確也不能代替有效的 path assignment、disjoint ownership
與同 task／scope／acceptance 綁定的原 authority contract。首包限定同 class 的
tier 提升，當前授權、撤銷、身分、scope 與新鮮度
防護不變；再次選取低 tier 來源仍須拒絕。

### 決策與執行分層

1. 既有選模流程讀取受保護 policy、新鮮可用性／資格及 correction lineage，產出
   可重建的下一步與原因；決策成功不代表 runtime 已執行切換。
2. 執行 adapter 只能使用當次公開 CLI／Desktop 能力，綁定實際 provider、
   model、effort、profile、catalog/context 與目的地。缺公開能力標示未完成，
   不改 private internals，也不以設定檔變更冒充本回合已切模。
3. 切換時建立有界交接包，保留原驗收、finding 處置、目前 diff 與失敗 lineage；
   不盲目重播已執行工具或外部寫入，不拼接不同模型的部分串流回應。
4. 每個目標按實際 input/output/total/reasoning 限制重新核對完整輸入及預留；
   需要時先壓縮或重建交接包。容量不明、不能安全縮減或工具不相容時不可送出。
5. Gateway 的 API retry/fallback 僅處理服務錯誤；品質升級由工程 workflow
   根據驗收與 review 證據決定。透明 alias 換後端仍須識別實際目標及 context，
   不能沿用原模型資格與容量。

本次官方存取路徑明確採用 Codex ChatGPT 登入／訂閱；不新增 OpenAI API
費用，不把 LiteLLM 的 OpenAI API upstream 當成訂閱 fallback。自架端可使用
本機 gateway，官方端須由 Codex 原生訂閱入口執行。不得將 Codex 登入憑證
抽出交給 LiteLLM。兩端的公開執行能力與資料處理政策分別核對。依
[官方驗證方式](https://developers.openai.com/codex/auth)核對；服務路由可參考
[LiteLLM Router](https://docs.litellm.ai/docs/routing)，文件能力不等於本機版本已驗證。

### 擴充驗收

- 離線合成案例涵蓋自架來源優先、自架來源不可達、重試耗盡／冷卻、自架來源高能力及官方
  品質升級、A→B 回歸不清零、原因未知先診斷、外部結果未知不重播。
- 撤銷／scope／資格／目的地漂移、秘密／機密輸入、較小 context、catalog
  同名模型衝突、工具不相容均須拒絕不安全 dispatch；不僅驗證 selector 輸出。
- 公開 adapter 的合成主／子代理循環及切換後讀回另行驗證；Desktop 與兩種
  CLI 各自標示支援與缺口，未完成 adapter 不宣稱端到端自動化。
- 新增跨目的地及返工控制的完整獨立 review、Security Diff Scan 與 changed-head
  Merge Review；原 mapping 審查僅可重用未變動的部分。完成前不合併／發行舊範圍。

### 中斷接手與恢復規則

接手沿用既有 context-continuity 的 digest-bound checkpoint、單一 writer、
lineage 及不重播契約。模型失去連線不代表原程序停止；新執行者啟動前須由
可信 runtime 確認舊程序及其寫入子程序已停止，並重新核對工作目錄現況。
無法確認停止時保留結果不明狀態；只有下述隔離、撤銷與可信 checkpoint 條件全部成立，才允許在另一個副本接手。

Checkpoint 保留原目標與驗收、repository／branch／HEAD、tracked 與 untracked
修改的有界快照、已完成與未完成步驟、測試／finding 處置、失敗與升級原因、
外部操作的已知及未知結果。不得保存憑證或機密；不能以摘要代替實際 diff
及讀回證據，亦不串接中斷的工具參數或模型串流。新目標重新核對整個交接
輸入的 context 預算、資格及資料目的地授權。

接手中的目標保持 ownership，原服務恢復不造成搶占。當前工作單元完成、
產生 checkpoint 且停止 writer 後，才重新評估下一單元；服務可用性恢復須
有新鮮證據及冷卻判定。品質不足導致的升級設為當前任務的最低能力要求，
不能由服務恢復降級或清除 correction lineage。新獨立任務重新分類。

外部寫入 unknown 先獨立查讀，將查證結論追加到原 lineage；不能刪除失敗
事件、把 unknown 改成未執行或重新送出同一操作。接手再次中斷也沿用同一
任務、驗收、ownership 與交接鏈，不重設返工／服務預算。

既有 CLI private-clone executor 僅接受 clean exact source；typed target 支援
不改此條件。半成品交接仍須完成獨立設計與驗證，不能自動 commit 使用者
修改、清掉 dirty files 或偷偷放寬 executor 來取得接手能力。當前一包 dispatch
介面不是持久接手 controller，亦未證明真實 provider 或 production 資格。

必要故障案例包括：寫檔中斷、舊程序尚活著、cleanup 失敗、外寫已成功但回應
遺失、快照後檔案漂移、接手再次中斷、原服務中途恢復、較小 context、以及
重啟後 checkpoint／dispatch replay。所有案例須核對實際 dispatch 與檔案，
不能僅測 selector 意圖。上述行為須經 Astra 深入設計審查及獨立實作審查。

### 持久工作包協調器設計草案

下列是接手 blocker 的修正方向，尚待設計審查與實作，不是現有功能。
父代理保留交付與整合責任；自架及官方模型僅執行有界工作包。協調器不另建
選模分類或品質規則，使用同一 V2 classifier、provider 順位與返工 lineage。

| 狀態 | 必須保留的事實與下一步 |
| --- | --- |
| ready | 已驗證 checkpoint、原始 source 身分／digest、尚無 active attempt。 |
| claimed | 在受保護本機紀錄原子保留 attempt ID／target binding／checkpoint；重播不再啟動。 |
| running | 紀錄 runtime process identity 與唯一 packet writer；服務恢復不能搶占。 |
| reconciling | 中斷、失敗或重啟後讀回受控執行邊界已停止，或確認舊副本已隔離且結果採用權已撤銷；程序樹掃描不足以建立此證據。再核對可封存成果與未知外寫。 |
| checkpointed | 停止寫入後保存修改 digest、驗收／返工／讀回證據；選模前重新核對容量與授權。 |
| integration-ready | 完整驗證與獨立 review 通過，父代理再核對 source 沒有漂移，僅整合已審內容。 |
| blocked | ownership、結果或 snapshot 無法查明；保留成果及紀錄，拒絕相依 dispatch。 |

`claimed` 與 `running` 在 crash 後均不能靠時間過期當成未執行；lease／冷卻
只控制選模頻率，不是停止程序的證明。Ledger lock 忙碌立即拒絕；不能刪除
或重建 ledger 解除未知狀態。恢復使用追加的查證紀錄，綁定原 attempt、
checkpoint 與操作 identity，保留原先的不確定事件。

Privately fenced packet workspace 必須由可信 executor 建立及管理。失敗時
不整合半成品、不清掉可恢復的私有修改；成功的一輪也先保留 checkpoint，
讓下一輪在同一隔離任務成果上修補，直到整體驗收及 review 通過才整合。
初始 user source 的 dirty files 不得自動 commit 或覆寫；若納入受控快照，
需先完成非秘密內容檢查、檔案型別／path／大小限制與一致性核對。

任何 attempt 都不得重新取得 commit／push／PR／deploy 權限；外部寫入由
父代理原有授權與 gate 管理。協調器沒有可信外部結果讀回能力時保留 blocked，
不能由子模型文字、自填 JSON 的 `stopped: true` 或 exit code 推定安全接手。

### Writer containment 資格缺口與待決範圍

深入 review 的受控本機程序反例顯示：root process 在首次 inventory 前已退出，
detached descendant 仍存活時，既有 polling tracker 可返回成功。Polling 不能
證明從未觀測到的子程序不存在；即使補強 root birth identity 也不能據此完成
writer containment 資格。Portable 公開 CLI 尚無本專案已資格的完整停止保證。

因此 `PACKET_STOP_ADAPTERS` production 清冊維持空，packet executor 及共用
consumer 在派工前拒絕未資格的執行路徑。測試的 synthetic stop adapter 不得
被當成 production adoption。現在已實作的 durable claim／checkpoint primitive
及受控接線保留，不能以其離線測試通過取代停止保證。

採用隔離副本、可信監督器及單一成果整合器的完整寫入路徑。模型及其背景
程序只能修改本次 attempt 的副本；來源、封存 checkpoint、ledger、其他副本、
主機控制介面與憑證不得暴露為可寫資源。不同目錄或同 UID 的權限不足以證明隔離。

舊執行環境無法確認停止時，僅在可信主機即時讀回隔離仍有效、外部效果已排除、
舊 generation 已撤銷結果採用權後，允許新副本從上一個封存 checkpoint 接手。
不讀取舊環境的即時半成品，亦不把 quarantine 記為程序已停止。晚到結果必須拒收。
原模型恢復不搶占目前 attempt；工作單元完成後才重新評估。

Linux 優先資格化受限 rootless container 與受控生命週期；cgroup 只提供程序與
資源管理，另需檔案、憑證、控制介面及網路隔離。Mac 可使用本機 Docker Linux VM
提供相同邊界，或其他獨立資格的隔離環境。公開 CLI 的 native permission profile 可作另一候選，
但 shell 的讀寫拒絕不能證明內建工具、繼承 FD、子程序、網路與憑證排除全部合格；
每個入口均須逐項驗證。未具備資格時保留安全暫停與確認停止後
續作。這些規則也適用官方訂閱模型的服務失敗，不能推導 API 付費 fallback。

合成容器測試只能驗證有限的隔離性質。正式 adoption 仍須驗證啟動前隔離、重啟、
撤銷、可信輸出擷取、外部效果讀回及成果整合；production adapter 清冊在完整資格
通過前維持空，不因單一主機測試成功開放自動接手。

正式資格依下列順序完成，每項須綁定執行檔、profile、工具清冊與環境身分，
不能由其他主機或入口的合成測試代替：

1. N1：檔案讀寫、rename、link、symlink、繼承 FD、背景／脫離程序，及 TCP、
   UDP、Unix socket 的邊界；另核對控制介面、資源上限及重啟後隔離是否仍有效。
2. N2：使用合成 provider 驅動真正 CLI dispatcher，逐項驗證所有啟用工具、
   nested CLI、hooks、project config 與 escalation；未驗證入口停用。未解析
   native metadata 的實驗不得作為工具清冊資格。
3. N3：可信 prepare／launch／inspect／quarantine／export 與唯一整合器，
   驗證 crash、重啟、撤銷、late result fencing、checkpoint 擷取及重放邊界。
4. N4：逐 provider 驗證真實自架來源登入及官方訂閱入口、credential broker 與
   機密排除；以當前 context、能力及授權證據完成新 target 的資格。

本 Issue 的發行評估必須涵蓋上述資格與端到端交付驗收。只有合成隔離測試、
default-off primitive 或純選模決策通過時，不得以完整自動切換功能發行。
控制面與 worker bridge 的候選設計及公開 CLI 限制見
[隔離模型執行與可信接手](../design/isolated-model-execution.md)。

### 可重跑的局部驗證與剩餘資格

N3-A 已提供 host-injected backend 的 durable supervisor：啟動前保留 runtime
身分及 launch intent，恢復只 inspect 原 runtime，不重播 launch；停止及封存
成果經綁定與 generation fence 後產生 integration candidate。Unknown observations
保留於同一 ledger，查證後追加 resolution，不刪除原事件。Candidate 讀回同時
核對實際 checkpoint 與 sealed bytes；合法空 patch 仍須通過相同控制。
此介面另接入固定合成 recipe 的本機 Docker backend（N3-B1）；create 後的
physical descriptor 必須在同一 ledger 封存，才可 start。恢復只讀回 exact ID，
回覆遺失不重建或重啟。Bounded export 不執行 worker Git，累積 checkpoint
不丟失前輪成果。Production backend／來源整合器仍未資格化，亦未驗 daemon restart。
原始 execution 身分的首次採認仍須 qualifier；共享 daemon 的首次啟停時間
觀察不能排除曾再次 start，缺證明時不發布 integration candidate。

B2 已實作私有、獨占 synthetic Git source 的唯一整合 fixture；固定 add-update
與 noop 產生持久 intent，crash／reply-lost 只讀回，部分完成保留 unknown。
授權與驗收／review artifacts 僅供固定 fixture，不授予使用者 repository 寫入權。
Schema4 與原 ledger 共存；任何 integration record 阻擋後續 claim，正式整合後
續作尚未資格化。CLI／Docker 實測須另有當前入口證據，單元測試不代替它。

N1 probe 擴充固定合成檔案、rename、hardlink、symlink、繼承 FD、背景程序與
TCP／UDP／Unix socket 正反控制。缺少工具或正控制失敗時保留 unknown；不能
以工具不存在推定隔離成功。它尚不涵蓋 detached Codex、重啟及全部資源邊界。
N2 的固定 PreToolUse hook 故障案例需先讀回 hook 執行標記，再核對 OS 唯讀
邊界；hook 錯誤不能成為唯一寫入防線。全部啟用工具與配置入口仍須資格化。

官方訂閱另有固定無工具回覆 smoke probe，保留實際 CLI、catalog、使用者
instructions digest 與診斷計數，不抽取登入憑證。短請求成功不證明角色品質、
完整 context、credential broker 或 provider/model 獨立讀回；未解的 CLI
diagnostic 仍記為缺口。自架模型不可達時仍可完成以上實作與合成驗證，自架來源
真實連線、工具循環、品質升級及接手驗收則延後，不能宣稱端到端完成。

對未曾派工的不可達自架來源，選模介面可由可信 host 注入 `UnusedSourceGuard`：
真正 packet ledger 須已存在且從未使用，另有新鮮治理讀回，綁定身分、授權、
撤銷、task／scope／acceptance 與舊能力證據。只有能力資格 TTL 過期可被略過；
官方目的地仍須全部新鮮資格。JSON 或空 events 不能建立此權限；缺 guard 保留
原保守行為。此規劃 snapshot 不授予 dispatch，production governance reader
及 executor 的再次核對仍須另外接入。

匿名 public app-server probe 另驗證 no-environment 與固定 dynamic tool 的有限
正反控制；host-only stdio transport 保留 unknown、不重播及 direct-child-only
退出讀回。它仍未建立完整工具／憑證清冊、隔離 worker bridge 或實際派工能力，
也未將 C1 治理 reservation 轉為 executor claim。自架來源不可達不是這些本機接線
工作的阻擋原因，不能把待自架來源驗收誤寫成唯一剩餘項目。

匿名配置觀察另使用 public config／requirements／thread feature／MCP status
readback；固定保留啟動前隔離與 thread 快照未資格化，未知配置在模型 turn 前
停止。專用官方訂閱 home 的登入流程仍需採用者確認，不能抽取目前登入憑證。
單一 ledger 的實際 execution claim／lifecycle 接線須先完成 v6 設計審查；
v5 reservation 不因 metadata 觀察成功而取得 writer 權限。

## 設計與實作順序

1. 核對公開 runtime/schema，使用有界合成資料驗證主／子代理工具循環。
2. 載入 protected default-off store，只允許 model/effort 兩欄替換。
3. 綁定當前 provider、runtime、model/effort、canonical/effective profile、scope、
   quality/context evidence 與逐模型 catalog；缺件或漂移停止。
4. 在 route/receipt/integration 重新驗證資格與新鮮度，禁止靜默 fallback。
5. Installer 保留 user-owned target，同步文件、測試及 generated package。

## Schema 1 的 Context 與驗收條件

- 未啟用時保留 baseline；啟用不能降低 class/tier、擴權或切換資料目的地。
- 無效、不可用、撤銷、漂移、scope/runtime 不符皆停止，不自動換 provider/model。
- 更新不得覆寫 user mapping；consumer 拒絕損壞 receipt 時保留既有回報契約。
- 逐模型核對實際部署的 input/output/合計限制、推理計算與超限行為。
- 完整輸入加輸出／推理預留與安全餘裕不得超過實際容量，提前壓縮。
- 容量未知時不採用；設定合理性檢查不能取代逐 request enforcement。
- 真實 catalog 載入、長上下文、壓縮後工具續答與角色品質須另外取得證據。
- 不把 standalone CLI 的驗證當成 Desktop 保證；不把合成資格當 production 資格。
- 自架後端／gateway 離線時不得自動跨 provider 切回官方模型。Unavailable facts
  應停止路由；尚未觀察到離線的 facts 不保證請求成功。網路環境切換須重新
  核對 provider、store、baseline 角色載入、catalog/context 與 runtime facts。

以上是現有 schema 1 的邊界；自動路由擴充必須另外明確啟用及完成前述驗收，
不能把配置損壞、資格撤銷或目的地漂移解讀為可 fallback 的服務錯誤。

## 證據位置與重建

需求、設計、測試與以下程序受 Git 追蹤。執行輸出與 review/gate 收據存放
`.work/verification/issue-316/`，已由 `.gitignore` 排除。歷次輸出使用不同 run
目錄，保留失敗及過期結果。它們不是套件內容，也不能提交為公開文件。

在 repository root 使用以下程序；不連線自架 gateway，不修改 provider 配置。
全部 Python 驗證使用 pinned resolver。先核對 working tree，確保新的受審檔案
已納入 Git diff；未追蹤來源須另列路徑與內容 digest，不能只記 HEAD。

```sh
mkdir -p .work/verification/issue-316
evidence_dir=$(mktemp -d .work/verification/issue-316/run-XXXXXX)
git rev-parse HEAD > "$evidence_dir/head.txt"
git diff --binary HEAD > "$evidence_dir/working-tree.patch"
git status --short > "$evidence_dir/status.txt"
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(sys.version); print(yaml.__version__)' > "$evidence_dir/environment.txt" 2>&1
printf '%s\n' "$?" > "$evidence_dir/environment.exit"
./scripts/project-python -m unittest tests.test_loopctl tests.test_local_model_mapping tests.test_agent_routing -q > "$evidence_dir/tests.log" 2>&1
printf '%s\n' "$?" > "$evidence_dir/tests.exit"
./scripts/validate-repo.sh --skip-unit-tests > "$evidence_dir/structure.log" 2>&1
printf '%s\n' "$?" > "$evidence_dir/structure.exit"
./scripts/project-python scripts/sync-plugin-package.py > "$evidence_dir/package.log" 2>&1
printf '%s\n' "$?" > "$evidence_dir/package.exit"
git diff --check > "$evidence_dir/diff-check.log" 2>&1
printf '%s\n' "$?" > "$evidence_dir/diff-check.exit"
git diff --binary HEAD > "$evidence_dir/working-tree-after.patch"
cmp "$evidence_dir/working-tree.patch" "$evidence_dir/working-tree-after.patch"
printf '%s\n' "$?" > "$evidence_dir/source-stability.exit"
```

必要時另在新 run 目錄執行全量：

```sh
./scripts/project-python -m unittest discover -s tests -q > "$evidence_dir/full-tests.log" 2>&1
printf '%s\n' "$?" > "$evidence_dir/full-tests.exit"
```

核對所有退出碼與 log；有缺件、失敗、略過或來源漂移不能直接判 PASS。
`--skip-unit-tests` 只驗證結構，不能稱全量測試通過。比例重驗須在 review
收據說明修正範圍、未重跑項目及重用證據的理由；保留原失敗結果。

以上可重建離線驗證的內容與判定，時間／耗時等欄位不保證相同。Runtime
PoC、模型品質、容量與 Security Diff Scan／人工 review 必須另外按當前環境
重新執行；不能由單元測試產生先前的 scan ID、finding 處置或 live 觀察。

## Review 與交付邊界

Code review 檢查實作、驗收條件、適用證據與 finding 處置；merge review
重新核對當前完整 base-to-head、來源／diff digest、證據範圍、新鮮度與剩餘缺口。
Reviewer 不能只看 PASS 摘要；本機證據不在其 checkout 時須重跑，或使用核可
artifact 交換機制。Security 原生 scan 收據留在工具管理位置，以 ID／digest
定位，不搬入追蹤文件，也不宣稱測試可以重建安全分析結論。

本項為 additive pre-1.0 minor candidate；source/package 版本依 catalog，
候選紀錄與 publication truth 分離。Commit/content push／PR、exact-head、
merge、tag/Release、安裝與清理各自核對授權與 gate。既有 memory production、
M2／V3-C gates 維持不變。


### v6 前置：共用持鎖規劃接口

`PacketStore.planning_context(fd)` 只在 caller 已取得同一 store lock 時建立
host-only context；UG／HSG／RUG 與 V2 classifier 共用同一 snapshot，不再次
取鎖。Context 離開交易即失效，前後核對原始 ledger bytes、store、完整 root／ancestor、lock FD／path 與 directory
identity；沒有 JSON loader，也不授予 dispatch authority。既有 v2–v4 證據
仍按原規則核對；v5／v6 尚未接入，不能把這一前置接口當成 execution claim。

下一包採單一 ordered journal 的 v6 全部 synthetic lifecycle：原治理 request
與實際 execution request 分別保存；acquire、once-launch、unknown readback、
checkpoint、terminal release 及 successor 共用同一歷史與預算。正常 completed
先作為 objective terminal，不能偽造 failure 或清空 history。非空 v2–v5 不遷移，
沒有可信 objective locator 或停止／隔離證據就拒絕接手。完整流程與 crash、
revocation、alias、原始 bytes 漂移負例須同包審查，production registry 保持空。


### v6 synthetic lifecycle 候選範圍

候選實作已接同一 ledger 的 admit／actual acquire／once-launch／unknown
observation／cause resolution／seal／publish／terminal release／successor。
不重播 launch／export；隔離存續時從先前可信 checkpoint 或初始 source 接手。
正常 completed 關閉 objective，不增造服務或品質失敗。原始 events、獨立的治理
與 execution bytes、floors、預算及 canonical alias locator 均持久保存並完整回放。
Revocation 保留 host containment 讀回，禁止新模型效果。舊入口與非空 v2–v5
不遷移、不降版，dirty source 不採認。

效果前與成果採用前另重核來源、sticky revocation 與 retained writer containment；
acquire 後的漂移不能沿用先前許可。Export intent crash 的安全 quarantine 不重播
export，保留 predecessor 及原始失敗計數。Execution generation 與 owner epoch
採嚴格整數契約，bool／float 不能作為相同值採認。

驗收以 synthetic 固定 backend 與獨立 host 原始檔案為限，尚不接實際 provider、
Docker／app-server writer 或使用者工作區。完整 runtime／quality／context／
credentials qualification 維持未完成；V6 stale-unused 接線見下一節，legacy
例外不移植，historical-tier 仍須另接，不能以 fixture 通過替代。


### v6 未使用來源接點的合成實作

接線範圍為特定 source 從未 actual acquired 的 V6 私有 guard，包含初次 official
接手與 official 同 stage retry。完整原 execution／prefix 回放、每次新 proof、
原 archive 與目前 destination qualification 分開；沿用既有 selector，不建立
第二份 retry journal，也不偽造 legacy artifact。驗收需涵蓋 source 已 acquire
但未 launch、source ID／identity 改名、proof／prefix／runtime／destination 漂移、
callback fence、目前權限／context 過期、未知效果、服務及品質預算耗盡。
Legacy unused 語義與非空 v2–v5 blocker 保留；historical-tier 仍需另接。


### v6 歷史能力需求接點的合成實作

Schema 3 接線使用原 actual-acquire journal；不移植 legacy HSG artifact，
不把 event 數量當成 execution generation。新 claim 的完整歷史 proof 與目前
source／destination observation 分開；來源只適用最高原需求，仍要求新鮮、未撤銷
及相同 identity／scope／class。新目標符合目前分類與完整 context／executor／
subscription 契約，品質或服務政策決定 stage，升 tier 本身不升 stage。

驗收涵蓋內部至最佳模型及兩個歷史來源至官方／official retry、原最高需求、
原 archive 缺失／綁定漂移、每次新 proof、reader fence、目前資格與 context
漂移、pre-/post-intent gate、禁止的 failure cause、unknown overlay、預算／floor／
predecessor 保留、無使用證據／pending owner／gratuitous proof 及 schema 1／2
相容性。證據維持 ignored／原生工具儲存；production 接線、獨立 reader、provider、
credential／tool broker、source integrator 及各 runtime 資格不由此包宣稱完成。

### R1 準備交易接點

先完成 explicit prepared admission、host immutable plan、durable prepare intent
及獨立 saved descriptor／observation 確認。Flat／prepared 閉集合互斥，authority
原始 bytes 不變；歷史 operation archive-only replay 不呼叫今日 callback，新 ID
不可重複 phase。提交前／後失敗與 lost reply 保留 owner／intent，不因 absent／
created 宣稱 never-started，也不轉為 service／quality outcome。

驗收包含原 source／execution／policy／instance／nonce／control／prefix 綁定、
模式／phase／backend 型別、private artifact、pre-/post-intent current gates、
independent readback、archives／callback fence、freshness 與 immutable observation
更新，以及 schema 1 live gate、schema 2 first official unused TTL 和 schema 3
無 actual history 拒絕。Bootstrap／start／adoption／infra successor 尚未接線；
Docker／provider／登入與自架來源驗收分開，發行評估仍保留未就緒。

### B1 固定 bootstrap 接點

採獨立 bootstrap fixture mode，六類 phase 只到 bootstrapped；未來完整執行模式
須另建 packet，不沿用 B1／R1 journal authority。Input 由 sealed plan／descriptor
純函式推導，durable intent 先於固定 saved file 效果；receipt 綁 actual committed
intent ref 與 input，新鮮 observation 及四份獨立 exact bytes readback 才確認。

驗收三份 artifact 每個寫入失敗點、partial／lost reply、phase uniqueness、
archive-only replay、raw input／receipt／observation 綁定、私有檔案與兩個實體
fence，以及前／後 intent 的 source／authority／context gates。任何 bootstrap
狀態都不構成 model failure、writer stopped 或治理完成；owner／unknown 保留。
完整啟動／runtime／export／安全 finish／同 journal HSG 接手另在新模式實作。
真實自架模型驗收仍待自架服務可用的環境；專用 CODEX_HOME 官方訂閱登入安排仍待使用者
決策。這些證據不代表 production 或 release readiness。

### R2 完整 saved-fixture 接點

新 mode／packet 串接 preparation、bootstrap、launch、獨立 runtime、export、
publish 與 safe finish，不遷移 B1／R1／flat authority。Launch binding 將原 acquire
與 immutable artifact chain／actual committed launch ref 綁定；原六類與 execution
schemas 不改。只有固定 running genesis 確認 fixture start，infra partial 不能
補造 genesis、model failure 或 successor authority。

Runtime 讀全部 bounded immutable events，包含 publish／finish 原 proof 的
monotonic frontier；缺失尾端、gap、fork、partial 或舊 mode proof 均拒絕。
驗收原 mode projection／replay 不變、四效果提交前後／lost reply／phase uniqueness、
兩個實體 fence／current gates、反 rollback 及保留 unknown／owner。以同一真實
R2 journal 的失敗、safe finish 與多次 actual acquire 驗收 HSG：原需求 tier 不同，
取最高需求的正反案例，保留 quality／service 預算、floors 與 predecessor；來源
模型恢復不得 preempt 接手者。First-official schema 2 另走完整合成鏈。

完整 saved fixture 不等於完整 runtime qualification。自架模型／context／角色
驗收等自架服務可用的環境；官方訂閱登入、公開工具／credential 接點、production authority
reader／sole integrator 與各入口 qualification 仍須各自證據，發行保持未就緒。

### N1 固定 double-fork／兩輪啟動補充控制

既有 isolation probe 的 opt-in `--lifecycle` 增加固定 double-fork／setsid／
launcher exit、host process inventory、實際 writer 的 private cgroup 數值讀回，
以及 exact own container 的第二次 start。每輪實際 own write 與 protected path
嘗試、policy／mount／image、StartedAt、host canary 和自然退出均須核對；
缺正控制或 incomplete observation 保持未通過。證據綁 executable／profile
與當前環境身分，全部在 Git 外，重跑可重建等價 assertions。

這是固定 synthetic writer 的實際 Docker 測試，不是完整 N1 qualification。
Protected exact-path mounted positive、daemon／host restart、resource enforcement、
任意 Codex descendant 與全部 tool／credential 邊界仍未驗證。接通 production
authority reader／sole integrator 須先確立上述執行路徑；不能新增另一份合成
registry 作為全域 authority，也不能由這些補充控制開啟正式派工。

### 不需自架服務網路的 N2 容器路徑

固定公開 Codex source 的完整工具註冊查讀支持匿名 native CLI 的 Docker 候選，
其設計與 inventory 條件見 [匿名原生 CLI](../design/isolated-model-execution.md#匿名原生-cli-的容器候選)。
先核對固定官方 Linux asset、版本／公開 flags、create intent／cidfile 與前後 policy；
再用固定 provider 呼叫 native exec／patch 並讀回 scratch 與未掛載的 host canaries。
這些是可在不依賴自架服務的環境推進的局部測量，不是全工具、N2 或 production 資格。

後續須補完整 source／runtime inventory 對帳、每個允許工具與排除入口的實測、
native sessions、巢狀 CLI、hooks、project config、escalation 與可信 observer。
N1 剩餘隔離控制、N3 真實 backend／authority reader／整合器與官方訂閱登入資格
亦不能由自架模型端點恢復自動完成；專用登入環境仍待採用者決策。自架服務可用的環境只負責
真實自架 target／context／能力／登入與跨 provider 的端到端驗收，不能取代上述工作。

固定 28-case native container probe 已將重跑 recipe 納入工程 source；證據仍在
Git 外。涵蓋 default namespace、被排除 handler 名稱、exec 內隱與 argv0 patch、
升權拒絕及逐輪 advertisement。Host 固定案例身分／數量與 exact continuation，
不由 worker 自述決定 coverage；engine／policy／mount 逐次讀回且未知結果不重送。
Transport 綁核對過的本機 Desktop Unix socket，拒絕 context 名稱同名但遠端
或漂移的 endpoint；證據根目錄限定核對 owner／sticky mode 的系統 `/private/tmp`。
只掛載已驗證公開 binary bytes 的 private 唯讀副本，不以先前原路徑雜湊代替
實際執行內容身分；反例涵蓋原檔替換、非 regular descriptor、未知內容與副本漂移。
此版只測固定 Mac Docker／Linux arm64 CLI tuple，維持 registry／startup／
production 未資格化。CLI 的預設 local environment 與 app-server 空 environment
為不同入口；system／managed／cloud／project config closure 及完整 dispatcher
readback 仍是 N2 後續工作，不由兩個 ignore flags 或三工具 advertisement 宣稱完成。

### N1 exact-path read/write 控制

以獨立固定 recipe 補三份 synthetic source／checkpoint／sibling canary 的讀寫
對照，正控制額外掛載單一檔案至其 exact host paths，確認實際可讀寫與退出後
才重設；負控制移除 canary mounts，保持同 image／UID／program／paths／政策，
每項 read 與 write 必須各自遭 boundary denial，host bytes／inodes 不變。
兩輪有獨立 workspace 正控制、intent／CID／policy／自然退出及 unknown 不重播。
反例覆蓋 mount、身份、數量／案例混用、缺 write、未知 errno、OOM／running、
canary／reset 漂移，以及 unknown positive 不 reset／不啟動 negative。
工程 source 與重跑方式納入 repository，證據保留 Git 外；不放寬舊 probe 契約，
亦不宣稱其餘 N1、N2、N3、訂閱登入或自架服務可用的環境驗收已完成。

### N1 固定 PID 上限控制

新增獨立無 host mounts 的 Mac Docker fixture，PID1 單一 task、30 秒 explicit
deadline、上限控制最多 32 次 fork，含正控制整輪最多 33 次。先完成
single-child readiness／wait 正控制，再要求
31 個不同 children、第 32 次 EAGAIN、current 32 及兩種本地可讀 max events 各
增加一次；EOF 釋放後逐一 wait exit 0、current 回 1。反例涵蓋無 counter 的
EAGAIN、counter／PID／UID／policy／mount 漂移、缺 readiness／wait、child 異常、
未知 create／start 不重播；離線測試不在 host fork。工程 source 可重跑等價
assertions，證據留 Git 外。這不完成全部資源隔離、N1／N2／N3 或 production 資格，
也不由 cgroup events 推定 ancestor 的拒絕因果；不依賴自架服務的環境可獨立執行此控制。

### N2 匿名 project config／hook 局部控制

以固定匿名容器、唯一 exec call／兩次 Responses requests，驗證受控 user provider／
project trust 與 project-local `PreToolUse` 路徑；不需要自架來源網路或登入。先盤點固定
local config candidates，未知檔案／symlink 停止；不把此清單當成完整 cloud 或
effective-layer readback。Project hook／self-trust state 兩輪相同，user normalized
hash 一輪正確、一輪刻意不符；不使用 trust bypass。正控制要求一次 hook event
及 tool marker，負控制要求 hook 無效果且 tool 正常執行，維持 exact continuation、
advertisement、實際 project config bytes 與 container policy 身分。未知 positive
不接續或重播。工程 source／反例與重跑方法 tracked，採證留 Git 外；不宣稱完整
N2／startup／hook trust／credentials／production 資格。後續 sessions、nested CLI、
其他 hook 故障與完整 contributor／registry 對帳仍分別驗證。

### N2 匿名 native terminal session 局部控制

不依賴自架服務的環境可繼續依[app-server 工具清冊設計](../design/app-server-tool-inventory.md)
逐項對帳 source guards、公開 readback 與實際 dispatch；清冊本身不完成資格。

固定 recipe 使用兩個新 CLI／獨立 loopback provider 與匿名 homes。A 的 TTY
terminal 先產生 READY；B 在無 terminal 的另一個 CLI 實際使用 A 的 ID，要求
unknown。A 空 poll 不重現 READY，固定 chars 只送一次；唯一 ACK／marker 加上
工具 exit 0 後，再驗證舊 ID unknown。Host 只接受原始 header 的本輪 process ID，
對帳 UUID、固定 call sequence、當輪 continuation、model、宣告 schema 與 exact
container policy，不宣稱完整 request／input byte 對帳；不把 thread UUID 當工具
ID，也不從正文推定身分。Poll 是消耗式操作，
未知結果不重播。Fixture 有整體 50 秒及 subprocess／barrier 上限，證據保存在
Git 外、方法與反例 tracked。此包不完成 non-TTY、nested CLI、完整配置／工具
清冊、restart、credentials 或 N2／production 資格；後續分項仍保留。自架來源
模型端點恢復不能取代這些驗證，官方訂閱專用登入安排仍待原先提出的決策。

### N3 固定實體 checkpoint 接手組合控制

沿既有 one-shot container supervisor／sole integrator 補非空 C→存活且隔離的
A→新副本 B 的匿名案例，scope／acceptance 保持同一固定驗收。B 用 noop 仍須
保留 C 的累積 patch，A 的活躍 `holding` 不得進入 B；host exact readback 在
candidate／整合前後以 bounded process table 核對同一個 live 降權 child、holding
階段與無 completion 的 root control 綁定，不把 init running 當成 worker 存活。
唯一整合器採納 B，拒收 A 晚到的各個入口；
未知副作用不重播，隔離／checkpoint／authority 漂移須拒絕。這不替換 R2 saved
backend、不啟用 production registry、不接 provider，不完成全域 authority 或
完整 N3／原生工具／訂閱資格。工程方法與反例 tracked，原始證據留 Git 外。

### N1 Mac 原生 socket 補充控制

既有 `verify-model-permissions.py` 增加 opt-in `--network-controls`，在相同
私有 workspace／filesystem profile 上對照 network 開關。固定 C client
只用 system libraries；可信 host 分別驗證 loopback TCP／UDP 與允許路徑的
Unix socket 正控制 nonce 往返，再觀察負控制到完整期限。TCP／Unix 必須在
connect、UDP 必須在 sendto 得到明確拒絕，且 host 沒有負控制收件或 stream
accept；其它錯誤、缺失／逾期證據、compiler 或 observer 不可用保留 unknown。
Binary／設定漂移不得沿用原結果，收到負階段連線或 nonce 就回報 failed。

此包可在 Docker 不可用及自架來源不可達時測量 Mac 原生 sandbox 的固定
邊界；相關反例包括實際無隔離收件，不以缺工具或無回應當成功。設計與可重跑
assertions tracked，原始證據保存在 Git 外，供 code／merge review 讀回。
它不補足完整 N1、native tool inventory、credentials、restart 或 production
authority／executor 資格；原 N1–N4 與發行條件保持適用。
