# Issue #271：交易前容量壓力的追加觀察

## 結果與證據

依[追加計畫](pretransaction-plan.md)完成新增的一次 256 MiB APFS image 試驗，
兩包合計兩次。filler 移至目標 writer connection／BEGIN 前，當時 journal 確實
不存在；OS 回報 ENOSPC 後，SQLite 仍成功提交。因此這次仍為
**incomplete / os-enospc-only**，沒有 physical SQLite FULL，也沒有該失敗後的
fresh-authority 正常 control。[去識別摘要](pretransaction-observation.json)保存
本次來源指紋與結果；[第一次紀錄](verification-and-review.md)保持原有點時內容。

| 本次觀察 | 可支持的結論 |
| --- | --- |
| `before-transaction`；journal 為 absent／bytes null | 壓力在目標 writer 開啟前施加，不能把不存在的 journal 說成零 byte 實測。 |
| own filler 寫入 260,046,848 bytes；三種 block size 均遇 errno 28 | OS 拒絕 filler 寫入；不是 SQLite error 13。 |
| page_count 12；profile／effective max_page_count 都為 1,048,576 | 沒有 page-quota 注入或 quota 降低；SQLite errors 為空集合。 |
| update applied、revision 2；fresh readback digest／proof 與 writer 相符，green 1／blue 0 | 交易成功且 current projection 一致；不能宣稱失敗交易保持原狀。 |
| 歷史 add 為 state-unknown、proof 保留；消耗過的 handle 拒絕重播 | 不把較早操作誤認為當前 applied，也沒有恢復 mutation handle。 |
| own filler 截短、可用容量增加，之後 fresh reader 檔案摘要不變 | 已觀察容量恢復與唯讀讀回；未做 DB／journal repair。 |
| 正常 detach、事後 exact-image attachment 零匹配、mount 未附掛，image 身分及上限符合 | 新 image 已卸載並保留；未重新附掛任何既有 image。 |

writer／reader 沒有 timeout；fresh reader 使用自己的 authority 且不呼叫 accept。
協調器因缺少「失敗交易」前置條件而不執行 recovery control，不能用成功交易後的
讀回替代此項驗收。兩次試驗都沒有證明 SQLite 為何仍能寫入；不將剩餘容量取樣
或 APFS 保留空間推測當成根因，也不為取得 FULL 放寬分類。

## 實作與無物理故障驗證

修改只在 repository-only fixture、tests 與文件。worker 使用既有 core checkpoint，
以 `lstat` 區分 journal 不存在、空檔、非 regular 與查讀失敗；非空 journal 在填充
前拒絕。早期 fixture 例外保留有界診斷、空 proof／state，協調器仍依實際讀回判斷。
dry-run 預覽同步新的 fault stage。core、SQL、page quota、錯誤分類與 production
registry 不變；未取得 writer quota 時仍不能證明 FULL 的物理來源。

- 新增三項測試，含五類早期失敗子案例，驗證 writer／fill 順序、journal 邊界、
  quota 不變、先 restore 再 readback、一次 restore、拒絕重播與不啟動 control。
- 首次測試 helper 在主測試程序執行而未符合 observer 的 FD census 邊界；改為
  獨立子程序並套用同一 descriptor 上限後，相關 14 項通過，完整模組 29 項通過。
  初次失敗保留在本地紀錄，沒有將其算成通過。
- 試驗前獨立 deep review 發現 PR-271-03（MUST-FIX/P2）：本地 preview driver 的
  `select` 後接 `readline` 未保證整體 60 秒上限。改成總 deadline 與有界 `os.read`，
  完整 token、無 newline、超長、錯字及 EOF 五例通過，再審為 Fixed／PASS 後才試驗。
- 全部 shards、checks-only、package parity、offline release-state、最終 code/docs
  review、安全掃描與 changed-head Merge Review 的結果，綁定最後提交版本保存在
  PR 證據；此物理紀錄不替代那些 gates，也不將尚未完成的檢查視為通過。

驗證沿用本 worktree 的 `.venv`，以 `.venv/bin` 前置 PATH 並使用 tracked
`./scripts/project-python`；Python 3.12.9 與 PyYAML 6.0.3 已確認。
可重跑的無物理故障檢查沿用[第一次驗證清單](verification-and-review.md#驗證與審查)。
`--run` 不在重跑集合；這次新增額度已耗用，不再執行第三次物理試驗。

## 剩餘責任與交付限制

MR-272-01 仍阻擋 Issue 完成與 merge readiness：physical SQLite FULL 與該失敗後
fresh-authority 正常 control 尚缺。責任人為 G1 storage／Issue #271 delivery owner。
再次進入物理驗證前須先重新評估方法，提出與兩次既有觀察一致的有界新方案、
精確資源與恢復預覽，並取得新增試驗授權；不能直接增加次數、擴容或自動 retry。
非空 journal recovery 仍屬 G2，不在本包修復。

PR #272 維持 draft、Issue #271 維持 open；不加會關閉 Issue 的引用，不以部分
觀察通過 repository 的 ready-PR gate。原始 host capacity、機器與裝置身分、路徑、
PID、OS release 僅留本地，公開 summary 使用明確白名單。
取樣仍不證明完整 J/T/G、temp envelope、maintenance reserve、power-loss 或
4 GiB 最壞延遲。default-off、空 production registry 與未 qualified 狀態維持。

沒有可安裝行為變更，不另發版；catalog 的 source/package 版本維持 0.24.7。
本包不新增 candidate，也不改寫既有 release notes 或追蹤最新 publication 斷言。
