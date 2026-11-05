# 回饋判讀案例／Feedback interpretation cases

## 繁體中文

本包驗收聚焦 Agent 與技能所支援的正常工作流程，以及當次任務實際使用的工具、資料與權限邊界；不以抵抗有管理權者蓄意修改可信程式、設定或證據為完成條件。既有必要授權、驗證、交接、保存及相依停止條件仍保留。下方完整反例保留；涉及顯示轉換或故意改設定的資料，是有限測試資料與證據宣稱界線，不是要求先資格化整個主機或防止所有人為惡意操作。

本文件供 consumer 維護者與 reviewer 選用，補充 [讀取伴讀](core-reading-guide.md) 及 [決策／遮蔽格式](review-decisions.md)。這些是合成情境，不是模型結果、實際事件、新契約或權限機制。正式契約與有效較高優先指令仍優先。未定義務及 #21 的非權威提案見 [工作包](../maintenance/2026-11-01-remaining-feedback.md)。

### #27：反例不能變成豁免

本輪不以完成跨接口通用分類、全主機副作用分級或所有保護要求的總排序為交付前提；當次實際衝突仍依有效來源核對，不能據此自行豁免。

| 情境 | 可支持的判讀及界線 |
| --- | --- |
| 合成協調圖通過檢查，所以 consumer 想提交真實事件 | 資料形式不能判定公開安全。Core repository 限制不授權 consumer 公開真實狀態；先查資料及有效專案政策，通用分類仍待決。 |
| tracked files 沒變，但 shell 可寫 ignored cache 或 repo 外檔案 | Git clean 只涵蓋觀察範圍。分開記角色禁止、實際工具能力及任務需要的隔離；不推導任何位置唯讀或全球最低副作用等級。 |
| 缺委派工具，但另有可用且合格的獨立 reviewer；另一任務缺必要 scan | 前者的實作可用既有單一 writer fallback，必要 review 仍由不同的合格 reviewer 經可用路徑完成。缺該 review 路徑或必要 scan 時，writer 都不能代替；停止相依 readiness，獨立且已授權工作可續。 |
| 使用者取消實作，但失敗紀錄仍被其他工作引用 | 停止已取消工作，不推導紀錄可刪除。取消、減少載入與保存分開判斷，仍查有效保護及操作授權。 |
| push 前想列遠端 refs，卻準備 prune | 可比較無 prune 的清單讀取；清單不證明物件已取得、scan 已完成或目的地相同。仍依原破壞性保障，沒有本機 refs 的通用豁免。 |
| 已有 preview，便認為任何清理都可執行 | Preview 不授權操作，清理仍先 dry-run。原文未對所有搬移／歸檔一律 dry-run；本包不添該門檻，也不免除其他有效政策。 |
| 同一紀錄受保存要求及敏感資料移除要求約束 | 先查有效要求、精確欄位、受控保存選項及權責，停止相依清理。伴讀不自訂優先序、天數、公開保存或刪除權。 |
| 作者以「不適用」排除未提交設定改動 | 建議列明差異、受影響路徑、政策及 unknown，供獨立 reviewer 核對。Unknown 不是已排除，也不授予作者豁免權。 |

ASD 註記保留原文，沒有新增跨接口固定顯示字串。按既有接口要求讀完整原檔；讀者拿不到目標時，ID 不足以傳達條件。可在既有報告列固定來源、已讀文件及額外 overlay，不新增閱讀 receipt 或宣稱節省 token。

### #21：分類不能消除失敗

矛盾驗收須核對來源及重評，不能只換模型，也不能自行改驗收。規格一致而程式把加法寫成減法，仍可是範圍內品質缺陷。真實需求缺口可與程式缺陷並存，分開保留並依 REQ-GAP／授權流程處理相依部分；無相依且已授權的修正可續。Reviewer 無來源的推測不是已證實的規格根因。完成必要重評後，若前提及 scope 仍成立，可繼續有界修正；兩輪本身仍不是自動停工。這些是窄版提案的預期測試情境，不是已通過的 eval。

Core-only MUST-FIX 會排除有效專案需求，本包不選它。必要需求／DoD、相容性與安全仍依原契約查核。前提問題可能伴隨品質缺陷，不能一律改稱非品質或降低 severity。

