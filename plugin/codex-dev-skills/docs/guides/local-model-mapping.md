# 本機角色模型映射

Issue #316 增加預設停用、供應商中立的 V2 `agent-route` opt-in。未提供或明確
停用 store 時沿用原有 profiles／候選資格流程；啟用但不適用時停止該次路由。
不依賴特定 gateway，也不建立各 gateway 的共享流程副本。

## 兩個獨立控制面

對話主模型由 Codex 公開設定與入口選擇控制。CLI 可用 `--model`、user-level
`model_provider`／`model_providers` 與隔離配置；Desktop 必須核對當次公開
模型選單與 callable schema。技能不注入選項，修改檔案也不證明既有對話切模。
Project-local provider keys 在官方設定中不受支援；不得放進專案共享配置。

角色映射只替換 canonical TOML 的 `model` 與 `model_reasoning_effort`。
指令、sandbox、scope、capability class/tier、完成與審查要求維持原值。
所有角色必須繼承**當前 runtime 已選定的 provider**；本功能不切換 provider。
同一 provider 可提供實作模型 A、審查模型 B、主模型 C。跨 provider 組合須先有
獨立公開 runtime 支援與資料目的地授權，本功能不自動提供。

## 公司連線中斷與居家使用

以下描述目前 schema 1 的行為。Internal-first、服務 fallback 與品質返工
自動升級仍屬待完成擴充；安裝目前版本不會取得這些能力。

安裝本技能不會啟用 LiteLLM，也不修改個人 provider。若已選 LiteLLM，而
gateway 或公司後端在離開公司後不可達，不會自動改走 OpenAI 官方 provider。
可信父代理若已觀察到模型不可用，preflight 會停止；如果當前 facts 尚未反映
連線中斷，實際 runtime 請求仍可能連線失敗或逾時。此 loader 不自行連線探測，
既有 API 成功或 catalog entry 不能證明目前公司服務可達。

工作與居家應明確切換各自的 provider、模型、catalog/context 與角色配置。
只改模型名稱而保留 LiteLLM provider，不代表已切回官方服務。居家配置可
使用隔離的 user-owned 配置 root；若沿用同一 root，須明確停用整份公司映射
store，恢復並重新核對 baseline 角色載入及 installed bytes。只停用單個 record
仍會停止該角色路由，不會自動 fallback。切換後重新取得 runtime facts；
不能推定既有對話或子代理立即重載配置，也不將工作資料自行送往另一 provider。

## 訂閱官方模型與自動升級規劃

官方端採 Codex ChatGPT 登入／訂閱時，由官方 parent／原生合格子角色執行，
公司工作包可使用另行驗證的公開 CLI executor。LiteLLM 的 OpenAI API upstream
使用 API 計費路徑，不能當成訂閱 fallback；技能不抽取或轉交登入 token。

`loopctl.py model-failover-plan INPUT.json` 是純決策入口：公司目標優先；有
新鮮證據確認不可達，或可重試服務錯誤耗盡有界預算時規劃官方目標。品質
返工沿用同一 task/scope/acceptance lineage：合理修補後同一驗收仍失敗，或
兩輪修補陸續出現缺陷，先分類／診斷；確認能力不足時依公司一般、公司最高
合格目標、官方的順序規劃升級。換 SHA、錯誤名稱或模型不清零總返工紀錄。

此入口**不執行切換**，輸出始終 `dispatched: false`。`planned`／`retry` 僅
表示輸入摘要符合決策條件；`diagnose` 需改變診斷方法，`blocked` 表示不能
採用該切換，兩者均不是任務停止次數上限。CLI 退出碼 0 不是任務完成或 gate。
缺公開 executor、新鮮資格／可用性／逐目標 context，或 scope／授權／機密排除
不符時拒絕規劃。現有 schema 1 mapping、`agent-route` 與 installer 邊界維持原值。

