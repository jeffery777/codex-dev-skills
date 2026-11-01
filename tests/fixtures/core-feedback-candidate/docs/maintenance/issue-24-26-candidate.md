# #24／#26 修改候選／Modifying candidate

## 繁體中文

本文件記錄從 Core v0.1.1 `7b66978a76597d09be1b55ad199a969b4ee59c0f` 準備的隔離候選。它不是已接受、已合併或已發行的正式 Core 義務。使用者允許候選修改與 Codex pin／eval；依最新決定，Grok 暫不實作，追蹤於 [Grok #36](https://github.com/jeffery777/grok-build-dev-skills/issues/36)。原本兩端都須 pin／eval 的接受門檻尚未滿足，因此本候選不得合併。

背景為 [Claude core-feedback.md@071c1a7](https://github.com/jeffery777/claude-dev-skills/blob/071c1a7ff1f2ce67a605d54ce5c3e85480852b69/docs/core-feedback.md) 的 CF-004／006、Core [#24](https://github.com/jeffery777/engineering-workflow-core/issues/24)／[#26](https://github.com/jeffery777/engineering-workflow-core/issues/26) 全文及 [Claude #91](https://github.com/jeffery777/claude-dev-skills/issues/91) 的只增句子教訓。非權威伴讀另外處理於 [PR #28](https://github.com/jeffery777/engineering-workflow-core/pull/28)，本候選從 main 分開準備，避免把伴讀當修改型義務的接受證據。

### 實際修改及風險界線

[review-findings](../../contracts/review-and-security.md#review-findings) 新增四種需求關係、來源說明、REQ-GAP／Needs Human Decision、使用者納入後的後續輪次，以及安全 blocker／授權保留。[wf-assumptions-and-options](../../contracts/workflow.md#wf-assumptions-and-options) 新增每個機制的獨特作用與需求來源。有效使用者要求、適用 Core 義務與有效專案要求都可追溯，不要求另建需求編號系統。

本候選沒有採用 #21 的嚴重度或強制停工門檻，也沒有採用 #23 的新工具限制或 #22 的每次公開動作掃描義務。需求關係與 severity／disposition 正交，不能把 gap／unrelated 當作安全豁免。阻擋 readiness 不能創造越界修正權；finding 也不能自行增加需求。使用者納入需求後，實際重核 scope／DoD／證據才進後續輪次，可在同一 Session；不能只改輪次標籤繞過決策。

風險是需求分類錯誤、無根據的機制擴張與過度 human gate。早期獨立深入設計／安全分析已針對這三個邊界完成；實際候選還需完整 diff 審查、適用安全掃描及兩端實際 eval。記錄的規劃不是通過證據。

### 驗收與保存

所有基準檔原始 bytes 及完整行序保持，原規則不改任何字；本包只插入完整句子／段落。LICENSE、authorization-and-stops、exact-head 及原 notices 完整 equality。以固定基準 Git object 逐行 raw-byte 比對，不做空白、換行或 Unicode 正規化，並跑刪字、替換、順序、正規化、missing／mode／type 負例。新增句子的語意及與原文一致性另由獨立 reviewer 檢查。重跑範例與本包相同的 raw-byte 方法見 [伴讀工作包的固定版](https://github.com/jeffery777/engineering-workflow-core/blob/709454e96c1b41362fe8840dc4e4dbc8d4fe2cf8/docs/maintenance/2026-10-31-consumer-feedback.md#preservation-check)；本候選對兩個新增句子的契約驗 insert-only，不宣稱 equality。

Codex [#361](https://github.com/jeffery777/codex-dev-skills/issues/361) 在測試路徑固定本候選 exact revision、全部文件／LICENSE 清冊、digest、mode、來源及 notices；正式 v0.1.1 loader／vendor／安裝不改。Eval 區分完整性、情境回應與評分、runtime／模型身分限制；至少驗證範圍內可修、gap 待決、使用者納入後可續、安全 blocker 不因關係解除、無需求機制不加入、Core 既有義務可追溯及原 gate 不放寬。Grok 未驗證必須明列，不用 Codex 或 synthetic fixture 代替。

Core 不承載執行套件、候選 loader 或 validator；本包不建立它們。候選 SHA 與實際 eval 結果由 consumer 工作包及 PR 證據綁定，避免在會自我改變的文件中嵌自身 SHA。正式 merge、tag／Release、安裝與 formal approval 均不執行。

## English

This record describes an isolated candidate based on Core v0.1.1 at `7b66978a76597d09be1b55ad199a969b4ee59c0f`. It is not accepted, merged, or published Core policy. The user authorized candidate work and Codex pin/evals. Grok implementation is deferred in Grok #36. The original dual-consumer acceptance gate is unsatisfied, so this candidate must not merge. Sources are fixed Claude CF-004/006, the complete Core #24/#26 Issues, and Claude #91. The optional companion PR #28 is separate and cannot prove acceptance.

### Meaning of the added sentences

Each finding separately records requirement_relation as in-scope, gap, no-requirement, or unrelated, with a requirement source or a statement that one is missing. In-scope is covered by an existing requirement; gap proposes a missing requirement; no-requirement has no basis for the proposed change; unrelated is outside the current objective. Valid user requests, applicable Core duties, and effective project requirements can be sources. No new numbering system is required.

The relation replaces neither severity nor disposition. A gap also carries REQ-GAP and Needs Human Decision; the agent adds no requirement or implementation because of it in that round. The user chooses to add, defer, or reject. New work with no requirement is scope expansion and is not added in that round. Unrelated findings receive residual-risk/follow-up treatment under existing disposition rules. If the user adds a requirement, recheck scope, acceptance, and affected evidence before a subsequent review/fix round, which can use the same session.

Safety, data-loss, authorization, and integrity Core blockers remain blocking for every relation. Blocking readiness grants no out-of-scope fix, new requirement, or external-write authority. Other safely fixable findings remain limited to the existing authorized scope.

For every new mechanism, including one proposed to fix a finding, record its unique role and existing requirement source in the existing plan/report. Without a requirement, record scope expansion and do not add it in that round; follow requirement-decision and authority procedures. A finding creates no requirement or authority. Existing necessary Core safety duties can be traceable sources. This adds no requirement system or automatic human gate for local choices within authorized requirements.

This candidate adopts no #21 severity/mandatory-stop proposal, #23 tool restriction, or #22 publication-scan obligation. Risks include wrong relation labels, unsupported mechanisms, and excessive human gates. Early independent deep design/security analysis addressed these boundaries; the real diff still needs review, applicable scanning, and actual consumer evals. Plans are not successful checks.

### Acceptance and preservation

Keep every original byte and complete line in order; add only complete sentences/paragraphs. LICENSE, authorization/stops, exact-head, and original notices remain equal. Compare raw bytes against immutable Git objects, without whitespace, newline, or Unicode normalization. Test deletion, substitution, order, normalization, missing files, mode, and type failures. Independent review checks sentence completeness and semantics. The linked fixed companion packet gives the reproduction method; the two modified contracts use insert-only checks, not equality claims.

Codex #361 pins the exact candidate revision, full document/LICENSE inventory, digests, modes, sources, and notices under test paths. Its formal v0.1.1 loader/vendor/installation stays unchanged. Evals separate integrity, actual scenario responses and scoring, and runtime/model identity limits. They cover in-scope fixes, undecided gaps, user-added scope, unrelated safety blockers, unsupported mechanisms, traceable Core duties, and unchanged gates. Record Grok as unverified; Codex or synthetic success cannot replace it.

Core adds no executable package, loader, or validator. Consumer/PR evidence binds the actual candidate SHA and eval results without a self-referential document SHA. No formal merge, tag/Release, install, or formal approval is performed. Written per ASD-STE100 principles; full conformance is not verified.
