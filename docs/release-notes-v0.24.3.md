# Release Notes: v0.24.3

Status: release candidate prepared through Issue #257.

此點時紀錄描述 source/package 準備；發布真相另由 annotated tag 與正式
GitHub Release 的讀回確認。本文件不證明合併、發布、安裝或部署完成。
Commit、merge、tag、Release 與部署保留 separate human gates；依當時有效
使用者授權及各項前置證據執行，已有授權不因階段切換要求重複確認。

## Review Fallback 與返工續行

- #255 / PR #256 修正 production preflight 的 fallback tier 驗證：使用當次
  classifier 的 task tier，保留 profile identity、digest、sandbox 及 qualification
  檢查；standalone preflight 預設仍驗證 profile tier。
- 返工規範要求先分類失敗。合理修正後同一核心驗收仍失敗，或同工作包兩輪修正
  仍出現不同缺陷時，重評假設、完整流程、驗證缺口及必要模型／effort 能力。
  門檻不代表停止任務；環境或權限問題不以提高 effort 解決。
- 補齊 plugin 的 model-selection policy 封裝，以及 review、task brief 與共用
  契約入口。這是工作流程指引，沒有修改 harness 或實作自動模型切換。

## Runtime 與 Installer 相容性

- #239 / PR #241 補齊 thread capability discovery、deferred discovery 與
  Desktop／TUI 完整 namespace/schema 分流，加入原生 TUI create／fork 指引；
  不可觀察的能力保持 unknown，不能從另一 runtime 的成功推定可用。
- #240 / PR #243 讓 installer diff 保持唯讀，釐清 Linux UID namespace 診斷，
  並在 managed backup 路徑碰撞時拒絕覆寫。
- #249 / PR #250 更新點時 runtime 相容性證據及六個 Astra xhigh profile 配置。
  這是維護者的配置決策，並非新的成本／品質 benchmark qualification；保留
  原設定註解、role identity、class/tier 與候選 opt-in／digest 資格邊界。

## G1 內部驗證進展與限制

- #245 / PR #246 增加有界本機執行 ports，使用新建合成 Git／SQLite roots 驗證。
- #247 / PR #248 補齊 process-loss 後的 fresh readback；採用 proof-v2 與固定
  比較摘要。舊 G1 metadata／proof 家族不相容時拒絕開庫，不自動遷移。
- #253 / PR #254 增加 storage fault、容量與持鎖觀察；page quota SQLITE_FULL、
  注入 errno、物理 ENOSPC、SQLite FULL 與 CANTOPEN 證據保持分開。

這些是既有 default-off 管理核心的內部強化。Production registry 仍空，沒有
合格的真實資料管理 adapter；完整容量上界、4 GiB 最壞持鎖時間、power-loss、
production qualification 及 G2/G3 尚未完成，不宣稱完整 G1／MG1 或生產啟用。
歷史實驗不是本次重新執行的物理測試，也不構成跨環境資格。

## Compatibility And Boundaries

本次以相容性修正及內部強化準備 patch，沿用既有 M1 public API、權限、獨立
審查與 exact-head gates。G1 proof-v2 的不相容範圍僅限上述未合格的內部合成
roots；不得用新版本自動採納或改寫舊庫。版本判斷與完整來源見
[Issue #257 計畫](loops/issue-257/plan.md)。

Desktop 遠端 thread 能力缺席（#242）及 standalone fork 的 child-identity
EPERM（#251）仍是分開追蹤的未解問題，本版不宣稱修復。
沒有新代表性跨模型比較，不宣稱 token、速度、週額度或成本改善。
發行不會自動安裝到個別機器，也不啟用記憶 backend、dual-write 或 migration。

## Verification And Release Gate

發行範圍為 v0.24.2 至最終候選，而非僅版本準備 commit。發布前須完成完整
offline verification、適用 review／Security Diff Scan、PR exact-head review、
hosted CI、receipt 讀回及專用 App gate；再核對合併 commit 與 tag／Release 衝突。
實際結果記於 Issue #257／其 PR 證據，不以本候選紀錄預先宣稱通過。

```bash
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/test-shards.py run-all
./scripts/project-python scripts/validate-release-state.py
./scripts/project-python scripts/sync-plugin-package.py
git diff --check
```

## Traceability

Issue #257: <https://github.com/jeffery777/codex-dev-skills/issues/257>

來源 Issue / PR：#239 / #241、#240 / #243、#245 / #246、#247 / #248、
#249 / #250、#253 / #254、#255 / #256。
