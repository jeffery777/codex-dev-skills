# Issue #304：單專案 memory-maintenance

## 目標與邊界

以既有 GovernanceCore 的 add／update／stop／resume／restore 為唯一 mutation
路徑，新增可安裝 shared 薄入口及可信程式整合。既有 pilot 保留作回歸。
僅支援 host-owned 單一本機 POSIX root 與 PinnedGitReader 固定 Git artifacts。
default-off、manual、空 production registry；不讀寫既有、原生或外部 memory。

不新增 schema migration、持久 authority store、跨程序 handle 恢復、G2 或
任意路徑／loader。Process-local provider 僅保存本次 host 已接受要求；重啟
全部失效。SQLite proof 與核心 RAM handle 分別負責 durable evidence 及單次執行。
同一 OS 使用者的任意 Python 執行仍在 TCB 外的隔離保證之外。

## 實作順序

1. 意圖 schema、獨立 mutation grant、host factory／dispatch。Audit grant 不相容。
   Scope/root、來源接受、雙時鐘、撤銷與各 operation qualification 由 host 提供。
2. Core preview 原樣交給 host confirmation port；等待不持 DB 鎖，執行前重新
   驗證。只 execute 一次，再以新 core／reader 讀回 proof、revision 與 projection。
   Readback 不明或輸出失敗不重播、不宣稱 rollback。
3. CLI 與 Desktop 薄 adapter、advisory preflight、隔離 canary、skill／docs／catalog
   及 generated package；入口缺少正式 source／confirmation port 時 unavailable。

## 驗收與審查

- 五操作同入口的 synthetic Git／SQLite E2E；current-only、新舊 cues、retained
  versions、proof／audit／新 reader 一致。Off 路徑零觸及。
- Scope/root/operation mismatch、TTL、撤銷、source/state drift、grant/handle/digest
  replay、contention、process restart。等待中的 state change 不可通過舊 preview。
- 真正核心／SQLite 路徑注入交易前、item/proof/commit、讀回及輸出故障；結果為
  applied、not-applied 或 unknown，未知不以例外推定未提交。
- 使用 tracked resolver 執行 focused、affected regression、repo checks 與完整
  shards；generated parity、隔離 install／upgrade。
- 獨立 deep review、Security Diff Scan、修正並重審；PR 出現後另做完整 exact-head
  Merge Review、CI／receipt／App readback。

## 交付決策

實作期間不改 canonical version。完成新增入口與全部 DoD 後評估 minor 版本價值；
merge、tag／Release、實際部署及 production 啟用仍是獨立授權邊界。
隔離 host 成功不代表真實 CLI／Desktop ports 已可用，也不證明完整 G1／MG1 資格。
