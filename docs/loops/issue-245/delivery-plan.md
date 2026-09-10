# Issue #245：G1 本機執行介面與端到端驗證

## 基準與所有權

2026-09-10 以 GitHub connector 確認 main 為
`4bfb67c2d62cfca2012ab3a0635676fa386eca4b`，#235／PR #236 已合併。
查重後建立並逐字讀回 [Issue #245](https://github.com/jeffery777/codex-dev-skills/issues/245)，
再建立、推送及讀回 `codex/issue-245-mg1-g1-execution`，SHA 與上述基準相同，
之後才修改 tracked 檔案。本使用者任務為唯一 writer；reviewer 唯讀。
不沿用或操作 #242／PR #244、#188，不改 M1 公開契約或處理 #222 歷史 finding。

## 最小切片

沿用 [G0 production proposal](../issue-213/g0-production-proposal.md)、
[envelopes](../issue-213/g0-production-envelopes.md)、
[scope/lifecycle](../../memory-scope-lifecycle-design.md)及
[native 共存邊界](../../native-memory-coexistence.md)。

- 選定本機 POSIX Python 3.12.9，組合實際 UTC／monotonic clock、host-owned 單 root
  registry、固定 repo artifact 的有界內容綁定，以及明確注入的 artifact reader、source review、
  confirmation、readback authority、storage qualification ports。
- Git bytes／digest 只證明來源綁定；內容支持、適用前提、敏感性與 eligibility
  仍須獨立 source reviewer。沒有 production source/confirmation/qualification
  時保持不可用，不從候選、檔案、參數、TTY 或記憶建立接受。
- 用新建 synthetic Git repository 與 SQLite roots 串接上述元件；合成測試才提供
  明確標示的 source review、confirmation 與 budget TCB。原 production registry
  保持空，governancectl 不增加 mutation／root／adapter flags。
- 通用 Git reader 不在本切片：config include、alternate object store、隱含 fetch
  與 filesystem 範圍仍須獨立保證；Git helper 只操作 fixture 自己新建的 tiny repository。
- 端到端驗證所有 G1 操作、有限歷史、current-only projection、readback、拒絕與
  process restart。固定 SQLite build／OS／filesystem 量測故障及容量；將實測值、
  受控故障注入、取樣下界、未測上限與缺少 qualification 分開記錄。

## 正式控制面查核

當次公開 Desktop 工具提供使用者提問，但沒有可直接供本機 Python host 認證的
MG1 source attestation、revocation、preview-confirmation 或 qualification registry。
[官方 Approvals](https://learn.chatgpt.com/docs/app-server#approvals)說明 shell、
檔案、permissions、MCP elicitation 及實驗性 user-input 回應；此文件沒有建立
MG1 完整 preview／source／scope／readback 的 host 接受契約。一般 shell 核准也
不能直接替代它。這是本次可用介面的缺口，不聲稱所有未觀察 API 都不存在。
本切片不啟動 app-server、不注入工具、不讀取私有狀態、不自動回答人類確認。

## 驗收及後續 gate

焦點 tests、故障注入及 M0/M1/V2b 回歸後，執行 deterministic shards、offline repo
validation、package parity、release-state 與 diff hygiene。新 installed source
須生成相同 bytes 的 plugin counterpart。獨立 deep/code/docs review 與 Security
Diff Scan 通過後才 commit／push／PR 準備；PR readiness 另綁完整 exact-head
Merge Review、CI、receipt 發布讀回與 dedicated App。

本次結果與限制見[驗證證據](verification-and-review.md)。實際 APFS ENOSPC 已觀察，
但最終 SQLite 為 CANTOPEN、filler truncate 也失敗；正常卸載成功，實驗仍 incomplete。
production human/source adapter、持久撤銷與 host registry 保護、完整 temp envelope、
4 GiB 最壞鎖定時間及 maintenance reserve 仍須各自取得資格。G2 清除／維護、G3
整體資格、自然語言入口不在此切片；不以局部成果宣稱完整 MG1。
source/package 保持既有版本，不建立 candidate 或改歷史 release notes。
發版價值留在同一 Issue 評估；merge、tag／Release、安裝／部署另核對有效授權。
