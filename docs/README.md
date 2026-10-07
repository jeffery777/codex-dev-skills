# 文件分類

新增或更新文件時依內容分類，不能只因檔名含 Issue ID 就將執行紀錄當作工程文件。

| 內容 | 位置 | Git 追蹤 |
| --- | --- | --- |
| 需求、範圍、DoD、實作與驗證計畫 | `docs/plans/` | 是 |
| 操作指南、設定契約與使用限制 | `docs/guides/` | 是 |
| 可維護的架構、資料流與設計決策 | `docs/design/` | 是；有實際文件才建立目錄 |
| 測試輸出、PoC 觀察、review/gate 收據與執行環境快照 | `.work/verification/<issue>/` 或 `.work/review/<issue>/` | 否 |

可重跑的測試、fixture、驗證工具與程序應受版本控制；它們產生的驗收證據
由 `.gitignore` 的 `.work/` 規則排除。既有根目錄工程文件、release notes
及歷史紀錄仍按既有用途維護；本次不遷移其他 Issue 的歷史資料。

Code review 與 merge review 必須能取得並檢查適用證據，包含來源版本／完整
diff 身分、執行範圍、命令、退出碼、失敗、略過項目、限制與 finding 處置。
Git 忽略不是免審；換 checkout 或 reviewer 時須重新產生，或提供有版本與
digest 綁定的 CI/job artifacts。跨主機保存使用核可的 artifact 機制與存取權限，
不能將機密、private runtime 狀態或本機快照放入共享 Git。

同一來源、環境與輸入下，確定性測試應重現同一判定；時間、耗時、暫存路徑
等執行欄位可能不同。模型 PoC、外部服務狀態、安全分析及人工 review 也不
保證逐字相同。重跑產生新證據，不能重建或覆寫先前那次執行的歷史事實。
