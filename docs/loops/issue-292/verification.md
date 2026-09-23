# Issue #292 驗證紀錄

此紀錄區分離線契約、合成模型行為、審查與平台狀態；尚未完成項目不當成 PASS。
範圍僅本 repository；不含外部專案來源、URL、附件或環境資料。

## 配置與來源

- 9 baseline + 3 既有 Astra candidates；五個既有日常 profiles 遷移 GPT-6，
  新增 everyday/read-only Sol-high reviewer。Astra 六個既有檔案維持原 bytes。
- Current builder revision 為 `v2-2026-09-23`；無 revision 與 `v2-2026-09-06`
  以凍結語意驗證，不授權新 dispatch。舊 source/profile digest 不能冒充當前安裝。
- 全域規範仍為 46 行，SHA-256
  `617e1982326869b4d0aebb7303a4d754bd75292494d18de02be54d72c6a4a10c`；未修改。
- Python resolver 選定 3.12.9、PyYAML 6.0.3。只有已授權的 fresh ephemeral CLI
  合成 runs 使用網路模型服務；普通 repository validation 維持 offline。

## 六角色 CLI acceptance

[可重現 harness 與點時結果](pilot/README.md) 保存 request、fixture/profile hashes、
原始事件 digest、公開 usage 及獨立判讀。父 deterministic assertions 全部通過；
模型必須完成真實檔案與命令，父驗收不替代模型曾實跑的證據。

| Packet / requested config | 獨立判讀 |
| --- | --- |
| R / Luna-low | 5/5：latest-event 分類、counts、來源行號、注入資料處理與唯讀。 |
| E / Luna-high | 5/5：實跑 7/9/11/60、call chain、優先序及不可達 legacy。 |
| W / Sol-medium | 5/5：chunker 實際修改、edge cases、input 不變性。 |
| S / Sol-high | 5/5：分層 validation/merge、0/false、非法覆蓋值、不變性。 |
| A / Sol-medium | 5/5：三檔真實修改、UTF-8/binary、missing source、第二次 copy fault recovery、重跑一致性。 |
| V / Sol-medium | 兩個 defects、controls、skip、唯讀成立；heredoc 來源 unknown。 |
| E / Luna-low（lower） | **FAIL**：final 說無失敗，但 events 有缺檔失敗；可見 dry-run 為 7/7/9/60，不能據此證明指定四案例皆執行。 |
| S / Sol-medium（lower） | 5/5：真實修改、反例與 run/skip/fail 都與可見事件一致。 |
| V / Sol-medium + review guidance | 同類 heredoc provenance unknown；其餘四項成立。 |
| V / Sol-high + 相同 guidance | 5/5：findings/controls 正確，初次 control 預期錯誤及補正有完整事件與揭露。 |

保留 `P292-EQ-01/03` 的最初「evidence-quality FAIL」判讀，但後續
[最小事件診斷](pilot/event-observation.json) 要求原樣 heredoc 再 printf，公開
JSONL 仍只出現 printf，而模型回覆先前 heredoc 的 shell failure。此模式亦出現在
不同模型。**缺少公開事件不足以判定 fabrication**；相關敘述最終列 provenance
unknown，不能用最初 FAIL 排名模型。後續 [RCA](heredoc-rca/README.md) 已用公開 diagnostic 實際 args/result 定位受控重現的上游根因；歷史每筆缺項沒有回填成已證明執行。`P292-EQ-02` 的已記錄缺檔失敗與 final
「無失敗」矛盾則保留，不以父代理後跑補成成功。

一般 reviewer 選 Sol-high 是本次採用決策：它在相同 V case 的可見證據完整，
且下列盲審對控制分支的查核較完整；不是已證明 medium 能力不足或 high 普遍
較佳。原始 runs/hash/不利結果保留。high run 來源 TOML 當時仍為 medium，使用
explicit effort override；其 model/effort/developer-instructions 有效欄位吻合最終
high 配置，舊來源 hash 不冒充新 TOML digest。

