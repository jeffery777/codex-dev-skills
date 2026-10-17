# Fixed Core Loading Contract

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

The validator is offline and read-only. It pins repository/revision, all 11 file
paths/bytes and recorded source Git modes, both independently defined set digests, LICENSE,
local links/anchors and required inventory. Filesystem files must be 0600; source
Git mode 100644 and effective POSIX permissions are distinct. Upstream Git-tree
modes are provenance readback; this offline validator does not inspect a Git index.
It rejects unsafe
entries before reading document bytes. The validator's own reviewed bytes and
actual selected root remain part of operator evidence; a matching lock does not
authenticate an installation or prove trust, authority, review or runtime quality.

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

Core remains Markdown only. Codex keeps tools, validators, skills, model/effort,
qualification/profile/session, packaging and installation. Each surface proves
its own effective capability; loading these files grants no runtime qualification.
Do not enable Memory/Hooks/Schedulers or another provider through this loader.
Provider selection and actual external-write authority remain separate.
