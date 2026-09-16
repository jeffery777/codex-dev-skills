# Issue #259：整合審查與驗證證據

## 已核對起點與範圍

2026-09-16 讀回 Issue #259、建立並 push
`codex/issue-259-integration-review-evidence`，再讀回遠端 ref，才開始 tracked
實作。起點 `476d2437519965e44e97de3423041852104c80e5`。

當時最新正式 Release 為 v0.24.3，Release ID `389601078`，
`draft=false`、`prerelease=false`；annotated tag object
`0499fa26172f814232fb5ccc7f81e6ea8135791f` 解參照至同一起點。
Release／tag-object 的 connector 操作不存在，按
`connector-operation-unavailable` 使用 `gh api` 唯讀 fallback。
這是點時證據，發布前仍須重查。

## 交付

1. code-review 短入口與共用 integration reference；deep review 引用同一份。
2. task brief 的可選執行與邊界證據，不增加固定框架、全套矩陣或 routine gate。
3. source／generated plugin 可達性與 parity、合成 oracle、必要 repo checks。
4. 固定 Astra 的有界指令配對 pilot，沿用 #223 ME-01；ME-02 reviewer
   replacement 與 ME-03 profile/effort 資格保持獨立未完成。
5. 獨立 review／Security Diff Scan、PR、完整 exact-head 及 GitHub gates。

不修改 routing、test sharding、installer 邏輯、全域 profile、個人設定或 harness。
所有 fixture 為合成；沒有公司環境、input、主機、secret 或原始 logs。

## 發行判斷

相較 v0.24.3 起點沒有其他未發行 commit。這次提示與範本會隨技能安裝，
提供可重用的接點檢查與驗證證據指引，具有獨立交付價值；不是只發研究紀錄。
選擇相容 patch `0.24.4`：沒有新 workflow、public API、強制 gate 或資料格式，
只是補強既有 review／brief。完整候選範圍包含 review／brief 補強、可達性測試、合成
pilot 證據與版本同步。沒有節費證明不阻止此品質改善；品質／續行 regression
須先處理。發布取決於全部必要 gates，不由此計畫或版本 parity 宣告完成。

## 設計審查處置

- O-01：Fixed。A/B 比較整組 skill＋brief 提示；不拆分因果效果。
- O-02：Fixed with limitation。fresh CLI context、固定 bundle/digest，排除 oracle
  及其他 run 輸出於 prompt；共用主機無 filesystem 讀取隔離，不宣稱 blind
  security isolation，實際指令 trace 檢查是否越界／污染。污染樣本保留但不採信。
- O-03：Fixed。四個接點可獨立呼叫重現，控制 suite 與 bundle suite 分開；
  第一個失敗不阻止其他檢查。這是新檔案的整體審查，非每項都宣稱由某一行
  變更造成既有功能回歸。

Owner：本次 delivery owner；評分與限制見 [pilot results](pilot-results.md)。

執行中發現的 read-only filesystem 與排程限制，追加至
[偏離紀錄](pilot-deviations.md)，不改寫凍結的 trial plan。受限 pilot 不延伸
成正常 Runner、完整交付節費或 profile 資格主張。
