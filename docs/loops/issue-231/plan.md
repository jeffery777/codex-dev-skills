# Issue #231：範圍與交付計畫

2026-09-08 透過 GitHub connector 讀回 [Issue #231](https://github.com/jeffery777/codex-dev-skills/issues/231)：
狀態 open、無留言；設計與合成驗收範圍仍適用。已 fetch 遠端，從
`6ab5ee2982637c78e80d723e5b6310885d02f5e0` 建立並推送
`codex/issue-231-memory-scope-lifecycle` 後才開始修改。
基準已包含 G0 PR #230 與技能相容性 PR #233；不以歷史文件推定安裝狀態。

## 本次交付與完成條件

1. 補充 scope/backend 分離、明確保存目標、來源與可見性判斷。
2. 用純函式的獨立 synthetic schema 驗證有界儲存清單、查詢覆蓋、精確集合、
   preview/confirmation、版本漂移、防重播及逐目標結果。
3. 固定專案穩定身分、改名／離線／UI 移除與明確退場的區別；列示跨專案關聯。
4. 更新治理規格、原生共存與 roadmap；具體記錄尚待接受的 backend、quota、
   多儲存上限及觸發方案，不改 G0 生產預設或批次排除。
5. 完成正反測試、既有記憶回歸、離線 repository/package 檢查、code/docs/security
   review 與審查準備紀錄。PR 尚不存在時，不聲稱 exact-head merge readiness。

## 實作形狀與邊界

- `scripts/memory_scope_lifecycle.py`：只處理呼叫者提供的合成 metadata；沒有
  backend、檔案讀寫、網路、自然語言模型、CLI 命令或持久 replay store。
- `tests/test_memory_scope_lifecycle.py`：固定案例與對抗性變形；schema 成功
  仍保持 `operation_authorized`、`runtime_proven`、`write_performed` 為 false。
- `docs/memory-scope-lifecycle-design.md`：產品及未來 host/executor 的契約；
  不把測試用上限、hash 或聲明當生產授權。
- 新測試納入既有 test shard；不加入 installed skill/plugin allowlist。

沿用 `project-delivery`／`implementation-slice` 的必要流程；主代理為唯一寫入者，
獨立唯讀 reviewer 核對資料邊界與最後 diff。原生記憶仍由其官方管理介面擁有。
不讀真實私人資料、不建新 backend、不清除內容、不監控、不改設定、不發布或安裝。
初次交付只授權建立／推送起始分支。2026-09-08 後續授權允許修正後重新通過
正式 review 與 Security Diff Scan，無 findings 才 commit／push／建立 PR；
exact-head Merge Review 無 findings 且必要平台檢查通過後可直接合併。
不發布、不安裝的限制保持適用。

## 驗證策略

先用 `./scripts/project-python` 確認 pinned Python 與 PyYAML，再執行 focused
tests；檢查完整 shard inventory、既有記憶契約回歸及 repository offline validation。
各項結果與限制另記於 `verification-and-review.md`。這些證據只證明設計 oracle，
不證明自然語言判斷品質、真實跨儲存交易、原生清除或實體空間回收。
