# Issue #253：G1 儲存故障與恢復驗證

2026-09-11 核對 `jeffery777/codex-dev-skills`、connector 身分 `jeffery777`、
乾淨獨立 worktree，fetch 後 `origin/main` 為
`b7d245646568c0397f5c516e2f6972f1b4e91fa1`。#248 已合併，#247 已結案。
查重、建立及逐字讀回 [Issue #253](https://github.com/jeffery777/codex-dev-skills/issues/253)
後才建立、push／readback `codex/issue-253-g1-storage-faults`，基底 SHA 相同。
本任務唯一 writer；saved main、#242／#247／#251 worktrees 不在操作範圍。

## 第一個有界切片

沿用 [G0 儲存契約](../issue-213/g0-production-proposal.md)、
[envelopes](../issue-213/g0-production-envelopes.md)及
[#247 fresh readback](../issue-247/process-loss-contract.md)。
不改歷史 #245／#247 觀察，不重新實作 process-loss 契約。

- 新建合成 Git／SQLite；先正常 add，再以不同 cue／較大 payload 更新，核對
  transaction 的版本、current projection、完整 logical digest 與 proof。
- quota 的 error 13、注入 errno 28、physical ENOSPC、SQLite FULL、CANTOPEN
  分開分類。物理實驗在 journal 已建立的 `before-commit` 填滿自己的映像；
  不能因已有 OS ENOSPC 就宣稱 SQLite FULL。
- 失敗後拒絕 consumed handle；釋放自己的 filler 後用新 subprocess、fresh
  authority／source 讀回原 normal operation 與失敗 operation。缺 proof 的
  ID-only readback 仍是 unknown；只有已驗證前態可支持實驗的一致性結論。
- 非空 journal 先拒絕開庫；需要 repair／maintenance 才能恢復時保留現況、
  記錄 incomplete，G2 recovery 不在此包。
- 以 test-only instrumentation 包住成功 flock 與 close，記錄完整持鎖區間的
  syscall 前後時間界限；檔案大小取樣涵蓋 main、journal、sidecar、獨立 temp
  目錄及測試子程序的有界 fd metadata。取樣最大值不提升為 workload 上界；
  無法觀察的短暫／記憶體 temp 明列缺口。

## 物理測試前置與回收

預設 dry-run；明確 `--run` 才建立自己的 256 MiB APFS image，不接受現存映像
或 volume。至少 1 GiB host headroom，attach 回應、diskutil filesystem、mount
與 device／inode 都要核對；只在確認的獨立 filesystem 建檔、填寫自己的 filler。
每個指定模式一次，不盲重試；external command、worker、filler loop 各有期限。
回收僅截短本程序建立並核對的 filler descriptor；正常 detach 後保留映像與
結構化報告。身分未知、截短／detach 失敗就保留，禁止 force／repair／broad kill。

## 驗證與交付邊界

Python 由 `./scripts/project-python` 選到 3.12.9，PyYAML 6.0.3。
先 focused contract/fault tests，再完整 deterministic shards、offline validation、
generated parity、release-state、diff hygiene。commit 前獨立 code/deep/docs review
及 Security Diff Scan；PR 後完整 exact-head content review、required CI、strict
receipt 發布／逐字讀回、dedicated App 及平台 gate。授權到 PR readiness，禁止 merge。

目前預期只改 tests/fixtures、本 Issue 文件與直接相關 active docs；沒有缺陷證據
就不改 production code。source/package 沿用 catalog.yaml；不新增 candidate、
tag／Release、安裝或部署。production registry 永遠空且 default-off；不接觸
真實／native memory、runtime 私有狀態，不啟用 backend、dual-write 或 migration。
完整 J/T/G、4 GiB 最壞鎖定時間、power-loss、production qualification 及 G2/G3
仍為獨立工作；本包不得宣稱完整 G1／MG1。
