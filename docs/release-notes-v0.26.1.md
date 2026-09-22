# Release Notes: v0.26.1

Status: release candidate prepared through Issue #290.

本檔為 source/package 候選準備紀錄；annotated tag 與非 draft／prerelease GitHub
Release 讀回才證明發布。Merge、tag、Release 與部署保留 separate human gates。

## Exact-Head Controller

區分 controller 執行健康與專用 App 的合併判定。缺少收據、尚無 upstream run、
合法 pending／非成功 CI 狀態仍發布 App failure；只有完成 failure 與 native-latest
讀回確認才讓 job 正常結束。異常狀態、API／schema、收據或證據漂移、發布／讀回
故障仍維持 job failure，不把未知結果當成功。既有 output 會在平台存取前拒絕。

## Compatibility And Boundaries

既有控制平面修正採 patch 0.26.1；catalog／installer／plugin 版本同步。
沒有 v2 envelope、offline validator、App 權限、ruleset 或記憶 API/schema 變更。
既有 0.25.0／0.26.0 候選功能與限制沿用其歷史 release notes，未改寫其紀錄。

## Verification And Release Gate

受控測試聚焦異常妥善處置、failure publication/readback、CLI 結果與 workflow
分流，另需 offline package/release-state、獨立 review 與 Security Diff Scan。
實際命令／結果見 Issue #290 驗證紀錄；注入故障不是實體故障或 hosted 驗證。
Controller 只執行 trusted default branch，因此候選 PR 的測試不構成新版 hosted
rollout；合併後 open PR 的實際評估另需讀回。歷史已合併 PR 檢查不改寫。

正式 payload 為 annotated tag/title `v0.26.1`、本檔正文、draft=false、prerelease=false；
target 須於候選 PR 合併後核對。本次準備不授權發布或部署。

## Traceability

- Issue #290: <https://github.com/jeffery777/codex-dev-skills/issues/290>
- Branch: `codex/issue-290-controller-outcomes`
- [Issue #290 plan](loops/issue-290/plan.md)
