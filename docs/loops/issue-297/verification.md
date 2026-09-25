# Issue #297 驗證紀錄

## 行為與故障 oracle

以 pinned `scripts/project-python`、實際 GovernanceCore／SQLite／PinnedGitReader 測試，
不使用真實專案或原生記憶。受控注入不是物理耗盡證據。

| 邊界 | 驗收條件 |
| --- | --- |
| 預設與取消 | scenario 無 opt-in 零觸及；ADD 取消後 items／versions／proofs 零筆，後續取消只保留已確認寫入。 |
| 完整 preview | ADD 完整候選；UPDATE 舊內容來自與 preview 相同 snapshot，新版來源不同且相符。 |
| 版本與查詢 | revision 1 → 2 → 2 → 2；舊版除 retired_at 外不變，舊專屬或新舊混合詞查無，STOP 查無，RESUME 仍 current v2。 |
| 漂移與重播 | 顯示前／等待中 state 漂移、期限、來源、root、鎖衝突拒絕；已消耗 handle 不可重送。 |
| 交易與 proof | add/update item-write、before-commit 注入回前態；after-commit 新讀回判 applied；proof insert 故障不留下半套新版本。 |
| 提交後未知 | fresh readback、audit 或中斷失敗保 state-unknown，保留 fixture，停止後續操作。 |
| 輸出與程序 | ADD confirmation 輸出故障不寫；UPDATE 提交後輸出故障保留兩 proof；POSIX 子程序提交後退出，新 core 可讀回，舊 grant 不復活。 |

首輪新舊 maintenance 及 audit pilot 測試全部通過；發現 unittest 載入測試模組時
重複收集匯入的 test class，已改為 module reference，後續統計排除重複收集。

## 實際驗證結果

- 新 content pilot 11 項、原 maintenance/audit pilot 30 項皆通過，independent reviewer
  另行執行同組驗證。較廣的 core/local/process/storage/audit/authority 回歸及 shard
  檢查共 188 個實際測試通過；該命令另因兩個誤填模組名稱產生 loader errors，
  不將該次 command exit 1 說成整體通過。
- 修正模組名稱後，release-state／plugin packaging／test shard 共 34 項通過。
  候選準備曾漏改 plugin version 及缺少 validator 的固定 gate 字串，已修正並重驗；
  不是產品 runtime 故障。另 2 項 CLI／Desktop installer 分層回歸通過。
  去除重複執行後，共 216 個不同測試通過。
- `./scripts/validate-repo.sh --skip-unit-tests` exit 0；其內嵌 unit-test 群組依旗標跳過，
  不宣稱本機全套 tests。`sync-plugin-package.py` 驗證 140 generated files；
  offline release-state 與 `git diff --check` 通過。
- 隔離 HOME／XDG_STATE_HOME 的 fresh install 與基準 0.27.0 → 0.28.0 upgrade
  均通過。先核對 non-force update 拒絕且 bytes/modes 不變，再 force update，
  驗明舊檔 backup、receipt 0.28.0、installed source parity。`diff --all` 僅指出
  故意未安裝的其他 groups，受測 group 無差異。兩者的 installed CLI 均實際完成
  ADD／UPDATE／STOP／RESUME，revision 1/2/2/2、recall 1/1/0/1；fixture 保留。
  未改使用者日常安裝，未驗證 Desktop 原生 UI 的互動終端呈現。

## 審查與索引

獨立 `code-review-deep`／docs coherence 審查 17 個變更檔，無 MUST-FIX、SHOULD-FIX
或待處置 findings。核對 current-only、snapshot before、固定兩版來源、空 ADD root、
postcommit unknown，以及 source/package、candidate、publication、active guidance、
historical records 五種 release 角色。正式 Security Diff Scan 使用獨立固定
working-tree snapshot 與其持久 scan artifact；本頁不代替該結果或 PR 後的 Merge Review。

GitNexus 收尾刷新遇到 `file_fts` 既有索引不一致；以工具公開的
`analyze --index-only --repair-fts` 修復後重跑。後續 registry 寫入因 workspace
sandbox 拒絕，在核准的 index-only 執行後成功。這是索引／檔案權限事件，
與 #295 killpg EPERM 的根因沒有同一性證據。前後 1,197 項保護快照一致，
包括 AGENTS.md、所有工作修改與 Git metadata；HEAD／branch／兩個主要修改檔的
hash 相符後才查圖。`detect_changes` 覆蓋 17 檔，指向 acceptance/source review
四條 source/generated flows；已由精確 source 與獨立審查核對，不把圖譜計數當完成證明。

## 限制與交付邊界

Default-off、空 production registry、schema 與 shared core 不變。
沒有真實／原生記憶、任意 root/import、歷史 restore、G2、背景服務、清理或 journal recovery。
本包不證明完整 G1/MG1、物理 FULL／ENOSPC／ENOMEM、power-loss、完整 J/T/G 或 production 資格。

候選 source/package 0.28.0，歷史 release notes 不改。遠端 publication truth 本次未查核；
合併、tag／Release、本機部署與正式啟用各自保留授權邊界。
