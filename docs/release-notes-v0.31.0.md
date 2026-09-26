# Release Notes: v0.31.0

Status: release candidate prepared through Issue #304.

本檔記錄 source/package 候選準備；發布狀態須另核對 annotated tag 與正式
GitHub Release。候選、合併、tag／Release 與安裝保留 separate human gates，
已取得的明確授權可依原範圍續行，不以候選文件推定發布完成。

## Single-Project Memory Maintenance

新增可安裝的 shared `memory-maintenance` 薄入口，透過可信 host 整合既有
GovernanceCore 的 add／update／stop／resume／restore。每次要求綁定單一
本機 POSIX root、operation 與固定 Git artifacts；process-local authority
與 audit grant 分離，程序重啟後失效，不恢復 mutation handle。

Host 分別接受要求與核心 preview；等待不持有 DB 鎖，執行前重新驗證 scope、
來源、狀態、時效、撤銷與操作資格。Mutation 僅執行一次，再以 fresh reader
核對 proof、revision、projection 與保留版本。讀回不明或輸出失敗不重播，
不以例外推定未提交或已 rollback。一般 recall 只使用 current revision。

Advisory preflight 區分缺失的 host ports；canary 僅接受隔離 host。原有固定
synthetic pilots 保留作回歸，不由新入口自動開啟正式記憶。

## Compatibility And Boundaries

新增可安裝操作入口採 pre-1.0 minor `0.31.0`，catalog、installer 與 generated
plugin manifest/package 同步。一般 CLI／Desktop 尚缺合格的 production
source／confirmation／qualification ports，回報 unavailable；production
registry 保持空白，維持 default-off、manual。隔離驗收不代表完整 G1／MG1 資格。

沒有 schema migration、持久 authority store、跨程序 handle 恢復、任意
root／loader、G2、既有專案、原生或外部記憶啟用。既有記憶與 runtime state
不屬於安裝或舊版套件備份清理範圍。同一 OS 使用者可任意執行 Python 的情境
不在 process-local capability 的隔離保證內。

歷史 release notes 保留原貌；active guidance 不維護可變的目前發布版本指標。

## Verification And Release Gate

功能驗收依[本包計畫](plans/issue-304-memory-maintenance.md)，涵蓋五操作、
current-only recall、保留版本、scope／source／state 漂移、雙時鐘、撤銷、
重播、contention、程序重啟與受控交易／讀回／輸出故障。使用 synthetic Git
與 SQLite 實際路徑；沒有實體資源耗盡或 production ports 資格聲明。

發布驗收包含 pinned Python、完整功能 test shards、候選變更的相關回歸、
offline release-state／repo validation、generated parity、隔離安裝與升級、
獨立深入審查與 Security Diff Scan。PR head 變更後重新完成完整 base-to-head
exact-head Merge Review，另核對最新 hosted CI、receipt 讀回與專用 App gate。
既有測試證據僅在內容、範圍、政策及環境仍相符時重用。

正式 payload 為 annotated tag/title `v0.31.0`、本檔正文、draft=false、
prerelease=false；target 須於合併後核對。發布後讀回 tag object、dereferenced
commit 與 Release target；從 immutable 發布來源安裝，另驗
`install.sh diff --all`、來源 parity 及受保護檔案。舊版安裝備份清理須有
明確授權與精確預覽，且只在部署驗證成功、GitHub 復原來源已確認後執行。

## Traceability

- Issue #304: <https://github.com/jeffery777/codex-dev-skills/issues/304>
- Feature and release PR #305: <https://github.com/jeffery777/codex-dev-skills/pull/305>
- Branch: `codex/issue-304-memory-maintenance-entry`
- [Memory maintenance entry](../skills/loop-engineering/references/memory-maintenance-entry.md)
