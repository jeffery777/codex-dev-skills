# Issue #228：MG1 研究與交付流程審計

## 範圍與證據基準

本次審計 [#228](https://github.com/jeffery777/codex-dev-skills/issues/228)
承接原生記憶共存文件與研究到交付的追溯，不是完整 MG1 runtime 的驗收。
建立 #228 後才建立 `codex/228-memory-delivery-audit` 隔離分支，基準為
`91404cca038ab18aadad6d8d061a5971cdf05e87`。
以保留來源註記的 cherry-pick 承接 [PR #227](https://github.com/jeffery777/codex-dev-skills/pull/227)
的 `4af6daea41d9720821b43191b9034c46cccaeb2f`；承接當下六份文件內容相同，
其後依本次審計補強 G0 接受清單與 roadmap。
不追溯宣稱原始文件是在 #228 建立後才開始撰寫。

本文記錄本次整合前的審計與交付計畫。後續 commit、PR、CI、scan、review receipt
與 merge 狀態以各自的精確 revision 及平台讀回為準，不在本文預先宣稱通過。

| 階段 | 已核對的來源 | 審計判斷 |
| --- | --- | --- |
| 外部研究與建議 | [研究文件](../../memory-governance-research.md)，#212／[PR #214](https://github.com/jeffery777/codex-dev-skills/pull/214)，文件 revision `e0ffeb4a271961b9b11a279713885f9985da2534` | 研究與設計已合併；產品文件、固定原始碼、研究結果與本專案推論有區分。 |
| MG1 設計與 roadmap | [里程碑](../../memory-governance-milestone.md)、[roadmap](../../roadmap.md)；#214 merge `368a0948cc0fac7d06bb760ef20357d0e0b3e753` | G0→G1→G2→G3 的依賴與功能界線明確；研究合併不等於功能完成。 |
| G0 合成交付 | [契約](../../memory-governance-g0-contract.md)、[驗證與審查](../issue-225/verification-and-review.md)，#225／[PR #226](https://github.com/jeffery777/codex-dev-skills/pull/226)，head `f4945a0d0d41a7b663c2130410716179a3271b93` | checker、11 組固定案例與拒絕情境已合併；merge 為本次基準。它不讀 backend，也不產生操作授權。 |
| 原生記憶共存 | [共存邊界](../../native-memory-coexistence.md)、[G0 接受資料](../issue-213/g0-acceptance.md)，PR #227 | 原生召回、MG1 管理資料與交付證據分開；本次承接後以新 PR 完成整合。 |
| 完整 G0 與 G1–G3 | #213 與里程碑的接受條件 | 生產 profile、可信控制面/readback、storage/failure model 尚待具體化及接受；完整 G0 與 G1–G3 未完成。 |

上述合併身分已從 GitHub 讀回，並與本機 Git 來源核對。
既有 research、milestone 與 G0 的歷史 review 是其當時範圍的證據，不替代本次 review。
本次審計不重新執行外部 benchmark，也不把已合併研究當成供應者完整安全認證。

## 從研究到採納原則

| 研究來源 | 已採納的設計原則 | 保留的限制 |
| --- | --- | --- |
| Mem0 | 以明確 identity 提供管理操作，區分版本正文與操作證明。 | Platform 與 OSS 分開；DELETE history 可能仍有原文，不能只憑刪除成功回覆宣稱完整清除。 |
| Microsoft Memora | 正文、主題摘要與替代檢索線索分開，並綁定同一 revision。 | 不照搬先刪再生成、自動 ingestion、多儲存依賴或無上限 history。 |
| PlugMem 合作研究 | 事實與方法保留前提、來源、成功證據及失效條件。 | coding 設計、研究核心與其他插件分開；promotion、模型信心與一次成功只產生候選。 |

這些原則可在本機核心採用，不要求安裝上述 backend。
原生 Codex 記憶提供召回線索；MG1 的差異在可盤點、可修改、可停止與範圍明確的
清除管理。外部研究或原生記憶開啟，都不能取代這些生命週期與授權驗證。

## 授權與工作流程的審計

使用者本次已明確授權在審計與專案要求通過後做到合併。
這包括此交付範圍內的 Issue／分支、修正、驗證、commit、push、PR、必要 review
收據發布與 merge；內部階段結束不是新的授權缺口。
資料刪除、runtime 啟用、部署、Release、權限設定或新增實質風險不從此自動延伸。

[implementation-slice](../../../skills/implementation-slice/SKILL.md) 是有界實作步驟，
其 commit 條件有兩條路徑：使用者明確要求；或 repo policy 明確要求 commit，
且 human gate 已滿足。本次是使用者明確授權交付到合併，符合前一條路徑；
不能拆成每個動詞都重問一次，也不能將模糊的 repo 授權當成後一條路徑已滿足。
[project-delivery](../../../skills/project-delivery/SKILL.md) 明定沿用既有授權，
並在乾淨審查後繼續安全的唯讀或已授權階段。
本次應由 delivery 流程包住 implementation、review 及 merge gate。

Skills 提供適用的程序與預設，不能收回目前使用者的明確授權。
全域指引、專案規範與技能應一起解讀；有衝突時遵守本次有效指令及其優先關係，
不能以檔名或載入技能這件事自行創造更高權限。
技能也不只在沒有 AGENTS.md 時才適用：驗證與 review 方法仍應執行。
Codex 官方將 AGENTS.md 與 skills 描述為互補層，且更接近工作目錄的專案指引
覆蓋較外層的 AGENTS 指引，見 [官方說明](https://learn.chatgpt.com/docs/customization/overview)
與 [AGENTS.md 載入規則](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。
官方載入規則不代表 skill 檔案可以忽略使用者指令。

零 findings 證明該範圍的審查結果，不能自行提供 merge 權限；本次 merge 權限
來自使用者。既有授權也不省略正式 review、Security Diff Scan、CI 或平台強制檢查。
未取得新 head 的有效審查證據時，先補驗證與審查，不把可自行完成的程序交回使用者。

## 流程問題與處置

| 項目 | 證據與影響 | 處置 |
| --- | --- | --- |
| FLOW228-001：部分交付綁在完整 G0 Issue | #227 只有 #213 的部分材料；直接加 Closes #213 會誤報 G0 結案。 | #228 作為有界整合交付；新 Issue-ID 分支、新 PR 關閉 #228，只引用 #213，之後關閉被替代的 #227。 |
| FLOW228-002：把實作切片當成交付終點 | implementation-slice 的單步 commit 條件，須與 project-delivery 的既有授權及持續交付條款一起解讀。 | 本次沿用使用者授權到合併；保留每個 formal gate，僅在新的實質決策或權限缺口停止。 |
| FLOW228-003：不能用舊 PR 證據替代新整合 | #227 的六檔 review／CI 不涵蓋本審計文件與新 PR 身分。 | 新範圍做文件審查及 Security Diff Scan；建立 PR 後重新完成完整 exact-head Merge Review、CI、收據讀回與 App gate。 |
| MG1-AUD-001：完整 G0 清單缺少持久內容／來源語意 | 里程碑要求方法的前提、證據與失效條件；合成 version 只有 body／summary／cues。 | 已在 #213 接受資料與 roadmap 補入 revision-bound provenance、驗證狀態及 fact／procedure 契約，連同 audit/readback、刪除與容量；生產實作仍由 #213 後續接受。 |

這些處置不修改 Issue linkage、merge enforcement 或 installed skills 的政策。
本次整合須等上述證據成立才合併；表格不是提前宣布平台操作已完成。

## 下一個 G0 工作包與真正的決策

#213 下一包應由代理先提出可審查的生產契約：revision-bound 內容來源、驗證狀態、
fact／procedure 支援範圍及方法型知識前提／證據／失效條件，具體十二項 profile、代表負載與
容量算式、可信 principal/root／confirmation 的來源、source eligibility/readback
協議，以及 transaction、journal、磁碟不足與程序中斷的狀態轉換。
先準備合成正反案例與故障矩陣，不能因缺少具體方案就把抽象選擇交回使用者。

可以自行選擇符合既有需求的模組切分、測試組織、單位及拒絕診斷。
只有選擇改變使用者效果或安全／資料契約時，才帶具體方案請求決策。
例如歷史只保留一日或三十日會改變可恢復範圍；授權來源若從已驗證平台證據
改成任意 caller JSON，會讓一致但未授權的資料被當作合法寫入。
這類選擇須列出建議、替代方案及驗證，不能以一般 merge 授權默填已接受。
G0 全部前置條件完成並接受後才進 G1；本次 #228 合併不代替它。

## 驗證與版本範圍

七份 repository 文件是本次範圍；G0/M0/M1 程式、schema、fixtures、安裝來源與
產生套件不變。tracked resolver 選定 Python 3.12.9 與 PyYAML 6.0.3。
承接當下六檔有 90 個不重複焦點測試與 24 links 的證據；新增文件與審計修正後
須重驗受影響部分，不能把舊計數說成七檔驗證結果。

本次需要的驗證包括 `git diff --check`、七檔本機連結、
`PYTHONDONTWRITEBYTECODE=1 ./scripts/validate-repo.sh --skip-unit-tests`、相稱文件審查、
完整範圍 Security Diff Scan、新 PR 的 exact-head Review 與 hosted CI。
報告把本機焦點測試、跳過的 full discovery、hosted test shards 分開記錄。

Source/package 維持 catalog 的 0.24.0；沒有新 candidate 或 release note，
不作 GitHub publication 主張，也不修改歷史發行紀錄。
此文件交付不另發版。後續可執行能力與安裝介面變更再依當時 diff 評估。
