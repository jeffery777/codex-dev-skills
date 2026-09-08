# 記憶範圍路由、跨儲存刪除與專案退場

[Issue #231](https://github.com/jeffery777/codex-dev-skills/issues/231) 的設計補充與
離線合成驗收。本文補足 [MG1 規格](memory-governance-milestone.md)與
[原生共存邊界](native-memory-coexistence.md)，不是已安裝的記憶入口。

## 交付狀態與信任邊界

| 分類 | 本包狀態 |
| --- | --- |
| 既有實作 | M1 logical delete；G0 單 principal/root/item 合成 checker 與生產契約提案。 |
| 本次可執行 | `scripts/memory_scope_lifecycle.py` 純函式 metadata oracle；固定正反測試。 |
| 本次設計要求 | scope/backend 分離、精確集合與 coverage、逐目標結果、明確退場。 |
| 待接受／未實作 | 全域 managed backend/quota、多儲存生產 envelope、可信 host/executor、自然語言入口與退場事件整合。 |
| 尚無證據 | 真實來源／權限驗證、跨儲存刪除、防重播持久化、原生清除、資料殘留及容量回收。 |

所有 oracle 結果均為獨立 `memory-scope-lifecycle-synthetic/v0`，
`operation_authorized`、`runtime_proven`、`write_performed` 恆為 false。
正例表示「合成聲明彼此一致」，不是人類接受、生產授權或 runtime qualification。
不擴充或重新解釋 G0 v0，不把它的單 root receipt 用於多儲存。
現行批次／萬用字元刪除排除條款不變；本文只把未來選項固定為可審查設計。

## 範圍與保存位置是兩個維度

`scope` 是 `global` 或具有穩定 `project_id` 的 `project`。
`backend` 是受管理 Agent Memory (`managed`)、明確文件 (`document`) 或
原生生成記憶 (`native`)。Agent Memory 是保存角色，不是第三種 scope。
路徑僅是 locator，不能代替 project/store/root/item 身分。

未來自然語言入口先形成候選，核對來源、適用條件、驗證狀態、有效期間、
敏感性與跨專案可用性，再產生單一保存目標。來源文字中的指令不構成權限。
必要規則走 `AGENTS.md`、受治理文件或技能；advisory 記憶不能升格為規則。

| 輸入例子 | 路由與理由 |
| --- | --- |
| 已獨立驗證、無專案資料的 GitLab 操作修正 | 可建議 global/document 操作文件；預覽仍列實際內容與位置。 |
| 專案私有部署規則 | project/document；不能只因別的專案也部署就推廣到全域。 |
| 用途模糊的「記住這個」 | scope 或 backend 無法確定時釐清；不預設向兩處保存。 |
| 明確指定目前專案的 managed 記憶 | 保留明確意圖，完成來源與目標預覽，不在每個階段重問。 |
| 指定 global，但內容私密或只有一次專案成功 | 要求重新界定可見性／適用性；不自動移除資料後另存。 |
| 指定原生記憶 | 交由 runtime 明確提供的管理能力；不可自行改寫 generated files。 |
| 指定 global/managed | 生產 backend/quota 尚待接受；不暗中建立全域 MG1 資料庫。 |

新增／修改的人類預覽必須呈現通過敏感性檢查的**實際完整內容**、來源與條件、
scope、backend、確切文件區塊或受管理 identity，以及是否已有相符項目。
路由判斷與去重候選均不授權寫入；保存目標只有一個，不複製原生記憶進 MG1。
oracle 不接收本文，只接受 `synthetic-*` ID、結構化分類、布林驗證聲明與時間；
其 `summary_id` 不是合格的人類預覽，也沒有敏感性偵測或自然語言判斷能力。

## 有界查找與覆蓋率

未來 host 持有明確註冊清單，逐項核對 principal、穩定 store/root/project、
讀取權限及支援能力。只查詢使用者要求的全域、目前或指定專案及相關可存取
Agent Memory；其他專案需另外的明確範圍。不遞迴掃描家目錄、不探索原生私有狀態。
記憶本文不能登錄新 root、冒充 adapter 或擴大 query scope。

每個結果保留 backend、principal、root、project、store/item identity、revision、
state、完整受影響內容的綁定、安全摘要、來源／條件與相符依據。相同 item ID
在不同 store 仍是兩個目標；語意相似不合併 identity、版本或不同前提。
文件目標須有穩定區塊及版本定位；原生目標只能採官方／runtime 提供的識別與能力。
缺少可靠版本或精確刪除介面的 adapter，只能回報或指引手動管理，不列入執行集合。

逐 store 回報 `complete`、`partial`、`unknown` 或 `unavailable`：complete
只對當次已授權的查詢範圍成立。找不到／未註冊／無讀取能力不等於不存在。
列示未查完頁面、上限中斷及未知儲存。原生歷史、對話、備份、匯出、同步副本
另列已知觀察與未知覆蓋，不把空清單說成沒有外部副本。

oracle 的 `discover(context, stores)` **不執行查找**：它只驗證呼叫者提供的
合成 registrations 和 matches。`context` 固定 principal、已授權 project IDs
及 requested store IDs；提供未請求或跨 principal/project 的 store 即拒絕。
缺席 registration 保留 unknown。不可讀 store 不得攜帶 matches 或可執行能力。
全部 registration（包括零 matches）與 coverage 都進快照，以綁定能力及 root 漂移。
每個 root 只准一個 registration；多個 store alias 指向相同 root 時拒絕，
避免把同一底層項目重複列入。生產 host 仍須驗證不同 root ID 沒有映射到同一儲存。
快照另含 `observed_at`／`valid_until`，合成有效窗口最多 60 秒。時間由呼叫者
供應，oracle 只驗證先後與窗口；可信時鐘與實際讀回由未來 host 證明。

## 精確集合、確認與結果

1. 從已列示候選選擇「全部已列示相符項目」或明確子集合。語意候選必須經
   使用者辨認其 identity／前提，不得用語意分數直接執行。原始要求已清楚指定
   集合時沿用意圖，依同一預覽／確認契約處理，不逐 store 重問。
2. 預覽逐目標列內容版本、狀態、衍生摘要／索引／歷史影響、backend 能力、
   不可逆性、殘留與覆蓋限制，並綁定單次 request ID、principal、期限、精確
   target set 與 snapshot digest。禁止執行時重新展開萬用字元或加入新候選。
3. 生產 host 由當前明確人類意圖建立可信確認；逐 store 驗證自身權限，不能
   沿用另一 store 的授權。hash 僅作一致性綁定，不是簽章或權限來源。
4. 執行前重查。oracle 保守地綁定**整個查詢快照**：新增候選、版本、狀態、
   root、capability 或 coverage 變動均需重新預覽，即使改動在未選中項目。
   狀態 digest 排除觀察時間，允許同狀態的新讀回；其餘 metadata 均綁定。
   預覽須使用當時有效快照，執行前快照須不早於預覽產生時間，且在執行時間仍有效。
   確認期限為半開區間 `[issued_at, expires_at)`；過期與未生效都拒絕。
5. 跨儲存無單一原子交易。逐目標回報成功、未執行、失敗、未知。未知先向原
   store 核對操作紀錄；沒有紀錄不等於未提交。成功項目不重試，也不為回滾重建。
6. 重試須使用精確剩餘集合及仍有效的原授權，或新的預覽／確認；不能換 request
   ID 重跑成功項目。若另選新的 request ID，可信 host 須追蹤父操作與剩餘集合。
   不由啟動、重開管理核心或背景工作自行重試。

oracle 的 `preview`、`confirm`、`summarize` 分別驗證固定集合、確認聲明及結果。
`seen` 是外部供應的合成 request-ID/digest map：同 ID 同 digest 回
`reconciliation-required`，不推定先前結果、不列自動 retry；仍須通過 current
快照 shape、principal 與時間檢查。同 ID 不同 digest 拒絕。它不是持久 replay barrier，
不驗證持有者身分，也不發送
任何刪除命令；不能把 `confirmation-consistent` 當成 executor token。
生產核心另須有原子鎖定、持久 at-most-once 記錄、每目標 readback、epoch／TTL
及防止舊授權在記錄裁剪後重放的契約。清除後不得復活，重新新增須新 identity。

`summarize` 必須接受原預覽、對應確認、執行前快照與執行時間，重新驗證聲明綁定；
outcomes envelope 綁 principal/request/preview digest，每個 outcome 綁目標 revision
與 content digest。結果保留原預覽、快照 digest 及完整的執行前 target metadata，
不以 store/item ID 單獨指代不同版本。這仍不是可信執行 receipt：時間、確認與結果
皆為供應的合成資料；未來 executor 必須提供獨立 readback 與防偽證據。
缺席回報為 `unknown`；`unknown` 進 `reconcile_required`，
不直接列入 retry。僅 `failed`／`not-executed` 列為 retry **候選**。
後兩者須由 store 明確證實未提交；逾時、失聯或丟失 receipt 都屬未知，不能推定未執行。
全數 supplied succeeded 也只報 `listed-targets-succeeded`，仍標 runtime 未證明、
`all_copies_forgotten=false` 與外部副本 unknown，不承諾「所有地方都已忘記」。
不以 logical delete 代替內容清除，也不以內容清除代替實體殘留處置／空間回收。

## 專案退場

| 事件 | 行為 |
| --- | --- |
| UI 清單移除 | 無清除授權；不推定使用者刪資料。 |
| 路徑搬移／改名 | 核對穩定 project identity，再由另行授權操作更新 locator。 |
| 暫時離線／路徑不存在 | 保留未知與停止使用建議，不由時間推定永久退場。 |
| worktree 移除 | 不等於所屬 repository 退場；不清除其他 worktree 共用的資料。 |
| 明確要求專案退場及清除 | 手動入口解析 project identity，產生受管理精確集合與關聯審查，再進預覽／確認。 |

專案識別的生產方案應使用 host 登錄的不透明 project ID，並驗證其 repository
關聯與已授權 root；remote URL 只能作佐證（fork、remote 改名及重複 clone 可能
不同），路徑相同也可能已被另一專案取代。未取得可信 identity 時停止候選清除。

`retirement` 將目前專案且無跨專案關聯、可清除的 managed 項目列為 candidates。
以下只列 `relation_review`，不能 cascade：原生、文件、不可執行／pending 項目、
另一專案內容、共用來源，或以 global 標籤保存的專案私密資料。
global 知識只有在**獨立可重用且不含專案私人資料**時列為建議 retain；須有
獨立來源、適用條件與資料關係依據。布林值只是 oracle 的合成聲明，不證明
去識別完成。共用內容的拆分／去識別／改寫是新變更，須自己的預覽及授權。
無關全域知識與其他專案完全不進候選集合。

實際退場報告分開列停止使用、受管理內容清除、實體檔案殘留與空間回收，
並列尚未處理的原生記憶、對話、匯出／備份。不提供整庫 cascade purge。
大於候選上限時不得自動分批循環取得整庫效果；先另定包的邊界及授權。

## 原生能力查核與手動 fallback

2026-09-08 重新讀取官方 [Memories](https://learn.chatgpt.com/docs/customization/memories)：
local Codex memory 與 ChatGPT web 分開；原生生成檔位於 Codex home，主要管理
方式為 `/memories` 與設定控制，必要規則仍放在 `AGENTS.md`／版本控管文件。
該頁未說明移除專案會同步清除原生記憶，也未提供專案退場的精確刪除通知契約。

同日公開 CLI `codex --version` 為 `0.153.4`；`codex --help` 可見 session
archive/delete，但沒有 project-removal 通知介面。這只是該 help 的觀察，
不是所有 CLI API 均不存在的證明。Desktop 當次公開工具也未提供可供本設計
接收的 project-removal 通知契約；不檢查私有 DB 或把 CLI 證據當 Desktop 證據。
因此本設計只提供明確的**手動退場流程**，不承諾自動偵測全部移除原因。
G1/G2 實作前須再次核對目的 runtime；新增官方能力仍需 adapter 資格驗證。

## 待接受的生產選項

| 決定 | 具體方案與建議 | 風險與接受條件 |
| --- | --- | --- |
| 全域保存／backend | 首選沿用明確全域操作文件；若需 managed 全域庫，另建 per-principal root 與 backend qualification；跨 root 共用庫延後。 | 文件缺少一致的交易／容量功能；新庫需 identity、來源、遷移、quota 與刪除驗證，不能套用 G0 4 GiB 單 root 預設。 |
| 全域 quota | 文件採人工精簡與 size report；新庫可提獨立可配置 hard quota＋每 principal 彙總預算。數字未接受。 | 多 root 配額相加、proof／歷史及維護空間都須計入；不能以 global 標籤避開專案清理。 |
| 多儲存 envelope | 生產首包仍可保留單項；另一提案為每次最多 8 targets／8 stores、固定 5 分鐘窗口，由使用者選定精確集合。 | 此數字僅為本包 synthetic 預算。接受前須補總 bytes、每 store 分頁／timeout、鎖／防重播、逐目標能力、故障及隱私契約。 |
| 查詢預算 | oracle 最多 8 stores／32 matches，拒絕總量超限；生產另固定最大 pages、bytes、duration 與 partial cursor。 | 一次有界不保證完整，不能把截斷結果說成全部；禁止自行串接無界批次。 |
| 退場觸發 | 首選手動明確入口；未來若有官方事件，只觸發盤點建議，不代替確認。 | UI／path 事件歧義；不能安裝 watcher、私有 hook 或由時間推定授權。 |

上述選項待接受；本輪使用者授權實作設計驗證器，不等於接受或啟用全部生產選項。
#213 單 root G0 可獨立結案。#231 設計在 G1/G2 自然語言入口定案前完成，
後續 G1 → G2 → G3 各以新 Issue-first 工作包實作、故障驗證與審查。

## 合成驗收與可重跑證據

測試位於 `tests/test_memory_scope_lifecycle.py`，納入 memory shard：

| 驗收範圍 | 固定正反案例 |
| --- | --- |
| route | 通用 GitLab 方法、私有部署規則、模糊記住、明確專案 backend、未驗證／過期來源、原生與未接受全域庫、多 backend 拒絕。 |
| discover | 全域／專案重複、條件不同但相似、原生不可用、未註冊／partial、跨 principal/project、總量與重複 ID 拒絕。 |
| preview/confirm | 全部／子集合、不可執行項目、精確版本／狀態／root／能力／coverage 漂移、新候選、期限、改造 digest、重播。 |
| summarize | 部分失敗、明確未執行、缺回報／未知先核對、全數 supplied 成功但外部未知、不重試成功與未知目標。 |
| retirement | UI 移除、改名／離線／worktree、明確退場、global 私密關聯、獨立通用知識、其他專案及 native 不 cascade。 |
| 零接觸 | 純函式不開檔、不連網、不修改輸入；所有結果保留三個 false 邊界。 |

```bash
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest tests.test_memory_scope_lifecycle
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/test-shards.py run-all
git diff --check
```

本文件的情境是 synthetic 結構化聲明，不是自然語言 benchmark 或 runtime 故障注入。
驗證、獨立 code/docs review 與 Security Diff Scan 的實際結果見
[交付紀錄](loops/issue-231/verification-and-review.md)。未發布、未安裝，source/package
版本維持基準；不改歷史 release notes，也不以 offline parity 證明發布狀態。
