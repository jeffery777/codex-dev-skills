# Issue #213：G0 接受資料與下一階段邊界

## 目前接受狀態

2026-09-07，使用者對補完後的 [G0 生產契約](g0-production-proposal.md)明確回覆
「接受其餘建議，完成 G0」，包含 4 GiB 預設及其餘產品／資料條件。
本包正式審查、CI 與合併完成後可另立 G1 執行 Issue；尚未啟用記憶 runtime，
也未取得真實資料操作或發行授權。當前設計與驗證界限以該生產契約為準。

以下保留先前部分交付的範圍、當時未決事項及驗證紀錄，屬歷史材料；
其中「前置決定未完成」等敘述不代表目前的接受狀態。

## 本次範圍與來源

本次延用 [#213](https://github.com/jeffery777/codex-dev-skills/issues/213)，
先確認 Issue，再建立 `codex/213-native-memory-g0-acceptance` 隔離分支。
基準為 `91404cca038ab18aadad6d8d061a5971cdf05e87`；已從 GitHub 讀回
[PR #226](https://github.com/jeffery777/codex-dev-skills/pull/226) 的 merged 狀態與
merge SHA，再以 local Git fetch 取得相同 origin/main。未以舊 main 或 Issue 關閉當作程式證據。

本次使用者同意繼續 MG1 並授權選擇既有或新 Issue、本機 Issue-ID 分支及開發。
原生記憶開啟不代表已接受 G0 生產參數，也不提供資料刪除、commit／push／PR／發行權限。
本次交付只補充設計與接受資料，不執行 G1/G2，不改帳號設定或讀取真實記憶。

| 來源 | 可驗證的交付 | 保留的限制 |
| --- | --- | --- |
| #212／PR #214，文件提交 `e0ffeb4a271961b9b11a279713885f9985da2534` | MG1 外部研究與里程碑設計已納入基準。 | 合併設計不等於實作或核准所有參數。 |
| #225／PR #226，head `f4945a0d0d41a7b663c2130410716179a3271b93` | G0 合成契約、離線 checker、CLI、11 組固定案例及測試已合併。 | 合成格式不自動升為生產 schema；checker 不讀／寫 backend。 |
| #222 [來源分析](../issue-222/source-analysis.md) | 已獨立確認並修正私有 evaluator tuple 註記。 | 原始 finding 的精確身分仍未證實；class-crowding 另行追蹤。 |
| 本次 #213 | 原生記憶共存、對照組控制與本接受資料。 | 文件不新增 runtime 功能，也不宣稱執行效益。 |

## 精確變更與完成條件

- 新增 `docs/native-memory-coexistence.md` 與本文件。
- 更新 `docs/memory-governance-g0-contract.md`、`docs/runtime-compatibility.md`、
  `docs/context-continuity.md`、`docs/roadmap.md` 的對應邊界與連結。
- 不更動 G0/M0/M1 程式、fixtures、版本化 JSON 欄位、profile、installed skills 或產生套件。
- 官方行為、專案決策、合成測試與尚未執行的實驗明確分開。
- 通過相稱的文件／既有合成回歸、離線 release-state、package parity、diff 與獨立審查。

## 可先確認的 G0 部分交付

建議將 [G0 契約](../../memory-governance-g0-contract.md)作為**後續設計的合成一致性基準**，
連同 [原生記憶共存邊界](../../native-memory-coexistence.md)。這只確認 G0 的部分材料，
**不滿足既有 G1 runtime 的進入條件**，也不將 #213 視為完成。部分材料包含：

1. identity、revision、正文／摘要／線索一致性；candidate、preview、confirmation
   與 caller context 分離，不從資料自我取得 authority。
2. 停止使用、內容清除、受管理殘留、空間回收與 pending continuation 的區分。
3. 有限歷史、proof／marker、明確拒絕下限與重播拒絕；不承諾真實 crash ordering。
4. audit 完整性與內容可信度分開；本專案 off 與原生記憶狀態分開。
5. 原生召回只提供查找線索；不自動匯入、不承諾跨儲存全域刪除或隔離。

**完整 G0 接受狀態：前置決定未完成，尚不可請求整體通過。** 合併 PR #226、
測試通過或對上述部分材料的同意都不能代填完整接受。
依 [canonical milestone](../../memory-governance-milestone.md)，G0 還須固定並取得
生產 profile、可信控制面、readback、儲存與故障模型的接受，才進入 G1 可執行核心。
本補充不更改該階段契約，也不把未決事項改名為 G1 來繞過它。

## 完整 G0 仍須定案的具體選擇

以下是建議處置；數值與機制尚未冒充產品預設，也不阻止準備可審查方案。

| 決定 | 建議與理由 | 何時需要接受／驗證 |
| --- | --- | --- |
| MG1 管理範圍 | 維持單一 principal/root，原生生成檔案列為外部範圍。 | G0 的生產儲存與入口契約；G1 實作。 |
| 可信來源 | 由獨立控制面提供身份、有效時間、來源 eligibility、前態及精確確認；不接受相互一致的 JSON 作真實授權。 | G0 定義可測試來源、readback 與失敗規則；G1 實作。 |
| 內容與來源契約 | 明訂 fact／procedure 支援範圍，將 provenance、來源 revision、verified_at／eligibility 結果綁到內容 revision；方法型知識保留前提、成功證據與失效條件。 | G0 定義持久表示及 audit／readback／失效語意，納入刪除與容量計量；若首版不支援 procedure，須明確排除並同步 milestone。 |
| 生產 profile | 十二項上限顯式提供並綁版本；保留 G0 測試值只供合成案例。 | G0 提供代表負載與容量計算後接受；不直接採用 10 版／30 日／80%。 |
| 外部副本未知狀態 | 生產 preview 需能表示已知集合與未知覆蓋率；目前 G0 空清單不能表示沒有副本。 | G0 的新生產格式設計；不回填 v0 欄位。 |
| G1 入口 | 先做本機可驗證核心，再接 audit／maintenance 自然語言入口。 | G0 列明 G1 精確檔案、操作及 review 計畫。 |
| G2 清除與維護 | 明確 journal/storage envelope，測試主檔、索引、WAL／temp、故障、剩餘階段與實際空間。 | 清除設計接受後才實作／資格驗證；不宣稱硬體取證抹除。 |
| 效益實驗 | 固定原生使用／生成與 context management，再比較本專案 backend。 | 獨立實驗範圍、種子與用量預算；未知條件不得稱乾淨對照。 |

建議下一包仍是 **#213 的 G0 生產契約補完**：以已交付合成格式為參考，
提出 revision-bound 內容／來源與方法型知識契約、具體 profile 數值、容量計算、
可信控制面／readback 及 storage failure model，
完成資料／安全審查並取得完整 G0 接受後，才開始 G1 可執行管理核心。
這些安全的設計準備不需要先把合成格式假定成完整接受。
G1 實作屆時另開執行 Issue，取得其 ID 後另開分支；本次不混入資料庫或自動記憶整合。
不得因 #222 原始 finding 身分未明就重做 G0；若要修改 M1 公開回傳契約或找到新證據，
再觸發該項的精確追溯。

#228 的流程審計另確認：合成 version 只有 body／summary／cues，不能被當作已涵蓋
生產 provenance、驗證狀態或方法型知識前提。上述內容契約補入完整 G0 前置清單，
不修改現有 v0 schema；處置與後續交付見 [流程審計](../issue-228/delivery-audit.md)。

## 驗證與審查

本次由 tracked resolver 選定 Python 3.12.9 與 PyYAML 6.0.3。
56 個焦點測試、六份文件的 24 個本機連結、whitespace 與精確範圍檢查通過。
`validate-repo.sh --skip-unit-tests` 通過，包含 G0 固定案例、plugin parity 與
offline release-state；其跳過的 unit groups 不算已執行。未重跑全庫 discovery。
獨立 reviewer 另跑 `tests.test_native_runtime_contract_docs`，34 tests 通過。
修正後主代理重跑該模組與兩個直接受影響文件模組，共 53 tests 通過。
連同仍有效的未受影響結果，共 90 個不重複 tests；不是單次完整 discovery 的宣稱。
這組證據適用於本文所列文件變更；不證明真實記憶行為或效益。

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_memory_governance_g0 tests.test_memory_m0_contract_docs \
  tests.test_memory_sqlite_contract_docs tests.test_runtime_compatibility_release_docs \
  tests.test_loop_state_roadmap_docs tests.test_release_state_contract \
  tests.test_native_runtime_contract_docs
PYTHONDONTWRITEBYTECODE=1 ./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python scripts/validate-release-state.py
git diff --check
```

連結檢查另驗證六份變更文件的本機連結；官方外部頁面由唯讀文件工具查核。
獨立 docs review 檢查共存邊界、既有契約一致性、接受範圍與過度承諾。
本次無程式／執行權限變更；不以文件審查重新認證整個 G0 runtime 或舊 PR。

第一輪獨立 docs review 提出 DOC213-001（階段接受歧義）、DOC213-002（生成控制
不夠明確）、DOC213-003（漏列直接受影響的既有文件測試）。已明訂完整 G0 的前置
決定仍未完成、A–D 生成 disabled 或互相隔離的不可變 snapshot，並納入 34-test
驗證證據。獨立複查結論為 PASS_WITH_NIT，DOC213-001／002／003 全部閉環，
無新 MUST-FIX／SHOULD-FIX。DOC213-004 僅指出連結數由 23 增至 24；
主代理已修正並重新檢查。複查後只有本節計數、測試與審查結果的紀錄收尾，
規範內容不變；沒有剩餘可行動 finding。這是文件審查結果，不是完整 G0 接受。

## 版本與權限

- Source/package：基準 `catalog.yaml` 為 `0.24.0`；本次不改版本。
- Candidate preparation：不增加 release note 或新候選。
- Publication truth：未查 tag／Release；合併 PR 不能證明發布。
- Active guidance：補齊現有 G0 與原生記憶的限制，不維護當前發布版本指標。
- Historical records：不修改 #225 審查、#222 分析或既有 release notes。

建議本次不另發版：六份 repository 文件不屬 installer/catalog 或 plugin allowlist
的交付來源，未改變安裝能力、G0 checker、M1 公開操作或既有產生套件。
若之後將規則接入可安裝工作流程或新增可執行能力，依當時精確 diff 重新評估。
本次完成與本機驗證不等於 commit／push／PR／merge；存在新 PR 後才建立其 exact-head
Merge Review 與所選 GitHub enforcement 證據。
