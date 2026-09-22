# Issue #284：驗收與審查範圍

## 已實作

獨立 pilot default-off；只有確認建立才產生自己的固定 synthetic fixture，沒有 root／
JSON／resume loader。私有 seed 沿用 core initialize／add／proof／readback，完成後
封閉寫入 ports，再以 audit-only binding 組合既有 provider／preflight／canary。
兩次確認分別接受建立 fixture 與本次精確 target 的 audit；後者等待結束後重查環境。

## 可重跑驗證

```sh
./scripts/project-python -m unittest tests.test_memory_audit_pilot -q
./scripts/project-python -m unittest tests.test_memory_audit tests.test_memory_audit_adapter tests.test_memory_audit_authority tests.test_memory_audit_dispatch tests.test_memory_audit_preflight tests.test_governancectl -q
./scripts/validate-repo.sh --skip-unit-tests
```

Pilot tests 涵蓋 disabled／未知參數零接觸、建立前與預檢後取消、等待期間期限／權限
漂移、Ctrl-C／輸出失敗的 owner close、部分初始化保留、managed bytes 不變，以及
真正隔離 HOME 安裝後從空 cwd／新程序執行 source package 與 plugin 入口。

Authority 故障矩陣在真實 SQLite connection 的 INSERT／UPDATE、commit 前／後與
readback 受控注入 FULL/BUSY/IOERR/NOMEM、ENOSPC/ENOMEM、unknown，驗證不重試、
instance 停用、connection／lock 釋放、舊 request 拒絕及新接受成功。Source reader
I/O／memory 失敗驗摘要遮蔽；最後 disclosure 的 close/revoke 驗內容／digest 清空。
這些是處置證據，不是物理耗盡或 production qualification。既有 audit regression
另涵蓋 fork／restart、未知 commit、source identity/hash、schema 與 envelope。

Focused tests、repo checks、package parity、獨立 code/deep/docs 與 Security Diff Scan
的實際結果由本次 PR 證據保存；PR 後須完整 exact-head Merge Review／CI／receipt／App。
本文件只描述驗收來源，不能代替那些 gate，也不授權 merge／發版／實際安裝。

## 設計處置

- fixture 不引入 tests/docs loader，使用固定三個 loose objects，不執行 Git。
- bootstrap 與 audit 權限分開，seed callback 比對固定 binding／candidate／item／operation；
  finally 封閉 ports，不提供再次寫入入口。
- 預檢不提前 accept；未讀內容及無 request 的 unknown/missing 不粉飾為通過。
- 等待確認後重查必要 metadata／qualification；不默默延長 synthetic TTL。
- 外層區分 fixture／authority 寫入，內層 managed audit 唯讀；終止保留資料。
- pilot 程式納入 ports fingerprint；安裝內容改變使既有資格失效。

## 發行評估

2026-09-22 以 GitHub 正常控制面唯讀核對：正式 `v0.24.7` Release 非 draft／prerelease，
annotated tag object `934d1c0aa985e3a3568a914bbcf19287cf182866` 指向
`aedfdb124b996eb1626999bcbdda0f31abe2382d`，與 Release target 一致。
這是當次觀察，不是可持續沿用的目前版本指標；發行 gate 必須重新核對。

該版本之後已合併異常處置及 audit report／adapter／dispatch／authority／preflight，
本包再補受控 synthetic 操作入口。功能屬新增且維持 default-off，故可將 **0.25.0**
列為下一個候選版本建議；不能把此候選描述成實際專案記憶已可正式啟用。

建議在本包完整驗收及合併後，另開有 Issue 的 release-preparation 切片：更新 canonical
source/package 與新 candidate note、檢查安裝／升級行為、審查上述五種發行狀態，
再由 exact-head gate 評估 publication。此 PR 的 catalog／installer／plugin version
維持 0.24.7；不改歷史 release notes，不建立 tag／Release。未完成本包 gate 前不能
宣稱可立即發行，正式 publication 仍須單獨授權。

## 審查處置 R284-01

第一輪獨立 code/deep/docs review 重現持續 stdout write／flush 失敗，handler 再次
寫同一通道而讓原始例外逸出，disabled 也未受保護。已改為固定內部 output-failure
訊號、外層 exit 2、停止原通道重試及 provider finally close；CLI shutdown 的 buffered
flush 轉到 null sink，避免再次對 broken pipe 拋錯。新增持續 write／flush 的 disabled、
建立前、確認前與 report 階段測試，以及實際已關閉 pipe 的 subprocess exit／stderr
驗證。此項為 MUST-FIX，不能以初輪安全掃描無可報告漏洞取代修正；修後另行重審。
