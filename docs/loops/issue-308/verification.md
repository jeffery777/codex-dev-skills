# Issue #308 驗證與採用紀錄

## 範圍與決策

基準為 v0.31.1 / ee0907c48460a7d58a3c1040b254ac93497f96fe。
Issue 與 codex/issue-308-model-cost-routing 分支均先建立、推送並讀回，再修改。
官方費率及模型定位分析完成後，維護者同意採用，明確略過本 Issue 的模型配對
與節省率量測；必要離線驗證及獨立審查保留。

四個 Sol profiles 只改 model 與相應 digest/mapping date，effort、指令與 sandbox
不改。其他八個 profile bytes 不改。Source/package 候選為 0.32.0；新模型需求
與主代理建議適合 minor 發行，publication 與部署另行授權。

## 驗證

- 固定 interpreter：Python 3.12.9，PyYAML 6.0.3。
- Profile、routing、qualification、qualificationctl、隔離 installer 及 routing eval
  六組 focused suites：130 tests PASS。
- 獨立複審執行 `tests.test_loopctl`：93 tests PASS，涵蓋四個 Sol 角色在僅有
  舊模型 runtime facts 時必須 human-gate；沒有放寬 production preflight。
- Profile validator：12 profiles PASS；四個 Sol profiles 只變更 model，其他八個
  bytes 與基準相同，effort、sandbox 及指令不變。
- Package parity：147 generated files PASS；offline release-state：0.32.0 PASS。
- 完整 `./scripts/validate-repo.sh`：PASS（exit 0），包含隔離安裝、CLI/Desktop
  adapter、routing、memory 與 MG1 synthetic contracts。
- `git diff --check`：PASS。

## 獨立審查與限制

獨立 deep review 初次發現當前 routing fixture 尚用舊模型、跨行指引模型未更新、
以及新模型誤歸於歷史 Issue 三項問題，均已修正。複審無未解 MUST-FIX／SHOULD-FIX。
審查綁定 base HEAD `ee0907c48460a7d58a3c1040b254ac93497f96fe` 與本次工作樹，
不替代後續正式 gate 或 PR exact-head Merge Review。

Security Diff Scan：不適用。檢視範圍為四個模型 mapping、主代理 example、
registry/digests、相應測試與文件，以及本次按風險判定 scan 的規範修改。
未變更 sandbox、授權、工具能力、資格驗證、資料存取或安裝執行行為；
規範仍要求安全邊界變更或具體安全疑慮時掃描，沒有類別自動豁免。
此判定不是 scan PASS；若後續 diff 引入上述影響須重新評估。

當前原生 custom role 的載入不由 source 修改證明；離線測試
不建立 CLI/Desktop 模型品質資格。無 live model pilot、usage benchmark 或個人
安裝，沒有啟用觀察排程或記憶功能。


## 按風險選擇掃描與正式 gate

後續維護者要求將 scan 改為依安全影響適用，已同步 AGENTS、exact-head contract、
orchestrator、loop 入口及生成套件。新增規範不豁免安全邊界變更，不以 clean
code review 取代必要 scan；scope 或假設改變須重評。
`tests.test_exact_head_merge_review_contract_docs` 與
`tests.test_release_state_contract`：18 tests PASS；package parity 與 diff check PASS。
先前完整 750 tests 的執行內容、runtime 與程式碼不變，沿用其證據；本輪只增加
文件／規範與生成副本，PR head 的 hosted CI 仍須另行通過。

既有 finding dispositions：R308-01（MUST-FIX，routing fixture）、R308-02
（SHOULD-FIX，跨行模型指引）、R308-03（SHOULD-FIX，歷史歸屬）均為 Fixed，
修正與獨立複審證據見上述紀錄，無 deferred 或 needs-human-decision 項目。

R308-04（SHOULD-FIX，deep merge review 入口舊掃描要求）已同步為中央契約的
適用性判定並更新生成副本，狀態 Fixed；完成獨立複核後才進入 commit。
