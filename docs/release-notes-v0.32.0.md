# Release Notes: v0.32.0

Status: release candidate prepared through Issue #308.

本檔是 source/package 候選準備，不代表發布。Publication 以 annotated tag 與
非 draft／非 prerelease 的 GitHub Release 讀回為準；各階段保留 separate human gates。

## GPT-6.1 Everyday Configuration

balanced_worker、advanced_worker 改為 GPT-6.1 Sol-medium，senior_worker、
routine_reviewer 改為 GPT-6.1 Sol-high。Canonical registry、profile digests 與
生成套件同步。八個其他 profiles、class/tier、sandbox 與 candidate 資格不變。

日常主代理 example 改 6.1 Sol-medium，Plan mode 建議 high，速度建議 Standard。
官方成本分析區分 6 Sol 與 5.6 Sol 基準、cached input、內含量與額外點數；
本次依維護者選擇採用，不做模型配對或節省率量測，不宣稱品質／成本實測優勢。
部署後先觀察真實任務選路與完成，再逐類比較較低 effort。

Security Diff Scan 改依最終 diff 的安全影響判定；不適用時記錄範圍與理由，
不當成掃描通過。涉及安全邊界或具體疑慮仍須適度掃描；完整 exact-head review 保留。

## Compatibility And Boundaries

採 minor `0.32.0`，因固定角色模型需求與日常主代理建議改變；不改公開 route
schema 或 classifier，無需重寫歷史 receipts。舊 loaded bytes 不滿足新 profile
identity；目的 runtime 不支援 6.1 時依既有 preflight/fallback，不能靜默改名。
Candidate qualification、首次高風險審查、exact-head gate 與 memory default-off
保持。安裝器不修改個人主代理／Plan／speed 設定；既有對話不保證自動重新載入。

## Verification And Release Gate

必要檢查為 profile/registry、stale bytes 拒絕、routing、隔離安裝、package parity、
offline release-state/repository validation 與獨立審查。實際執行結果見
[驗證紀錄](loops/issue-308/verification.md)，未跑項目不視為 PASS。
CLI/Desktop 真實模型行為、訂閱扣量與部署後成效尚未量測。

合併、annotated tag、Release 與個人部署須有各自授權及適用 gate。PR 建立後
仍需完整 base-to-head exact-head review、hosted CI、strict receipt/App/ruleset
讀回；本次候選文件不能替代。未發布、未部署時不得聲稱運行觀察已開始。

## Traceability

- Issue #308: <https://github.com/jeffery777/codex-dev-skills/issues/308>
- Branch: `codex/issue-308-model-cost-routing`
- [配置、官方成本及觀察計畫](gpt61-adoption-and-observation.md)
- Compare: <https://github.com/jeffery777/codex-dev-skills/compare/v0.31.1...v0.32.0>
