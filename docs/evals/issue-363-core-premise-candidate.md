# Core #21 premise-failure text candidate

## 繁體中文

[Issue #363](https://github.com/jeffery777/codex-dev-skills/issues/363) 先於遠端 Issue 分支及來源修改建立。本包在 [Core draft #30](https://github.com/jeffery777/engineering-workflow-core/pull/30) 的固定 `9cec34449cc9557d78842c01d88f3ab561c5823b` 測試兩句非權威提案；不向 Core 權威契約或本產品規則先行增句。

### 精確輸入與既有機制

[測試 pin](../../tests/fixtures/core-premise-candidate.lock.json) 固定來源 revision、提案文件 raw digest、完整四契約的逐檔 digest，以及 [382 bytes 引文](../../tests/fixtures/core-premise-proposal.txt)。引文只移除 Markdown 的 `> ` 前綴，兩句原字與 LF 完整保留。這是明列的五份語意輸入，不是完整二十二檔 Core snapshot 或正式 loader adoption；未驗證原文其他部分的模型閱讀也不能聲稱已閱讀全庫。

四契約直接重用 [既有二十檔準備 fixture](../../tests/fixtures/core-release-preparation.lock.json)，經原固定 verifier 檢查完整歷史清冊與 raw bytes，再比對本次 pin 的四個 hash。它們與 Core `9cec3444` 及已發布 v0.2.0 的四契約 bytes 相同；歷史準備的 reviewed-head／null publication 欄位保留，不倒寫為正式發布身分。未來普通 vendor 升級不會讓此歷史基準漂移。沒有重複複製全部來源、另建一般 snapshot bypass 或放寬 provider hygiene。

[離線 helper](../../scripts/eval-core-premise-candidate.py) 重用既有安全讀取／固定 fixture／嚴格 JSON 機制，只新增這一提案的信任錨、prompt 與評分。它不啟動模型、讀登入或設定、不執行文件、不寫檔、不下載、不改 loader／vendor／套件／安裝。相同 helper 的正確預期答案只能當 scorer 合成測試，不能當真正模型 observation。

### 新案例與狀態

[十二案](../../tests/fixtures/core-premise-cases.json) 涵蓋矛盾驗收、真實需求缺口、純實作缺陷、混合原因、無證據猜測、重複修補取代重評、重評完成後續行、需求變更授權、兩輪重評、保留 blocker、評估後的模型選擇及環境失敗。模型 prompt 含四契約全文、未生效提案、情境及所需欄位，不提供 expected 值。

原生模型 eval 尚未執行時必須記 NOT_RUN。機械評分另查候選身分、案例順序、完整欄位、精確型別、非空簡短理由及預期判讀；理由仍須人工查核。Helper 不驗 observation 的 runtime 來源，不能把可自行填入的 JSON 當作來源認證。完整執行與來源證據保存在受控位置，公開只列版本／範圍／結果／限制。

目前已完成輸入完整性及七個 unit tests，包含 byte／pin／案例改動、missing、symlink／ancestor、hardlink、FIFO、mode、超限、歷史基準變更、重複／非有限 JSON、錯誤候選、缺漏／重複／改序案例、bool/int、理由與額外欄位反例。新增需求建議可以是 REQ-GAP，卻沒有失敗根因證據；測試亦拒絕把這種建議直接判成已證實前提失敗。普通 vendor 的變動不會移動歷史測試輸入。這些測試不證明模型理解。

Codex 候選包完成後才接續 Grok 各自 pin／eval；Codex 的答案不替代 Grok。新結果不能沿用舊 #24／#26 九案。即使兩端有限文字測試通過，也不等同完整 runtime 資格、有效唯讀隔離、正式 Core 採納或 consumer 普通 loader 採用。既有 Core v0.2.0／產品 0.36.0、loader、vendor、installed skills 均不變。本輪只準備 draft，無合併、formal approval、Tag／Release 或安裝授權；若後續接受新增義務，再依 Core 與各 consumer 獨立版本政策準備相依升級。

```bash
./scripts/project-python -B scripts/eval-core-premise-candidate.py
./scripts/project-python -B scripts/eval-core-premise-candidate.py --prompt
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 ./scripts/project-python -B -m unittest tests.test_engineering_workflow.CorePremiseProposalTests -v
```

評分可用 `--observations` 指定已取得且可安全讀取的 JSON；不與 `--prompt` 同時使用。輸出 `proposal_accepted`、`runtime_qualified`、`merge_authorized` 永遠 false，`observation_provenance_authenticated` 亦 false。這些是 helper 的能力界線，不能拿來查實際發行狀態。

### 2026-11-01 文字觀測

上述候選已取得一次新的 Codex 原生 worker 文字回應，十二案機械評分 12/12，理由逐案查核亦符合本次準則。使用四契約全文及未生效引文，未給 expected 值。這是 n=1 的有界情境觀測，不是 scorer 的合成正例；完整 prompt／答案／來源與評分留受控證據。繼承模型／effort 的實際 worker 身分未另有獨立讀回，不宣稱特定模型／profile 品質或完整 runtime 資格。未評估 CLI／Desktop 所有入口的自動載入、工具控制或動作執行。

Grok 尚未完成本新候選驗證，雙端門檻仍 pending。此觀測不改普通 loader 或正式採納，四份權威契約也未因此先增句。前述 NOT_RUN 是「尚未取得真實 observation 時」的規則，不拿離線測試冒充本次回應。

## English

Issue #363 preceded its remote Issue branch and source edits. This development packet pins Core draft #30 at `9cec34449cc9557d78842c01d88f3ab561c5823b`. The two-sentence quotation remains inactive test data; no authoritative or product rule is added.

The pin records the revision, full proposal-document raw digest, four complete contract digests and the exact 382-byte quotation. Only the Markdown `> ` prefix is removed; text and LF remain. These are five selected semantic inputs, not the complete twenty-two-file Core snapshot, full-repository model reading or ordinary-loader adoption. The four contracts reuse the existing independently fixed twenty-file preparation fixture and its safe verifier. Their bytes match this Core proposal and published v0.2.0. Keep historical reviewed-head/null publication fields unchanged. Later vendor upgrades cannot move the baseline. No full-source duplication, general snapshot bypass or provider-hygiene exception is added.

The offline helper reuses existing bounded safe-file, fixed-fixture and strict-JSON mechanisms. It adds only this proposal's anchors, prompt and scorer. It starts no model, reads no authentication/settings, executes no documents, writes/downloads nothing and changes no loader/vendor/package/installation. Expected-answer fixtures prove scoring mechanics only.

Twelve fresh cases cover contradictory criteria, real gaps, pure defects, mixed causes, speculation, patches replacing assessment, completed assessment, change authority, two-round reassessment, retained blockers, later model choice and environmental failure. Prompts contain all four contracts, inactive text, cases and requested fields without expected values. Actual model evaluation remains NOT_RUN until executed. Scoring checks binding, ordering, exact fields/types and a short nonempty reason; humans must review reasoning. The helper cannot authenticate observation provenance. Detailed runtime evidence stays controlled; public records contain safe version/scope/results/limits only.

Input integrity and seven unit tests passed, including corruption, missing/unsafe file types/ancestors/modes, FIFO, excessive input, changed historical bytes, duplicate/nonfinite JSON, wrong binding/order/count, boolean coercion, reason and extra-field negatives. A justified feature suggestion can be REQ-GAP without proof of a failure cause; a negative case rejects treating it as a proven premise failure. Ordinary vendor drift cannot move historical inputs. Tests do not prove model understanding. Complete Codex first, then independently pin/evaluate Grok. Neither old #24/#26 results nor another consumer's answers substitute. Limited text success does not prove full runtime qualification, technical read-only control, authoritative adoption or ordinary loading. Published Core v0.2.0/product0.36.0, loaders/vendors and installations stay unchanged. Draft only; no merge, formal approval, publication or installation. Any later accepted obligation needs separately prepared dependent versions. All helper authority/qualification/provenance flags remain false; they are not publication-state indicators. Full ASD-STE100 conformance is unverified.

### November 1 text observation

One fresh native Codex worker response scored 12/12 on the twelve cases; case-by-case reasoning review agreed with the criteria. Its prompt contained all four contracts and the inactive quotation without expected values. This is a bounded n=1 observation, not a synthetic scorer positive. Full prompt/answer/provenance/scoring evidence remains controlled. Effective inherited worker model/effort identity had no separate independent readback, so no specific model/profile quality or full-runtime claim follows. This did not test automatic loading, tools or execution across all CLI/Desktop entrypoints. Grok has not yet evaluated this new candidate; the dual-consumer gate remains pending. No ordinary loader, formal adoption or authoritative contract insertion changes. Earlier NOT_RUN guidance governs absent actual observations, not a substitute from offline tests.
