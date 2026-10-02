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
