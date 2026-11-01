# 決策卡片／Decision cards

[繁體中文](#zh) · [English](#en)

<a id="zh"></a>

## 繁體中文

本文件是 [Issue #25](https://github.com/jeffery777/engineering-workflow-core/issues/25) 的選用伴讀範本，不是權威契約。它整理 [auth-stops](../../contracts/authorization-and-stops.md#auth-stops) 與 [wf-writing](../../contracts/workflow.md#wf-writing) 已要求交代的資訊，不新增停止條件、需求分類或核准機制。若內容不一致，以正式契約及有效的較高優先指令為準。

建議一張卡只問一個需要決定的問題，沿用既有報告或回覆，不另建紀錄系統。提出前先完成不依賴答案的安全工作。卡片代號方便使用者簡答；空白、逾時、建議選項或工具成功都不是使用者的決定。實際操作仍逐項核對授權與必要 gate。

### 選用範本

```text
決策卡 <代號>：<短標題>
問題：<一句話>
為什麼需要你決定：<代理不能自行決定的需求、風險或授權界線>
選項 a：<名稱>
  做法：<具體動作>
  結果：<動作之後的狀態>
  風險：<可能出錯之處與限制>
  成本：<工作、時間、驗證或費用；未量測時寫未知>
選項 b：<名稱；同樣交代做法、結果、風險、成本>
建議與理由：<選項與來源依據>
未決定的後果：<哪些操作等待；哪些安全工作可繼續>
證據：<檔案行號、公開安全來源、命令及已遮蔽的結果>
事實：<有來源的觀察>
推論與未知：<判斷及仍缺少的證據>
```

### 假想示例

某候選規則尚未在兩個 consumer 完成 eval。決策可以比較「保留候選、先交付伴讀」和「先完成兩端候選驗證再處理修改」。前者的結果是本包只有說明文件，修改仍待驗證；風險是提案延後，成本是後續工作包。後者的結果是延後本次交付，風險與成本包含尚未確認的接口相容性及驗證時間。建議依相依性決定，不能把使用者選擇當作 eval 已通過，也不能藉此免除安全或獨立審查。

範本改編自 claude-dev-skills 的 [decision-card.md，固定 revision](https://github.com/jeffery777/claude-dev-skills/blob/071c1a7ff1f2ce67a605d54ce5c3e85480852b69/skills/dev-review/references/decision-card.md)，省去該接口專屬的規則代號與強制採用要求。來源與完整 MIT notice 見 [來源記錄](../provenance/source-map.md#consumer-feedback-companions) 及 [notices](../provenance/upstream-notices.md#claude-feedback-notice)。本範本不把 Claude 專屬規則移植成共用義務。

<a id="en"></a>

## English

This optional companion template addresses [Issue #25](https://github.com/jeffery777/engineering-workflow-core/issues/25). It is not an authoritative contract. It arranges information already required by [auth-stops](../../contracts/authorization-and-stops.md#auth-stops) and [wf-writing](../../contracts/workflow.md#wf-writing). It adds no stop condition, requirement category, or approval mechanism. The formal contracts and effective higher-priority instructions govern any conflict.

We suggest one decision per card in an existing report or reply, without a new record system. First finish safe work that does not depend on the answer. Card identifiers help the user reply briefly. Silence, a timeout, a recommendation, or tool success is not the user's decision. Check authority and required gates separately for each action.

### Optional template

```text
Decision card <identifier>: <short title>
Question: <one sentence>
Why you must decide: <requirement, risk, or authority boundary>
Option a: <name>
  Action: <specific action>
  Result: <state after the action>
  Risk: <possible failure and limits>
  Cost: <work, time, checks, or expense; unknown if not measured>
Option b: <name; the same action, result, risk, and cost fields>
Recommendation and reason: <option and source evidence>
Without a decision: <actions that wait; safe work that can continue>
Evidence: <file and line, safe public source, command and masked result>
Facts: <sourced observations>
Inferences and unknowns: <judgments and missing evidence>
```

### Hypothetical example

A candidate rule has not passed evals in both consumers. Compare keeping the rule as a candidate while delivering companion notes first, with finishing both candidate evaluations before handling the modification. The first option delivers only guidance now and leaves the modification pending. Its risk is delay of the proposal; its cost is a later work packet. The second delays this delivery, with unknown interface compatibility and evaluation time. Choose based on dependencies. The user's choice cannot prove that evals passed or waive safety or independent review.

The template adapts the [fixed claude-dev-skills decision card](https://github.com/jeffery777/claude-dev-skills/blob/071c1a7ff1f2ce67a605d54ce5c3e85480852b69/skills/dev-review/references/decision-card.md). It omits interface-specific rule identifiers and mandatory adoption. See [provenance](../provenance/source-map.md#consumer-feedback-companions) and the [complete MIT notice](../provenance/upstream-notices.md#claude-feedback-notice). It does not make Claude-specific rules shared obligations. Written per ASD-STE100 principles; full conformance is not verified.
