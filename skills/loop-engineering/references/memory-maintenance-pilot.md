# 單專案 synthetic memory-maintenance stop/resume pilot

預設停用，production registry 為空。這是當次新建固定 synthetic fixture 的操作示範，
不讀既有專案／原生記憶，也不認證人類身分或授予 production qualification。

```sh
python3 ~/.agents/skills/loop-engineering/scripts/memory_maintenance_pilot.py --create-synthetic
```

Source checkout 改用 `./scripts/project-python`；plugin 使用其同名 scripts 入口。
不加旗標只回 `disabled`，不讀 stdin／目標或探測環境。沒有 root／JSON／import／
自動確認／重開舊 workspace 參數，沒有 erase/prune/compact 或清理命令。

1. 輸入 `CREATE SYNTHETIC` 並換行，接受在 OS `/tmp` 新建不可預測的隔離目錄。
   忽略 TMPDIR；目錄 0700、資料檔 0600，建立固定 Git objects 與一筆 managed item。
2. 顯示完整 stop preview（scope、item、nonce、前後態 digest、檔案、容量與期限），
   輸入當次顯示的 `STOP <preview_digest>`。EOF、錯字、額外字元均取消。
3. 等待後重驗期限與狀態；只執行一次。stop 保留版本與 proof，一般 recall 查無。
   新 core 以唯讀 connection 再核對 proof/state/projection，輸出 verified。
4. 只有 stop 確認 applied 才顯示新的 resume preview。另輸入
   `RESUME <preview_digest>`；stop 接受不包含 resume。resume 重驗來源，保持 revision 1。

確認預設期限 300 秒；過期不延長，不接受舊 digest／grant 重播。每個輸出事件標記
synthetic-only／production_qualified=false。成功或取消 exit 0，Ctrl-C exit 130，
無法完成 exit 2。seed 寫入及 stop/resume 均會修改 fixture，並非唯讀盤點。
Audit-only provider 不參與 mutation 授權。

## 異常與恢復

取消、漂移、鎖衝突或到期拒絕；儲存/proof 失敗由核心以新 connection 查核，
匹配 proof/後態才 applied，完整前態且無 proof 才 not-applied，其餘 unknown。
seed 準備階段可能已寫入；其失敗或中斷標為 preparation／unknown。
readback 失敗或執行期間中斷不能推論 rollback；輸出故障後停止向故障 sink 寫入，
可能沒有最後事件。任何非 applied 結果都不進入下一個操作，也不重送 mutation。

結束會丟棄 RAM handle 並關閉 ports；OS 強制終止不保證 finally 執行。
完整或部分 fixture 均保留於顯示的 workspace。入口不重開既有 root；重新執行
只建立新 fixture。可信 host 的故障恢復須保留原可信 binding、取得新 readback，
判明 state/proof 後重新 preview／接受新操作，不能恢復舊 grant。非空 journal 保持
recovery-required／unknown，不自動修復、清理或宣稱復原成功。

故障測試使用受控 clock／注入，重點是實際核心路徑的處置，不要求實體
SQLITE_FULL／ENOSPC／ENOMEM 發生。入口以 allowlist 保留 SQLite code／name、OS errno 與記憶體故障分類，不回顯原始錯誤；synthetic
成功不證明物理儲存、power-loss、完整 J/T/G、4 GiB latency 或 production 資格。
同一 OS 使用者任意程式執行不在隔離保證內；沒有背景服務或跨專案能力。
