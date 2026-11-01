# Core 讀取伴讀／Core reading companion

[繁體中文](#zh) · [English](#en)

<a id="zh"></a>

## 繁體中文

本文件回應 [Issue #27](https://github.com/jeffery777/engineering-workflow-core/issues/27) 全部十點與 2026-10-30 補充，依據 Core v0.1.1。這是非權威伴讀，不裁定原文未定的義務，也不放寬任何契約。以下「既有義務」只指所連結的原文；「建議」可選用；「待決」不是已接受的新規則。衝突回到正式契約及有效較高優先指令，不用伴讀覆蓋原文。

### 讀原文的建議索引（第 7 點）

建議接口按階段載入完整權威原檔，以 anchor 定位問題，而非把 anchor 摘要當全文。接口自己的加嚴或平台專屬規則分開列出並標來源。摘要漏寫或較寬時，不能取代 Core。若讀者無法取得引用目標，單用規則 ID 不足以傳達必要條件；給 subagent 的必要規則可保留全文，但原始來源、讀者及權限仍須查核。這不是強制某個 runtime 的載入架構或指令通道。

| 階段 | 建議定位；讀完整所屬文件，不只該節 |
| --- | --- |
| Discover／Plan | [wf-stages](../../contracts/workflow.md#wf-stages)、[wf-assumptions-and-options](../../contracts/workflow.md#wf-assumptions-and-options)、[auth-scope](../../contracts/authorization-and-stops.md#auth-scope)、[review-risk-timing](../../contracts/review-and-security.md#review-risk-timing) |
| Implement／Verify | [wf-capability](../../contracts/workflow.md#wf-capability)、[wf-delegation](../../contracts/workflow.md#wf-delegation)、[wf-verification](../../contracts/workflow.md#wf-verification)、[auth-stops](../../contracts/authorization-and-stops.md#auth-stops) |
| Review／Docs Sync | [review-independent](../../contracts/review-and-security.md#review-independent)、[review-findings](../../contracts/review-and-security.md#review-findings)、[review-security](../../contracts/review-and-security.md#review-security)、[wf-writing](../../contracts/workflow.md#wf-writing) |
| 已有變更請求／Delivery Gate | [exact-identity](../../contracts/exact-head-and-evidence.md#exact-identity)、[exact-coherence](../../contracts/exact-head-and-evidence.md#exact-coherence)、[exact-transition](../../contracts/exact-head-and-evidence.md#exact-transition)、[exact-dimensions](../../contracts/exact-head-and-evidence.md#exact-dimensions)、[exact-pinning](../../contracts/exact-head-and-evidence.md#exact-pinning) |
| Continue／證據處理 | [wf-stages](../../contracts/workflow.md#wf-stages)、[wf-evidence-lifecycle](../../contracts/workflow.md#wf-evidence-lifecycle)、[auth-data](../../contracts/authorization-and-stops.md#auth-data)、[review-evidence](../../contracts/review-and-security.md#review-evidence) |

此索引不是相依閉包清冊，也不豁免接口的其他必讀文件。CF-007／CF-008 的 Claude 結果是來源報告：按階段讀原檔、保留 subagent 所需全文，單一規則副本才改引用。當時估計 bytes 是原先的 1.5–1.85 倍，後來規則成長未重估；token 成對比較各一次，無結論。本文件不聲稱節省 token、成本或延遲，也不聲稱三端等價。

### 十點的狀態與界線

1. **runtime state：既有義務與待決。** [auth-data](../../contracts/authorization-and-stops.md#auth-data) 禁止共用庫收受所列敏感資料；本 Core repository 保留該限制。consumer 自己的協調圖／事件檔應如何分類，原文未明定。不能從本伴讀推導 consumer 可提交真實 runtime state，也不推導所有 consumer 狀態都被禁止；新增分類需修改型評估。
2. **唯讀：既有義務與待決。** [review-independent](../../contracts/review-and-security.md#review-independent) 已要求 reviewer 唯讀、作者獨立，且沒有通用逐子代理技術隔離要求。它未明列 Issue 的四種副作用範圍；本包不把其中任一級定成新的最低標準。Claude 的「任何地方不寫檔」、停用 Python bytecode／pytest cache，以及指定測試自行建立再刪除系統暫存檔的例外，只是該接口的加嚴做法。移除 Edit／Write 但留下 shell，不能證明無寫入能力；Git 前後狀態也不能涵蓋 repo 外或被忽略檔。如任務要求技術隔離，仍須實際驗證。
3. **ASD 註記：既有義務。** [wf-writing](../../contracts/workflow.md#wf-writing) 已給出中文註記「依 ASD-STE100 原則編寫，尚未完成完整符合性驗證」。原字面保留。本包不另規定所有接口只能使用同一顯示字串，也不聲稱完整符合性；固定字面檢查若成新門檻，須另外評估。
4. **fallback：既有義務的交叉閱讀。** [wf-delegation](../../contracts/workflow.md#wf-delegation) 明列缺委派採單一 writer、缺 session／排程 API 採手動 checkpoint；缺必要 review、scan、平台或安全執行能力則阻擋相依 readiness。可用它交叉閱讀 [auth-stops](../../contracts/authorization-and-stops.md#auth-stops)，不能用一般 fallback 免除必要檢查。此處不新增另一種 stop rule。
5. **取消或替換目標：既有義務的交叉閱讀。** [wf-verification](../../contracts/workflow.md#wf-verification) 的續行例外，和 [wf-evidence-lifecycle](../../contracts/workflow.md#wf-evidence-lifecycle)／[auth-data](../../contracts/authorization-and-stops.md#auth-data) 的保存義務一起讀。取消工作不是刪除證據的授權；仍適用成果與受影響證據依原規查核。本包不要求繼續已取消的工作。
6. **prune：既有義務與建議。** [auth-destructive](../../contracts/authorization-and-stops.md#auth-destructive) 已列 prune，沒有對本機 remote-tracking refs 的 blanket exception。依實際 ref、設定、可能刪 tag 的影響與有效政策查核，不能因為是 push 前準備就省略 safeguards。Claude 改用 `git ls-remote --heads --tags <remote>`，是取得遠端清單的替代例子；這不能證明物件已下載、scan 已完成或 push 目的地相同，也不授權 fetch／prune。
7. **摘要：建議。** 使用上方索引與原文，不把壓縮後的改寫當完整義務。CF-008 的去重只適用真正可取得的單一規則副本，不能刪掉複合條件或獨立讀者所需全文。
8. **preview／dry-run：既有義務。** [auth-data](../../contracts/authorization-and-stops.md#auth-data) 對搬移、歸檔、清理都要求查核必要 preview，對清理另明列先 dry-run。這個字面區別保留；其他有效政策與破壞性保障仍可能要求更多。把 dry-run 一律擴及三者屬修改型，本包不採用。也不把 preview 單獨當成任何操作已獲准。
9. **保留與保護例外：既有義務與待決。** [wf-evidence-lifecycle](../../contracts/workflow.md#wf-evidence-lifecycle) 已允許有效政策專化保留期，但不能弱化必要保存等保障，且沒有政策／期限時保留並記待決，不是所有 raw log 永久保存。它未提供保護例外要求移除資料時的通用衝突排序。本包不自訂天數、不批准縮短必要保留或刪除、不以無條件公開保存覆蓋敏感資料限制。具體衝突先核對有效要求、精確範圍與權責，停止相依清理，交付可審查的決策。
10. **「適用」：既有義務與待決。** [review-risk-timing](../../contracts/review-and-security.md#review-risk-timing)、[review-security](../../contracts/review-and-security.md#review-security) 與 [exact-coherence](../../contracts/exact-head-and-evidence.md#exact-coherence) 已要求按內容、scope、有效政策及實際影響留下證據。建議任務 owner 在既有報告列明納入／排除的未提交修改與 checks、理由、來源及 unknown，供獨立 reviewer 核對；不能省略必要項或用排除掩蓋未查差異。誰有最終適用性裁定權並無通用新定義；本包不讓作者自行豁免，也不把限定詞刪掉。具有安全影響的 executable 已有安全適用性規則，不需另造判定者。

完整背景與未接受修改見 [維護評估](../maintenance/2026-10-31-consumer-feedback.md)。

<a id="en"></a>

## English

This non-authoritative companion addresses all ten points and the October 30 supplement of [Issue #27](https://github.com/jeffery777/engineering-workflow-core/issues/27), against Core v0.1.1. It does not settle unspecified obligations or weaken a contract. “Existing duty” refers to the linked original text; “suggestion” is optional; “pending” is not an accepted rule. Formal contracts and effective higher-priority instructions govern conflicts.

### Suggested reading map (point 7)

Use the stage table in the Chinese section to locate relevant anchors, and read each complete source file. Discover/Plan covers stages, assumptions, authority, and risk timing. Implement/Verify covers capabilities, delegation, verification, and stops. Review/Docs Sync covers independence, findings, security, and writing. Existing change requests/Delivery Gate cover all five exact-head sections. Continue/evidence handling covers stages, lifecycle, data, and review evidence. The map is not a dependency-closure inventory and waives no other required reading.

We suggest loading authoritative originals per stage, with interface-specific or stricter rules listed separately with sources. A missing or weaker summary cannot replace Core. An identifier alone does not convey conditions to a reader who cannot obtain its target. Keep complete necessary rule text for subagents where needed, while checking source, reader, and authority. This does not mandate a runtime architecture or instruction channel.

CF-007/CF-008 report Claude's experience with originals per stage, complete subagent text, and citations for copies of single rules. The estimate at the change was 1.5–1.85 times the bytes; later rule growth was not re-estimated. Paired token comparisons ran once each and gave no conclusion. No token, cost, latency, or cross-runtime equivalence claim follows.

### Status and limits of the ten points

1. **Runtime state — existing duty and pending question.** [auth-data](../../contracts/authorization-and-stops.md#auth-data) excludes listed sensitive data from the shared repository. Core retains that limit. Classification of coordination graphs/events in a consumer's own repository is not explicit. This note permits neither real runtime-state publication nor a blanket ban on all consumer state. New categories need modifying evaluation.
2. **Read-only — existing duty and pending question.** [review-independent](../../contracts/review-and-security.md#review-independent) requires read-only review and author independence, without universal per-subagent technical isolation. It does not enumerate the Issue's four side-effect levels. This packet selects no new minimum. Claude's no-file-writes rule, disabled Python bytecode/pytest cache, and exception for a named test's self-created, self-removed system temporary file are interface tightenings. Removing Edit/Write while keeping a shell does not prove absence of write capability. Git comparisons miss outside and ignored files. Verify technical isolation when the task requires it.
3. **ASD note — existing duty.** [wf-writing](../../contracts/workflow.md#wf-writing) supplies the Chinese literal quoted in point 3 above; it remains unchanged. No new universal display string or full-conformance claim is added. A mandatory exact-string gate needs separate evaluation.
4. **Fallback — read existing duties together.** [wf-delegation](../../contracts/workflow.md#wf-delegation) names a single writer for missing delegation and manual checkpoints for missing session/schedule APIs. Missing necessary review, scan, platform, or security execution capability blocks dependent readiness. Read [auth-stops](../../contracts/authorization-and-stops.md#auth-stops) with it. A general fallback does not waive a required check. This adds no stop rule.
5. **Cancellation/replacement — read existing duties together.** Read the continuation exception in [wf-verification](../../contracts/workflow.md#wf-verification) with lifecycle and data-preservation duties. Cancelling work does not authorize deleting evidence. Retain applicable results and recheck affected evidence under existing rules. This does not require continuing cancelled work.
6. **Prune — existing duty and suggestion.** [auth-destructive](../../contracts/authorization-and-stops.md#auth-destructive) names prune without a blanket local-ref exception. Check actual refs, settings, possible tag deletion, and effective policy. Preparation for a push waives no safeguards. Claude's `git ls-remote --heads --tags <remote>` is an alternative for listing remote refs. It proves neither downloaded objects, completed scans, nor matching push destinations, and authorizes no fetch/prune.
7. **Summaries — suggestion.** Use the map and originals. Compressed rewrites are not complete obligations. Deduplication concerns accessible copies of a single rule, not compound conditions or text needed by independent readers.
8. **Preview/dry-run — existing duty.** [auth-data](../../contracts/authorization-and-stops.md#auth-data) requires checking the necessary preview for movement, archiving, and cleanup, and separately names a dry-run for cleanup. Keep that literal distinction. Other effective rules and destructive safeguards can require more. Extending dry-runs to all three is a modifying proposal, not adopted here. Preview alone grants no authority.
9. **Retention/protection exceptions — existing duty and pending question.** Effective policy can specialize retention without weakening necessary preservation. Without policy/duration, retain sources and record the question; not every raw log must remain forever. Core gives no universal ordering for a protection exception that requires removing data. This packet invents no duration, approves no reduction/deletion, and does not override sensitive-data limits with unconditional public retention. Check effective requirements, exact scope, and authority, stop dependent cleanup, and prepare a reviewable decision for a real conflict.
10. **“Applicable” — existing duty and pending question.** Risk timing, security, and exact-coherence clauses require evidence tied to content, scope, policy, and actual impact. We suggest that the task owner records included/excluded uncommitted changes and checks, reasons, sources, and unknowns for independent review. Exclusions cannot hide unchecked changes or waive necessary items. This creates no universal final decision-maker, author exemption, or removal of the qualifier. Security-affecting executables already have applicability rules.

See the [maintenance assessment](../maintenance/2026-10-31-consumer-feedback.md) for sources and unaccepted modifications. Written per ASD-STE100 principles; full conformance is not verified.
