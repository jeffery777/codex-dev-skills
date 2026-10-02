# Issue #316 本機角色模型映射工程計畫

## 需求與範圍

提供 default-off、provider-neutral 的本機角色模型映射。只有受保護的使用者
配置可以替換模型與 effort；保留 canonical class/tier、指令、sandbox、scope、
獨立 review、操作授權與完成契約。配置不進共享 Git 或套件。

CLI 與 Desktop 分別依公開 runtime 介面驗證；不依賴 private API，不從傳輸
成功推定正式角色資格。操作與 schema 見[指南](../guides/local-model-mapping.md)。

## 自動路由擴充需求

本 Issue 後續範圍包含公司與官方模型同時可用的 internal-first 路由，以及
服務失敗與品質返工兩條獨立升級路徑。以下是待實作與驗證的目標，現有
schema 1 mapping 不具備這些自動切換能力，不得以原有測試通過宣稱完成。

沿用既有 `agent_routing.classify_task`、profile preflight／qualification 及
`model-selection-policy.md` 的返工重評規則。官方單一 provider 的既有選模
流程繼續適用；公司目標是新增候選及執行入口，不另建公司專屬選模腦或另訂
修補門檻。新增 helper 只處理供應商順序、服務預算與返工 lineage 的下一步意圖，
由既有 V2 classifier 綁定當前 class/tier/scope，不得以自填較低要求繞過分類。

| 情境 | 目標行為 |
| --- | --- |
| 公司與官方均可用 | 優先使用適合角色與工作範圍、已取得資格的公司模型。 |
| 已取得新鮮證據確認公司服務不可達 | 略過公司重試，選擇已核准且可用的官方模型；不能只憑位置或網路名稱判斷。 |
| 可重試服務錯誤 | 在有界次數及總時間內重試，持續失敗後轉官方；冷卻期間不逐請求重走失敗鏈。 |
| 合理修補後同一核心驗收仍失敗 | 重新分類並補足診斷；能力不足時先升到同角色／scope 已資格的公司最高能力目標。 |
| 同工作包兩輪修補陸續出現不同缺陷 | 保留 correction lineage，檢查完整工作流及契約；能力不足時依相同鏈升級，不因 A 變 B 清零。 |
| 公司最高能力目標仍無法修復 | 以原驗收與診斷證據轉到已核准的官方目標；重新驗證及獨立 review。 |

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
費用，不把 LiteLLM 的 OpenAI API upstream 當成訂閱 fallback。公司端可使用
本機 gateway，官方端須由 Codex 原生訂閱入口執行。不得將 Codex 登入憑證
抽出交給 LiteLLM。兩端的公開執行能力與資料處理政策分別核對。依
[官方驗證方式](https://developers.openai.com/codex/auth)核對；服務路由可參考
[LiteLLM Router](https://docs.litellm.ai/docs/routing)，文件能力不等於本機版本已驗證。

### 擴充驗收

- 離線合成案例涵蓋公司優先、公司不可達、重試耗盡／冷卻、公司高能力及官方
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
父代理保留交付與整合責任；公司及官方模型僅執行有界工作包。協調器不另建
選模分類或品質規則，使用同一 V2 classifier、provider 順位與返工 lineage。

| 狀態 | 必須保留的事實與下一步 |
| --- | --- |
| ready | 已驗證 checkpoint、原始 source 身分／digest、尚無 active attempt。 |
| claimed | 在受保護本機紀錄原子保留 attempt ID／target binding／checkpoint；重播不再啟動。 |
| running | 紀錄 runtime process identity 與唯一 packet writer；服務恢復不能搶占。 |
| reconciling | 中斷、失敗或重啟後先確認 process tree 停止，再核對私有修改與未知外寫。 |
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
證明從未觀測到的子程序不存在；即使补強 root birth identity 也不能據此完成
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
4. N4：逐 provider 驗證真實公司登入及官方訂閱入口、credential broker 與
   機密排除；以當前 context、能力及授權證據完成新 target 的資格。

本 Issue 的發行評估必須涵蓋上述資格與端到端交付驗收。只有合成隔離測試、
default-off primitive 或純選模決策通過時，不得以完整自動切換功能發行。
控制面與 worker bridge 的候選設計及公開 CLI 限制見
[隔離模型執行與可信接手](../design/isolated-model-execution.md)。

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
- 公司後端／gateway 離線時不得自動跨 provider 切回官方模型。Unavailable facts
  應停止路由；尚未觀察到離線的 facts 不保證請求成功。工作／居家切換須重新
  核對 provider、store、baseline 角色載入、catalog/context 與 runtime facts。

以上是現有 schema 1 的邊界；自動路由擴充必須另外明確啟用及完成前述驗收，
不能把配置損壞、資格撤銷或目的地漂移解讀為可 fallback 的服務錯誤。

## 證據位置與重建

需求、設計、測試與以下程序受 Git 追蹤。執行輸出與 review/gate 收據存放
`.work/verification/issue-316/`，已由 `.gitignore` 排除。歷次輸出使用不同 run
目錄，保留失敗及過期結果。它們不是套件內容，也不能提交為公開文件。

在 repository root 使用以下程序；不連線公司 gateway，不修改 provider 配置。
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
