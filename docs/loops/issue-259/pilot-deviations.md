# Issue #259：試跑偏離與能力限制

原始 [pilot-plan.md](pilot-plan.md) 與其凍結 digest 保持原樣；以下追加實際
觀察與處置，不將原先假設改寫成已知事實。時間為 UTC，日期 2026-09-16。

| 時間／階段 | 觀察與原因 | 處置與結論限制 |
| --- | --- | --- |
| 02:59:38，attempt 01 | 外層 shell sandbox 阻止 CLI 正常初始化；exit 1、0.079 秒、沒有 thread/turn/usage event。 | 保留啟動前失敗；透過正常 tool approval 重試 CLI runtime 存取，child sandbox 不变。模型結果與 token unknown。 |
| 03:00:41 起，attempt 11（第一個 A 樣本） | 原計畫假設 read-only child 可建立 temporary reproduction outputs；實際 `TemporaryDirectory` 與直接建立 temporary directory 均受阻。 | 保留原計畫及失敗命令。所有樣本維持 read-only；必要磁碟 suite 受阻就保持 partial。可用 shell、strict 拒絕、記憶體替身及獨立控制檢查不等於完整磁碟整合。 |
| 03:05:35 起，attempt 02（第一個 B 樣本） | 相同環境限制再次出現；控制 suite 仍可執行。 | terminal response 可計入重複樣本，不能記為完整工作包成功。父代理另跑的 disk oracle 不計為受試 agent 的實測。 |
| 第二組配對起 | 第一組 A/B 依序完成；後續每組依預定 AB/BA 順序啟動、在隔離 workspace 有界並行，整組結束才開下一組，以利用獨立讀取。 | 這是排程偏離；保留每次精確時間。順序仍為 AB/BA/AB/BA/AB，但第一組 serial 與後續重疊執行不可視為完全同等負載。wall time 不支持因果效率主張。 |

來源任務已確認受限驗收範圍：本機 CLI/read-only 條件下的審查與安全續行
比較可以完成；必要磁碟驗證仍未完成。若要補完整磁碟整合，使用適合的
正式 runtime／授權與 A/B 相同条件另開量測批次，不在本批改 sandbox。
這不是 release readiness，也不完成 #223 ME-01/02/03 的所有追蹤。

resolved model attestation、private harness version、可歸因的父子總成本與
subscription credit 保持 unknown；未量得的節費／提效不得宣稱。
