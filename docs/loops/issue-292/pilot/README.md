# Issue #292 bounded CLI pilot

六個 role packets 的 fixture、通用 task 與父驗收 oracle。這是需手動啟動的點時
合成評測，不是 unit-test、模型排名或 production qualification。`results.json`
保存 request、hashes、raw usage 與獨立判讀；raw events/finals 僅保留本機，不把
runtime logs、個人路徑、已安裝技能 metadata 放進公開 repository。

使用 repository 的 `./scripts/project-python`，先將 `CODEX_PILOT_ROOT` 設成新的
repo 外暫存路徑，再執行 `build.py`。它生成 `fixtures` 與 `packets.json`。
經當次模型用量授權後，執行 `run.py R`（或 E/W/S/A/V）；E/S 可另用
`run.py E lower`／`run.py S lower`。每次新 process 的 timeout 為 600 秒，之後有
15 秒 SIGTERM grace，仍未停止才對自己的 process group 發 SIGKILL；timeout 仍會
寫出結果 artifact 並以非零結束。既有 run 目錄禁止覆寫。`grade.py R-default ...`
只執行固定 oracle，**不能**代替獨立
semantic review 或把父代理後跑的命令算成模型已跑。

公開 harness 僅將原當次工具的 repo/temp/CLI 路徑改為可移植設定；fixture、task、
oracle 的內容保持一致。此處 model/effort 是 requested config；JSONL 沒有獨立
resolved-model attestation。`--ignore-user-config` 仍可能載入 global instructions
及 installed skill metadata，不能稱為整個 instruction stack 完全隔離。
模型 runs 不可讀 sibling oracle 是 task boundary，不是 OS 讀取隔離保證。

所有不利結果與原判讀均保留：E-lower 有已記錄失敗卻回報無失敗的矛盾。
V-default／V-review-guidance 的 heredoc 原先判 evidence-quality FAIL，後因最小
事件診斷亦重現相同公開紀錄缺口，修正為 provenance unknown；缺 event 不能
單獨證明模型虛構。V-review-high 的實際執行與 controls 有完整可見證據。
歷史 `V-review-guidance` record 的 requested effort 是 medium，且不重寫。現行
`run.py V review-guidance` 與 `run.py V review-high` 都讀取 high（後者為 explicit
high override）；因此目前兩個 label 不是 effort A/B 對照，也不能用它們宣稱
current effort comparison。

原 grader 曾誤用 repo resolver 而使 cwd 回 repo，改 fixture resolver 後重驗；
此 harness 問題與模型結果分開。原始用量不等於帳單或 subscription credits。
