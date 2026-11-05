# Fixed Core Loading Contract

## v0.4.0 source adoption / 來源採用

本來源包固定正式 Core v0.4.0 commit `4c8d35ad7c8e9d6a7c47331e5bd93eea2b45c535`、reviewed head `21c1fe39a87f5207fd962d61e69910cf48b4d88c`、annotated tag object `b0d04f75fd491adb200799ba89115e762b4011d1` 的 26 檔（25 份 Markdown 與 LICENSE），共 494192 bytes；Release 434673080 已讀回非 draft／非 prerelease。普通 loader 僅選此身分；v0.3.0 的 23 檔新增為第五個明確 installer history，仍須 opt-in。以下較舊 pin 的現行描述只記錄其歷史適用階段，不改普通選取結果。

This source adopts the exact published Core v0.4.0 identity above. Preserve all earlier installer histories, notices and fixed evaluations. Verify the full snapshot before loading required contracts. Source/package preparation does not establish publication, installed adoption or runtime qualification.

For required review, read full review/security, including `review-required-read-only` and its complete environment-specific exception. No acceptance record is inferred or supplied by this package. For public operations, also read `review-publication-data`; actual Codex controls, raw data and destinations need current evidence. Existing optional PR-text tooling covers only its documented subset.

## v0.3.0 source adoption / 來源採用

本來源包採正式 Core v0.3.0 commit `7efe4eea59031ed5f9ff9c4a8aef5b8f7d2be02e`、annotated tag object `0e91dfaa7f3969c9ec3d9647a765ec2f116057bb` 的二十三檔，包含二十二份 Markdown 與原 LICENSE；Release 430452222 已讀回非 draft／非 prerelease。普通 loader 僅選此身分；v0.2.0 二十檔新增為第四個明確 installer history，既有歷史身分、原文、驗證及停止規則保持。下方 v0.2.0／v0.1.1 現行描述保留為當時來源階段歷史。

This source adopts the exact published Core v0.3.0 identity above with 23 files. Preserve v0.2.0 as the fourth explicit installer history and retain all earlier histories and safety rules. Earlier current-pin paragraphs describe their historical stages. Source/package preparation does not establish consumer publication, installation or runtime qualification.


## v0.2.0 source adoption / 來源採用

本來源包固定 Core v0.2.0 commit `6887bfe6183465e9a9e6ccb4ccd7305a58b37302`、annotated tag object `0ba0fd98e2343f72e555d9bf0e8b1bc5650cd93d` 的二十檔，包含十九份 Markdown 與原 LICENSE。普通 loader 只選此正式身分；選 root、驗證、停止與 runtime 限制不變。下方 v0.1.1-only 及原兩種 history 的描述保留為舊 pin 的歷史適用範圍；本版 installer 明列 v0.1.1 十四檔為第三個 history，仍須明確 opt-in，不得當普通 current。

This source adopts the exact formal v0.2.0 identity above. The v0.1.1-only identity paragraph and original two-history description below apply to their historical pin. They retain their words; the current validator selects twenty files and explicitly keeps the fourteen-file v0.1.1 descriptor as additional installer history. Layout, stop, integrity, authority and qualification rules remain applicable.

Runtime compatibility: shared document loading; runtime qualification is separate.

Core shared obligations come from the reviewed snapshot in this package. They are
not copied into another independently maintained neutral policy. Existing Codex
policy paths and headings are compatibility entrypoints and retain Codex overlays.
Core's Traditional Chinese text is authoritative; identifiers/notices remain raw.
The P0/P2 design records describe their original stage, not current qualification.

## Select And Verify One Layout

Select the actual package/templates root before dependent work. Never search
another installation, cwd, network or mutable Core main as fallback.

| Layout | Snapshot, relative to the explicit root | Lock |
| --- | --- | --- |
| Repository source or generated plugin | `vendor/engineering-workflow-core/` | `vendor/engineering-workflow-core.lock.json` |
| Filesystem templates | `orchestration/core/` | `orchestration/core.lock.json` |

In source, run the tracked resolver from that checkout:

    ./scripts/project-python -B scripts/validate-core-contract-snapshot.py --root /explicit/package/root --layout source

