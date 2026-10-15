# Issue #335：P3-C 固定 Core 消費

[繁體中文](#zh-tw) · [English](#english)

<a id="zh-tw"></a>

兩語維持相同 scope 與 DoD；Core 繁中權威及既有 Codex 契約效力不變。
英文以 ASD-STE100 Issue 9 為寫作目標，尚未完成完整符合性驗證。

[Issue #335](https://github.com/jeffery777/codex-dev-skills/issues/335)；
[實作接法](../core-contract-snapshot.md)；
[P2 設計](../design/core-contract-consumption.md)。

## 前置與 scope

協調端已確認 P1 獨立正式驗收、PR #4 合併、兩端 P2 對最終契約一致及本包
必要授權。Core 固定 b4c37798b6d3a9efd91c8c6d518093f2dd847a98；
reviewed head 10e97ddde5e04b085da357138ebdae4d0cb5a0f4。十份 Markdown＋
LICENSE 共 11 檔；算法與來源／notice／集合 hashes 詳見實作接法及 lock。

Codex base ab5e517077df7ce83b8e2dd1a11cafe6d1b3fd35；真實 Issue/readback
先於 codex/issue-335-core-contract-consumption 遠端分支/readback，再 fetch、
專用 clean checkout／upstream／identity／ownership 核對後才修改。
單一 writer 為本包主代理；reviewer 唯讀；あき保留長期協調。網路環境恢復
與一次正常核准屬 Git 外證據，不改 repo 或持久安全／網路設定。

只改 snapshot/lock/validator、相容政策薄層及必要資源、tests/docs。四個舊
政策入口與 reusable 七個 anchors 保留，技能入口／模型／profile／權限及
provider enforcement 不改。既有 Hermes 消費的共用資源只補 dependency closure。
不混 #317，不寫 root README／roadmap／model guide；P0/P2 與 release notes
歷史不倒寫。Catalog source/package version 與 manifest/installer 保持一致；
本包以 exact commit 識別，不宣稱 tag/Release publication 或 release readiness。

## 最小完整相依切片

| Producer／consumer | 必要查核 |
| --- | --- |
| 固定 Core → snapshot/lock/validator | 來源 PR/tree、11 檔 allowlist、原 bytes/modes、兩種 digest、notices、relative closure；source trust 與完整性分開 |
| Core → 四相容政策 → 原 skills/workflows | 必讀 trigger、Core 全文、七 anchors、完整 source-map 義務、Codex-specific details/fallback／qualification/provider 保留 |
| Source → sync-plugin → generated package | tracked roots＋allowlist；新增資源入列；全 inventory／bytes／modes／snapshot 身分 |
| Catalog＋installer manifests → temporary templates | shared dependency groups、target mapping、private modes、default/legacy/custom roots、失敗 preflight 不 mutation |
| 共用政策 → 既有 Hermes resource catalog | 同一 Core bytes 與 notices/loader；既有 no-overwrite/readback；無新 Hermes runtime |
| Validator／package／installer → tests/shards/repo CI | 相關 parser/file-boundary／source/plugin/filesystem／負面 tests；manifest 完整分割與既有回歸 |

不變的 loop/routing/qualification/continuity/OE/proposal/evaluation 程式與 schemas
保留 Codex ownership，按實際影響做回歸；不搬到 Core、不啟用延後功能。
Core/Grok repo、其他專案及現有 consumer 安裝均不寫。

## DoD 與 evidence

1. Immutable 來源、107 source-map 單位與必要補充義務完整；兩種 digest 明分，
   loader 固定實際 root；必要檔／trust metadata 不明就停止相依操作。
2. 同一 snapshot/lock/notices 在 source、generated plugin、temporary filesystem
   可重建驗證；所有相依 groups 及既有 Hermes closure 不斷鏈。
3. 正負面測試含 wrong source/ref/digest、ambiguous JSON、unsafe inventory/path/
   mode/symlink/FIFO/limits、missing docs/notices、wrong root、preflight rejection
   的目的地不變，以及 installed validator 離開來源 repo 獨立執行。
4. 使用 project-python 的 pinned Python/PyYAML；必要 deterministic checks、
   affected test families、完整 shards／最新 hosted CI 分別記錄，skip 不當 Pass。
5. 初次即深入獨立 code/docs review，保留 findings/dispositions；本包涉及
   source trust、parser、檔案與 installer/packaging，必要比例 Security Diff Scan
   不沿用 P2 的不適用結論。
6. PR 後完整 base-to-head exact-head content review、coherence 與所選 GitHub
   CI/receipt/readback/dedicated App/native-latest/final live gates；changed head
   完整重審。各動作沿用既有明確條件式授權，不以 review 自行產生權限。

驗證／review 原件留核可 Git 外位置；PR 綁 exact revisions、diff identity、
commands/results、findings/dispositions、限制與平台證據。本計畫不預填 PASS。
正式 readiness 前驗證兩語語意一致、local links／anchors 與 GitHub 實際呈現。
P3 DoD 不包含四入口 P4 runtime 資格；未測／Unknown 保留，不開始未授權模型
操作、consumer 安裝、Tag/Release、部署或禁止功能。失敗保留證據，回復只用
已授權的可審 source revert／舊 lock 重建，不 force push、刪資料或改安全設定。

<a id="english"></a>

## English

The two languages retain the same scope and DoD. Core's Traditional Chinese
authority and existing Codex contracts remain unchanged. English targets
ASD-STE100 Issue 9; full conformance has not been verified.

[Issue #335](https://github.com/jeffery777/codex-dev-skills/issues/335) ·
[Implementation](../core-contract-snapshot.md) ·
[P2 design](../design/core-contract-consumption.md)

### Prerequisites and scope

The coordinator confirmed independent P1 acceptance, merged PR #4, alignment of
both P2 designs with the final contract, and authority for this packet. Pin Core
`b4c37798b6d3a9efd91c8c6d518093f2dd847a98`, reviewed head
`10e97ddde5e04b085da357138ebdae4d0cb5a0f4`. Ten Markdown files and LICENSE form the
11-file set. The implementation document and lock define algorithms, provenance,
notices and hashes.

Codex baseline is `ab5e517077df7ce83b8e2dd1a11cafe6d1b3fd35`. Actual Issue creation
and readback preceded remote branch `codex/issue-335-core-contract-consumption`
and its readback. Fetch and a dedicated clean checkout, upstream, identity and
ownership check preceded edits. The packet's main agent is the sole writer;
reviewers remain read-only. あき retains long-term coordination. Network recovery
and one normal approval are Git-external evidence; no persistent security/network
configuration changes follow.

Change only the snapshot/lock/validator, compatible policy adapters, necessary
resource closure, tests and docs. Preserve four policy entries and seven reusable
anchors. Do not change skill entries, models, profiles, authority or provider
enforcement. Existing Hermes consumers receive only required shared resources.
Exclude #317 features and root README/roadmap/model-guide overlap. Preserve P0/P2
and release-note history. Keep catalog, package and installer source versions in
sync. Identify this packet by exact commit; do not assert publication or release
readiness from a tag/Release.

### Smallest complete dependency slice

| Producer/consumer | Required evidence |
| --- | --- |
| Fixed Core → snapshot/lock/validator | Source PR/tree, 11-file allowlist, original bytes/modes, both digests, notices and relative closure; separate trust from integrity |
| Core → four compatible policies → existing skills/workflows | Required triggers, full Core reading, seven anchors, complete source-map obligations and retained Codex details/fallback/qualification/provider rules |
| Source → sync-plugin → generated package | Tracked roots and allowlist, added resources, exact inventory, byte/mode parity and snapshot identity |
| Catalog/installer → temporary templates | Shared dependencies, target mapping, private modes, default/legacy/custom roots and rejection before mutation |
| Shared policies → existing Hermes catalog | Same Core bytes/notices/loader and existing no-overwrite/readback; no new Hermes runtime |
| Validator/package/installer → tests/shards/CI | Parser/file-boundary and layout/negative tests, complete shard partition and existing regressions |

Loop, routing, qualification, continuity, OE, proposal and evaluation code/schemas
remain Codex-owned. Run regressions according to actual impact. Do not move them
to Core or enable deferred features. Do not write Core/Grok repositories, other
projects or existing consumer installations.

### DoD and evidence

1. Preserve immutable identity, all 107 mapped units and additional obligations.
   Distinguish both digests and select the actual root. Unknown required files
   or trust metadata stop dependent operations.
2. Rebuild and verify the same snapshot, lock and notices in source, generated
   plugin and temporary filesystem layouts. Preserve all group dependencies
   and existing Hermes closure.
3. Cover wrong source/ref/digest, ambiguous JSON, unsafe inventory/path/mode,
   symlinks/FIFOs/limits, missing docs/notices and wrong roots. Check unchanged
   destinations after rejected preflight and installed validation outside the
   source checkout.
4. Use pinned Python/PyYAML through `project-python`. Record deterministic
   checks, affected test families, the complete test-shard run and latest
   hosted CI separately. Skipped checks are not passes.
5. Use independent deep code/docs review from the first pass. Preserve every
   finding/disposition. Source trust, parsing, filesystem and packaging changes
   require proportional Security Diff Scan; do not reuse P2's not-applicable
   conclusion.
6. After PR creation, review the complete exact base-to-head range and coherence.
   Verify selected GitHub CI, receipt/readback, dedicated App, native-latest and
   final live gates. A changed head requires complete new range review. Existing
   conditional authority remains valid; review creates no new write authority.

Keep raw verification/review evidence in approved Git-external locations. Bind
the PR to exact revisions/diff identity, commands/results, findings/dispositions,
limits and platform evidence. This plan does not prefill PASS. Verify bilingual
meaning, local links/anchors and actual GitHub rendering before final readiness.

P3 DoD does not include P4's four-surface qualification. Preserve untested/unknown
states. Do not start unauthorized models, consumer installs, Tag/Release,
deployment or forbidden features. Preserve failed evidence. Recovery uses only an
authorized reviewable source revert or reconstruction from the old lock; no force
push, data deletion or security-setting change.
