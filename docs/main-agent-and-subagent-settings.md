# Main-agent and subagent settings

This repository owns reusable configuration sources and routing policy. Those
sources are not necessarily the files a running Codex client loads. Installation
and explicit client settings determine the effective runtime configuration.

| Concern | Repository source | Runtime location or control |
| --- | --- | --- |
| Main-agent recommendation | `examples/project-main-agent.config.toml` | Trusted project `.codex/config.toml`, or user `~/.codex/config.toml` for a cross-project default |
| Explicit conversation choice | No repository-owned current value | Desktop model/effort picker or CLI `--model` and configuration overrides |
| Child role model, effort and sandbox | `agent-profiles/*.toml` | Installed custom-agent profiles, for example `~/.codex/agents/` or a selected project agent root |
| Classification and fallback | `policies/model-selection-policy.md`, `skills/loop-engineering/scripts/agent_routing.py`, `loopctl.py` | The invoked workflow and its installed scripts |
| Canonical role contracts | `skills/loop-engineering/references/agent-profile-registry.json` | The canonical registry shipped with the invoked skill |
| Availability and quality opt-in | Caller-supplied runtime facts | Current destination/runtime evidence, not a permanent repository assertion |

The main-agent example selects Astra-high for demanding delivery, decomposition,
integration and acceptance. It is a project recommendation, not an OpenAI-wide
default or a measured equivalence claim. Routine bounded work may use medium;
Sol-high is an explicit alternative when Astra is unavailable. Do not silently
substitute a model or infer capability from its name alone.

