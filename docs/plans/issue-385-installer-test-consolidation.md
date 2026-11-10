# Issue #385：安裝測試精簡與覆蓋取捨

這個切片減少測試內重複的安裝交易與歷史來源故障組合，對應
[Issue #385](https://github.com/jeffery777/codex-dev-skills/issues/385)。
兩個長模組合計由72項變為66項；產品安裝器、共用 fixture、歷史來源清冊、
workflow及測試分組保持原樣。按風險選測與既有CI結果重用仍屬後續工作。

## 三項修改

| 修改 | 保留的保障 | 接受的取捨 |
| --- | --- | --- |
| 舊11檔 Core 的五故障點改用 `update codex-agent-profiles` | dependency closure涵蓋原管理三群組；backup、promote、history、inventory、profile全部保留，原有回復斷言不變 | 不再於這五點同時新增其他預設群組；完整 `--all` 整合仍由其他案例執行 |
| 合併舊來源資料／promisor拒絕與umask002安裝更新 | 舊程式sentinel不執行、版本及payload、拒絕診斷、最終權限；另驗fresh精確權限及拒絕前後的有界狀態 | 4→3次installer呼叫；sentinel由繼承的default umask移至002，兩個獨立HOME變成一條相依流程 |
| 省略五個獨立歷史故障案例 | 既有14檔完整七切點矩陣承接升級後驗證失敗；保留current→14檔降級的首次history receipt promotion故障 | 減少特定歷史資料與故障的交互組合及獨立診斷，並非無損等價 |

合併流程是 OLD install002 → promisor拒絕 → current update002；current update前
還原舊來源程式及promisor設定，finally再保底。fresh模式檢查可抓到後續更新
會修復並掩蓋的0644偏差；0666則原案與新案都能偵測。拒絕狀態比較包含
測試擁有的目錄、型別、模式、檔案內容及symlink target，並非整台主機狀態證明。

## 歷史故障的代表與損失

`installer-inventory.py` 將Core聚合為一個directory交易；回復依replaced、
backed-up及created處理。14檔與20檔升級的42份puts完全相同，14檔矩陣
還會核對原Core模式、bytes與目錄集合。28檔有七個額外unchanged artifact，
但其他來源本來就同時含unchanged directory/file，未找到它獨有的通用回復分支。

省略的是20／23／28檔三個獨立postverify fault，以及降至23／28檔的首次
history receipt promotion fault。正常歷史roundtrip與mapping仍保留；它們
不能完全替代省略的備份bytes、hash、descriptor及特定key×狀態的失敗組合。

升級postverify位於首次payload驗證，receipt尚未promotion；降級代表則先
完成真實payload／歷史Core驗證，再在history promotion失敗，包含退休
`skills/dev-retro` 的恢復。這兩個切點不能互相取代。保留的
`test_twenty_file_downgrade_fault_restores_current_tree` 名稱沿用歷史，其實際目標是14檔。

## 驗證與診斷

本機候選已完整執行14檔七切點矩陣及降級代表，2 cases／8次installer呼叫
通過，wall time232.625秒。另對保留路徑注入Core restore失敗、receipt original
restore失敗及未受管sibling誤寫，三例都在指定snapshot assertion失敗，零error／skip。

實際診斷對照在第一個backup呼叫返回後才刻意改錯fixture Core，模擬錯誤的
回復狀態；這不是已發現的產品缺陷。矩陣第一點snapshot失敗，後六點均被
受損payload的preflight阻擋。從固定基準重建的獨立20檔參考案例仍能抵達
postverify。整體framework保持失敗，後續參考通過沒有被當作整套成功。
因此精簡減少獨立診斷資訊；這次對照未觀察到誤綠，也不證明所有錯誤都不會誤綠。

研究負例以相同字典相等語意省略昂貴的完整bytes差異排版，正式測試斷言未改。
先前一輪負例在unittest差異格式化中中斷，仍保留未完成結果；後續成功未將
它改記為PASS。既有snapshot只涵蓋一般檔案，不構成所有空目錄／symlink的狀態證明。

五個省略案例的單輪本機觀察合計約167秒，含研究用查讀與fixture準備，
不是正式CI可承諾的節省。前述232.625秒也不是與舊整套的受控A/B；不同輪次
的時間不可直接相減。可以確認的是少六個installer呼叫：合併fresh install少一個，
省略五個歷史案例再少五個；五故障點的scope精簡只減少每次工作量，不減呼叫數。

同一候選已在乾淨本機checkout完整執行兩個相關模組：fault-boundaries 21項
通過（958.671秒），source-integrity 45項通過（1151.802秒），共66項，零失敗／skip。
兩個模組並行執行，這些時間是各模組wall time，不是整體wall time、CPU時間
或正式CI改善量。其他模組按未變邊界重用既有證據，未宣稱全repository unit suite已重跑。
重新執行相關模組可用：

```sh
./scripts/project-python -B -m unittest -v tests.test_installer_fault_boundaries
./scripts/project-python -B -m unittest -v tests.test_installer_source_integrity
./scripts/validate-repo.sh --skip-unit-tests
```

installer整合驗證須使用乾淨的來源checkout，避免本機ignored caches污染payload；
每個checkout都使用自己的tracked Python resolver，不複製個人環境或安裝狀態。

## Linux receipt旗標的輕量行為覆蓋

另在 `tests.test_installer_runtime_groups.InstallerBoundaryUnitTests` 補一個測試，
執行 `install.sh` 中真實的 `validate_receipt_writable` Python程式，只模擬Linux
平台選擇及 `fcntl.ioctl` 回傳：無旗標可接受，append-only、immutable及ioctl讀取
失敗須以明確診斷拒絕。四種情境均核對receipt bytes不變及開啟的descriptor已關閉。
此案例不執行installer交易、不需sudo，也不設定真實inode旗標；不改動前述兩個
長模組的66項計數，亦不取代Linux核心／檔案系統的真實旗標整合測試。

既有 `os.chflags` 的append-only及immutable案例在Linux仍可能因API不存在而
略過；這不代表Linux沒有對應旗標，也不代表本輪執行了正式Security Diff Scan。
產品既有Linux分支以 `FS_IOC_GETFLAGS` 查讀旗標，無法查讀時拒絕繼續，行為未改。
輕量案例可獨立執行：

```sh
./scripts/project-python -B -m unittest -v tests.test_installer_runtime_groups.InstallerBoundaryUnitTests
```
