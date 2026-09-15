# Issue #255：日常 review fallback 與返工續行

## 目標與授權

依使用者核准的成本效益審查，修正已重現的安全 fallback 錯配，並補齊
返工分類、能力重評與持續交付規範。Issue #255 建立、讀回後，建立並推送
`codex/issue-255-review-fallback-rework`，才開始實作。來源為
`1afd13884431b225d7c2c1731ed7fc6e79c76840`。

## 修改包

1. Production preflight 使用 classifier 的 task tier 驗證 fallback；profile
   identity、digest、sandbox、qualification 保持原義，standalone 預設仍驗 profile tier。
2. 補 parent／sequential、未知／不可用 surface、安裝缺失，以及 class／tier／
   collision 拒絕的 production regression。
3. 共用契約只加按需入口；詳細返工規則放既有 model-selection policy，並封裝
   該政策供 plugin 使用。對齊 usage-model、review workflow 與 task brief。
4. 新增[語意案例](prompt-cases.md)，以獨立審查及有界模型回應檢查歧義；
   更新既有 ME-01～03 測量接續條件。

## 邊界與風險

不變更 harness、個人設定、全域規範 repository、實際公司 pipeline、模型
baseline／qualification 或 release version。模型比較尚未達正式資格時，
不得以靜態測試或可呼叫狀態取代品質證據。

主要風險是 fallback 意外放寬高風險 tier、profile 信任邊界與返工規範造成
非必要停止。以 production 負面測試、獨立 deep review 與 Security Diff Scan
驗證。安全角色及 exact-head gates 不因成本優化降低要求。

## 驗證與完成條件

- 使用 tracked `./scripts/project-python`；跑受影響 routing／profile／CLI tests。
- 跑 `./scripts/validate-repo.sh`，確認 source／package parity 與必要 evals。
- 新舊 prompt 比較固定 source、runtime、model／effort；結果僅作有界行為
  觀察，正式模型資格另依 ME-01～03。
- 修正獨立審查 findings 並按影響範圍重驗；有 PR 時另完成 exact-head gate。
- 報告 source 修改、驗證、未驗證條件及模型採用限制；不宣稱未量測的節省。
