# 純 Markdown 核心的遷移計畫

[繁體中文](#zh-tw) · [English](#en)

使用 GitHub 原生展開／收合區塊：繁中預設展開，英文可另行展開；兩者可同時開啟。這不是互斥頁籤，也不會自動偵測語言。若連結指向收合內容，請先展開該語言。[呈現方式說明](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-collapsed-sections)。

GitHub disclosure sections are independent. Traditional Chinese is open by default. Expand English to read it. Both can stay open. These are not exclusive tabs, and they do not detect your language. Expand a closed section before you follow its internal links.

<a id="zh-tw"></a>

<details open>
<summary>繁體中文（預設展開）</summary>

本頁是遷移導讀，原 P0／P1 驗收描述保留為歷史與後續前置。P1 已由 [PR #4](https://github.com/jeffery777/engineering-workflow-core/pull/4) 在 `b4c37798b6d3a9efd91c8c6d518093f2dd847a98` 完成；本次不是重新抽取契約，也不宣稱已完成接口實作或 runtime 資格。

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

## 本次導讀包與 consumer 固定版本

本次只改善 README、責任邊界與本計畫的單檔雙語呈現。正式契約、provenance、相依盤點與 LICENSE 不變；兩 consumer 保持 `b4c37798b6d3a9efd91c8c6d518093f2dd847a98`。新 Core main 不觸發 consumer 重新 pin、vendored snapshot 更新或 rollout。

Core 定義共同義務；skills 引導讀取與遵循，不創造 API 或平台能力。在既有能力選取契約下，各 consumer 優先使用當次已發現、符合任務契約的原生子代理／獨立 session 工具；分開查核能力文件、loaded schema 與實際資格。缺能力採既有安全 fallback，不能假定可用、放寬 DoD 或跳過必要獨立審查。

本包在獨立翻譯／語意 review 與適用 pre-commit gate 通過後，才 commit/push 並建立 draft PR；再於 exact PR head 驗證實際 GitHub 預設展開、英文展開、窄視窗、anchors／links。完成必要 render 與完整 exact-head review／gate、無阻擋 findings 且授權有效後才 merge。未驗證不記 Passed。本包不開始其他工作包，不改接口／既有技能，不做 runtime／模型資格、Grok Build、EdgeInstaller／Orca／Space、memory/hooks/schedulers、tag/Release/install/deploy。

正式契約仍以繁體中文為權威；本頁英文供人類導讀，不新增規範或改變契約效力。英文依 [ASD-STE100 Issue 9](https://asd-ste100.org/STE_downloads.html) 原則編寫，尚未完成完整符合性驗證；本包未完成全部規則與詞彙核對。繁體中文不宣稱符合英文受控語言標準。

</details>

<a id="en"></a>

<details>
<summary>English (expand to read)</summary>

This page is a migration guide. The P0/P1 acceptance descriptions remain historical records and prerequisites for later work. P1 completed in [PR #4](https://github.com/jeffery777/engineering-workflow-core/pull/4), revision `b4c37798b6d3a9efd91c8c6d518093f2dd847a98`. This package does not extract the contracts again or claim completed interface implementation or runtime qualification.

The plan follows the program charter. The [P0 four-document design](https://github.com/jeffery777/engineering-workflow-core/tree/0815b74abe52d57efd032bd075e39c83c2ebf0d6) is historical. Its full deferral of Grok implementation/qualification and its stage numbers remain at that revision. Do not rewrite them as completed actions. [P1 #3](https://github.com/jeffery777/engineering-workflow-core/issues/3) extracted documents from read-only sources. It moved no code and performed no interface migration or runtime test. See [project-split](project-split.md) for boundaries and the [dependency inventory](dependency-inventory.md) for dependencies.

## Package order and prerequisites

| Stage | Outputs and owner | Prerequisites and acceptance |
| --- | --- | --- |
| P0 historical design | Four Core design documents; [PR #2](https://github.com/jeffery777/engineering-workflow-core/pull/2) | Six-topic official-document comparison, fixed-source inventory, and Markdown-only boundary; P0 findings closed within that package |
| P1 contract extraction | Four Core contracts, source-map, upstream-notices, and required entrypoint updates | Actual Issue, remote Issue-ID branch, ready checkout, one writer, no reduced obligations, full notices, unchanged source/LICENSE, independent document review and gates; complete exact-head Merge Review after PR creation |
| P2-C/P2-G preparation; may overlap P1 | Each interface's read-only dependency inventory, official research, design, and conformance matrix; coordinator resolves drift | State source revision, scope, ownership, assumptions, and untested capabilities. Label drafts. Align with the final fixed Core revision/digest. The coordinator assigns Grok controlled fixtures/capability qualification separately; P1 does not start them. |
| P3-C/P3-G bounded implementation; may proceed separately | Each interface implements fixed-document loading, entrypoints/tools, validators, installers, and assembly in its own repository | Start only after **P1 review and formal merge, immutable Core revision/digest, both P2 designs aligned with the final Core contract, and package authority**. After these common prerequisites, one side need not wait for the other's full implementation. Codex preserves behavior and source/plugin/temp-filesystem parity. Codex may develop the Grok repository. An unqualified Grok worker does not automatically block a qualified Codex developer. |
| P4 per-interface/per-surface conformance and runtime qualification | Each interface's identity/capability, loading, permission, review/scan, exact-head, negative-case, and recovery evidence | Do not borrow another runtime's, surface's, or synthetic fixture's qualification. Check actual CLI, TUI, Desktop, and bundled CLI entrypoints separately. Grok execution needs a separate package, scope, sandbox, authority, and safety controls. Untested stays unknown. |
| Consumer rollout; outside split delivery | Installation/deployment of an exact version | Exact consumer/environment, preview, backup/readback, recovery, separate authority and gate; no automatic EdgeInstaller skill updates |

The charter permits the coordinator to assign parallel Grok development and controlled tests. It does not authorize P1 to execute them. P1 still forbids Grok Build, interface changes, deploy/tag/Release, consumer installation, existing EdgeInstaller skill updates, memory/hooks/schedulers, company systems, and Orca. At every stage, Core contains only Markdown and the existing LICENSE. Code, schemas, decision engines, routers, state-machine programs, validators, installers, APIs, settings, and assemblers do not move into Core.

<a id="parallel-preparation-en"></a>

## Coordination, ownership, and fixed revisions

The designated coordinator succeeded the original project-split coordination chat and owns cross-project coordination. Each package has one writer or explicit non-overlapping ownership. The P1 writer completes P1 and reports in its own chat. It does not message or assign other chats, create persistent monitoring, or start the next stage.

An interface may use a draft for read-only design if the version and assumptions are explicit. A draft is not the merged contract. After P1 merge, read back the immutable Core revision, individual document digests, and a clearly defined set digest. Check interface drift, review, and new-package authority. The source is fixed at `codex-dev-skills@993597561881d6ed8c552f9a18c59315015ad245`. Core P1 started at `0815b74abe52d57efd032bd075e39c83c2ebf0d6`. Each package rereads Git state, changes, and ownership. Do not mix draft #317/#324/#326.

Subagents can inherit the parent sandbox and approval mode. Separate technical isolation is not required for every child. Select model/effort for the task. Each interface checks actual inheritance/overrides, effective permissions, and required qualification. Independent reviewers, read-only work, and main-agent verification remain required. Model or sandbox names do not prove qualification.

## P1's six outputs and acceptance

| P1 output | Acceptance focus |
| --- | --- |
| [workflow](../../contracts/workflow.md) | Stages, complete capability substitution, delegation, Outcome/improvement acceptance, failure/rework, and continuation |
| [authorization-and-stops](../../contracts/authorization-and-stops.md) | Exact authority, destructive safeguards, unknown effects, stops, data, and evidence retention |
| [review-and-security](../../contracts/review-and-security.md) | Independence, findings/dispositions, formal gates, and required-scan applicability |
| [exact-head-and-evidence](../../contracts/exact-head-and-evidence.md) | Complete ranges, identity/coherence, full new-head review, content/platform/authority, and fixed source |
| [source-map](../provenance/source-map.md) | Individual source dispositions, required dependencies/change marks, and existing OE/proposal/evaluation coverage |
| [upstream-notices](../provenance/upstream-notices.md) | Original copyright and complete MIT permission/warranty; destination LICENSE does not replace them |

P1 checks links/anchors, fixed source references/ranges/digests, mechanical and semantic coverage of 107 primary-source units, diff/scope/whitespace, sensitive data/Traditional Chinese, and unchanged source/LICENSE. Temporary bounded check tools stay outside Core. For P1, Python uses the verified source `scripts/project-python` with `PYTHONDONTWRITEBYTECODE=1`. It installs nothing and writes no source cache.

Complete independent docs-review, dispositions, and docs-review-gate. Reassess Security Diff Scan from the final diff. Document-only extraction without actual trust/permission/data/executable/dependency/installation changes can be not applicable, with examined scope and rationale. An unexecuted scan is not Passed. If documents weaken safety obligations or raise a concrete concern, fix them and perform the required proportional scan.

After PR creation, complete base-to-head exact-head verification, integration review, coherence checks, and merge-readiness-gate. A changed head requires complete review again. Core has no selected hosted enforcement profile. Do not apply the source App/ruleset. Report missing configuration separately from unexecuted CI. Authorized Commit/Push/PR/Merge may proceed after all gates pass. This grants no other authority.

## Interface assembly and separate conformance

The table defines work for interfaces. It is not Core code or a claim that P1 implemented it.

| Item | Interface responsibility |
| --- | --- |
| Fixed source | Version if published, immutable revision, each path/digest, explicit set digest, sections, source/notices; runtime does not follow Core main |
| Build/identity | Adapter repository/revision/version, assembler, layout/environment; allowlist/dependency closure, bytes/modes/inventory, regular/non-symlink/path safety, duplicate-skill safeguards |
| One source | Rebuild derived copies. Synchronize Codex source/plugin/catalog/installer lists in the interface. Do not hand-edit projections or move assemblers to Core. |
| Negative cases | Missing/tampered documents, wrong revision/digest, missing required reading/broken links, unknown versions/source confusion, duplicate skills, permission widening, loading errors |
| Conformance evidence | Actual loading, public tools/schemas, effective model/effort, permissions/sandbox/session, independent review/scan, evidence/exact-head, failure/recovery; each interface and surface proves its own results |
| Updates | Core revision/digest/obligation changes require affected review/conformance checks. Do not reuse old-repository/head receipts. |

Shared Markdown does not prove equivalent tools, results, quality, cost, latency, or isolation. The P0 official comparison remains a 2026-10-14 record. Check Grok `-s` differences and live behavior in a separate package. Synthetic fixtures, installed profiles/metadata, and CLI success do not replace runtime qualification or engineering acceptance.

## Recovery and the next bounded package

P1 does not deploy. Do not promote a failed contract or assembly acceptance result. Interfaces retain the previous fixed revision/digest. Recovery uses a reviewable revert commit with authority/ownership checks, never force push, history replacement, or data deletion. This is a plan, not a tested rollback claim.

After delivery, the coordinator aligns both P2 designs to the merged revision/digest and selects the smallest P3-C/P3-G slice. Each interface slice covers a complete producer/consumer/test family and preserves Codex behavior. Core receives a separate Markdown-only change only for a shared-obligation gap. Do not move executables to Core or let P1 automatically start another package, schedule, install, or deployment.

## This guide package and fixed consumer revisions

This package changes only the single-file bilingual README, boundary guide, and migration plan. Formal contracts, provenance, dependency inventory, and LICENSE stay unchanged. Both consumers remain at `b4c37798b6d3a9efd91c8c6d518093f2dd847a98`. New Core main content does not update consumer pins or vendored snapshots, or start rollout.

Core defines shared obligations. Skills guide readers through them; they create no APIs or platform features. Under the existing capability-selection contract, consumers prefer native subagent/independent-session tools discovered for the task that preserve its contract. Check capability documentation, loaded schemas, and actual qualification separately. Use the existing safe fallback for missing capability. Do not infer availability, lower DoD, or skip required independent review.

This package requires independent translation/semantic review and applicable pre-commit gates before commit/push and a draft PR. At the exact PR head, test GitHub's actual default-open Chinese, English disclosure, narrow viewport, anchors, and links. Merge only after required rendering tests, complete exact-head review/gates, no blocking findings, and valid authority. Do not mark unverified work Passed. This package starts no other package and changes no interface or installed skill. It performs no runtime/model qualification, Grok Build, EdgeInstaller/Orca/Space operation, memory/hooks/schedulers, tag/Release/install/deploy.

Traditional Chinese remains the authoritative language of the formal contracts. This English guide adds no policy and does not change contract authority. The English text is written using [ASD-STE100 Issue 9](https://asd-ste100.org/STE_downloads.html) principles. Full conformance has not been verified. This work has not checked every rule and dictionary entry. The Chinese text does not claim conformance to an English controlled-language standard.

</details>
