# Release Notes: v0.31.1

Status: release candidate prepared through Issue #306.

本檔記錄 source/package 候選準備；發布狀態另以 annotated tag 與正式 GitHub
Release 查證。候選、合併、tag／Release 與部署保留 separate human gates；
已取得的明確授權可依原範圍續行，審查或候選文件不自行授權發布。

## Runtime Checkout And Continuation Contracts

共享編排依使用者／repo 偏好、既有修改、writer ownership、所需 base 及隔離
需求選擇 local 或 worktree，偏離偏好時說明原因。本專案單一進行中話題優先
沿用 local；可重用技能不把此偏好套給所有專案，也不要求所有 worktree 都逐次
詢問。新對話、外部寫入及破壞性操作仍依自己的授權處理。

修正 Desktop `create_thread` 的 local 預設，保留當次 callable 對 Git worktree
的明確使用者意圖要求；此限制不擴張為 CLI／共享層通則。Fresh rollover 可用
已乾淨、符合 checkpoint branch／HEAD 且具 exclusive ownership 的 saved
local checkout，目的端唯讀核對後才取得 writer。

目前任務 `create_worktree` 先盤點及重用適合的 active worktree；補齊
`allowAsync: true`、remote default branch 起點與 pending `operationId`
完成讀回。Desktop fork 可能包含 interrupted active turn，先查證 Git、操作
結果及來源 writer，不因複製文字推定完成或重播不明操作。

CLI 薄入口同步說明 local/worktree 與 cwd 選擇；非互動 executor 的 private
clone、clean-source、exact-head 及 integration checks 保持必要。

## Compatibility And Boundaries

採 patch `0.31.1`：修正可安裝操作指引，不新增公開 mode、request schema、
CLI executor 功能或 installer 行為。Catalog、installer 版本及 generated
plugin manifest/package 同步。CLI／Desktop 獨立入口與共享完成判定保持分層。

不新增 app-server integration、未公開 Desktop internals、背景服務、原生
memory 啟用或 migration。既有記憶、個人設定、session 及 cache 不屬於部署
或舊版套件備份清理範圍。歷史 release notes 保留原貌；active guidance 不維護
可變的目前發布版本指標。

## Verification And Release Gate

使用 pinned Python 執行 runtime／context-continuity 契約回歸、package 與
release-state 檢查、offline repository validation 及 diff hygiene；安裝流程
實作不變，相關既有證據須核對內容與範圍後重用。文件測試不是 live runtime
mutation 驗收，未宣稱已重跑 live start／resume／fork 或 SSH caller。

發布前須完成獨立文件／程式審查、Security Diff Scan 與完整 base-to-head
exact-head Merge Review；所有 findings 修正並重審為零。另讀回最新 hosted
CI、strict JSON receipt、專用 App check 與 ruleset。PR head 改變必須重審完整
range，不能沿用先前 verdict。

正式 payload 為 annotated tag/title `v0.31.1`、本檔正文、draft=false、
prerelease=false；target 須於合併後核對。發布後讀回 tag object、dereferenced
commit、Release target 與正文，再從 immutable 來源部署。核對安裝來源 parity、
`install.sh diff --all` 及受保護資料後，才依授權清理本次新增且已盤點的舊版
套件備份；既有未知資料不受此授權影響。

## Traceability

- Issue #306: <https://github.com/jeffery777/codex-dev-skills/issues/306>
- Branch: `codex/issue-306-runtime-checkout-contracts`
- [2026-09-29 runtime 相容性證據](codex-runtime-compatibility-evidence-2026-09-29.md)
- Compare: <https://github.com/jeffery777/codex-dev-skills/compare/v0.31.0...v0.31.1>