輸入只由可信父代理準備；JSON 欄位不能自行證明使用者授權、秘密已排除、
真實品質或 runtime 能力。摘要須引用獨立查證的 evidence digests，對每個目標
綁 provider configuration、model、runtime、profile、context policy 與 catalog。
Input tokens 是按**目的模型**對完整輸入的估算；切換後不得沿用來源模型數值。
前置資格、授權及內容排除在真正送出前還須重新核對；純 planner 不讀 protected
policy、不探測服務、不寫 attempts、不 dispatch，不能取代 production executor。

此擴充重用既有 `agent_routing.classify_task` 與 canonical tier 順序，並綁定
既有 V2 task 的 id、qualification scope、class/tier。`INPUT.json` 頂層必須
是 `task`（既有 agent-route V2 task）及 `model_failover`（可信父代理的目標／
事件摘要）；輸出包含同一 classifier 的 `classification` 與 advisory `plan`。
不建立第二套公司專屬分類規則，不替代原 preflight／qualification，也不將
摘要的 `qualified` 欄位當成實際 qualification。官方-only 的既有流程不必
啟用這項公司／官方目標擴充。

首次採用保持 default-off。目標順位及公司最高能力角色由採用者根據同 scope
證據核准，不依模型名稱或 effort 排序。只有明確啟用的 policy 可規劃官方目標；
配置損壞、資格撤銷、認證／權限問題、context 超限、機密內容及工具寫入結果
不明不能藉 fallback 繞過 gate。失敗與結果未知先讀回，不能自動重播外部操作。

`loopctl.py model-task-execute INPUT.json` 將同一 V2 決策綁到既有 CLI executor，
僅接受一個 typed `start` 工作包。**目前 production writer containment adapter
清冊為空，入口在任何 session 派工前拒絕；不能啟用正式自動接手。** 輸入增加
`cli_request`，包含 protected
`target_ref`（schema version、opaque ID、store 與 record digest）。它讀取
`${CODEX_HOME}/model-execution-targets.json`，按實際 prompt／HEAD／角色／
執行檔與版本重驗 protected 目標、資格、context、授權及內容排除；送出前再讀回。
CLI target 不接受任意 config flags，官方限 builtin OpenAI 與 ChatGPT 訂閱。
受控工作包使用核准 HEAD 的 shallow snapshot，不攜帶其他 refs／tags／歷史物件。
Typed source 或 private clone 存在 `.codex/config.toml` 時拒絕，避免未驗證的
project 設定合併；不讀該配置或弱化既有 private-clone 隔離與 patch 契約。

工作包的程序完成不等於 provider 已獨立讀回或任務驗收。Receipt 的
`provider_readback` 保留 `unknown`；consumer 進入 executor 後遇到結果不明，
回傳 `dispatched: null` 並要求獨立查證，不能變成「尚未送出」後自動重試。
Protected summaries 仍是可信操作人的輸入，不能由 loader 自行產生正式資格。

持久冷卻、單一 writer 交接、半成品快照與切換後續作仍待實作及深入審查。
原服務恢復不搶占接手中的工作；品質升級不因恢復而降級。既有 CLI executor
仍要求 clean exact source，不能把一包 typed dispatch 當成 dirty workspace
接手能力或完整自動路由器。驗收證據保存在 ignored `.work/`，不放入 user
policy 或套件；各 runtime 的真實容量與角色品質須另行取得資格證據。

新增 durable packet primitive 已涵蓋 claim／CAS／replay、immutable checkpoint
及逐 attempt 私有工作目錄；成功或失敗半成品先留在 packet，不立即整合 source。
Production root `${CODEX_HOME}/model-packets` 必須另行採用且位於 Git 外、mode
0700。沒有可信完整 writer containment／停止讀回資格時，不以 process polling、
程序 exit code 或 timeout 推定停止。合成 adapter 只用於測試；不得自行登錄成
production adapter。Unknown process、跨重啟恢復、持久返工／冷卻、外寫讀回及
最終驗收／promotion 尚未完成，CLI 函式可呼叫不等於 workflow 已可正式使用。

## 一次性採用