提交「這個 head 已通過」的 verdict 會改變 head，該 verdict 不能證明新 head。可用既有政策允許且不改 head 的受控位置，綁定 revision／diff／結果。必要設計與需求紀錄仍在完整 diff 中；不全面禁止提交紀錄，不刪除來源避免重審，紀錄本身的 finding 也須有實質理由。

### #23：控制與證據的範圍相同

此處的通道範圍，是選定 reviewer 在當次正常介面中實際可呼叫且涉及受保護資源的操作；不要求證明敵對主機或管理員無法篡改限制。角色唯讀不等於技術禁止，缺任務必要的限制或證據仍如實記錄並停止相依操作。有限驗收可核對同一自有 fixture 的可讀、所需禁止的直接寫入，以及該介面實際暴露的 shell／broker 寫入；不新增全 OS sandbox 或未使用通道的全面資格 gate。

Brief 寫「唯讀」或 reviewer 沒回報寫入，不等於撤除寫入能力。移除 Edit／Write 卻保留 shell 或其他 broker，不證明全部通道受控。某子程序的寫入 probe 被拒絕，也不資格化模型、其他程序、MCP、網路或任意檔案。正反 probe 只支持其實際路徑、工具、程序、版本與前提。

現行 Core 允許沿用 parent sandbox。任務若明定技術唯讀，缺有效證據便停止相依操作，不能靠 prompt 或「沒看到副作用」通過。#23 要求必要獨立 review 不採用仍有寫入工具的替代 reviewer，這不等同要求每個代理另建 OS sandbox；最低工具限制及有效寫入能力範圍仍未採納。現有原生子代理 schema 沒有逐子代理工具 allowlist；共用 sandbox 也不能單獨證明其他限制方式不可行。可在自有合成 fixture 記錄允許／拒絕及不可用／NOT_RUN，不為取得 PASS 放寬權限。本說明不修改設定或宣稱 runtime qualification。

### #22：先定義要公開的 payload

公開檢查限定於技能支援的當次操作、可取得的實際 payload、metadata 與目的地；payload 或目標改變須重查。未支援或不可觀察的部分保留限制，不宣稱全面偵測或全平台防繞過。正常流程的有界正反例應區分相同 payload／目標的可追溯讀回、檢查後變更而未重查、漏查該操作支援的 metadata，以及讀取失敗仍報 clean；不需先防止管理員繞過技能直接發送。

下表是選用人工範圍，不是每次動作都跑完整 Security Diff Scan 的新規則或完整 secret detector。既有敏感資料與必要 scan 義務保留。

| 欲公開內容 | 建議檢查及反例 |
| --- | --- |
| commit／push | 列明新公開的完整可達 commit 範圍，不只 HEAD diff；raw author／committer、message、trailers、簽章 headers 及未查祖先都可能在範圍內。 |
| merge／squash | 檢查可取得的預期結果、身分、message、內容與 metadata。未知結果仍未驗證，原 head 檢查不能冒稱已覆蓋。 |
| annotated tag／簽章 | 檢查實際 raw object 與隨附的簽章／證書資料。關閉 pretty-log 顯示不代表沒有資料；合成簽章可見性測試不驗真實簽章，也不需聯網取 key。 |
| 作者顯示 | `.mailmap`、replace refs、顯示設定可能遮蔽／轉換值。讀明確物件 ID 的 raw bytes 並停用 replacement；美化結果不代替原資料。 |
| remote／refspec | fetch 與 push 可不同，push 可有多個 URL／refspec，還可能有 URL rewrite。核對實際目標、範圍及權責，不以 fetch URL 證明 push 檢查完成。 |
| PR／Issue／Release／留言／附件 | 檢查實際擬發 payload，它未必存在 Git tree。commit metadata 檢查不能代替，檢查成功也不是外寫授權。 |

可疑值沿用遮蔽格式，原資料依有效政策留受控位置。Unknown、讀取失敗或拿不到的 metadata 不記為「無敏感資料」。文字留言無須掃描無關 repository；必要安全 scan 仍按實際影響及有效政策決定。

