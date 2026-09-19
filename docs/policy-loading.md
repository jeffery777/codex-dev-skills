# 一般技能的政策載入

Issue #267 將一般 `docs-review` 與 `implementation-slice` 的初始必讀範圍改為
技能本身加上 `policies/reusable-workflow-contract.md` 完整核心與觸發表。
核心連到 `reusable-workflow-details.md` 的適用章節；批次、並行或大量工具
編排才載入完整 Code Mode 政策。其他技能的明確必讀要求仍有效，不能用本次
局部精簡跳過其政策，也不能因預計節省文字而跳過已成立的觸發。

## 來源與義務前後對照

比較基準是 `b3c195b69a0f5c948627d16cfd5fb154dcaf609e`。機器可讀的
[來源快照](policy-loading-baseline.json) 記錄原檔 bytes、原入口指定章節 bytes
及全部七個章節 body 的 SHA-256。新細則保留這七個完整 body；核心摘要
與觸發表另經語義審查，hash 相同本身不證明觸發正確或模型行為等價。

| 原來源章節 | 原必讀／條件性 | 現在必要義務與去向 |
| --- | --- | --- |
| Contract-Preserving Capability Selection | 兩入口明確指定；可能整檔讀取 | 核心保留優先序、方法相容、fallback、證據新鮮度、輸出與不可降標；相容性不明及 runtime 操作讀完整細則。 |
| Protected Boundaries | 原共用檔內，適用 gate／委派／adapter／持久資料情境 | 核心觸發表保留邊界；gate/exact-head、編排、runtime／資料入口取得各自完整要求。 |
| Contextual Prompt Composition | implementation 明確指定；docs 未指名 | 核心保留指令／事實、自主續行、比例驗證、使用者修正與輸出；委派／多階段交付讀完整 brief、qualification、整合規則。 |
| Decision And Stop Conditions | implementation 明確指定；docs 未指名 | 核心保留真正停止條件、逐操作授權、破壞性 safeguards、skill 停止說明及拒絕分類；gate 與返工讀完整細則。 |
| Shared Phases | 原共用檔內 | 核心列出一般階段；編排多階段交付讀完整八步。 |
| Runtime Differences | 原共用檔內 | 核心保留共享義務與控制面區別；runtime 操作讀完整差異與 discovery。 |
| Review And Merge | 原共用檔內 | 核心保留 primitive／gate／授權區別；正式 gate 讀全文，change request 讀 exact-head 與明確選定的 provider profile。 |
| Code Mode tool policy | 兩入口直接 `follow` 完整政策 | 核心保留原工具契約、循序依賴、授權、輸出上限與 fallback；批次／並行或大量工具編排前讀完整政策。原細則保留。 |

原政策路徑與七個 heading 留作相容入口。新細則位於同一政策目錄：
source 與 plugin 由技能的 `../../policies/` 解析；filesystem 由
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/` 解析。
它與核心同屬 `shared-review-gates`，沿既有 dependency 部署。catalog、installer
manifest、生成 allowlist 及 plugin bytes 同步；沒有新 install group、模型／effort
預設或資格變更。整體來源字數增加，換取較小的初始載入與完整可查細則。

## 情境驗收

| 情境 | 必須可觀察的契約結果 | 驗證界線 |
| --- | --- | --- |
| 一般文件審查：局部 diff、無 gate／委派／批次 | 技能＋核心；唯讀、來源比對、findings、revision/scope/limits 仍在。 | 靜態入口與義務檢查；不宣稱模型必然遵守。 |
| 局部實作：簡單循序操作 | 技能＋核心；先讀、最小變更、必要驗證、diff、授權與輸出不變。 | 當工作量觸發工具編排時須加讀政策，不能套用簡單情境的減量。 |
| 正式 gate／changed head | findings/dispositions/獨立審查；完整最新 base-to-head；內容與 provider 分開。 | 本 repo 額外要求 GitHub CI→receipt 讀回→dedicated App→合併前讀回，不將 App verdict 作 receipt 發布前置。 |
| 驗收失敗／返工 | 先分類並按 model selection 重評；兩輪未完成 review/fix 評估 context；不降資格、不自動停工／開新任務。 | 靜態路由覆蓋，未做 live 返工配對測量。 |
| 委派／角色選取 | 完整 contextual brief＋編排技能的 qualification；ownership、作者／reviewer 獨立、主代理整合責任。 | skill／runtime 缺失走既有安全 fallback，不能假造資格或載入自訂角色。 |
| 必要技能／政策缺失 | 明示缺口與未完成要求；只重用已知相容部分，繼續獨立安全工作。 | 不由缺少檔案推定相容、不假報執行或放寬 gate。 |

## 可重跑證據

```bash
./scripts/project-python -m unittest tests.test_policy_loading
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python scripts/validate-code-mode-tool-policy.py
./scripts/project-python scripts/test-shards.py validate
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/test-shards.py run-all
```

`test_policy_loading` 檢查七個原章節 body、source/plugin 的觸發連結與 anchors、
舊 anchors、六種條件列及一般入口初始 bytes。installer 與 plugin 測試另驗證
所有相依群組、一般／legacy／custom templates 的部署和新細則 bytes。
測試以隔離目錄執行，不更新使用者實際安裝。

重算來源快照時，從上列固定 commit 的原政策取每個 `## ` heading 後至下一個
heading 的 body（保留所有換行）計算 SHA-256；bytes 一律 UTF-8。初始量的
保守基準是原入口明確指名的章節加 Code Mode 全文與技能本身，另列整檔讀取
基準。相同來源只計一次，不含 repo/global instructions、工具回應或對話。

| 簡單情境 | 原指名章節基準 bytes | 原整檔基準 bytes | 新技能＋核心 bytes | 相對指名基準減量 |
| --- | ---: | ---: | ---: | ---: |
| docs-review | 9,905 | 17,132 | 8,556 | 13.6% |
| implementation-slice | 14,499 | 17,286 | 8,710 | 39.9% |

這是宣告載入文字量，不是 token 量測。若需 Code Mode，新路徑另加該政策全文；
若需 gate、返工、委派或 runtime，須再加相應章節／技能。上述百分比不能推廣
到這些情境。live 行為、模型品質、實際 token、費用、耗時與跨模型等價均未實測。

## 後續安裝準備

版本發行與使用者安裝是不同步驟；本 Issue 的發行候選見 release notes，
不更新使用者層級安裝或部署全域指令。來源版本以
`catalog.yaml` 為準；此次變更以 PR／merge commit 辨識，也須核對 exact commit。
後續如獲授權安裝，先確定只使用 plugin 或 filesystem 一條路徑，讀回目標與
既有差異；filesystem 可先執行 `./install.sh diff <group>`，保存受影響核心、
技能與政策檔的內容／權限備份，再依既有 update 契約執行並核對差異、細則引用
和 bytes。更新同時增加新細則、替換核心與兩入口，不可只複製核心而留下斷鏈。
回復須恢復整組舊內容；新增細則的清理另按破壞性操作授權處理。
現有使用者安裝的差異、更新／回復與新工作階段載入未在本交付執行。
