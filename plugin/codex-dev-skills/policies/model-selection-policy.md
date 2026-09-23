# Model Selection Policy

This repository does not hardcode provider-specific workflow assumptions.

Select model capability and reasoning effort by measured task need:

- repository scanning, summarization, and other read-heavy worker packets: favor
  a fast, efficient model profile;
- bounded implementation, routine review, and documentation: use a balanced
  coding and reasoning profile;
- orchestration, ambiguous multi-step work, deep review, security, migrations,
  or cross-module contracts: use a frontier reasoning profile when evals show a
  material quality gain;
- independent grading or final review: use a fresh context and, when practical,
  a separate reviewer profile from the implementer.

When migrating model families, preserve the current reasoning setting as the
baseline and compare it with at least one lower-cost setting on representative
workflow cases. Measure task success, false completion, route selection,
evidence completeness, latency, and token or cost use. Do not assume that the
highest available reasoning effort is the best default.

Model selection changes execution quality and cost; it does not change source
of truth, permissions, human gates, or completion rules.

## Main Agent And Escalation

For demanding project delivery, the optional main-agent recommendation is
Astra-high; it is separate from child-profile qualification and is not a global
product default. The repository provides a two-key example, not an installer
write into personal configuration. Select child profiles explicitly so small
tasks do not unintentionally inherit that main-agent setting.

