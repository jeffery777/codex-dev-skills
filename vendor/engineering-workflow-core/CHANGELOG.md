# Changelog

[繁體中文](#changelog-zh-tw) · [English](#changelog-en)

<a id="changelog-zh-tw"></a>

<details open>
<summary>繁體中文（預設展開）</summary>

## 版本與記錄方式

Core 的文件版本由本檔已提交的版本條目記錄，採 `vMAJOR.MINOR.PATCH` 命名。Core 與各 consumer 各自管理版本，不要求同步升版。`0.x` 階段的 minor 更新可能調整契約；每次採用仍須審查實際差異。Patch 用於不改變義務的文件修正，也不能取代 consumer 的完整性與遵循驗證。版本號不保證模型、工具、接口或 runtime 相容。

本檔及 release note 是點時準備／歷史紀錄，並非已發行證據。版本條目合併後仍須分別核對新的 annotated tag 與 GitHub 正式 Release。既有 tag 不覆寫；歷史條目不因後續發布而回填狀態。README 提供穩定導讀，不鏡像 mutable latest 或當前 publication 指標。

<a id="v0-1-0-zh-tw"></a>

## v0.1.0 — 初版準備紀錄

### 範圍與變更

- 將既有純 Markdown 共用契約整理為第一個版本化發行包：工程階段、授權及停止、獨立審查與必要安全檢查、exact-head 與證據。既有簡明寫作、證據生命週期、依風險及早檢查、安全適用性、前提／方案與停止改善義務一併保留。
- 本發行文件包更新 README 與來源記錄，新增本 changelog 及 [v0.1.0 準備紀錄](docs/releases/v0.1.0.md)。四份正式 contracts、三份架構文件、完整上游 notices 與 LICENSE 保持原 bytes／mode；原 107 單位及過往工作包歷史保留。
- 預期清冊為 12 份 Markdown 加原 LICENSE，共 13 檔。最終清冊、逐檔 bytes／mode／digest、全 repository 與完整 Markdown 集合 digest 在最終合併後的 tag annotation／Release metadata 及交接證據中核對，不在本檔內嵌自身 commit 或 digest。
- 不新增程式、validator、installer、schema、catalog、runtime API、模型控制或 Reason 功能；既有文件義務不改稱新的 runtime 能力。

### 採用及升級影響

使用者不需獨立安裝 Core。`codex-dev-skills` 與 `grok-build-dev-skills` 各自在建置／組裝時採用固定文件。Consumer 必須核對 tag object，將 tag 解析為完整 immutable commit，鎖定所選文件的逐檔及集合 digest、來源、allowlist、完整 dependency closure 與 notices；runtime 不追蹤 Core `main` 或動態解析 tag。

新增 changelog 與 release note 會改變完整清冊、集合 digest，以及可能的 allowlist／dependency closure。Consumer 應逐項判定所需文件與相對引用，更新自己的 lock／snapshot／組裝及驗證，保存 LICENSE 和完整上游 notices。不得沿用前一基線 `64b19bb5658432c42cd6a26aa357fd6b1d0fd857` 或舊 10 份 Markdown 集合 digest 冒充本發行包；最終 pin 必須包含本次發行文件。

本包不修改 consumer、既有技能或安裝，也不部署。正式發行、consumer 採用及實際安裝各需自己的授權與證據；Core 發行不證明接口遵循、兩端行為等價或模型／runtime 資格。驗證項、未驗證限制與來源／license 見 [準備紀錄](docs/releases/v0.1.0.md)。

正式契約的繁體中文權威與既有 ASD-STE100 限制保留。以下英文須與繁中主要資訊等價，不新增契約義務；未宣稱完成全部 ASD-STE100 規則及詞彙驗證。

</details>

<a id="changelog-en"></a>

<details>
<summary>English (expand to read)</summary>

## Versions and records

Committed version entries in this file record the Core document version. Names use `vMAJOR.MINOR.PATCH`. Core and each consumer manage their own versions. They do not need matching version numbers. During `0.x`, a minor update can change contracts. Review the actual changes for every adoption. A patch corrects documents without changing obligations. It does not replace consumer integrity or conformance checks. A version number does not guarantee model, tool, interface, or runtime compatibility.

This file and release notes are records of preparation and history. They do not prove publication. After a version entry is merged, separately verify the new annotated tag and formal GitHub Release. Do not overwrite existing tags or update historical entries merely to reflect later publication. README provides stable guidance. It does not mirror a mutable latest or current-publication pointer.

<a id="v0-1-0-en"></a>

## v0.1.0 — Initial preparation record

### Scope and changes

- Assemble the existing shared Markdown contracts into the first versioned release package: engineering stages, authority and stop conditions, independent review and required security checks, exact-head, and evidence. Retain existing obligations for plain writing, evidence lifecycle, early risk-based checks, security applicability, assumptions, options, and stopping optional improvement.
- This release-document packet updates README and the source record. It adds this changelog and the [v0.1.0 preparation record](docs/releases/v0.1.0.md). The four formal contracts, three architecture documents, complete upstream notices, and LICENSE keep their original bytes and modes. Retain the original 107 units and earlier packet history.
- The expected inventory is 12 Markdown files and the original LICENSE: 13 files. After the final merge, verify the final inventory, per-file bytes, modes and digests, and both repository and complete Markdown digests in the tag annotation, Release metadata, and handoff evidence. Do not put a self-referential commit or digest in this file.
- Add no code, validator, installer, schema, catalog, runtime API, model control, or Reason feature. Existing document obligations are not new runtime capabilities.

### Adoption and upgrade impact

Users do not install Core separately. `codex-dev-skills` and `grok-build-dev-skills` each adopt fixed documents during build or assembly. A consumer verifies the tag object, resolves it to a full immutable commit, and locks the selected files, per-file and set digests, source, allowlist, complete dependency closure, and notices. Runtime must not follow Core `main` or resolve a tag dynamically.

The new changelog and release note change the full inventory and set digests. They can also change a consumer's allowlist or dependency closure. Each consumer assesses the required documents and relative references, updates its own lock, snapshot, assembly, and verification, and retains LICENSE and complete upstream notices. Do not use the earlier base `64b19bb5658432c42cd6a26aa357fd6b1d0fd857` or the old 10-file Markdown digest as this release's pin. The final pin must include these release documents.

This packet does not change consumers, existing skills, or installations. It does not deploy. Publication, consumer adoption, and installation each require their own authority and evidence. Core publication does not prove interface conformance, equivalent behavior, or model/runtime qualification. See the [preparation record](docs/releases/v0.1.0.md) for checks, unverified limits, sources, and licensing.

Traditional Chinese remains authoritative for the formal contracts. Existing ASD-STE100 limits remain. This English text provides equivalent main information and adds no contract obligation. Full rule and dictionary conformance has not been verified.

</details>
