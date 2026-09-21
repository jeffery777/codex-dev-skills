# Issue #280：驗收範圍及整合證據

## 交付行為

本包提供可安裝的 `AuditAuthorityProvider`、獨立 authority store 與可信 host
整合 reference。原 factory／dispatch／report 介面不變；新程式納入 adapter ports
fingerprint，因此使用更新程式須重新接受 qualification。production registry 仍空。

磁碟只有 lifecycle 與 target digest，不保存可恢復的 grant。owner RAM 的 pending
先消耗才寫 consumed；所有儲存／提交結果不明停用該 provider。原 owner revoke
先撤銷 RAM 再持久化；foreign provider 不宣稱撤銷成功。新 instance、PID 或 restart
不能接手舊要求，故障排除後要有新的 host 接受及新要求。

## 隔離故障驗收

`tests/test_memory_audit_authority.py` 使用真實 authority SQLite、flock、既有
factory／dispatch、audit adapter 及 CLI。授權與來源接受／qualification 仍屬 synthetic。
受控故障注入經實際 connection／transaction／rollback／close 路徑，並未偽造最外層
報告，也不要求實體磁碟／記憶體耗盡。

- 新接受→consumed→owner revoked 有實際持久紀錄；盤點 memory bytes/inode/mtime 未改。
- off 不消耗或接觸兩個 store；先前 accept 的 bookkeeping 不由 off 回溯取消。
- 兩個 provider／同 request 併發、UUID 重用、fresh process／commit 後程序退出皆不重播。
- FULL／BUSY／IOERR／NOMEM／ENOSPC／ENOMEM／未知錯誤在 take 的 BEGIN、UPDATE、
  commit 前後及 readback 注入；grant 不返回、舊要求失效、connection/lock 釋放，
  故障排除後新接受可以恢復。
- accept 的提交結果不明不發布 RAM grant；owner revoke 失敗仍停止原授權，
  不聲稱 durable revoked。snapshot 關閉後的撤銷失敗驗證最後揭露清空內容／digest。
- scope/principal/clock/PID/target 不匹配、close、store replacement/mode/symlink/
  hardlink、sidecar/schema／row 漂移及列數／檔案容量拒絕，沒有自動修復。
- 初始化提交失敗保留產物並關閉 connection；重新初始化非空目錄拒絕覆寫。

新增 16 項測試通過；此前 13 項新增測試連同既有 audit／adapter／dispatch／CLI
共 69 項通過，其後追加 3 項並重跑完整新增 module 通過。使用 tracked
`scripts/project-python` 選擇 Python 3.12.9／PyYAML 6.0.3。其餘 required checks、
獨立 reviews、Security Diff Scan 與 PR 後 exact-head／hosted CI／App gate 的最終
結果由 PR 證據保存；本文件本身不宣稱後續 gates 已完成。

## 設計處置及限制

獨立設計審查 D280-01～03 要求：foreign revoke 不得宣稱原 owner 已停止、消耗後
保留撤銷 ownership、磁碟狀態不得恢復 RAM authority。實作採原 provider 限定撤銷、
pending/live/known 分離、同 session／完整 row 核對與 commit/readback 後供應 grant。
這是設計處置紀錄，仍需最終程式與安全審查驗證。

`write_performed=false` 指 managed memory 內容；authority bookkeeping 是獨立寫入。
每庫 1,024 要求及 4 MiB 主檔 quota 不代表總 filesystem／RSS 上界，journal 另占空間。
provider mutex 序列化 owner 操作；trusted clock 不得重入或無界阻塞。沒有 OS 強制
終止／不可中斷 syscall 清理、硬時間／RSS、跨程序強制撤銷或任意同 OS 攻擊隔離保證。

source/package 維持 `0.24.7`，不新增 release candidate、tag、Release 或安裝部署；
既有歷史紀錄不改寫。本包不需要真實專案，但 synthetic 接受不能用作正式啟用。
