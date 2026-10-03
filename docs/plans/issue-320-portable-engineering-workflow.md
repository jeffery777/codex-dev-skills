# Issue #320 Portable Engineering Workflow

## Objective And Source

[Issue #320](https://github.com/jeffery777/codex-dev-skills/issues/320) 依使用者要求
延伸 #318：同一工程工作流能由 Codex 或 Hermes Agent 執行，標準一致、原生
執行方式分開。起點為 main `09ca939dc7b3ded636abc8720bf53718a62bc4db`，
Issue／遠端分支讀回後才建立隔離 checkout。#316 分支與未合併來源不在範圍。

## Slices And DoD

1. 建立共用工程階段／證據／能力替代契約；既有 Codex 與 Hermes 入口引用。
2. Hermes 三入口補具體 planning、implementation、verification、獨立 review／
   fix、docs sync、delivery gate 與 checkpoint 接續；必要服務不限定 Codex。
3. 同一固定合成案例由兩入口各自執行，父代理獨立驗 tests／spec 未變、成果與
   文件，另驗 checkpoint／原生 session；functional 與資格分開。
4. 隔離 Hermes install／diff、Codex resource install／generated parity、負向
   回歸、適當獨立深入 code/docs review 與 Security Diff Scan。Blocker 修正重審。

唯一 writer 為主代理；唯讀探索與獨立 reviewer 分離。驗收不依賴 LiteLLM 或
公司環境。不新增自動模型 router、scheduler、managed-memory 或 OS sandbox，
不改 profiles／資格／completion authority，不把有限驗收當全部 runtime 合格。

## Verification Plan

所有 source Python 用 `./scripts/project-python`。Focused tests 覆蓋共同 fixture
的受保護文件漂移、缺件、錯誤成果、symlink 與安全 prepare；Hermes package
驗 dependencies closure。變更安裝共用資源後跑 installer／package／repo checks
與完整 shards。隔離 runtime 檢查逐次核對公開版本、tool schema 與授權；沒有
正式 reviewer／scan／平台證據時負向 gate 仍須 BLOCKED。

固定 fixture 不連網、讀憑證或 dispatch；實際 model 驗收以合成內容及既有明確
選定的訂閱來源，在隔離 playground 進行，不啟用 API fallback 或改持久 provider
設定。原始輸出、身份、source/diff digest、skip/failure、review 收據留 Git 外，
不提交 runtime state。Runtime 啟動若要修復依賴，先停下該操作並分類。

## Delivery And Release

目前授權實作、Issue／初始分支、驗證與審查；commit/content push／PR／merge／
發行／部署／清理另核對有效授權。Source/package 版本沿 main，不採 #316 候選。
新增可安裝能力值得 additive minor；版本與發行 scope 在同 Issue 依整合及完整
驗收重評，不以本計畫宣稱 publication 或 release readiness。
