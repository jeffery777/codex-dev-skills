# Issue #284：單專案 synthetic memory-audit 操作 pilot

Issue #284 建立與讀回後，從 main `1f85f6d9a5939dd665f3bab781c8f3535f083baf`
建立並推送 `codex/issue-284-memory-audit-pilot`，之後才實作。主代理唯一 writer，
獨立 reviewer 唯讀；交付至 PR readiness，merge／publication／實際安裝另有權限。

入口僅建立本次自己的 synthetic source／managed／authority fixture；不接任意 root、
import、JSON 或 resume。明確確認建立後，顯示目標／讀取範圍，做 advisory 預檢，
再取得綁此次目標的單次確認，沿用 provider → canary → audit。取消不核發 grant，
結束 close RAM 授權而不刪資料。Seed 重用 core 的 initialize／add／proof／readback，
完成後封閉 seed ports；不安裝 tests loader，不新增 production adapter。

驗收重點是異常處置：可控地注入實際 SQLite／來源讀取路徑，核對失效拒絕、內容
清空、連線與 lock 釋放、未知提交不重試，以及新 provider／新接受後恢復。
不要求真的耗盡磁碟／記憶體，不重啟 #273。測隔離安裝及新程序，不動實際使用者安裝。

必要 gate：focused tests／repo checks／package parity、獨立 code/deep/docs review、
正式 Security Diff Scan、precommit gate；PR 後完整 base-to-head exact-head review、
hosted CI、strict receipt/readback、dedicated App。計畫不是通過證據。

使用者另要求發行評估：核對 source/package、candidate、正式 annotated tag／Release、
active guidance 與 historical records，再依實際驗收提出是否發版與版本建議。
本包維持 source/package 0.24.7；評估本身不等於建立 tag／Release 或啟用正式記憶。
