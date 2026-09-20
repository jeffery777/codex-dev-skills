# Issue #271：第四次補壓與恢復失敗觀察

## 結果與授權範圍

2026-09-20，使用者在[三檔補壓準備](pressure-pool-preparation.md)完成交付與
精確資源／恢復方案核對後，另行授權一次全新 256 MiB APFS 試驗。執行來源為
`25d88ddf0a397d298b87a314445143122bf42814`；19 份消費來源（18 份 tracked
來源及本機執行器）、方案摘要、資源不存在及親目錄身分在執行前一致。
使用 worktree venv、tracked `scripts/project-python`、Python 3.12.9／PyYAML 6.0.3；
最新唯讀預檢通過後才執行。精確路徑、原始觀察、授權與執行器只留本機。

本次僅執行一次，累計四次額度均已使用，沒有重試或第五次方案。結果為
**incomplete／sqlite-cantopen**：SQLite 回傳 `SQLITE_CANTOPEN`（14），
沒有 `SQLITE_FULL`（13）；writer 正常退出，回報 not-applied。
own filler 的容量恢復未能證明，因此沒有執行獨立新程序讀回或正常 control。
映像已正常卸載並保留。去識別證據見
[pressure-pool-observation.json](pressure-pool-observation.json)。

## 已觀察事實

壓力於目標交易前、journal absent 時開始；九個固定 progress frames 完整收到。
所有階段共用 256 MiB、70,000 次寫入及單一 30 秒期限，實際如下：

| 階段 | 實寫 bytes | write／pwrite 次數 | 停止原因 | 同步 |
| --- | ---: | ---: | --- | --- |
| bulk | 260,046,848 | 251 | 1 MiB／64 KiB／4 KiB 均 ENOSPC | succeeded |
| 同 fd 同步後 EOF 探測 | 0 | 1 | ENOSPC | succeeded |
| small_1 | 917,504（896 KiB） | 225 | ENOSPC | succeeded |
| small_2 | 0 | 1 | ENOSPC | succeeded |
| 合計 | 260,964,352 | 478 | 低於共同上限 | 四階段均完成 |

最後 small_2 實際 ENOSPC、同步及觀察完成後，唯一一次目標交易才繼續。
writer 正常退出、沒有 timeout 或截斷 frame；核心、SQL、quota 與分類器未改，
max_page_count 仍為 1,048,576、交易前 page_count 12。SQLite execute 回報
CANTOPEN；writer 的 not-applied 是同一程序中的觀察，不能當成後續獨立一致性證據。

writer 退出後，restore worker 依序嘗試三個已綁定 filler：第 0、1 檔的
截短／同步恢復流程回報 errno 28；第 2 檔本來沒有資料，回報 restored、
released bytes 0。最終未證明全組檔案皆為空，可用容量取樣沒有增加，
整組 result 為 unproven。報告沒有區分失敗的系統呼叫，不能斷言失敗一定發生在
`ftruncate` 或 `fsync`；reported released bytes 0 也不是逐檔實際狀態的完整證明。

協調器按既有規則停止 fresh readback 與 control，沒有再次恢復、修復資料庫或
改動 journal。正常 detach 後，另以唯讀附掛清單及 mount 狀態確認精確映像
沒有附掛；映像仍是原身分的 regular file 且未超出 256 MiB。映像旁報告與
本機執行器報告逐項一致，宿主 headroom 檢查通過。**正常卸載不代表容量恢復成功**，
也沒有重新掛載映像以查讀或清理其內容。

## 方法重評與下一個決策

這次能確認：同一個大檔在同步後仍無法延伸時，另一個預建 inode 仍可寫入
896 KiB；因此單一 filler 的 ENOSPC 不能證明其他檔案完全無法配置空間。
這不是 APFS reserve、metadata 配置或延遲配置根因的證明。SQLite CANTOPEN
沒有提供失敗檔案身分；量測期間曾出現 journal 也不能定位失敗時點或證明
事後 journal 狀態。沒有新 reader，因此失敗交易一致性及 journal maintenance
需求均保持未驗證。

更強的補壓改變了觀察結果，但同時暴露容量恢復未成功的限制。下一步應先
研究可恢復的壓力控制及錯誤發生位置，提出能區分恢復失敗系統呼叫的有界觀測，
再評估精確資源與復原方案。不能直接沿用「截短 filler 一定能釋放容量」的假設，
也不能靠加大壓力、原樣重跑、刪檔或重掛目前映像來追逐 FULL。
這是研究方向，沒有第五次試驗、映像維護、repair 或清理的授權。

MR-272-01 保持 Needs Human Decision，owner 為 G1 storage／Issue #271 delivery owner。
原 DoD 仍為 physical SQLite FULL → writer 退出 → own pool 容量恢復 →
失敗交易 fresh readback → 新 preview／confirmation 正常 control → 正常卸載。
本次缺少 FULL、可確認的容量恢復與後續獨立讀回／control；新的恢復限制納入
同一未完成驗收追蹤，不用 CANTOPEN、not-applied、ENOSPC 或 detach 替代驗收。
若要調整驗收範圍，須另外明確決定。

## 驗證、審查與版本界線

執行來源的完整 12 shards／1,258 tests、15 個 hosted CI jobs 已通過，見
[來源驗證 run 35505579400](https://github.com/jeffery777/codex-dev-skills/actions/runs/35505579400)。
第四次專用執行器另有 11 項離線測試、獨立安全核對及來源綁定；這些事前證據
不能證明實體恢復一定成功。本次實測以 exit 2 如實回報 incomplete，不列為通過。

本次追加僅同步去識別證據與 active docs，沒有程式、測試、SQL 或可安裝內容變更。
既有程式測試須核對來源與環境後才沿用，另以 raw-to-summary／JSON／文件連結／
隱私檢查、repository checks、獨立文件審查與相應安全掃描核對本次材料。
最終提交的完整 base-to-head Merge Review 及 CI 結果以
[PR #272](https://github.com/jeffery777/codex-dev-skills/pull/272)版本審查紀錄為準。

Issue 保持 open、PR 保持 draft，不發布成功 strict receipt、不合併。不另發版：
catalog source/package 0.24.7、default-off／空 production registry／unqualified 保持；
前次準備與試驗文件留作點時紀錄，不將它們當成第四次以後的即時狀態。
