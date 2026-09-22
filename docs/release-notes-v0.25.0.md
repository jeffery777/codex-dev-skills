# Release Notes: v0.25.0

Status: release candidate prepared through Issue #286.

這是 source/package 候選準備的點時紀錄；annotated tag 與非 draft、非 prerelease
GitHub Release 的讀回才證明發布。Commit、push、PR、merge、tag、Release
與 deploy 保留 separate human gates，依各自有效授權及適用 gate 執行。

## Memory Audit 與異常處置

- #272 完成 G1 儲存異常處置驗收，重點是失敗後拒絕、資料保留與重新確認恢復；
  不要求實體 SQLITE_FULL／ENOSPC 一定發生，亦不將注入證據當成實體資格。
- #275／#277 提供有界唯讀盤點與單專案 adapter，依 source provenance、資格、
  期限及最終 disclosure 檢查決定是否揭露摘要；失效不保留可揭露內容。
- #279／#281 串接單次要求、dispatch 與獨立 authority lifecycle store；授權仍綁
  provider RAM／session／PID，持久 row 不會自動恢復 grant，未知提交不自動重試。
- #283 補 metadata advisory 預檢與隔離 canary；未觀察的狀態保留 unknown，
  不能將預檢視為內容讀取權限或 production qualification。
- #285 新增固定 synthetic 操作 pilot：先確認建立新 fixture，再確認本次精確
  target，等待後重驗才接受 audit；取消不核發要求，結束 close 授權並保留資料。
  修正持續 stdout 故障的重複輸出，另驗實際 broken pipe 的收束行為。

操作與限制見 [synthetic pilot](../skills/loop-engineering/references/memory-audit-pilot.md)。

## Compatibility And Boundaries

這批新增能力適合作為 pre-1.0 minor 候選版。catalog、installer 與 plugin manifest
同步 0.25.0。本候選準備切片只更新版本與文件；累積 v0.24.7 → 0.25.0 已在
既有 `codex-delivery-workflow` 群組納入 `memory-audit`，升級會新增該技能。
群組名稱、installer 控制流程與既有 M1 public API 保持不變，沒有資料 migration。
既有安裝不會自動更新；更新需遵循 installer 的 diff、拒絕覆寫及備份契約。

預設停用、production registry 仍空。Pilot 只建立自己的固定 synthetic source／
managed／authority，不接受既有 root、任意 JSON、import 或 resume；不讀原生記憶。
fixture 與 authority bookkeeping 會寫入，內層 managed audit 唯讀不是整體零寫入。
沒有真實專案啟用、G2 清除、跨程序強制撤銷、硬 RSS／deadline 或 OS kill cleanup
保證；同 OS 使用者的任意程式不在隔離保證內。stdout 與 null-sink open／dup2
同時失敗的 shutdown 行為未驗證，不能延伸一般輸出故障測試的保證。

沿用 CLI／Desktop／plugin 的既有安裝邊界，不主張新增平台資格或部署完成。
歷史 release notes 不改寫，publication truth 必須於正式發行 gate 另行查核。

## Verification And Release Gate

候選驗證需涵蓋隔離 HOME 的 fresh install、v0.24.7 → 候選版 update、差異拒絕
時資料／receipt 不變，以及明確 force update 的備份與版本讀回。沿用既有 installer
異常測試檢查不安全目標、備份衝突及 receipt 失敗，不以物理耗盡作為驗收前提。
實際命令與結果保留於 Issue #286 的驗收紀錄及 PR，候選文字不代替執行證據。

```bash
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/validate-release-state.py
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python -m unittest tests.test_plugin_packaging tests.test_release_state_contract
git diff --check
```

獨立 review、必要 Security Diff Scan、PR 後完整 exact-head Merge Review、hosted CI、
strict receipt／dedicated App 仍須完成。合併候選不授權 annotated tag／Release、
使用者實際安裝或真實記憶啟用。

## Traceability

Issue #286: <https://github.com/jeffery777/codex-dev-skills/issues/286>

此紀錄不宣稱候選已合併、已發布或完成 production qualification。
