# Core #24／#26 候選 eval／Candidate evaluation

## 繁體中文

本工作包對應 [Codex #361](https://github.com/jeffery777/codex-dev-skills/issues/361)。它在測試路徑固定 Core 修改候選，驗證需求關係與機制範圍的文字可遵循性，不更新正式 Core pin、安裝或生產預設。背景是 [Claude core-feedback.md@071c1a7](https://github.com/jeffery777/claude-dev-skills/blob/071c1a7ff1f2ce67a605d54ce5c3e85480852b69/docs/core-feedback.md) CF-004／006 與 [Claude #91](https://github.com/jeffery777/claude-dev-skills/issues/91)。非權威伴讀另在 [Core PR #28](https://github.com/jeffery777/engineering-workflow-core/pull/28)。

### 固定來源與執行範圍

候選的 exact revision、來源 repo、基準 revision、完整 15 檔 allowlist、逐檔 SHA-256／size／Git mode 均列於 [測試 lock](../../tests/fixtures/core-feedback-candidate.lock.json)。文件 bytes 在 [測試 snapshot](../../tests/fixtures/core-feedback-candidate/README.md)，含 LICENSE、完整原 notices 與相依文件；不在安裝 catalog 或 generated plugin 中。[開發 eval 工具](../../scripts/eval-core-feedback-candidate.py) 另固定 lock 與案例的 digest，未知 pin、損壞、漏檔、多檔或不安全 type／mode 都拒絕；它不接受任意 manifest 作新信任來源。

正式 `scripts/validate-core-contract-snapshot.py`、`vendor/engineering-workflow-core*`、installer、catalog、技能與 plugin bytes 不改。普通 loader 仍拒絕候選 revision。這是測試 pin，不是正式 consumer rollout；若日後採用，另完成正式版本、closure、loader、組裝、審查及安裝流程。

此工具只讀文件與指定觀測 JSON，不派送模型、不執行 Markdown、不執行 shell／git、不寫檔、不聯網。 上述唯讀宣稱適用於下方列出的 `-B` 支持入口；未使用 `-B` 的其他 Python 入口可能產生 import bytecode cache，本包不把它們宣稱為零寫入。它驗證固定文件的引用及與正式 v0.1.1 原文的 raw-byte 行序保留，並對四份受保護資料作 equality。兩份有新句子的契約只驗 insert-only；新增句子的完整性與語意仍由獨立 reviewer 核對。輸出的 formal_core_adopted／runtime_qualified／grok_evaluated／merge_authorized 保持 false。

### 實際情境與判準

[固定案例](../../tests/fixtures/core-feedback-cases.json) 包含九個獨立情境：既有需求內小修正、未決 REQ-GAP、使用者加入需求後的新輪次、被誤標 unrelated 的安全 blocker、無需求 wrapper／validator、可追溯 Core 安全義務、真正無關的改進、保留 unrelated 標籤的 gate-only blocker，以及 REQ-GAP／原 severity／disposition 欄位。每個回答列需求關係、當輪可否實作、實作前是否需要使用者需求／範圍／授權決策，以及必要安全 blocker 是否仍保留。尚未完成的普通修正不等同安全 blocker。

`--prompt` 只給完整四份候選契約、情境及輸出欄位，不給 expected。以一個獨立原生 Codex agent 讀取並回答，唯一 writer 留在主代理。觀測原始安全輸出保留在本工作包的系統暫存 evidence 位置，不把真實 session transcript／機器設定放進 repo。主代理將該實際 JSON 原樣交給 `--observations` 評分，不能以人工填 expected 代替模型結果。單元測試中的合成觀測只驗評分器，不計為模型 eval。

評分器要求 exact candidate SHA、完整且同序的案例 ID、精確欄位和值型別；缺漏、重複、錯序、未知欄位及 boolean／integer 混淆不能偽裝成功。評分器不能認證觀測來源、有效 model／effort 或證明實際寫入行為。必須另保留派工／讀回證據；此處只評短文字情境，單次 run 不能證明普遍模型品質、CLI／Desktop／Hermes／Grok 等價或必要 reviewer 工具限制。

### 重跑與結果解讀

在本 checkout 使用受追蹤 resolver；它必須選中 `.python-version` 的 Python。

```text
./scripts/project-python -B scripts/eval-core-feedback-candidate.py
./scripts/project-python -B scripts/eval-core-feedback-candidate.py --prompt
./scripts/project-python -B scripts/eval-core-feedback-candidate.py --observations /absolute/path/to/actual-observations.json
./scripts/project-python -B -m unittest tests.test_engineering_workflow -q
./scripts/project-python -B scripts/validate-core-contract-snapshot.py --root . --layout source
./scripts/project-python scripts/sync-plugin-package.py
```

完整性 exit 0 的 behavioral_eval 是 NOT_RUN，不代表九個情境已通過。觀測評分 exit 0 只代表該固定觀測符合九案 outcome；exit 1 是 outcome 未通過；exit 2 是 pin／來源／觀測不合法或無法查核。必要安全、獨立審查與最新 exact-head gate 仍另行完成。

初始驗證：在未修改的 Codex main `9eef3c298da97ad5c72c8a099258487783149d70` 的隔離 clone，Python 3.12.9／PyYAML 6.0.3 已核對，既有 Core snapshot suite 28 項通過（275.451 秒），plugin 180 檔 parity 通過。主要舊 checkout `34872c6343e880c2fea1e60f371fd1dbf8afa9ba` 的額外同名 suite 曾有 14 failures（installer source payload differs: skills/loop-engineering）；不同 revision 的成功不倒證舊失敗已解決，舊 checkout 未改。候選實跑結果由後續 evidence 綁定，這段 baseline 不冒稱新 eval。

Grok 未做新 pin／eval，追蹤於 [Grok #36](https://github.com/jeffery777/grok-build-dev-skills/issues/36)。本包可完成 Codex 準備，但不滿足原雙 consumer gate，因此 Core 修改候選維持 pending，不 merge。沒有 formal approval、tag／Release、安裝、全域或安全／權限設定修改。

### 2026-10-31 實跑結果

實際測試 pin 為 [Core PR #29](https://github.com/jeffery777/engineering-workflow-core/pull/29) 的 `87db5867fbed58c81e64f0c316168d537452425e`，完整 15 檔從 immutable Git objects 逐檔匯入，mode 為 100644。Lock SHA-256 為 `ac0e713bda1a708f1575402ecc0901bdf4e5d6ff9cba1ecc00a1d13c5242bc89`，cases SHA-256 為 `c3322e94283f67580b56a32ba185934c1658daedd2a390e2fec950dc48d541cd`；eval 工具獨立固定兩者。

獨立原生派工 `/root/codex_candidate_eval` 實際讀取完整 prompt，回覆九案 JSON，主代理沒有用 expected 改寫答案。安全觀測檔 `core-feedback-361-observations.json` 保留在系統暫存工作 evidence；SHA-256 為 `00d35d85230f50879d2a35d31a1a5b970a22d8b5d2e61b6bf2a4a2861de3dddc`。它只含合成情境的結構化答案，不含憑證、機器設定或完整 session transcript；本 repo 記錄來源派工與結果，不保存真實對話。暫存 evidence 可能被作業系統清除，不能當永久原始證據保存承諾；仍可用相同 pin／cases 重跑並分別記新觀測。有效 model／effort 未由此 callable 獨立讀回，沿用 native inherited 設定，保留未知，不稱模型身分已驗證。

| 案例 | 實際 outcome 評分 |
| --- | --- |
| in-scope-fix | PASS |
| gap-needs-decision | PASS |
| approved-later-round | PASS |
| unrelated-safety-blocker | PASS |
| unsupported-wrapper | PASS |
| traceable-core-duty | PASS |
| unrelated-enhancement | PASS |
| retained-unrelated-blocker | PASS |
| req-gap-record-fields | PASS |

實際觀測評分 exit 0，9/9 通過；四個 readiness／adoption 旗標均 false。候選完整性 verified／15 檔；`tests.test_engineering_workflow` 14 項通過，含新的 pin／破壞／逐字／scorer 反例；正式 v0.1.1 snapshot verified／14 檔、plugin parity／180 檔及 shard inventory／12 shards、100 modules 均通過。這些是列出的本機驗證，尚不等於 hosted CI 或最終 review。

相同觀測 bytes 另以 persistent supplemental artifact 保存在 SDS `5c2568e6-65e5-4026-a407-bfb6b35a7f29` 的 `artifacts/evaluation/core-feedback-361-observations.json`，digest 相同，沒有放入 repository。原生 eval 的實際派工使用 `fork_turns: "none"`，未繼承父代理含 expected 的歷史。

早期獨立 code/security review 的 EV-COV-01、EV-COV-02 均已修正：新增保留 unrelated 標籤的 gate-only 案例，以及 REQ-GAP／原 severity／disposition 的顯式欄位。原七案未覆蓋這兩項的狀態保留為設計缺口，沒有當作已通過結果；實際模型 run 在九案固定後才執行。Core 本體 SDS `b75b92c8-a7fe-4701-a272-f737baa5a713` 已封存讀回，五檔候選安全語意 coverage 完整、零 findings；本 Codex 新 eval 程式仍另依完整實際 diff 做審查及安全適用性判定。

## English

This packet for Codex #361 pins the Core #24/#26 candidate under test paths and evaluates the text's requirement-relation and mechanism-scope outcomes. It changes no formal Core pin, installation, or production default. Sources are fixed Claude CF-004/006 and Claude #91; optional companions are separate in Core PR #28.

The test lock records the exact revision, repository, baseline, all fifteen files, SHA-256, size, and Git mode. The snapshot includes LICENSE, complete original notices, and dependency closure. The developer evaluator independently fixes the lock/case digests and rejects unknown pins, corrupt/missing/extra files, unsafe types, and modes. It provides no arbitrary-manifest trust bypass. Ordinary loader/vendor, installer, catalog, skills, and generated plugin retain their bytes and still reject the candidate as a formal pin. Later adoption needs its own version, closure, loader, assembly, review, and installation work.

The tool reads fixed documents and a supplied observation JSON file. It dispatches no model, executes no Markdown/shell/git, writes nothing, and uses no network. The read-only claim applies to the supported `-B` commands below; other Python entrypoints without `-B` can produce import bytecode caches and are not claimed to perform zero writes. It checks references and raw-byte ordered preservation against formal v0.1.1, with equality for four protected resources. Modified contracts use insert-only checks; independent review checks complete new sentences and semantics. Adoption, runtime, Grok, and merge-authority flags stay false.

Nine fixed scenarios cover in-scope repair, an undecided gap, a user-approved subsequent round, a mislabeled safety blocker, an unsupported wrapper, a traceable Core safety duty, and an unrelated enhancement, an unchanged unrelated-label gate-only blocker, and explicit REQ-GAP/severity/disposition fields. Answers classify relation, current-round implementation, prior user requirement/scope/authority decision, and preservation of necessary safety blocking. Ordinary unfinished repair is not automatically a safety blocker.

The prompt contains all four candidate contracts, scenarios, and output fields, but no expected outcomes. One independent native Codex agent answers without writes. The parent retains its actual safe JSON in temporary evidence and submits it unchanged for deterministic scoring; synthetic unit-test answers prove only scorer mechanics. Do not commit real session transcripts or machine settings. Exact candidate binding, ordered IDs, field sets/types, and outcomes are checked. Missing/repeated/reordered cases, extra fields, or integer/boolean coercion cannot pass. The scorer does not authenticate model provenance, effective model/effort, or actual write behavior. Preserve separate dispatch/readback evidence. One short text-only run proves neither general model quality nor CLI/Desktop/Hermes/Grok equivalence or restricted reviewer tools.

Use the commands above with the pinned resolver. Integrity-only success reports behavioral_eval NOT_RUN. Observation exit 0 means only that those nine outcomes match; exit 1 means an outcome fails; exit 2 rejects unverifiable input. Safety, independent reviews, and exact-head gates remain separate.

Baseline evidence at clean isolated main `9eef3c298da97ad5c72c8a099258487783149d70`: Python 3.12.9/PyYAML 6.0.3, 28 existing Core snapshot tests passed in 275.451 seconds, and 180 plugin files matched. The older primary checkout at `34872c6343e880c2fea1e60f371fd1dbf8afa9ba` had fourteen installer-precondition failures in that extra suite. A different revision's success does not resolve those old failures; the primary checkout was untouched. Actual candidate results require their own evidence.

Grok pin/evals remain unrun and tracked in Grok #36. Codex preparation does not satisfy the dual-consumer acceptance gate. Modifying Core rules remain pending and must not merge. No formal approval, tag/Release, installation, global setting, or security/permission setting is changed. Written per ASD-STE100 principles; full conformance is not verified.

### Executed results on 2026-10-31

The actual test pin is Core PR #29 at `87db5867fbed58c81e64f0c316168d537452425e`. All fifteen files were imported from immutable Git objects with mode 100644. The lock and case SHA-256 digests are listed above and independently fixed in the evaluator.

Independent native dispatch `/root/codex_candidate_eval` read the complete prompt and returned the nine-case JSON. The parent did not replace answers with expected values. The safe structured observation remains in the temporary work evidence as `core-feedback-361-observations.json`, with the SHA-256 above. It contains only hypothetical-case answers, not credentials, machine settings, or a full session transcript. This repository records dispatch provenance/results, not the real conversation. OS cleanup may remove temporary evidence; no permanent raw-evidence guarantee is claimed. Reproduce with the same pin/cases and record new observations separately. The callable did not independently expose effective model/effort identity; native inherited settings were used, with that identity left unverified.

All nine rows in the table passed the actual observation scorer, exit 0. All four readiness/adoption flags remained false. Local checks passed: fifteen-file candidate integrity, fourteen engineering-workflow tests including new pin/corruption/byte-preservation/scorer negatives, the unchanged fourteen-file formal v0.1.1 snapshot, 180-file plugin parity, and the twelve-shard/100-module inventory. These are local results, not hosted CI or final review.

The same observation bytes are retained as a persistent supplemental artifact in SDS `5c2568e6-65e5-4026-a407-bfb6b35a7f29` at `artifacts/evaluation/core-feedback-361-observations.json`, with the same digest, outside the repository. Actual native dispatch used `fork_turns: "none"`, so it did not inherit the parent history containing expected outcomes.

EV-COV-01 and EV-COV-02 from early independent code/security review were fixed by the gate-only unchanged-unrelated case and explicit REQ-GAP/severity/disposition fields. The original seven-case gaps are retained as design history, not reported as successful coverage. The actual model run occurred after the nine cases were fixed. Core's separate sealed SDS `b75b92c8-a7fe-4701-a272-f737baa5a713` covered all five changed candidate documents with zero findings. The new Codex evaluation code still needs its own full-diff review and security applicability decision.

## 開發檢查的窄例外／Narrow development-check exception

完整 repository validation 初次因來源引用中的 provider 詞彙而失敗，記為 EV-VAL-01，沒有當成功。新增的前置分支先驗固定候選完整性，再僅排除本文件與固定 snapshot 中 maintenance／source-map 兩份文件；其他所有路徑與原 compatibility guard 維持原檢查。沒有全域允許詞彙、忽略整個 docs/tests，或改寫 immutable 來源；正常技能、政策、installer、vendor 與 generated package 不因此取得新 provider 支援。

The first full repository validation failed on provider terms in required provenance and remains recorded as EV-VAL-01. The added branch first verifies the fixed candidate, then exempts only this document and the snapshot maintenance/source-map documents. All other paths retain the original check and compatibility guard. There is no global term allowance, broad docs/tests ignore, immutable-source rewrite, or new provider support in ordinary skills, policies, installer, vendor, or generated package.

修正後 `validate-repo.sh --skip-unit-tests` exit 0；輸出明列的 embedded unit groups 是 SKIP，不改稱完整 suite 通過。新增窄例外反例測試後，`tests.test_engineering_workflow` 共 15 項通過：active skills、active policies、其他 eval 文件仍拒絕 provider 詞彙；來源毀損與 pin 缺失也拒絕，移除自有測試字串後可恢復通過。新的測試輸出放在 mini-source 外，避免輸出自行成為下一案例的命中來源。三個既有 Codex 檔只增行，原始 bytes／行序保留；九案輸入與模型觀測未變，原 eval 證據只重用於相同 pin／cases／prompt。

After the fix, `validate-repo.sh --skip-unit-tests` exited 0. Its explicitly skipped embedded unit groups are not reported as a full suite pass. With the narrow-exception negative test added, all fifteen engineering-workflow tests passed: active skills, active policies, and other eval documents still reject provider terms; corrupt source and missing pins also fail, and removing owned test markers restores success. Test output lives outside the mini-source, so it cannot contaminate later matches. Three existing Codex files retain their original raw bytes/line order with insertions only. The nine-case inputs and actual observations are unchanged; their evidence is reused only for the same pin/cases/prompt.
