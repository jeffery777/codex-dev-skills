# Issue #290 驗證紀錄

## 異常處置與驗收

`./scripts/project-python -m unittest tests.test_plugin_packaging tests.test_release_state_contract tests.test_exact_head_merge_readiness_control_plane tests.test_exact_head_merge_readiness_workflow tests.test_exact_head_merge_review tests.test_exact_head_merge_review_contract_docs`：110 項通過。

- 缺收據：App failure 完整發布及 completed/native-latest 讀回後，CLI 0 並明示 blocked；無 success envelope。
- failure PATCH、completed readback、native-latest readback 分別故障：CLI 非零、保留原因、單次發布、不回假成功。
- API、schema、receipt drift、受控 OSError，以及與正常阻擋同文字的普通錯誤：仍非零。
- CI pending/非成功、未知或矛盾 status/conclusion、缺欄位、錯誤 repo/run URL、malformed collection：依明確類型拒絕，未放寬 App readiness。
- 舊 output 在任何平台存取前拒絕；workflow shell 的 ready/blocked/noop/error 分流實測，錯誤不吞掉，只有 ready 啟動獨立 offline validator。
- 既有 valid receipt、雙讀穩定性、invalid receipt、drift、App 身分與 native-latest 回歸保留。

測試使用 mock API／controlled fault injection 驗證異常後的處置，不要求製造真實 API outage、實體磁碟耗盡或中斷。測試成功不等於 hosted 或物理故障資格。

## Reviewer disposition

I290-R1（MUST-FIX/P2）Fixed：pending run 必須具有 conclusion 欄位，details_url 必須精確綁定 repository/run ID；否則不能成為正常 block。獨立 reviewer 以兩項合成輸入複驗，修後無 open findings。

獨立 deep/security 邊界與 docs/version review：84 項測試、package 140 files、release-state 通過。主代理比對 source/generated digest 與完整 tracked diff，agent-integrate accepted；worker receipt 本身不代替完成證據。

## Offline、安裝及版本

`./scripts/validate-repo.sh --skip-unit-tests` exit 0；內嵌 unit tests 依旗標跳過，不聲稱本機跑過全套。`sync-plugin-package.py` 140 files、`validate-release-state.py` 0.26.1、`git diff --check` 通過。

隔離 HOME/XDG_STATE_HOME 的 fresh 與 0.26.0 → 0.26.1 upgrade 通過：diff 唯讀、non-force 拒絕且 bytes/modes 不變、force update 的 changed controller template 備份比對、receipt 0.26.1、安裝後 diff/parity，以及既有 synthetic maintenance disabled/stop/resume 回歸。未改真實安裝。

驗證過程曾使用錯誤 test module 名稱（test_plugin_package）及前一 Issue 的 skill backup 假設；修正測試命令與本次實際 template 路徑後通過。一次 package test 在 source/generated 同步期間偵測差異；固定內容後 110 項完整重跑通過。這些失敗不併入不同測試數。

0.26.1 是既有控制平面 bugfix 的 patch 候選，catalog/installer/plugin 一致；0.26.0 歷史 note 未改。發布需另核對 annotated tag/Release，候選不證明已發布。

## 尚未完成的 hosted qualification

新版 controller 在 PR 階段不會以 App 憑證執行；正式 workflow checkout trusted main。需合併後在 open PR 讀回 missing receipt → App failure/controller success → valid receipt/App success 才能宣稱新版 hosted 行為完成。不得修改 checkout 到 PR head 來縮短驗證。已合併 #285 歷史 checks 保留。

安全掃描、PR CI 與 exact-head review 的點時證據由 PR 交付紀錄補充；merge/tag/Release/deploy 保留各自授權。

## Security Diff Scan

Scan `250bdad8-438a-48ff-9bc5-5c7a77661c5b` completed，0 findings，warnings=[]；
5 個 source review items 全數檢查，另核對 supporting workflow/validator/tests/docs。
綁 working-tree snapshot `a951b7ae969a9978a9835e2bc164927b50c9374a49725cf350f1d819d19a1c52`，
collector source/generated SHA256 `6427f7e23ee282220afe7197816d03eb067865838c5a5379c30b8947ca56a9f7`。
封存後僅新增本驗證文件；不得將不同 source bytes 視為同一掃描結果。
工具量測 totalTokens=5816041，cachedInputTokens=5678976，threadCount=3；
數字含 cached context，不由此推算成本。Daybreak status=granted，programs=Daybreak Blue。
