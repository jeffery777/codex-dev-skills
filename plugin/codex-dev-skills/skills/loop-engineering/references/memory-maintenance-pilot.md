# 單專案 synthetic memory-maintenance pilot

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

## 新增／修改與版本一致性

```sh
python3 ~/.agents/skills/loop-engineering/scripts/memory_maintenance_pilot.py --create-synthetic --scenario add-update
```

這是同一 shared script 的固定情境，可由 CLI 或 Desktop 的明確互動終端使用；
不依賴 Desktop internals，也不新增 runtime-specific grant。只加 `--scenario`
而沒有 `--create-synthetic` 仍回 disabled。原指令保留上述 stop/resume 行為。

1. `CREATE SYNTHETIC` 接受建立空 managed root 與兩份固定來源，以及本次 fixture 的
   讀回／recall／audit；不自動 seed ADD，也不接受任意文字、路徑或既有資料。
2. 顯示完整 ADD preview，包含候選 body、summary、cues、provenance、validation
   與 scope。另輸入當次 `ADD <preview_digest>`，才寫入 blue revision 1。
3. UPDATE 顯示完整前後內容。舊內容以新唯讀 recall 取得，snapshot digest 必須
   等於 preview 前態；green revision 2 有獨立固定 Git artifact 與 permit。
   另輸入 `UPDATE <preview_digest>`；等待期間的狀態／來源／期限漂移仍須拒絕。
4. 接著分別確認 STOP、RESUME。每步先核對 applied，再以新 core 讀回 proof，
   有界 audit 核對 revision／保留版本數／status／來源覆蓋，並比較 blue、green、
   widget 及新舊關鍵詞組合。UPDATE 後只召回 revision 2，blue 或 blue+green 查無；
   STOP 全查無，RESUME 恢復 revision 2，保留兩版，不新增 revision 3。

取消 ADD 後 items／versions／proofs 皆為零；後續取消保留已確認且提交的操作。
更新保留舊版內容與 provenance，只補 retired_at；此情境不執行歷史 restore。

## 歷史版本還原

```sh
python3 ~/.agents/skills/loop-engineering/scripts/memory_maintenance_pilot.py --create-synthetic --scenario add-update-restore
```

這個固定情境依序 ADD → UPDATE → RESTORE，每步仍須獨立確認。建立時另明示
還原預覽會讀取本次 fixture 的指定舊版全文；沒有任意 revision／root 或歷史匯入參數。

1. ADD 與 UPDATE 分別建立 blue revision 1、green revision 2，沿用上述確認與核對。
2. RESTORE 預覽以當次可信 binding 的有界唯讀 transaction 取得實際 current 與
   retained revision 1；完整內容包含 provenance、原 validation、created_at 及
   retired_at。兩版與 preview 前態／epoch 綁定，顯示為 `change.before`、
   `change.restore_source`；`change.after` 是新候選，`snapshot_digest` 標示同一前態。
   在等待輸入前釋放讀鎖，歷史全文不加入一般 recall。
3. 新候選保留 blue 內容與原 Git provenance，重新讀取 pinned artifact、核對 bytes，
   使用當下時間與新的 validation evidence ID；不沿用 ADD 的 observation。
   另輸入 `RESTORE <preview_digest>`，等待後仍重驗期限、來源、前態與容量。
4. 還原產生 blue revision 3，保留 revisions 1/2 及 proof；fresh readback／audit
   核對 `(before=2, after=3, restore_source_revision=1)` 與三版歷史。
   一般 recall 只回 revision 3，green、green+widget、blue+green 皆查無。

取消 RESTORE 保留已提交的 revision 2；不回到 revision 1，也不新增第三版。
原 stop/resume 及 add/update 指令保持原行為。這是 synthetic 還原示範，
不啟用 production，也不表示 G1/MG1 qualification 已完成。

## 共用確認與結果

確認預設期限 300 秒；過期不延長，不接受舊 digest／grant 重播。每個輸出事件標記
synthetic-only／production_qualified=false。成功或取消 exit 0，Ctrl-C exit 130，
無法完成 exit 2。建立 fixture、舊情境 seed 與已確認 mutation 均有寫入，並非唯讀盤點。
Audit-only provider 不參與 mutation 授權。

## 異常與恢復

取消、漂移、鎖衝突或到期拒絕；儲存/proof 失敗由核心以新 connection 查核，
匹配 proof/後態才 applied，完整前態且無 proof 才 not-applied，其餘 unknown。
seed 準備階段可能已寫入；其失敗或中斷標為 preparation／unknown。
readback 失敗或執行期間中斷不能推論 rollback；輸出故障後停止向故障 sink 寫入，
可能沒有最後事件。任何非 applied 結果都不進入下一個操作，也不重送 mutation。
add/update/restore 的提交後 audit 或驗證失敗同樣保留 unknown；先前 applied 事件只是
該步讀回，不能代替整段完成。只有該步所有核對成功才輸出 verified。

結束會丟棄 RAM handle 並關閉 ports；OS 強制終止不保證 finally 執行。
完整或部分 fixture 均保留於顯示的 workspace。入口不重開既有 root；重新執行
只建立新 fixture。可信 host 的故障恢復須保留原可信 binding、取得新 readback，
判明 state/proof 後重新 preview／接受新操作，不能恢復舊 grant。非空 journal 保持
recovery-required／unknown，不自動修復、清理或宣稱復原成功。

故障測試使用受控 clock／注入，重點是實際核心路徑的處置，不要求實體
SQLITE_FULL／ENOSPC／ENOMEM 發生。入口以 allowlist 保留 SQLite code／name、OS errno 與記憶體故障分類，不回顯原始錯誤；synthetic
成功不證明物理儲存、power-loss、完整 J/T/G、4 GiB latency 或 production 資格。
同一 OS 使用者任意程式執行不在隔離保證內；沒有背景服務或跨專案能力。
