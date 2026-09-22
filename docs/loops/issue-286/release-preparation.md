# Issue #286：0.25.0 候選準備

Issue #286 建立、讀回後，從 PR #285 合併 commit
`2ab0ace18be4c2874c54c866f1d402e77a51694c` 建立並推送
`codex/issue-286-release-0-25-0`，之後才實作。

## 範圍與版本角色

- Source/package：catalog、installer、plugin manifest 同步 0.25.0；installer
  只變 VERSION，runtime／authority／storage 邏輯不變，generated package 維持 parity。
- Candidate：新增 release note，整理已合併 #272、#275、#277、#279、#281、#283、#285。
- Publication：2026-09-22 唯讀查核 v0.24.7 正式 Release 非 draft／prerelease；
  annotated tag `934d1c0aa985e3a3568a914bbcf19287cf182866` 解參照至
  `aedfdb124b996eb1626999bcbdda0f31abe2382d`，與 Release target 一致。
  當次未見 v0.25.0 tag；這不是可持續沿用的發布狀態，正式 gate 須重查。
- Active guidance：roadmap 補已完成的單次 dispatch、持久 authority、預檢與 pilot，
  明記 production registry 仍空；不維護目前發布版本指標。
- Historical records：原 release notes 與既有驗收紀錄保持不變。

## 隔離安裝／升級驗收

在自己的暫存目錄用 `git archive v0.24.7` 取得正式基線，使用不同 HOME／
XDG_STATE_HOME 分別驗舊版升級與候選 fresh install；清除 installer overrides、
PYTHONPATH／PYTHONHOME，CODEX_CLI 指向隔離區內不存在的路徑。
不執行使用者實際安裝，不寫入真實記憶或 profile。

依序執行以下驗收，group 為 `codex-cli-session-handoff`（含 loop-engineering）：

1. 舊版 `install` 成功，receipt 為 0.24.7、pilot 尚不存在。
2. 候選 `diff` 顯示差異但整個 HOME／state bytes 與 modes 不變。
3. 未加 force 的 `update` 拒絕，所有資料／receipt 不變。
4. 已檢視隔離目標差異後才執行 `update --force`；核對原 loop-engineering
   備份 bytes／modes、候選程式 parity、receipt 0.25.0、後續 diff 無差異。
5. 新程序的已安裝 pilot 預設回 disabled，沒有 stderr。
6. 人為加上局部修改後，non-force update 拒絕且 HOME／state 不變；
   已有 backup slot 的 force update 亦拒絕且不改資料。
7. 另一個空 HOME 的 fresh install 成功，diff 無差異，pilot bytes 與 source 一致。

另跑既有 installer 異常 tests：expanded-group conflict、backup collision、
receipt replace failure rollback、unsafe state mode／symlink。這些驗安全處置，
不要求物理耗盡，也不將 sandbox 模擬當成正式環境資格。
實際執行結果由本次 PR 同 head 證據提供，這份驗收程序本身不是 PASS。

## Review 與發行邊界

必要驗證為 package／release-state tests、上述 installer 故障 tests、offline repo
checks、獨立 docs／deep review 與 Security Diff Scan。PR 後再完成完整 base-to-head
Merge Review、hosted CI、strict receipt 與 dedicated App，不用 precommit verdict 替代。

預計 publication 名稱／tag 為 `v0.25.0`、正文取本版本 release note，非 draft／
prerelease；target 必須等候選 PR 合併後核對，現在不預填 commit、不建立 tag／Release。
本包交付至候選 PR readiness。候選合併、publication、部署及真實記憶啟用均須另有授權。

## 審查處置

R286-01（MUST-FIX）修正 release note 的範圍混淆：本切片只更新版本／文件，
但累積 release 已在既有 delivery group 加入 memory-audit，升級會新增技能。
R286-N1（NIT）修正 SQLITE_FULL 拼寫與繁體字，Issue 本文也同步修正。
原 snapshot 安全掃描未發現漏洞不替代上述修正；修後須核對文件與覆蓋證據。

CI286-01：首輪 PR CI 的最後 observation 到期測試未到達 callback。以 canary 前
受控 1.1 秒延遲重現同一 reached 斷言失敗，確認真實一秒 TTL 可在目標路徑前到期。
修正僅限 fixture clock：accept 前固定 sample，目標 observation 完成才推進兩秒；
保留 reached、items／listed／snapshot_digest 清空斷言，runtime／期限不改。
同樣延遲的修後測試與相關回歸須通過；changed head 重新做完整 Merge Review／CI。