案例依四個 Issue 全文及固定 Claude CF-001／002／003／009 設計，不是上游已驗證結果。契約繁中權威；依 ASD-STE100 原則編寫，尚未完成完整符合性驗證。

## English

This packet evaluates normal supported agent/skill workflows and the tools, data and authority boundaries actually used by the task. It does not require resistance to a privileged person intentionally changing trusted code, settings or evidence. Retain necessary authority, verification, handoff, retention and dependent stops. Existing synthetic display/configuration examples limit evidence claims; they do not require whole-host qualification or prevention of all malicious human behavior.

For #27, delivery needs no universal consumer-state taxonomy, host-wide side-effect tier or total policy ordering. Check actual conflicts against effective sources without granting a waiver. For #23, scope channels to operations actually callable through the selected review interface that affect the protected task resources. Role instructions are not technical prevention. Verify required controls or report the unsupported path and stop dependent adoption. Owned-fixture read/direct-write and actually exposed shell/broker branches are a finite acceptance target, not a new full-OS or unused-channel qualification gate. For #22, check the supported operation's observable payload/metadata and actual destination, rechecking changed payloads/targets. Retain unobservable limits without claiming complete detection or whole-platform anti-bypass. Test normal matching readback, stale post-check changes, omitted supported metadata and failed reads reported clean; privileged bypass outside the skill is not a completion prerequisite.

This optional casebook supplements the linked reading and decision/masking guides for maintainers and reviewers. Cases are synthetic, not model results, real incidents, contracts or permission controls. Formal contracts and effective higher-priority instructions govern. The maintenance packet records undecided obligations and the non-authoritative #21 proposal.

For #27, a synthetic graph does not authorize real consumer-state publication. A clean Git status cannot prove no writes to ignored/outside files. Separate role instructions, actual capabilities and required isolation. One writer can cover implementation when delegation is missing, while a different qualified reviewer must still complete required independent review through an available route. A writer replaces neither a missing necessary review route nor a necessary scan; dependent readiness stops. Cancellation ends cancelled work, not retention. Listing remote refs can avoid prune but proves neither object retrieval, scans nor push identity. Preview grants no action authority; keep the existing cleanup dry-run distinction. Conflicting retention/removal requirements need exact effective scope, controlled options and decision authority; stop dependent cleanup without inventing priority, duration or deletion rights. Suggested applicability reports identify changes, paths, policies and unknowns for independent review; authors gain no waiver. Keep the ASD literal without a universal display check. Follow existing complete-source reading requirements; inaccessible IDs are insufficient. No new receipt or token claim follows.

For #21, contradictory criteria need evidence and reassessment, not model substitution or unauthorized criterion changes. A defect under a consistent specification remains an implementation-quality problem. Real gaps can coexist with defects; preserve both and apply REQ-GAP/authority handling to dependent work. Independent authorized fixes may proceed. Speculation proves no root cause. After required reassessment confirms premises/scope, bounded fixes may continue. Two rounds alone do not automatically stop work. These are intended test cases, not completed evaluations. Project requirements, DoD, compatibility and safety remain; no Core-only severity or blanket non-quality class is adopted. Committing a head verdict changes the head. Use an existing permitted controlled evidence location where suitable, without banning necessary design/requirement records, removing sources or automatically changing finding severity.

For #23, prompts and absence of reported writes do not remove capability. A remaining shell/broker can write despite missing Edit/Write. A denied child-process probe qualifies neither models, other processes, MCP, network nor every file. Evidence supports only its observed scope/version/premises. Core permits inherited sandboxes. Task-required technical read-only operation needs effective evidence or dependent work stops. The Issue rejects write-tool substitutes for required independent review, not shared parent sandboxes or the absence of a separate per-agent OS sandbox. The minimum tool restriction and effective write-capability scope remain unadopted. The current native child schema has no tool allowlist; shared sandboxes alone do not prove other restrictions impossible. Owned fixtures may record allowed/denied and unavailable/NOT_RUN outcomes; never widen permissions merely to pass. No settings or runtime qualification change follows.

