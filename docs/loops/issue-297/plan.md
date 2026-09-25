# Issue #297：synthetic 新增／修改與版本一致性

## Bootstrap 與範圍

Issue #297 先建立並讀回 open，再於 GitHub 建立
`codex/issue-297-memory-add-update`，遠端與本機 HEAD/upstream 均讀回
`890961470376ee2cb674f169c9954643381dce43`，工作樹乾淨。主代理為唯一 writer。
GitNexus 以 `--index-only` 刷新本 checkout，1,193 項保護快照前後一致，
包括 AGENTS.md；metadata、目標檔案 digest 與 symbol 查詢均已核對。

## 設計

- 保留 `--create-synthetic` 的既有 stop/resume，新增
  `--create-synthetic --scenario add-update`，無 opt-in 仍零觸及。
- 新情境建立空的隔離 managed root、固定兩版 Git source，再依序
  add → update → 盤點 → stop → resume。每次 mutation 顯示完整候選及來源，
  以各自的 operation/preview digest 確認；update 另呈現與同一前態綁定的舊內容。
- 沿用 GovernanceCore，不修改 schema、版本交易或 production registry。
  新情境限定一筆固定 item；固定 synthetic ports 的 audit 權限只涵蓋本 fixture，
  不使用 audit-only authority provider 授予 mutation。
- 每步用新 core 讀回 proof、current state、完整有界盤點與新舊關鍵詞 recall；
  update 產生 revision 2、保留 revision 1，stop/resume 維持 revision 2。
- 取消、到期、漂移、重播、鎖衝突、儲存／proof／readback／輸出故障或中斷
  均停止相依操作；結果不明不重試、不宣稱 rollback。CLI 不重開既有 root。

## 驗證與交付

新增操作及更新來源透過實際核心與 pinned Git reader 驗證；測試涵蓋
完整內容確認、各階段取消、舊版本不可召回、版本/proof 原子性、防重播、
source/root/state 漂移、受控交易前後及輸出故障、程序退出後 fresh readback。
使用 `scripts/project-python`，執行 focused tests、受影響 audit/G1 回歸、
repository/package checks、隔離安裝驗收、獨立 deep review 與 Security Diff Scan。

本包是 G1 操作能力的部分交付；default-off、空 production registry 不變。
不包含 G2 清除、真實／原生記憶、任意 import/root、歷史 restore、背景操作或
物理耗盡研究。版本影響在本 Issue 評估；候選準備與 tag/Release、部署各自分開。

新增可安裝的 add/update 行為採 pre-1.0 minor 0.28.0，同步 catalog／installer／plugin，
另建本版 candidate note；不改 0.27.0 歷史紀錄。本次未查核 publication truth，
候選內容不宣稱已發布；正式 tag／Release 前須重新核對遠端衝突及合併後 target。
