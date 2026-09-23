# 獨立合成 reviewer 盲審

這些 fixtures 完全自行構造，沒有外部專案程式或資料。僅手動執行，需當次模型
用量授權；一般 validation 不啟動模型。兩個 variants 各包含兩個功能缺陷、維護性
呈現邏輯、正確 retention 與合法 YAML controls。此作者說明及 `oracle.py` 不送給
受試模型。通用 task 與 developer prompt 固定於 `run.py`，不揭露缺陷數量或答案。

以 `./scripts/project-python` 執行。先將 `CODEX_REVIEW_PILOT_ROOT` 設為全新 repo
外目錄，`build.py --repo <repo-root>` 產生固定 fixtures 與 SHA manifest；
`oracle.py` 以真實 PyYAML／受控 subprocess 驗證，不靠 mock ValueError。
`run.py v1 sol-medium` 執行單一 arm；variants 為 v1/v2，arms 為 sol-medium、
sol-high、astra-xhigh。每 run 最多 600 秒且不覆寫已存在目錄。每個 arm 使用
fresh explicit CLI model/effort、read-only sandbox、同份 source review guidance；
這是模型比較，不是把某個固定 custom profile 的 model/effort 默默改掉。

評分分開列真 bug 發現／漏報、controls 誤報、maintenance 建議、retention 契約、
證據與 ownership。父 oracle 通過不代表 reviewer 曾實跑該命令；回答中的每項
執行與失敗原因還要對 raw events 查核。不依 finding 數量排名，不推論其他環境
或原生 Desktop qualification。raw events 保留本機，公開結果只記 hashes/usage
與可核對判讀。只有兩個小型 case、沒有多次抽樣，不能證明普遍優勢或帳單節省。

Fixture authoring 期間曾修正 PID oracle、文件 operation 名稱與 scope；正式六個
model runs 只使用 `blind-review-final` 凍結版本，不把 authoring failures算模型結果。
