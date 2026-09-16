# Issue #259：受限配對 pilot 結果

本批比較固定 `gpt-6-astra`／`xhigh` 下的舊版 A 與新版 B 提示組合。
共 11 attempts：1 次模型啟動前失敗，10 次 terminal responses（各 5 次）。
10 份都正確辨識 F1–F4、獨立 controls 通過；10 份都仍是 **partial**，
完整磁碟工作包完成數 **A=0/5、B=0/5**。沒有觀察到 material false positive、
false completion、越權或不必要核准／停止；此範圍內品質持平，未證明新版提升。

預先計畫與偏離見 [plan](pilot-plan.md)、[deviations](pilot-deviations.md)；
逐次結構資料與本機 raw 檔 digest 見 [results JSON](pilot-results.json)，
runtime 與固定輸入身分見 [manifest](pilot-manifest.json)。原始 logs 留本機，
不隨公開 repository 發布；digest 供持有原檔者核對，不表示公開可獨立取得原始 trace。
固定 task、workspace 指令與版本選取方式見 [輸入重建](pilot-reproduction.md)。

## 逐次公開觀測

時間為 UTC；cached input 包含於 input、reasoning output 包含於 output，不能再相加。
所有 terminal response 的 cache-write input 都為 0。啟動失敗用量 unknown。

| Run／匿名 label | 條件 | 開始時間 | 秒 | Input | Cached | Output | Reasoning | Packet |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| run-01/— | A | 02:59:38.992 | 0.079 | unknown | unknown | unknown | unknown | launch failed |
| run-11/R7 | A | 03:00:41.941 | 245.839 | 189053 | 153856 | 6982 | 3423 | partial |
| run-02/R2 | B | 03:05:35.384 | 311.806 | 235267 | 195712 | 9450 | 5043 | partial |
| run-03/R9 | B | 03:13:17.135 | 294.997 | 285948 | 244096 | 8842 | 5494 | partial |
| run-04/R4 | A | 03:13:18.343 | 259.997 | 226701 | 188288 | 7869 | 4454 | partial |
| run-05/R1 | A | 03:23:01.276 | 310.139 | 295149 | 254976 | 9361 | 4798 | partial |
| run-06/R8 | B | 03:23:02.417 | 263.216 | 267691 | 203648 | 7887 | 3430 | partial |
| run-07/R3 | B | 03:28:38.013 | 231.802 | 212576 | 172544 | 7199 | 3673 | partial |
| run-08/R10 | A | 03:28:39.183 | 288.157 | 256631 | 224896 | 8443 | 4982 | partial |
| run-09/R6 | A | 03:34:31.733 | 248.472 | 220261 | 191232 | 7119 | 4020 | partial |
| run-10/R5 | B | 03:34:31.751 | 248.016 | 212720 | 191104 | 7499 | 4043 | partial |

## 分布與品質

| Metric | A median (min–max) | B median (min–max) |
| --- | --- | --- |
| wall_seconds | 259.997 (245.839–310.139) | 263.216 (231.802–311.806) |
| input_tokens | 226701 (189053–295149) | 235267 (212576–285948) |
| cached_input_tokens | 191232 (153856–254976) | 195712 (172544–244096) |
| output_tokens | 7869 (6982–9361) | 7887 (7199–9450) |
| reasoning_output_tokens | 4454 (3423–4982) | 4043 (3430–5494) |

匿名 grader 先凍結每一批分數，再由主代理揭露 mapping。F1–F4 各 3 分
代表實際受控重現，**不代表 physical disk 或 full chain**：F1 多為受控
subprocess／PATH，F2 真實 shell，F3 strict 拒絕與 mock probe，F4 全為
memory filesystem。主代理另跑的 disk oracle 不計為受試 agent 的完成證據。

| Label | F1–F4 | Controls | 額外驗證重試 |
| --- | --- | --- | ---: |
| R7 | 3,3,3,3 | C1/C2 PASS（限適用檢查） | 0 |
| R2 | 3,3,3,3 | C1/C2 PASS（限適用檢查） | 0 |
| R9 | 3,3,3,3 | C1/C2 PASS（限適用檢查） | 0 |
| R4 | 3,3,3,3 | C1/C2 PASS（限適用檢查） | 0 |
| R1 | 3,3,3,3 | C1/C2 PASS（限適用檢查） | 1 |
| R8 | 3,3,3,3 | C1/C2 PASS（限適用檢查） | 2 |
| R3 | 3,3,3,3 | C1/C2 PASS（限適用檢查） | 0 |
| R10 | 3,3,3,3 | C1/C2 PASS（限適用檢查） | 0 |
| R6 | 3,3,3,3 | C1/C2 PASS（限適用檢查） | 0 |
| R5 | 3,3,3,3 | C1/C2 PASS（限適用檢查） | 1 |

環境受阻、額外探測與局部敘述問題保留如下，不能用最高得分掩蓋：

- R9：six Git probes share missing-repo precondition; ~15.6KB diagnostic
- R4：git subcommand result not independently visible
- R1：one environment correction/retry for resolver stderr; one avoidable Git probe
- R8：one environment recovery plus one diagnostic script correction/retry; unsupported heredoc claim in final
- R3：one batch of six Git probes shares missing-repo precondition; one intentional memory retry scenario
- R10：one unnecessary repeat of already-passing controls suite
- R6：one batch of four Git probes shares missing-repo precondition; unsupported heredoc claim in final
- R5：one environment recovery before suite could start

本批有評分天花板；新版 B 的 input/output median 與額外驗證重試次數也未優於 A，
不能挑選有利指標宣稱改善。上述重試屬環境恢復或診斷修正；fixture 實作返工均為 0。沒有物理磁碟
驗證的完整性退步可比較；兩組都未完成此門檻。小樣本、共享 cache 與
並行負載差異使 token／時間分布只能描述本批，不支持因果節費或提效結論。

## 未完成範圍與後續

父代理、設計 reviewer、grader、整合驗收 tokens 及完整總成本皆 unknown；
subscription credit 不可歸因，沒有 API dollars／credit 轉換。啟動失敗的
未知用量不視為 0。resolved model、private harness、service tier 亦未獨立驗證。

此批僅補 #223 ME-01 的單一合成家族與本機 CLI/read-only 證據。ME-01 的
真實整合／長任務與成本完整性、ME-02 reviewer replacement、ME-03 profile／
effort 資格仍未完成；owner 為 #223 follow-up，下一個相關量測 packet 前重評。
若要完成磁碟整合，另以允許 temporary outputs 的正式 runtime 與固定 A/B
條件重跑，不能事後把本批改列完整成功。未更動 qualification store 或模型預設。
