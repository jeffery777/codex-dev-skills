# Exact-head 與完成證據契約

適用於已有 change request 或宣稱正式 merge content readiness。Change request 可以是 PR、MR、其他 forge review object；無 provider adapter 時可選明確的本機 base-to-head range。這是 Markdown 流程與證據義務，沒有狀態機、validator、collector 或 runtime API。正式文字為繁體中文；來源見 [source-map](../docs/provenance/source-map.md)，授權原文見 [upstream-notices](../docs/provenance/upstream-notices.md)。

<a id="exact-identity"></a>

## 證據角色與身分

Pre-commit code/docs/deep/security review 可在內容、revision/diff、scope、假設、階段、政策及環境仍符合時重用其證據，但 verdict 不滿足 exact-head Merge Review。後者是最後完整 base-to-head 整合審查，必須綁定：

- repository 與存在時的 change-request 身分；exact base、head、merge-base revisions。
- deterministic diff／range 身分、review mode、適用 DoD。
- verification commands／results、findings、dispositions、residual risk。
- code、documentation、configuration、package、version 的 coherence。

Local report、chat handoff、worker summary、goal/session 狀態、provider status 或較早 review 都不能替代上述證據。完成依當前 repo/Git、必要驗證、獨立 review、核可平台證據與使用者 DoD；協調狀態及 bool/PASS/helper 結果不自行證明完成。

<a id="exact-coherence"></a>

## 完整範圍與 coherence

每次檢查最後完整 range，不只最新 commit 或碰巧 docs-dominant 的檔案。執行專案提供且適用的 deterministic offline repo/version/package/schema/generated-artifact/docs checks；比對使用者可見宣稱與 code/config/spec/tests／實際觀察。查過期 names、commands、paths、feature states、compatibility claims、release scope 與被取代描述；變更行為須有相應文件，或記無需修改的理由。每個 finding 在 readiness 通過前有持久 disposition。

Tests 不證明語意文件一致；人／模型 review 不替代可機械驗證的事實檢查。不存在／未跑 CI、空 inventory 或缺狀態不是 Passed；逐項明列適用、不適用及未驗證。

<a id="exact-transition"></a>

## 必要流程與新鮮度

文字流程依序為：change request created（無 forge 時 exact range selected）→ exact-head verification passed → exact-head content review passed → content readiness ready → merge authority verified。最後一步核對有效人類指示或核可平台操作；既有明確授權仍有效時不要求重新核准。不得跳過前置或由較晚 provider status 推定較早內容通過；review evidence 明示本身不授權 merge。

Repository/change-request 身分、base、head、merge-base、diff identity、required verification、finding disposition 或 coherence evidence 變動，回到最早受影響的 REVIEW_REQUIRED 狀態。**每個 changed head 都重新完成完整 base-to-head Merge Review**，不能沿用舊 exact-head verdict。

<a id="exact-dimensions"></a>

## 分開回報內容、平台與授權

| 維度 | 狀態與意義 |
| --- | --- |
| `content_review` | `PASSED`／`BLOCKED`／`NEEDS_HUMAN_DECISION`；只對精確已審內容的共用契約成立 |
| `platform_enforcement` | `VERIFIED`／`UNVERIFIED`／`BLOCKED`／`NOT_CONFIGURED`；獨立描述所選 provider profile 證據 |
| 操作授權 | 逐項核對當前目標／scope 與有效授權；不由任一 readiness 狀態產生 |

Content PASSED 不宣稱已檢查 forge pipeline、discussion、approval、check、receipt、ruleset 或 merge box。專案未選 profile 時 NOT_CONFIGURED 有效；已選或有相關狀態卻無當前成功讀回為 UNVERIFIED。Required profile 的 UNVERIFIED／BLOCKED 阻擋整體 formal merge readiness，但不抹除有效 content evidence。

Provider profiles 是 opt-in 專案 overlay，明列 provider／exact repo、normalized evidence、新鮮度規則及 pipeline/thread/approval/receipt/check/protection/final-readback 等要求。不得弱化 exact-head／coherence、混淆內容與授權，或對缺失／過期證據作肯定宣稱；未選 profile 不要求它的 provider objects。GitHub App/check/ruleset 專用流程留選用它的接口／專案，其他 forge 不借用其證據或 payload。

修正後的比例 review 與必要 scan 依 [審查契約](review-and-security.md) 執行，仍須新 head 的完整 Merge Review。合併前立即重查 applicable platform 狀態與 live base/head、review 身分／新鮮度及授權；漂移重回受影響前置。工具能力或 receipt 不授權任何 external write、policy mutation、tag/Release 或 deploy。

深入審查及安全分析依 [任務風險及早啟動](review-and-security.md#review-risk-timing)，不等最終版本固定。Merge Review 核對最終候選所需證據是否充分、當前且覆蓋完整範圍，不因進入合併階段就機械重做全庫深掃；證據失效、新風險或適用政策要求時補足相應深入 review／scan。掃描後改動須有新候選身分與影響分析；未受影響證據的重用理由／coverage 可保留，但不能沿用舊 head 的完整內容 verdict。

<a id="exact-pinning"></a>

## 固定文件來源、digest 與 notices

各接口在建置時實作 core version（若已發布）、完整 immutable revision、每份 Markdown path／digest、明確定義的文件集合 digest、allowlist、dependency closure、來源與 license notices 的 lock／查核／組裝。亦記接口 repo/revision/version、組裝器版本、layout、驗證環境與使用章節；runtime 僅使用已組裝的固定文件，不追蹤 core `main` 或下載可變規範。

改變 core revision、digest 或義務，觸發各接口自己的受影響遵循驗證／review；不能因共享 Markdown 宣稱等價，也不能以舊 receipt 證明新內容通過。Digest 只驗完整性，不代替來源審查、授權或 provenance；source/package version、tag/Release publication、install 與 deploy 是分別的證據。Derived copies 保持唯一來源及修改標記，保留原 copyright 與完整 permission/warranty notices；[來源授權](../docs/provenance/upstream-notices.md) 不被目的 LICENSE 取代。

Core 只記文件義務與 provenance，不承載 manifest/schema 檔、程式套件、下載器、installer、assembler 或 validator。核心不反向依賴兩端；來源 permalink 是出處，不是執行依賴。此契約不建立 release／install／deploy 權限。
