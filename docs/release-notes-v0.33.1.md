# Release Notes: v0.33.1

Status: release candidate prepared through Issue #330.

本檔是 source/package 候選準備的 point-in-time 紀錄，不代表發布。
Publication 以 annotated tag 與非 draft／非 prerelease 的 GitHub Release
metadata 讀回為準；commit、merge、tag、Release 與部署保留 separate human gates。
本次使用者已授權維護版發行；沒有安裝或部署授權。

## 必要相容性回移

從正式 v0.33.0 commit `ad2e8a0772768b01d6e675a43b23047efc68ea39` 回移
PR #331 的共享 preflight 修正：fresh custom-profile route 必須提供已觀察的
parent sandbox，未知 parent 或 historical sentinel 不再產生 readiness；
歷史收據仍可驗證。子代理繼承 parent 權限，profile 的 sandbox 是 workflow
expectation，不能作為獨立技術唯讀隔離的證明。

Desktop sidebar 指引依 2026-10-14 公開 callable 校正：排序只接受 `manual`／
`updated_at`，`projects` 是 `chats` 的別名，兩者同時提供必須一致。
補齊 v0.33.0 缺少的 `orbit`（`Your dot`）heading 與 synthetic 範例；
保留 call-site schema、使用者意圖、完整自訂 IDs、讀回及手動 fallback。
Hooks 文件校正 command／`mcp_tool` 的公開支援；command 範本未改或啟用。

## Compatibility And Boundaries

這是 patch `0.33.1`，只修正相容性與證據判讀，不增加操作功能。
CLI／Desktop 薄入口與共享層仍分開，CLI executor、profile TOML／registry、
授權及完成標準保持既有契約。Generated plugin 同步 canonical 來源。
維護 PR 僅合入 `codex/issue-330-maintenance-v033`；不合回或覆寫 main，
不納入 main 的未發布 0.34 候選、local／第三方模型、Agent Memory 或 Hermes 新投入。

Public help、公開 schema、unit tests 及 package parity 是有限證據，不能證明
live start／resume／fork、Desktop mutation、OS 唯讀隔離或跨平台完整資格。
#242／#251／#293 的既有上游缺口未在本次修復。
v0.33.0 的 default-off memory 與受限本機操作資格保持原界線；D310-V02
installer 間歇異常仍為已接受的歷史 Deferred／根因 unknown，本次不宣稱修復。
若出現固定環境再現、CI failure 或與本 patch 有關的新證據，須重新阻擋。
本次不安裝、不部署、不啟用 hook／provider／memory，也不清理舊分支或工作樹。

## Verification And Release Gate

驗證使用 tracked `scripts/project-python`，Python 3.12.9／PyYAML 6.0.3。
此候選要求 agent profiles／routing／loopctl、Desktop native contract、CLI
public-help、release-state／version 及 generated parity 的相關驗證；離線
repository validation 不證明 GitHub 發布。
另須當前維護 diff 的獨立深入審查、必要 Security Diff Scan、完整 base-to-head
Merge Review、hosted CI、strict receipt／dedicated App 讀回，再檢查 tag／Release
衝突與精確目標。此候選紀錄不取代當次 gate，也不預寫尚未取得的 PASS。
候選準備時既有 ruleset 只涵蓋 main；維護 PR 合併前須取得對維護 base 適用
且生效的 ruleset，保留 strict CI／closing Issue／dedicated App、resolved threads
與無 bypass 等原要求。平台設定須精確預覽、個別授權及讀回；此候選不證明
保護已生效，也不豁免 repository 選定的 enforcement profile。

## Traceability

- Issue #330: <https://github.com/jeffery777/codex-dev-skills/issues/330>
- Main 相容性修正：PR #331，commit `74cae2a524844743d1a0340eb48ea08d7c0d6515`
- 維護 base：`codex/issue-330-maintenance-v033`，原始 commit `ad2e8a0772768b01d6e675a43b23047efc68ea39`
- 候選 branch：`codex/issue-330-release-v0331`
- [維護版證據與範圍](codex-runtime-maintenance-v0.33.1.md)
- [Release-state contract](../policies/release-state-contract.md)
- Compare: <https://github.com/jeffery777/codex-dev-skills/compare/v0.33.0...v0.33.1>
