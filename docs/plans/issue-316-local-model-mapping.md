# Issue #316 本機角色模型映射工程計畫

## 需求與範圍

提供 default-off、provider-neutral 的本機角色模型映射。只有受保護的使用者
配置可以替換模型與 effort；保留 canonical class/tier、指令、sandbox、scope、
獨立 review、操作授權與完成契約。配置不進共享 Git 或套件。

CLI 與 Desktop 分別依公開 runtime 介面驗證；不依賴 private API，不從傳輸
成功推定正式角色資格。操作與 schema 見[指南](../guides/local-model-mapping.md)。

## 設計與實作順序

1. 核對公開 runtime/schema，使用有界合成資料驗證主／子代理工具循環。
2. 載入 protected default-off store，只允許 model/effort 兩欄替換。
3. 綁定當前 provider、runtime、model/effort、canonical/effective profile、scope、
   quality/context evidence 與逐模型 catalog；缺件或漂移停止。
4. 在 route/receipt/integration 重新驗證資格與新鮮度，禁止靜默 fallback。
5. Installer 保留 user-owned target，同步文件、測試及 generated package。

## Context 與驗收條件

- 未啟用時保留 baseline；啟用不能降低 class/tier、擴權或切換資料目的地。
- 無效、不可用、撤銷、漂移、scope/runtime 不符皆停止，不自動換 provider/model。
- 更新不得覆寫 user mapping；consumer 拒絕損壞 receipt 時保留既有回報契約。
- 逐模型核對實際部署的 input/output/合計限制、推理計算與超限行為。
- 完整輸入加輸出／推理預留與安全餘裕不得超過實際容量，提前壓縮。
- 容量未知時不採用；設定合理性檢查不能取代逐 request enforcement。
- 真實 catalog 載入、長上下文、壓縮後工具續答與角色品質須另外取得證據。
- 不把 standalone CLI 的驗證當成 Desktop 保證；不把合成資格當 production 資格。

## 證據位置與重建

需求、設計、測試與以下程序受 Git 追蹤。執行輸出與 review/gate 收據存放
`.work/verification/issue-316/`，已由 `.gitignore` 排除。歷次輸出使用不同 run
目錄，保留失敗及過期結果。它們不是套件內容，也不能提交為公開文件。

在 repository root 使用以下程序；不連線公司 gateway，不修改 provider 配置。
全部 Python 驗證使用 pinned resolver。先核對 working tree，確保新的受審檔案
已納入 Git diff；未追蹤來源須另列路徑與內容 digest，不能只記 HEAD。

```sh
mkdir -p .work/verification/issue-316
evidence_dir=$(mktemp -d .work/verification/issue-316/run-XXXXXX)
git rev-parse HEAD > "$evidence_dir/head.txt"
git diff --binary HEAD > "$evidence_dir/working-tree.patch"
git status --short > "$evidence_dir/status.txt"
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(sys.version); print(yaml.__version__)' > "$evidence_dir/environment.txt" 2>&1
printf '%s\n' "$?" > "$evidence_dir/environment.exit"
./scripts/project-python -m unittest tests.test_loopctl tests.test_local_model_mapping tests.test_agent_routing -q > "$evidence_dir/tests.log" 2>&1
printf '%s\n' "$?" > "$evidence_dir/tests.exit"
./scripts/validate-repo.sh --skip-unit-tests > "$evidence_dir/structure.log" 2>&1
printf '%s\n' "$?" > "$evidence_dir/structure.exit"
./scripts/project-python scripts/sync-plugin-package.py > "$evidence_dir/package.log" 2>&1
printf '%s\n' "$?" > "$evidence_dir/package.exit"
git diff --check > "$evidence_dir/diff-check.log" 2>&1
printf '%s\n' "$?" > "$evidence_dir/diff-check.exit"
git diff --binary HEAD > "$evidence_dir/working-tree-after.patch"
cmp "$evidence_dir/working-tree.patch" "$evidence_dir/working-tree-after.patch"
printf '%s\n' "$?" > "$evidence_dir/source-stability.exit"
```

必要時另在新 run 目錄執行全量：

```sh
./scripts/project-python -m unittest discover -s tests -q > "$evidence_dir/full-tests.log" 2>&1
printf '%s\n' "$?" > "$evidence_dir/full-tests.exit"
```

核對所有退出碼與 log；有缺件、失敗、略過或來源漂移不能直接判 PASS。
`--skip-unit-tests` 只驗證結構，不能稱全量測試通過。比例重驗須在 review
收據說明修正範圍、未重跑項目及重用證據的理由；保留原失敗結果。

以上可重建離線驗證的內容與判定，時間／耗時等欄位不保證相同。Runtime
PoC、模型品質、容量與 Security Diff Scan／人工 review 必須另外按當前環境
重新執行；不能由單元測試產生先前的 scan ID、finding 處置或 live 觀察。

## Review 與交付邊界

Code review 檢查實作、驗收條件、適用證據與 finding 處置；merge review
重新核對當前完整 base-to-head、來源／diff digest、證據範圍、新鮮度與剩餘缺口。
Reviewer 不能只看 PASS 摘要；本機證據不在其 checkout 時須重跑，或使用核可
artifact 交換機制。Security 原生 scan 收據留在工具管理位置，以 ID／digest
定位，不搬入追蹤文件，也不宣稱測試可以重建安全分析結論。

本項為 additive pre-1.0 minor candidate；source/package 版本依 catalog，
候選紀錄與 publication truth 分離。Commit/content push／PR、exact-head、
merge、tag/Release、安裝與清理各自核對授權與 gate。既有 memory production、
M2／V3-C gates 維持不變。
