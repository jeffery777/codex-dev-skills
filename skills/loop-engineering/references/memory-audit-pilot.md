# 單專案 synthetic memory-audit 操作 pilot

這是可明確操作的固定 synthetic 示範，不是實際專案 memory adapter、資格認證或
人類身分驗證。預設停用，production registry 保持空。只使用當次新建資料，
不接受 root／config／JSON／resume／自動確認參數，不發現既有專案或原生記憶。

## 操作

使用已安裝環境的 Python 執行：

```sh
python3 ~/.agents/skills/loop-engineering/scripts/memory_audit_pilot.py --create-synthetic
```

1. 輸入 `CREATE SYNTHETIC` 並換行，接受建立一筆固定 synthetic memory、三個 Git
   loose objects、獨立 authority store。未確認前不建立 fixture；不呼叫 Git 或網路。
2. 程式在 `/tmp` 建立不可預測的新目錄（macOS 顯示 canonical `/private/tmp`），
   目錄 `0700`、資料檔 `0600`，忽略 `TMPDIR` 選址；顯示實際 workspace 與精確 scope。
3. 觀察 advisory 預檢。尚無 request 及尚未讀內容時，missing／unknown 是正常狀態，
   不能解讀為 PASS 或正式啟用資格。其他必要項目不符就停止。
4. 輸入本次顯示的 `AUDIT <target_digest>` 並換行。只接受完全相同的單行，EOF、錯字
   或額外字元均取消。確認後重查 metadata 與資格；超過 300 秒期限須重新執行，
   不默默延長期限。不應事先把確認字串當永久憑證保存或自動重播。
5. 執行單次 audit 並輸出 JSON lines；成功 exit 0，取消 exit 0，Ctrl-C exit 130，
   無法完成 exit 2。每個 event 都標記 synthetic-only；不回顯原始錯誤。
   輸出通道故障時停止輸出，可能沒有最後事件；仍 close provider 並 exit 2，
   不向原通道重試或將原始例外改送 stderr。

不帶 `--create-synthetic` 只回 disabled，不讀 stdin／目標／環境。若從 source checkout
執行，使用 `./scripts/project-python skills/loop-engineering/scripts/memory_audit_pilot.py`；
plugin 安裝使用其同名 scripts 入口。入口沒有依賴 checkout 的 tests 或 docs。

## 寫入、停用與恢復

整次 pilot 會寫入 fixture 與 authority lifecycle；外層事件分別標記 fixture_writes、
authority_bookkeeping。內層 audit 的 `write_performed=false` 僅指 managed memory
盤點不改寫，不能解讀為整個流程沒有寫入。提交失敗可能已落盤，不宣稱 rollback 成功。

取消確認不核發 request。正常結束、例外或 Ctrl-C 後關閉 provider，RAM grant 失效；
這不等於持久 row 已撤銷。OS 強制終止不保證 finally cleanup，但下一次程序不會載入
或恢復舊 grant。入口沒有重開舊 workspace 功能；排除故障後重新執行、建立新 fixture、
重新確認。可信 host API 的同 target 新 provider／新接受恢復另由測試驗證。

停止／停用不刪資料；完整或部分 fixture 都保留在顯示的 workspace。入口沒有 cleanup
命令，刪除須另核對精確路徑與權限。沒有 daemon、跨程序強制撤銷、硬 RSS／deadline、
G2、清除、輪替或真實來源啟用。本機相同 OS 使用者的任意程式執行不在隔離保證內。

故障驗收以實際 provider／SQLite／reader 路徑的受控注入驗合理處置，不需要實體
SQLITE_FULL、ENOSPC 或 ENOMEM 發生。Synthetic 成功不證明實際環境 qualification。
