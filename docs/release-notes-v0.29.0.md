# Release Notes: v0.29.0

Status: release candidate prepared through Issue #299.

本檔只記錄 source/package 候選準備；發布須另核對 annotated tag 與正式
GitHub Release。候選、合併、tag／Release 與部署保留 separate human gates。

## Synthetic Historical Restore

固定 memory-maintenance pilot 新增 `--create-synthetic --scenario add-update-restore`，
在 ADD 與 UPDATE 後獨立確認 RESTORE。預覽從相同 snapshot 讀取完整 current
與 retained revision 1，包含來源及原驗證資料，並另顯示新的還原候選。

RESTORE 重新驗證原 pinned Git artifact，以新 validation/evidence 建立 revision 3。
舊版與 proof 保留，一般 recall 只回 current；每步 fresh readback、audit 及關鍵詞核對。
取消保留已確認操作，漂移／到期／重播拒絕；提交後結果不明維持 unknown、不重試。

## Compatibility And Boundaries

新增可安裝操作能力採 pre-1.0 minor 0.29.0，catalog、installer、plugin 同步。
原 stop/resume、add/update 行為及無 opt-in 的零觸及保持相容，CLI／Desktop
沿用獨立入口與共享核心。沒有 core/schema 或 production registry 變更。

不含真實／原生記憶、任意 root/import、G2、背景服務或清理。Synthetic 與受控故障
測試不證明完整 G1/MG1、物理儲存、power-loss 或 production qualification。
歷史 release notes 保持原樣，active guidance 不維護可變的目前發布版本指標。

## Verification And Release Gate

[Issue #299 驗收紀錄](loops/issue-299/verification.md)記載測試、套件與隔離安裝、
正式審查及限制。正式 payload 為 annotated tag/title `v0.29.0`、本檔正文、
draft=false、prerelease=false；target 須於合併後核對，發布及部署須另有授權。

## Traceability

- Issue #299: <https://github.com/jeffery777/codex-dev-skills/issues/299>
- Branch: `codex/issue-299-memory-restore`
- [Issue #299 plan](loops/issue-299/plan.md)
