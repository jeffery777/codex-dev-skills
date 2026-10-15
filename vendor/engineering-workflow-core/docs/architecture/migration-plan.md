# 純 Markdown 核心的遷移計畫

本頁依拆分章程更新現行計畫。[P0 四文件設計](https://github.com/jeffery777/engineering-workflow-core/tree/0815b74abe52d57efd032bd075e39c83c2ebf0d6) 是點時歷史；原「Grok 實作／資格全部延後」及階段編號保留於該 revision，不倒寫為已執行。本 [P1 #3](https://github.com/jeffery777/engineering-workflow-core/issues/3) 抽取文件，來源唯讀，無程式搬移、接口改接或 runtime 測試。責任見 [project-split](project-split.md)，相依見 [dependency-inventory](dependency-inventory.md)。

## 工作包順序與前置

| 階段 | 產物／責任 | 前置與驗收 |
| --- | --- | --- |
| P0 歷史設計 | Core 四份設計；[PR #2](https://github.com/jeffery777/engineering-workflow-core/pull/2) | 官方六面向唯讀比較、固定來源盤點、純 Markdown 邊界；P0 findings 在該包結案 |
| P1 契約抽取 | Core 四份 contracts、source-map、upstream-notices；必要入口同步 | 真實 Issue／遠端 Issue-ID 分支與 ready checkout；單 writer；逐條義務不減、完整 notices、來源／LICENSE 不變、獨立文審與 gates；PR 後完整 exact-head Merge Review |
| P2-C／P2-G 接口準備，可與 P1 並行 | 各接口唯讀相依盤點、官方研究、接口設計與遵循矩陣；協調者補齊漂移 | 來源 revision／scope／ownership／假設與未測能力分明；草稿標版本。核心定稿後對齊固定 revision/digest。Grok 受控 fixture／能力資格由協調者按專門工作包安排，不由本 P1 啟動 |
| P3-C／P3-G 有界實作，可分別推進 | 各自在接口 repo 實作固定文件、入口／工具、validator、installer／組裝 | **P1 正式審查與合併、immutable Core revision/digest、兩端 P2 設計皆與最終 Core 契約對齊、該包授權全部成立後**才實作；此共同前置成立後，不必等對端後續實作整體完成。Codex 保持行為與 source/plugin/temp-filesystem parity；Grok repo 可由 Codex 開發，Grok worker 未合格不自動阻擋合格 Codex 開發者 |
| P4 各端／各 surface 遵循與 runtime 資格 | 各接口 identity/capability、載入、權限、review/scan、exact-head、負面與恢復證據 | 不借另一端／surface／synthetic 的資格；CLI、TUI、Desktop、bundled CLI 按實際入口各自驗證。Grok 執行須另包 scope／sandbox／授權／安全 controls，未測保持未知 |
| Consumer rollout，非拆分交付 | 精確版本的安裝／部署 | 精確 consumer/environment、preview、backup/readback、復原與另案授權／gate；不自動更新 EdgeInstaller 技能 |

章程允許協調者安排 Grok 同步開發與受控測試，並非本 P1 執行授權。當前包仍禁止執行 Grok Build、修改兩接口、deploy/tag/Release、consumer 安裝、EdgeInstaller 既有技能更新、memory/hooks/schedulers、公司環境或 Orca。Core 全階段只有 Markdown 與既有 LICENSE；程式、schema、判定器、router、state machine、validator、installer、API、設定、assembler 都不搬入 Core。

<a id="parallel-preparation"></a>

## 協調、ownership 與固定 revision

指定協調者承接原「評估 codex-dev-skills 專案拆分」的唯一跨專案協調責任；各包只一個 writer 或明確不重疊 ownership。P1 writer 完成本包並於本話題回報，不主動派工／傳訊其他話題，不建立持續監看或下一階段任務。

接口可引用標明版本／假設的 P1 草稿作唯讀設計；不能當已合併契約。P1 merge 後讀回 immutable Core revision、逐文件與定義清楚的集合 digest，再核對接口漂移、review 及新包授權。來源固定 `codex-dev-skills@993597561881d6ed8c552f9a18c59315015ad245`，Core P1 起始 `0815b74abe52d57efd032bd075e39c83c2ebf0d6`；每包重讀 Git／dirty／ownership，不混 draft #317/#324/#326。

子代理可繼承 parent sandbox／核准模式，不逐一要求獨立技術隔離；按需求選模型／effort，各接口查實際繼承／覆寫、有效權限與必要資格。獨立 reviewer、唯讀工作約束與主代理驗證保留，模型或 sandbox 名稱不證明資格。

## P1 六份產物與驗收

| P1 產物 | 驗收重點 |
| --- | --- |
| [workflow](../../contracts/workflow.md) | 工程階段、完整能力替代、委派、Outcome／改善、失敗／返工與續行 |
| [authorization-and-stops](../../contracts/authorization-and-stops.md) | 精確授權、破壞性 safeguards、未知效果、停止、資料與證據保存 |
| [review-and-security](../../contracts/review-and-security.md) | 獨立性、findings/dispositions、formal gate、必要 scan 適用性 |
| [exact-head-and-evidence](../../contracts/exact-head-and-evidence.md) | 完整 range、identity/coherence、新 head 全審、內容／平台／授權、固定來源 |
| [source-map](../provenance/source-map.md) | 固定來源逐條處置、必要依賴／修改標記、既有 OE/proposal/evaluation 涵蓋 |
| [upstream-notices](../provenance/upstream-notices.md) | 原 Copyright／完整 MIT permission／warranty；目的 LICENSE 不取代來源 |

驗 links/anchors、固定 source refs／範圍／digest、107 個主要來源處置單位的機械覆蓋與語意完整性、diff/scope/whitespace、敏感資料／繁體中文、來源／LICENSE unchanged。檢查工具只在有界臨時位置執行，不進 Core；Python 用已核對來源 `scripts/project-python` 與 `PYTHONDONTWRITEBYTECODE=1`，不安裝或寫 source cache。

完成獨立 docs-review、dispositions、docs-review-gate。最終 diff 重評 Security Diff Scan：若只抽契約且未改實際 trust/permission/data/executable/dependency/installation，記 examined scope/rationale 為不適用；未跑不得稱 Passed。若弱化安全義務或引入具體疑慮，先修正並按風險完成必要掃描。

正式 PR 後完整 base-to-head exact-head verification、整合 review、coherence 與 merge-readiness-gate；head 改變完整重審。Core 未選 hosted enforcement，不套來源 App/ruleset；未配置與 CI 未執行分列。已授權 Commit/Push/PR/Merge 在全部 gates 成立後續行，其他動作不因此擴權。

## 接口組裝與各自遵循

下表是待實作義務，不是核心程式或本包完成聲明：

| 項目 | 接口責任 |
| --- | --- |
| 固定來源 | version（若發布）、immutable revision、逐文件 path/digest、明確集合 digest、章節、來源／notices；runtime 不追 core main |
| 建置與身分 | adapter repo/revision/version、組裝器、layout／環境；allowlist／dependency closure、bytes/modes/inventory、regular/non-symlink/path safety、duplicate-skill safeguards |
| 唯一來源 | derived copies 可重建；Codex source／plugin／catalog／installer lists 在接口同步，不手改 projection 或搬組裝器進 Core |
| 負面案例 | missing/tampered docs、wrong revision/digest、漏必讀／broken links、未知版本／來源混淆、duplicate skill、permission widening、載入錯誤 |
| 遵循證據 | 實際載入、公開工具／schema、model/effort 生效、permissions/sandbox/session、獨立 review／scan、evidence/exact-head、失敗／恢復；各端各 surface 自證 |
| 更新 | core revision/digest／義務變動重評受影響 review／遵循；不用舊 repo/head receipt |

共享 Markdown 不證明工具、結果、品質、成本、延遲或隔離等價。P0 官方比較仍是 2026-10-14 點時資料；Grok `-s` 文件差異及 live 行為另包核對。Synthetic fixture、profile／metadata、CLI success 不替代 runtime 資格與工程驗收。

## 回復與後續最小工作包

P1 不部署。契約或組裝驗收失敗不 promotion，接口保留舊固定 revision/digest；回復用可審 revert commit，核對授權／ownership，不 force push／覆寫歷史／刪資料。此為計畫，未宣稱 rollback 實測。

交付後由指定協調者依 merge revision/digest 對齊各端 P2，選最小 P3-C／P3-G 切片。每片在接口處理完整 producer/consumer/test family，維持 Codex 行為；Core 只在共用義務有缺口時另包修 Markdown。不搬 executable 進核心，不由 P1 自動啟動下一包、排程、安裝／部署。