由操作人員在 user-owned `${CODEX_HOME:-~/.codex}` 保存
`agent-model-mapping.json`，並把 effective profiles 放在例如 `role-models/`。
此 root 必須在 Git repository 外、沒有 symlink，owner／寫入權限要求沿用
[資格 loader](../agent-qualification-autoload.md)的受保護讀取契約。store 限 64 KiB，
每份 evidence 限 1 MiB；duplicate keys、unknown fields、非 regular files、
讀取漂移及不安全路徑拒絕。安裝器不建立或啟用 store，也不修改個人 provider。

以下全部為 synthetic，不能作為真實角色資格；SHA placeholders 須換成實際
檔案 digest。每一 record 對應確切 role/runtime，所有欄位必填。

```json
{
  "schema_version": 1,
  "enabled": false,
  "mappings": [{
    "role": "loop_v2a_balanced_worker",
    "runtime": "cli",
    "provider_id": "synthetic-provider",
    "provider_config_sha256": "<64 lowercase hex>",
    "model": "synthetic-worker",
    "reasoning_effort": "low",
    "base_profile_sha256": "<canonical profile SHA-256>",
    "profile": "role-models/loop_v2a_balanced_worker.toml",
    "profile_sha256": "<effective TOML SHA-256>",
    "capability_class": "balanced-worker",
    "capability_tier": "everyday",
    "task_scopes": ["fixture-repair"],
    "quality_evidence": "quality/fixture-repair.md",
    "quality_evidence_sha256": "<evidence SHA-256>",
    "context_policy": "context/worker.json",
    "context_policy_sha256": "<context policy SHA-256>",
    "expires_on": null,
    "enabled": false
  }]
}
```

操作人員先從安裝版本的 canonical profile 只修改兩個模型欄位，再透過目的端
公開 custom-role 設定載入同名 effective profile。不要同時載入 baseline 和
mapped 同名角色。`destination_root` 指向 effective directory；store 的
`profile` 必須精確對應該 directory 及 canonical filename。候選 Astra records
維持獨立，不可用舊候選開關資格化任意模型。

先完成代表性同 scope 角色評估，核對真正 loaded model／effort、工具、結果
回傳與權限；由操作人員批准 evidence 後才啟用 store 和 records。API 可連線、
單一 synthetic 成功或模型名稱都不證明 class/tier 品質。effort 依逐模型實證填寫；
相同 `high`／`xhigh` 字樣不代表品質等價，不依模型供應商省略 effort。

`provider_config_sha256` 是目的端公開 provider 設定的 canonical JSON SHA-256：
至少包含 `provider_id`、`base_url`、`wire_api`，及所有會改變路由／資料目的地的
非機密設定。不要把 key/token、credential path 或私人 metadata 加入 receipt。
此 digest 由可信 workflow parent 每次重新核對，loader 不讀 provider 設定、
不連網，也不驗證 gateway 行為。相同 alias 的後端模型漂移仍需重新評估／撤銷。

## 逐模型 context window 必要條件

自訂 model metadata 不可依 generic fallback 資格化。每個 record 的
`context_policy` 是 protected root 內的 JSON，完整 required 欄位如下；數字僅為
合成測試範例，不能抄成任何公司模型容量：

```json
{
  "schema_version": 1,
  "model": "synthetic-worker",
  "runtime": "cli",
  "provider_config_sha256": "<provider config SHA-256>",
  "backend_context_window": 16000,
  "backend_max_input_tokens": 14000,
  "backend_max_output_tokens": 2000,
  "reserved_output_tokens": 1000,
  "reserved_reasoning_tokens": 500,
  "safety_margin_tokens": 1000,
  "model_context_window": 16000,
  "model_auto_compact_token_limit": 12000,
  "model_catalog_sha256": "<runtime-version-matched catalog SHA-256>",
  "capacity_evidence": "capacity/worker.md",
  "capacity_evidence_sha256": "<capacity evidence SHA-256>"
}
```

容量證據需涵蓋實際部署版本、input/output/合計限制、推理 token 計算、超限拒絕
或截斷、alias 漂移及工具／壓縮後續答；原廠規格不能代替 gateway 部署事實。
所有容量未知時維持停用，不能自行填 32K／128K。輸出預留加推理預留不得超過
已確認輸出上限；安全餘裕須為正數。壓縮門檻嚴格低於：

