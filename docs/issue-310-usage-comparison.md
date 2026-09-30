# Issue #310：相近記憶工作用量觀察

查核日期：2026-09-30。歷史觀察窗口為 Asia/Taipei 2026-09-22～2026-09-25。
本任務未完成，資料屬點時比較準備，不宣稱完成效率或因果節省率。
本檔只保存去識別 task/phase 彙總；無私人對話、帳戶、機器路徑或 runtime logs。

## 資料與去重邊界

使用當前公開 `list_threads`／`read_thread` 查讀本專案相近聊天，再以公開
Codex Security `get_codex_security_scan_context` 讀回既有 scan usage；沒有直接
讀取 Desktop DB、log、session 或未公開 API。歷史對話提及的 scan 數值已與公開
工具當前結果核對。公開聊天回傳 turn 時間、階段與協調內容，但本次未見逐 turn
token/credits 或完整父子/fork incremental accounting。

補查本專案的「同步 GitHub 並推薦開發項目」、「審計 Agent 模型與升級策略」及
archived listing。公開 archived listing 本次只有窗口外的舊聊天；可見專案 inventory
已覆蓋窗口前的紀錄，但公開列表不是不可見／刪除聊天的完整性證明。相近記憶聊天
的 turn pages 已查至 hasMore=false；模型遷移／release／sidebar／runtime 診斷只用
來辨認階段，不混入下列產品樣本。已找到之前「異常處置與恢復、不要求物理耗盡」
的交辦記錄，與本次使用者重申一致。

下表是工具標記 `source=codex_rollout`、`coverage=complete` 的 scan-associated
usage；complete 限工具的掃描計量，不代表任務全部階段完整。`input` 已含 cached，
`output` 已含 reasoning，兩者不能再次加總其子欄位。`total=input+output`。
同 scan 在失敗、恢復及不同對話重複提及只列一次；不同 scan 可能涵蓋重疊的
父／子 rollout 或 cumulative 區段，因未提供 incremental/fork 邊界而不相加。

公開 scan model/effort 是 scan 配置，不能冒充主代理或全部納入子代理的 resolved
model。下列 count 是工具 usage.threadCount，不能視為完整 agent lineage；speed、
逐 execution resolved model、主代理完整用量、一般 review 用量及實際 credits 均
unknown。因此暫不按單一 scan model 費率給混合彙總估價，也不從帳戶額度差換算。

## 歷史分組

| Task / 日期 | Scan 階段 | 配置 model / effort | Input | Cached input | Output | Total | 計量 thread count |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| #282 / 9/22 | 原始預檢／canary | GPT-6 Astra / medium | 10,335,150 | 10,123,264 | 29,579 | 10,364,729 | 3 |
| #282 / 9/22 | R282-01 修正 | GPT-6 Astra / medium | 2,394,085 | 2,381,184 | 3,984 | 2,398,069 | 1 |
| #282 / 9/22 | 封存／coverage 恢復 | GPT-6 Astra / medium | 1,425,481 | 1,373,184 | 5,542 | 1,431,023 | 1 |
| #282 / 9/22 | Linux filesystem identity 修正 | GPT-6 Astra / medium | 1,669,036 | 1,660,672 | 3,813 | 1,672,849 | 1 |
| #284 / 9/22 | audit pilot 原始 | GPT-6 Astra / medium | 6,827,461 | 6,689,920 | 26,663 | 6,854,124 | 2 |
| #284 / 9/22 | output 故障修正 | GPT-6 Astra / medium | 1,930,669 | 1,918,592 | 6,911 | 1,937,580 | 1 |
| #284 / 9/22 | exact-head coverage 補齊 | GPT-6 Astra / medium | 1,799,732 | 1,716,864 | 7,606 | 1,807,338 | 1 |
| #288 / 9/22 | stop/resume 原始 | GPT-6 Astra / medium | 7,255,650 | 7,067,520 | 26,918 | 7,282,568 | 3 |
| #288 / 9/22 | exact-head 複驗 | GPT-6 Astra / medium | 1,866,739 | 1,856,896 | 2,178 | 1,868,917 | 1 |
| #297 / 9/24 | add/update 原始 | GPT-6 Astra / xhigh | 4,999,677 | 4,818,048 | 27,374 | 5,027,051 | 2 |
| #297 / 9/24 | completed coverage 對帳 | GPT-6 Astra / xhigh | 906,873 | 901,888 | 2,943 | 909,816 | 1 |
| #299 / 9/25 | restore | GPT-6 Astra / xhigh | 12,003,218 | 11,239,168 | 53,553 | 12,056,771 | 3 |

