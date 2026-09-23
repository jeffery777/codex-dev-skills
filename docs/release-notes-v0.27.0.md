# Release Notes: v0.27.0

Status: release candidate prepared through Issue #292.

本檔為 source/package 候選準備紀錄；annotated tag 與 non-draft／non-prerelease
GitHub Release 精確讀回才證明發布。Merge、tag、Release 與部署保留 separate human gates；
本紀錄本身不授權這些操作或安裝。

## GPT-6 Daily Profiles

日常角色改用 GPT-6 Sol／Luna：mechanical reader 為 Luna-low、explorer 為 Luna-high，
balanced／advanced worker 為 Sol-medium、senior worker 為 Sol-high。新增 Sol-high
read-only routine reviewer，僅承接 everyday tier；deep/security/exceptional 仍用
Astra-xhigh。正式 inventory 為 9 baseline＋3 既有 Astra candidates。

新 route builder 使用 `v2-2026-09-23`；歷史無 revision 與 `v2-2026-09-06` receipts
各按原語意驗證，不以新角色重寫舊證據。現行具名 profiles 不再使用 GPT-5.5/5.6，
歷史 fixtures 與紀錄保留。Runtime、installed bytes、class/tier、sandbox 與 authority
仍需核對；Astra candidates 保留既有資格條件。

## Skills And Rework

交付、協調及 loop 入口按階段載入 context、qualification 與工具編排引用。
返工先記錄失敗分類、修正假設、profile 與結果，再按既有門檻重評；環境、資料
及權限問題不藉由增加 effort 解決。成本文件分開說明官方 Codex credits、API
費率與實際任務用量，不把費率差異當成已測量的工作成本改善。

## Compatibility And Boundaries

日常預設及 installed routing 能力變更採 minor 0.27.0；catalog／installer／plugin
版本同步。這是專案來源發布，不會更新個人安裝、設定或 qualification store。
舊 profile bytes 不能作為新 dispatch 的 freshness 證據；另行授權安裝時需 update。
Parent/default fallback 保持 model-neutral 能力證據，不憑空推論其 model 世代。

全域規範、memory default-off、授權與 merge/release gates 維持原邊界，既有歷史
release notes 不改寫。舊模型退役時間屬點時官方資訊，不由此套件決定平台可用性。

## Verification And Release Gate

[Issue #292 驗證紀錄](loops/issue-292/verification.md) 區分 deterministic contract
測試、六個真 CLI packets、獨立審查、安全掃描與 hosted evidence。
CLI explicit configuration 不等於 Desktop native-role qualification；小型有界
驗收不證明完整模型等價、長任務優勢、實測成本節省或 ME-01/ME-02/ME-03 全部完成。

正式 payload 為 annotated tag/title `v0.27.0`、本檔正文、draft=false、prerelease=false；
target 須於候選 PR 合併後核對。Active guidance 不維護目前發布版本的可變指標。

## Traceability

- Issue #292: <https://github.com/jeffery777/codex-dev-skills/issues/292>
- Branch: `codex/issue-292-gpt6-routing`
- [Issue #292 plan](loops/issue-292/plan.md)
- [GPT-6 cost and routing](gpt6-cost-routing.md)

## Known Issue: CLI command event gap

Codex CLI 0.156.0 的 early sandbox denial 可回傳工具失敗結果，卻缺少
`command_execution` JSONL item。本專案已緩解錯誤判讀，上游仍未修復；
同一 heredoc 在本專案措施後仍可重現，不能稱修復後 PASS。
[根因與證據](loops/issue-292/heredoc-rca/README.md)、
[上游 #47433](https://github.com/openai/codex/issues/47433)、
[本專案後續 #293](https://github.com/jeffery777/codex-dev-skills/issues/293)。
此已知問題不取消已驗證的功能／routing 契約，亦不支持單凭缺事件降低模型
評價。依使用者決定在必要 gates 通過後發行；上游修復驗證持續獨立追蹤。
