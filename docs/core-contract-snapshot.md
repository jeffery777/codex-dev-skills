# 固定 Core 文件的 Codex 接法

[繁體中文](#zh-tw) · [English](#english)

<a id="zh-tw"></a>

Core 正式契約以原繁體中文為權威；本頁兩語描述必須同義，不改既有 Codex
政策與機器識別碼的效力。英文以 ASD-STE100 Issue 9 為寫作目標，尚未完成
完整符合性驗證；不宣稱繁體中文符合該英文標準。

Issue #335 的 P3-C 實作接續 [P2 設計](design/core-contract-consumption.md) 與
[P2 工作包](plans/issue-333-p2c-core-preparation.md)。P0/P2 是點時紀錄，不回寫為
已固定 P1 或已通過 runtime；本頁記錄目前的文件消費與建置接法。

Issue #341 接入 Core PR #8 的簡明寫作契約，更新固定集合及 docs-update／
docs-review 的操作指引。docs-review-gate 保持原有薄包裝；該包不更新現有安裝。

Issue #343 一起接入 Core PR #10 的證據生命週期與 PR #12 的風險／審查時機。
先在既有執行、編排、review、結案入口落實，再同步本頁及 README；不另建技能、
gate 或清理 framework。共用定義仍以固定 Core 為準，未執行歷史清理或更新現有安裝。

Issue #347 接入 Core PR #14 的安全政策、能力缺口與外部補查規則，
更新固定集合與既有安全 adapter。有效政策不要求某項檢查，與必要檢查
尚未執行／能力不可用分開記錄；外證及正式例外依固定 Core 綁定候選、
檢查與交付動作。這是文件與接口接點採用，不證明 runtime 行為或公司政策實例。

Issue #349 接入 Core PR #16 的前提檢驗、方案取捨與有界改善規則。
既有 loading 入口導向完整 Core；planning、執行與 review 沿既有必讀鏈取得義務，
不逐技能複製。既有 [integration review 報告](../templates/orchestration/integration-review-report.template.md)
以適用的選填提示記前提／反證、採拒理由、保障／成本／殘餘風險、改善判讀及
停止條件。簡單低風險工作可短述，不強制長表或 Loop。改善判讀不替代 findings
disposition，不以共識、digest 或同意證明歸屬，也不豁免必要安全、review、
scan、exact-head、保存或操作授權；本包不聲稱模型或 runtime 已遵循。

<a id="固定來源與兩種-digest"></a>

## 固定來源與集合 digest

Issue #353 固定正式 Core v0.1.0。Annotated tag object
`e984c880a05065c8bcd0d78e83d78220b05bfc32` 解析到 PR #18 merge commit
`174df2af8dedf813b9bd4e3c184a627ee87d3cd8`；reviewed head
`bc20699a5c46458647a01c5edb2830d8381219ef` 與 merge 的 tree 相同。
完整引用 closure 明選 12 份 Markdown 與 LICENSE，共 13 檔、264,088 bytes。
原 UTF-8 bytes、相對路徑、100644 Git mode、LICENSE 及完整 notices 保留。
含四份正式 contracts 在內的九個保護檔案維持 PR #16 基線 bytes；新增 CHANGELOG、
release record 及 README/source-map 發行導讀，不增加 Reason 或 runtime 功能。

| 身分 | 精確算法與值 |
| --- | --- |
| Core 12 份 Markdown 集合 | UTF-8 path 排序，path/TAB/raw SHA256/LF，含最後 LF、不含 LICENSE；`484923e7dc1407dde1702cf88e93afb5a279b25f79a2c6ff9631d58d7589ab13` |
| Core 完整 13 檔集合 | 同一 path/TAB/hash/LF 算法，含 LICENSE；`3c985420e8017bde6b59f2625d451686202e2f6a03d807a361df166634a88de9` |
| Core LICENSE | 原 bytes SHA256 `49d64e81e9fd3b12470c1da48367b120b28d404ca08edfdd950278e28e4da34f` |
| Codex 13 檔集合 | UTF-8 path 排序的 path/sha256/size_bytes/mode records；keys 排序、compact JSON、非 ASCII 不 escape、無 BOM/尾 LF；domain `codex-core-document-set/v1`、NUL、JSON array；`91e3153d31f4096e21927e653b74010fbaa504c7f1550ecf56af687db288d482` |

算法或範圍不同，不可互換。Lock 固定 repository、commit、reviewed head/PR、
version `0.1.0`、tag 及 tag object；runtime 不動態解析 tag。
`import_baseline_revision` 保留初次匯入的 Codex 歷史基線，不冒充本次或將來
consumer HEAD。當次 source/package、revision、assembler bytes、layout 與驗證
範圍由 build/review 證據另外綁定，避免自引用。

既有 Issue #349 的 Core PR #16／11 檔採用是歷史。只有目前受審 installer 明選
`--allow-reviewed-history` 才接受那份固定歷史集合，用於受管舊來源重裝／降版及
部分 uninstall；仍驗 exact source、lock、每檔 bytes/mode、集合 digest 與 closure，
回傳明示歷史 revision／digest／count。一般 loader 不使用此選項，拒絕把舊快照
當正式 v0.1.0。未知鎖或任意宣告的 hashes 皆不能新增 allowlist。

Digest 驗完整性，不證明信任、授權、runtime 資格或出版狀態。來源審查、單向
責任與 notices 仍必需。原 copyright/完整 MIT permission/warranty 在
snapshot 的 LICENSE 與 upstream-notices 中各自保留；後者的原 Codex LICENSE
區塊 bytes 與 Codex LICENSE SHA256 a58ebea45ac922c21500dad64c6e5f54423f831d2dfdfd2b4c882aab29822d4e 相同。

## 載入與相容入口

操作契約為 [core-contract-loading](../policies/core-contract-loading.md)。
四個舊政策路徑及 reusable 的七個 anchors 保留；共用義務指向固定 Core，
Codex 的工具、model/effort、qualification/profile/session、provider 與專用
資料契約留接口。既有 primitive、編排、CLI/Desktop adapters 與 deprecated
aliases 沿原入口，不增加自動 lifecycle 或改既有模型／權限預設。

| Core 義務／source-map 單位 | Codex 接點 |
| --- | --- |
| workflow 八階段 E02–E10、R19、D28 | engineering-workflow-contract／reusable 的 Shared Phases；原 delivery/planning/implementation/docs/review 技能 |
| P1 之後新增的 wf-writing／plain-writing-update | engineering-workflow-contract 的 Documentation Writing And Review；docs-update／docs-review 檢查讀者、句意、術語、步驟、雙語語意及符合性宣稱；仍使用既有 review 報告 |
| P1 之後新增的 wf-assumptions-and-options／assumptions-options-update | core-contract-loading 導讀完整 Core；既有 planning／執行／review 載入義務，integration-review-report 按需記前提、反證、方案與停止條件；不新增 gate 或逐技能規則副本 |
| P1 之後新增的 security-policy-update／review-security／review-evidence | security-review-escalation-policy 引導既有報告記政策權責、檢查狀態、實際工具覆蓋與外查交接；必要 gate、不可豁免、獨立 review、exact-head 與操作授權保留，不新增機器化例外 enforcement |
| P1 之後新增的 review-risk-timing／review-security | engineering/security/exact-head adapters；planning／implementation／delivery／orchestrator 在開始與變動重評，high-risk Markdown 不繞過早期深入與必要比例 scan；Merge Review 核對當前覆蓋與重用理由 |
| P1 之後新增的 wf-evidence-lifecycle／auth-data／auth-destructive | artifact policy／cleanup／closure／continuation；既有報告保存原因、修正、版本、替代引用與原失敗覆蓋；保護未解／間歇／共享／仍引用證據，缺 retention 保留，實際不可逆刪除另須當下確認 |
| 能力相容／新鮮度 E11–E12、R01–R05/R12/R18/R22、D01–D09/D14 | reusable Capability Selection／Protected Boundaries；native discovery、Code Mode 與實際 validator |
| 委派／runtime E01/E13–E14/E16–E18、R16/R20、D11–D12/D15/D17–D20/D29–D30 | reusable details／engineering Adapter Boundaries；原 model selection、agent delegation、integration、qualification、continuity |
| 驗收／改善 E15/E19、R08–R09/R15、D21–D23 | workflow verification；既有 OE/proposal/evaluation 保持 advisory 與 default-off |
| 授權／停止 R06–R07/R10–R11/R17、D13/D16/D19/D24–D25/D27、E20/X34 | reusable stop/details、human gates、artifact/data/privacy 專用規則 |
| 獨立 review／dispositions E07、R13/R21、D10/D31、X15/X30–X32 | 原 review/deep/gate/security-escalation/artifact 接點；修正比例重審 |
| Exact-head X01–X29/X33、R14/D26 | exact-head 相容政策；原 schema/validator/collector/report；本 repo 明選 GitHub profile，其他專案不默套 |
| 固定來源與補強／107 單位之外的 provenance | loading policy、snapshot/lock/validator、build/installer；Core source-map 與 notices 原樣保留 |

此表以 source-map IDs 作語意導航，不把重複出現的 ID 當新義務，也不替代
逐條審查。E20 等單位仍須完整讀其目的契約。四份主要來源共 434 行、
107 單位已由 P1 對照；P3 必須維持完整觸發與接口保留項，而非只看表格數量。

## 三佈局與建置

- Source／plugin 使用 vendor/engineering-workflow-core 與同層 lock。
  Generator 同時納入 tracked roots 與明確 allowlist，先驗 canonical source，
  再同步原 bytes/modes，最後驗 plugin inventory 與固定 snapshot。
- Filesystem templates 使用 orchestration/core 與 orchestration/core.lock.json；
  installer resource lists 與 catalog 同屬 shared-review-gates，所有既有相依
  groups 都取得完整文件。保留技能 root／legacy/custom-root 入口；修改依固定來源、
  receipt 管理權與完整交易驗證，force 不豁免；非 executable 檔為 0600。
- 已有 Hermes 包也引用這四個共用政策，僅補同一固定文件資源 closure；
  不增加 Hermes 功能、投資或 runtime 資格。它保留自己的 source-shaped 子樹，
  regular files 0600；沒有自動更新任何現有安裝。

依[固定來源安裝與回復](installer-source-integrity.md)先驗完整來源與 receipt 綁定的管理權。
未知、自訂、symlink／hardlink、額外空目錄、缺檔或 unsafe mode 都拒絕，`--force`
不能認領或強蓋。舊 installed.jsonl 沒有 root binding，實際舊安裝由 Agent 另盤點。
Core receipt 仍逐檔記錄；交易把已驗完整 Core 目錄作為單一 directory artifact，
lock 仍是獨立 artifact。這讓 13／11 檔升降版及 rollback 保留精確子目錄集合，
不額外刪未知空目錄，也不改成跨所有 roots 的原子交易。

完整 staging、暫時 originals 與 receipts 位於已驗 owner-safe state，排除已知
runtime discovery roots／aliases；不放在 Core 旁或技能探索路徑內。Staging 與
target 必須同 filesystem。完整 payload／Core／receipt／退休檔讀回後才成功，
成功僅清理本次可重建 originals；歷史 backups、未知內容與恢復失敗原件保留。
失敗保留精確 recovery 路徑；沒有斷電／SIGKILL 跨 roots 原子性或敵對 same-UID 保證。
Filesystem 收據不等於 native plugin manager 的生命週期資格。

## 驗證與後續界線

Repo 開發驗證只用 tracked project-python；snapshot validator 僅 stdlib，無
網路、subprocess、外部設定讀取或寫入。它以目錄 descriptors／O_NOFOLLOW
檢查固定 inventory，拒 symlink/special/executable/unexpected entries；限制
每檔 128 KiB、正式集合總量上限 264,088 bytes、lock 16 KiB，驗逐檔 hash／size、固定來源、兩種
digest、完整 LICENSE 及相對 links/anchors。既有 source/plugin mode parity
另由 generator 檢查；filesystem 明驗 0600。Root 由操作人員明選，不從 cwd、
環境或其他安裝 fallback。

此 verifier 使用 POSIX filesystem primitives；本機 macOS fixture 與 hosted
Linux CI 是不同證據。Windows 行為仍未驗證；shared 工作流標籤不代表所有
OS 都能執行此 verifier，缺必要能力時須回報驗證缺口。

負面測試涵蓋來源與 metadata 錯配、lock 重複 keys、路徑/大小/模式/碰撞、
missing/tampered notices、symlinks/FIFO、broken links、錯 root、目的地額外檔／同 bytes
錯權限、失敗不 promotion／不發佈成功 state、postcondition failure／force rollback、
三種 filesystem roots 和既有 Hermes closure。Tests 與回傳 verified 不授予
操作權、獨立 review 或 runtime qualification；兩項 false-authority flags 固定 false。

深入 code/docs review、比例 Security Diff Scan 及正式 exact-head/profile gates
與測試分開。CLI/TUI/Desktop/Bundled CLI 的入口證據各自保留原 scope 與限制；
已完成的有界驗收只在內容、環境與假設仍有效時重用。這次固定來源與政策更新
不重開既有四入口驗收，也不要求全平台 qualification；不借 fixture 或別的入口
資格。不啟動模型 runtime、不更新既有 consumer 安裝。此前採用包不部署或發 Tag/Release；
Issue #353 的獨立發行另依明確授權與 gates，實裝仍由主話題接續。各包均
不操作 Memory、Hooks、Schedulers、Orca、EdgeInstaller、其他專案或模型路由。

<a id="english"></a>

## English

Core's original Traditional Chinese contract is authoritative. The two language
sections must describe the same implementation. Translation does not change
existing Codex policies or machine identifiers. English targets ASD-STE100
Issue 9; full conformance has not been verified. That English standard does not
establish conformance for the Chinese text.

Issue #335 implements P3-C after the [P2 design](design/core-contract-consumption.md)
and [P2 packet](plans/issue-333-p2c-core-preparation.md). P0 and P2 remain records
of their original stages. They do not assert fixed P1 acceptance or runtime
qualification. This page describes local document consumption and assembly.

Issue #341 adopted Core PR #8's plain-writing contract through the fixed set and
docs-update/docs-review. docs-review-gate remains a thin wrapper.

Issue #343 adopts Core PR #10's evidence lifecycle and PR #12's risk/review timing
together. Functional instructions in existing execution, orchestration, review
and closeout entries precede this guide and README update. Fixed Core retains the
shared definitions. No new skill, gate or cleanup framework, historical cleanup
or update to an existing installation follows.

Issue #347 adopts Core PR #14's security-policy, capability-gap and external-check
rules through the fixed set and existing security adapter. Record a policy's
decision that a check is not required separately from a required check that has
not run or whose capability is unavailable. Bind external evidence and formal
exceptions to the candidate, check and delivery action under fixed Core. This
document and adapter update does not prove runtime behavior or a company-policy
instance.

Issue #349 adopts Core PR #16's assumptions, options and bounded-improvement
rules. The existing loader points to full Core; planning, execution and review
receive the duties through their existing required-reading chain, without copies
in each skill. Optional prompts in the existing [integration review report](../templates/orchestration/integration-review-report.template.md)
record premises/counterevidence, option decisions, safeguards/cost/residual risk,
improvement assessment and stop conditions. Simple low-risk work can be brief;
no long table or Loop is required. Improvement assessment does not replace finding
dispositions. Consensus, a digest or consent does not prove ownership. Required
safety, review, scans, exact-head, retention and action authority remain. This
adoption does not prove model or runtime conformance.

<a id="fixed-source-and-separate-digests"></a>

### Fixed source and distinct set digests

Issue #353 pins formal Core v0.1.0. Annotated tag object
`e984c880a05065c8bcd0d78e83d78220b05bfc32` resolves to PR #18 merge commit
`174df2af8dedf813b9bd4e3c184a627ee87d3cd8`. Reviewed head
`bc20699a5c46458647a01c5edb2830d8381219ef` has the same tree.
The complete reference closure contains twelve Markdown files and LICENSE:
thirteen files, 264,088 bytes. Preserve original bytes, paths, modes and notices.
Nine protected files, including the four contracts, retain the PR #16 baseline bytes.
New release/navigation documents add no Reason or runtime feature.

| Identity | Algorithm and SHA-256 |
| --- | --- |
| Twelve-Markdown set | UTF-8 path order; path/TAB/raw SHA256/LF, final LF, excluding LICENSE; `484923e7dc1407dde1702cf88e93afb5a279b25f79a2c6ff9631d58d7589ab13` |
| Full thirteen-file set | Same path/TAB/hash/LF algorithm including LICENSE; `3c985420e8017bde6b59f2625d451686202e2f6a03d807a361df166634a88de9` |
| LICENSE | Raw SHA256 `49d64e81e9fd3b12470c1da48367b120b28d404ca08edfdd950278e28e4da34f` |
| Codex thirteen-file set | UTF-8-path-sorted path/sha256/size_bytes/mode records; sorted-key compact UTF-8 JSON, unescaped Unicode, no BOM/final LF; domain `codex-core-document-set/v1`, NUL and JSON array; `91e3153d31f4096e21927e653b74010fbaa504c7f1550ecf56af687db288d482` |

Do not substitute different algorithms or sets. The lock binds repository, commit,
reviewed head/PR, version0.1.0, tag and tag object. Runtime never resolves a tag.
The import baseline remains the historical first Codex import, not a current or
future consumer HEAD. Build/review evidence separately binds revision, package
version, assembler, layout and scope without self-reference.

Issue #349's eleven-file PR #16 adoption is historical. Only the current reviewed
installer explicitly selects `--allow-reviewed-history` for managed historical
reinstall/downgrade and partial uninstall. It verifies exact source, lock, every
file/mode, set digests and closure, and reports the selected historical identity.
Ordinary loading never selects history as formal v0.1.0. Unknown locks or arbitrary
declared hashes cannot extend the allowlist.

A digest proves integrity, not trust, authority, runtime qualification or
publication. Preserve source review, one-way responsibilities and notices. The
original copyright and complete MIT permission/warranty remain in LICENSE and
upstream-notices. The latter's original Codex LICENSE block matches Codex LICENSE
SHA-256 `a58ebea45ac922c21500dad64c6e5f54423f831d2dfdfd2b4c882aab29822d4e`.

### Loading and compatible entries

Follow [core-contract-loading](../policies/core-contract-loading.md). Keep all four
existing policy paths and the seven reusable-policy anchors. Fixed Core owns
shared obligations. Codex retains its tools, model/effort, qualification,
profiles/sessions, provider enforcement and specialized data contracts. Existing
primitives, orchestration, CLI/Desktop adapters and deprecated aliases retain
their entries. No automatic lifecycle, model default or permission change follows.

| Core obligation and source-map units | Codex connection |
| --- | --- |
| Eight stages: E02–E10, R19, D28 | Engineering/reusable Shared Phases; existing delivery, planning, implementation, docs and review skills |
| Post-P1 wf-writing/plain-writing-update | Engineering Documentation Writing And Review; docs-update/docs-review check readers, sentence meaning, terminology, steps, bilingual equivalence and conformance claims in the existing review report |
| Post-P1 wf-assumptions-and-options/assumptions-options-update | Core loading points to full Core for existing planning/execution/review; integration-review-report records applicable premises, counterevidence, options and stop conditions. No new gate or per-skill rule copies |
| Post-P1 security-policy-update/review-security/review-evidence | Security adapter connects existing reports to policy authority, check status, actual tool coverage and external handoff. Preserve required gates, non-waivable obligations, independent review, exact-head and action authority; add no machine-enforced exception mechanism |
| Post-P1 review-risk-timing/review-security | Engineering/security/exact-head adapters; planning/implementation/delivery/orchestrator reassess at start/change. High-risk Markdown retains early deep review and necessary proportional scan; Merge Review checks current coverage and reuse rationale |
| Post-P1 wf-evidence-lifecycle/auth-data/auth-destructive | Artifact policy/cleanup/closure/continuation; existing reports retain cause/fix/version/replacement and original-failure coverage. Protect unresolved/intermittent/shared/referenced records; absent retention means retain; actual irreversible deletion needs action-time confirmation |
| Capability compatibility/freshness: E11–E12, R01–R05/R12/R18/R22, D01–D09/D14 | Reusable Capability Selection/Protected Boundaries; native discovery, Code Mode and actual validators |
| Delegation/runtime: E01/E13–E14/E16–E18, R16/R20, D11–D12/D15/D17–D20/D29–D30 | Details/engineering Adapter Boundaries; model selection, delegation, integration, qualification and continuity |
| Acceptance/improvement: E15/E19, R08–R09/R15, D21–D23 | Workflow verification; existing OE/proposal/evaluation remain advisory and disabled by default |
| Authority/stops: R06–R07/R10–R11/R17, D13/D16/D19/D24–D25/D27, E20/X34 | Reusable stop/details, human gates and specialized artifact/data/privacy rules |
| Independent review/dispositions: E07, R13/R21, D10/D31, X15/X30–X32 | Existing review/deep/gate/security/artifact entries; proportional fix review |
| Exact-head: X01–X29/X33, R14/D26 | Compatible exact-head policy and existing schemas, validator, collector and report; this repository selects GitHub explicitly. Other projects must select their own overlay. |
| Fixed-source obligations and provenance beyond the 107 units | Loading policy, snapshot/lock/validator, build/installer and unchanged Core source-map/notices |

This table navigates source-map IDs. Repeated IDs are not new obligations, and
the table does not replace individual review. Read complete destination contracts,
including E20. P1 mapped 434 source lines into 107 units. P3 must retain all
required triggers and Codex connections; counts alone do not prove preservation.

### Three layouts and assembly

- Source and plugin use `vendor/engineering-workflow-core` and its sibling lock.
  The generator selects tracked roots and an explicit allowlist. It validates
  source before copying original bytes/modes, then verifies exact plugin
  inventory, parity and snapshot identity.
- Filesystem templates use `orchestration/core` and
  `orchestration/core.lock.json`. Catalog and installer place these in
  `shared-review-gates`; existing dependent groups receive the complete set.
  Retain skill-root/legacy/custom-root selection. Mutations require fixed-source,
  receipt-ownership and complete transaction verification; force cannot bypass
  them. Non-executable installed files require mode `0600`.
- The existing Hermes package also consumes these shared policies. It receives
  the same fixed-resource closure in its source-shaped tree, with regular files
  at `0600`. This adds no Hermes feature, investment or qualification, and does
  not update an existing installation.

Follow [fixed-source installation and recovery](installer-source-integrity.md).
Verify the full source and root-bound receipt ownership. Unknown/custom content,
links, extra empty directories, missing files and unsafe modes fail closed even
with force. Legacy installed.jsonl needs a separate Agent-assisted assessment.
Receipts retain per-file Core inventory. The transaction moves the verified
complete Core root as one directory artifact; its lock remains separate. Existing
directory rename/rollback preserves the thirteen/eleven-file subdirectory set
without broad empty-directory removal or an all-roots atomicity claim.

Stage payload, temporary originals and receipts in verified owner-safe state
outside known discovery roots/aliases, not beside Core. Require the same filesystem.
Read back complete payload, Core, receipt and retired-file absence before success.
Clean only this transaction's reconstructible originals. Preserve historical
backups, unknown data and failed recovery originals. Report exact recovery paths
on failure. Power-loss/SIGKILL atomicity across roots and hostile same-UID isolation
are not guaranteed. Filesystem receipts do not qualify native plugin lifecycle.

### Verification and later boundaries

Repository verification uses tracked `project-python`. The stdlib-only snapshot
validator has no network, subprocess, external-config read or write. Directory
descriptors and `O_NOFOLLOW` guard the fixed inventory. Reject symlinks, special,
executable and unknown entries. Limits are 128 KiB/file, 264,088 bytes for the
formal set total, and 16 KiB
for the lock. Verify file hashes/sizes, fixed identity, both set digests, LICENSE
and local links/anchors. The generator checks source/plugin effective-mode parity;
upstream Git modes are provenance readback, distinct from runtime permissions.
Filesystem verification requires `0600`. Select one root explicitly; do not fall
back to cwd, environment or another installation.

This verifier uses POSIX filesystem primitives. Local macOS fixtures and hosted
Linux CI are separate evidence. Windows behavior remains unverified. The shared
workflow label does not qualify verifier execution on every OS; report a
verification gap when required capabilities are missing.

Negative cases cover identity/metadata mismatches, duplicate JSON keys, unsafe
paths/sizes/modes/collisions, missing/tampered notices, symlinks/FIFOs, broken links,
wrong roots, extra destination files and same-byte wrong modes. Tests also cover
rejection before promotion/success state, postcondition failure/force rollback,
three filesystem roots and existing Hermes closure. Tests and `verified` results
grant no authority, independent review or qualification. Both result authority
flags remain false.

Deep code/docs review, proportional Security Diff Scan and exact-head/profile
gates remain separate from tests. CLI, TUI, Desktop and Bundled CLI evidence
retains each surface's original scope and limits. Reuse completed bounded
acceptance only while content, environment and assumptions still match. This
fixed-source and policy update does not reopen that acceptance or require
all-platform qualification. It borrows no fixture or other surface's qualification
and starts no model runtime. It performs no existing consumer installation
rollout. Earlier adoption packets did not deploy or publish. Issue #353 has
separate release authority and gates; installation remains coordinator-owned.
No packet activates Memory/Hooks/Schedulers or operates Orca, EdgeInstaller,
other projects or model routing.
