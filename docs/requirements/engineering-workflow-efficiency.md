# 工程流程效率需求

來源：[Issue #316](https://github.com/jeffery777/codex-dev-skills/issues/316)。
效率是工程流程產品品質與 DoD；保留選定範圍的模型切換、writer 隔離、
秘密排除、獨立審查及驗收目標。本切片不授予 runtime／production 資格。

## 最小可交付範圍與 DoD

- 共用 [工程契約](../../policies/engineering-workflow-contract.md#workflow-efficiency)、
  delivery／implementation／orchestrator 技能、plan／report 模板及 plugin 副本一致。
  Codex filesystem 與 Hermes 安裝資源使用同一契約及 fixture verifier。
- 前移廉價契約、環境與 consumer smoke；本 repo 提供 `--workflow-smoke`，
  部署後提供 fixture `preflight`，失敗在執行 fixture code 前拒絕。
- 第一輪完整工程包、後續受影響邊界、有效 primitive 重用、兩輪不收斂改診斷；
  NIT／SHOULD-FIX 批次處置，blocker 不延後。保留內容、範圍、假設、階段、
  政策、環境與未提交修改的證據綁定。
- 未 ready draft 可標示 `REVIEW_REQUIRED`；readiness／merge／release 前必做
  最新完整 base-to-head Merge Review。正式 verdict schema、CI、App、ruleset
  與 provider gate 維持原契約，不能把 draft 當成 READY。
- 文件測試驗證連結、schema、狀態一致性、必要安全行為及安裝／package parity；
  不綁歷史敘述原句、finding 列數或偏好措辭。
- 完成獨立公開契約審查、適用安全檢查、局部測試及實際 consumer readback。
  證據保留於 Git 忽略位置；重跑能重建相同行為判定，UUID、時間與 PID 不必相同。

## 代表性驗收

| 風險／案例 | 固定檢查 | 完成邊界 |
| --- | --- | --- |
| 低：有界文件修正 | 契約連結、狀態一致性；routine reviewer 選取 | 成本符合小任務，正式 gate 仍適用 |
| 中：有界功能與 consumer | fixture preflight／固定 port tests；有效／stale receipt、父代理整合驗證；兩輪 context 評估 | 可重用有效協調證據；漂移拒收，無自動 rollover 授權 |
| 高：credential／writer／公開契約 | 高 cost 偏好仍選 deep/security review；protected drift 在 spawn 前拒絕；draft 正式 gate 仍拒絕 | 成本不能弱化隔離、秘密排除、獨立性或最新 head |

本 repo 以 `./scripts/validate-repo.sh --workflow-smoke` 快速重建代表性行為，
再依變更跑局部測試／必要 gate。此 smoke 不是完整 repository validation。
其他專案安裝後以共用模板選自身的 spec、consumer、CLI／Docker schema 與
固定驗收；使用 `verify-engineering-workflow.py preflight` 的合成契約案例只是
共用入口驗證，不推定該專案能力或完整自動切換合格。

## 量測與剩餘依賴

使用同一組代表性測試的簡單計時及工程包審查輪次；查讀次數、全流程成本、
模型品質及不可比較的改善幅度保留 `unknown`。不新增治理框架或聲稱節省百分比。
Issue #316 的有限 A/B 基礎已由 PR #322 交付；所選入口的官方訂閱或 LiteLLM
原生接入、context／品質與跨目的地實際驗收改由
[Issue #323](https://github.com/jeffery777/codex-dev-skills/issues/323) 追蹤。
本期 C 另依賴所選執行器情境的可信觀測、撤權、
writer 控制與唯一採認。舊 N1–N4 全矩陣及任意失聯恢復不作共同前置；
局部成功不能取代各自適用的依賴。
相依按所選本地 runtime／scope 判定；上游人工或 dots 派工不增加直接 dots
工具入口資格或額外矩陣。實際執行環境／權限／授權／工具差異才補整合證據。
