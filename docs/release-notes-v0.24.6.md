# Release Notes: v0.24.6

Status: release candidate prepared through Issue #267.

這是 source/package 候選準備的點時紀錄；annotated tag 與非 draft、非 prerelease
GitHub Release 的讀回才證明發布。Commit、push、PR、merge、tag、Release
與 deploy 保留 separate human gates，依有效授權與前置執行。

## 一般技能政策載入

`docs-review` 與 `implementation-slice` 先讀技能與共用核心，再依正式 gate、
返工、委派、runtime／資料操作或工具編排情境讀完整細則。原七個章節全文
保留於可直接發現的 `reusable-workflow-details.md`；既有路徑與 headings
仍可解析。來源對照、六種驗收情境與安裝準備見 [政策載入說明](policy-loading.md)。

保留使用者優先序、授權、安全 fallback、證據新鮮度、獨立審查、完整最新
base-to-head Merge Review、provider 分離與原角色資格。簡單情境的宣告
必讀 bytes 相對原指名章節基準減少：docs review 13.6%、局部實作 39.9%。
這是靜態文字量；觸發更多細則時須另計，並非 live 行為、token、成本或耗時改善。

## 隨此版本收錄的既有維護

- Issue #263／PR #264：Desktop 26.911 的公開介面相容性點時證據與文件更新；
  沒有修改 adapter payload 或宣稱新增 live 遠端／session 驗收。
- Issue #265／PR #266：G1 儲存故障、恢復及量測證據契約的受控 fixtures 與
  測試加強；不新增持久資料啟用權、backend 行為或真實使用效益證明。

## Compatibility And Boundaries

發行價值：本次可安裝的共享指引改善一般入口的載入範圍，完整契約、入口
名稱、source/plugin/filesystem 引用與既有安裝群組保持相容，適合作為 patch。
版本三方同步 0.24.6；新細則隨 `shared-review-gates` 的既有相依部署，沒有
新 API、schema、migration、模型／effort 預設或角色資格降低。

使用者既有安裝不會自動更新。本次不部署全域指令、不變更使用者技能或模型
設定。歷史 release notes 不改寫；發行後 active guidance 仍保持正確。
共享指引的 live 配對行為、token、費用、延遲與跨模型品質均未驗證。

## Verification And Release Gate

候選須通過離線版本／catalog／installer／plugin parity、來源與觸發契約、
隔離安裝及完整測試 shards。獨立 release-sensitive review 與 Security Diff Scan、
完整 exact-head Merge Review、GitHub hosted CI、receipt readback、dedicated App
及合併 gate 通過後，才能依授權發布；實際結果以 PR 和平台證據為準。

```bash
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/test-shards.py run-all
./scripts/project-python -m unittest tests.test_policy_loading
./scripts/project-python scripts/validate-release-state.py
./scripts/project-python scripts/sync-plugin-package.py
git diff --check
```

## Traceability

Issue #267: <https://github.com/jeffery777/codex-dev-skills/issues/267>

原比較基準與必要義務對照見 [政策載入說明](policy-loading.md)。本紀錄不證明
合併、發布、使用者安裝或部署完成，也不替代各自的 exact-state 讀回。
