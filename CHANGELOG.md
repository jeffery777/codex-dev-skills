# Changelog / 變更紀錄

本檔記錄版本範圍及尚未選版的變更，不是目前已發布版本指標。來源版本以
[catalog.yaml](catalog.yaml) 為準；發布事實另核對 annotated tag 與非 draft、
非 prerelease 的 GitHub Release。English entries follow the Chinese entries.

## 0.35.0 — 有限索引寫入候選 / Limited index-write candidate

[Issue #355](https://github.com/jeffery777/codex-dev-skills/issues/355)
分別記錄 CLI `0.163.0`、Desktop `26.1013.40934`／build `20770` 及 bundled CLI
`0.163.0-alpha.10.2`。兩個 CLI 的 public-help／production argv 檢查分開通過；
不證明 live session 或全部入口資格。

新增 GitNexus `1.6.12` 明確本機 library profile：綁定接受的 entry／Node／
package、獨立相依解析與明定 coverage，重用 version/help 證據；接既有 controller
作不使用舊 parse cache 的完整重建，驗證 registry 與分版 sidecar；執行前拒絕
repo `.gitnexusrc`，避免未資格化設定改變執行範圍。
保留 `1.6.9` operator CLI；不啟用 automatic refresh、hooks、query 或 MCP。
A02 已驗收此接受的 GitNexus `1.6.12`／Node `25.9.0`、macOS arm64 本機整合：
單檔 commit 後舊索引變 stale，實際 controller 更新並驗證 registry、metadata、
sidecar 與內部 freshness。原 worker 的早期 Git index stat-cache baseline
exception 及停止狀態保留；離線讀回確認 staged 內容未變，未重跑 live。
當次編排方指定單一索引 writer、協調穩定來源與交接；Codex／Grok 功能對等仍待
各自驗證。詳見[審計](docs/codex-runtime-compatibility-evidence-2026-10-17.md)與
[交付評估](docs/releases/runtime-audit-2026-10-17.md)。2026-10-18 使用者選定
`0.35.0` 候選；Core pin 及實裝不改，原 docs-only 與 parser 準備候選保留為歷史。

Issue #355 separates CLI, Desktop and bundled CLI evidence; public help does not
qualify live sessions. Add an explicit local GitNexus 1.6.12 library profile with
accepted binary/package identity, independent dependency resolution and declared
coverage. Reuse accepted probes; the existing controller performs a full rebuild
without old parser output, rejects repository `.gitnexusrc` execution defaults,
checks the private registry and reads back its sidecar.
The 1.6.9 operator CLI stays unchanged. No automatic refresh, hook, query or MCP
is enabled. A02 accepts the limited integration for this approved GitNexus
1.6.12/Node 25.9.0 installation on macOS arm64: a fixture commit invalidates the
old index, then the actual controller updates it and verifies metadata, registry,
sidecar and internal freshness. Retain the worker's earlier Git index stat-cache
baseline exception and stopped status; file-only readback confirms unchanged
staged content. No live retry occurred.

The current orchestrator assigns one writer and coordinates stable source and
handoff. Codex/Grok parity remains unverified. The user selected candidate
`0.35.0` on 2026-10-18; Core pin and installation stay unchanged. Earlier documentation
and parser-only snapshots remain historical; delivery needs matching evidence.

## 0.34.0 — 拆分發行準備 / Split release preparation

2026-10-17，透過 [Issue #353](https://github.com/jeffery777/codex-dev-skills/issues/353)
建立新的拆分發行工作包；維護者同意重新使用 `0.34.0`。
這是獨立決策，不恢復 #316 的原候選目標。
[完整雙語範圍、安裝與 gates](docs/releases/v0.34.0-split.md)。

- 固定攜帶 Engineering Workflow Core 的共用 Markdown 契約、來源 notices、
  13 檔 snapshot、lock 與離線完整性驗證；Codex 保留技能、工具、模型／effort、
  sessions、validators、組裝及安裝責任。固定 Core v0.1.0 commit `174df2af8dedf813b9bd4e3c184a627ee87d3cd8`。
- 依使用者意圖選最小技能，優先使用當次語意相符的原生能力；保留 CLI shell
  executor、既有 fallback、人工授權及 CLI／TUI／Desktop／Bundled CLI 的獨立資格。
- 補入簡明雙語寫作、風險與早期審查、證據保存、前提／替代方案檢查；必要
  review、scan、exact-head 與 provider gates 均保留。
- 納入已合併 #352 的固定來源 installer：完整 payload／receipt 管理權驗證、
  新 receipt 管理的升降版、交易回復、探索路徑外 staging，以及成功後清理
  本次可重建 originals。舊 receipt 不自動遷移；Agent 協助換版另作實際盤點。
- 提供雙語 README／進階 reference，更新 Desktop sidebar 與 parent sandbox
  證據指引；v0.33.1 維護修正另核對等價，沒有合回其 Git 支線。
- 如實包含已合併的 default-off local model mapping／advisory failover，以及
  分離的 Hermes adapters。這些程式存在，但停止新增投入；不承諾正式模型或
  全入口資格，不吸收 draft #317／#324／#326，不啟用 Memory／Hooks／Schedulers。

On 2026-10-17, Issue #353 records a new split release decision and maintainer
agreement to reuse `0.34.0`. It does not resume the original Issue #316 candidate.

- Bundle fixed Core Markdown contracts, notices, a thirteen-file snapshot, a lock
  and offline integrity checks. Codex retains runtime and distribution ownership.
  Core v0.1.0 is pinned at `174df2af8dedf813b9bd4e3c184a627ee87d3cd8`.
- Select the smallest applicable skill from intent and prefer suitable active
  native capabilities. Preserve the CLI shell executor, fallbacks, authority and
  separate CLI, TUI, Desktop and Bundled CLI qualification.
- Add plain bilingual writing, risk-based early review, evidence preservation
  and premise/option checks without weakening mandatory review or provider gates.
- Include the merged #352 installer: fixed payloads, receipt-bound ownership,
  managed upgrades/downgrades, rollback, staging outside discovery roots and
  cleanup of this transaction's reconstructible originals after success.
  Legacy receipts require separate Agent-assisted assessment.
- Add bilingual navigation and retain the Desktop/sidebar and inherited-parent
  sandbox fixes also delivered on the v0.33.1 maintenance line.
- Disclose existing default-off local model mapping/advisory failover and
  separate Hermes adapters. Further investment remains stopped. No draft
  #317/#324/#326 feature or Memory/Hook/Scheduler activation is included.

## 0.33.1 — 獨立維護支線 / Separate maintenance line

以 v0.33.0 為基線，修正 parent sandbox readiness、Desktop sorting aliases、
不接受的 `priority` 與 `orbit` 指引，並同步直接相關文件、tests 與 package。
正式維護 commit 為 `6b5b0d0bf4e61119a5a87761fc4a6c4d35002e1c`。
其[維護發行紀錄](https://github.com/jeffery777/codex-dev-skills/blob/6b5b0d0bf4e61119a5a87761fc4a6c4d35002e1c/docs/release-notes-v0.33.1.md)
留在該支線，不補寫到 main 的歷史位置。

The maintenance line starts from v0.33.0 and fixes parent-sandbox readiness,
Desktop sorting aliases, unsupported `priority` and `orbit` guidance. Its
release commit is `6b5b0d0bf4e61119a5a87761fc4a6c4d35002e1c`.
Main does not inherit this commit; equivalent fixes are checked separately.

## 0.33.0 — 共同正式基線 / Common published baseline

基線 commit 為 `ad2e8a0772768b01d6e675a43b23047efc68ea39`，提供 default-off、
受限本機 memory-maintenance operator CLI。保留
[當時發行紀錄](docs/release-notes-v0.33.0.md) 的 runtime、同 UID 信任與未驗證限制；
本次拆分不啟用或擴大其資格。

The common baseline commit is `ad2e8a0772768b01d6e675a43b23047efc68ea39`.
Its bounded local memory-maintenance operator CLI remains default-disabled.
The original release record retains its runtime, same-UID and qualification limits.

更早版本見各自 `docs/release-notes-v*.md` 的原時點紀錄。
Earlier versions retain their original point-in-time release notes.
