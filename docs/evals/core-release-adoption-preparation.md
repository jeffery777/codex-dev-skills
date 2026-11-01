# Core v0.2.0 正式採用準備 / Formal adoption preparation

本頁以下保留 `e83553f2`／Core reviewed head `cbe3efa1` 準備階段的歷史紀錄，其中「當前」與未完成項均指該階段。後續本 source 已採用正式 Core v0.2.0 `6887bfe6183465e9a9e6ccb4ccd7305a58b37302`，catalog／plugin／installer 版本為 v0.36.0；現行歷史重現測試使用真正的正式 validator 接受完整二十檔，不再 stub 接受邊界。準備 fixture 的出版欄位仍為 `null`，只描述原固定準備資料，不能判定後續版本是否已發布；目前來源與驗證範圍見 [v0.36.0 發行說明](../releases/v0.36.0-split.md)。

The remainder preserves the historical preparation record at `e83553f2` / Core reviewed head `cbe3efa1`; its current-state and pending statements refer to that stage. This source subsequently adopted published Core v0.2.0 `6887bfe6183465e9a9e6ccb4ccd7305a58b37302`, with catalog/plugin/installer version v0.36.0; the current historical-reproduction test uses the real formal validator to accept all twenty files without stubbing acceptance. Null publication fields remain part of the fixed historical preparation fixture and cannot determine later publication status; see the [v0.36.0 release notes](../releases/v0.36.0-split.md) for current source and validation scope.

## 繁體中文

本開發工作包接續 Issue #361 與 [Core PR29](https://github.com/jeffery777/engineering-workflow-core/pull/29)，固定 reviewed head `cbe3efa1ecc1d2ec04d2edc7078eb22c9dbec038`、tree `3acff4c9241800f47c9df0d642aa21258bab6f92` 的二十檔。完整 raw 集合為 `ff3b48febea205d5f6de33adbe387b420d96f8105b67eeb689bfc55c3e07cae4`；十九份 Markdown 集合為 `731b7bc86dade62fba5e59d75829fcf7f9dd746c66077f733e2e8e90016ee287`，共363639 bytes。這是固定發行準備來源，不是已發行版本。準備資料的 publication revision、tag object 與 Release ID 保持 `null`，不可用 reviewed head 或 tree 代填。

`tests/fixtures/core-release-preparation.lock.json` 列出全部 path／raw digest／size／Git mode、Codex document-set digest、新增 v0.2.0 文件閉包，以及將來正式切換的具體 anchors／lock／layout／版本欄位。`scripts/verify-core-release-preparation.py` 先核固定資料本身的獨立 SHA，再以 no-follow descriptors 驗精確檔案集合、bytes、types／modes／hardlinks／sizes、links、集合算法、原字保留與四契約 equality。它不下載、不啟動模型、不寫檔、不修改普通 loader 或安裝。

### 歷史重現修正

ADOPT-01 的原因是歷史 `87db5867` eval 以當時的 vendor 當基準；vendor 升級後會把合法的舊候選誤當成刪字。新增獨立固定 v0.1.1 十四檔 baseline／lock，保留原候選十五檔與原 scorer／cases。驗證當前正式來源與歷史比較基準分開：普通來源仍由原 validator 查核，保留檢查使用已捕捉的歷史 bytes。

單元測試在臨時 fixture 推進 vendor，僅於該測試邊界 stub 未來正式 loader 的接受，再確認舊 eval 可重現；同時以真正現行 loader 確認該準備 tree 仍被拒。這不是正式採用成功或出版證據。缺檔、額外項目、tamper、mode、symlink／hardlink／FIFO、祖先 symlink、未知 pin／虛構出版欄位、JSON coercion 及 provenance 排除的負例另驗。

### 實跑入口與未完成項

從本 source checkout 執行：

```sh
./scripts/project-python -B scripts/verify-core-release-preparation.py
./scripts/project-python -B scripts/verify-core-release-preparation.py --require-publication
./scripts/project-python -B -m unittest tests.test_core_release_preparation tests.test_engineering_workflow.CoreFeedbackCandidateTests
```

