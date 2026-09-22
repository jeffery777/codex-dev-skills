# Issue #288 驗證與處置紀錄

## 行為及異常證據

`./scripts/project-python -m unittest tests.test_memory_maintenance_pilot`：17 項通過。
測試走實際 GovernanceCore／LocalHost／SQLite／PinnedGitReader 路徑，採受控 clock／fault
injection；POSIX process fixture 在 after-commit 直接退出，再由保留可信 binding 的新
core 讀回。沒有從 JSON／CLI 復活 host 或 grant。

| 邊界 | 已驗證 oracle |
| --- | --- |
| 預設／取消 | disabled 零觸及；create、stop、resume 各自取消；production registry 空。 |
| 正常停用／恢復 | stop recall=0；resume recall=1；版本仍一筆、revision=1、proof 共三筆。 |
| 等待與漂移 | 到期、source/root/state 漂移及 lock conflict 拒絕；handle 消耗後不可重送。 |
| 儲存／proof | item-write、before-commit、proof insert 失敗，fresh readback 判 not-applied；after-commit reply loss 判 applied。 |
| 讀回未知 | commit 後 readback 故障保持 unknown，後續 fresh readback 判明，不自動再 execute。 |
| 程序中斷 | after-commit POSIX 子程序退出，父程序新 core 核對 proof／投影；舊 handle 拒絕，新 resume 確認才恢復。 |
| seed 準備 | seed before/after commit/readback 的中斷與 MemoryError 保 preparation／unknown；不冒稱未嘗試。 |
| 輸出 | confirmation 輸出失敗不 execute；提交後輸出失敗保留 proof、不自動 resume；不回原始 PRIVATE 錯誤文字。 |
| 錯誤分類 | 原生 SQLite code/name、OS errno 保留於核心 cause；入口只輸出 allowlist 分類及受限數值。 |

首輪聚焦回歸 124 項中，3 項 release-state tests 因新 note 固定章節／traceability 格式
失敗，其餘通過。格式修正後 release-state 10 項通過；新增及修正的 maintenance
17 項通過。Package／shard tests 24 項通過。此處不將重跑次數相加成不同測試數。

`./scripts/validate-repo.sh --skip-unit-tests` exit 0：offline checks 通過；內嵌 unit-test
群組依旗標跳過，不宣稱本機已跑全套。`validate-release-state.py`、
`sync-plugin-package.py` 及 `git diff --check` 通過。新檔須 intent-to-add 後 generator
才納入 tracked allowlist；最終 package 為 140 generated files。

## 獨立審查處置

| ID | 等級 | 處置 | 驗證 |
| --- | --- | --- | --- |
| ISSUE288-DEEP-R1 | MUST-FIX / P2 | Fixed：seed 準備前設 mutation 階段，未知回 preparation/state-unknown。 | seed 前／後 commit／readback 中斷與 MemoryError 入口測試。 |
| ISSUE288-DEEP-R2 | SHOULD-FIX / P2 | Fixed：加入安全 fault_class／OS errno／SQLite primary code/name；不回原始例外。 | CLI 分別注入 ENOSPC、ENOMEM、CANTOPEN、MemoryError。 |

審查採 baseline deep-reviewer，當次 Desktop public schema 可用、read-only sandbox
不放寬 parent；資格 store 的 CLI 專屬候選不適用，本次未聲稱候選品質資格。
主代理核對 finding 重現及修正 tests，複審結果與 scan／exact-head 狀態由 PR 證據提供。

## 安裝與發布邊界

隔離 HOME／XDG_STATE_HOME 的 fresh install 及 v0.24.7 → 0.26.0 upgrade：
先 install 舊版、預覽 diff、non-force update 拒絕並比對 bytes/modes 不變，
再 force update 並核對 loop-engineering backup bytes、receipt 0.26.0、source parity、
後續 diff 與 installed 入口 disabled。所有目標僅新建暫存 sandbox，未改真實安裝。
安裝後的完整 stop/resume 與 installer fault regression 另於 PR 驗收結果列明。

2026-09-22 精確查核 v0.25.0 tag/ref 與 Release-by-tag 均 HTTP 404；當次無其發布證據。
此點時讀回不維護目前發布版本指標；正式 publication gate 必須重查 v0.26.0 衝突、
annotated tag／dereferenced commit／Release metadata。Release note、計畫與測試不是發布證據。

限制：synthetic qualification、受控注入及程序中斷不證明 production、物理
SQLITE_FULL／ENOSPC、power-loss、完整 J/T/G 或 4 GiB worst-case latency。
CLI 不重開舊 fixture，不提供 journal recovery、cleanup、原生記憶或 G2。

## 修後 gate 與安裝結果

獨立 reviewer 比例複審回 code/data／docs PASS，R1/R2 均 Fixed、無新 findings；
主代理核對 source／test digest、重跑 17 項並完成 agent-integrate accepted。
這是協作證據，整體完成仍由以下 repository／平台 gate 判定。

最終隔離 fresh／upgrade 的 installed CLI 均完成 create → stop → resume，verified
recall_count 為 0、1，receipt/parity/diff 通過；fixture 刻意保留。四項 installer
異常回歸（expanded-group conflict、backup collision、receipt replace failure、
unsafe state mode/symlink）通過，沒有改 installer 控制流程。

Security Diff Scan `5812fa3b-0fd3-4dff-874a-1513bcce66d0` 完成、0 findings。
它綁初始 working-tree snapshot，掃描期間有上述功能修正，工具明記 snapshot drift，
不能作為最終 head 的掃描證據。主代理另檢修正的 phase/error 輸出邊界；
提交後再對固定 base/head 取得 Security Diff Scan 與完整 Merge Review。
