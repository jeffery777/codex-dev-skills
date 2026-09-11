# Issue #247：G1 process-loss readback

2026-09-10 核對 jeffery777/codex-dev-skills、PR #246 merged、Issue #245 closed，
遠端 main 與本 worktree HEAD 為 `2db0b29a5f20d6b7f342874f6a1d3d22cacbd288`。
查重後建立並逐字讀回 [Issue #247](https://github.com/jeffery777/codex-dev-skills/issues/247)，
再建立、推送及讀回 `codex/issue-247-g1-process-readback`，SHA 同上，之後才寫 tracked 文件。
本 task 為唯一 writer；獨立 reviewer 只讀；不操作父 worktree／saved checkout。

先完成[契約草案](process-loss-contract.md)與主代理檢視，再實作 contract/core/storage、
新 subprocess fixtures/tests、必要 active guidance 及 generated plugin counterpart。
2026-09-11 使用者確認已安裝 reviewer 的 model/effort 差異是刻意設定，本輪沿用
Astra/xhigh 唯讀 reviewer；不修改 profiles/router/config，不宣稱 canonical router
通過。獨立審查與 Security Diff Scan 仍為 commit 前必要證據。
source/package 版本保留 catalog.yaml 0.24.2；不準備 candidate、發布、安裝或部署。

Python 已由 ./scripts/project-python 選到 3.12.9，PyYAML 6.0.3；使用既有 worktree
環境解析，不複製 .venv。後續需焦點／回歸、全部 deterministic shards、offline
validation、package parity、release-state、diff hygiene，及獨立 code/deep/docs review
與 Security Diff Scan。完整 bounded DoD 後才建立 PR，進行完整 exact-head Merge
Review、CI、strict receipt 發布／讀回、dedicated App 及合併前 live gates。

本次不處理 #242／PR #244、#188 cleanup、#222 歷史 finding、G2/G3、native/真實
memory、dual-write、migration 或 runtime 私有狀態；局部 G1 不代表完整 MG1。
