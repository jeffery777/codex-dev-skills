# engineering-workflow-core

純 Markdown 共用工程契約庫，供接口維護者、交付主代理與 reviewer 讀取工作流、規範、約束、授權、獨立審查、必要安全掃描、exact-head、證據、驗收與停止條件。

本次 [P1 契約抽取](https://github.com/jeffery777/engineering-workflow-core/issues/3) 新增四份契約、逐條來源對照與完整上游 notices，同步必要設計入口。P0 四文件設計保留於 [PR #2 的固定 merge revision](https://github.com/jeffery777/engineering-workflow-core/tree/0815b74abe52d57efd032bd075e39c83c2ebf0d6)。P1 未改接接口或更新既有安裝，不宣稱兩端已遵循或行為等價。

## 開始閱讀

先讀完整 [工作流](contracts/workflow.md)，每次操作保留 [授權與停止條件](contracts/authorization-and-stops.md)；適用審查／正式交付時讀 [獨立審查與安全掃描](contracts/review-and-security.md)，已有 change request 或宣稱 merge readiness 時讀完整 [exact-head 與證據](contracts/exact-head-and-evidence.md)。缺必要文件或能力不能視為豁免。

- [逐條來源處置、修改說明與改善契約涵蓋](docs/provenance/source-map.md)
- [完整上游 MIT notices](docs/provenance/upstream-notices.md)
- [責任邊界與 P0 官方六面向比較](docs/architecture/project-split.md)
- [固定來源相依盤點](docs/architecture/dependency-inventory.md)
- [現行遷移順序、接口前置與驗收](docs/architecture/migration-plan.md)

正式契約以繁體中文為權威，identifiers／引用原文保留原樣；全面雙語與 ASD-STE100 符合性不在本包聲明範圍。

## 責任邊界

| Repository | 責任 |
| --- | --- |
| [engineering-workflow-core](https://github.com/jeffery777/engineering-workflow-core) | 僅 Markdown 契約、來源與授權說明，以及既有 LICENSE；無可執行判定器、router、state machine、runtime API、validator、installer、schema file 或程式套件 |
| [codex-dev-skills](https://github.com/jeffery777/codex-dev-skills) | Codex 技能入口、程式／工具適配、model/effort/profile/session、資格／驗證器、安裝及套件組裝；本包唯讀，維持既有行為 |
| [grok-build-dev-skills](https://github.com/jeffery777/grok-build-dev-skills) | 對應 Grok 接口、設定、工具／權限／session、資格／驗證、安裝與組裝；協調者另包安排，本 P1 不修改或執行 Grok Build |

兩接口各自依賴固定核心 Markdown，核心不反向依賴兩端。接口在建置時實作 immutable revision/digest、來源、dependency closure 與 license notices 的固定組裝；runtime 不追蹤 core `main`。共享文件不是動態行為、模型品質、隔離或 runtime 資格證明。

子代理可沿用 parent sandbox／核准模式，不要求逐個獨立技術隔離；按任務選模型與思考深度，各接口核對實際生效與必要資格。作者／reviewer 獨立、唯讀工作約束、主代理整合及完成證據仍保留。

## 當前限制與交付

P1 只改核心 Markdown，來源固定於 `codex-dev-skills@993597561881d6ed8c552f9a18c59315015ad245`。不搬程式、不修改接口或既有安裝、不部署、不更新 EdgeInstaller 使用的技能、不執行 Grok Build，不啟用 memory/hooks/schedulers，不操作公司環境或 Orca。官方比較是 2026-10-14 的文件證據，非本包 runtime 測試。

跨專案協調已由原「評估 codex-dev-skills 專案拆分」交接給指定協調者，由它安排後續工作。P1 writer 只完成本包；章程及明確使用者授權涵蓋的 commit/push/PR/merge，在必要審查、驗證及 gates 成立後續行。Tag/Release、consumer 安裝、部署與其他階段不包含於此授權。

核心未配置 hosted enforcement profile 或 CI；未執行不得回報 Passed。文件描述契約，不能技術攔截 runtime 或授予外部寫入權。適用專案自行選 overlay 並驗證遵循。

本 repository 採 [MIT LICENSE](LICENSE)，既有 bytes 不變。抽取部分另保留 [原作者完整 MIT notices](docs/provenance/upstream-notices.md)，目的 LICENSE 不能取代來源 notices。
