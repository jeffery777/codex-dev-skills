# Codex update compatibility audit — 2026-10-17

Runtime compatibility: observations are scoped separately below.
Issue: [#355](https://github.com/jeffery777/codex-dev-skills/issues/355).

## 繁體中文

### 目的、來源與範圍

本紀錄供維護者判斷更新後的接口相容性與最小修正。它不是供應商整套 QA，
也不是 live session／模型／四入口資格重新驗收。舊紀錄保留原版本與範圍，
不能移作新版通過證據。

本次來源為正式 v0.34.0 commit `c37444bd12aeeb8a4363cfdb61d1f4c76af405ad`。
先讀回 Issue、從該 SHA 建立並讀回遠端
`codex/issue-355-updated-runtime-audit`，再 fetch／核對專用 checkout 與單一 writer。
原主 checkout 保留在乾淨的 `993597561881d6ed8c552f9a18c59315015ad245`，
未更新、重置或重建其索引。Checkout 沒有 `.agents/skills`；相關技能從
本專案 `skills/` 原始來源讀取，不假裝已由 runtime catalog 注入。

### 初始分層觀測（10 月 18 日續作另列）

| 入口／依賴 | 當次證據 | 判定及限制 |
| --- | --- | --- |
| Standalone CLI | `0.163.0`；其 executable 的 help 與 production argv 測試 | 3 項 public-help tests 通過，未發現 parser 回歸；不證明 start／resume／fork lifecycle。 |
| Desktop application | app bundle identity `com.openai.codex`，`26.1013.40934`，build `20770` | 版本來自已安裝 bundle metadata；未重啟 app／session，也未操作 UI。 |
| Desktop bundled CLI | `0.163.0-alpha.10.2`；另一 executable 獨立測試 | 另 3 項 public-help tests 通過；alpha 與 standalone、Desktop native 工具不互相資格化。 |
| Desktop native dispatch | 本委派環境當次 create/fork schema；`list_projects` 唯讀回傳 schemaVersion 2 | local/worktree、source/host、queued/ready IDs 及 explicit send 邊界相符。未 create／fork／send；不資格化 standalone／bundled model turn，也不推定所有平台操作可用。 |
| Skills discovery | 官方 local discovery 文件及實際 filesystem receipt／payload | 標準 user root 為 `~/.agents/skills`。原 27 技能／193 檔當次重新 hash 比對 receipt 一致；不改設定、不重裝，也不宣稱已開會話重新載入。 |
| Core loader／installer | 已安裝 loader 自身 hash、正式 source pin、filesystem validator | 13 檔 closure 當次通過，既有實裝不變；後續候選的 source mapping 需求另列。 |
| Shared profiles／模型 | 官方 parent permissions 繼承規則、profile registry／preflight 與本委派環境當次 surfaced model schema | 保留 class/tier、模型／effort、當次 capability 與 qualification 邊界；未另作 live runtime／模型資格實驗，也未建立新資格。原生審計／審查使用模型推論，用量／費用未量測。 |
| Security interface | 當次 Standard/diff prompt-only scan schema，官方 Changes 指引，現有 escalation policy | 模式／target／revision／scope 仍須明選；工具存在不等於 scan 已執行，舊 sealed 結果不資格化新版。 |
| GitNexus | 實際 CLI `1.6.12`、本地已安裝來源及 `status --json` | 初始 adapter 只資格化 `1.6.9`；後續 A02 已驗收明確本機 `1.6.12` 路徑，見下節。 |

CLI 測試各自核對 exec／resume／fork usage、JSON 旗標、plugin list JSON shape，
並把 production argv 的 prompt 換成 `--help`。它們使用 disposable config；
不建立 session／JSONL。額外 help 查讀涵蓋 root、agents、doctor、plugin list。
`agents send` 不存在，但本專案沒有使用此命令；它不構成回歸。

[官方 CLI 0.163.0 更新](https://github.com/openai/codex/releases/tag/rust-v0.163.0)
包括執行中 steer／Code Mode 中止、獨立唯讀工具平行、resume 權限還原，以及
標準 shell executor。這些是供應商能力，未要求本套件模擬 daemon 或改變完成／
授權語意。本專案沒有依賴已退休 patched-zsh flags，原 executor 不改。

[Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents#approvals-and-sandbox-controls)
仍區分 parent sandbox／approvals 繼承和唯讀指令；後者不產生獨立技術隔離。
版本更新不解除 reviewer independence、角色／模型 preflight 或必要 scan。

### Findings 與最小處置

**UP355-01 — GitNexus 新版不在舊資格內。** 現有 adapter 在版本及 metadata
邊界保守拒絕，並非一般工作流失效。1.6.12 的已安裝來源與
[正式版本紀錄](https://github.com/abhigyanpatwari/GitNexus/releases/tag/v1.6.12)
顯示 runner 身分、scope 完整性、schema fingerprint，以及可選外部 storage／
retention 等語意。只放寬版本／JSON 欄位不能證明 conformance。最小處置為
補明此支援邊界並保留 source/Git fallback。R2 僅補封閉 typed 診斷；目前候選另加
明確的 1.6.12 本機 library profile／controller 採用流程，operator CLI 仍選 1.6.9，
單次 A02 已驗收此接受安裝的有限 index-write 整合；其他資格缺口保留。

**UP355-02 — 同 HEAD 的舊索引仍不具新版 freshness。** 當次 Codex 主 checkout
與 metadata 都是 `9935975`，但 GitNexus status 回報 `stale`、
`runnerIdentityStatus=stale-or-unknown`、`scope-extraction-unverified`，
contentDrift 為 `not-checked`。這不是目前內容 drift 已證實，也不是 clean/fresh。
未執行 query、impact 或任何依賴該索引的分析。

| 專案 checkout | 當次索引盤點 | 本輪建議 |
| --- | --- | --- |
| codex-dev-skills | 舊 schema-5 metadata；runner 未知、完整性未驗證，status=stale | 本審計使用原始碼／Git，不刷新。後續確需圖查詢時，先選最終 checkout／HEAD 與單一 owner。 |
| engineering-workflow-core | 沒有該 checkout 的索引／registry entry；status not-indexed | 小型 Markdown 契約查讀不需為版本同步建立索引。 |
| grok-build-dev-skills | 沒有該 checkout 的索引／registry entry；status not-indexed | 不從缺索引推定 Grok runtime 失效；由其 owner 判斷實際工作是否需要圖查詢。 |

Codex 的 GitNexus controller／hook 路徑仍為 optional、default-disabled；沒有
日常工程流程必須依賴此索引的條件。1.6.12 的有限本機資格綁定完整 package／
Node／entry 身分、新 metadata／來源保留與 storage policy、負面案例、隔離 fixture
及成本；由主話題指派單一 owner。共享索引重建另行決策，不自動同時刷新三專案。

### 2026-10-18 有界本機寫入與協作責任

原四檔 docs-only 與 R2 parser-only 候選保留歷史快照。R2 有效新版 metadata
仍 unsupported；後續增加獨立的 `qualify_local_1612` library 入口，既有 operator
CLI 仍選 1.6.9。新路徑綁定 caller 接受的 entry／實際 Node／package bytes、
runner、獨立相依 closure／較近 lockfile guards 與明定 coverage；不下載 npm。
只准 self-contained 相依，拒絕外部 fallback 與目錄 links；自報 digest 不自授信任。

既有 controller 以 `--index-only --no-parse-cache` 作完整重建，不信舊 parser
cache／metadata 對既有 DB 的宣告；同 HEAD 與損壞既有 metadata 拒絕。
新 private HOME 承載 registry／tmp／identity cache。逐檔 coverage、metadata
mirrors、registry、完整 content／Git-control、分版 digest／sidecar 讀回都必須
通過；新 profile automatic eligibility 固定 false。原 32 個 parser 負例與
新版 closure／內容／adoption 合成測試保留；離線成功不能代替 A02。

A01 的獨立 macOS arm64 fixture 初次 analyze 成功：exit 0、10.478 秒、程序組
停止，tracked fixture、17 個保護目標與 package inventory 未變。Node 實際為
25.9.0，FTS unavailable/extension-unavailable、零 embeddings。這不是新 controller
閉環或圖查詢資格。固定本機 DDL 的 35 個 node／628 個 relation pairs 靜態 digest
為 `60fc01e4e4ed516aaec56686114f067d728059eeeb0ac6d11606762217634f66`；
前 12 碼吻合 metadata，但不是實際 DB／npm 發布驗證。祖先 lockfile 由新本機
closure 綁定；隔離 HOME 不代表 filesystem read confinement。

A02 由唯一 test worker 執行一次，驗收我方技能／agent adapter 對此 GitNexus
1.6.12／Node 25.9.0、macOS arm64 安裝的有限 index-write 整合。單檔 commit
將 HEAD 由 `16939de` 推進至 `fb07c43`，舊證據為 stale/indexed-revision-stale；
實際 controller 回 refreshed/qualified-index-adoptable，寫入並讀回新 sidecar，
內部 final freshness、5 路徑 hashes、metadata mirrors 與 registry 均吻合。
Analyze exit 0、6.945 秒、程序組停止；含 qualification 的全段約 69 秒，低於
180 秒界線。17 正式保護目標、完整 package 與 13 檔候選未變。

外層 worker 的原始 STOPPED_NO_RETRY／AssertionError 保留：較早的 Git-control
baseline 與 controller entry 不同。獨立離線解析完整 Git index 確認僅
`src/calculator.py` cached ctime 改變，OID／mode／stage／extensions 未變，
writer 身分未知；controller entry／post／外層 after baseline 一致。外層第二次
freshness API 未執行；採用證據是實際 controller 的必要 final freshness 檢查與
新 sidecar／receipts 讀回，不將 worker 整輪改記 PASS。原始紀錄與獨立核對保存
於私人交接，未重試或新增 live。這不是 GitNexus 演算法、功能或 bug 的驗證。

累計呼叫 6/13，單次 A02 授權已用完，後續 live 授權為零；不重跑已接受的
version／help／六個 synthetic controls。A03 同 HEAD、A04 真實 forced timeout
延後。沒有 RSS 觀測或 RAM hard cap。

專案規範由當次編排方決定何時 query／update 與由誰操作，每共享索引邊界一位
writer；先協調來源穩定及 reader 狀態，再驗證並交接。Codex／Grok 功能對等是
後續目標，接入實作可不同，不固定 Codex 為永久管理者。當前 read_query、MCP、
Grok 與跨平台 concurrency 均未驗證。對等功能必要接續是 Grok 實際技能薄入口
依相同 identity／lock namespace／sidecar 正確調用已審 controller；不搬整套
LoopMemory、不新建技能／daemon／hooks，也不重跑 upstream 全功能測試。
僅在兩端 overlay 發現實際共通缺口時考慮 shared 純契約，不重寫 Core 平台細節。

### No-change 與驗證界線

- CLI executor、Desktop thin adapters、共享層、模型 profiles、installer／catalog
  與正式 Core pin 均無必要程式修正。Core 仍為 v0.1.0
  `174df2af8dedf813b9bd4e3c184a627ee87d3cd8`；接口工具升版沒有改變共用義務。
- 本候選包含明確本機 profile、controller／sidecar、合成測試及 generated plugin；
  使用者於 2026-10-18 選定 `0.35.0`，同步 source/package 版本 metadata。
  CLI executor、installer 邏輯、模型 profiles、實裝與 Core pin 保持不變。
  Source-catalog mapping 未重寫；四項隔離安裝測試因新 payload 不符舊 mapping 而 FAIL，
  不能記 PASS，commit 本身也不能修好。後續須受審不可變來源與新 mapping。歷史證據不改。
- No-change 是受查接口契約的判斷，不是全平台、所有 lifecycle、模型品質或
  sandbox／拒絕／取消行為都通過。#242／#251／#293 保留原追蹤狀態。
- 除上述已批准、已停止的 A01／A02 外，未新增 live runtime／session 或模型資格實驗。原生審計與獨立審查
  使用模型推論，用量／費用未量測。沒有日常設定／權限變更、session restart、
  安裝、shared-index rebuild、Memory／Hooks／Schedulers 啟用或 Space 寫入。
- 文件採簡明雙語原則；未證明完整 ASD-STE100 符合性，未作新的外部 Markdown POST。

## English

This Issue #355 audit uses fixed Codex commit
`c37444bd12aeeb8a4363cfdb61d1f4c76af405ad`. It keeps the primary checkout and
old evidence unchanged. Its Issue branch was created, read back and fetched
before documentation edits. One writer owns the dedicated checkout.

Standalone CLI `0.163.0` and bundled CLI `0.163.0-alpha.10.2` each passed three
public-help tests, including production argv with `--help` in place of a prompt
and plugin JSON shape. The Desktop bundle reports `26.1013.40934`, build `20770`.
Desktop create/fork schemas and read-only project discovery were checked
separately in the current delegated task context. They do not qualify tools in
a standalone or bundled model turn. None establishes live dispatch, lifecycle,
model or universal runtime qualification. An unsupported `agents send` probe is not a regression:
the adapter does not use it.

Official skill discovery still includes the user `~/.agents/skills` root.
The installed receipt's 27 skills and 193 files were checked again against
their hashes. The installed Core loader and thirteen-file closure passed fresh
filesystem validation. Existing configuration and installation were not changed;
already-open sessions were not reloaded or claimed to have updated.

The 0.163 update adds steering/cancellation and read-only concurrency, restores
saved permissions and uses the standard shell executor. These supplier features
do not change this pack's authority or completion rules. Parent permission
inheritance remains distinct from read-only reviewer instructions. Model/effort
and scan capabilities still require their own current evidence. A surfaced
Standard/diff scan tool is not an executed scan or reusable old scan approval.

**UP355-01:** the original operator/controller qualified GitNexus `1.6.9` and
rejected `1.6.12`. New runner provenance, completeness, schema fingerprint and optional
storage/retention semantics need bounded qualification. A version-string or
field-allowlist change is insufficient. The continuation adds an explicit local
library profile and controller adoption path; A02 now accepts its limited local
index-write integration for the approved installation. The
operator CLI retains 1.6.9 and source/Git fallback remains available.

**UP355-02:** Codex's old index and primary checkout have the same `9935975`
HEAD, but current status is `stale`, runner identity is unknown, scope extraction
is unverified and content drift was not checked. Do not call that fresh or
interpret it as demonstrated content drift. Core and Grok checkout indexes
were absent. None of those project indexes was queried or rebuilt. No mandatory common-index
dependency was established; each owner chooses whether a later task needs one.

No CLI executor, installer, profile or shared Core change is required by the
examined interfaces. The local-profile continuation changes installable bytes;
the user selected candidate `0.35.0` on 2026-10-18, with source/package version
metadata aligned. Installer logic and actual installation remain unchanged. Core remains v0.1.0 at
`174df2af8dedf813b9bd4e3c184a627ee87d3cd8`. Separate entrypoints and the shared
layer remain intact. Prior unresolved lifecycle investigations stay unresolved.

The original documentation and R2 parser-only candidates remain historical.
`qualify_local_1612` now reuses accepted probe receipts and binds local entry,
actual Node, package bytes, accepted runner identity, independently enumerated
self-contained dependencies, nearest-lockfile guards and explicit coverage.
External fallback modules and directory links are refused. No npm download or
publisher authentication is required or claimed. The operator CLI still selects
1.6.9; new metadata without this profile remains unsupported.

The existing controller uses `--no-parse-cache` for a full rebuild, refusing
same-HEAD refresh and invalid existing metadata. A private HOME contains registry,
tmp and identity cache. Coverage hashes, metadata mirrors, registry, complete
content/Git-control postconditions and the versioned sidecar must pass. Automatic
eligibility is false. Offline fixtures cover the new boundary and retain the
32 parser negatives; they do not prove A02 success. Four isolated installation
tests still FAIL because the changed payload differs from the old catalog
mapping. A commit alone cannot fix that; a reviewed immutable source and matching
new catalog mapping are required.

A01 succeeded in 10.478 seconds with unchanged protected/package state and a
stopped process group. Node was 25.9.0, FTS unavailable, embeddings zero. The
fixed local DDL digest starts `60fc01e4e4ed`; it is not an actual DB or npm release
check. The new closure binds the ancestor lockfile. HOME isolation does not prove
read confinement.

A02 used one actual controller call for our skill/agent integration with the
accepted GitNexus 1.6.12/Node 25.9.0 installation on macOS arm64. One fixture
commit advanced `16939de` to `fb07c43`; old evidence became
stale/indexed-revision-stale. The controller returned
refreshed/qualified-index-adoptable after writing and reading its sidecar and
checking final freshness, five coverage hashes, metadata mirrors and registry.
Analyze exited 0 in 6.945 seconds with its process group stopped; the whole
qualification/controller run took about 69 seconds within the 180-second bound.
Seventeen formal protected paths, the full package and all 13 candidate files
were unchanged.

Retain the outer worker's original STOPPED_NO_RETRY/AssertionError: its earlier
Git-control baseline differed from controller entry. Independent file-only
analysis of both full Git indexes found only calculator cached ctime changes;
OID/mode/stage/extensions were unchanged and writer identity is unknown.
Controller entry/post and outer after baselines match. The optional second outer
freshness API was not run. Acceptance relies on the controller's actual required
final freshness gate and saved sidecar/receipt readback; the worker run is not
relabeled PASS. Private raw evidence and independent review are retained. No
live retry or upstream algorithm/feature/bug QA was added. Calls total6/13, but
the single A02 approval is spent and further live authorization is zero.
A03/same-HEAD and A04/real forced timeout remain deferred; no accepted
probe/control rerun occurred. RSS and a RAM hard cap remain unavailable.

The current orchestrator decides query/update timing and operator assignment,
coordinates stable source and reader ownership, and assigns one writer per
shared index boundary before evidence handoff. Equivalent Codex/Grok features
are a future target; the integrations may differ. Codex is not the permanent
index manager. read_query, MCP, Grok and cross-platform concurrency remain
unverified. Required parity follow-up is Grok's actual thin skill entry using
the reviewed controller with the same identity, lock namespace and sidecar.
Do not transfer the whole LoopMemory system, create another skill/daemon/hook,
or repeat upstream feature QA. Consider a shared pure contract only for an actual common gap;
keep GitNexus platform details out of Core. No cross-platform query framework
is implemented here. Apart from approved A01/A02, no additional live runtime/session or model-qualification
experiment was run for this continuation. Native audit and independent review use model inference;
usage/cost was not measured. The audit does not restart sessions, change daily
configuration/permissions, install software, activate hooks/memory/schedulers or
write Space. It does not claim complete ASD-STE100, visual GitHub rendering,
all-platform safety or lifecycle acceptance. Historical notes are not rewritten.
See the [release impact assessment](releases/runtime-audit-2026-10-17.md).
