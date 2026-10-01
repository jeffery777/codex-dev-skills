# Release Notes: v0.33.0

Status: release candidate prepared through Issue #312.

本檔記錄 source/package 候選準備，不代表發布。Publication 以 annotated tag
與非 draft／非 prerelease 的 GitHub Release 讀回為準；各階段保留 separate human gates，
本次依使用者已給予的發行與部署授權續行。

## 正式本機 memory-maintenance 入口

Issue #310／PR #311 新增 default-off、單專案／單 host 的固定 operator CLI，
支援 add、update、stop、resume、restore。新 root 初始化後保持 disabled；
每次完整 canonical review、當次 digest 接受及 freshness 重查後，執行一次
mutation，再獨立 fresh readback，保留 applied／not-applied／unknown。

預設 human；明確受委派 agent 使用相同接受機制，actor flag 僅作稽核標記。
同 OS 帳號與已審查 build 是信任邊界，不宣稱抗同帳號偽造或驗證上游委派。
Desktop 沿公開互動終端使用同一 CLI，沒有 native confirmation port 資格。

## Compatibility And Boundaries

正式入口要求可追溯官方 source 的隔離 Python 3.12.9／SQLite 3.53.4 Darwin
runtime，不能以系統 SQLite 或一般測試 Python 取代。技能部署不自動建立
runtime、不啟用 memory root、不執行既有 memory migration。
容量不足安全拒絕；admission 不是 reservation。不宣稱完整 MG1、實體 FULL、
power-loss、RSS／deadline 或滿庫 stop 保證。通用 production registry 仍空。
升級前須以原版本 disable 已啟用 root；fingerprint 漂移會拒絕，沒有自動 migration。

本次採 minor `0.33.0`，因新增正式操作入口與受限本機契約。版本同步不更改
已合併的操作程式；歷史 release notes 保留為原時點紀錄。

## Verification And Release Gate

PR #311 的完整 exact-head review、Security Diff Scan、12-shard hosted CI、
receipt 與 dedicated App gate 已於其合併前通過。原正式 TTY 五操作與
disabled-root readback 為該次驗收證據，不證明本次部署已啟用任何 root。

Installer 測試已保留階段／stdout／stderr；D310-V02 間歇異常根因仍 unknown，
使用者接受 Deferred，補測與該次 hosted CI 通過不表示根因已修復。固定環境
再現、CI failure 或與 patch 相關證據會重新阻擋。用量比較缺值保留 unknown，
不宣稱單任務 credits 或節省率。

本候選另須離線 repository／release-state／package checks、獨立發行敏感 review、
完整 base-to-head Merge Review、hosted CI 與當次 receipt／App／ruleset 讀回；
此檔不能取代那些 gate。發行與部署依使用者明確授權逐步執行並讀回。

## Traceability

- Issue #312: <https://github.com/jeffery777/codex-dev-skills/issues/312>
- Feature: Issue #310 / PR #311
- Branch: `codex/issue-312-release-v0330`
- [本機操作指南](../skills/loop-engineering/references/memory-maintenance-local.md)
- [受限儲存契約](../skills/loop-engineering/references/memory-maintenance-local-storage.md)
- [功能驗證與 finding dispositions](plans/issue-310-verification.md)
- Compare: <https://github.com/jeffery777/codex-dev-skills/compare/v0.32.0...v0.33.0>
