# Issue #235：MG1 G1 第一個可驗證實作切片

## 基準、順序與範圍

[Issue #235](https://github.com/jeffery777/codex-dev-skills/issues/235)於 2026-09-09
建立並讀回，再建立及推送 `codex/issue-235-mg1-g1-core`；遠端分支讀回為
`eed22ddf41ddb6b525e5f9455737218cd94c01a5` 後才修改程式／文件。
GitHub connector 已確認 G0 PR #230 與 scope/lifecycle PR #234 merged，且最新 main
包含二者；本切片未使用父任務舊分支作基底。

依據是[已接受 G0 生產設計](../issue-213/g0-production-proposal.md)、
[精確 envelopes](../issue-213/g0-production-envelopes.md)、
[範圍與生命週期](../../memory-scope-lifecycle-design.md)及
[原生共存邊界](../../native-memory-coexistence.md)。舊 G0 oracle 及其 false flags 保持原樣。
本次不重做 #222 歷史 finding，也不更動 M1 public API、#188 或機器設定。

最小一致範圍是單專案 schema＋trusted port＋空 production registry＋SQLite 交易核心，
及隔離 synthetic roots 的測試。核心新增內部 storage 模組，讓檔案／SQLite 邊界與
host orchestration 分開審查。content/profile 完整驗證與 G1 subset preview/proof/readback
均有界；G2 enum 仍保留，G1 對未實作能力明確拒絕。

## 本切片 DoD

- 嚴格資料與 UTF-8 上限、來源／scope／policy／revision 綁定。
- default-off；可信 host 授權與 caller JSON 分離，production registry 空。
- add/update/restore/stop/resume 原子更新版本、current-only projection 與 proof；
  stopped 更新不自行 resume，舊 cue 無法從歷史召回。
- fresh readback 重建狀態與 proof；例外／重開／重播不自動重送 mutation。
- snapshot audit、協作鎖、journal 零變更拒絕、數量／容量限額與 clock/revision 衝突。
- pinned Python/PyYAML、焦點與完整 deterministic tests、offline release-state、package
  parity、diff/docs coherence、正式 code/deep/docs review、Security Diff Scan。
- PR 後另有完整 base-to-head exact-head Merge Review、hosted CI、receipt readback、
  dedicated App 與 required checks；全部通過後依既有明確授權合併。

## 後續與發版判斷

首切片沒有真實 host/source/confirmation adapter、自然語言入口或 production storage
qualification。G2 才實作清除／維護、跨儲存與全域 backend 的另外接受項；G3 彙整資格。
不讀私有記憶、不 dual-write、不自動 recall/write、不 migration，不擴張 native 權限。

初步不另發版：本切片不能安全管理真實資料，G2 內容清除與維護空間、temp/peak、
真實 source/host、最壞延遲等資格仍缺。新增核心檔案會隨既有 allowlist 產生 package，
不能因此宣稱沒有 installed-source 差異；它們的 production registry 與人類入口仍關閉。
source/package 維持基準版本；不建立新 candidate，不改歷史 release note，不把 package
parity 視為 publication truth。最終五類版本判斷與實際驗證見
[交付證據](verification-and-review.md)。若最終改為適合發行，版本/candidate 與待辦仍
留在 #235；實際發布、安裝、部署另有授權邊界。
