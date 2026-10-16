# engineering-workflow-core

[繁體中文](#zh-tw) · [English](#en)

使用 GitHub 原生展開／收合區塊：繁中預設展開，英文可另行展開；兩者可同時開啟。這不是互斥頁籤，也不會自動偵測語言。若連結指向收合內容，請先展開該語言。[呈現方式說明](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-collapsed-sections)。

GitHub disclosure sections are independent. Traditional Chinese is open by default. Expand English to read it. Both can stay open. These are not exclusive tabs, and they do not detect your language. Expand a closed section before you follow its internal links.

<a id="zh-tw"></a>

<details open>
<summary>繁體中文（預設展開）</summary>

## 用途與讀者

工程團隊需要一套可共同理解的交付要求，例如：誰能修改、要留下哪些證據、何時需要獨立審查，以及遇到什麼情況必須停止。把這些要求分散在不同工具專案，容易產生不同解讀。

`engineering-workflow-core` 把共同義務放在純 Markdown 文件中，讓不同接口可以引用同一個固定版本。它適合接口維護者、交付主代理、reviewer，以及想了解工程要求的專案成員。這個庫提供可讀的契約，不是會執行工作的程式或服務。

## 使用情境

例如，你要為一項修改安排實作與審查：先讀共同流程，確認修改範圍與完成標準，再由使用中的接口選取當次可用工具、安排獨立 reviewer，並保存驗證與審查證據。文件說明應達成的要求；工具執行與資格查核由接口處理。

## 開始閱讀

1. 讀完整 [工作流](contracts/workflow.md)，確認工程階段與必要產物。完成標準也稱 Definition of Done（DoD）。
2. 每次操作都保留 [授權與停止條件](contracts/authorization-and-stops.md)。讀過文件或通過測試，不會自動取得寫入權。
3. 需要審查或正式交付時，讀 [獨立審查與安全掃描](contracts/review-and-security.md)。
4. 已有 PR／MR（變更請求）或要判定能否合併時，讀完整 [exact-head 與證據](contracts/exact-head-and-evidence.md)。Exact-head 表示審查綁定精確提交與完整差異；head 改變須重審。

缺必要文件或能力不能視為豁免。使用接口前，依其自己的載入與固定版本說明操作；Core 沒有安裝器。各 consumer 在建置時鎖定 immutable revision、文件 digest、來源與 notices；runtime 不追蹤 Core `main`。

## 責任邊界

| 專案 | 負責什麼 |
| --- | --- |
| [engineering-workflow-core](https://github.com/jeffery777/engineering-workflow-core) | 純 Markdown 共用義務、來源與授權說明，以及既有 LICENSE |
| [codex-dev-skills](https://github.com/jeffery777/codex-dev-skills) | Codex 技能入口、程式與工具適配、model/effort/profile/session、資格／驗證器、安裝及套件組裝 |
| [grok-build-dev-skills](https://github.com/jeffery777/grok-build-dev-skills) | Grok 對應的技能入口、程式與工具／權限／session、設定、資格／驗證、安裝與組裝 |

依賴方向是兩個接口各自依賴固定 Core 文件，Core 不反向依賴它們。Core 不承載可執行判定器、router、state machine、runtime API、validator、installer、Schema 檔案或程式套件。

Skills 引導讀取與遵循契約，不創造 API 或平台能力。在既有能力選取契約允許範圍內，各 consumer 優先使用當次已發現、且符合任務契約的原生子代理或獨立 session 工具。能力文件、已載入的完整工具 schema、實際資格證據是三種不同資訊，不能互相替代。能力缺失時採既有安全 fallback；缺必要獨立審查或驗證時停止相依 readiness，不降低完成標準。

子代理可沿用 parent sandbox／核准模式，不要求逐個獨立技術隔離；按任務選模型與思考深度，各接口核對實際生效與必要資格。作者／reviewer 獨立、唯讀工作約束、主代理整合與完成證據仍保留。

## 已驗證的 Core 基線與深入文件

[P1 #3](https://github.com/jeffery777/engineering-workflow-core/issues/3) 已由 [PR #4](https://github.com/jeffery777/engineering-workflow-core/pull/4) 在 `b4c37798b6d3a9efd91c8c6d518093f2dd847a98` 合併四份契約、逐條來源對照與完整上游 notices。P1 未改接接口或更新既有安裝，不能以它證明接口現在已遵循或兩端行為等價。P0 設計保留於 [PR #2 的固定 revision](https://github.com/jeffery777/engineering-workflow-core/tree/0815b74abe52d57efd032bd075e39c83c2ebf0d6)。

- [責任邊界與 P0 官方六面向比較](docs/architecture/project-split.md)
- [固定來源相依盤點](docs/architecture/dependency-inventory.md)
- [遷移順序、前置與驗收](docs/architecture/migration-plan.md)
- [逐條來源處置與修改說明](docs/provenance/source-map.md)
- [完整上游 MIT notices](docs/provenance/upstream-notices.md)

## 當前限制與交付

[PR #6](https://github.com/jeffery777/engineering-workflow-core/pull/6) 的三文件雙語導讀包未重開 P1，也未改正式契約、provenance、相依盤點、LICENSE 或 consumer pins。當時兩 consumer 固定 P1 revision `b4c37798b6d3a9efd91c8c6d518093f2dd847a98`；該包 Core main 改變未觸發重新 pin、snapshot 更新或 rollout。

[Issue #7](https://github.com/jeffery777/engineering-workflow-core/issues/7) 將 [簡明寫作要求](contracts/workflow.md#wf-writing) 加入共用工作流，來源與限制見 [更新記錄](docs/provenance/source-map.md#plain-writing-update)。接口採用須另包更新固定文件並驗證；本包不改 consumer 或既有安裝。

採用本工作流時，[證據生命週期](contracts/workflow.md#wf-evidence-lifecycle) 是共用預設。專案有效政策可專化位置、保留期與歸檔方式，但不能弱化必要安全、授權、保存義務或指令優先序。索引／摘要可減少重複載入；這不授權刪除來源，缺保留期間也不代表立即清理。不可逆刪除須操作當下確認；[Issue #9](https://github.com/jeffery777/engineering-workflow-core/issues/9) 僅修改文件，不執行歷史證據清理。

[Issue #11](https://github.com/jeffery777/engineering-workflow-core/issues/11) 補明 [依風險及早檢查](contracts/review-and-security.md#review-risk-timing)：任務開始判風險，資訊不足不默認低風險，scope／設計變動重評；高風險初期即深入 review／安全分析，有實質 diff 即做必要比例掃描。最終版本用於證據綁定與 merge 驗收，不是開始深查的前提。依影響補測／重審／重掃，只重用可證未受影響的證據；不機械要求每次全庫深掃，也不保證省成本。接口採用仍須另包固定文件與驗證。

本包不搬程式、不修改接口或既有安裝、不部署、不更新 EdgeInstaller 技能、不執行 Grok Build 或模型／runtime 資格測試，不啟用 memory/hooks/schedulers，不操作公司環境、Orca 或 Space，不 tag/Release/install。P1 抽取來源固定 `codex-dev-skills@993597561881d6ed8c552f9a18c59315015ad245`。官方比較是 2026-10-14 文件證據，不能證明當前 runtime 資格、隔離、模型品質、成本或延遲。

指定協調者承接原「評估 codex-dev-skills 專案拆分」的跨專案協調。各包分別核對 scope、ownership、授權、必要審查與 gates；review／gate 不自行授權 commit、push、PR、merge 或其他外部寫入。Core 未配置 hosted enforcement profile 或 CI；未執行不得回報 Passed。文件無法技術攔截 runtime；使用專案自行選 overlay 並驗證遵循。

本 repository 採 [MIT LICENSE](LICENSE)。抽取內容同時保留 [原作者完整 MIT notices](docs/provenance/upstream-notices.md)，目的 LICENSE 不能取代來源 notices。

正式契約仍以繁體中文為權威；本頁英文供人類導讀，不新增規範或改變契約效力。英文依 [ASD-STE100 Issue 9](https://asd-ste100.org/STE_downloads.html) 原則編寫，尚未完成完整符合性驗證；本頁未完成全部規則與詞彙核對。繁體中文不宣稱符合英文受控語言標準。

</details>

<a id="en"></a>

<details>
<summary>English (expand to read)</summary>

## Purpose and readers

Engineering teams need shared delivery requirements. These include who can change files, which evidence to keep, when independent review is required, and when work must stop. Separate tool projects can interpret these requirements differently.

`engineering-workflow-core` keeps the shared obligations in Markdown. Interfaces can refer to the same fixed revision. The readers are interface maintainers, delivery agents, reviewers, and project members who need to understand the requirements. This repository provides readable contracts. It is not an executable tool or service.

## Example

Suppose you must assign implementation and review for a change. Read the shared workflow first. Confirm the scope and completion criteria. The interface then selects available tools, assigns an independent reviewer, and keeps verification and review evidence. The documents define the required outcomes. The interface performs actions and checks qualification.

## Start here

1. Read the complete [workflow](contracts/workflow.md). Confirm the stages and required outputs. Definition of Done (DoD) means the completion criteria.
2. Keep the [authorization and stop conditions](contracts/authorization-and-stops.md) for every action. Reading a document or passing a test does not grant write authority.
3. For review or formal delivery, read [independent review and security scans](contracts/review-and-security.md).
4. For an existing PR/MR (change request), or a merge-readiness decision, read the complete [exact-head and evidence contract](contracts/exact-head-and-evidence.md). Exact-head review binds the exact commits and complete diff. A changed head requires a new review.

A missing required document or capability is not an exemption. Follow the interface's own loading and version-lock instructions. Core has no installer. Each consumer locks the immutable revision, document digests, source, and notices at build time. It does not follow Core `main` at runtime.

## Responsibility boundaries

| Project | Responsibility |
| --- | --- |
| [engineering-workflow-core](https://github.com/jeffery777/engineering-workflow-core) | Shared Markdown obligations, source and license information, and the existing LICENSE |
| [codex-dev-skills](https://github.com/jeffery777/codex-dev-skills) | Codex skill entrypoints, code and tool adapters, model/effort/profile/session controls, qualification and validators, installation, and package assembly |
| [grok-build-dev-skills](https://github.com/jeffery777/grok-build-dev-skills) | The equivalent ownership for Grok skill entrypoints, code, tools/permissions/sessions, settings, qualification, validators, installation, and assembly |

Each interface depends on fixed Core documents. Core does not depend on either interface. Core contains no executable decision engine, router, state-machine program, runtime API, validator, installer, Schema file, or software package.

Skills guide the reader through the contracts. They do not create APIs or platform capabilities. Within the existing capability-selection contract, consumers prefer native subagent or independent-session tools that are discovered for the current task and preserve its contract. Capability documentation, loaded complete tool schemas, and actual qualification evidence are separate inputs. One cannot replace another. Use the existing safe fallback when a capability is missing. Missing required independent review or verification blocks dependent readiness; it does not lower completion criteria.

Subagents can inherit the parent sandbox and approval mode. A separate technical sandbox is not required for every subagent. Select the model and reasoning effort for the task. Each interface checks the effective settings and required qualification. Author/reviewer independence, read-only work constraints, main-agent integration, and completion evidence remain required.

## Verified Core baseline and further reading

[P1 #3](https://github.com/jeffery777/engineering-workflow-core/issues/3) merged through [PR #4](https://github.com/jeffery777/engineering-workflow-core/pull/4) at `b4c37798b6d3a9efd91c8c6d518093f2dd847a98`. It added four contracts, the source map, and complete upstream notices. P1 did not change interface loading or existing installations. It does not prove current interface conformance or equivalent behavior. The P0 design remains at [PR #2's fixed revision](https://github.com/jeffery777/engineering-workflow-core/tree/0815b74abe52d57efd032bd075e39c83c2ebf0d6).

- [Boundaries and the P0 official-document comparison](docs/architecture/project-split.md)
- [Fixed-source dependency inventory](docs/architecture/dependency-inventory.md)
- [Migration order, prerequisites, and acceptance](docs/architecture/migration-plan.md)
- [Source dispositions and change notes](docs/provenance/source-map.md)
- [Complete upstream MIT notices](docs/provenance/upstream-notices.md)

## Current limits and delivery

[PR #6](https://github.com/jeffery777/engineering-workflow-core/pull/6) added bilingual guides to three files. It did not reopen P1 or change formal contracts, provenance, the dependency inventory, LICENSE, or consumer pins. At that time, both consumers were pinned to P1 revision `b4c37798b6d3a9efd91c8c6d518093f2dd847a98`. That package did not update pins or snapshots, or start a rollout.

[Issue #7](https://github.com/jeffery777/engineering-workflow-core/issues/7) adds [plain-writing requirements](contracts/workflow.md#wf-writing) to the shared workflow. See the [update record](docs/provenance/source-map.md#plain-writing-update) for the source and limits. Each interface must update its fixed documents and verify them in a separate package before adoption. This package changes no consumer or existing installation.

When a project adopts this workflow, the [evidence lifecycle rules](contracts/workflow.md#wf-evidence-lifecycle) are shared defaults. A valid project policy can specify storage locations, retention periods, and archive methods. It cannot weaken mandatory safety, authorization, retention duties, or instruction priority. Indexes and summaries can reduce repeated context loading. They do not authorize source deletion, and a missing retention period does not permit immediate cleanup. Irreversible deletion requires confirmation at action time. [Issue #9](https://github.com/jeffery777/engineering-workflow-core/issues/9) changes documents only and performs no historical evidence cleanup.

[Issue #11](https://github.com/jeffery777/engineering-workflow-core/issues/11) adds [early checks based on task risk](contracts/review-and-security.md#review-risk-timing). Assess risk at task start. Do not treat missing information as low risk. Reassess when scope or design changes. High-risk work needs early in-depth review and security analysis. Start required, proportionate scanning when a meaningful diff is available. The final version binds evidence for merge acceptance; it is not a prerequisite for starting in-depth checks. After changes, repeat affected tests, reviews, and scans. Reuse only evidence shown to be unaffected. A full-repository deep scan is not required for every merge, and cost savings are not guaranteed. Interface adoption still needs a separate fixed-document update and verification.

This package moves no code and changes no interface or existing installation. It does not deploy, update EdgeInstaller skills, run Grok Build or model/runtime qualification tests, enable memory/hooks/schedulers, operate company systems, Orca, or Space, or create a tag/Release or install. P1's extraction source is fixed at `codex-dev-skills@993597561881d6ed8c552f9a18c59315015ad245`. The official comparison records documents read on 2026-10-14. It does not prove current runtime qualification, isolation, model quality, cost, or latency.

The designated coordinator succeeded the original project-split coordination chat. Each package checks scope, ownership, authority, required reviews, and gates. A review or gate does not authorize commit, push, PR creation, merge, or another external write. Core has no selected hosted enforcement profile or CI. Do not report an unexecuted check as Passed. Documents cannot technically intercept runtime actions. Each project selects its own overlay and verifies conformance.

This repository uses the [MIT LICENSE](LICENSE). Extracted content also retains the [complete original MIT notices](docs/provenance/upstream-notices.md). The destination LICENSE does not replace those notices.

Traditional Chinese remains the authoritative language of the formal contracts. This English guide adds no policy and does not change contract authority. The English text is written using [ASD-STE100 Issue 9](https://asd-ste100.org/STE_downloads.html) principles. Full conformance has not been verified. This page has not checked every rule and dictionary entry. The Chinese text does not claim conformance to an English controlled-language standard.

</details>
