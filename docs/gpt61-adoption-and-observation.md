# GPT-6.1 採用與部署後觀察

查核日期：2026-09-30。Issue #308 依維護者同意，採官方模型定位與費率作配置
依據；本次不執行模型配對或節省率量測，不宣稱實測品質等價或成本優越。
此文件不是 router 價格函數、候選資格、部署授權或背景監控設定。

## 官方成本與採用理由

官方 [Pricing](https://learn.chatgpt.com/docs/pricing#token-rates) 的 Standard
費率如下（credits / 1M tokens）：

| 模型 | 未快取 input | Cached input | Output |
| --- | ---: | ---: | ---: |
| GPT-5.6 Sol | 100 | 10 | 500 |
| GPT-6 Sol | 50 | 5 | 250 |
| GPT-6.1 Sol | 50 | 2.5 | 250 |
| GPT-6 Astra | 250 | 25 | 1250 |
| GPT-6 Luna | 2.5 | 0.25 | 12.5 |

在相同 token 數與分布下，6.1 相對 5.6 的 input/output 費率低 50%、cached
低 75%；相對本專案先前已採用的 6 Sol，只有 cached 低 50%，其餘同價。
這支持遷移方向，但不能當作工作包或訂閱額度的節省百分比。Codex credit
billing 沒有另收 cache-write；API-key 計價是另一套規則，不混用。

官方 [Speed](https://learn.chatgpt.com/docs/agent-configuration/speed) 區分：
Fast 內含訂閱量為 Standard 的 2.5×，purchased credits／Enterprise pay-as-you-go
為 2×；Astra Ultrafast 分別為 8×／6×。建議日常選 Standard。這些是扣量倍率，
不是整體完成速度倍數。點數單價不能直接換算訂閱內含量、每模型月配額或
Quota 調整的抵銷效果；Work 與 Codex 共用用量，實際限制以當期公開介面為準。

官方 [Models](https://learn.chatgpt.com/docs/models) 建議複雜 coding／agentic
工作優先考慮可用的 6.1 Sol，明確且重複的工作採 Luna，最困難工作保留 Astra。
本次採用結合此定位與上述費率，不以版本號推定能力，也不以低成本降低審查門檻。

## 配置決策

| 角色 | Source model / effort | 邊界 |
| --- | --- | --- |
| mechanical_reader | GPT-6 Luna / low | 保留；機械唯讀。 |
| fast_explorer | GPT-6 Luna / high | 保留；來源探索。 |
| balanced_worker | GPT-6.1 Sol / medium | 有界實作／文件更新。 |
| senior_worker | GPT-6.1 Sol / high | 複雜有界實作。 |
| advanced_worker | GPT-6.1 Sol / medium | 多觸發實作；不可降派 senior-high 冒充 advanced。 |
| routine_reviewer | GPT-6.1 Sol / high | everyday 唯讀審查，不滿足 deep/security。 |
| deep_reviewer | GPT-6 Astra / xhigh | 保留高風險深度審查。 |
| security_reviewer | GPT-6 Astra / xhigh | 保留安全／授權／資料邊界審查。 |
| exceptional_researcher | GPT-6 Astra / xhigh | 保留 quality-first 與分類條件。 |
| astra_advanced_worker | GPT-6 Astra / xhigh | 既有獨立 candidate，仍須資格。 |
| astra_deep_reviewer | GPT-6 Astra / xhigh | 既有獨立 candidate，仍須資格。 |
| astra_security_reviewer | GPT-6 Astra / xhigh | 既有獨立 candidate，仍須資格。 |

27 個 skill 入口仍由實際工作包的 class/tier 決定角色，不逐 skill 增設固定
模型或 agent。一般交付、規劃、續行及 adapter 由主代理整合；實作／文件用
適當 worker；一般 review 用 routine reviewer；高風險首次就走 deep/security。
Gates 整合必要內容與平台證據，不多開模型代替確定性檢查，也不省略獨立審查。
Deprecated aliases 沿用對應共享入口；memory 維持 default-off、空 production
registry 與單次 dispatch 契約。沒有新增自動重試／切模控制器。

可選主代理三鍵配置：

```toml
model = "gpt-6.1-sol"
model_reasoning_effort = "medium"
plan_mode_reasoning_effort = "high"
```

這是專案建議，不是官方對所有人的固定預設。Plan high 適合此專案常見的
跨檔規劃與取捨；一般執行 medium。官方
[config reference](https://learn.chatgpt.com/docs/config-file/config-reference)
只定義 Plan override，未設定時使用該模式內建 preset，不保證繼承一般 effort。
可在後續觀察中比較 Plan high/medium；不直接把 xhigh 設為每次規劃必用。

合併至正確設定層，不覆寫整份個人檔案。6.1 不可用時，主代理明確選可用的
6 Sol-medium；固定子角色則依 preflight/fallback，不偷偷改模型後沿用 digest。
[Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents) 說明 custom
file 的 model/effort 優先於先解析的 spawn/default/parent 設定。改主代理不會
遷移固定子角色。安裝 source 不等於既有對話已重新載入。

速度須在目的端另行確認 Standard；此三鍵不覆寫 speed，不杜撰通用的
`service_tier = "standard"`。CLI `/fast` 是 toggle，先看狀態，不盲切。
CLI、Desktop 與 SSH 目的端分開查核；既有 Desktop 對話可能仍載入舊
Sol mapping，不能因 source 已改就聲稱當前 custom role 已是 6.1。

## 部署後的兩階段評估

先完成已授權的發布／部署與 installed-byte 讀回，再開始觀察；本次文件不
自行啟動排程、背景蒐集、私人 session/log/SQLite 讀取或 qualification store。
使用者後續選定工作範圍與觀察期間後，以任務執行時的公開控制介面及核准
紀錄取得證據。共享 repo 只放去識別的彙總，不放私人對話或機器 runtime 狀態。

第一階段固定新模型與原 effort，涵蓋有代表性的實作、文件、探索、一般與
高風險審查。期間長度不足以代表覆蓋率；沒有遇到的角色標記未觀測。
每個工作包記錄：

- 任務類型、風險與驗收，預期 class/tier/role；部署來源與 profile digest。
- runtime、requested model/effort/speed、公開介面觀測的實際值與來源；
  只看到 request/config 時不能當成 resolved-model attestation，缺值用 unknown。
- route、fallback 及原因、整合驗收、未完成與失敗、修正 lineage、誤報／漏報。
- 完成時間與可取得的用量，含父／子代理、失敗／返工／整合；未知用量不算零。

分別判斷路由是否符合預期、任務是否通過必要驗收。子代理自報、工具成功與
測試 PASS 不取代完整完成條件；路由偏差先修復，不急著調低 effort。

第二階段只選一類低風險、可客觀驗收的工作調低 effort，例如 routine docs
review high → medium；模型、速度、工具／指令、驗收與任務難度分組保持可比。
固定 profile 的 effort 變更必須走正常 source/digest/驗證流程，不偷偷覆寫並
沿用舊資格；本次尚未實施降低。以相近任務比較完成率、返工、漏報、時間與
完整工作包用量，保留失敗與未完成，不只比整週用量或 finding 數。

降低後若出現 blocker 漏報、false completion、越權，或返工抵銷收益，停止
該低 effort 試驗並依已核准範圍恢復基準，重新讀回配置。Deep/security 的
降低另行評估，不從 routine 結果外推；沒有足夠樣本就保持未定，不宣稱通用等價。
