# 整合接點審查參考表

只在受影響路徑涉及下列接點時載入，選用相關列。先沿呼叫者到 consumer
追查，再找能區分假設的最小安全證據；不要求每個 mock 改成真環境測試，
也不新增例行停止、核准 gate 或全套 CI 矩陣。review 保持唯讀。

| 接點 | 檢查問題 | 最小可用證據與限制 |
| --- | --- | --- |
| 外部命令與 mock | 除主要命令，是否還有 `--version`、能力探測、前置或清理呼叫？它們是否都落在預期 mock 邊界，或意外依賴主機 PATH、已安裝工具及版本？ | 對照完整 command call sites 與 fake 的實際 argv/回傳契約；用隔離 PATH 或受控 fake 驗證輔助分支。mock 完整不等於真實工具相容。 |
| 啟動與環境傳遞 | 真實帳號、login/non-login shell、工作目錄與有效環境，如何不同於測試？Runner 或 shell 初始化是否在 repo script 啟動前就失敗／改寫 proxy、PATH 等設定？ | 畫出 launcher → shell → script 的相關路徑；用非敏感 sentinel 或受控 shell fixture 檢查必要變數是否存在、來源與優先序。沒有真實 Runner 權限就標明未驗證，不輸出完整環境或秘密值。 |
| 輸入 loader → builder | 實際或具代表性的 input 是否走到同一 parser/builder？locator、schema、strict flags 與預設值是否一致？dry-run 是否跳過真正會拒絕的步驟？ | 用合成但形狀相符的正／反例穿過 loader 與 strict builder，斷言接受／拒絕原因。空值或過度簡化 fixture 通過，不能證明實際 input 可用。 |
| 產物 producer → consumer | producer 會輸出哪些檔案、型別、編碼、命名與部分產物？consumer 的每個受影響分支是否遵守該契約，fake 是否漏文字／二進位混合輸出？ | 優先廉價契約測試：以實際 producer 或形狀相符 fixture 餵 consumer，包含相關二進位、空／缺失產物及 strict 分支；檢查是否錯把所有內容當 UTF-8。只驗 producer exit 0 不足以驗 exporter。 |
| 失敗、部分成功與重試 | 前段成功、後段失敗時留下什麼？錯誤是新回歸或被前次失敗遮住？重試會覆寫、重複提交或沿用不完整產物嗎？ | 對受影響失敗點觀察殘留狀態與恢復前置。外部寫入結果未知先 readback，不盲重播；清理／重試仍須既有授權。診斷應指出階段、命令類型與安全錯誤類別，避免 secret、完整環境或原始敏感 input。 |

在既有 review report 記錄已查證問題、必要 suite／情境實際 run/skip/fail
與原因（或等價證據）、mock 邊界、真實／代表性環境及 input、未驗證範圍。
沿用專案的適用判準；不把所有 skip 當失敗，也不把必要情境未執行當 PASS。
找到第一個問題後繼續可獨立完成的檢查；缺少環境只限制相依結論。
只因新變更、失敗或未解疑慮增加檢查，不重跑仍適用的證據。
