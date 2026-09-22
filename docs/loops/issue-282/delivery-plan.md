# Issue #282：啟用前預檢與隔離 canary

GitHub Issue #282 已建立及讀回，再切換既有且已 push 的
`codex/issue-282-memory-audit-preflight-canary`；基準為
`c1f02fd1ca1831142b5248f19872f8ef37eea0d8`。主代理是唯一 writer，
獨立 reviewer 唯讀。交付至 PR readiness，merge 另待授權；source/package
維持 0.24.7，不改發行歷史、不發版、不安裝、不啟用真實資料。

本包新增 host-only advisory 預檢及隔離 canary，沿用既有單專案 authority。
預檢不建立／消耗 grant、不初始化／修復 store，不讀正文／lifecycle。
Metadata 許可綁完整目標、時效與撤銷；authority filesystem 資格獨立接受。
Canary 不從預檢取得權限，仍需 host 新接受，執行及最後揭露重新核對。
介面與限制見 [reference](../../../skills/loop-engineering/references/memory-audit-preflight.md)。

驗收以安全失敗及恢復為主：off 零接觸、預檢不消耗、過期／撤銷／重播／scope／
identity／fingerprint／環境漂移拒絕、失效報告清空；適用 SQLite／OS 故障在真正
交易／cleanup／report 路徑受控注入，驗 connection／lock 釋放及新接受恢復。
不需要真實專案或物理耗盡，不重啟 #273，production registry 保持空。

流程為 focused tests → required repo checks/package parity → 獨立 deep/code/docs
review 與正式 Security Diff Scan → precommit gate → commit/push/PR → 完整
base-to-head exact-head review、hosted CI、strict receipt/readback、dedicated App。
各 gate 的实际結果由驗收紀錄及 PR 證據保存，計畫本身不代表通過。
