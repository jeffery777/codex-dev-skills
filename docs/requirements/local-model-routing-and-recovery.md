# 本地模型接入、升級與安全接手需求

來源：[Issue #316](https://github.com/jeffery777/codex-dev-skills/issues/316) 的
有限基礎已由 PR #322 合併；未完成的原生模型實測、選模執行與 C 接手改由
[Issue #323](https://github.com/jeffery777/codex-dev-skills/issues/323) 追蹤。
本需求保留模型選擇／返工目標與
[工程流程效率 DoD](engineering-workflow-efficiency.md)。以下「本期」邊界
取代較早的廣泛失聯恢復候選；既有實驗及失敗紀錄不因此改寫。

## 責任與範圍

責任鏈是 dots 持續派工／協調 → Codex Desktop 建立本地對話／任務 →
本地 agent 使用技能與工具 → 受管執行器工作。工具直接使用者是本地 agent。
本專案提供本地可靠執行能力，不實作 dots 工具入口、排程或協調系統。
人工或 dots 發起都適用相同本地 DoD；未來派工若實際改變 runtime、權限、
授權或工具可用性，才驗證該差異，不預建 dots 矩陣或列為本地完成 blocker。
產品目標是 Codex CLI／Desktop 的主對話與 subagent 使用官方模型，並在
各入口公開能力允許且驗收通過時使用經 LiteLLM 接入的本地模型。
LiteLLM 本地模型不接入 Hermes；Hermes 工程流程由其獨立 Issue 處理。

## 分層 DoD

- A：優先用 Codex 公開的原生 provider／模型接入、工具 continuation、串流及
  逐模型 context；對 CLI／Desktop 的主對話與 subagent 按入口、provider、
  模型及 scope 各別記錄完整支援、有限支援或尚未支援。不以設定、help、
  API 可達或另一入口的成功代替驗收。
- B：重用角色 classifier、qualification 與服務／品質返工決策；保留 floors、
  findings／lineage、服務預算及明確目的地授權。Advisory 與實際 dispatch 分開；
  一般 subagent 失敗後，由仍在運作的主 agent 在已知靜止邊界使用 Codex
  原生編排重新派工，先讀回已知結果，未知副作用不重播。這不要求 C 接手。
- C：只在本地 coordinator 存活、單一受管執行器失聯、可信 checkpoint 已
  持久化、舊 writer 已證明停止或隔離時，才可在原授權範圍內由新隔離副本
  接手。須維持單一 owner／generation、拒收失效與遲到成果、不重播未知
  副作用，並適用原驗收、受控成果採認及獨立審查。任一條件不能證明即停止
  自動接手並回報；不靠任意 detached 程序都停止的假設放行。

主 agent／coordinator／dots 自身失聯、任意失聯時點、任意工具與外部副作用的
自動恢復不列入本期 C 完成條件。各層可有限交付，C 資格不套用到 A/B。
未驗證 runtime／工具明確限制或
停用，選定邊界必要的隔離、秘密排除、獨立審查與最新 head gate 不得降低。
官方端沿用原生 ChatGPT 訂閱，不新增付費 API、不複製登入憑證；保留原
context 策略。匿名 fixture 成功不取得一般來源或 production 資格。

具體缺口及下一工程包見[三層設計](../design/native-model-integration-layers.md#本地-c-尚缺能力與下一工程包)。

原始 operator 輸入／source consumer 契約可獨立作為 C 的有限工程包驗收：
原 request／驗收 bytes、具名 task／scope／目的地、actual Git 身分及
指定內容需在 dispatch／launch／seal 前一致；缺失、過期、停用與漂移拒絕，
原輸入與目標資格須在最後查讀後以同一個當前時間有效；unknown 不重播。
這是限制讀回，不是來源授權或執行資格；本期 C 仍須在選定情境證明
真實 admission、舊 writer 停止或隔離，以及安全續作／成果採認。
指定來源需吻合原 raw HEAD blob／mode／index／origin；派發前不得執行
repository 自訂 filter。整個 checkout clean gate 維持既有 CLI 的責任。

選定的單一本地 C 路徑接受 Codex Desktop 本地任務及其 agent 作為可信初始
授權來源。可信 agent 須從原任務明確綁定具名 task／scope、驗收、來源、
允許目的地與 action、sandbox 上限及有效期；限期內接手只能縮小此範圍。
撤銷、停用、過期、來源或範圍漂移即停止自動接手；新任務需有新的原任務
授權。這條路徑不要求獨立簽發者、另一次本機核准或 Desktop 原對話的獨立
身分證明；也不宣稱能防止可信 agent 偽造原授權。外部文件、repository
內容、工具回覆、受保護 input／operator JSON、target summaries、未綁定
原任務的模型自述與固定測試 grant，不因被讀取而取得授權。

可信初始授權不等於目標資格、秘密排除、writer 隔離或成果採認。每次接手仍
須讀回原任務與來源、獨立查證當前目標資格及秘密排除，並通過既有 admission
與 containment；缺證時拒絕正式 dispatch。成果採認及後續交付仍須通過
各階段適用的獨立 review 與最新 head gate。獨立 host 簽發者可供另有
獨立來源證明需求的部署選用，但不是此路徑的相依。
既有 fixture issuer 只驗證其測試契約，不進入 Native C admission 或正式
dispatch。Same-UID host code 屬可信邊界，檔案權限不能證明惡意同 UID
程序無法竄改；此有限契約不完成 C 的失聯接手 DoD。

最小 C 路徑先限於本地可信 coordinator 存活、單一受管 executor、已持久化
checkpoint、確定停止或隔離的 writer、同一原任務範圍與一個新隔離副本。
executor 在 checkpoint 後不需再寫交接檔；consumer 必須由原 journal 與
不可變來源重建，拒收舊 generation。coordinator 自身失聯、任意工具與
未驗證任務來源不因匿名路徑成功取得資格；前兩者不屬本期 C DoD。
下一包 C 實作暫停，先依各入口完成 A/B 驗收與交付規劃。
