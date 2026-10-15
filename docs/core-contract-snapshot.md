# 固定 Core 文件的 Codex 接法

[繁體中文](#zh-tw) · [English](#english)

<a id="zh-tw"></a>

Core 正式契約以原繁體中文為權威；本頁兩語描述必須同義，不改既有 Codex
政策與機器識別碼的效力。英文以 ASD-STE100 Issue 9 為寫作目標，尚未完成
完整符合性驗證；不宣稱繁體中文符合該英文標準。

Issue #335 的 P3-C 實作接續 [P2 設計](design/core-contract-consumption.md) 與
[P2 工作包](plans/issue-333-p2c-core-preparation.md)。P0/P2 是點時紀錄，不回寫為
已固定 P1 或已通過 runtime；本頁記錄目前的文件消費與建置接法。

## 固定來源與兩種 digest

來源為 jeffery777/engineering-workflow-core，P1 PR #4 merge
b4c37798b6d3a9efd91c8c6d518093f2dd847a98。Reviewed head
10e97ddde5e04b085da357138ebdae4d0cb5a0f4 與 merge 的 Git tree 相同。
snapshot 明選全部十份 Markdown 與 LICENSE，11 檔共 156,120 bytes；原 UTF-8
bytes、Core 相對路徑與非 executable Git mode 100644 不變。正式契約繁體中文
為權威，無翻譯替換，也不宣稱完整 ASD-STE100 符合性。

| 身分 | 精確算法與值 |
| --- | --- |
| P1 十份 Markdown handoff 集合 | 按 UTF-8 path bytes 排序；每列 path、TAB、原 bytes 的小寫 SHA256、LF，含最後 LF，不含 LICENSE；SHA256 8446dfbf5e2820dd696ef411e87cc7a92b39305c369c808122b63554b9be83f6 |
| Core LICENSE | 原 bytes SHA256 49d64e81e9fd3b12470c1da48367b120b28d404ca08edfdd950278e28e4da34f |
| Codex 11 檔集合 | 按 UTF-8 path 排序的 records，每筆只有 path/sha256/size_bytes/mode；UTF-8 JSON，keys 排序、compact separators、非 ASCII 不 escape、無 BOM/尾 LF；SHA256 輸入為 codex-core-document-set/v1、單一 NUL、JSON array；結果 9aed05bf415039319936cd4af4d34c77ae812df80a46f6d095c59182bedd242d |

兩種集合算法與檔案集合不同，不能互換。Lock 同時綁 repository、immutable
merge revision、reviewed head/PR、版本 absent、Codex import baseline 與組裝契約。
import_baseline_revision 是取得此 snapshot 時的 Codex 基線，不冒充將來的
消費者 HEAD；consumer 實際 revision、source/package version、assembler script
digest、layout、驗證環境與使用章節由當次 build/review/operation 證據另記，
避免 lock 或 source-map 自我包含 commit/digest 的循環。

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
  groups 都取得完整文件。原技能 root／legacy/custom-root 選擇、碰撞、
  preview／backup／force transaction 規則保持原樣；非 executable 檔依原規則 0600。
- 已有 Hermes 包也引用這四個共用政策，僅補同一固定文件資源 closure；
  不增加 Hermes 功能、投資或 runtime 資格。它保留自己的 source-shaped 子樹，
  regular files 0600；沒有自動更新任何現有安裝。

來源與目的地 preflight 在 installer 的 target/state mutation 前執行。目的地
可以缺少待新增的列入資源；既有 Core entries 必須符合閉集合、regular/non-symlink、
0600 與大小限制。額外檔案或權限不符時保留原資料並拒絕，即使 --force 亦然；
不自動刪檔或更改權限。既有列入檔案的 bytes 差異仍走原 collision/force/backup
流程。Shared group 同時供應接口所需的 native capabilities 文件。
驗證失敗不開始 promotion；source plugin 組裝前亦拒絕不符來源。
安裝／非 force update 在 shared group 記錄成功前驗完整 Core；force transaction
在發佈 receipts 前驗證，不符時使用既有 rollback，保留非本 transaction 的資料。
Core replacements 的 transaction 暫存位於 orchestration 內、core 旁的 private directory，
不放進 Core 閉集合；staging 與 destination 必須同 filesystem，否則拒絕 promotion。
既有 installer 在 promotion
中途的錯誤、衝突、backup 與恢復語意沿原契約，不宣稱跨全部檔案的新原子交易。
缺檔/錯 root/錯 lock/未知版本在 dependent operation 前停止，不能 runtime fetch
main、借另一安裝或改 sandbox。這是需依工具執行的工作流要求，不是模型行為
或 OS 攔截保證。

## 驗證與後續界線

Repo 開發驗證只用 tracked project-python；snapshot validator 僅 stdlib，無
網路、subprocess、外部設定讀取或寫入。它以目錄 descriptors／O_NOFOLLOW
檢查固定 inventory，拒 symlink/special/executable/unexpected entries；限制
每檔 128 KiB、總量 256 KiB、lock 16 KiB，驗逐檔 hash／size、固定來源、兩種
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

P3 的深入 code/docs review、比例 Security Diff Scan 及正式 exact-head/profile
gates 與測試分開。CLI/TUI/Desktop/Bundled CLI 的真實工具、有效 model/effort、
權限、session、載入、失敗/恢復仍各自留 P4 證據；本包不啟動模型 runtime，
不借 fixture 或別的入口資格。不更新 consumer、部署、Tag/Release、Memory、
Hooks、Schedulers、Orca、EdgeInstaller、其他專案或模型路由。

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

### Fixed source and separate digests

The source is `jeffery777/engineering-workflow-core`, P1 PR #4 merge revision
`b4c37798b6d3a9efd91c8c6d518093f2dd847a98`. Reviewed head
`10e97ddde5e04b085da357138ebdae4d0cb5a0f4` has the same Git tree. All ten Markdown
files and LICENSE are selected: 11 files, 156,120 bytes. Preserve original UTF-8
bytes, paths and Git mode `100644`. No translation replaces the Core snapshot.

| Identity | Algorithm and SHA-256 |
| --- | --- |
| P1 Markdown handoff set | Sort paths by UTF-8 bytes. Join each path, TAB, lowercase file SHA-256 and LF, including the final LF. Exclude LICENSE. `8446dfbf5e2820dd696ef411e87cc7a92b39305c369c808122b63554b9be83f6` |
| Core LICENSE | Hash its original bytes. `49d64e81e9fd3b12470c1da48367b120b28d404ca08edfdd950278e28e4da34f` |
| Codex 11-file set | Sort records by UTF-8 path. Each record has only `path`, `sha256`, `size_bytes` and `mode`. Encode JSON with sorted keys, compact separators, unescaped Unicode, no BOM and no final LF. Hash UTF-8 `codex-core-document-set/v1`, one NUL byte and that JSON array. `9aed05bf415039319936cd4af4d34c77ae812df80a46f6d095c59182bedd242d` |

The two set algorithms and inventories differ. Do not substitute one digest for
the other. The lock binds repository, immutable merge revision, reviewed head/PR,
absent version, Codex import baseline and assembly contract.
`import_baseline_revision` records the Codex baseline at import, not a future
consumer HEAD. Record the actual consumer revision, source/package version,
assembler digest, layout, verification environment and loaded sections in each
build/review/operation's evidence. This avoids self-referential commit/digest data.

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
  Keep skill-root/legacy/custom-root selection, collision, preview, backup and
  force-transaction rules. Non-executable installed files require mode `0600`.
- The existing Hermes package also consumes these shared policies. It receives
  the same fixed-resource closure in its source-shaped tree, with regular files
  at `0600`. This adds no Hermes feature, investment or qualification, and does
  not update an existing installation.

Validate source and existing destination before target/state mutation. A partial
destination may lack listed resources. Existing Core entries must satisfy closed
inventory, regular/non-symlink type, `0600` mode and size limits. Preserve and
reject extra files or invalid permissions, even with `--force`; do not delete or
repair them automatically. Listed byte differences retain existing collision,
force and backup handling. The shared group also supplies native-capability docs.

Reject invalid source before plugin assembly or installer promotion. Install and
ordinary update validate the complete Core set before shared-group success.
Force update validates before receipt publication; failure uses existing rollback
and preserves data outside that transaction. Core replacement staging uses a
private sibling directory under `orchestration`, outside the closed Core set.
Staging and destination must share a filesystem or promotion is rejected.
Existing partial-failure/recovery semantics remain; this adds no atomic
transaction across every installed file. Missing files, wrong roots/locks and
unknown versions stop dependent work. Do not fetch mutable main, borrow another
installation or change the sandbox. These are workflow requirements, not model
behavior or complete OS enforcement guarantees.

### Verification and later boundaries

Repository verification uses tracked `project-python`. The stdlib-only snapshot
validator has no network, subprocess, external-config read or write. Directory
descriptors and `O_NOFOLLOW` guard the fixed inventory. Reject symlinks, special,
executable and unknown entries. Limits are 128 KiB/file, 256 KiB total and 16 KiB
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
gates remain separate. P4 must establish actual tools, effective model/effort,
permissions, sessions, loading and failure/recovery for CLI, TUI, Desktop and
Bundled CLI independently. This packet starts no model runtime and borrows no
fixture or other surface's qualification. It performs no consumer update,
deployment, Tag/Release, Memory, Hooks, Schedulers, Orca, EdgeInstaller,
other-project or model-routing operation.
