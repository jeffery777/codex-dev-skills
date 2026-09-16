# Issue #257：v0.24.3 補發行

## 目標與基準

維護者於 2026-09-16 明確要求補發行版本。本工作包完成必要版本準備、驗證、
review、PR／合併，以及 annotated tag／正式 GitHub Release 發布。
先建立並讀回 [Issue #257](https://github.com/jeffery777/codex-dev-skills/issues/257)，
再建立、推送與讀回 `codex/issue-257-v0-24-3-release`，之後才修改 tracked files。
採用獨立 checkout，避免切換其他工作中的分支；本工作包只有一位 writer。

- 起始 main：`0689f6e15117b0edf7317c17b5367124768bb8cc`。
- 前一版 v0.24.2 commit：`89fe71d5f7f3772beac852550ea3aa0b06d5f8a7`。
- 完整候選範圍包含 #239、#240、#245、#247、#249、#253、#255 及本次版本準備。

## 版本分類與最小修改

本次採用 patch v0.24.3，理由為修復既有 runtime discovery、installer、fallback
與返工續行行為。G1 新 ports／proof-v2 是既有 default-off 核心的內部增量，
production registry 仍空、沒有新合格真實資料 adapter，不能以此宣稱完整 MG1。
G1 proof 家族不相容時拒絕既有 synthetic root；不自動遷移、不修改 M1 public API。
沿用 v0.24.2 對合成／內部核心與相容 workflow 修正的分類方式，不依 diff 大小升 minor。

同步 catalog、installer 與 plugin manifest 的三處版本，新增本計畫及
[release notes](../../release-notes-v0.24.3.md)。不變更 production 邏輯、harness、
模型／effort、全域規範、qualification store 或歷史 release notes。
不包括機器安裝／部署、公司環境操作或任何 backend 啟用。

## 驗證、審查與發布順序

1. 使用 tracked `scripts/project-python` 核對 Python 3.12.9 與 PyYAML，執行
   offline repository checks、全部 test shards、release-state、package parity 及 diff hygiene。
2. 對本次 diff 執行正式 review 與 Security Diff Scan；另檢查完整未發行範圍的
   來源、既有審查適用性、版本／文件一致性與已知限制。歷史測試不冒充本輪實測。
3. PR 後完成完整 base-to-head merge-review-deep、hosted CI、strict receipt
   發布／讀回、專用 App 驗證與最終平台讀回，使用 expected head 合併。
4. 核對合併 commit、三處版本、精確 tag／Release payload 與衝突後，建立 annotated
   tag；讀回 tag object 與 commit 後才發布非 draft、非 prerelease GitHub Release，
   再讀回發布身分。發行說明保持點時候選紀錄，不另改歷史文件來追認發布。

## 風險與恢復

版本檔案不一致、漏列累積變更或將未合格能力宣稱可用，均阻擋發行。
安全／功能審查必須保留實際 coverage 與證據限制；不能由測試成功推定無缺陷。
若發現 blockers，先修正並重驗受影響證據；變更 PR head 必須重新完整 exact-head review。

發布前可修正本 Issue 分支；發布後保持 tag 不移動、不 force push、不改寫舊版。
需要修復時另開 Issue／版本向前修正；刪除 Release／tag 是另需明確授權的恢復方式。
若必要平台或驗證能力缺失，報告具體未完成條件，不能繞過 gate 或把候選稱為已發布。
