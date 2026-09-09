# Issue #237：依角色與當次需求校正提示詞

## 基準與順序

[Issue #237](https://github.com/jeffery777/codex-dev-skills/issues/237)先建立並讀回，
再從 `ea461332da1fb06b188ecf56498c01ca93df74ee` 建立
`codex/issue-237-contextual-prompts`，遠端分支讀回同 SHA 後才編輯。
父代理為唯一實作者；獨立 reviewer 唯讀。#235 / PR #236 已合併，保留 G1
首切片；依使用者指示，後續里程碑先讓位給本 Issue。

## 工作包與 DoD

1. 在既有 reusable-workflow contract 定義當次組合及決策條件；分開事實與
   指令優先序、主代理與子代理權限、已授權續行與真正待決事項。
2. 對齊 delivery／orchestrator／implementation／continuation 入口，修改
   task brief、next-session 與 loop-handoff 範本；新增欄位為文字指引，
   不變更 route／receipt schema，也不直接切換模型、effort 或 qualification。
3. 必要驗證完成後以漂移／失敗／疑慮決定重跑，保留獨立審查、完整 changed-head
   Merge Review。receipt 授權發布／讀回先於 App verdict，合併 gate 不放寬。
4. 指南與[案例 oracle](prompt-cases.md)覆蓋角色、授權、風險、effort、mid-turn
   steering 與證據新鮮度；獨立語意 review 不冒充真實模型測量。
5. Source/plugin 與 filesystem 入口可達，補足 task-continuation 引用驗證。
   使用 project-python 執行既有相關測試、完整 shards、repository 與 release
   離線檢查、package parity、diff 檢查，完成獨立 code/deep/docs／security review。

## 版本判斷

建議同 Issue 準備 `0.24.2` patch：此差異修正已安裝 workflow 的指令歧義，
不新增模型路由、effort profile、授權來源、資料 schema 或 runtime controller。
指引應有可辨識的安裝版本，因此有發行價值。

完整 release 範圍不能只看本 Issue。Pre-commit 使用 `git diff v0.24.1`，
搭配新增檔案清單及當前內容 digest，涵蓋已提交與尚未提交的來源；commit 後
改以 `git diff v0.24.1..HEAD` 核對不可變範圍。其間 #231 的
scope/lifecycle 合成工具與 #235 的 G1 contract/host/storage/core、governancectl
及 reference 已合併，會隨此版本帶出；production registry 仍空、預設關閉，
proposal 只是有界 schema 檢查，沒有可用的真實資料管理 adapter。這些先前
已審查但未獨立發布的來源明列於 candidate，不能宣稱 release 只有文件差異。
現有使用者可用的管理 backend/API 未被啟用或替換，因此本包採相容修正 patch；
未來新增可用真實管理入口仍須另評估 feature release 與資格。

五類版本狀態：catalog／installer／plugin manifest 定義 source/package；新
release note 僅為 candidate；publication 另讀回 annotated tag 與非 draft、
非 prerelease 的 GitHub Release；active guidance 不保存 mutable latest 指標；
historical notes 原樣保留。發布前重新核對 tag／Release 衝突與精確合併 SHA。
安裝／部署、個人設定、真實記憶與大量模型評測不在本次範圍。

## 主要風險與處置

- 把自主執行誤讀為擴權：沿用當前有效授權、子代理禁止平台寫入，PASS 不授權。
- 消除過度停止時漏掉真實風險：保留未解決決策、高風險驗證與破壞性 safeguards。
- 共用提示詞影響不同模型：保留 profiles，明示代表性配對評估方法與未測限制。
- qualification 僅靠 profile digest 漏掉模板漂移：要求另查實際載入指令及 evidence。
- 包含先前未發布核心：以完整 release range 檢查、清楚揭露 default-off 與資格缺口。
