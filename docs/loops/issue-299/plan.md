# Issue #299：synthetic 歷史版本還原

## Bootstrap 與範圍

Issue #299 先於 GitHub 建立並讀回 open，再建立並讀回
`codex/issue-299-memory-restore`。遠端與乾淨本機 HEAD/upstream 均為
`fecbbe7b591fa9e1c65e788a78cbc00e1b94cada`。主代理為唯一 writer；
獨立 reviewer 只讀。GitNexus 先以 `--index-only` 刷新，1,197 項保護快照
前後一致，包含 AGENTS.md 與 Git 設定；status 及有界 symbol 查詢已對照來源。
修改後的查讀使用實際來源，不沿用舊圖譜宣稱當前 qualification。

## 設計與 DoD

- 在同一 shared pilot 新增固定 `--create-synthetic --scenario add-update-restore`。
  原 stop/resume、add/update 情境及無 opt-in 的零觸及保持相容。
- 當次新建空 synthetic fixture，依序 ADD、UPDATE、RESTORE；每步完整 preview、
  獨立 digest 確認與來源驗證。不接受任意 root、正文、import 或既有 workspace。
- RESTORE 顯示與 preview 同一前態綁定的 current 與指定保留 revision 1，
  包含完整內容與來源；重新驗證固定 Git artifact，使用新 validation/evidence。
  沿用 GovernanceCore 既有 restore，不改 schema 或 production registry。
- 還原產生 revision 3，保留 revisions 1/2；一般 recall 只命中 current，
  fresh readback、audit 與新舊關鍵詞均須一致。舊 revision 不復用為 current。
- 覆蓋取消、到期、來源／root／state 漂移、handle/digest 重播及受控交易前後、
  readback／audit／輸出故障。未知停止、不重送 mutation、不推論 rollback。
- 使用 pinned project Python、focused 與受影響回歸、套件 parity、隔離安裝
  驗收、獨立 deep review、Security Diff Scan 及適用 formal gate。

## 交付與排除

新增可安裝操作能力，沿用 pre-1.0 minor 慣例準備 source/package 0.29.0，
同步 catalog、installer、plugin 與獨立候選 note；不改寫歷史 release notes。
候選準備不表示發布，tag／Release／部署仍依當次授權與精確讀回。

維持 CLI／Desktop 獨立入口與共享核心。未包含真實／原生記憶、production
啟用、G2、背景服務、物理耗盡研究或完整 G1/MG1 qualification。
Issue／分支規範只約束本 repository，不向其他使用技能的專案傳播。
