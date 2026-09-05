# 外部記憶治理設計研究

## 研究範圍與可信程度

此研究屬 [Issue #212](https://github.com/jeffery777/codex-dev-skills/issues/212)
的 docs-only 交付，不授權外部系統整合或功能實作。

2026-09-05 以官方文件及公開原始碼進行唯讀研究，供
[MG1 規格](memory-governance-milestone.md)決策。本次沒有安裝、連接或實測
外部記憶服務，沒有提供私人資料，也不構成採用任何外部 backend 的決定。
Mem0 OSS 原始碼固定於 `dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3`；
官方網頁為查閱日的內容，後續可能改變，實作前應核對所選版本。

本次依後續要求另比較微軟相關的 Memora 與 PlugMem。
[Microsoft Research 的 Memora 介紹](https://www.microsoft.com/en-us/research/blog/memora-a-harmonic-memory-representation-balancing-abstraction-and-specificity/)
連至 `microsoft/Memora`；
[PlugMem 的官方研究頁](https://www.microsoft.com/en-us/research/publication/plugmem-a-task-agnostic-plugin-memory-module-for-llm-agents/)
連至合作研究 repository `TIMAN-group/PlugMem`，不是其他同名套件。
兩者分別固定於 `dec3f8f2444eace7004fc084abe1be9f3d88270e` 與
`3b2ce75257d40bca8fac3f78e54e22ea41d92529`。
這不是確認使用者原先記得哪一個名稱，而是依其同意比較兩個候選。

「文件有功能」「原始碼可見行為」「本專案採用建議」分別列出。
API 的 delete 成功、搜尋找不到及有 history，都不能自行推出全副本清除、
跨儲存原子性、可復原或固定容量。以下是設計比較，不是對供應者的完整安全審計。

## Mem0：管理操作、歷史及保留

| 來源與層次 | 查得事實 | MG1 借鑑或需補足之處 |
| --- | --- | --- |
| [Update 文件](https://docs.mem0.ai/core-concepts/memory-operations/update)，Platform／OSS 分列 | 提供按 memory ID 修改內容的操作，要求再確認更新結果；部分能力因產品／SDK 不同。 | 人類的「修改」可直接是管理操作，不必將保留歷史包裝成第二條獨立記憶。 |
| [OSS main.py](https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/mem0/memory/main.py#L1909)，原始碼 | `_delete_memory` 先刪 vector，再把 `prev_value` 原文寫入 DELETE history；entity 清理容許 non-fatal 失敗。可見呼叫沒有共同交易。 | 單筆刪除不等於原文消失；本機新核心採同一交易域並驗證衍生資料。此結論不外推至 Platform。 |
| [OSS storage.py](https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/mem0/memory/storage.py#L138)，原始碼 | history 保存 old/new 原文，`get_history` 按 ID 讀取而不先查主記憶；交易只涵蓋自己的 SQLite。另有獨立 messages 表。 | 把內容版本與操作證明分開；清除須涵蓋歷史全文，不能為稽核永久保留原文。 |
| [Platform 遷移說明](https://docs.mem0.ai/migration/platform-v2-to-v3)，新版擷取流程 | 新 extraction 採 ADD-only；官方明說記憶數會累積，建議用到期或刪除管理數量。 | 不照搬永久累積；擷取策略不是完整容量策略，也不等於取消明確 update/delete API。 |
| [Get Memories](https://docs.mem0.ai/api-reference/memory/get-memories)，Platform v3 API | 有 identity filters、page/page_size 及 count/next/previous/results。頁面未保證跨頁同一快照。 | 借鑑獨立列舉；另外定義快照完整性、生命週期涵蓋及截斷。 |
| [Memory Expiration](https://docs.mem0.ai/platform/features/memory-expiration)，官方說明 | 到期使 search/get_all 預設不顯示，內容仍存在，按 ID 可讀，清除日期可恢復。 | 可借鑑停止使用與恢復的語意；到期不等於釋放容量。 |
| [Memory History](https://docs.mem0.ai/api-reference/memory/history-memory)，Platform API | history 格式可包含 ADD/UPDATE/DELETE、old/new memory 與 input。文件未交代 delete 後全部副本及備份的清除承諾。 | 歷史可能也是敏感原文存放處；Platform 清除完整性仍屬未驗證。 |

原始碼補充：同一 pinned `main.py` 的 `get_all` 預設 `top_k=20`，不能把名稱
當作完整列舉承諾；`_update_memory` 分別改 vector 與 history。這些有限觀察不表示
所有後端都沒有自身交易，也不表示 Platform 與 OSS 內部相同。

版本注意：較舊介紹常把新增時的 ADD／UPDATE／DELETE／NOOP 決策當作 Mem0
統一架構；本次新文件已改變擷取策略。不同讀取可能取得不同頁面修訂或快取，
到期參數也要按 OSS／Platform、SDK 及路由核對，不能由遷移概述推定全部支援或移除。
本規劃不採用未獨立驗證的供應者效果分數或法遵承諾。

## Zep：時間、來源與刪除衍生物

| 來源 | 查得事實 | MG1 借鑑或需補足之處 |
| --- | --- | --- |
| [Facts](https://help.getzep.com/facts)，官方文件 | 分別記錄事實何時有效／失效及系統何時得知資訊改變。 | 不把建立時間、最後驗證時間與失效時間混為一談；矛盾／替代要列來源與時間。 |
| [Deleting Data from the Graph](https://help.getzep.com/deleting-data-from-the-graph)，官方文件 | 刪 episode 時依共享來源關係保留部分 nodes/edges；共用節點名稱或摘要不一定重算，可能仍含已刪來源資訊。刪除造成失效的來源也不會自動恢復舊事實。 | 清除需列出來源到衍生物關係，且「刪除更正」不等於「舊資料恢復可信」。 |
| [Reading Data from the Graph](https://help.getzep.com/reading-data-from-the-graph)，官方文件 | 列表與 search 分開，按 graph/user、過濾條件、排序及 cursor 列舉。 | audit 要有完整性欄位，不能把相關性查詢當整體清單。 |

Zep 的產品文件與 Graphiti OSS 有版本及 runtime 差異，本次不將兩者當同一
實作證據。也不照搬 graph topology；本專案只有結構化本機記憶時，明確的版本／
來源關係就足夠。若日後加入共用摘要、圖或向量儲存，必須重做刪除集合與部分失敗設計。

## Letta：使用關係與管理入口

[Letta V1 archival memory](https://docs.letta.com/v1-sdk/memory/archival-memory)
區分 agent 日常 insert/search 與開發者的管理操作；此頁屬 V1 SDK 說明，
不推定新版所有 agent 都有相同權限。
[Detach Archive](https://docs.letta.com/api/resources/agents/subresources/archives/methods/detach)
與[Delete Passage](https://docs.letta.com/api/resources/agents/subresources/passages/methods/delete)
是不同介面。可借鑑「某個 agent 不再使用」與「移除資料」的概念分離，
不能據此推定本專案已有共享 archive 或 Letta 保證媒體層抹除。

## Memora：內容、主題與檢索線索分離

| 來源與層次 | 查得事實 | MG1 借鑑或需補足之處 |
| --- | --- | --- |
| [固定版 README](https://github.com/microsoft/Memora/blob/dec3f8f2444eace7004fc084abe1be9f3d88270e/README.md)，架構說明 | 記憶由完整 value、主要 abstraction 與 cue anchors 組成；索引摘要及線索，保留內容細節，相關更新可歸入同一項目。 | 分開管理「實際保存的內容」與「找回內容的入口」；不必引入向量服務才能採用這個概念。 |
| [論文 v2](https://arxiv.org/html/2602.03315v2)，方法與實驗 | 以摘要匹配及模型判斷選擇新增／更新；檢索可重新查詢、沿 cue 擴展、停止。實驗比較長對話回答品質、建構成本與檢索成本。 | 語意相近只形成修改候選，不能代替範圍／來源／人類確認；研究中的 token 或項目數改善不是本專案的磁碟容量與刪除保證。 |
| [memory_builder.py](https://github.com/microsoft/Memora/blob/dec3f8f2444eace7004fc084abe1be9f3d88270e/src/memora/builder/memory_builder.py#L530)，更新路徑 | 先刪舊項目，再產生 cue、組 history、加入新項目；此呼叫鏈未形成共同交易。 | 借鑑同主題整理，但不照搬先刪再生成；本機新 revision、檢索入口及 receipt 同一交易切換。 |
| [utils/memory.py](https://github.com/microsoft/Memora/blob/dec3f8f2444eace7004fc084abe1be9f3d88270e/src/memora/utils/memory.py#L139)，history 建立 | 每次更新將新 value 加入既有 history；此函式沒有數量、期限或 byte 裁剪。 | 合併項目不等於內容總量不成長；計量目前正文、歷史與索引，保留界限仍需另定。 |
| [core/memory.py](https://github.com/microsoft/Memora/blob/dec3f8f2444eace7004fc084abe1be9f3d88270e/src/memora/core/memory.py#L679)，primary 刪除 | 移除該 primary 與 cue 的關係；共享 cue 尚有其他 primary 時保留，無引用才刪。此路徑未沿 episodic_memory_ids 清除來源事件。 | 借鑑依引用關係清理；primary 消失不代表原始事件及其他副本已清。MG1 首版不加入原始對話或共享 cue 圖。 |
| [local_memory_store.py](https://github.com/microsoft/Memora/blob/dec3f8f2444eace7004fc084abe1be9f3d88270e/src/memora/core/local_memory_store.py#L340)，local store | 單筆 get/delete 使用 collection 與 key；各操作由程序內 RLock 包覆，不能據此推出跨步驟或跨程序原子性。 | 核心需以實際交易及 scope 證據驗證；不能用 Python lock 或 collection 名稱替代。 |

Memora 對本專案最有價值的是記憶表示方式，而非直接移植全部自動 ingestion、
ChromaDB／Redis、額外 LLM 或 GRPO 流程。本次未執行它的測試、模型或 benchmark；
沒有驗證媒體層清除、固定磁碟預算或完整多使用者隔離。
README 的完整生命週期概述不能代替這些個別驗證。

## PlugMem：從互動經驗到事實與方法

| 來源與層次 | 查得事實 | MG1 借鑑或需補足之處 |
| --- | --- | --- |
| [微軟研究介紹](https://www.microsoft.com/en-us/research/blog/from-raw-interaction-to-reusable-knowledge-rethinking-memory-for-ai-agents/)，研究目標 | 將互動整理為事實與可重用方法，依任務檢索並整理成精簡知識；研究評估效用與 context 消耗。 | 借鑑保存可重用知識而非全部軌跡；效用指標仍需本專案合成任務驗證。 |
| [coding 設計](https://github.com/TIMAN-group/PlugMem/blob/3b2ce75257d40bca8fac3f78e54e22ea41d92529/design_docs/plugmem_for_coding.md#L79)，設計文件 | 區分 semantic／procedural／episodic；提議 coding 預設不保存完整事件，人工維護的專案指引在衝突時仍優先。列出五種 promotion signals。 | 事實、方法、事件的保留需求不同；設計的五種訊號不是已驗證實作能力，更不是本專案的人類授權。 |
| [promotion.ts](https://github.com/TIMAN-group/PlugMem/blob/3b2ce75257d40bca8fac3f78e54e22ea41d92529/plugmem-coding-core/src/promotion.ts#L21) 與 [core.ts](https://github.com/TIMAN-group/PlugMem/blob/3b2ce75257d40bca8fac3f78e54e22ea41d92529/plugmem-coding-core/src/core.ts#L224)，coding 實作 | detector 定義 failure_delta／correction；SessionEnd／PreCompact 會把候選交給 extract，再呼叫 insertMemories，未加入逐筆人類預覽確認。 | 可借鑑候選階段，不能把 pattern、模型 confidence 或一次成功當保存許可；偵測窗口上限不是持久記憶預算。 |
| [memory_graph.py](https://github.com/TIMAN-group/PlugMem/blob/3b2ce75257d40bca8fac3f78e54e22ea41d92529/plugmem/core/memory_graph.py#L1298)，Chroma 服務核心 | merge 建立新 semantic 節點並連結來源；consolidation 可將舊節點 is_active=False。 | 整理知識不等於清除原文；多次儲存呼叫不能視為同一原子修改。 |
| [inspector.py](https://github.com/TIMAN-group/PlugMem/blob/3b2ce75257d40bca8fac3f78e54e22ea41d92529/plugmem/api/routes/inspector.py#L170)，盤點介面 | 可包含 inactive、回報符合總數及有限清單，另讀單筆與關聯；PATCH 只改 is_active。 | 借鑑完整數量、截斷提示及來源視圖；不能把該 PATCH 說成全文修改或逐筆內容清除。 |
| [chroma.py](https://github.com/TIMAN-group/PlugMem/blob/3b2ce75257d40bca8fac3f78e54e22ea41d92529/plugmem/storage/chroma.py#L83)，持久層 | delete_graph 逐一刪 collections 並略過例外；episodic 保存 observation/action，recall audit 另存 observation/goal/state；stats 主要計數節點。 | 成功回覆不足證明所有受管理內容清除；需逐面向結果與 byte 計量。檢索紀錄也可能是原文副本。 |

研究核心 `src/`、Chroma 服務核心 `plugmem/`、coding core 與既有 OpenClaw
插件不可混為同一功能面。特別是
[OpenClaw config](https://github.com/TIMAN-group/PlugMem/blob/3b2ce75257d40bca8fac3f78e54e22ea41d92529/openclaw-plugmem-plugin/src/config.ts#L27)
預設啟用 autoRemember；
[插件說明](https://github.com/TIMAN-group/PlugMem/blob/3b2ce75257d40bca8fac3f78e54e22ea41d92529/README.md#L167)
描述 reset／compaction 保存 session trajectory，不能用 coding 設計的 episodic-off
推論整個專案都不保存原始互動。本專案不移植這些自動採集及執行入口。

本次未實測 graph 清除、模型抽取、跨程序 cache、Chroma 磁碟回收或外部備份。
指定路徑未提供足以驗證有限全文保留、exact-preview authorization 或整體交易的證據，
這不是宣稱所有分支／部署都沒有相關能力。既有本專案對 PlugMem backend 的排除
維持不變；研究設計不等於取得啟用許可。

## SQLite：內容移除與檔案回收

[VACUUM 官方文件](https://www.sqlite.org/lang_vacuum.html)說明刪除可能只留下可再利用
空白頁，檔案重整才縮小實際大小，而且需要額外空間及寫入鎖。
本專案因此應分開量測 payload、空白頁與磁碟大小。
[secure_delete 官方限制](https://www.sqlite.org/pragma.html#pragma_secure_delete)
明示 FTS shadow tables 可能保留痕跡；單一設定不能代替整體清除驗證。
這些是儲存引擎事實，不是 MG1 已有清除能力的證明。

## 對本專案的結論

### Mem0、Memora 與 PlugMem 的比較框架

| 面向 | Mem0 | Memora | PlugMem | MG1 的取捨 |
| --- | --- | --- | --- | --- |
| 主要借鑑 | 明確 CRUD 與歷史介面 | 完整內容、主題摘要、替代檢索線索分離 | 將經驗整理為事實與可重用方法 | 保留人類易懂的操作，補上有來源的內容表示。 |
| 更新整理 | 依產品／版本區分明確修改與擷取策略 | 相關內容可整併至同一主題，保留 history | 圖中的知識單元可整理、替代或停用 | 同一已確認 identity 原子更新；其他相似內容只列候選。 |
| 刪除與容量 | OSS DELETE history 可留原文；到期非清除 | primary／cue 清理不等於來源事件清除；history 持續追加 | 停用節點、原始事件與 recall audit 必須分開計量與處置 | 明確清除集合、有限歷史、無原文證明及獨立空間回收。 |
| 不直接移植 | 未驗證的 provider 語意 | 自動 ingestion、模型判定即寫入、多儲存／模型依賴 | 自動採集、promote、回想注入及持久原始軌跡 | default-off、manual、精確確認，維持本機單一交易核心。 |

這是依上述固定來源作的設計比較，不是產品排名。兩篇研究的 benchmark
有各自資料集、模型及基準版本；不能拿它們的 Mem0 分數評定目前 Platform／OSS，
也不能由「更少檢索 token／記憶項目」推定「完整磁碟容量有界」。

### 建議採用的共同原則

1. 管理操作採人類能理解的新增／修改／停止／恢復／刪除，工程格式放附錄。
2. 明確讀取 scope 與列舉完整性；記憶內容只形成建議，agent 不自行取得刪除權。
3. 單一本機管理核心保存目前版本、有限舊版與精簡操作證明，減少多儲存交易負擔。
4. 刪除覆蓋受管正文、舊版本與衍生物，保留證明不藏原文；剩餘副本如實列出。
5. 停止使用可逆；內容刪除完成後本系統不能復原；空間回收獨立回報。
6. 對全文、歷史、證明、防重放及維護空間設定預算；達界限先阻止新增，清除仍需確認。
7. 修改／清除／壓縮採新版本契約並重新資格驗證。現行 M1 限制完整保留，
   不用它的 logical delete 名稱掩飾新產品預期。
8. 將確切內容與摘要／檢索線索分開，保持同一 revision；線索不是授權或唯一身分。
9. 方法型知識保留前提、成功證據及失效條件，不把一次成功自動提升為正式規則。
10. 以同一合成任務另量測記憶效益、建構／檢索成本及磁碟 byte，
    不把外部研究成績當本專案完成證據。

以上補足方案屬本專案設計推論，完整 DoD、風險、授權、失敗狀態與交付切片以
[里程碑規格](memory-governance-milestone.md)為準。沒有以「外部系統應該想過」
替代具體來源，也沒有因外部設計不完整而停止提出可審查的解法。
