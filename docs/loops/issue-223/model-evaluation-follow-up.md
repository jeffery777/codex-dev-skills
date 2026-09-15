# Issue 223: Measurement And Adoption Follow-up

Owner: repository maintainer and the delivery owner of an explicitly authorized
measurement packet. Durable target: this file under Issue #223.

## Remaining Questions

| ID | Question | Current disposition | Promotion trigger |
| --- | --- | --- | --- |
| ME-01 | Does progressive disclosure reduce actual task usage without missed constraints? | Deferred to paired task trials; static footprint is available now. | Before publishing a quantitative token/cost improvement claim. |
| ME-02 | Can an everyday read-only reviewer replace the current deep fallback? | Deferred; no new profile or registry mapping is activated. | Before changing the routine reviewer default. |
| ME-03 | Do the exact Astra custom profiles outperform their baseline and lower-effort alternatives? | Deferred; the existing subscription pilot did not activate the full custom-profile instructions and leaves review comparisons incomplete. | Before adding production qualification or changing defaults. |

The deferral is deliberate: synthetic routing correctness and model availability
cannot establish task quality or spending efficiency. Existing profiles, sandbox
rules and qualification gates remain in force. The remaining risk is an
unmeasured performance tradeoff, not permission to drop review requirements.

## Paired Trial Design

1. Freeze a representative task set: a local implementation, routine review,
   ambiguous cross-file review, security-boundary review and installed runtime
   handoff preparation. Use identical source revisions, tool permissions,
   acceptance criteria and environment for each pair. No live external action
   is needed in these tasks.
2. First compare the old and new instructions using the same model/effort and
   fresh context. Then evaluate profile changes separately so prompt changes
   and model changes are not confounded.
3. For a profile trial, activate the exact production developer instructions,
   model, effort, sandbox and profile digest. Record the actual native dispatch
   surface; a CLI observation does not qualify Desktop. Compare the baseline,
   the candidate at matching effort and one lower supported effort.
4. Repeat each pair with balanced run order. Start with five completed runs per
   condition as a bounded pilot; report variability and incomplete attempts,
   and expand only if the decision remains uncertain and the run is authorized.
5. Grade independently for correctness, missed blockers, false completion,
   authority violations, evidence completeness, correction rounds and task
   completion. Preserve hard safety and contract checks before comparing usage.
6. Record actual input, cached input, output and reasoning tokens when available,
   wall time and failure classification. Missing usage is unknown, not zero.
   Report median and spread. Account usage and API dollar cost are different
   measures; use current verified pricing only for a relevant API cost analysis.

### Issue #255：當前 runtime 與返工比較

- 每批記錄 Desktop app/build、實際 CLI／內附 runtime、模型／effort、可驗證的
  service tier、source/diff、完整已載入的 profile／skill／prompt 身分與權限。
  CLI 與 Desktop 分開；共享 skill 改變時，不能只看 profile digest 沒變。
- harness／工具／授權／壓縮或技能載入更新後，重跑受影響的成對案例；
  不把更新前後樣本混合當成模型優劣。歷史試跑維持原始條件與限制。
- 納入[返工語意案例](../issue-255/prompt-cases.md)，再以代表性實作驗證
  同錯誤反覆發生、不同錯誤累積、能力升級及父代理續行；情境回答不能
  代替實際返工或長任務完成證據。
- 對完整工作包計入失敗、重試、交接、父代理整合與驗收的用量及時間。
  保留不可用、未完成、漏報與升級後更慢的結果；不只比較成功 child。
- 優先比較日常唯讀 reviewer 的合適較小模型，以及主代理／深度角色的
  Astra-high 與現有 xhigh。各自使用相同品質與續行要求，不建立全模型矩陣。
  單案例 screening 不授權修改 baseline、安裝 profile 或建立 production 資格。

## Acceptance And Recovery

Prefer the lower-usage condition only when it meets the same task-quality and
safety bar. Any missed material blocker, unauthorized action or false completion
requires investigation before adoption; aggregate speed cannot offset it.
Keep neutral or worse outcomes visible. A small pilot is not a universal
equivalence claim, and shorter input may still yield slower completion.

Publish a qualification only after exact scope/runtime/profile/evidence bindings
are reviewed and the operator approves adoption. Retain baseline fallback and a
clear revocation path. Do not edit personal configuration or an approved store
merely to prepare this measurement plan.

## Guidance Behind The Changes

The instruction split follows OpenAI's progressive-disclosure guidance in
[Build skills](https://learn.chatgpt.com/docs/build-skills). Model/effort choices
remain task-dependent under the official
[subagent settings](https://learn.chatgpt.com/docs/agent-configuration/subagents).
The approved audit also used the current
[model guidance](https://developers.openai.com/api/docs/guides/latest-model)
and [evaluation practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices).
These support bounded prompts and empirical comparison, not automatic removal
of repository-specific safety or evidence requirements.
