# 剩餘回饋工作包／Remaining feedback packet

## 繁體中文

### v3 結果與 draft 修改候選階段

Codex [#364](https://github.com/jeffery777/codex-dev-skills/pull/364) 先完成新 pin、一次 v3 機械及獨立理由 12/12，再接續 Grok [#39](https://github.com/jeffery777/grok-build-dev-skills/pull/39) 自己的新 pin／原生回應與逐案理由 12/12。兩端相同 protocol、相同 prompt、相同十二案／expected，各 n=1；只滿足本包兩句提案的有限文字門檻，不證明品質提升、完整 runtime 或其他未測義務。v1／v2 的 Grok 各 11/12、一次逾時及歧義皆保留，不重貼標籤或追改分數。

現於 wf-verification 插入與下方引文完全相同的 382-byte 原字文字及一個段落換行，準備 [v0.3.0 draft](../releases/v0.3.0.md)。預期 workflow raw SHA-256 為 `5ddb9220413e2d778e06286e98c8e314b600736ac8d67622ef7395dac1c69179`；只移除本次插入即完整還原基準。其餘三契約、LICENSE、完整 notices 保持 equality。下方「四契約未改」「尚未接受」「不向契約加入」等段落記的是較早非權威測試階段；正式 main 的採納與 publication 仍未完成，普通 consumer loader／vendor／已安裝技能維持原來源。候選清冊新增 v0.3.0 文件，共二十三檔；新清冊／digest／引用由本階段另驗。

### 使用者確認的範圍校正

本次維護保障 Agent／workflow 本身正常遵循、授權、驗證、交接與誤操作／流程失效防護。先前「全部通道」「所有發送路徑」等限制證據宣稱的字句完整保留，但不把抵抗主機／repo 管理員蓄意篡改可信程式、設定或所有證據列為完成條件；這不是宣稱技術能力增加，也不免除任何既有強制安全規則。

#27 的十點與反例可獨立交付，不需先定義跨接口通用分類、全主機副作用等級或所有政策總排序；實際任務遇到衝突才依有效來源處理。#23 聚焦選定 reviewer 正常可呼叫、涉及受保護資源的直接及實際暴露 shell／broker 通道；現有 schema 若不能滿足必要限制，誠實記不支援並停止相依候選採用，不據此封鎖無相依的既有 review 工作。#22 聚焦技能支援的當次 payload／metadata／目的地、變更後重查與結果讀回；現有保存／授權義務不變，新增強制 adapter gate 仍須獨立有界設計及雙端證據，不要求全平台或所有秘密形式的完整防禦。

#21 的 v3 只對一案原題幹追加使用者批准的既有義務遺漏澄清，十二案 expected、其餘十一案及通過門檻不改；仍先取得 fresh Codex 再 Grok 的實際答案。v1／v2 失敗、逾時與歧義保留，不以範圍校正追改分數或先轉寫為已驗證案例。下方表格的未定通用方案是原評估歷史，不再把無界方案當成本輪伴讀交付前提；具體任務必要的能力缺口仍明列。

本包依 #27 → #21 → #23 → #22 接續，不重開已結案 #25／#24／#26。基準為 Core v0.2.0 `6887bfe6183465e9a9e6ccb4ccd7305a58b37302`、Codex v0.36.0 `aad6d4cce65ea50f6ade13aa1a524873bb0c6b54`、Grok v0.3.0 `d58f5e927b4d6048b9f1d09ab75279086847772b`。各 Issue 全文、全部實際留言及 [固定背景](https://github.com/jeffery777/claude-dev-skills/blob/071c1a7ff1f2ce67a605d54ce5c3e85480852b69/docs/core-feedback.md) 已納入評估；#23 沒有虛構的 2026-10-30 留言。先前 [七案評估](2026-10-31-consumer-feedback.md) 保留歷史。

這是非權威提案／評估資料。四份正式契約全部保留原 bytes；下方文字不生效、不覆蓋原文，也不證明修改型門檻已通過。完成 Codex、Grok 新候選 pin／eval 前，不向權威契約加入提案句子。[案例伴讀](../companion/remaining-feedback-cases.md) 只提供選用說明。

### 依序判定

| Issue | 可交付範圍與理由 | 未採納或未完成 |
| --- | --- | --- |
| [#27](https://github.com/jeffery777/engineering-workflow-core/issues/27) | 十點已有 [讀取伴讀](../companion/core-reading-guide.md)。本包新增反例，釐清 fallback、取消、prune、preview 及「適用」不能當豁免。按既有接口要求讀原檔，不另造載入架構。 | consumer runtime state 通用分類、唯讀副作用最低等級、保護衝突排序與最終適用性裁定仍未定。跨接口固定顯示字串、三類操作一律 dry-run 無足夠新增共用門檻的理由，本包不採納。 |
| [#21](https://github.com/jeffery777/engineering-workflow-core/issues/21) | 準備兩句窄版提案，補明有證據的規格／驗收／設計前提失敗及混合原因，不以換模型取代必要重評。這是既有前提查核的明確分類與順序，不另建框架或 gate。 | 不採納 Core-only MUST-FIX、兩輪自動停工、全面禁止提交紀錄或一律非品質分類。新提案須先 Codex 再 Grok 各自 pin／新案例 eval。 |
| [#23](https://github.com/jeffery777/engineering-workflow-core/issues/23) | 提案要求必要獨立 review 不用仍提供寫入工具的替代 reviewer。這是新增工具／有效寫入能力門檻，不等同逐代理獨立 OS sandbox。伴讀區分角色指令、實際通道及局部 probe 證據。 | 最低工具限制、shell／broker 通道及有效唯讀證據仍未定；本包未接受新門檻。現有原生子代理 schema 沒有逐子代理工具 allowlist 欄位，不能捏造已撤除寫入工具；但共用 parent sandbox 本身也不證明其他受限 reviewer 路徑不可能。缺必要能力仍停止相依工作，fail-closed 缺口保持 open。不改持久安全設定。 |
| [#22](https://github.com/jeffery777/engineering-workflow-core/issues/22) | 提供選用的人工公開檢查範圍與合成反例，包含 raw objects、完整公開範圍、預期結果、簽章、顯示轉換、實際 push 目標及非 Git payload。 | 不把每次文字／commit 都等同完整 Security Diff Scan。強制 payload／metadata gate 仍需 adapter 可執行方案及雙端驗證；沒有證明完整秘密偵測或所有發送路徑受控。 |

### #21 的非權威候選文字

以下引文是待測輸入，不是生效規則；只有雙端門檻滿足後才評估是否新增到 wf-verification，且所有舊字行序必須保留。

> 若失敗證據指向規格、驗收條件或設計前提本身的矛盾或缺口，先查核並區分實作缺陷、前提問題及混合情況；在必要的前提與範圍重新評估完成前，不以更換模型、增加 effort 或重複修補取代該評估。這項分類不免除既有 blocker、必要安全檢查或交付 gate，也不授權變更需求或驗收條件。

這個提案保留無相依且已授權工作，以及重評後有證據支持的能力調整。它不把所有設計缺陷都改稱非品質，也不自動停止整個任務。必要重評未完成時，不能只用換模型或多修幾輪替代。重大需求／驗收變更仍查原授權流程。

新案例至少涵蓋矛盾驗收、真實需求缺口、純實作缺陷、混合失敗、無證據猜測、反覆修補已知矛盾、重評完成後續行、需求變更授權，以及兩輪只觸發重評。另查必要 blocker 不因分類消失。舊 #24／#26 九案不能覆蓋新語義；scorer 測試不能冒充模型答案，兩端答案不能互代，文字 eval 也不證明完整 runtime 資格。

### 版本、完整性與後續門檻

本輪只到 draft，沒有建立新版本、tag 或 Release。若後續接受新增義務，依版本政策準備下一 minor；普通 loader、vendor 及已安裝技能保持已發布來源。提案文件新增會改清冊與相依閉包；正式採用仍須真實 immutable 來源、逐檔／集合 digests、allowlist、notices 與各接口驗證，不以改 lock 或舊 digest 代替。

本候選完整預期清冊為二十二檔，即二十一份 Markdown 與原 LICENSE；在基準二十檔上只增加本工作包與案例伴讀。最終 Git tree 仍須逐檔核對，不能把此數量當成完整性證明。

對基準二十檔做 raw bytes／完整行序、mode／type 檢驗。四契約、LICENSE、完整 notices 及未動檔 equality 另驗。負例包含刪字、換字、空白、LF／CRLF、Unicode、行序、missing／mode／type；不以正規化掩蓋差異。再重跑 [舊三基準範例](../releases/v0.2.0.md#preservation-reproduction)。語意、完整新句子及雙語一致性由獨立 review 查核。

實際 review 證據另外綁定 exact head、完整 base-to-head 範圍、適用 checks、scan 及真實平台狀態。Core 未配置 CI 不記 PASS。公開只含候選、範圍、結果、限制與待辦；詳細執行資料留受控證據。未執行記 NOT_RUN。沒有 merge／formal approval／發行／安裝授權；本包不修改登入、Reason 或持久安全設定，不啟動無關功能。保留 MIT LICENSE 與完整 notices；依 ASD-STE100 原則編寫，尚未完成完整符合性驗證。

## English

### V3 results and modifying-draft stage

Codex #364 completed its own fresh pin, one v3 mechanical12/12 and independent reasoning review before Grok #39 independently did the same. Matching protocol/prompt/twelve cases/expected values, n=1 each, meet only this packet's limited two-sentence text gate. They prove no quality improvement, full runtime qualification or untested duties. Retain both Grok11/12 histories, timeout and ambiguity without relabeling or rescoring.

The draft now inserts the exact382-byte quotation below plus one paragraph newline into wf-verification and prepares v0.3.0. Expected workflow rawSHA256 is5ddb9220413e2d778e06286e98c8e314b600736ac8d67622ef7395dac1c69179; removing only that insertion restores the complete baseline. The other three contracts/LICENSE/full notices remain exact. Earlier four-unchanged-contract/unaccepted/no-insertion statements describe the prior inactive-test stage. Formal main adoption/publication remains incomplete; ordinary consumer loaders/vendors and installations retain their prior sources. Add the v0.3.0 record for23totalfiles and verify the new inventory/digests/references separately.

### User-confirmed scope calibration

Protect normal agent/workflow compliance, authority, verification, handoff and prevention of agent mistakes/process failures. Preserve earlier evidence-limit statements about all channels/send paths, while excluding resistance to privileged intentional rewriting of trusted code/settings/all evidence as a completion condition. This adds no technical capability and waives no existing mandatory safety rule.

Deliver #27's guide/cases without a universal taxonomy, whole-host side-effect tier or total policy ordering; resolve actual conflicts against effective sources. Scope #23 to the selected review interface's normal callable direct and exposed shell/broker operations on protected resources. Unsupported necessary restriction blocks dependent candidate adoption, not unrelated existing review. Scope #22 to supported payload/metadata/destination, rechecking changes and reading back results. A new mandatory adapter gate still needs separate bounded design and both consumers' evidence; complete defense across every platform/secret type is not required. Keep current authority and retention duties.

V3 appends the approved existing-obligation clarification to one #21 situation, preserving all twelve expected objects, the other eleven cases and threshold. Obtain fresh Codex then Grok answers; retain v1/v2 failures/timeout/ambiguity without rescoring or premature verified examples. Undecided universal designs below retain assessment history; they are not unbounded prerequisites for this companion delivery. Keep concrete task-required capability gaps explicit.

This non-authoritative packet continues #27, #21, #23, #22 from the three exact released baselines above. It does not reopen completed Issues. Assessment includes all actual comments and fixed Claude feedback; no October 30 comment is invented for #23. Earlier records remain historical. All four contracts retain their original bytes. Proposal text has no effect and does not override them. Complete fresh Codex then Grok pins/evaluations before considering an authoritative addition.

For #27, optional cases extend the existing ten-point guide. Keep consumer-state classification, universal read-only floor, protection precedence and final applicability authority undecided. Adopt no fixed display-string check, universal dry-run requirement or new loading architecture. For #21, propose only explicit cause classification and sequencing, without a new framework or gate. Adopt no Core-only severity, automatic two-round stop, blanket record ban or blanket non-quality class. For #23, the request prohibits a substitute reviewer with write tools for required independent review. A tool/effective-write-capability threshold is not a separate per-agent OS sandbox. The minimum restriction, shell/broker coverage and effective evidence remain unresolved and unadopted. The current native subagent schema exposes no per-child tool allowlist; do not invent one. An inherited parent sandbox alone does not prove that every other restricted reviewer path is impossible. Missing required capability stops dependent work; local probes qualify neither a reviewer nor all tools, and fail-closed evidence remains open. For #22, suggested manual scope is not a universal full Security Diff Scan or complete secret detector. Mandatory payload/metadata enforcement still needs executable adapter design and both consumers' evidence.

The proposed two sentences mean: if failure evidence points to a contradiction or gap in the specification, acceptance criteria or design premises, first check and distinguish implementation defects, premise problems and mixed cases. Model changes, increased effort or repeated patches cannot replace required premise/scope reassessment. This classification waives no blocker, necessary safety check or delivery gate and authorizes no requirement/acceptance change. Independent authorized work may continue. Evidence-supported capability changes remain possible after assessment; not every design defect becomes non-quality and the entire task does not automatically stop.

Fresh cases cover contradictory criteria, real gaps, pure defects, mixed causes, unsupported speculation, repeated contradictory patches, post-assessment continuation, change authority and two-round reassessment. Retain blockers. Old #24/#26 cases cannot cover new semantics. Scorer mechanics are not model answers; one consumer's answers cannot replace another's. Text results do not qualify a full runtime.

This is draft preparation, not a new version/tag/Release. Accepted new duties would require the next minor. Ordinary loaders/vendors and installed skills retain published sources. New documents change inventory/closure; later adoption needs immutable source, digests, allowlists, notices and each consumer's checks. Expected full inventory is twenty-two files: twenty-one Markdown files and LICENSE, adding only this packet and the casebook to the twenty-file baseline. Verify the final Git tree; the count is not integrity proof. Check all twenty baseline files using raw complete-line order, modes/types, exact four-contract/LICENSE/notices equality and corruption negative cases without normalization. Retain the old three-baseline check too. Independently review meaning, complete added sentences and bilingual consistency. Bind reviews to exact head and full range; unconfigured CI is not PASS. Public records contain safe candidate/scope/results/limits/TODO only. Unrun work is NOT_RUN. No merge, formal approval, publication, installation, authentication, Reason or persistent safety setting changes are included. Full ASD-STE100 conformance is unverified.