For #22, the table suggests manual scope, not a universal full Security Diff Scan or complete secret detector. Inspect newly public reachable commits and raw identity/message/trailer/signature metadata, not just HEAD's diff. Inspect available prospective merge/squash results; unknown results remain unverified. Inspect raw annotated tags and signature/certificate data. Disabled display does not remove data; synthetic visibility tests do not validate real signatures or require network key retrieval. Mailmaps, replace refs and formatting can alter views; read explicit raw objects with replacement disabled. Check all actual push URLs/refspecs and rewrites, which can differ from fetch. Inspect proposed non-Git text/attachments separately. A successful check grants no write authority. Mask suspect values and keep originals in policy-permitted controlled storage. Unknowns/failures are not clean results. A comment need not trigger an unrelated repository scan; required scans still follow impact/policy. Sources are the four Issues and fixed Claude CF-001/002/003/009, not verified upstream results. Full ASD-STE100 conformance is unverified.

<a id="followup-22-23"></a>

## #23／#22：來源交付與共用義務的區別／Interface delivery and shared duties

### 繁體中文

本節是供接口維護者及 reviewer 選用的增量伴讀，保留上方全部原文，不新增強制 gate。具體來源、點時狀態、候選方向與預期正反案例見 [2026-11-04 接續評估](../maintenance/2026-11-04-issue-22-23-followup.md)。正式契約與有效任務要求仍優先。

對 #23，可依序問：誰是作者與 reviewer、要審查哪個 revision／diff、當次任務要求哪些唯讀條件，以及選定路徑有什麼當前證據。只有角色名稱、唯讀 brief、安裝成功或文字測試，不能回答必要技術控制是否生效。若要求限制對受保護資源的有效寫入，建議將資源限定為受審內容及任務已明定範圍，再核對實際暴露的相關直接、shell／broker 操作；不把整台主機所有目錄納入，不為探測擴權。

Core 已要求唯讀工作行為、作者獨立、適用資格與缺必要 review 的相依停止，且允許繼承 parent sandbox；任務明定技術隔離時仍須驗證。接口把這些要求寫成更明確的選取 binding，不代表 Core 新增了所有 reviewer 一律撤除寫入工具的規則。符合資格還需要完成當前內容的實際 review。一次合格 review、有限 probe、CI 及文件測試，都不能資格化別的路徑、整套 runtime 或另一個 consumer。

例如，一個直接 patch 被拒，但同一介面仍暴露可寫受審 fixture 的 shell，不能用前者證明必要限制成立。另一例是路徑缺必要控制或條件未知：維持必要 review 未完成並停止相依 gate，依既有契約繼續無相依、已授權安全工作。這些例子不宣稱當次控制已測，也不把共用 sandbox 本身視為所有受限路徑都不可能。

對 #22，建議先列當次真正要送出的內容、metadata 與目的地，再對照已檢查、未知及不在覆蓋內的項目。單一 PR 標題／本文的流程，不涵蓋完整 Git range、merge／squash、tag 簽章、Issue 文字或附件；反過來，Git metadata 檢查也不能代替 PR payload 檢查。送出前讀取與寫入間若缺原子條件限制，仍保留競態；獨立讀回有其用途，但不能消除該限制或證明未知寫入由誰執行。

