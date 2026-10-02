# Hermes Agent 基礎支援需求

追蹤：[Issue #318](https://github.com/jeffery777/codex-dev-skills/issues/318)。
本需求獨立於 Issue #316；不依賴 LiteLLM、公司模型或未合併分支。

## 目標與驗收層級

提供獨立 Hermes 安裝入口及薄 adapter，重用 repository-owned 的授權、
驗證、review 與 exact-head 完成契約。`shared` 仍是既有 Codex 分類，
不是 Hermes 認證。下表是**驗收要求**，不是當次測試結果。

| ID | 範圍 | 完整支援條件 | 基礎交付邊界 |
| --- | --- | --- | --- |
| H-01 | 安裝、發現、載入 | 專用 skills、全部引用依賴、原生 skills_list／skill_view 實測 | 離線 plan／install／diff；不寫 config、auth、Codex discovery roots |
| H-02 | 工具、權限、隔離 | 實際 backend／mounts／credentials／network 可查證且不擴權，負向測試阻止越界 | 人工 supervised 執行；approval、檔案 deny rules 與容器各自查證；不認定等同 Codex sandbox |
| H-03 | 模型與委派 | 明確 model/provider/effort、實測工具 roundtrip、角色品質及獨立 reviewer 邊界 | 無自動 model mapping；逐次 preflight，無能力證據採單一 writer；缺獨立 review 則阻擋正式 gate |
| H-04 | context／session／接續 | 正確 session 身分、cwd、歷史、權限及 durable checkpoint 讀回 | 手動新 session 搭配 repo checkpoint；不自動 resume／fork／schedule |
| H-05 | planning／implementation／verification | 原生模型依 adapter 執行有界 fixture，產物與命令讀回符合 DoD | 可重用工作流契約；實際模型驗收與離線合成測試分開 |
| H-06 | review／delivery／正式 gate | 獨立適當強度 review、必要 scan、exact-head、provider enforcement 各有證據 | 薄 gate 保留阻擋條件；缺 connector／scan／review 不可宣稱 ready |
| H-07 | 既有 runtime 回歸 | Codex installer、catalog、profiles、plugin parity 與既有 tests 通過 | Hermes 不加入 Codex `--all` 或 plugin discovery；不變更 Codex profiles |

## 狀態語意

- **完整支援**：指定能力、版本、surface 與環境的必要實測全部通過。
- **有限支援**：有可用且已驗證的子範圍，明列限制與未完成驗收。
- **尚未支援**：沒有保留全部必要契約的 adapter／證據，不 dispatch。
- source inspection、help、技能載入、synthetic fixture、真實模型與品質驗收
  分開記錄；任何一種成功不得替代另一種。

## 不變條件

不複製或自動採用 Codex credential；不選擇付費 API、不購買服務。
Hermes 自己的 OpenAI subscription 登入由使用者決定並在私人環境完成。
不存真實憑證、私人設定、runtime DB／logs 或機器專屬敏感資料於 Git。
不改 Issue #316 的 checkout、版本或未合併 roadmap。若 main 改變，
同步後重做受影響測試及完整 changed-head Merge Review，核對 roadmap 語意。

tag／Release、部署、破壞性清理另核對授權。名稱評估不是驗收條件。
