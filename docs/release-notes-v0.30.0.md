# Release Notes: v0.30.0

Status: release candidate prepared through Issue #301.

本檔記錄 source/package 候選準備；發布狀態須另核對 annotated tag 與正式
GitHub Release。候選、合併、tag／Release 與安裝保留 separate human gates，
已取得的明確授權可依原範圍續行，不以候選文件推定發布完成。

## Desktop Sidebar Preferences

既有 `desktop-sidebar-organization` 薄入口新增公開
`update_sidebar_preferences` 的按需操作契約。排序偏好共用於 Codex／Work；
`sorting.projects` 表示專案內任務排序。分組則限定已確認且可觀察的 surface。

只送指定且需要改變的欄位，省略欄位保持不變；已符合則 no-op。排序偏好
與項目 reorder 分開，不自動互相補送。回應與 fresh readback 分別驗證；
目標 surface 不可觀察、讀回不符或未指定欄位漂移時保留 unverified，
不盲目重送、不補償性還原。

## Compatibility And Boundaries

新增可安裝 Desktop 操作能力採 pre-1.0 minor `0.30.0`，catalog、installer
與 plugin manifest/package 同步。CLI／Desktop 保留獨立入口；共享編排的
ownership、驗證、review 與完成判定不變。沒有 CLI executor、thread adapter、
記憶核心、production registry 或全域設定變更。

本次 runtime 比對沒有發現需修改核心接口的破壞性差異。公開 callable 仍是
點時證據；未實測 live start／resume／fork、sidebar mutation、所有 surface
可觀察性、UI 重新呈現或 remote caller。Synthetic 範例與文件測試不能證明
上述 live 行為，也不是 runtime 攔截器。

歷史 release notes 保留原貌；active guidance 不維護可變的目前發布版本指標。
安裝使用已核對的 immutable 發布來源、既有 installer 與 managed backups，
不包含記憶初始化、啟用、清理或私人 runtime state 操作。

## Verification And Release Gate

功能驗證範圍與限制見 [2026-09-25 runtime 證據](codex-runtime-compatibility-evidence-2026-09-25.md)。
發布驗收包含 pinned Python、完整本機 test shards、offline release-state／repo
validation、generated package parity、隔離安裝與更新、完整 exact-head 深入
審查，以及最新 hosted CI、receipt 讀回與專用 App gate。通過結果依當次
驗收與平台證據判定，不從本候選記錄推定。

正式 payload 為 annotated tag/title `v0.30.0`、本檔正文、draft=false、
prerelease=false；target 須於合併後核對。發布後讀回 tag object、dereferenced
commit 與 Release target；本機安裝另驗 `install.sh diff --all`、來源 parity
及受保護檔案。任何尚未通過的必要條件都不能宣稱完成。

## Traceability

- Issue #301: <https://github.com/jeffery777/codex-dev-skills/issues/301>
- Feature PR #302: <https://github.com/jeffery777/codex-dev-skills/pull/302>
- Branch: `codex/issue-301-release-v0300`
- [Sidebar preferences reference](../skills/desktop-sidebar-organization/references/preferences.md)