```text
min(backend input limit,
    backend total context - output reserve - reasoning reserve - safety margin,
    effective Codex context - output reserve - reasoning reserve - safety margin)
```

完整輸入包含指令、技能、history、tool schema／result；JSON policy 的計算只是
設定合理性檢查，不是逐 request tokenizer 或超長請求攔截器。Gateway 的
metadata／pre-call checks、請求輸出限制與 Codex 逐模型 catalog 都要另行驗收；
不因 context 超限切其他模型或資料目的地。需要長容量測試時另訂有界預算。

Catalog 會取代 bundled catalog，若同一配置需選官方模型，須保留符合該 runtime
版本的官方 entries，不改其 metadata。CLI 用 gateway 專用 profile，Desktop
分別核對 bundled runtime／載入；不對所有模型套單一全域 context override。
父代理的 `context_metadata` 是逐角色實際 effective values（含繼承／override），
不是只有設定檔存在。catalog SHA 與兩個數值須匹配 policy；缺件、漂移、過大
client context、無輸出餘裕或壓縮太晚都停止路由。整合亦重新核對。

官方：[自訂模型 catalog](https://learn.chatgpt.com/docs/enterprise/roll-out-a-gateway#use-a-model-catalog-for-custom-names)。

## 每次 workflow 使用

父代理準備既有 runtime facts、exact `task.qualification_scope` 與下列新增欄位：

```json
{
  "local_model_surface": {
    "runtime": "cli",
    "provider_id": "synthetic-provider",
    "provider_config_sha256": "<current provider config SHA-256>",
    "supported_roles": ["loop_v2a_balanced_worker"],
    "context_metadata": {
      "synthetic-worker": {
        "model_context_window": 16000,
        "model_auto_compact_token_limit": 12000,
        "model_catalog_sha256": "<current catalog SHA-256>"
      }
    }
  }
}
```

仍須提供 `model_surface.runtime/source/observed_on`、`available_models`、
逐模型 `reasoning_efforts`、custom role surface 與 parent sandbox 的當前證據。
`supported_roles` 必須來自當次公開 callable／載入觀察，不能從 store 推定。
CLI／Desktop 分別驗證；API record 不能用於本功能的 CLI／Desktop 放行。

`loopctl.py agent-route INPUT --runtime-facts FACTS` 在候選及 fallback 前讀取
store。啟用後缺 record、revoked、expiry、scope、provider/runtime、model/effort、
profile/evidence bytes、collision、sandbox 或 class/tier 不符都回傳 human-gate；
不自動切到 baseline、parent/default 或其他 provider。coupled 工作亦不得靠
mapped record 自授權 current-session 執行。修正當前證據或明確停用並重路由。

mapped receipt 的 `config_evidence.local_model_mapping` 綁定 canonical/effective
profile、store、provider configuration、quality evidence digests、model、effort、
runtime 和 scope；不含 evidence 內容、URL 或本機 path。舊 receipt 不改寫。
整合時 `agent-integrate` 必須另提供 fresh `--runtime-facts`、`--profile-dir`
與 actual `--profile-path`；重新讀回 store/evidence/profile/runtime，撤銷或漂移
阻擋整合。Receipt 是完整性及 operator assertion，並非密碼學 attestation。

## 更新、撤銷與恢復

store 與 effective profiles 由使用者管理，不屬 generated package。
一般 skill update 保留它們；若 installer 的 profile target 指向 enabled store
保留的 effective directory，連 `update --force` 也拒絕覆寫。Installer 不代替
操作人員修改／更新 mapping。canonical profile 更新後 base digest 不符，路由
停止；重新產生兩欄替換的 effective TOML、重驗 evidence 並更新 record。

將 record 停用可撤銷角色，但 enabled store 不會因此 fallback。整份 store
明確停用後恢復 baseline 路由；仍須先在公開 runtime 恢復 baseline 角色載入、
核對 installed bytes，否則既有 collision／availability checks 仍生效。
不自動 rollback、不刪除 user files、不改動 provider 設定。

## 驗收與 review

採用前分別驗證 standalone CLI、bundled CLI 與 Desktop callable。傳輸成功
不等於正式角色資格。Desktop schema 不接受自訂 model 時，記錄缺口，
不強送參數或使用 private API。真實容量、catalog 載入、長上下文與壓縮後
工具循環均須有各自證據，不能從短請求推定。

需求、設計與可重跑驗證程序見 repository 的
[Issue #316 工程計畫](https://github.com/jeffery777/codex-dev-skills/blob/main/docs/plans/issue-316-local-model-mapping.md)。
測試、PoC 與 review 收據存放 Git 忽略的 `.work/verification/issue-316/`；
該目錄不是套件內容，不能以公開文件或範例代替當前驗收證據。

官方來源：[設定參考](https://learn.chatgpt.com/docs/config-file/config-reference)、
[子代理模型與 effort](https://learn.chatgpt.com/docs/agent-configuration/subagents#choosing-models-and-reasoning)。

### 隔離執行資格的合成檢查

`scripts/verify-model-isolation.py` 是 opt-in 合成測試，使用既有映像的 immutable
identity，不拉取映像、不掛載憑證、停用網路與 capabilities。兩個 attempt 只各自
掛載自己的可寫副本；來源及封存 checkpoint 不掛載。測試確認接手者在舊 writer
仍執行時完成，並確認舊 writer 稍後寫入不影響接手成果與來源。

使用 `./scripts/project-python scripts/verify-model-isolation.py --engine docker
--image <existing-image> --evidence-root <directory-outside-git>`；Linux 可指定
`--engine podman`，僅執行本機 rootless 路徑。證據目錄必須已存在且在 Git checkout
以外。未委派 CPU 控制器時可顯式指定 `--cpu-limit-unavailable`，證據保留該缺口，
不能據此認定正式資源管理通過。測試程序自行結束，容器及資料保留，不自動清理。

預期重跑得到相同的布林檢查結果；artifact path、時間與容器識別自然不同。
`production_qualified` 固定為 false：這個檢查不能證明完整 supervisor、憑證隔離、
可信 checkpoint 擷取、重啟、撤銷或成果整合已合格，亦不啟用任何 production adapter。

`scripts/verify-model-permissions.py` 提供另一個 macOS-only opt-in 合成檢查，
以空白 HOME／CODEX_HOME 與乾淨環境呼叫公開 `codex sandbox` permission profile，
不呼叫模型。背景子程序在 root 已退出後寫入自己的副本，另一 profile 的接手者
先完成；檢查背景子程序不能寫接手副本或讀合成控制端檔案。以
`./scripts/project-python scripts/verify-model-permissions.py --evidence-root
<directory-outside-git>` 重跑，原始證據留在該目錄。本檢查不驗證真實憑證、網路、
socket、完整內建工具或 Codex exec，亦不登錄 production adapter。

`scripts/verify-model-dispatch.py` 使用本機 loopback 合成 Responses fixture，驅動
真正 CLI 的 shell 或 patch 入口，沒有真實模型或登入。以 `--case shell` 或
`--case patch` 及 `--evidence-root <directory-outside-git>` 選擇合成案例。它使用
named permissions；shell 案例先確認相同沙箱內的讀取工具可用，再檢查控制端
讀寫被拒絕。patch 案例檢查控制端檔案未被改寫，不驗證讀取限制。
兩者都讀回指定成果與同 call ID 的 tool output，
不能只靠最終文字判定成功。模型名稱只選擇 CLI metadata，不是可用模型的證據。

預設只接受 request.tools 明確宣告的工具與 namespace；沒有適合 schema 時失敗。
部分 native metadata 把工具指引放入 input 而未宣告 request.tools；顯式選擇
`--allow-unparsed-native-fixture` 僅供實驗與回歸調查，不能用來資格化 tool manifest。
原始合成 requests、CLI logs 與結果都保留於 Git 外，production_qualified 固定 false。
正式採用另須完成 N1（完整檔案／FD／socket邊界）、N2（全部啟用工具）、
N3（supervisor／重啟／撤銷／可信export）、N4（實際provider及官方訂閱憑證）資格。