For CLI/IDE, official precedence is explicit CLI overrides, trusted project
configuration, a selected configuration profile, user configuration,
cloud-managed defaults, system configuration, then built-in defaults. A user config is therefore not inherently
project-specific. Desktop conversation selections must be verified through the
active public client control; copying a file does not prove an existing Desktop
conversation changed model or effort. See the official
[configuration basics](https://learn.chatgpt.com/docs/config-file/config-basic)
and [model controls](https://learn.chatgpt.com/docs/models).

## Adoption

Read and merge the example's two keys into the intended configuration layer;
do not overwrite an existing file or copy secrets and machine-local settings
into this repository. The installer does not install this example or change
personal main-agent defaults. This Issue does not apply it to the current chat.
Confirm the selected model/effort in the destination before delegating work.

Child roles should receive explicit model/effort settings from their selected
profile. Otherwise native inheritance can make a small child task inherit the
main agent's stronger configuration unnecessarily. Official custom-agent
resolution first chooses explicit spawn values, configured subagent defaults,
or parent settings; model/effort in the selected custom-agent file then take
precedence over those resolved values.
If a spawn/default selects a model without an effort, resolution uses that
model's default effort; a custom file setting only model preserves the resolved
effort. Verify support and effective settings
in the destination runtime; an override argument cannot be assumed to replace
a custom file's fixed mapping. See the official
[subagent settings](https://learn.chatgpt.com/docs/agent-configuration/subagents#choosing-models-and-reasoning).

Issue #292 adopts GPT-6 for everyday baseline profiles: Luna-low mechanical,
Luna-high explorer, Sol-medium balanced and advanced, and Sol-high senior. It
adds the read-only Sol-high `routine_reviewer` baseline for the
deep-reviewer class's everyday tier. Deep, security and exceptional baselines
remain Astra-xhigh. The three separate Astra-xhigh candidates remain qualified
opt-ins with exact scope, runtime, profile digest and current installed-byte
requirements. `routine_reviewer` is not a candidate and never satisfies deep
or security review. This is a user-adopted routing decision, not a claim that
this repository measured GPT-6 quality, cost, or task success superiority.

The source change does not install profiles, create or enable a qualification
store, or change personal configuration. Confirm current installed bytes and
destination runtime before delegation. Issue #249's dated Astra configuration
record remains historical; see [the decision and rollback record](astra-xhigh-profile-decision.md).

Routine read-only review now has an everyday capability requirement and uses
the dedicated read-only GPT-6 Sol-high baseline. Parent/default and sequential
fallbacks remain model-neutral evidence paths; their use does not prove which
model the runtime selected. The named GPT-6 baseline profiles themselves do
not contain a 5.x mapping.
Exceptional selection, including fallback, requires quality-first
research/orchestration with the classifier's multiple complexity triggers.
Tier rank and `cost_degraded` are policy labels, not usage or price measurements.

During normal delegation, shared delivery/orchestration skills make the parent
prepare current runtime facts and invoke the router, which automatically
discovers approved user qualification records. Users do not repeat candidate
JSON or qualification-path arguments. This is scoped workflow automation, not
a global conversation hook. See [automatic qualification loading](agent-qualification-autoload.md)
for one-time adoption, revocation and the separate current-runtime checks.
When multiple qualified Astra candidates meet the same baseline and scope,
select the lowest sufficient tier and preserve stable registry order within that
tier; the order is not price evidence. See [GPT-6 cost routing](gpt6-cost-routing.md)
for the point-in-time migration and rate context; it does not affect router logic.

## Escalation is a workflow decision

The main agent first gathers repository evidence, records task factors and uses
the existing class/tier classifier. Security, data, migration, public-contract
and broad-write risk cannot be offset by a desire for speed. Use high-effort
review for those boundaries; implementation still requires the appropriate
scope and authority.

Reassess after a reasonable correction fails the same core check, when a root
cause cannot be explained, or when authoritative evidence conflicts. Update the
bounded task assessment and select a supported, sufficient profile. Examples:

- Clear extraction or mechanical work starts at GPT-6 Luna-low. Ambiguous
  cross-file reasoning should move to an appropriate GPT-6 Sol or stronger role.
- Exploration starts at GPT-6 Luna-high; ordinary implementation at GPT-6
  Sol-medium; complex bounded implementation may require GPT-6 Sol-high senior.
- Advanced work starts at GPT-6 Sol-medium or a qualified Astra-xhigh candidate.
  If deeper reasoning is needed, use an explicitly supported high-effort task
  configuration only where the runtime and workflow permit it. It is not an
  automatic effort-changing controller. The Astra-xhigh implementation candidate
  still needs its own matching qualification.
- Deep/security review uses the maintainer-adopted Astra-xhigh baseline. This
  does not raise every task's required capability tier or qualify a candidate.
  Max/Ultra are not default escalation targets.
- A delivery main agent starts at Astra-high under this optional preset; xhigh
  requires the same concrete depth triggers and a supported client control.

These conditions are decision guidance, not an implemented automatic retry or
effort-changing controller. Do not alter a fixed profile's bytes/effort in place
and retain its old qualification digest. The current classifier chooses existing
profiles; new combinations require an explicit supported override outside that
fixed-profile route, or a separately validated profile change. Neither route may
lower the required class/tier or widen sandbox and authority. Missing data,
permissions or environment support require resolving those constraints rather
than increasing reasoning effort.

## 依當次工作組合提示詞

使用 [共用契約](../policies/reusable-workflow-contract.md)的 Contextual Prompt
Composition 與 [Agent Task Brief](../templates/orchestration/agent-task-brief.template.md)。
主代理依任務先選既有路由，再填目標、ownership、來源、授權、DoD、必要
驗證與升級條件。這是 workflow 指引，沒有新增動態 prompt engine、schema
或 runtime 攔截器，也不會自動修改模型或 effort。

| 角色／既有配置 | 當次 brief 的重點 |
| --- | --- |
| Mechanical reader／GPT-6 Luna-low | 有界輸入、明確輸出欄位、缺值處理；非機械語意交回主代理。 |
| Explorer／GPT-6 Luna-high | 搜尋問題、證據位置、範圍與停止搜尋條件。 |
| Worker／GPT-6 Sol-medium、GPT-6 Sol-high | 依分類選角色；指定檔案 ownership、可自行決定的局部細節、行為驗收與必要測試。 |
| Routine reviewer／GPT-6 Sol-high | 唯讀 everyday review；不得用於 deep/security review 或自行修正。 |
| Deep/security reviewer／Astra-xhigh | 唯讀、反例與風險邊界、severity／檔案證據、漏測與限制；不得自行修正或合併。 |
| Exceptional researcher／Astra-xhigh | 仍需 quality-first 與分類條件；列出比較問題、證據衝突及研究停止條件。 |
| Delivery owner／可選 Astra-high | 拆解、必要委派、結果整合與整體完成；對已授權階段持續推進。 |
| 已合格的 Astra candidates | 仍沿用對應角色責任；xhigh、runtime、scope 與 digest 需各自符合資格，舊 medium/high 資格及主代理設定不能代替。 |

例如：worker 可自行沿用現有 helper 完成已接受的行為與焦點測試；發現須改變
public API 才回報主代理重新評估。reviewer 的既定工作若是 public API 審查，
則應自主完成唯讀查證，不因該關鍵字停下來。主代理需要合併時，先查有效
使用者授權與 exact-head gate；測試通過既不自授權，也不撤銷既有授權。

OpenAI 的 [Astra prompting guidance](https://developers.openai.com/api/docs/guides/latest-model#prompting-best-practices)
於 2026-09-09 查閱，提示稽核指令衝突、續行、委派、文字風格及驗證尺度。
本專案將共通部分放在契約與 brief，保留各角色的權限、模型及資格邊界。
沒有實測依據時不追加 Astra 專屬補丁；官方範例亦不替代本專案的必要 gates。

### 配對評估與證據新鮮度

先固定模型／effort、案例、來源版本、工具與權限，比較舊／新提示詞；再固定
提示詞，比較 GPT-6 baseline、Astra 同 effort 與支援的較低 effort。提示詞變更
與模型／effort 遷移分開 A/B 比較。使用隔離
checkout、實際載入的 instructions／profile digest 與獨立評分。正式 gate
仍使用已合格的角色，較低 effort 的試驗結果不能直接作高風險驗收。

記錄成功、false completion、越權、漏報 blocker、非必要澄清、重複驗證、
修正輪數、wall time 與實際 usage；缺值保持 unknown。受影響模型需代表性
回歸案例，不能只測一個模型後推論其他 GPT-6 或 Astra role 也改善。案例 oracle 與離線
tests 只驗證契約／套件，不能證明模型遵循或速度／成本優勢。

變更 profile 文字會改 digest，不可沿用不相符資格；只改共用 skill/template
也可能改行為，即使 profile digest 相同仍須檢查受影響 evidence。保留歷史
pilot 原始紀錄；新增評估須有明確執行範圍與資源額度。Issue #292 的代表性
CLI acceptance 結果及保留的失敗見 [verification record](loops/issue-292/verification.md)；
有界案例不等於完整品質 qualification 或成本優越結論。