JSONL 沒有獨立 resolved-model attestation，維持 unknown。CLI explicit config
不是 native custom-role activation，不建立 Desktop quality qualification。
`--ignore-user-config` 仍可載入 global instructions／installed skill metadata，
所以不是完整 instruction-stack 隔離。Sibling oracle 的不可讀是 task boundary，
不是 OS read isolation。原 grader 初次用 repo resolver 導致 cwd 返回 repo，已改
fixture resolver 重驗；這是 harness 問題，不列模型失敗。

## 獨立盲審評測與成本

[可重現案例](blind-review/README.md) 及 [結果](blind-review/results.json)：兩個全合成
variants × Sol-medium／Sol-high／Astra-xhigh，共六個 fresh runs；相同通用提示、
developer instructions、source review guidance、fixture 與 readonly sandbox，提示
不透露預期缺陷／數量。固定 oracle 經父代理與獨立 reviewer 的隔離執行驗證，使用
真實 PyYAML 與自建 child PID／CLI subprocess，沒有 mock ValueError。

六 arms 都辨識兩個 seeded defects，沒有把 maintenance／retention controls 誤報
為功能 bug。真 parser CLI 都觀察到 exit 1／ParserError traceback，與契約要求的
exit 2／受控摘要不符；正常 YAML exit 0。Lock 證據是靜態路徑、真實 PID／函式
與 mock file flow；模型均未完成實體 lock CLI 整合，父 oracle 的實體驗證分開記錄。

Sol-medium/v2 沒有單獨執行「過期但屬 latest-N」control，且未嘗試 temp creation
即說唯讀不能建立；該句只能作推論。Sol-high/v2、Astra/v1/v2 的 heredoc claim
因公開 event 缺口列 unknown；確實有記錄的 TemporaryDirectory/PermissionError
另行成立。沒有觀察到 source 修改、外部存取或越權。

| Arm（各兩案例合計） | Wall seconds | Input tokens | Cached input | Output tokens | Standard credits rate proxy A / B |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sol-medium | 190.665 | 412009 | 354304 | 7516 | 6.5358 / 24.2510 |
| Sol-high | 263.777 | 508942 | 445952 | 12021 | 8.3845 / 30.6821 |
| Astra-xhigh | 521.220 | 520810 | 434944 | 15496 | 51.7101 / 160.4461 |

