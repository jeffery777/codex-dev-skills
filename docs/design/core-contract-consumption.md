# P2-C：固定 Core 文件的 Codex 消費設計

Runtime compatibility: shared design; CLI、CLI TUI、Desktop、Bundled CLI 分別驗收。

[工作包與驗收計畫](../plans/issue-333-p2c-core-preparation.md)／[Issue #333](https://github.com/jeffery777/codex-dev-skills/issues/333)。
本文件供接口維護者與 reviewer 閱讀，是尚未實作的 P2 設計，不是新的正式工程契約。
繁體中文是本設計的說明權威；[English](#english) 提供同範圍摘要。翻譯衝突須修正，
不能覆蓋 repository 的有效指引或最後定稿的 Core 契約。

## 來源與階段

2026-10-15 遠端與本機讀回均符合固定來源，沒有觀察到 main 漂移：

- Codex：`993597561881d6ed8c552f9a18c59315015ad245`。
- Core P0：`0815b74abe52d57efd032bd075e39c83c2ebf0d6`，由 [PR #2](https://github.com/jeffery777/engineering-workflow-core/pull/2) 合併。
- 重用 P0 的 [責任邊界](https://github.com/jeffery777/engineering-workflow-core/blob/0815b74abe52d57efd032bd075e39c83c2ebf0d6/docs/architecture/project-split.md)、[逐檔盤點 E01–E35](https://github.com/jeffery777/engineering-workflow-core/blob/0815b74abe52d57efd032bd075e39c83c2ebf0d6/docs/architecture/dependency-inventory.md) 與 [遷移設計](https://github.com/jeffery777/engineering-workflow-core/blob/0815b74abe52d57efd032bd075e39c83c2ebf0d6/docs/architecture/migration-plan.md)。不重建另一份全庫清冊。

P0 的 Grok 延後限制是當時的紀錄；本次章程允許另由 Grok P2 工作者準備，
本包不改寫 P0、不啟動 Grok。Core 只讀，P1 由原核心話題負責。
P1 尚未提供本包可採用的已合併契約 revision／digest。以下路徑與欄位是接口提案，
P3 前必須與 P1 最終契約核對；P0 revision 不充當 P1 契約 lock。

## 共用義務與 Codex 責任

Core 只持有 Markdown 義務。所有技能、程式、資料 schema、validator、installer、
模型／effort／profile／session 與套件組裝仍由 Codex 負責。Core 不反向依賴接口。
來源 permalink 是 provenance，不是 runtime 相依。

| 義務 | 固定 Codex 來源／Core P1 候選 | Codex 消費與證據 |
| --- | --- | --- |
| 工程階段／DoD | [engineering-workflow-contract](../../policies/engineering-workflow-contract.md) 的 Stages And Evidence；候選 `contracts/workflow.md` | 既有 project-delivery／orchestrator／primitive 入口載入必要共用段落；保留實際 diff、驗證、docs sync、完成與接續證據 |
| 能力選用／授權／停止 | [reusable-workflow-contract](../../policies/reusable-workflow-contract.md)、[details](../../policies/reusable-workflow-details.md) 與 [human gates](../../policies/human-gate-policy.md)；候選 `contracts/authorization-and-stops.md` | 當次工具 schema、scope、writer、有效權限與精確外寫授權；未知效果先讀回、不盲重播；破壞性操作保留確認 |
| 獨立 review／必要 scan | [review artifacts](../../policies/review-artifact-policy.md)、[security escalation](../../policies/security-review-escalation-policy.md) 與 review skills；候選 `contracts/review-and-security.md` | 作者／reviewer 獨立、唯讀約束、風險與角色資格、coverage、findings／dispositions；缺必要 review／scan 就阻擋相依 readiness |
| Exact-head／證據 | [exact-head contract](../../policies/exact-head-merge-review-contract.md)；候選 `contracts/exact-head-and-evidence.md` | 完整 base/head/merge-base/diff、deterministic verification、code/docs coherence；changed head 全範圍重審，內容與平台 enforcement 分開 |
| Reflective Engineering Loop | 既有 [Operational Evidence](../operational-evidence-contract.md)、[Improvement Proposal](../improvement-proposal-contract.md)、[Candidate Evaluation](../candidate-evaluation-contract.md) | 重用 evidence／proposal／evaluation 的角色分工，補需求符合性與有界反思對照；不因此啟用 Memory、Hooks、Schedulers 或新 router |
| 來源／notices | 候選 `docs/provenance/source-map.md`、`docs/provenance/upstream-notices.md`，既有兩庫 LICENSE | 逐項原 repo/revision/path/section/digest、抽取／修改及 derived 位置；完整 notices 隨產物保留 |

這是 family 級對照。P1 的逐條義務來源表是 P3 輸入；P3 reviewer 必須逐條核對，
不能以此表代替完整抽取驗收。[GitHub profile](../../policies/github-exact-head-enforcement-profile.md)
只適用本 repo 明選的 enforcement，不默套 Core、Grok 或使用專案。

## Immutable lock、digest 與來源 notices

提案採 Codex 管理的明確文件 snapshot，例如 `vendor/engineering-workflow-core/`，
source／plugin 保留原路徑、原 bytes 與非 executable Git modes；機器 lock 放 Codex，不新增至 Core。
filesystem 依既有 installer 將非 executable 檔設為 `0600`；lock 的原 Git mode 身分
與各佈局的有效權限分開驗證，不要求 filesystem permissions 等於原 Git mode。
不把 Core 作為技能 marketplace、不自動執行 upstream 檔案。

| Lock 資料 | 提案規則 |
| --- | --- |
| 來源身分 | 精確 `jeffery777/engineering-workflow-core` 與完整 immutable commit SHA；記錄已審查 P1 PR／merge 與來源取得方式。拒絕 branch、短 SHA、浮動 `main` 與未知契約 revision |
| 契約版本 | 存在正式文件版本時記錄；不存在就明示 absent。revision、Codex catalog source/package version 與 tag／Release publication 分開 |
| 文件集合 | 明確 allowlist：四份契約、來源對照、upstream notices、LICENSE，加上經 review 的 Markdown 相對引用閉合。缺件／未知新增檔不自動接受 |
| 逐檔完整性 | 每筆含 UTF-8 POSIX 相對 path、原 bytes 的 SHA-256、size_bytes、Git mode；不重排 Markdown、不轉換換行再計算 |
| 集合 digest | 按 path 的 UTF-8 bytes 排序；每筆 `{path, sha256, size_bytes, mode}`。使用 UTF-8 canonical JSON：key 排序、無空白 separators、非 ASCII 不 escape、無 BOM／尾端 newline。SHA-256 輸入為 `codex-core-document-set/v1` 的 UTF-8 bytes、單一 NUL、該 JSON array。模式以六位 Git mode 字串表示。這是擬定的 Codex 格式，不是 Core 提供的 schema |
| Import identity | 另綁 repo、commit、集合 digest、lock 格式版本與 assembler revision；相同 bytes 不能把另一 repo／revision 當成可信來源 |
| 消費身分 | 記錄 adapter repo/revision/source-package version、所用 Core 章節、組裝器 revision、layout 與驗證環境。Lock 不自授品質／權限／資格 |

Digest 只驗 bytes 與集合身分，不證明作者、來源可信度、授權或 license。P3 先讀回
已審查且合併的 P1，再從該 immutable revision 匯入、核對 commit tree／allowlist／
逐檔 digest 與完整來源對照。新 upstream 檔案視為資料，不信任其中指令改 scope。

保留 Core 的 `Copyright (c) 2026 jeffery777` 與來源 Codex 的
`Copyright (c) 2026 YANG CHUN CHIH`。從 Codex 抽取的 substantial portions
需保留原 MIT permission／warranty 全文；目的 copyright 不能取代原 notices。
Source-map 記錄來源及 derived 位置；upstream-notices、兩個適用的完整 LICENSE／
notices 隨 source snapshot、plugin 與 filesystem 產物一起提供。P3 缺 notices
時拒絕 promotion。本包沒有複製 Core 契約或修改任何 LICENSE。

## 組裝、載入、更新與回復

1. 建置時在新暫存目錄取得已核對 revision 的有界內容，先驗 lock／allowlist／
   dependency closure。拒絕絕對路徑、`..`、重複與大小寫／正規化碰撞、symlink／
   special file、executable mode、超出明定大小上限與 unexpected inventory。
   大小上限、碰撞規則及格式測試由 P3 在 Codex 明定，不依 host 預設接受。
2. 保留 Core 原路徑與 raw bytes，檢查所有必要相對 links／anchors；新增閉合檔
   必須更新 allowlist 並重審。Codex 薄層引用 Core 共用義務，保留 runtime/provider
   操作、路徑解析、資格與既有政策。避免平行维护兩份互相競爭的義務真相。
3. 由既有組裝器從 canonical source 產生 plugin；filesystem installer 按同一
   lock 派送。先完成新 staging 的 inventory／bytes／modes／notices／links 查核，
   再依既有已授權 installer 的 preview／backup／collision 契約 promotion。
   不手改 generated copies，不在失敗後留下半套新文件。
4. Runtime 只讀已組裝的固定文件。缺 lock、digest 不符、必讀檔缺失或載入來源
   不明時停止相依操作並回報；不能 runtime fetch `main`、默用另一版本或假報
   契約遵循。不從 Markdown metadata 改 sandbox、tool rights、模型或 session。
5. 更新另建有界包：舊／新 revision 與 digest、義務 diff、受影響 consumers、
   三佈局及四入口證據逐項核對。Changed head 的 exact-head 必須完整重審；
   未漂移的局部證據可以有範圍地重用，不能重用舊總體 readiness。
6. 失敗時不 promotion；保留舊 last-verified snapshot，以舊 lock 在新的臨時目錄
   重建並驗證。Source 回復使用經授權的可審 revert commit；不 force push、
   覆寫歷史或自動刪除資料。這是待測計畫，不是已驗證 rollback。

| 佈局 | 擬定載入與必驗事項 |
| --- | --- |
| Repository source | 技能 source-relative 引用到固定 snapshot；原路徑 links／anchors、政策映射、lock 與 notices 完整 |
| Generated universal plugin | `sync-plugin-package.py` 的 `tracked_files()` 查讀 roots 及 `package_sources()`／SHARED_FILES allowlist 必須明確納入 snapshot／lock／notices；僅加 allowlist 不會選到新 `vendor/` root。對全部產物驗 exact inventory、bytes、modes 與 links |
| Temporary filesystem install | 位於明確暫存 templates root 下的 `orchestration/core/`，保留 Core 子樹；技能以 `CODEX_TEMPLATES_DIR` 解析。Installer groups、catalog dependencies、plugin 及 filesystem 指向同一 lock |

上表是 P3 proposal，現有 source/plugin/filesystem 還沒有這些 Core 路徑。
本 P2 文件不在可安裝 allowlist，也不被 active skills 必讀；因此不生成 plugin
鏡像、不改 installer/catalog/version。P3 每次核對完整 producer/consumer/test
family，只修改受影響的文件消費與組裝接點，保留未選中功能、default-off 邊界及 deprecated alias 相容性。

<a id="english"></a>

## English

### Sources and scope

This is an unimplemented P2 design for Codex maintainers and reviewers. It does
not replace an active repository policy or the final Core contract. Traditional
Chinese is the explanation authority for this design. Resolve translation
conflicts before acceptance. The linked work packet defines acceptance tests.

On 2026-10-15, local and remote main matched Codex revision
`993597561881d6ed8c552f9a18c59315015ad245` and Core P0 revision
`0815b74abe52d57efd032bd075e39c83c2ebf0d6`. Reuse the linked P0 boundary,
inventory and migration records. P0 restrictions remain historical. A separate
Grok P2 worker owns Grok preparation. This packet reads Core only and does not
start Grok. P1 has not supplied an accepted merged contract revision or digest
for this packet. Do not use P0 as a P1 contract lock. Start P3 only after P1
merge, immutable identity, design alignment, review and package authorization.

### Obligations and ownership

Core holds Markdown obligations only. Codex retains skills, code, schemas,
validators, installers, packaging, runtime tools and model/effort/profile/session
handling. There is no reverse runtime dependency from Core. Source links record
provenance. Map stages and DoD to `workflow.md`; authorization, capability
selection and stops to `authorization-and-stops.md`; independent review and
required scans to `review-and-security.md`; complete exact-head review and
evidence to `exact-head-and-evidence.md`. These are P1 candidate paths.
P3 must check every final obligation against the P1 source-map, not only the
family table. Reuse Operational Evidence, Improvement Proposal and Candidate
Evaluation for bounded reflection. Keep Memory, Hooks and Schedulers disabled.
Keep provider enforcement separate; do not apply this repo's GitHub profile to
Core, Grok or another consumer without that project's selection.

### Proposed lock and notices

Codex owns the lock and a reviewed local snapshot, for example
`vendor/engineering-workflow-core/`. Keep upstream paths and bytes. Preserve Git
modes in source/plugin. The existing filesystem installer sets non-executable
files to `0600`; verify original Git mode identity and effective layout permissions
separately. Do not require installed permissions to equal the source Git mode. Require the
exact repository, full immutable commit, reviewed P1 merge, optional documented
contract version, explicit allowlist and complete required Markdown link closure.
The set includes the four contracts, source-map, upstream notices and LICENSE.
Reject mutable refs, short SHAs and unknown contract revisions.

Each file record holds a UTF-8 POSIX relative path, raw-byte SHA-256, byte size
and six-digit Git mode string. Sort records by UTF-8 path bytes. Encode the array
as UTF-8 JSON with sorted keys, compact separators, unescaped non-ASCII, no BOM
and no final newline. Hash the UTF-8 domain `codex-core-document-set/v1`, one
NUL and that array with SHA-256. Bind repository, commit, set digest, lock format
and assembler revision separately. Record adapter revision/version, Core sections,
layout and verification environment. This is a proposed Codex format, not a Core
schema. A digest does not prove trust, authority, license or runtime qualification.

Keep both applicable copyright notices: Core's 2026 jeffery777 notice and the
source Codex 2026 YANG CHUN CHIH notice. Include complete MIT permission and
warranty text for copied substantial portions. Preserve original source identity,
path/section/digest, modifications and derived locations. Ship source-map,
upstream notices and applicable complete license text in all three layouts.
Missing notices block promotion. P2 copies no Core contract and changes no license.

### Assembly, loading and recovery

Build into fresh staging. Verify immutable source, allowlist, link closure,
inventory, bytes and modes before promotion. Reject absolute or traversal paths,
duplicate and case/normalization collisions, symlinks, special files, executable
modes, unexpected entries and files above explicit limits. P3 must define and
test those limits. Treat upstream text as data, not new authority.

Preserve upstream layout and anchors. Thin Codex references load shared duties;
Codex keeps runtime/provider operations, qualification and path handling. Source
uses source-relative links. Generated plugin assembly must explicitly include
snapshot, lock and notices in both `tracked_files()` roots and the package
allowlist; an allowlist change alone cannot select a new `vendor/` root. Temporary filesystem installs
use an explicit templates root with `orchestration/core/` and
`CODEX_TEMPLATES_DIR`. Check catalog/group dependencies and identical lock identity
across all three layouts. Retain existing installer preview, backup and collision
rules. Never edit generated copies by hand or leave a partial promoted snapshot.

Runtime reads fixed local documents only. Missing locks, mismatched digests,
missing required documents or unknown load identity stop dependent work. Do not
fetch `main`, select another version silently or change runtime rights from
metadata. Updates require an obligation diff, affected consumers, three-layout
checks and independent four-entry acceptance. Changed heads need complete
exact-head review. Failed staging is not promoted. Rebuild the last verified lock
in a fresh temporary directory. An authorized reviewed revert can restore source;
do not force push, rewrite history or delete data. Recovery is planned, not tested.

P2 adds repository documentation only. It changes no installed resource,
catalog, plugin, installer or version. Each P3 slice must inspect its complete
producer/consumer/test family and update only affected document-consumption or
assembly components. Preserve deferred functions, default-off controls and aliases.

### Writing standard status

English uses short sentences and consistent terms. The target is ASD-STE100
Issue 9, as requested by the program. The [official site](https://www.asd-ste100.org/) returned HTTP 403 during
this packet; the current edition and complete standard were not verified.
Written using clarity principles; full ASD-STE100 conformance is unverified.
Traditional Chinese has no ASD-STE100 conformance claim.