公開交付範圍來源：[PR #283](https://github.com/jeffery777/codex-dev-skills/pull/283)、
[PR #285](https://github.com/jeffery777/codex-dev-skills/pull/285)、
[PR #289](https://github.com/jeffery777/codex-dev-skills/pull/289)、
[PR #298](https://github.com/jeffery777/codex-dev-skills/pull/298)、
[PR #300](https://github.com/jeffery777/codex-dev-skills/pull/300)。

這是 selected comparable task 群組，非整段日期總量。#286 release-only、#290
controller、#295 runtime 診斷、#301 sidebar 與其他專案不混入產品用量。
#288 前置 worktree 啟動失敗與重試、#282 掃描封存失敗／恢復、#284 output 修正、
#297 暫停／續作與 coverage 補齊均保留流程差異；未提供可靠用量的階段標 unknown，
不刪除失敗、不當零值、不只選最後成功 scan。

## 本任務與可比限制

| 欄位 | Issue #310 點時狀態 |
| --- | --- |
| Requested 主代理 | GPT-6.1 Sol / medium；使用者指定，未降低 effort |
| Runtime | Desktop 本機入口；正式 CLI 委派 agent 五操作驗收完成，最後 root 停用 |
| Deep 設計 review | 已 route baseline GPT-6 Astra / xhigh，唯讀；回報容量資格 blocker |
| Resolved model / speed | unknown；配置或自報不作底層 attestation |
| 父／子／一般 review／返工 tokens | unknown；沒有完整 incremental accounting |
| Security scan tokens | 已封存 scan-associated 點時數值見下表；不當完整任務增量 |
| 估算 credits / 實際扣量 | unknown / unknown |
| 完成品質／時間 | 本機受限契約驗收完成；正式 commit／PR gate 未簽發，詳見驗證紀錄 |

2026-09-30 公開 scan context 讀回（scan 配置 GPT-6.1 Sol／medium；resolved execution
model 仍 unknown）。掃描已封存，coverage complete、26 changed surfaces、0 findings；
含 original snapshot 後結果分類修正的獨立比例重審，不將舊 snapshot 冒充新 revision。

| 點時範圍 | Input | Cached input | Output | Total | 計量 thread count |
| --- | ---: | ---: | ---: | ---: | ---: |
| #310 scan-associated；本任務仍進行中 | 5,776,444 | 5,481,344 | 26,013 | 5,802,457 | 3 |

工具標記仍為 `source=codex_rollout`、`coverage=complete`。不得把 count 3 當作本任務
完整父子 lineage；本任務另有獨立 source/deep review、mechanical config preflight
及 security discovery。歷史與當前均未提供可靠增量／繼承邊界，不相加，也不以
#310 此時的數字低於部分歷史 scan 推論節省率。官方隔離 runtime 建置、FTS5
依賴修正、結果分類返工、測試命名／package／scan schema 修正與當時未完成人工驗收
都属于本任務階段差異；沒有逐階段 tokens 時保持 unknown，不剔除返工。

#310 新增正式 operator、root 首用／綁定、runtime/source/storage qualification；歷史
包多為固定 synthetic pilot。現有資料可看出 coverage 補齊與返工會增加被計量階段，
cached input 在這些樣本中占比高；不能據此判斷少開 agent、降低 effort 或换主模型
會節省多少。掃描配置 medium → xhigh、scope、工具版本、驗收與 runtime 都有差異。

後續若公開工具或使用者匯出可補足，每 execution 需有 task/stage、父子/fork lineage、
時間與時區、requested/resolved model、effort/speed/runtime、input/cached/output、
incremental/cumulative 標記與計量邊界、估算 credits 和實際扣量來源。先去除繼承與
cumulative 重複，再按 task/phase 比較，包含失敗、返工、未完成及必要資格工作。
資料不足不阻止產品開發，也不建立背景蒐集或大型觀測系統。

2026-09-30 actor 比例重審 scan `ee723513-212d-4c5b-a0d9-29ec774047a7`
已封存，12 production files 覆蓋、0 findings。公開工具返回 input 8,072,833、
cached input 7,843,968、output 28,187、total 8,101,020、thread count 2。
這仍是 scan-associated 累積點時數值，與前次／歷史可能重疊，不相加，也不作
本次 agent 授權修改的增量成本或完整任務 credits。resolved model、實際扣量與
逐階段增量仍為 unknown。正式五操作與停用已完成，證據見
[驗證紀錄](plans/issue-310-verification.md)。