費率來自 [當日官方 Codex Standard 表](https://learn.chatgpt.com/docs/pricing#token-rates)。
A 假設 input 已包含 cached，B 假設兩欄獨立；這是**兩種條件估值**，不是信賴區間
或實際帳單。服務 tier、counter 計費解讀與 subscription bucket 換算未 attested，
reasoning 不再另加到 output。不同 arm 的命令次數、cache reuse 與回答長度不同；
只有兩個相近小型 case、每 arm 一次，不宣稱模型排名、普遍成本節省或完整
ME-01/ME-02/ME-03。它支持日常 Sol、風險首次路由及深入 Astra 邊界的保守採用。

## 安裝與契約驗證

隔離 `0.26.1 → 0.27.0`：11 → 12 profiles、五個變更 baseline 的 backup bytes
完全吻合舊版、其餘六個既有 profiles 不變、全部 installed bytes 等於 current
source；diff 與 non-force update 不改 profiles，force update 僅作用於 disposable
skills/templates/agents/state targets。未更新個人安裝或 qualification store。

保留 harness 修正紀錄：最初使用未支援的 target 變數，舊版 install 只回報既有
檔案 up-to-date；第二次只隔離 agents，dependency template staging 被 sandbox
拒絕。隨後唯讀 diff 確认個人安裝仍與原版一致；第三次隔離全部 targets 才得到
上述成功證據。失敗嘗試不計入升級 PASS。

12 個 test shards 已分組完成：1488 tests PASS。初次並行驗證遇 profile 修改中造成 digest 漂移，installer／loop-control 穩定後重跑通過；另既有 memory fork case 曾有 child SIGSEGV（-11），單例與完整 493-test shard 重跑通過，根因未認定，不抹除初次失敗。新增 RCA/evidence 8 tests 通過，最終 repository-policy shard 90 tests PASS（合計 1496 項）。Offline repository validator、release-state、140-file plugin parity 與 diff check 亦通過；獨立審查及安全掃描的最終版本綁定由外部 gate receipt 記錄，不能由此測試總數替代。

## Finding dispositions 與發行狀態

- `R292-REV-01`：release note 缺必要章節，已修正；離線 validator 已於前一輪通過，
  最終 offline validator 已再次通過。
- `R292-REV-02`：release note 的 verification 連結缺檔，本紀錄補齊，獨立 reviewer 已回查。
- `R292-REV-03`：歷史 V2 selector validation bypass；共用 enum/type validation 已修，非法/null/list/int workload regression 與獨立重現通過。
- `R292-REV-04`：routine 未安裝時略過 installed deep fallback；先核對實際目的角色再找替代，獨立重現恢復 deep route。
- `R292-REV-05`：V1 高風險可能選低 tier routine；routine 限 V2，builder/validator/preflight/fallback 都覆蓋，舊 V1 fixtures 保留。
- `R292-REV-06`：README 把 current high/high labels 當 effort A/B；已改成歷史 medium/high 與 current 重跑語意分開。
- Pilot 品質失敗列為限制及提示詞改善依據，不隱藏或重標成成功。
- `R292-REV-07`：correlator 在 raw stream invalid 時曾把命令清單當空而誤判 confirmed gap；已改 unknown／count null，真實有 command item 再附 malformed 行的回歸通過。真實兩個 baseline streams 都 valid，不受此缺陷影響。
- `R292-RCA-01`（Deferred；owner `jeffery777`；target #293）：根因已定位、本專案判讀已緩解、上游事件缺口未修復；same-heredoc before/after 均 tool exit 1／command item 0。上游 #47433 與本專案 #293 未解；依使用者接受列為已知問題發行，不能稱修復。
- 本地 JSONL silent parse 弱點已修；strict stream/terminal/final 與 tool coverage 分開，8 項新 regression PASS，16 份歷史 streams 全數 strict 解析／final 一致。

source/package version 為 `0.27.0`。Release note 是 candidate preparation，舊版本
release notes 不改寫，active guidance 不維護 current published pointer。
PR、hosted CI、完整 exact-head review、strict receipt/App/ruleset readback、合併及
annotated tag/Release 尚待完成；此處不聲稱 publication，也不授權個人安裝／部署。

## 公開接口與 RCA 對發行的影響

CLI 0.155.1 用於原八次 role/lower runs；兩次 V guidance/high 與六次 blind runs
已是 0.156.0（逐 run 保留 version/hash），不把不同版本冒稱全程同一版本。
Desktop 公開更新檢查為 26.917.51856 build10492／up_to_date；119 項相關
interface tests 通過，未發現 routing／handoff 需改動的公開契約破壞。
模型 catalog 缺項不能當可用或不可用證明；native role activation 與 resolved
model attestation 未建立，資格邊界不變。詳見 [根因、措施前後及未解狀態](heredoc-rca/README.md)。

缺事件的個別敘述不再納入模型 evidence-quality 失敗排名；findings／真實
功能驗收與獨立 oracle 保留。E-lower 已記錄的失敗與 final 矛盾仍成立。
一般 reviewer Sol-high 是有限證據下的保守選用，不能宣稱普遍優於 medium；
高風險 Astra-xhigh 由風險路由決定。上游問題本身不推翻角色配置，也不以
配置切換替代修復。依使用者明確決定，適合以已知問題方式發行候選 0.27.0，
前提仍是全部本專案交付 gates；實際部署成本／品質尚需後續量測。

Deferred RCA 的原因是上游 event producer 未修，使用者已接受本專案緩解後作已知問題發行。若後續流程以完整工具事件作安全／資格放行的必要前提，卻缺實際 request/result 對照，或診斷格式漂移而無法可靠解析，該相依流程升為 blocking；#293 保留同 heredoc 的修復後驗證計畫。`P292-EQ-01/03` 的 fabrication 定論因證據不足而 Rejected，歷史資料不改寫；`P292-EQ-02` 的真實矛盾不接受較低 explorer effort，預設保留 Luna-high。