第一個命令驗完整準備資料後輸出 `prepared-publication-pending`，exit0 不代表已採用。第二個仍輸出 pending 並 exit1，要求真實出版身分時不能通過。舊 `eval-core-feedback-candidate.py` prompt／cases／scorer及其 fixture不改；重用兩端各一次9/9的證據只限於逐 byte 相同的四契約。完整 runtime 資格仍未由文字案例證明。

真正出版後，先由原平台控制面核實 Core annotated tag、解參照的完整 merge revision、非draft／非prerelease Release，以及已審 tree／二十檔集合。若不同，逐項補查受影響內容；不要跟隨 mutable main。然後以這些真實值更改正式 source、vendor／lock、`CURRENT_SNAPSHOT`／FILES／大小上限／digests及 loading docs。ADOPT-02 要把目前 v0.1.1 十四檔的完整身分加入明確 `HISTORICAL_SNAPSHOTS`，保持未知來源 fail-closed，再驗既有安裝升級。

具體後續範圍包含 source／generated plugin／filesystem templates／Hermes allowlist與closure、完整 LICENSE／notices、source-package建議minor `0.36.0` 的版本parity、upgrade／歷史來源update／downgrade／rollback及失敗不promotion。這些正式切換尚未執行，相關待驗不能由本 helper 的 success 取代。當前普通 Core仍v0.1.1、catalog／plugin／installer仍0.35.2，產品清冊排除本開發快照與helper。正式merge、tag／Release與installed payload更新各有獨立授權。

## English

This development packet pins Core PR29 reviewed head `cbe3efa1ecc1d2ec04d2edc7078eb22c9dbec038` and tree `3acff4c9241800f47c9df0d642aa21258bab6f92`: twenty files, nineteen Markdown documents and LICENSE, totaling 363639 bytes. The Chinese section lists separate full and Markdown digests. Preparation is not publication. Publication revision, tag object and Release ID remain null; a reviewed head/tree cannot replace them.

The fixed migration data records every path/digest/size/mode, the Codex document-set digest, complete closure and concrete future anchor/lock/layout/version changes. The read-only developer verifier independently pins that data, uses no-follow reads, checks inventory, file types/modes/hardlinks/sizes, links, collection algorithms, original text and evaluated-contract equality. It neither downloads nor starts a model, writes files, selects an ordinary loader or installs.

ADOPT-01 decouples historical 87db eval comparison from a moving formal vendor. Keep a separately pinned fourteen-file v0.1.1 baseline, the original fifteen-file candidate and its cases/scorer. The ordinary validator still checks formal source; historical comparisons use captured baseline bytes. A temporary unit fixture advances vendor and stubs only the future formal-acceptance boundary, while the real current loader must reject that preparation tree. This is regression evidence, not formal adoption or publication. Corruption, unsafe files, unknown/falsely published pins, JSON coercion and narrowly verified provenance exclusions have negative tests.

The commands above verify preparation, fail closed when publication is required, and run focused tests. Exit0 reports prepared-publication-pending only; --require-publication exits1. Reuse of each consumer's one 9/9 text eval covers only identical four-contract bytes, never full runtime qualification.

After real publication, verify the annotated tag, resolved merge revision, formal Release and reviewed tree/set before changing source/vendor/lock/current anchors and loading docs. Add v0.1.1's exact fourteen-file identity to installer history (ADOPT-02), retaining unknown-source rejection. Verify source/plugin/filesystem/Hermes closure, licenses/notices, proposed 0.36.0 version parity, upgrade/history-update/downgrade/rollback and no promotion on failure. Those formal changes remain pending. Ordinary Core stays v0.1.1; source/package remains 0.35.2. Developer preparation is excluded from product resources. Merge, publication and installed-payload updates retain separate authority. Full ASD-STE100 conformance is unverified.
