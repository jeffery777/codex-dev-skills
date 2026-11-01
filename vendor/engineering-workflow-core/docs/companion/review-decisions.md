# 審查決策與公開記錄／Review decisions and public records

[繁體中文](#zh) · [English](#en)

<a id="zh"></a>

## 繁體中文

本文件是 #21 第 4 點與 #22 遮蔽格式的選用伴讀。它不新增 finding 嚴重度、停止門檻、紀錄位置或必掃範圍，也不接受其他修改型提案。[正式審查契約](../../contracts/review-and-security.md) 與 [授權／停止契約](../../contracts/authorization-and-stops.md) 仍為準。

### 重複修正之後的決策選項（建議）

[wf-verification](../../contracts/workflow.md#wf-verification) 的兩輪門檻是重新評估，不是自動停工。若依有效規則已需交人決定，可用 [決策卡](decision-cards.md) 比較根因修正、再做一輪有界驗證、移至獨立後續項目、或保留現狀。把某機制移出、交付其餘部分，是要交使用者決定的範圍選項，不是代理自行降低 DoD。

選擇移出時，建議列明原範圍、新範圍、相依項目、仍未達成的目標、後續 owner／目標／驗證方式及殘餘風險。必要安全、授權、完整性、保存、獨立 review 與 exact-head 等保障仍保留。不可僅把 blocker 改名為 follow-up 就解除 gate；原 finding 仍依 [review-findings](../../contracts/review-and-security.md#review-findings) 處置。再做一輪也不自動保證收斂。

#21 的紀錄問題也出現在 PR 建立之前：已 commit 的 round 報告會進入完整 diff。建議在既有政策允許的受控外部位置保存綁定 exact revision／diff 的審查證據，或採其他不改變受審 head 的既有方式；位置與保留仍由專案決定，公開前仍查核資料及外寫授權。本包不禁止提交必要紀錄，也不移動或刪除任何既有證據。

### 公開記錄的遮蔽格式（建議）

[auth-data](../../contracts/authorization-and-stops.md#auth-data) 已限制公開資料。本格式幫助描述問題而不重貼私人值；它不能證明資料安全，也不能代替必要掃描。

| 種類 | 建議公開內容 |
| --- | --- |
| 可疑值 | 種類、在安全來源中的位置，以及必要且不洩漏的類別；長度本身敏感時也省略 |
| email | 是否為 noreply、必要且可公開的提供者類別；不貼私人地址 |
| 路徑或主機 | 用 `<ACCOUNT>`、`<HOST>` 等代號替代私人部分；其餘部分仍檢查敏感性 |
| 命令輸出 | 只保留已檢查的最小遮蔽片段；不貼包含私人值的原始輸出 |
| hash／binding | 私人值即使雜湊，也可能被離線猜測驗證；不把它當匿名化證明或自動公開的理由 |

例如，可寫「commit 身分欄含非 noreply 私人 email；原值留在受控證據」，不附原值或其 hash。相反地，公開 Core 文件本身的 SHA-256 可用於完整性查核；這不是對私人值作可猜測的公開承諾。是否可公開仍依資料內容、來源與有效權責判斷。Claude 的 hash 觀察是來源殘餘風險，不倒寫成它已有全面禁止公開 hash 的規則。

來源：[Issue #21 補充](https://github.com/jeffery777/engineering-workflow-core/issues/21#issuecomment-6514971387)、[Issue #22 補充](https://github.com/jeffery777/engineering-workflow-core/issues/22#issuecomment-6514971936)、[固定背景 CF-001／CF-002](https://github.com/jeffery777/claude-dev-skills/blob/071c1a7ff1f2ce67a605d54ce5c3e85480852b69/docs/core-feedback.md)。

<a id="en"></a>

## English

This optional companion covers point 4 of #21 and the masking format of #22. It adds no severity, stop threshold, record location, or mandatory scan scope, and accepts no other modifying proposal. The formal review and authorization/stop contracts govern.

### Decision options after repeated fixes (suggestion)

The two-round threshold in [wf-verification](../../contracts/workflow.md#wf-verification) triggers reassessment, not automatic stopping. If effective rules require a human decision, a [decision card](decision-cards.md) can compare a root-cause fix, one bounded validation round, moving work to a separate follow-up, or keeping the current state. Moving a mechanism out and delivering the rest is a scope choice for the user, not permission for an agent to lower the DoD.

We suggest recording old/new scope, dependencies, unmet goals, follow-up owner/target/checks, and remaining risk. Necessary safety, authority, integrity, retention, independent review, and exact-head protections remain. Renaming a blocker as follow-up cannot clear a gate. Give the original finding a disposition under [review-findings](../../contracts/review-and-security.md#review-findings). One more round does not guarantee convergence.

The record problem in #21 also occurs before PR creation: committed round reports enter the complete diff. We suggest an existing policy-permitted controlled location for evidence bound to the exact revision/diff, or another existing method that does not alter the reviewed head. The project controls location and retention. Check data and external-write authority before publication. This packet bans no necessary committed record and moves or deletes no evidence.

### Public-record masking format (suggestion)

[auth-data](../../contracts/authorization-and-stops.md#auth-data) already limits public data. This format describes a problem without repeating a private value. It proves neither safety nor completion of a required scan.

| Kind | Suggested public content |
| --- | --- |
| Suspect value | Kind, location in a safe source, and a necessary safe category; omit length if sensitive |
| Email | Noreply status and a necessary public provider category; no private address |
| Path/host | Replace private parts with `<ACCOUNT>`/`<HOST>`; check the remaining parts too |
| Output | Minimal inspected masked excerpt; no raw output containing private values |
| Hash/binding | A guess can verify a private value offline; hashing proves neither anonymity nor permission to publish |

For example, say that a commit identity contains a private non-noreply email and that the value remains in controlled evidence. Omit the value and its hash. A hash of an already-public Core document can support integrity checks; it is not a guessable public commitment to a private value. Publication still follows data, source, and effective authority. Claude's hash observation is a residual risk in the source record, not evidence of a blanket hash ban in that project.

Sources: the linked #21/#22 supplements and fixed CF-001/CF-002 record in the Chinese section. Written per ASD-STE100 principles; full conformance is not verified.
