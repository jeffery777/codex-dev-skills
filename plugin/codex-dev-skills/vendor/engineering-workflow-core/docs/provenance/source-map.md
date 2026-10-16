# 契約來源與逐條處置

P1 的固定抽取來源是 `jeffery777/codex-dev-skills@993597561881d6ed8c552f9a18c59315015ad245`；本機來源只讀，未混用 draft #317/#324/#326。目的基線是 P0 merge `0815b74abe52d57efd032bd075e39c83c2ebf0d6`，工作包為 [Issue #3](https://github.com/jeffery777/engineering-workflow-core/issues/3)。核心的正式契約以繁體中文為權威；英文 identifiers 及 notices 原文不翻譯。全面雙語改造另包評估，不在 P1 宣稱 ASD-STE100 符合性。

上述抽取身分與下列逐條對照記錄 P1 當時的來源及處置。P1 之後的使用者新增要求分開記於 [簡明寫作更新](#plain-writing-update)、[證據生命週期更新](#evidence-lifecycle-update) 與 [風險與審查時機更新](#risk-review-update)，不倒寫成原上游義務或 P1 當時已完成的符合性驗證。

以下按來源正文段落、每個編號／bullet 與表格義務列出穩定 ID、exact file/lines、disposition、目的章節及理由。標題／空行隨相鄰單位歸類；不是把整份來源都稱中立。`抽取` 保留義務並整理文字；`改寫` 保留共用義務，移除 runtime 具體映射或明示本次澄清；`接口保留` 不複製具體入口／路徑／程式；`不適用` 須有明確理由（本次主要來源沒有需要丟棄的共用義務）。合併文字不等於刪除義務。核心只保留 Markdown，所有可執行依賴留原接口或保留延後。

## 固定主要來源

| 代號／來源 | 行數 | SHA-256 |
| --- | --- | --- |
| [E · policies/engineering-workflow-contract.md](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md) | 68 | `3dd926e8d584404e35abedfbcc8fa1b9c4e90243f421bad1cbea5b170af702d8` |
| [R · policies/reusable-workflow-contract.md](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md) | 81 | `8373c67b977b62a9c71685d877bb31e18c88b41e306e43c88ad2d33822d680f0` |
| [D · policies/reusable-workflow-details.md](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md) | 134 | `b86db062dd54600f1509f14070f89a10dfe52b6334e9e7e062e60c93033b2df6` |
| [X · policies/exact-head-merge-review-contract.md](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md) | 151 | `9692e576788e55395ec82d48fc8c7edd95e234fc8cbbc8027a3c79465eb2c98e` |

## 逐條義務對照

### E · engineering-workflow-contract.md

| ID／來源行 | Disposition | 目的義務／接口保留理由 |
| --- | --- | --- |
| [E01 · L1–L6](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L1-L6) | 改寫 | [工程義務／adapter 分界；移除已驗證 runtime 的點時適用宣稱](../../contracts/workflow.md#wf-delegation) |
| [E02 · L7–L13](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L7-L13) | 抽取 | [可合併階段，不省義務；一般任務不強制 loop/Goal/多代理/排程](../../contracts/workflow.md#wf-stages) |
| [E03 · L14–L14](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L14-L14) | 改寫 | [Discover：指引、Git、ownership、工具、scope/DoD、衝突](../../contracts/workflow.md#wf-stages) |
| [E04 · L15–L15](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L15-L15) | 改寫 | [Plan：切片、writer、風險、驗收；計畫非授權](../../contracts/workflow.md#wf-stages) |
| [E05 · L16–L16](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L16-L16) | 改寫 | [Implement：已授權能力、無關修改、實際 diff](../../contracts/workflow.md#wf-stages) |
| [E06 · L17–L17](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L17-L17) | 改寫 | [Verify：主代理讀回、保護 tests/需求、命令及結果](../../contracts/workflow.md#wf-stages) |
| [E07 · L18–L18](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L18-L18) | 改寫 | [Review/Fix：獨立唯讀、必要 scan、findings/dispositions/重審](../../contracts/review-and-security.md#review-findings) |
| [E08 · L19–L19](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L19-L19) | 改寫 | [Docs Sync：行為、一致性、歷史／未知](../../contracts/workflow.md#wf-stages) |
| [E09 · L20–L20](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L20-L20) | 改寫 | [Delivery Gate：內容／平台／授權、完整 exact-head](../../contracts/exact-head-and-evidence.md#exact-dimensions) |
| [E10 · L21–L24](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L21-L24) | 改寫 | [Continue：checkpoint、來源、唯一 writer、DoD、advisory session](../../contracts/workflow.md#wf-stages) |
| [E11 · L25–L27](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L25-L27) | 改寫 | [公開能力、schema/model/effort/data/context/credential boundaries；unknown](../../contracts/workflow.md#wf-capability) |
| [E12 · L28–L31](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L28-L31) | 改寫 | [契約保留替代、資格證據、不可自動讀／複製其他 runtime credentials；具體 TOML/API 不抽](../../contracts/workflow.md#wf-capability) |
| [E13 · L32–L35](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L32-L35) | 改寫 | [同 runtime 獨立 reviewer 或服務；自審/context/toolset 不替代實際要求](../../contracts/review-and-security.md#review-independent) |
| [E14 · L36–L38](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L36-L38) | 改寫 | [單 writer／手動 checkpoint fallback；缺必要 review/scan 阻 readiness](../../contracts/workflow.md#wf-delegation) |
| [E15 · L39–L45](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L39-L45) | 改寫 | [協調與完成分離、失敗分類、未知效果、兩輪重評、不清歷史／預算](../../contracts/workflow.md#wf-verification) |
| [E16 · L46–L48](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L46-L48) | 接口保留 | [Codex 技能入口、qualification/profile preflight 留 Codex；核心保留必要資格義務](../../contracts/workflow.md#wf-delegation) |
| [E17 · L49–L51](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L49-L51) | 接口保留 | [Hermes 入口與專用 installer/siblings 保留延後，不抽或重新資格化](../../contracts/workflow.md#wf-delegation) |
| [E18 · L52–L57](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L52-L57) | 改寫 | [分別記 surface/backend/instruction bytes/驗收範圍；有限支援非全面資格](../../contracts/workflow.md#wf-delegation) |
| [E19 · L58–L62](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L58-L62) | 改寫 | [固定驗收與獨立讀回、synthetic 限制、失敗保留、私密身分資料；fixture 程式留接口](../../contracts/workflow.md#wf-verification) |
| [E20 · L64–L68](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/engineering-workflow-contract.md#L64-L68) | 改寫 | [適用正式 review/exact-head、opt-in provider 與逐項授權；GitHub 操作細則留接口](../../contracts/authorization-and-stops.md#auth-scope) |

### R · reusable-workflow-contract.md

| ID／來源行 | Disposition | 目的義務／接口保留理由 |
| --- | --- | --- |
| [R01 · L1–L6](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L1-L6) | 改寫 | [必讀核心與條件式細則；source/plugin/filesystem 載入路徑留接口](../../contracts/workflow.md#wf-capability) |
| [R02 · L7–L11](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L7-L11) | 抽取 | [指定方法、指令優先、必要指引／工具／validator/review/資格](../../contracts/workflow.md#wf-capability) |
| [R03 · L12–L13](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L12-L13) | 抽取 | [最小當前能力核對；名稱／安裝／自述非等價](../../contracts/workflow.md#wf-capability) |
| [R04 · L14–L17](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L14-L17) | 抽取 | [完整前置／輸出、部分相容、fallback、缺口與安全工作](../../contracts/workflow.md#wf-capability) |
| [R05 · L18–L22](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L18-L22) | 抽取 | [重用新鮮度與 provenance、PASS 限制、小任務產物比例](../../contracts/workflow.md#wf-capability) |
| [R06 · L23–L27](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L23-L27) | 改寫 | [有界 prompt、當前來源、指令優先、使用者／實際權限](../../contracts/authorization-and-stops.md#auth-scope) |
| [R07 · L28–L29](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L28-L29) | 抽取 | [已授權自主續行、階段不重問、缺決策等待相依部分](../../contracts/authorization-and-stops.md#auth-scope) |
| [R08 · L30–L31](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L30-L31) | 抽取 | [必要 checks 與新變更／失敗／疑慮才重跑，不能略 review/new-head](../../contracts/workflow.md#wf-verification) |
| [R09 · L32–L35](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L32-L35) | 抽取 | [中途修正、狀態詢問、輸出比例、模型特定提示須實測](../../contracts/workflow.md#wf-verification) |
| [R10 · L36–L42](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L36-L42) | 改寫 | [實質停止條件、逐動作授權、破壞性 preview/impact/recovery](../../contracts/authorization-and-stops.md#auth-stops) |
| [R11 · L44–L47](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L44-L47) | 改寫 | [技能停止引用、既有授權、拒絕分類與不得繞過](../../contracts/authorization-and-stops.md#auth-stops) |
| [R12 · L48–L56](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L48-L56) | 改寫 | [觸發才載必要細則，能力不明先完整比對；缺文檔不豁免](../../contracts/workflow.md#wf-capability) |
| [R13 · L57–L57](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L57-L57) | 改寫 | [正式 gate findings/dispositions/blocking/independence 不授權](../../contracts/review-and-security.md#review-findings) |
| [R14 · L58–L58](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L58-L58) | 改寫 | [change request/new-head 完整 review；provider opt-in](../../contracts/exact-head-and-evidence.md#exact-transition) |
| [R15 · L59–L59](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L59-L59) | 改寫 | [驗收失敗重評／必要資格；兩輪非自動停工或新話題](../../contracts/workflow.md#wf-verification) |
| [R16 · L60–L60](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L60-L60) | 改寫 | [主代理選擇、ownership、整合、唯讀reviewer／作者獨立／worker外寫權](../../contracts/workflow.md#wf-delegation) |
| [R17 · L61–L61](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L61-L61) | 改寫 | [公開 discovery/schema/readback、資料專屬契約、禁自啟／移轉／刪除](../../contracts/authorization-and-stops.md#auth-data) |
| [R18 · L62–L63](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L62-L63) | 改寫 | [批次編排能力由當前 surface 證明；未知順序fallback、依賴／approval/mutation/wait有序、有界逐項查結果](../../contracts/workflow.md#wf-capability) |
| [R19 · L64–L69](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L64-L69) | 抽取 | [共用工程階段、適用技能與必要review/docs sync](../../contracts/workflow.md#wf-stages) |
| [R20 · L70–L74](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L70-L74) | 抽取 | [共享義務與 runtime差異；子代理／thread/session/schedule 分開](../../contracts/workflow.md#wf-delegation) |
| [R21 · L75–L79](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L75-L79) | 抽取 | [Primitive vs formal gate、內容／provider／authority分開](../../contracts/review-and-security.md#review-findings) |
| [R22 · L80–L81](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-contract.md#L80-L81) | 抽取 | [文字／靜態案例非runtime攔截／等價，改善須配對量測](../../contracts/workflow.md#wf-capability) |

### D · reusable-workflow-details.md

| ID／來源行 | Disposition | 目的義務／接口保留理由 |
| --- | --- | --- |
| [D01 · L1–L7](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L1-L7) | 接口保留 | [Codex source/plugin/filesystem 路徑解析留接口；共用保留按觸發選讀](../../contracts/workflow.md#wf-capability) |
| [D02 · L8–L16](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L8-L16) | 抽取 | [直接推理／工具／技能組合與必要方法契約，不重跑相同工作](../../contracts/workflow.md#wf-capability) |
| [D03 · L17–L18](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L17-L18) | 抽取 | [選取條1：不得略必讀／工具／validator/review/資格](../../contracts/workflow.md#wf-capability) |
| [D04 · L19–L22](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L19-L22) | 抽取 | [選取條2：當前能力／公開schema，非名稱／安裝／自述](../../contracts/workflow.md#wf-capability) |
| [D05 · L23–L25](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L23-L25) | 抽取 | [選取條3：完整義務與可用≠enabled/authority/completion/quality](../../contracts/workflow.md#wf-capability) |
| [D06 · L26–L28](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L26-L28) | 抽取 | [選取條4：部分重用／fallback／缺口，不能降低驗收](../../contracts/workflow.md#wf-capability) |
| [D07 · L29–L31](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L29-L31) | 抽取 | [選取條5：provenance、內容／revision／假設／環境新鮮度](../../contracts/workflow.md#wf-capability) |
| [D08 · L32–L34](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L32-L34) | 抽取 | [選取條6：有界報告，必要 artifacts 不省](../../contracts/workflow.md#wf-capability) |
| [D09 · L35–L38](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L35-L38) | 改寫 | [公開 thread discovery；initial-missing vs unknown/unavailable，不保留Codex私有mapping](../../contracts/workflow.md#wf-capability) |
| [D10 · L39–L43](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L39-L43) | 抽取 | [Formal gates 語意與新head完整審查](../../contracts/review-and-security.md#review-findings) |
| [D11 · L44–L44](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L44-L44) | 抽取 | [子代理角色／模型資格，原生派送不可繞過](../../contracts/workflow.md#wf-delegation) |
| [D12 · L45–L46](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L45-L46) | 改寫 | [Adapter 身分、schema/response/readback；替代不授session/排程/外寫](../../contracts/workflow.md#wf-delegation) |
| [D13 · L47–L50](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L47-L50) | 改寫 | [持久資料專屬契約，recall非backend、禁自啟／遷移／雙寫／刪除](../../contracts/authorization-and-stops.md#auth-data) |
| [D14 · L51–L53](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L51-L53) | 抽取 | [文字非runtime/品質證明、改善配對量測](../../contracts/workflow.md#wf-capability) |
| [D15 · L54–L58](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L54-L58) | 抽取 | [只組適用契約／角色／task，模型提示須測、無完整矩陣](../../contracts/workflow.md#wf-delegation) |
| [D16 · L59–L62](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L59-L62) | 抽取 | [事實與指令優先分離，使用者／實際權限／safeguards](../../contracts/authorization-and-stops.md#auth-scope) |
| [D17 · L63–L65](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L63-L65) | 改寫 | [workload/risk/verification選模型effort/角色／資格；設定及route留接口](../../contracts/workflow.md#wf-delegation) |
| [D18 · L66–L68](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L66-L68) | 抽取 | [完整brief與授權來源；模板／PASS／能力／完成非授權](../../contracts/workflow.md#wf-delegation) |
| [D19 · L69–L71](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L69-L71) | 抽取 | [範圍內自主、假設、已授權續行、缺決策相依等待](../../contracts/authorization-and-stops.md#auth-scope) |
| [D20 · L72–L75](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L72-L75) | 抽取 | [主代理整合／驗證責任、ownership、唯讀reviewer、子代理不繼承外寫權](../../contracts/workflow.md#wf-delegation) |
| [D21 · L76–L79](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L76-L79) | 抽取 | [比例checks、不可省必要review/new-head、失敗分類不靠effort解環境](../../contracts/workflow.md#wf-verification) |
| [D22 · L80–L84](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L80-L84) | 抽取 | [中途範圍／狀態與分收件者輸出證據](../../contracts/workflow.md#wf-verification) |
| [D23 · L85–L90](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L85-L90) | 改寫 | [返工重評非停止上限，主代理保留選擇／整合責任](../../contracts/workflow.md#wf-verification) |
| [D24 · L91–L95](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L91-L95) | 抽取 | [領域名稱非停止；新實質風險／缺驗證／scope或來源衝突](../../contracts/authorization-and-stops.md#auth-stops) |
| [D25 · L96–L100](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L96-L100) | 抽取 | [逐項精確授權，破壞性意圖／preview／影響／復原](../../contracts/authorization-and-stops.md#auth-destructive) |
| [D26 · L101–L105](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L101-L105) | 接口保留 | [GitHub receipt→App→live-readback順序保留選用profile的接口；不默套Core](../../contracts/exact-head-and-evidence.md#exact-dimensions) |
| [D27 · L106–L110](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L106-L110) | 抽取 | [技能停止引條文、既有授權核對、拒絕合規處理](../../contracts/authorization-and-stops.md#auth-stops) |
| [D28 · L111–L121](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L111-L121) | 抽取 | [八個Shared Phases逐步保留；formal gate只於正式readiness](../../contracts/workflow.md#wf-stages) |
| [D29 · L122–L127](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L122-L127) | 改寫 | [有界共享子代理／不重疊 ownership／主驗證與順序fallback](../../contracts/workflow.md#wf-delegation) |
| [D30 · L128–L131](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L128-L131) | 接口保留 | [Desktop task/thread/worktree/schedule具體操作留Codex，不替代repoartifact/authority](../../contracts/workflow.md#wf-delegation) |
| [D31 · L132–L134](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/reusable-workflow-details.md#L132-L134) | 抽取 | [Primitive品質／formal gate readiness，兩者不授操作權](../../contracts/review-and-security.md#review-findings) |

### X · exact-head-merge-review-contract.md

| ID／來源行 | Disposition | 目的義務／接口保留理由 |
| --- | --- | --- |
| [X01 · L1–L13](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L1-L13) | 改寫 | [PR/MR/localrange適用，immutable內容 vs optional provider](../../contracts/exact-head-and-evidence.md#exact-identity) |
| [X02 · L14–L20](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L14-L20) | 抽取 | [Precommit有效證據可重用，verdict不能替代exact-head](../../contracts/exact-head-and-evidence.md#exact-identity) |
| [X03 · L21–L24](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L21-L24) | 抽取 | [完整base-to-head與repo/change-request身分](../../contracts/exact-head-and-evidence.md#exact-identity) |
| [X04 · L25–L25](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L25-L25) | 抽取 | [Exact base/head/merge-base revisions](../../contracts/exact-head-and-evidence.md#exact-identity) |
| [X05 · L26–L26](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L26-L26) | 抽取 | [Deterministic diff/range身分](../../contracts/exact-head-and-evidence.md#exact-identity) |
| [X06 · L27–L27](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L27-L27) | 抽取 | [review mode與DoD](../../contracts/exact-head-and-evidence.md#exact-identity) |
| [X07 · L28–L28](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L28-L28) | 抽取 | [verification commands/results](../../contracts/exact-head-and-evidence.md#exact-identity) |
| [X08 · L29–L29](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L29-L29) | 抽取 | [findings/dispositions/residual risk](../../contracts/exact-head-and-evidence.md#exact-identity) |
| [X09 · L30–L34](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L30-L34) | 抽取 | [code/docs/config/package/version coherence；摘要／goal/status非替代](../../contracts/exact-head-and-evidence.md#exact-identity) |
| [X10 · L35–L40](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L35-L40) | 抽取 | [最後完整range不只最新commit或docs檔](../../contracts/exact-head-and-evidence.md#exact-coherence) |
| [X11 · L41–L42](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L41-L42) | 抽取 | [專案deterministic offline checks](../../contracts/exact-head-and-evidence.md#exact-coherence) |
| [X12 · L43–L44](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L43-L44) | 抽取 | [可見宣稱對照code/config/spec/tests/observedbehavior](../../contracts/exact-head-and-evidence.md#exact-coherence) |
| [X13 · L45–L46](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L45-L46) | 抽取 | [stalenames/paths/features/compatibility/releasescope](../../contracts/exact-head-and-evidence.md#exact-coherence) |
| [X14 · L47–L48](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L47-L48) | 抽取 | [行為變更文件或無需改理由](../../contracts/exact-head-and-evidence.md#exact-coherence) |
| [X15 · L49–L51](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L49-L51) | 抽取 | [全部findings分類／持久disposition](../../contracts/exact-head-and-evidence.md#exact-coherence) |
| [X16 · L52–L55](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L52-L55) | 抽取 | [tests不替代語意、review不替代機械checks](../../contracts/exact-head-and-evidence.md#exact-coherence) |
| [X17 · L56–L73](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L56-L73) | 改寫 | [五步義務與localrange替代；最末查既有有效授權不強制重新詢問](../../contracts/exact-head-and-evidence.md#exact-transition) |
| [X18 · L74–L79](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L74-L79) | 抽取 | [identity/base/head/diff/check/finding/coherence漂移，changedhead完整重審](../../contracts/exact-head-and-evidence.md#exact-transition) |
| [X19 · L80–L86](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L80-L86) | 抽取 | [content_review與platform_enforcement獨立狀態](../../contracts/exact-head-and-evidence.md#exact-dimensions) |
| [X20 · L87–L90](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L87-L90) | 抽取 | [內容PASSED不宣稱providerobjects已查](../../contracts/exact-head-and-evidence.md#exact-dimensions) |
| [X21 · L91–L97](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L91-L97) | 抽取 | [NOT_CONFIGURED vs UNVERIFIED；requiredprofile阻整體gate](../../contracts/exact-head-and-evidence.md#exact-dimensions) |
| [X22 · L98–L103](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L98-L103) | 抽取 | [Profile opt-in；pipeline/thread/approval/receipt/check/protection/readback](../../contracts/exact-head-and-evidence.md#exact-dimensions) |
| [X23 · L104–L104](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L104-L104) | 抽取 | [Profile明列provider/exactrepo](../../contracts/exact-head-and-evidence.md#exact-dimensions) |
| [X24 · L105–L105](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L105-L105) | 抽取 | [normalizedevidence/staleness](../../contracts/exact-head-and-evidence.md#exact-dimensions) |
| [X25 · L106–L106](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L106-L106) | 抽取 | [保留exacthead/coherence](../../contracts/exact-head-and-evidence.md#exact-dimensions) |
| [X26 · L107–L107](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L107-L107) | 抽取 | [provider/content/authority分開](../../contracts/exact-head-and-evidence.md#exact-dimensions) |
| [X27 · L108–L109](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L108-L109) | 抽取 | [缺失／過期provider證據failclosed](../../contracts/exact-head-and-evidence.md#exact-dimensions) |
| [X28 · L110–L111](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L110-L111) | 抽取 | [未選profile不要求providerobjects](../../contracts/exact-head-and-evidence.md#exact-dimensions) |
| [X29 · L112–L117](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L112-L117) | 接口保留 | [GitHubprofile路徑與GitLabCE具體例子由接口擇用，不套Core](../../contracts/exact-head-and-evidence.md#exact-dimensions) |
| [X30 · L118–L124](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L118-L124) | 抽取 | [比例fixreview按實際風險、unchanged證據仍適用理由](../../contracts/review-and-security.md#review-findings) |
| [X31 · L125–L132](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L125-L132) | 抽取 | [必要SecurityDiffScan各impact/疑慮/不確定先查；未解materialrisk阻readiness](../../contracts/review-and-security.md#review-security) |
| [X32 · L133–L140](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L133-L140) | 抽取 | [無影響scope/rationale為N/A非Passed；docs/model/generated非blanket豁免；變動重評／擴大](../../contracts/review-and-security.md#review-security) |
| [X33 · L141–L146](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L141-L146) | 抽取 | [新head不得重用verdict，cleanstage已授權續行／真正停止](../../contracts/exact-head-and-evidence.md#exact-transition) |
| [X34 · L147–L151](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/exact-head-merge-review-contract.md#L147-L151) | 抽取 | [契約不授commit/push/PR/comment/review/merge/tag/Release/deploy/policymutation](../../contracts/authorization-and-stops.md#auth-scope) |

四份主要來源共 434 行、107 個對照單位；完整非空行均有處置。行數覆蓋只是機械檢查，語意義務完整性仍須獨立 docs-review。來源引用不形成核心反向執行依賴。

## 必要 Markdown 依賴與補充來源

| 來源／精確範圍 | 處置與涵蓋 | 留接口／延後 |
| --- | --- | --- |
| [policies/human-gate-policy.md · L3–L34](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/human-gate-policy.md#L3-L34) | 改寫至 [授權／停止](../../contracts/authorization-and-stops.md#auth-scope)：逐項授權、明確已授權不重問、風險決策與工具拒絕 | L31–34 GitHub receipt/App 順序留 opt-in profile；不能默套 Core |
| [policies/review-artifact-policy.md · L3–L19](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/review-artifact-policy.md#L3-L19) | 改寫至 [證據保存](../../contracts/authorization-and-stops.md#auth-data)：非真相替代、保留 current/referenced/unresolved、dry-run 與精確意圖 | L7 artifact root 慣例留接口／專案；分類枚舉的具體工具留接口 |
| [policies/security-review-escalation-policy.md · L3–L16](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/policies/security-review-escalation-policy.md#L3-L16) | 抽取至 [安全審查](../../contracts/review-and-security.md#review-security)：基線與十項風險升級、source-to-sink/failure/rollback/logging/驗證 | 實際工具、方式、獨立角色／資格與結果由接口提供 |
| [skills/docs-review-gate/SKILL.md · L25–L36](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/skills/docs-review-gate/SKILL.md#L25-L36) | 改寫至 [Findings/gate](../../contracts/review-and-security.md#review-findings)：四種 dispositions、Deferred 必填後續、NIT 與 blocking；適用來源 gate 的明確義務 | 技能入口、frontmatter、安裝引用與執行程式不抽取 |

主來源引用的 model-selection、agent-delegation／integration、context-continuity、native-runtime-capabilities、GitHub/control-plane、Code Mode、memory 專屬規則屬接口操作細則：P1 不複製其程式、schema 或所有政策。必要資格、主代理責任、兩輪重評、公開 discovery、操作授權、持久資料及順序／有界編排義務保留於四契約；接口改接時須保留這些入口與完整 dependency closure。P0 [相依盤點](../architecture/dependency-inventory.md) 保留各 family／producer-consumer；未抽取不等於取消原要求。

## 本次澄清與補強

| 義務 | 來源／處置 | 目的 |
| --- | --- | --- |
| 純 Markdown、單向依賴；程式／設定／驗證器／組裝留接口 | 使用者澄清及 P0 設計，改寫原 adapter 邊界，不搬 executables | [接口責任](../../contracts/workflow.md#wf-delegation)、[固定來源](../../contracts/exact-head-and-evidence.md#exact-pinning) |
| 子代理可繼承 parent sandbox／核准模式，不要求逐一技術隔離；按任務選 model/effort，由接口核對生效 | 使用者明確澄清，與源能力／獨立 reviewer 義務合併，不降低資格或獨立性 | [委派](../../contracts/workflow.md#wf-delegation)、[獨立審查](../../contracts/review-and-security.md#review-independent) |
| 破壞性意圖／精確目標／影響／preview／復原與較低風險替代 | 原 R/D 授權條款與使用者 safeguards 補強，仍依有效政策 | [破壞性操作](../../contracts/authorization-and-stops.md#auth-destructive) |
| Findings 四種 dispositions、Deferred 完整欄位、NIT 不消失 | E/R/D gate 義務，使用本包適用 docs-review-gate 完整判定欄位明文化 | [Findings/gate](../../contracts/review-and-security.md#review-findings) |
| Immutable revision／逐文件與集合 digest／來源 notices；runtime 不追 core main | 使用者澄清／P0 設計，組裝機制仍接口責任 | [固定來源](../../contracts/exact-head-and-evidence.md#exact-pinning) |
| 工程／Outcome／改善三層驗收及有界回饋 | 拆分章程第 9A 節要求，先核對既有 OE/proposal/evaluation，未符合使用者目標不能完成 | [驗收](../../contracts/workflow.md#wf-verification)；下節記錄本次取捨 |

<a id="improvement-coverage"></a>

## 既有改善契約的涵蓋評估

| 既有來源／評估範圍 | 已涵蓋 | 本 P1 處置與限制 |
| --- | --- | --- |
| [docs/operational-evidence-contract.md · L3–L65](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/docs/operational-evidence-contract.md#L3-L65) | 有界、digest-bound observation／來源身分與四項 false-authority；不是授權或完成 | 接口保留；L67–138 有限資料／隱私、offline validation、非自動蒐集或 controller；程式與schema留接口 |
| [docs/improvement-proposal-contract.md · L3–L114](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/docs/improvement-proposal-contract.md#L3-L114) | 失敗依據、完整 lineage、獨立來源重新驗證、proposal-only／pending promotion，評分不授權 | 接口保留；L116–163 CLI/validator/tests、資料規範留接口，不將建議變成 apply 或 executor |
| [docs/candidate-evaluation-contract.md · L6–L94](https://github.com/jeffery777/codex-dev-skills/blob/993597561881d6ed8c552f9a18c59315015ad245/docs/candidate-evaluation-contract.md#L6-L94) | 有界synthetic比較、獨立重播、負面／uncertain非成功、pending promotion；角色資料非認證 | 接口保留；L72–89 memory-off／optional seam，L91–128 CLI／tests／資料規範；不啟用 memory 或 runtime |

設計判斷：三者已有 observation／失敗lineage／候選比較與 false-authority 邊界，尚不等同完整 Outcome 驗收或所有開發工作必跑的反思流程。本 P1 最小補強是 workflow 的逐項目標驗收、有界缺口／原因／下一步與先核對既有契約要求；不再增加 machine contract、反思 executor、全面 pipeline 或常駐系統。後續若要自動化，由接口另包驗證及取得授權；共享文案不表示既有工具已實作新義務或 runtime 已資格化。

## 版本與重建

本表記的是上游 bytes，不在自身文件內填自己的 commit/digest，避免自我循環。下游應在 P1 正式合併後讀回 Core immutable revision 與文件集合，依 [固定來源義務](../../contracts/exact-head-and-evidence.md#exact-pinning) 在接口 lock／組裝。P1 PR head 或工作草稿不自動等同已定稿的消費版本；無 tag/Release/install/deploy 聲明。

抽取／改寫部分須隨附 [upstream-notices](upstream-notices.md) 的完整原 MIT copyright／permission／warranty。Core 根 LICENSE 保持原 bytes；它不取代上游 notices。

<a id="plain-writing-update"></a>

## P1 之後新增：簡明雙語寫作

本包於 2026-10-16 依使用者已接受的寫作要求，在 [Issue #7](https://github.com/jeffery777/engineering-workflow-core/issues/7) 新增 [文件與交付摘要的簡明寫作](../../contracts/workflow.md#wf-writing)，並接入既有 Docs Sync、使用者摘要及文件 review。這是新的共同義務，不是從 P1 的固定 Codex revision 抽取；原來源表、107 個對照單位、revision、hash 與完整 notices 保持原有紀錄。接口須另包更新固定文件與各自驗證，Core 文案不代表既有技能或 runtime 已採用。

| 新增要求的來源／處置 | 目的與驗收 |
| --- | --- |
| 使用者接受先分清英文標準與繁中調適，再加入可驗收清晰原則 | 按讀者、目的、操作深度與文類寫作；術語一致、句型直接、步驟明確，保留必要細節與安全／授權／證據／風險；短回覆不硬套四欄 |
| 英文以 ASD-STE100 Issue 9 為依據；繁中採對應原則 | 未完整核對正式規則、受控詞典及適用技術詞不聲稱符合；全文未取得時明示限制，仍可完成清晰原則所涵蓋的文件工作；繁中不宣稱官方 ASD 符合性或硬套英文單字數 |
| 雙語與原文保護 | 義務、風險、限制與重要資訊一致，正式繁中權威不變；機器字面及須保留的引用／授權原文不改 |
| 沿用既有 review | 在原 review 報告記抽查範圍、結果與限制；不新增 validator、gate、receipt 制度或認證系統 |

### 官方查核與取得限制（2026-10-16）

- [ASD 官方 About STE](https://asd-ste100.org/about_STE.html) 與 [首頁](https://asd-ste100.org/) 的搜尋擷取確認 Issue 9 發布於 2025-01-15，屬英文技術文件標準。
- [ASD 官方 FAQ](https://www.asd-ste100.org/STE_faq.html) 的搜尋擷取說明標準包含寫作規則與受控詞典，並允許依規則使用適用技術詞。清晰原則也可用於其他文類，這不等於它們已完整符合標準。
- [ASD 官方 Tools for STE](https://asd-ste100.org/STEsoftware.html) 的搜尋擷取說明工具不能代替作者或標準。本次直接讀取 About STE、FAQ 及 Tools for STE 皆未成功取得內容，不以搜尋擷取冒稱已讀完整頁面。

本次取得的是官方搜尋擷取內容，未取得完整正式標準，不宣稱已讀完整官方頁面、全部規則或詞典。未提交個資申請，未採用未查證的數字規則；完整 ASD-STE100 符合性未驗證。繁中調適與上述驗收方式是使用者接受的共同設計，不是官方中文標準。此更新不更動 P1 上游 license notices，也不重製完整標準。

<a id="evidence-lifecycle-update"></a>

## P1 之後新增：長任務證據生命週期

[Issue #9](https://github.com/jeffery777/engineering-workflow-core/issues/9) 依使用者於 2026-10-16 明確接受的要求，在 [工作流](../../contracts/workflow.md#wf-evidence-lifecycle) 加入現用／已取代／未解分類、替代覆蓋、上下文與來源保存分流，以及安全結案與小型示意。這是新使用者要求，不是 P1 上游抽取；原 107 單位、固定 revision／hash 與完整 notices 不倒寫。前述簡明寫作及官方查核仍是當時的紀錄，本包不重做或升格其符合性證據。

原 [保存及授權條款](../../contracts/authorization-and-stops.md#auth-data) 保留並補明專案 retention、共享／仍引用資料與保護例外；[不可逆刪除](../../contracts/authorization-and-stops.md#auth-destructive) 明定操作當下確認。替代須覆蓋原失敗情境、revision、scope 與 outcome，保留精簡原因／修正／版本／替代引用與實質 review／merge／acceptance 證據。這不把每份 raw log 永久化，也不讓無關 PASS、摘要或缺保留期間成為刪除依據。

README 兩語僅導讀共用預設、有效專案專化與不可弱化的界線。規則及示意供既有執行、review 與結案流程採用，不新增工具、framework、skill、schema、receipt 或 gate；實際接口載入及固定版本由各 consumer 另包處理。此包不執行歷史證據清理、刪除、搬移或歸檔，不修改 consumer、全域設定、安裝或 reflection／automatic entry／router roadmap。

<a id="risk-review-update"></a>

## P1 之後新增：依任務風險及早審查與安全分析

[Issue #11](https://github.com/jeffery777/engineering-workflow-core/issues/11) 依使用者於 2026-10-16 接受並澄清的要求，補明任務開始判風險與 scope／設計變動重評；unknown 不默認低風險。高風險初期即做深入設計／code review 與安全分析，有實質差異即按必要性比例掃描，不等最終候選。普通流程的快速檢查、獨立 review／fix／retest 與較穩定候選是安排指引，不禁止更早或無相依衝突的並行安全工作。

[審查契約](../../contracts/review-and-security.md#review-risk-timing) 承載風險、時機及候選證據規則；[工作流](../../contracts/workflow.md#wf-stages) 接入階段；[exact-head](../../contracts/exact-head-and-evidence.md#exact-transition) 保留最終完整範圍與有效證據驗收。掃描後變動形成新候選，依影響補測／重審／必要重掃，只重用可證未受影響的證據並記理由與 coverage；信任邊界改變或影響不明則擴查。Merge Review 不機械重跑全庫深掃，但新 head 完整審查與必要 scan 不豁免；不適用須有理由，未執行不是 Passed。

此為 P1 之後新增共用通則，不倒寫原 107 單位、revision／hash／notices、既有寫作或證據生命週期紀錄。有效專案政策可專化觸發、深度、時機及允許的有理由例外，不能弱化必要安全、獨立性、exact-head、授權或保存要求。README 兩語只作導讀；不新增 skill、gate framework、掃描 loop 或通用省成本承諾。本包不改 consumer／pin／安裝／全域設定，不執行歷史清理或 runtime，不打斷 consumer CI；接口採用由協調者另包安排。
