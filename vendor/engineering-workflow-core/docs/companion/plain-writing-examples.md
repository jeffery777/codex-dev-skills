# 簡明寫作例子／Plain-writing examples

[繁體中文](#zh) · [English](#en)

<a id="zh"></a>

## 繁體中文

本文件供文件作者與 reviewer 選用，說明如何運用 [wf-writing](../../contracts/workflow.md#wf-writing) 的讀者、術語及精度要求。正式繁中契約為準；本伴讀不新增義務、固定用語、禁用詞表、認證或 gate，也不要求逐篇使用本表。以下均為假設情境，不是實際測試、審查、授權或部署紀錄。

先確認讀者需要理解或執行什麼，再選擇詞語。可用熟悉的動詞說清楚行動時，減少行話和多個名詞連用。必要技術詞、通行縮寫及原語名稱仍可保留，依讀者需要在首次使用時解釋；面向熟悉領域的讀者，不必反覆解釋。不要為了少用英文而改動命令、識別字、引用或授權原文。

| 情境 | 較難讀的寫法 | 較清楚的寫法 |
| --- | --- | --- |
| 名詞堆疊；保留前提與範圍 | 部署前進行審查證據完整性驗證作業。 | 部署前，確認所有必要的審查證據齊全。 |
| 對首次接觸流程的讀者解釋縮寫 | CI 未執行，不能標示通過。 | 持續整合（Continuous Integration，CI）檢查尚未執行，不能標示為通過。 |
| 減少不必要的中英混用；保留操作授權 | Review 完成後，仍須 user approval 才可 merge PR。 | 審查完成後，仍須取得使用者的合併同意，才可合併變更請求（pull request，PR）。 |
| 保留精確命令與驗證限制 | 跑 `git diff --check` 做 whitespace validation；PASS 不代表 review complete。 | 執行 `git diff --check` 檢查空白字元問題。這項檢查通過，不代表審查已完成。 |

例子的改寫只處理表中情境。實際文件仍保留原有行動者、必要條件、適用範圍、數字、風險、限制及操作權限，不由短句推導測試通過、必要 review 已完成或任何執行環境具備技術控制。`git diff --check` 是 Git 命令字面，不是 Core 新增的通用必跑命令。

英文技術文件仍依正式契約處理 ASD-STE100；本頁例子未完成正式規則、受控詞典及適用技術詞的完整核對。繁體中文採簡明原則調適，不宣稱符合 ASD-STE100 或存在官方中文版本。寫作改善不證明 runtime、模型或 consumer 已遵循。

<a id="en"></a>

## English

This optional companion helps document authors and reviewers apply the reader, terminology and precision requirements in [wf-writing](../../contracts/workflow.md#wf-writing). The Traditional Chinese contract governs. This guide adds no duty, fixed phrase, prohibited-word list, certification or gate. A document need not use this table. All examples are hypothetical, not records of tests, reviews, permission or deployment.

First identify what the reader needs to understand or do. Use familiar verbs where they can state the action precisely. Reduce unnecessary jargon and noun sequences. Keep necessary technical terms, established abbreviations and original-language names. Explain them on first use when the reader needs it; avoid repeated explanations for readers familiar with the field. Preserve commands, identifiers, required quotations and license text.

| Context | Harder to read | Clearer wording |
| --- | --- | --- |
| Noun sequence; retain the prerequisite and scope | Perform pre-deployment review evidence completeness validation. | Before deployment, check that all required review evidence is present. |
| Explain an abbreviation to a reader new to the process | CI was not run. Do not report it as passed. | Continuous integration (CI) checks were not run. Do not report them as passed. |
| State the action and permission | After review completion, user approval remains a PR merge prerequisite. | After review, obtain the user's permission before merging the pull request (PR). |
| Keep the exact command and verification limit | Execute `git diff --check` for whitespace validation; PASS does not establish review completion. | Run `git diff --check` to check for whitespace errors. A successful check does not mean that review is complete. |

These rewrites address only their stated contexts. In real documents, retain the actor, prerequisites, scope, numbers, risks, limits and operation authority. A short sentence proves neither test success, completed required review nor technical enforcement in an execution environment. `git diff --check` is an exact Git command, not a new universal Core check.

English technical text remains subject to the formal contract's ASD-STE100 requirements. This page uses its plain-writing principles; full conformance is unverified. The examples have not been checked against all formal rules, dictionary entries and applicable technical terms. Traditional Chinese adapts plain-writing principles and claims neither ASD-STE100 conformance nor an official Chinese standard. Clear wording does not prove runtime, model or consumer conformance.
