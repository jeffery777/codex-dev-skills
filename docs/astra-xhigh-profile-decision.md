# Astra／xhigh 配置決策與回復紀錄

決策日期：2026-09-11。追蹤：[Issue #249](https://github.com/jeffery777/codex-dev-skills/issues/249)。

維護者明確要求將人工調整納入 repository，並把舊設定保留為 TOML 註解。
此次採用依據是維護者在實際工作中觀察到 xhigh 可能減少補充輪次與週額度
消耗；這是配置選擇與待驗證假設，不是跨模型成本或品質的測量結論。

## 配置矩陣

| Role | 上一版 model／effort | 本次有效 model／effort | 路由身分 |
| --- | --- | --- | --- |
| `loop_v2a_deep_reviewer` | `gpt-5.6-sol`／`high` | `gpt-6-astra`／`xhigh` | baseline，deep |
| `loop_v2a_security_reviewer` | `gpt-5.6-sol`／`high` | `gpt-6-astra`／`xhigh` | baseline，deep |
| `loop_v2a_exceptional_researcher` | `gpt-5.6-sol`／`xhigh` | `gpt-6-astra`／`xhigh` | baseline，exceptional |
| `loop_v2a_astra_advanced_worker` | `gpt-6-astra`／`medium` | `gpt-6-astra`／`xhigh` | candidate，advanced |
| `loop_v2a_astra_deep_reviewer` | `gpt-6-astra`／`high` | `gpt-6-astra`／`xhigh` | candidate，deep |
| `loop_v2a_astra_security_reviewer` | `gpt-6-astra`／`high` | `gpt-6-astra`／`xhigh` | candidate，deep |

其餘五個 baseline、main-agent 範例、角色名稱、class／tier、sandbox、權限與
候選資格流程維持原樣。security baseline 在人工版本中沒有有效的 effort key；
本次依 Astra／xhigh 方向明確設為 xhigh，保留 canonical 上一版 high 作回復值。
未改變的 key 不另留重複註解；例：exceptional 原本就使用 xhigh。

## 已知證據與限制

- 九個歷史任務樣本包含不同工作量、未完成驗收及權限／環境／流程往返。
  缺少兩段期間的週額度起訖快照、逐任務有效 model／effort 與完整重疊用量，
  無法量化 xhigh 的節省比例，也不能用根回合數當作模型推理或失敗重試次數。
- 官方 [Astra 指引](https://developers.openai.com/api/docs/guides/latest-model)
  支持按代表性任務比較完成成本；[訂閱用量說明](https://learn.chatgpt.com/docs/pricing#what-are-the-usage-limits-for-my-plan)
  不提供本帳號從 API token 價格換算週額度的公式。不可混用兩種成本指標。
- Canonical profile 與 registry digest 的一致性只證明配置契約。原 medium/high
  資格只適用於原 profile bytes；不得改寫歷史 pilot、qualification store 或其
  digest 來宣稱新的 xhigh 候選已合格。安裝亦不代表 runtime 已載入或品質合格。
- baseline 的本次採用來自維護者明確決策；三個 candidate 的 opt-in 與精確
  digest 資格仍保留。模型／effort 相同不使兩個不同 role 的資格互通。

## 後續追蹤

Owner：專案維護者。當官方更新模型行為／支援 effort／額度規則，或出現可重現
的品質退步、漏報、過度澄清或任務額度增加時，開啟重新評估；不自動回復設定。

比較時分開主代理、worker、reviewer、security 與 explorer，固定同範圍及 DoD、
來源版本、工具與權限，記錄實際載入的 profile digest、model／effort、Fast 狀態、
成功與缺陷、修正／人工介入、elapsed、開始／結束週 bucket 和 reset 時間。
標示平行任務與缺值，較大的成對工作包可減少整數百分比誤差；不把時間長短或
token 單價當作單獨的決策依據。本次不建立監控或啟動新的效能 benchmark。

## 回復程序

1. 先核對新證據、確切角色及目標 runtime，再以新 Issue／分支記錄回復決定。
2. 將選定 TOML 的目前有效 model／effort 移除或改成有日期說明的註解，再啟用
   表格中的舊值；每個 key 僅保留一個有效值。不得只新增第二個同名 key。
3. 重新計算 registry 的 profile SHA-256、有效 mapping 與驗證日期，同步活躍
   文件、相關契約測試與 generated package，執行驗證及獨立審查。
4. 分別確認是否有適用且新鮮的資格證據；回復舊文字不會自動恢復已失效或
   runtime／scope 不符的資格。正式安裝須另依授權及 installer 預覽／備份程序。

保留的註解只是可檢閱的回復來源，不會被 TOML parser 執行。本次 repository
更新不覆寫使用者個人設定、不部署、不更新或啟用任何資格 store。
