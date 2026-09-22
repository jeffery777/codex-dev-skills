# Release Notes: v0.26.0

Status: release candidate prepared through Issue #288.

本檔是 source/package 候選準備紀錄；annotated tag 與非 draft／prerelease GitHub
Release 讀回才證明發布。Merge、tag、Release、部署與真實記憶啟用保留 separate human gates，依各自有效授權及適用 gate 執行。

## Synthetic Maintenance

新增固定 synthetic stop/resume 操作入口，沿用 GovernanceCore preview／authorize／
execute／readback。每個操作顯示完整 preview、接受精確 digest，等待後重驗並單次執行。
stop 保留版本且一般查詢不命中；resume 重驗來源且不新增內容 revision。

取消、過期、漂移、鎖衝突、交易/proof/readback/輸出故障與程序中斷均以安全拒絕或
unknown 處置，不自動重試、不宣稱 rollback；新讀回及新接受才允許新操作。
操作與限制見 [maintenance pilot](../skills/loop-engineering/references/memory-maintenance-pilot.md)。

## Compatibility And Boundaries

新增可安裝能力採 pre-1.0 minor 0.26.0，catalog／installer／plugin 同步。
無 schema migration 或既有 M1 API 變更；既有 loop-engineering 安裝群組包含新入口。
累積功能另含 0.25.0 候選的 memory-audit 能力，參見其歷史 release note。

預設停用，production registry 仍空；僅當次新建一筆固定 synthetic item／source。
不接受既有 root、任意 JSON/import、舊 grant、原生記憶、跨專案或 G2 清理。
Fixture 保留，沒有 cleanup；synthetic PASS 不構成 production 或物理耗盡資格。

## Verification And Release Gate

驗收含聚焦故障處置、offline repo／package／release-state、隔離 fresh install／upgrade、
獨立 code/data deep／docs／security review；PR 另需完整 exact-head review、CI、receipt／App。
命令與實際結果保留於 Issue #288 交付證據，候選文字不代替執行結果。

正式 payload 為 annotated tag/title `v0.26.0`、本檔正文、draft=false、prerelease=false；
target 須於候選 PR 合併後核對，尚未發布或部署的項目不得由候選準備推定完成。

## Traceability

- Issue #288: <https://github.com/jeffery777/codex-dev-skills/issues/288>
- Branch: `codex/issue-288-memory-maintenance-pilot`
- 設計與驗收：[Issue #288 計畫](loops/issue-288/plan.md)。
