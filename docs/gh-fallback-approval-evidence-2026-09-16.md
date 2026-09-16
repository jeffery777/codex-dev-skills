# GitHub fallback 授權稽核 — 2026-09-16

追蹤：[Issue #261](https://github.com/jeffery777/codex-dev-skills/issues/261)。
本紀錄只保存去識別的命令形狀、公開診斷結果與限制，不收錄私人 task transcript、
規則內容、session id 或機器狀態。

## 觀測與診斷

使用者提供的任務經原生 `read_thread` 讀回後，可見多筆 `gh api ... > ...json`
命令；其中既有唯讀查詢，也有 `--method POST --input ...` 的寫入。部分最初
嘗試回報 network error，之後相同命令成功。這證明執行紀錄，不能還原每次
approval UI 的內容、使用者選項或當時所有有效規則。

本次唯讀檢查目前保存的相關規則，找到 9 條以完整 `/bin/zsh -lc` 命令保存、
含重導向的 allow 規則。使用 standalone CLI 0.154.0 的公開
`codex execpolicy check --rules <rule-file> -- <argv...>` 進行靜態診斷：

| 輸入形狀 | 本次結果 |
| --- | --- |
| 一條目前保存的完整 shell 命令 | `decision: allow`，1 個 matched rule |
| 同一條命令只更改重導向目的檔名 | 0 個 matched rules，沒有 decision |
| `gh api <read-endpoint>` 的直接 argv | `decision: allow`，1 個 matched rule |
| 改用 absolute executable path 的直接 argv | 0 個 matched rules，沒有 decision |

以上皆為 rule checker，不會執行 API。既存的直接 `gh api` 規則不是本次新增，
也不是建議採用的權限範圍。未匹配不等於 deny，也不等於獲准執行；改寫 argv
的診斷不授權換用 executable 來避開管制。保存規則的時間與目前 session 是否
載入它們，不能僅從檔案內容證明。

[官方 Rules 文件](https://learn.chatgpt.com/docs/agent-configuration/rules)
說明 argv prefix matching；對含 redirection、substitution 等複雜語法的 shell
採保守處理，以完整 shell invocation 判定，而非單純內部 command prefix。
因此 endpoint 或目的路徑變更可能不再匹配完整 shell 規則。

## 結論與限制

命令形狀及精確比對是有證據支持的成因之一，足以補上預防與診斷指引；無法
把歷史每一次提示全部歸因於它。直接 argv 診斷沒有重現 shell preprocessing、
Desktop approval reviewer、managed policy、network sandbox 或其他有效規則。
沒有證據顯示全域 AGENTS 要求逐次提示，也不能承諾簡化命令後必定免提示。

採用同一份 [GitHub control-plane policy](../policies/github-control-plane-policy.md)：
connector-first、正當 fallback、API 與本地保存分開、反覆提示先查實際 argv／
相關規則與 runtime，再依必要授權執行。不擴大前綴、不改規則或全域配置。
完整結果才可保存為 evidence；不可重建截斷 JSON 或重送 mutation 只為取得輸出。