Reassess task factors after a reasonable correction still fails the same core
check, unexplained root causes, or conflicting authoritative evidence. Use
higher reasoning for cross-system causality, interacting trust boundaries and
major architectural tradeoffs. Environment, data and permission failures are
not reasoning-effort triggers. Reclassification must retain class/tier minima,
fixed-profile digest binding, sandbox and authority. This guidance does not
implement automatic effort changes or add every model/effort combination to
the registry. See the repository document
[Main Agent And Subagent Settings](https://github.com/jeffery777/codex-dev-skills/blob/main/docs/main-agent-and-subagent-settings.md) for locations,
supported profile defaults and the explicit-override boundary.

### First-review risk and missed findings

Before the first review, classify actual impact. CI admission, installer behavior
and cross-module contracts map to existing `high` or `public-contract` risk
factors; security/data/migration use their existing hard triggers. Do not infer
risk from a task title alone or wait for retry failures before selecting deep
review and its verified model/effort. Cost and latency preferences cannot lower
that minimum. Parser or subprocess changes use the applicable integration
boundary reference; they do not automatically imply every high-risk domain.

A missed defect reported as no findings does not increment an observed-failure
retry counter. Evaluate reviewer candidates on independent synthetic cases with
unprimed review prompts, real library/command behavior, defective and correct
controls, and independent grading. Record missed defects, false positives,
maintenance suggestions, documented tradeoffs, evidence quality and usage
separately; finding count is not a quality score. Keep failed attempts and
unknowns. Small synthetic runs cannot establish production equivalence or
qualify a lower-tier reviewer for a high-risk route.

### 返工分類、升級與續行

遇到驗收失敗或反覆修正時才讀本節；正常工作不需建立額外流程或模型矩陣。
父代理使用既有 task brief／驗證紀錄，保留工作包、失敗的核心驗收、原因分類、
修正假設、修正後結果、實際模型／effort，以及下一個動作。一輪修正是
「依假設修改後執行指定驗收」，不是每次工具呼叫、搜尋錯字或預期失敗的負面測試。
以工作包及修正 lineage 累計；SHA、錯誤字串或模型改變不會自行清零。
不得刪除驗收、放寬斷言或隱藏失敗來減少返工數。

| 觀察 | 必須採取的動作 |
| --- | --- |
| 初次驗收失敗 | 先分類為實作／推理、上下文／證據、環境／資料、權限或外部結果不明；記錄可驗證的假設，再做有根據的修正。 |
| 合理修正一次後，同一核心驗收仍失敗 | 父代理重新分類，不再依原假設盲修。若證據指向能力不足，選擇已驗證且符合當次需求的其他模型或較高 effort profile；原因未知時先補證據或獨立診斷。 |
| 同工作包兩輪修正仍陸續出現不同缺陷 | 檢查受影響的完整工作流、上下游契約、環境假設及測試缺口；必要時獨立 review。區分新回歸、先前失敗遮住的問題及真正新增範圍，不能只因錯誤名稱不同而重新開始盲修。 |
| 升級後仍失敗，或已用高 effort | 以最小重現、額外觀測、來源重新核對或新上下文的獨立診斷改變策略；不預設繼續升到最高 effort。 |
| 環境、缺少資料、暫時性工具故障或權限不足 | 使用對應且已授權的 recovery。模型升級不能取得權限；先核對資料／工具契約，必要時向父代理回報精確缺口。 |
| 外部寫入結果不明 | 先讀回結果，確認操作身分、冪等性及目前授權；不得因回應遺失而盲目重播部署、發文或資源建立。 |

上述門檻觸發能力與方法重評，**不是停止任務、假報完成或自動建立新對話的
輪次上限**。已明確需要較強能力或獨立診斷時可提早重評，不必先消耗指定次數。
專案可依真實返工證據調整觸發門檻；另有使用者明確硬上限時遵守該上限並
回報未完成項目，不能把本預設門檻解讀成硬上限。

父代理依目前 runtime 重新執行既有分類、preflight 及適用的 qualification；
記錄升級原因、可用能力、選用結果及驗證。推理深度不足可選較高 effort；
模型或上下文造成反覆錯誤假設時，可換合適模型或獨立角色。不得假定所有
模型／effort 是單一固定優劣階梯，亦不得私改固定 profile、降低 class/tier、
放寬唯讀隔離／權限或沿用不相符的 digest／資格。

若當次介面不能改主代理模型，使用已支援的合格子角色或既定安全 fallback；
修改設定檔不代表目前回合已切換。父代理持續負責整合、驗證及整體完成。
只有真正待決風險、缺少必要授權或沒有安全相容路徑等既有 human gate，才停止
相依操作；同時繼續獨立且已授權的安全工作。改模型不授權 thread create／fork、
外部寫入、破壞性操作或 harness 修改。

兩輪未完成 review/fix 亦依 `context-continuity-policy.md` 評估上下文健康；
優先引用同一份當前證據，不重做相同盤點。能力重評與上下文評估互補，均不
自動轉移 writer、建立對話或放棄目標。

比較升級效果時，計入主代理、子代理、所有失敗／修正、交接、整合與驗收的
總用量及完成時間，保留未完成 attempts。以同等安全與品質下的完整工作包
成本作判斷，不能把便宜但未驗收的結果當成改善。

## V2a Capability Classification

Classify capability need from evidence about the work, not from its task name
alone. Record ambiguity, reasoning depth, code or context volume,
security/data/migration/public-contract risk, write blast radius, latency
sensitivity, cost or token sensitivity, independence or parallelizability, and
verification burden. Security, data, migration, public-contract, and broad-write
risks are non-compensatory: speed or cost preferences cannot average them down.

The minimum reusable capability classes are `fast-read-explorer`,
`balanced-worker`, `deep-reviewer`, and `security-reviewer`. The production
route must explain which factors selected the class and preserve the requested
scope, mutation authority, external-write authority, human gates, and
completion criteria unchanged.

Route contract version 2 keeps those workflow classes stable and adds a
separate ordered capability tier: `mechanical`, `efficient`, `everyday`,
`senior`, `advanced`, `deep`, and `exceptional`. The class owns sandbox and allowed work;
the tier owns the minimum model/reasoning requirement. Use an explicit workload
kind instead of inferring mechanical, exploration, implementation, review,
security-review, or research/orchestration work from a task title.

Select the lowest verified profile in the required class whose tier meets or
exceeds the requirement. A higher tier is a recorded cost-degraded fallback.
The legacy `cost_degraded` field records an ordinal tier difference, not measured
expense. Tier order and eval `latency`/`token_cost` proxies do not estimate model
latency, actual tokens, price or savings.

For V2, `task.quality_preference` accepts `balanced` or `quality-first`; omission
means balanced. Exceptional classification requires explicit quality-first
research/orchestration with at least three complexity triggers and no overriding
safety trigger. Exceptional profile, parent and sequential fallback are eligible
only when the required tier itself is exceptional; preference alone cannot
escalate ordinary work into that tier. A preference never lowers safety minima.

New V2 receipts bind these rules with
`routing_policy_revision: "v2-2026-09-23"`, emitted by the production builder.
Validators retain frozen V2 receipts without a revision and the prior
`v2-2026-09-06` receipts as historical evidence; they are not recomputed,
rewritten, or authorization for a new dispatch. Unknown revisions and mixed
legacy/new fields are rejected. Rebuild a current assignment from current facts;
an old installed digest cannot qualify a new dispatch. V1 behavior remains
unchanged.

Routine read-only review without high complexity or safety triggers retains the
`deep-reviewer` class with an `everyday` requirement and selects the dedicated
read-only `routine_reviewer` baseline. It is not a candidate and does not need
candidate qualification. It never satisfies deep or security work; do not
substitute a workspace-write worker for a reviewer merely to satisfy the lower
tier.

A lower tier cannot silently satisfy a higher-tier route. Use GPT-6 Sol-high
`senior` for complex bounded work that exceeds the GPT-6 Sol-medium balanced
profile, and retain GPT-6 Sol-medium `advanced` for multi-trigger advanced
work. Other GPT-6 effort settings are
eval-first alternatives, not defaults: compare them against the adjacent
published profiles on representative quality, correction, latency, and usage
evidence before adding a permanent route. Do not build a complete
model-by-effort profile matrix.

## Runtime Mapping And Fallback

### Prompt Adaptation

Keep shared authority and completion rules model-neutral. Compose role-specific
instructions with a bounded current task brief; do not maintain a full
model-by-effort prompt matrix. Match extraction output shape, implementation
ownership, reviewer evidence and parent integration duties to the actual role.
Prompt wording cannot change the effective runtime effort or qualify a model.

Evaluate prompt changes with fixed model/effort and case/source inputs first;
then compare supported model/effort configurations with the prompt held fixed.
Retain representative success, false completion, authority, missed findings,
unnecessary clarification, verification repetition and actual usage evidence.
Static prompt cases are review oracles, not model behavior measurements.

Changing profile instructions changes their digest and invalidates mismatched
qualification. Shared skill/template changes may alter behavior without changing
that digest: reassess applicable evidence against the loaded instructions too.
Do not modify historical evidence or qualification records to make it match.
Details and bounded examples are in the repository document
[Main Agent And Subagent Settings](https://github.com/jeffery777/codex-dev-skills/blob/main/docs/main-agent-and-subagent-settings.md).

### Runtime Preflight

Custom-agent roles and concrete model/reasoning mappings are runtime profiles,
not shared workflow truth. Preflight the custom-agent surface, profile validity,
model mapping, reasoning setting, sandbox expectation, and collisions before
claiming the profile is usable. Require current parent-sandbox evidence for any
profile that is not intrinsically read-only, and reject a mapping that would
widen that sandbox. This technical check is separate from workflow write
authorization. Degrade in this order:

1. the lowest sufficient available tier in the same class, respecting explicit
   quality preference; compare actual model cost only with measured evidence;
2. the parent or default model when current facts prove the class and tier;
3. sequential execution when current facts prove the class and tier;
4. a human gate when high-risk work cannot degrade safely.

Unknown availability is not completion evidence and a recoverable mismatch does
not permanently fail the objective.

The parent owns routine qualification and runtime-input preparation. For V2
candidate routing, the shared workflow automatically loads an explicitly
approved user-level qualification store when current facts omit
`enabled_candidates`; it does not ask the user to repeat JSON or CLI options.
Match the actual task to reviewed scope before assigning its scope identifier.
Require matching runtime, current profile/evidence bytes and approval that is enabled and either
explicitly has no fixed deadline or has not expired;
never synthesize a quality claim from availability or a task label. Saved
qualification does not establish current model, effort, native role or sandbox
capability. CLI and Desktop observations remain separate. An invalid or
inapplicable record leaves baseline selection and existing human gates intact.

If a requested capability is unavailable, state the fallback and its risk. Do
not encode host-private aliases or a permanently current model name into public
skills. Runtime profiles may map the capability classes above to models whose
availability has been verified in that environment.

## GPT-6 Baselines And Qualified Astra Candidates

Issue #292 makes GPT-6 the everyday baseline: Luna-low mechanical reader,
Luna-high explorer, Sol-medium balanced worker, Sol-high senior worker and
Sol-medium advanced worker. It also adds the read-only Sol-high
`routine_reviewer` baseline for the deep-reviewer class's everyday tier. The
deep, security and exceptional Astra-xhigh baselines remain unchanged. This is
a user-adopted routing decision; it does not claim repository-measured quality
or cost superiority. The nine baseline identities and three separate Astra
candidates remain distinct.

Issue #249 adopts Astra-xhigh for the deep/security and exceptional baseline
profiles by explicit maintainer configuration choice; the three separate Astra
candidates also use xhigh. The decision is not a benchmark qualification or a
claim of reduced weekly usage. Former model/effort values remain TOML comments. See
[Astra Xhigh Profile Decision](https://github.com/jeffery777/codex-dev-skills/blob/main/docs/astra-xhigh-profile-decision.md)
in the repository for the role matrix, evidence limits and
rollback procedure. The GPT-6 baseline migration does not alter the dated
decision record.

Candidate roles remain opt-in evaluation targets, including when a candidate
and baseline have the same model/effort. Compare representative same-scope work
and a supported lower-effort setting before qualifying each class/tier and exact
profile independently. Previous medium/high profile qualifications do not cover
the new xhigh bytes; max/ultra are not defaults.

Version 2 may select a candidate only for its canonical baseline role, after
current caller facts explicitly enable its exact profile digest and reference
operator-verified real-model quality evidence. Record the runtime interface,
public source, and observation date separately from model/effort availability.
Missing qualification, failed quality, stale profile digest, unavailable model,
unsupported effort, or missing installed bytes cannot activate the candidate.
Remove failed candidates from enabled facts; never reduce the required tier.
Candidates are excluded from implicit fallback searches and from v1 selection.
The same-class sufficient-tier baseline, evidenced parent/default, evidenced
sequential, and human-gate order remains unchanged. Model names and opt-in facts
cannot override sandbox, allowed scope, authority, or high-risk hard triggers.

Current GPT-6 baseline profiles require their current installed bytes and
runtime support, but not candidate-store opt-in. Native parent/default and
sequential fallbacks remain model-neutral evidence paths: they do not assert a
specific non-5.x model. This policy only guarantees that the named GPT-6
profiles themselves do not select 5.x models. No project-source edit installs
profiles, changes personal configuration, or enables a qualification store.

Detailed GPT-6 migration and cost-routing guidance is informational in the
repository document
[GPT-6 Cost Routing](https://github.com/jeffery777/codex-dev-skills/blob/main/docs/gpt6-cost-routing.md).
It is not a required installed-skill dependency or a router price input.

An evidence reference is a trusted operator assertion, not proof that the router
has fetched, graded, or authenticated a benchmark. Offline fixtures cannot supply
production qualification. Native direct custom-role invocation is outside the
router's qualification enforcement. See the repository document
[Astra Routing](https://github.com/jeffery777/codex-dev-skills/blob/main/docs/astra-routing.md) for the bounded
measurement plan and explicitly unverified claims.
