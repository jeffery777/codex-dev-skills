# Changelog

[繁體中文](#changelog-zh-tw) · [English](#changelog-en)

<a id="changelog-zh-tw"></a>

<details open>
<summary>繁體中文（預設展開）</summary>

## v0.4.1 — 簡明用語澄清候選

在 [wf-writing](contracts/workflow.md#wf-writing) 只新增完整句子，具體說明既有的讀者、術語及技術精度要求：減少不必要的行話、縮寫、中英混用及名詞連用；保留必要術語，依讀者需要解釋。新增[選用雙語例子](docs/companion/plain-writing-examples.md)，不設禁用詞表、不要求所有文件改為非工程用語，不新增 STE 認證或 gate，也不改安全、授權、審查或 #23 例外。

依不改變義務的文件澄清準備 patch 候選；範圍、來源、驗收與採用影響見 [v0.4.1 準備紀錄](docs/releases/v0.4.1.md)。全部舊字、其他三契約、歷史證據、LICENSE 及完整 notices 保留。此條目不證明已提交、合併、發布或更新任何 consumer；新增文件及引用須另核完整清冊、固定 revision、digest 與引用閉包。

## v0.4.0 — 必要 reviewer 與公開資料檢查準備

後續使用者要求加入特定環境的一次性殘餘風險接受例外：必要用途使寫入通道無法移除時，明確記錄通道、理由、替代偵測及未涵蓋範圍；環境及規則未變可重用接受，改變須重新接受，偵測到受審內容改動則該次審查作廢。下方有效唯讀要求保留為預設；例外不宣稱技術禁寫、完整偵測或 Claude 的接受紀錄已完成。

在 review-and-security 只新增完整句子，定義所有必要 reviewer 路徑對任務受保護資源的有效唯讀資格，以及每次相關 commit／push／merge／tag／PR／Issue 公開操作的有界資料檢查。保留 parent sandbox 繼承、相依停止、實際 review、按風險決定正式掃描、原始 metadata、公開授權與受控證據；不加入執行器、整台主機不可寫或完整秘密偵測保證。

本次 #22／#23 按使用者的新時點，由 Core 先完成自身必要評估、測試與審查，再核對採納／發布授權；Codex 後續採用自行驗證，Grok 工作暫緩、相容性未知。先前雙端先驗 gate 文字保留為舊工作包歷史，不能當成這次 Core 仍必須等待下游的要求，也不能改記下游已通過。詳見 [上游候選](docs/maintenance/issue-22-23-upstream-candidate.md)及 [v0.4.0 準備紀錄](docs/releases/v0.4.0.md)。

新增義務依版本方式準備下一 minor；此條目不證明已合併、tag／Release 已發布或下游已採用。其餘三契約、全部舊字／行序、LICENSE、完整 notices 與既有發行歷史保留，新清冊與引用閉包另驗。

## 尚未選版 — 剩餘回饋評估資料

本節標題保留原未選版評估入口；下方 v0.3.0 記錄後續 draft 候選階段，再下方的原評估段落保留準備歷史，不能單獨判定目前候選的契約 bytes。

## v0.3.0 — 前提失敗重評 draft 候選

在兩端相同 v3 各一次 12/12 及獨立理由查核後，於 wf-verification 僅插入已測的兩句原字提案，原 workflow 其他 bytes／完整行序與三契約、LICENSE、完整 notices 保留。依新增義務準備下一 minor；範圍、逐字組合身分、二十三檔清冊、歷史失敗及正式採用前置見 [v0.3.0 準備紀錄](docs/releases/v0.3.0.md)。以下未選版／未接受及四契約未改的說明保留早期評估歷史；本段只記 draft 修改候選，不代表已合併、發布或更新 consumer／安裝。

依使用者確認，伴讀與工作包補明正常 Agent／workflow 的有界驗收，不以防止有管理權者蓄意篡改可信程式或所有證據為完成條件。原文、強制保障及舊反例保留；#21 v3 僅澄清一案，雙端新觀測與正式候選處理另記。

新增 #27／#21／#23／#22 的具體案例及順序工作包，保留四份正式契約與全部舊字。#21 兩句窄版提案只作非權威待測資料，須先 Codex 再 Grok 各自 pin／eval，尚未接受。其他擴張的最低閱讀、severity、停工、紀錄位置、技術隔離或強制公開掃描未採納；不建立新發行或更新安裝。

## v0.2.0 — 需求追溯與伴讀準備紀錄

本 minor 準備正式採納 #24 的 requirement_relation／REQ-GAP 與 #26 的機制需求追溯，並整合 PR28 的非權威伴讀。四契約保持已通過兩端九案文字 eval 的固定候選 bytes；每端 n=1 的有限文字門檻已滿足，正式接受、publication 與 consumer adoption 分別核對。清冊、原文保留、版本／相依與未完成事項見 [v0.2.0 準備紀錄](docs/releases/v0.2.0.md)。下列隔離候選及先前工作包條目保留為點時歷史，不由後續結果改寫。

## 未發行候選 — #24／#26 需求可追溯性

在 review-findings 與 wf-assumptions-and-options 只新增完整句子，試行 finding 的 requirement_relation／REQ-GAP 與新增機制對應現有需求；嚴重度、disposition、必要安全 blocker、操作授權及其他原文保留。這是隔離修改型候選，不是已接受義務或新版本。Codex 候選 pin／eval 由 #361 處理；Grok 延後於 #36，雙 consumer gate 未滿足前不合併。範圍、英文對照、驗收及逐字保留方式見 [候選記錄](docs/maintenance/issue-24-26-candidate.md)。

## 未發行 — 使用端回饋伴讀

新增 #25 決策卡、#27 十點讀取伴讀與階段索引、#21 決策選項及 #22 公開記錄遮蔽格式。這些是選用非權威說明；四份正式契約保留原始 bytes。七項順序評估與修改型候選門檻見 [維護工作包](docs/maintenance/2026-10-31-consumer-feedback.md)。本條不建立新版本、tag 或 Release，也不表示 consumer 已 pin／eval、已安裝或兩端行為等價。

## 版本與記錄方式

Core 的文件版本由本檔已提交的版本條目記錄，採 `vMAJOR.MINOR.PATCH` 命名。Core 與各 consumer 各自管理版本，不要求同步升版。`0.x` 階段的 minor 更新可能調整契約；每次採用仍須審查實際差異。Patch 用於不改變義務的文件修正，也不能取代 consumer 的完整性與遵循驗證。版本號不保證模型、工具、接口或 runtime 相容。

本檔及 release note 是點時準備／歷史紀錄，並非已發行證據。版本條目合併後仍須分別核對新的 annotated tag 與 GitHub 正式 Release。既有 tag 不覆寫；歷史條目不因後續發布而回填狀態。README 提供穩定導讀，不鏡像 mutable latest 或當前 publication 指標。

<a id="v0-1-1-zh-tw"></a>

## v0.1.1 — 最小接續規則準備紀錄

- 在 [Continue](contracts/workflow.md#wf-stages) 明寫優先沿用原 Session；中斷點有結果不明的操作或委派工作時，先確認現況，再接續未完成部分。這是既有接續順序與未知效果查證義務的文件澄清；「優先」為偏好，不要求硬性還原 Session，也不擴張授權或新增委派權。
- 補上對應英文導讀、來源記錄與 [v0.1.1 準備紀錄](docs/releases/v0.1.1.md)，並在 README 連結本版。原 107 單位、v0.1.0 歷史、其餘三份正式契約及完整 notices／LICENSE 保留。預期完整清冊為 13 份 Markdown＋LICENSE，共 14 檔；採用者須重查清冊、固定版本、digest、allowlist、引用與組裝／遵循驗證。
- Core 與 consumer 各自管理版本；Core 發行不自動更新或安裝 consumer。後續版本方向為 Codex 0.35.1、Grok 0.2.2，須另核版本可用性及固定 Core 發行身分。本包不改 consumer、既有安裝或 runtime，不新增恢復框架、API、去重保證、Reason 或其他執行功能。

本條為點時準備紀錄，不證明 v0.1.1 已合併或發布。正式繁中權威、授權／停止及既有 gates 保留；英文提供等價導讀，尚未完成完整 ASD-STE100 符合性驗證。

<a id="v0-1-0-zh-tw"></a>

## v0.1.0 — 初版準備紀錄

### 範圍與變更

- 將既有純 Markdown 共用契約整理為第一個版本化發行包：工程階段、授權及停止、獨立審查與必要安全檢查、exact-head 與證據。既有簡明寫作、證據生命週期、依風險及早檢查、安全適用性、前提／方案與停止改善義務一併保留。
- 本發行文件包更新 README 與來源記錄，新增本 changelog 及 [v0.1.0 準備紀錄](docs/releases/v0.1.0.md)。四份正式 contracts、三份架構文件、完整上游 notices 與 LICENSE 保持原 bytes／mode；原 107 單位及過往工作包歷史保留。
- 預期清冊為 12 份 Markdown 加原 LICENSE，共 13 檔。最終清冊、逐檔 bytes／mode／digest、全 repository 與完整 Markdown 集合 digest 在最終合併後的 tag annotation／Release metadata 及交接證據中核對，不在本檔內嵌自身 commit 或 digest。
- 不新增程式、validator、installer、schema、catalog、runtime API、模型控制或 Reason 功能；既有文件義務不改稱新的 runtime 能力。

### 採用及升級影響

使用者不需獨立安裝 Core。`codex-dev-skills` 與 `grok-build-dev-skills` 各自在建置／組裝時採用固定文件。Consumer 必須核對 tag object，將 tag 解析為完整 immutable commit，鎖定所選文件的逐檔及集合 digest、來源、allowlist、完整 dependency closure 與 notices；runtime 不追蹤 Core `main` 或動態解析 tag。

新增 changelog 與 release note 會改變完整清冊、集合 digest，以及可能的 allowlist／dependency closure。Consumer 應逐項判定所需文件與相對引用，更新自己的 lock／snapshot／組裝及驗證，保存 LICENSE 和完整上游 notices。不得沿用前一基線 `64b19bb5658432c42cd6a26aa357fd6b1d0fd857` 或舊 10 份 Markdown 集合 digest 冒充本發行包；最終 pin 必須包含本次發行文件。

本包不修改 consumer、既有技能或安裝，也不部署。正式發行、consumer 採用及實際安裝各需自己的授權與證據；Core 發行不證明接口遵循、兩端行為等價或模型／runtime 資格。驗證項、未驗證限制與來源／license 見 [準備紀錄](docs/releases/v0.1.0.md)。

正式契約的繁體中文權威與既有 ASD-STE100 限制保留。以下英文須與繁中主要資訊等價，不新增契約義務；未宣稱完成全部 ASD-STE100 規則及詞彙驗證。

</details>

<a id="changelog-en"></a>

<details>
<summary>English (expand to read)</summary>

## v0.4.1 — Plain-wording clarification candidate

Add complete sentences only to [wf-writing](contracts/workflow.md#wf-writing) to explain its existing reader, terminology and precision requirements. Reduce unnecessary jargon, abbreviations, mixed-language wording and noun sequences. Keep necessary terms and explain them when the reader needs it. Add [optional bilingual examples](docs/companion/plain-writing-examples.md), without a prohibited-word list, universal nontechnical wording, new STE certification or gate. Change no safety, authority, review or #23 exception requirement.

Prepare a patch candidate for clarification without changed duties. The [v0.4.1 preparation record](docs/releases/v0.4.1.md) describes scope, sources, acceptance and adoption effects. Retain all earlier text, the other three contracts, historical evidence, LICENSE and complete notices. This entry proves no commit, merge, publication or consumer update. New files and references require verification of the full inventory, fixed revision, digests and reference closure.

## v0.4.0 — Required reviewers and publication-data preparation

The user's later exception permits one-time acceptance of residual risk for a specific environment when a necessary purpose prevents removal of a write channel. Record channels, reasons, alternative detection and uncovered scope. Reuse acceptance while the environment and rules remain unchanged; renew it on change. Detected reviewed-content modification invalidates that review. The read-only requirement below remains the default. Acceptance proves neither technical denial, complete detection nor a completed Claude acceptance record.

Add complete sentences only to review-and-security for every required reviewer route's effective read-only qualification over protected task resources and bounded inspection before relevant commit/push/merge/tag/PR/Issue operations. Retain inherited parent sandboxes, dependent stops, actual review, risk-based formal scans, raw metadata, publication authority and controlled evidence. Add no executor, whole-host no-write rule or complete-secret-detector guarantee.

Under the user's revised timing for this #22/#23 work, Core completes its own required evaluation, tests and review before separately authorized adoption/publication. Codex validates later adoption; Grok work is deferred and compatibility unknown. Earlier dual-consumer-first wording remains historical, neither a current Core dependency nor proof that consumers passed. The upstream candidate and v0.4.0 record explain the scope and checks.

New duties prepare the next minor. This entry proves neither merge/tag/Release nor consumer adoption. Preserve the other three contracts, every earlier word/line, LICENSE, complete notices and release history; verify the new inventory/reference closure separately.

## Unversioned — Remaining feedback evaluation data

Retain this original assessment heading in place. The v0.3.0 entry records the later draft stage; original assessment paragraphs below retain preparation history and do not independently describe current candidate-contract bytes.

## v0.3.0 — Premise-failure reassessment draft candidate

After one matching v3 12/12 response and independent reasoning review per consumer, insert only the exact tested two-sentence quotation in wf-verification. Preserve all other workflow bytes/line order, the other three contracts, LICENSE and complete notices. Prepare the next minor for added duties; the v0.3.0 record covers scope, exact composition,23-file inventory, historical failures and adoption prerequisites. Earlier unversioned/unaccepted/four-unchanged-contract statements retain assessment history. This draft is not merge, publication or a consumer/installation update.

Clarify bounded normal agent/workflow acceptance under the user's confirmed scope. Privileged intentional rewriting of trusted code/all evidence is not a completion prerequisite. Preserve all old text, mandatory safeguards and examples. The #21 v3 packet clarifies one case only; record fresh consumer observations and later candidate handling separately.

Add concrete cases and an ordered packet for #27/#21/#23/#22, preserving all four contracts and old text. The two-sentence #21 proposal is non-authoritative test data only. It needs fresh Codex then Grok pins/evaluations before acceptance. No broader reading, severity, stopping, record-location, isolation or mandatory-publication-scan duties, new publication or installed update are adopted.

## v0.2.0 — Requirement traceability and companion preparation

This minor prepares Issue #24 requirement relations/REQ-GAP and Issue #26 mechanism traceability, integrating PR28's optional companions. All four contracts retain the evaluated candidate bytes. Both consumers passed one actual nine-case text evaluation; formal acceptance, publication and consumer adoption remain separate. See the [v0.2.0 record](docs/releases/v0.2.0.md) for inventory, preservation, versions, dependencies and pending work. Retain the isolated-candidate and earlier entries below as point-in-time history.

## Unreleased candidate — #24/#26 requirement traceability

Add complete sentences to review-findings and wf-assumptions-and-options for requirement_relation/REQ-GAP and tracing new mechanisms to existing requirements. Preserve original severity, dispositions, safety blockers, authority, and all original text. This isolated modifying candidate is neither accepted policy nor a new version. Codex #361 handles candidate pin/evals; Grok #36 is deferred. Do not merge before the dual-consumer gate passes. See the [candidate record](docs/maintenance/issue-24-26-candidate.md) for scope, English wording, acceptance, and byte-preservation checks.

## Unreleased — Consumer feedback companions

Add optional, non-authoritative decision cards (#25), ten reading notes and a stage map (#27), decision options (#21), and public-record masking formats (#22). The four formal contracts retain their original bytes. See the [maintenance packet](docs/maintenance/2026-10-31-consumer-feedback.md) for the ordered assessment and modifying-candidate gates. This entry creates no version, tag, or Release and proves no consumer pin, eval, installation, or runtime equivalence.

## Versions and records

Committed version entries in this file record the Core document version. Names use `vMAJOR.MINOR.PATCH`. Core and each consumer manage their own versions. They do not need matching version numbers. During `0.x`, a minor update can change contracts. Review the actual changes for every adoption. A patch corrects documents without changing obligations. It does not replace consumer integrity or conformance checks. A version number does not guarantee model, tool, interface, or runtime compatibility.

This file and release notes are records of preparation and history. They do not prove publication. After a version entry is merged, separately verify the new annotated tag and formal GitHub Release. Do not overwrite existing tags or update historical entries merely to reflect later publication. README provides stable guidance. It does not mirror a mutable latest or current-publication pointer.

<a id="v0-1-1-en"></a>

## v0.1.1 — Minimal continuation preparation record

- State in [Continue](contracts/workflow.md#wf-stages) that the original session is preferred. If an operation or delegated task has an unknown outcome at the interruption point, check its current state before continuing unfinished work. This clarifies the existing continuation order and unknown-effect checks. “Prefer” is a preference. It does not require forced session restoration, extend authority, or grant new delegation rights.
- Add equivalent English guidance, source history, and the [v0.1.1 preparation record](docs/releases/v0.1.1.md), with a README link. Retain the original 107 units, v0.1.0 history, the other three formal contracts, and complete notices and LICENSE. The expected full inventory is 13 Markdown files plus LICENSE: 14 files. Adopters must review inventory, fixed versions, digests, allowlists, references, assembly, and conformance checks.
- Core and consumers manage separate versions. Core publication does not update or install consumers automatically. Proposed follow-up versions are Codex 0.35.1 and Grok 0.2.2. Recheck their availability and the fixed Core publication identity separately. This packet does not change consumers, installations, or runtime. It adds no recovery framework, API, deduplication guarantee, Reason feature, or other execution capability.

This is a point-in-time preparation record. It does not prove v0.1.1 is merged or published. Traditional Chinese authority, authorization, stops, and existing gates remain. English provides equivalent guidance. Full ASD-STE100 conformance has not been verified.

<a id="v0-1-0-en"></a>

## v0.1.0 — Initial preparation record

### Scope and changes

- Assemble the existing shared Markdown contracts into the first versioned release package: engineering stages, authority and stop conditions, independent review and required security checks, exact-head, and evidence. Retain existing obligations for plain writing, evidence lifecycle, early risk-based checks, security applicability, assumptions, options, and stopping optional improvement.
- This release-document packet updates README and the source record. It adds this changelog and the [v0.1.0 preparation record](docs/releases/v0.1.0.md). The four formal contracts, three architecture documents, complete upstream notices, and LICENSE keep their original bytes and modes. Retain the original 107 units and earlier packet history.
- The expected inventory is 12 Markdown files and the original LICENSE: 13 files. After the final merge, verify the final inventory, per-file bytes, modes and digests, and both repository and complete Markdown digests in the tag annotation, Release metadata, and handoff evidence. Do not put a self-referential commit or digest in this file.
- Add no code, validator, installer, schema, catalog, runtime API, model control, or Reason feature. Existing document obligations are not new runtime capabilities.

### Adoption and upgrade impact

Users do not install Core separately. `codex-dev-skills` and `grok-build-dev-skills` each adopt fixed documents during build or assembly. A consumer verifies the tag object, resolves it to a full immutable commit, and locks the selected files, per-file and set digests, source, allowlist, complete dependency closure, and notices. Runtime must not follow Core `main` or resolve a tag dynamically.

The new changelog and release note change the full inventory and set digests. They can also change a consumer's allowlist or dependency closure. Each consumer assesses the required documents and relative references, updates its own lock, snapshot, assembly, and verification, and retains LICENSE and complete upstream notices. Do not use the earlier base `64b19bb5658432c42cd6a26aa357fd6b1d0fd857` or the old 10-file Markdown digest as this release's pin. The final pin must include these release documents.

This packet does not change consumers, existing skills, or installations. It does not deploy. Publication, consumer adoption, and installation each require their own authority and evidence. Core publication does not prove interface conformance, equivalent behavior, or model/runtime qualification. See the [preparation record](docs/releases/v0.1.0.md) for checks, unverified limits, sources, and licensing.

Traditional Chinese remains authoritative for the formal contracts. Existing ASD-STE100 limits remain. This English text provides equivalent main information and adds no contract obligation. Full rule and dictionary conformance has not been verified.

</details>