檢查金鑰、憑證、機密文件、本機帳號、私人目錄與不必要執行紀錄時，建議沿用[遮蔽格式](review-decisions.md)，只公開安全位置及必要類別，不貼原始私人值或其可猜測 hash。這種有界資料檢查與 [review-security](../../contracts/review-and-security.md#review-security) 的風險適用性分開；不把每次文字檢查叫做完整 Security Diff Scan，也不以其通過取得發布權。

共用新義務若要正式採納，仍需固定同一修改候選與適用案例，由兩端各自 pin／eval，並取得所需實際接口證據。Grok 暫緩時，雙端門檻維持 pending；增量伴讀可先交付，但不能標成原修改型要求已完成。

### English

This optional addition preserves the earlier text and creates no mandatory gate. The linked follow-up records sources, observed status, candidate directions and expected positive/negative cases. Formal contracts and effective task requirements still govern.

For #23, identify the author, independent reviewer, reviewed revision/diff, task-required read-only conditions and current evidence for the selected route. Names, briefs, installation and wording tests do not prove technical controls. Where effective writes must be restricted, bound protected resources to reviewed content and the task's stated scope, then examine relevant direct and exposed shell/broker paths. Do not extend this to every host directory or widen permissions for a probe.

Core already requires read-only work, independence, qualification and dependent stops, while permitting inherited parent sandboxes and requiring evidence for task-specified isolation. An explicit interface selection binding does not adopt a new shared rule removing write tools from every reviewer. Qualification still needs actual current review. A successful review, limited probe, CI or text test qualifies neither other routes nor a full runtime or another consumer.

A denied patch does not constrain a remaining shell that can write the protected fixture. Missing or unknown required controls keep necessary review incomplete and block its dependent gate; independent authorized safe work can continue. These examples are not live control tests, and shared sandbox inheritance does not prove every restricted alternative impossible.

For #22, enumerate the actual payload, metadata and destination, separating inspected, unknown and uncovered items. A bounded PR title/body workflow covers neither full Git ranges, merge/squash results, tag signatures, Issue text nor attachments. Git metadata checks do not inspect PR payloads. Retain any non-atomic pre-read/write race; independent readback does not remove it or attribute an earlier uncertain write.

Use the existing masking format for keys, credentials, confidential material, local accounts, private directories and unnecessary execution records. Publish safe locations/categories only, without raw private values or their guessable hashes. Bounded data inspection is distinct from risk-based formal Security Diff Scan applicability and grants no publication authority.

New shared duties still need matching fixed candidates, each consumer's own pin/eval and applicable real interface evidence. Grok deferral keeps the dual-consumer gate pending. Delivering optional guidance does not complete the original modifying request. Written per ASD-STE100 principles; full conformance is unverified.

<a id="upstream-timing-correction"></a>

## 本次 #22／#23 的上游時點校正／Upstream timing correction

使用者於 2026-11-04 將本次工作改為 Core 先完成自身必要評估、測試與審查，再核對正式採納及發布授權；Codex 後續採用自行驗證，Grok 工作等另行通知。上方雙端先驗門檻及未採納說明保留為當時伴讀／準備階段，不再要求本次 Core 等待下游候選驗證，也不因此宣稱下游相容性已通過；Grok 相容性未知。新增權威文字、Core 自身驗收與版本準備見 [上游候選](../maintenance/issue-22-23-upstream-candidate.md)及 [v0.4.0](../releases/v0.4.0.md)，原資料保護、必要獨立審查、相依停止與操作授權均保留。

On 2026-11-04 the user changed this work to Core's own required evaluation/tests/review before separately authorized adoption/publication, with Codex validating later adoption and Grok work deferred. The earlier dual-consumer-first and unadopted statements retain their companion/preparation stage. They no longer require Core to wait for consumer candidate verification and do not establish consumer compatibility; Grok compatibility remains unknown. The linked upstream candidate and v0.4.0 record cover new authority, Core acceptance and version preparation, preserving data protection, required independent review, dependent stops and operation authority.

## 特定環境接受的後續例外／Later environment-specific exception

本節仍為非權威伴讀；[正式候選](../../contracts/review-and-security.md#review-required-read-only)後續加入使用者要求的具體例外，使上方排除可寫 reviewer 的描述保留為預設／先前階段，不能省略例外的完整條件。必要用途使有效寫入通道無法移除時，使用者可就特定環境一次性接受並記錄通道、理由、替代偵測及未涵蓋範圍；同環境及規則未變可重用，改變須重新接受，偵測到受審內容改動則該次審查作廢。接受或 HEAD／status／diff hash 比對不等於技術禁寫、完整偵測或改動歸因；缺有效接受及必要紀錄仍停止相依 gate。

This remains optional guidance. The authority candidate's later user-requested exception qualifies the earlier writable-reviewer exclusions as default or historical statements. A necessary retained write channel may receive one-time user acceptance for a specific environment, recording channels, reasons, alternative detection and gaps. Reuse requires unchanged environment/rules; changes require renewed acceptance, and detected reviewed-content modification invalidates the review. Acceptance and fingerprints establish neither technical denial, complete detection nor attribution. Missing valid acceptance or required records still blocks dependent gates.
