# Issue #265：G1 儲存可靠性與恢復驗收

## 順序及所有權

先唯讀核對 Git／origin、現有 Issue／PR、G0 契約與 #245／#247／#253 的
證據，再建立並逐字讀回 [Issue #265](https://github.com/jeffery777/codex-dev-skills/issues/265)。
之後才從 `11cee975f120b0a2389022722b264a4b69db9f5c` 建立及推送
`codex/issue-265-g1-storage-reliability`；HEAD、upstream 與遠端分支讀回相同，
再開始 tracked edits。原始 bootstrap 僅在乾淨 detached worktree 進行。
主代理是唯一 implementation writer，子代理僅做有界唯讀分析／獨立審查。

公開材料不含本機路徑、主機／OS 版本、device／mount／inode、PID 或私有 runtime
身分。原始診斷留在本地；公開證據只列去識別的合成測試結果與來源 digest。
歷史 #245／#247／#253 記錄保留原貌，不回填或重綁先前數值。

## 工作包

1. 分類 #253 的 image-create 失敗；以公開文件及受支援 help 核对空白 APFS
   image 的建立方法，保留未知原因。先 dry-run，再在全新隔離映像做一次有界試驗。
2. 維持 OS ENOSPC、quota SQLITE_FULL、physical SQLite FULL、CANTOPEN 及注入
   errno 的區別。恢復只釋放 own filler；fresh subprocess／authority 驗證內容、
   revision、current projection 與 proof，拒絕 consumed handle。
3. reader／control 使用試驗建立的隔離 temp 目錄，加入 named／own-fd 取樣、
   filesystem 可用容量及完整 flock 區間。每條連線讀回有效 pragma，不把 writer
   profile 宣告當 reader 設定，也不把取樣最大值當 J/T/G 上界。
4. 只修有證據的 fixture／核心缺陷，補負例與直接相關文件。沒有 production
   缺陷證據就不改可安裝核心；production registry 維持 immutable empty、default-off。

## 資源、恢復與停止條件

使用新建 test-owned 合成 Git／SQLite roots；image 上限 256 MiB，host headroom
至少 1 GiB，單一隔離 filesystem。image-create 一次；commands 60 秒、writer 90 秒、
fill loop 30 秒、reader/control/restore 30 秒。填寫前驗證獨立 mount／device／inode，
只截短同一 verified own filler。正常 detach 後保留映像；不 force、repair、blind
retry、broad kill、擴大容量或放寬 sandbox。

未知 mount、非空 journal、釋放容量失敗或需 G2 recovery 時停止相關依賴操作，
保存 incomplete 與確切缺口，繼續獨立量測／回歸。unknown 不能改為 not-applied；
模擬成功不能當物理驗收。真實/native memory、M1、migration、dual-write、backend
啟用、自然語言入口、G2/G3 均不在本包。

## 驗證與交付

所有 Python 使用 `./scripts/project-python` 的 tracked interpreter；先確認 PyYAML。
focused contract/fault tests、deterministic shards、offline validation、package parity、
release-state 與 diff hygiene。commit 前獨立 code/deep/docs review 及 Security Diff
Scan；PR 後完整 exact-head Merge Review、required CI、strict receipt／逐字讀回、
dedicated App／ruleset 及最終 live readback。

已授權 commit/push/PR/receipt；merge、tag/Release、安裝/部署不沿用其他 PR 授權。
最終 diff 決定是否在同一 Issue 準備新版本；repository-only fixtures／tests／文件
不構成已安裝功能改變。完整 J/T/G、4 GiB worst-case、power-loss 與 production
qualification 仍須另外完成，不由本切片推定。
