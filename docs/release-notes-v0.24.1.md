# Release Notes: v0.24.1

Status: release candidate prepared through Issue #232.

此點時紀錄描述 source/package 準備。Merge、annotated tag、GitHub Release
與部署仍有 separate human gates，依具體使用者授權與當時證據執行；
發布及安裝後讀回另行證明實際交付。

## 契約相容的能力選用

- 一般規劃、實作、文件更新與審查可採用符合必要契約的原生、內建或本地
  執行方式；直接技能入口與共用編排遵守同一規則。
- 部分相容結果只重用有效證據並補足缺口，未知／不可用則回到既有安全流程。
  方法可選，但前置、權限、驗證、輸出及完成判定不減少。
- 將共用契約納入 plugin，保留 filesystem 安裝位置；增加直接入口與隔離
  安裝的資源可達性驗證。

## Compatibility And Boundaries

保留技能名稱、必要工具與指定方法、輸出格式、獨立審查、模型資格、formal gate
及完整 exact-head review。原生 PASS 或格式重排不構成 gate 證據。
不新增 runtime engine、資料 schema、記憶 backend、原生記憶切換或自動啟用。
不宣稱已驗證跨模型品質、token、延遲或成本改善。

## Verification And Release Gate

驗證範圍包含 source/plugin parity、預設與自訂 templates 安裝位置、相關
契約測試、repository 離線檢查與 test shards；實際結果及審查限制記於
`docs/loops/issue-232/verification-and-review.md`。發布前另核對精確合併版本、
annotated tag、GitHub Release 與部署範圍，候選文件不能代替 readback。

```bash
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/test-shards.py run-all
./scripts/project-python scripts/validate-release-state.py
./scripts/project-python scripts/sync-plugin-package.py
git diff --check
```

`catalog.yaml`、installer 與 plugin manifest 的 source/package 為 `0.24.1`。
這是既有技能選用歧義的 patch 修正；版本評估及發行準備留在同一 Issue，
既有 release notes 保持歷史紀錄。

## Traceability

Issue #232: <https://github.com/jeffery777/codex-dev-skills/issues/232>