In a generated plugin, invoke its own scripts/validate-core-contract-snapshot.py
with the verified Python interpreter and explicit plugin root, layout source.
In a filesystem install, invoke
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/scripts/validate-core-contract-snapshot.py`
with explicit templates root and `--layout filesystem`. The source-relative
Core links below apply to source/plugin. For filesystem loading, replace
`../vendor/engineering-workflow-core/` with `../core/` relative to these policies.

The validator is offline and read-only. Ordinary loading accepts only Core
v0.1.1 at commit `7b66978a76597d09be1b55ad199a969b4ee59c0f`, annotated tag
object `7ce698fa853106c8ef44c4240c9334762da5ffb0`. It pins all 14 file
paths/bytes and recorded source Git modes, both independently defined set digests,
LICENSE, local links/anchors and required inventory. The closure includes Core's
CHANGELOG and release record; this does not require loading all files for every
operation. Filesystem files must be 0600; source
Git mode 100644 and effective POSIX permissions are distinct. Upstream Git-tree
modes are provenance readback; this offline validator does not inspect a Git index.
It rejects unsafe
entries before reading document bytes. The validator's own reviewed bytes and
actual selected root remain part of operator evidence; a matching lock does not
authenticate an installation or prove trust, authority, review or runtime quality.

Only the current installer explicitly uses `--allow-reviewed-history` to reconstruct
the separately fixed Core v0.1.0 thirteen-file snapshot or eleven-file development snapshot. That path still checks its
exact source, lock, inventory, bytes, modes, digests and link closure; it never runs
an old source's validator. Its output identifies historical acceptance. It cannot
qualify either historical snapshot as the ordinary Core v0.1.1 loading root. Unknown snapshots
are rejected even with this flag.

Missing/unknown lock or loader, mismatched identity/digest, missing document,
unsafe inventory or unresolved load root stops dependent work. Report the gap;
continue only independent authorized work. Do not claim compliance, silently
choose another root/version or execute upstream Markdown. Verify again when the
loaded bytes, revision, root, permissions, assumptions or relevant evidence drift.
Unchanged validated evidence may be reused with its original limits.

The filesystem installer checks an existing partial Core destination before
promotion: unknown entries, unsafe types/modes or excessive files stop the write
without deleting or repairing those entries. It then validates the complete
installed snapshot before recording success. The preflight alone is not a
complete snapshot verification; byte differences still require the existing
reviewed update/force/backup path.

## Required Reading

Read full required documents, not only a linked anchor. Preserve existing skills'
additional reading and project overlays.

| Trigger | Fixed shared obligation |
| --- | --- |
| Every engineering operation | Full [workflow](../vendor/engineering-workflow-core/contracts/workflow.md) and [authorization/stops](../vendor/engineering-workflow-core/contracts/authorization-and-stops.md) |
| Applicable review, fix or formal delivery gate | Full [review/security](../vendor/engineering-workflow-core/contracts/review-and-security.md) |
| Existing change request, changed head or merge content readiness | Full [exact-head/evidence](../vendor/engineering-workflow-core/contracts/exact-head-and-evidence.md) and applicable review/security |
| Source attribution or obligation mapping | [source-map](../vendor/engineering-workflow-core/docs/provenance/source-map.md), [upstream notices](../vendor/engineering-workflow-core/docs/provenance/upstream-notices.md), and [Core LICENSE](../vendor/engineering-workflow-core/LICENSE) |

For assumptions, option comparison and bounded improvement, follow
Core [wf-assumptions-and-options](../vendor/engineering-workflow-core/contracts/workflow.md#wf-assumptions-and-options)
within the full workflow and applicable review/security reading above. Record
applicable reasoning in existing plans/reports; simple low-risk work can be brief.
Report prompts do not replace finding dispositions, establish resource ownership,
waive required gates or grant action authority.

For continuation, full workflow `wf-stages` prefers the original session. Before
continuing, confirm the state of an operation or delegated work with an unknown
outcome. This does not authorize a retry, a new delegation or forced restoration.

Core remains Markdown only. Codex keeps tools, validators, skills, model/effort,
qualification/profile/session, packaging and installation. Each surface proves
its own effective capability; loading these files grants no runtime qualification.
Do not enable Memory/Hooks/Schedulers or another provider through this loader.
Provider selection and actual external-write authority remain separate.
