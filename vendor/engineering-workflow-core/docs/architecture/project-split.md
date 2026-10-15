# 純 Markdown 核心責任邊界

本文件定義純 Markdown 核心與兩端接口責任。P0 見 [PR #2 固定 revision](https://github.com/jeffery777/engineering-workflow-core/tree/0815b74abe52d57efd032bd075e39c83c2ebf0d6)；本 [P1 #3](https://github.com/jeffery777/engineering-workflow-core/issues/3) 新增 [契約與來源對照](../provenance/source-map.md)，並依章程更新現行順序，保留 P0 歷史。來源見 [相依盤點](dependency-inventory.md)，前置見 [遷移計畫](migration-plan.md)。本包不搬程式或改接來源。

<a id="official-comparison"></a>

## 官方文件比較：定稿前的唯讀依據

查讀日：2026-10-14。只使用 OpenAI 與 xAI/Grok Build 官方文件；以下是文件記載；比較過程沒有呼叫所述 runtime 操作或執行 Grok Build。本包的本機文件檢查與唯讀 Codex 子代理不構成兩端能力的 runtime 資格測試。官方文件為可變網站，不能視為固定來源程式 revision 或目前帳號／主機資格。六項比較決定文件契約應保持哪些義務，具體實作留接口。

| 面向 | Codex 官方文件記載 | Grok Build 官方文件記載 | 設計推論／尚未實測 |
| --- | --- | --- | --- |
| 技能載入 | `SKILL.md` 具 name/description，先載 metadata、選用時讀全文；本機 `.agents/skills` 與 plugins 是載入路徑。[Build skills](https://learn.chatgpt.com/docs/build-skills) | `.grok/skills`、plugins 與 user `.agents/skills` 可被發現；`allowed-tools` 不授予或限制工具，`model/effort/license/compatibility` 被接受但不套用。[Skills](https://docs.x.ai/build/features/skills-plugins-marketplaces) | 共用文件只定必讀義務；兩端自己管理 frontmatter、引用佈局與實際載入證據。格式能讀不代表契約會被遵循 |
| 工具 | 本機 Codex 支援 MCP STDIO/Streamable HTTP；同 host 的 app/CLI/IDE 可共用 MCP config，hosted plugin 能力可能不同。[MCP](https://learn.chatgpt.com/docs/extend/mcp) | MCP 工具加到 built-ins，使用 `<server>__<tool>` 命名；CLI 有工具選取／排除旗標。[MCP Servers](https://docs.x.ai/build/features/mcp-servers)、[CLI Reference](https://docs.x.ai/build/cli/reference) | 各接口查公開 namespace/schema／正常工具；不假定工具名、payload、hosted 與 local 功能互換。本包未測工具等價 |
| 權限／sandbox | 技術 sandbox 與 approval policy 分開；CLI/IDE 文件描述 OS enforcement。各執行環境分開查核。[Security](https://learn.chatgpt.com/docs/agent-approvals-security#sandbox-and-approvals) | Permissions 與 sandbox 分開；sandbox 預設 off，Linux/macOS 子程序網路限制與 in-process network 有文件列出的差異。[Permissions](https://docs.x.ai/build/features/permissions)、[Sandbox](https://docs.x.ai/build/features/sandbox) | 文件不能建立權限或隔離。接口須證明當前 sandbox／資料目的地／允許與阻擋行為；相同 profile 名稱不等於相同保護 |
| 子代理 | 支援委派；子代理繼承 parent sandbox/approval，custom instructions 不建立獨立 read-only sandbox。[Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents#approvals-and-sandbox-controls) | 子代理有獨立 context 並回 summary；explore/plan 的文件工具範圍不含 shell/edit。[Subagents](https://docs.x.ai/build/features/subagents) | 本契約允許沿用 parent sandbox／核准模式，不要求每個子代理另建技術隔離；模型／effort 按任務選擇，由各接口核對生效。ownership、作者／reviewer 獨立與主代理整合義務仍保留 |
| Session | CLI `codex exec` 有 resume/fork；無 prompt 的 exec fork 不啟動 turn。這是 CLI 文件，不推定 Desktop payload。[Developer commands](https://learn.chatgpt.com/docs/developer-commands#codex-exec) | Sessions 記載 `-r` resume、`--fork-session` 分支，以及 `-s` 指定新 UUID；Headless 表格卻稱 `-s` 可 create/resume named session，表述有差異。[Sessions](https://docs.x.ai/build/features/sessions)、[Headless](https://docs.x.ai/build/cli/headless-scripting) | 保留 exact session/host/ownership／啟動語意。Grok `-s` 行為列為待核對，不在此選一種當已驗證；未來 adapter 依完整公開 schema／實測解決 |
| 執行結果 | `codex exec --json` 提供 newline-delimited events；可接續非互動工作。[Developer commands](https://learn.chatgpt.com/docs/developer-commands#codex-exec) | headless 支援 plain/json/streaming-json；ACP 的 prompt metadata 與 update text 分開。[Headless](https://docs.x.ai/build/cli/headless-scripting) | 接口分別保存 command/exit/result/artifact/readback；stream 完結、摘要、native goal 或 process success 不代替 repo DoD/review/exact-head 證據 |

未實測項目包括實際技能載入、工具覆蓋、session 失敗恢復、權限與 OS 隔離、獨立 review／scan 路徑、模型品質、成本與延遲。兩端共享文件的設計可行性是推論；跨 runtime 行為等價沒有在本包成立。官方來源入口彙整於 [O01–O11](dependency-inventory.md#official-sources)。

## 核心與接口的單向責任

| 責任 | engineering-workflow-core | 接口專案／使用專案 |
| --- | --- | --- |
| 工程契約 | Markdown 定義 Discover/Plan/Implement/Verify/Review And Fix/Docs Sync/Delivery Gate/Continue、必要輸入輸出、驗收與停止條件 | 各端選入口、載入適用契約、執行流程並產出遵循證據 |
| 授權／約束 | Markdown 說明 scope/identity/ownership、受託權限、破壞性 safeguards、未知外部效果的處理 | 正常工具的 permissions/approval、精確動作核對與結果讀回；規範文字不是 enforcement |
| 獨立 review／必要 scan | Markdown 定義獨立性、風險分級、scan 適用性、coverage、findings/dispositions 與 blocker | Reviewer/scan 工具、資格/preflight、實際結果、固定產物／validator 由接口提供 |
| Exact-head／完成 | Markdown 定義完整 range、來源/diff identity、驗證、coherence、新 head 重審、完成證據 | Git／forge control plane、CI、receipt/check/schema/validator 與 accepted project artifacts |
| 流程狀態／證據格式 | 可以文字或 Markdown 表格描述狀態、必要欄位與示例 | 判定器、路由器、狀態機、schema/parser/validator、digest 程式全部由接口承載 |
| 版本與來源 | Markdown 記錄文件 revision/變更範圍、來源、license notices | 固定 version/revision/digest 的取得、鎖定、驗證、組裝、installer 與程式套件 |

兩端分別依賴固定核心文件契約；核心不 import 或呼叫 Codex/Grok/Orca API，沒有 runtime 動作，也不承載可執行判定器、validator、installer 或程式套件。Core 文件不要求其他 repo 存在才能載入；來源 permalink 是 provenance，不是反向執行依賴。接口可以保留自己的程式與驗證器；共用義務不要求共用可執行實作。

來源已有工程階段與 adapter 責任分離；其 `shared` 標籤仍主要描述 Codex surfaces，不能由標籤推定 Grok/Hermes 資格。[E01](dependency-inventory.md#e01) [E02](dependency-inventory.md#e02) [E03](dependency-inventory.md#e03)

## 可執行來源的歸屬

`loop_core.py` 的 canonical/digest、completion evidence、狀態／授權 guards **全部仍是 Codex 接口專案的程式責任**；技能 `ROUTES`、動態 `agent_routing` 與 Desktop 判定也不搬入核心。核心可用 Markdown 定義其應遵守的授權、證據與狀態規則，但不以程式檔名或純函式性宣稱核心 ownership。[E05](dependency-inventory.md#e05) [E06](dependency-inventory.md#e06)

同樣，`agent_routing`／profile/qualification、continuity、Git/filesystem/index/clock、evidence／graph projection、proposal/evaluation、CLI executors 與 exact-head validators 均留接口或保留延後。`completion_evidence` 的傳入 bool、graph nodes、schema validation PASS 都不自行證明真實來源或完成；接口須讀回證據並驗證契約遵循。[E10](dependency-inventory.md#e10) [E12](dependency-inventory.md#e12) [E13](dependency-inventory.md#e13) [E17](dependency-inventory.md#e17) [E27](dependency-inventory.md#e27)

抽象 class/tier、scope、ownership、review 獨立性可以寫入共用 Markdown；具體 model IDs、effort、profile bytes/digest、runtime tool/session mapping、資格與 dispatch 留各接口。不繼承另一 runtime 的資格，不把 role prompt 的唯讀要求當技術隔離。[E11](dependency-inventory.md#e11)

## 子代理設定與審查獨立性

共用契約允許子代理沿用 parent 的 sandbox 與核准模式，無須為每個子代理另建獨立技術隔離。接口核對當前實際繼承的設定、有效權限與核准行為；角色的唯讀工作約束仍須遵守。作者與 reviewer 的獨立性是工作責任與審查證據要求，可以在同一套繼承的 sandbox／核准模式下達成，不以另建 sandbox 作為每次委派的前置。

主代理按任務的推理需求、風險、上下文量與驗證負擔選擇模型及思考深度。若 parent 模型／effort 符合需求，可以沿用；需要不同設定時，由接口選用當次支援的設定並核對實際生效結果。接口負責 model/effort 的繼承、覆寫優先序、profile bytes 與必要 preflight／qualification；核心只記錄選擇及證據義務，不提供設定程式，也不固定最高 effort 或永久 model ID。未知設定保留未知，不用提示文字或另一 runtime 的紀錄宣稱已生效。[E11](dependency-inventory.md#e11)

若個別任務另有明確技術隔離要求，再按該任務驗證；這不形成所有子代理的通用要求。這次澄清不放寬受託 scope、有效權限、獨立 review、必要 scan、exact-head 或完成證據。

## 協調與並行準備

指定協調者承接原「評估 codex-dev-skills 專案拆分」的跨專案協調，安排有界相依盤點、官方研究及接口設計與核心文件並行；各包列明 revision、scope、ownership、假設與未測能力。本 P1 只新增六份純 Markdown 契約／provenance 並同步必要入口，不修改或派工至接口。

唯讀設計可引用標版本／假設的草稿。P1 正式合併、固定 immutable revision/digest、兩端 P2 設計皆與最終 Core 契約一致、該包授權成立後，P3-C／P3-G 各自推進；共同前置成立後，不必等對端後續實作整體完成。章程允許協調者另包安排 Grok 同步開發與受控測試；Grok repo 可由 Codex 開發，不推定 Grok worker 合格。本 P1 不執行 Grok Build 或 runtime 資格，Codex 行為／安裝維持，consumer/deploy/tag/Release、EdgeInstaller 技能更新另案。現行前置見 [遷移計畫](migration-plan.md)，P0 全部延後提案保留於歷史 revision。

## Host、forge 與保留延後項目

Host／forge 邊界是文件責任說明，不是核心 runtime API。接口使用正常 Git/filesystem／shell／connector／CLI，負責身份、權限、bounded execution、失敗分類與結果讀回。GitHub connector-first 等 provider 具體規則留接口／project overlay；核心只保留來源身分、外寫授權與 exact-head 義務。

`codex-dev-skills` repository-only 的 GitHub App、ruleset、receipt、Issue/branch 維護流程與 CI 不默套核心或使用專案。Provider enforcement profile 由各專案明選；required profile 缺證據時阻擋 readiness，不把空清單當 pass。[E15](dependency-inventory.md#e15) [E16](dependency-inventory.md#e16) [E17](dependency-inventory.md#e17)

Orca 是可選 host／操作入口，操作技能保持上游 ownership；本包不操作／vendor／修改它。未來接口採 Orca 前另核對上游版本、完整操作契約與授權，缺能力用正常 Git/shell 或手動 checkpoint，不能降低完成標準。

Memory／SQLite/MG1/audit/maintenance、Hermes 專用入口、third-party mapping/failover、GitNexus controller/hooks 與 schedulers 均保留來源並延後；default-off 維持，不為核心文件載入而 import、啟用或新增投資。完整 tests/evals 與資源仍在 [盤點](dependency-inventory.md) 留責任，不表示本包測試或搬移。[E14](dependency-inventory.md#e14)

## 文件契約必須保留的邊界

1. 先讀現況與有效指引，核對目標、身分、scope/ownership、Git／修改／環境。只有受託範圍內執行；修改／平台動作各自核對授權與適用 gate。
2. 實作後由主代理讀回成果、完成必要驗證；獨立 reviewer 唯讀審查當前內容，修正 blocker 並重審。Model/工具可用、摘要或 tests pass 不能替代獨立性／資格／完成證據。
3. 依最終 diff 的 security/trust/permission/data/executable/dependency/installation 影響完成必要 Security Diff Scan；未完成／失敗／coverage 不足不算通過。無適用影響時明列 scope/rationale 為不適用，不把 skipped 記成 passed。
4. Exact-head 綁定完整 base-to-head、repository/change-request/base/head/merge-base/diff identity、驗證、findings/dispositions、code/docs/package/version coherence；head 改變後完整重審。`content_review`、`platform_enforcement`、操作授權分開。
5. 外部效果不明先讀回不盲重播；目標／來源／ownership／authority 衝突、必要 review/scan/高風險驗證缺口或真正需決策時，先完成獨立安全工作，停止相依操作。
6. 完成判定以當前 repo/Git/驗證/review/accepted platform 證據與 DoD 為準；native goal/session/subagent/memory 狀態只是協調資料。來源舊 receipt 不證明新 repo readiness。

上述義務以來源工程與 exact-head 契約為依據，抽取時逐條對照，不因純文件定位弱化。[E01](dependency-inventory.md#e01) [E04](dependency-inventory.md#e04) [E15](dependency-inventory.md#e15) [E23](dependency-inventory.md#e23)

## 版本、組裝與來源 notices

核心只提供固定 revision 的 Markdown 文件與文件化來源說明。兩個接口各自實作建置時的 lock／digest／文件 allowlist／dependency closure／license notices 組裝，runtime 使用已組裝固定文件，不 fetch core `main`。任何資料 manifest/schema、下載器、validator、plugin/installer 程式皆放接口，不能回灌核心。

Codex generated plugin 仍從上層 source+allowlist 產生，維持唯一 source 與 bytes/modes/inventory 驗證；接口版本、core 文件 revision、tag/Release/install/deploy 各自記錄。未來 Grok 用自己的組裝與驗證，不從相同 Markdown 或 metadata 推定輸出等價。[E18](dependency-inventory.md#e18) [E19](dependency-inventory.md#e19)

目的 LICENSE 保持原樣；抽取文件／組裝 substantial portions 時保留來源 MIT copyright/permission notice、source revision/path/digest 與修改標記。固定 digest 驗完整性，不能取代來源審查、授權或 license provenance。[E20](dependency-inventory.md#e20)
