# Release Notes: v0.28.0

Status: release candidate prepared through Issue #297.

本檔記錄 source/package 候選準備；annotated tag 與 non-draft／non-prerelease
GitHub Release 精確讀回才證明發布。候選合併不授權 tag、Release、部署或記憶啟用。
Merge、tag、Release 與部署保留 separate human gates。

## Synthetic Add And Update

固定 memory-maintenance pilot 新增 `--create-synthetic --scenario add-update`，
從空 managed root 依序新增、修改、盤點、停用及恢復。每個 mutation 顯示完整 preview
並接受獨立 digest；修改另顯示綁定實際前態的完整舊／新內容，兩版各有相符來源。

UPDATE 保留舊版、只召回 current revision；STOP／RESUME 不增加版本。
每步 fresh readback、audit 及新舊關鍵詞核對，故障不自動重試；提交後未知維持 unknown。

## Compatibility And Boundaries

新增可安裝操作能力採 pre-1.0 minor 0.28.0；catalog、installer 與 plugin 同步。
沿用 shared GovernanceCore 與固定 synthetic ports；CLI／Desktop 入口與分層不變。
原 stop/resume 指令相容，無 opt-in 零觸及，production registry 仍空。

不包含真實／原生記憶、任意 import/root、G2、歷史 restore、背景服務或清理。
合成與受控故障驗收不證明完整 G1/MG1、物理儲存、power-loss 或 production qualification。
未改寫歷史 release notes，active guidance 不維護可變的目前發布版本指標。

## Verification And Release Gate

[Issue #297 驗收紀錄](loops/issue-297/verification.md) 分開記載行為測試、受控故障、
套件／隔離安裝驗收及審查；所有結果依實際證據更新，測試不代表發布。
正式 payload 為 annotated tag/title `v0.28.0`、本檔正文、draft=false、prerelease=false；
target 須於候選 PR 合併後核對。tag／Release 與本機部署各自需要授權。

## Traceability

- Issue #297: <https://github.com/jeffery777/codex-dev-skills/issues/297>
- Branch: `codex/issue-297-memory-add-update`
- [Issue #297 plan](loops/issue-297/plan.md)
