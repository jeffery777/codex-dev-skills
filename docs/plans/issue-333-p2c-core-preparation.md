# Issue #333：P2-C 準備與驗收計畫

[Issue #333](https://github.com/jeffery777/codex-dev-skills/issues/333)／[消費設計](../design/core-contract-consumption.md)／[English](#english)。
本包只新增這兩份文件，供接口維護者與 reviewer 使用。繁體中文是本計畫的說明權威；
英文摘要須維持同範圍與限制。現有正式政策及 P1 定稿契約優先。

## 工作包身分與現況

- Repository：`jeffery777/codex-dev-skills`；branch：`codex/issue-333-p2c-core-preparation`。
- Writer：本有界委派的主代理，單一 writer；reviewer 使用獨立 context、唯讀工作約束。
  長期協調仍由あき負責，不新增排程或協調系統。
- 來源與 base：`993597561881d6ed8c552f9a18c59315015ad245`；Core P0：`0815b74abe52d57efd032bd075e39c83c2ebf0d6`。
- 2026-10-15 已核對 remote main、Core P0 merge、Issue scope／open state、遠端含 Issue ID 的 ref／SHA，
  再 fetch、建立專用 disposable checkout、核對 HEAD／upstream／clean state 後才修改。
  主 checkout 保留乾淨 main；未使用其他 active worktree。私人 checkout 路徑／章程／原始工具輸出留 Git 外。
- PR #326、#324 的檔案清單已讀回；本包不寫 README、roadmap、model guide 或既有計畫。
  #317 候選不併入、不執行。`.agents/skills` 本 checkout 不存在，相關技能從 tracked `skills/` 讀取。

P1 由原 Core 話題負責；本次協調回報尚未啟動，本包 Core 唯讀。允許 Issue／branch、上述設計、驗證與獨立 review；
commit／push／draft PR 僅在章程與正式 gates 成立後交付。Merge 另核對完整 exact-head、
最新 CI／threads／receipt／專用 App 及必要平台 gates；draft 不符合 ready profile。
禁止 Tag／Release、部署、更新其他專案技能、EdgeInstaller、Memory／Hooks／Schedulers、
Orca、Codex Grok／LiteLLM 模型路由、擴權、force push、資料刪除。

## 重用相依與 P3 最小完整切片

以 [Core P0 固定盤點](https://github.com/jeffery777/engineering-workflow-core/blob/0815b74abe52d57efd032bd075e39c83c2ebf0d6/docs/architecture/dependency-inventory.md)
為完整清冊。來源 revision 未漂移，本包只補接口接法；以下列 P3 需要共同核對的接點。
這些檔案本次不修改；P3 核對完整 producer/consumer/test families，只修改受影響的文件消費與組裝接點。

| 接點與固定來源 | P3 改接／必要驗證 |
| --- | --- |
| `policies/engineering-workflow-contract.md`、`reusable-workflow-contract.md`／`details`，`skills/project-delivery`／`project-orchestrator`／`planning`／`implementation-slice`／`docs-update`（P0 E01/E03/E21/E22） | 逐條共用義務 → P1 source-map → Codex 薄層；保留必讀觸發、授權、fallback、輸出與 relative links。`tests/test_policy_loading.py`、`test_engineering_workflow.py`、review disposition 與受影響 docs tests |
| Review／merge skills、`policies/exact-head-merge-review-contract.md`、GitHub profile（E15–E17/E23） | 分離中立契約與本 repo provider；保留 findings、scan 適用性、完整 range／coherence／changed head。Exact-head docs／validator／control-plane tests、review dispositions |
| `skills/loop-engineering/scripts/loop_core.py`／`loop_yaml.py`／`loopctl.py`、routing／profile／qualification／continuity（E05/E06/E10/E11/E25–E27） | 可執行程式、資料 schemas、registry 與 runtime facts 全留 Codex；只改文件消費接點。受影響 loopctl／loop-core／routing／qualification／continuity tests 與 evals；不能弱化 completion guards |
| Operational Evidence／Proposal／Evaluation families（E12/E13/E28/E29） | 對照章程反思義務與既有證據／提案／評估，保持 advisory、人工決策及 promotion 邊界；相關 tests／evals。未涉及的 Memory family 保留 default-off |
| `scripts/sync-plugin-package.py:SHARED_FILES/package_sources/verify`、plugin manifest／catalog（E18/E30） | 明確納入已驗 snapshot、lock、notices 與 links closure；全部 tracked source／generated inventory、bytes、modes、版本一致。`tests/test_plugin_packaging.py` 與離線 release-state validator |
| `install.sh:group_deps/group_skills/group_templates/template_target` 與 `catalog.yaml`（E19） | 手寫 resource lists 與 catalog dependencies 同步；temporary templates 目的地、預覽、backup/collision、安全失敗。Installer runtime groups／agent profiles tests，source/plugin/filesystem 三佈局閉合；不更新既有使用者安裝 |
| CLI handoff／native TUI reference、Desktop 三 adapters 與 deprecated aliases（E07–E09/E24） | 當次入口、namespace/schema、host、session、queued/ready 身分、權限與工具語意；CLI handoff／native runtime docs／受影響 installer tests。不能用 bundled CLI 或 app-server 代替 Desktop 資格 |
| `scripts/validate-repo.sh`、`tests/test-shards.yaml`、repository-validation CI（E31–E35） | 新測試仍由 Codex 持有，更新 exact partition；必要 repo checks／manifest-driven shards／CI 綁最新 PR head。不把 fixtures 或 controller 綠燈當 runtime／App ready |

P0 的 53 scripts／97 test modules／62 eval files 是固定來源盤點，不是已執行測試。
Hermes、Memory、第三方 mapping/failover、GitNexus hooks/controllers 保留原 family，
本包不啟用或重新資格化；P3 若實際改共用資源而影響既有 Hermes 包，需補其 dependency
closure 回歸，不能因不做新投入而省略既有 consumer 保護。

## 四個入口的獨立驗收

以下均為 P3/P4 計畫，P2 未執行。重用 [native capability contract](../native-runtime-capabilities.md)
和 [2026-10-14 點時證據](../codex-runtime-compatibility-evidence-2026-10-14.md)。
舊 help/schema 成功只支持當時的相容性描述；四入口版本、模型／effort、工具與資格仍需當次讀回。

| 入口 | 正面驗收與獨立證據 | 特有負面／恢復案例 |
| --- | --- | --- |
| Standalone CLI | executable/version、公開 help、有效設定／model/effort/sandbox/approval；實際 `codex exec` 在專用 fixture 載入固定文件、工具修改、固定 tests／docs、獨立 review。JSON events／exit／artifact 獨立讀回 | 不能把 process exit 0／最後摘要當完成；缺契約、denied tool、未知外寫效果、resume 身分錯誤都保持 blocked；resume/fork 按實際 help／schema另驗 |
| CLI TUI | 實際 TUI session 與 callable discovery、完整 namespace/schema；load／tools／approval、fork 不啟動 turn 的當次語意、explicit send、source cwd 與 child identity | 初始缺工具不能立刻稱 unavailable；未知／不相容 schema 回 manual prompt。超長 prompt／來源錯配／child identity 失敗不得偷用 Desktop payload 或重播；#251/#293 缺口不能由新 help 推定修復 |
| Desktop | 當次 app／host／公開 callable、project/source/target、queued→ready identity、有效 permissions/model/effort；固定文件與工具結果、task artifacts／DoD、獨立 review各自讀回 | `clientThreadId` 不當 ready `threadId`；缺公開工具、host／source錯配、unknown create/send結果先讀回。Shared profile 只代表唯讀 workflow expectation，非獨立 OS sandbox；#242 缺口不以 SSH／bundled成功推定修復 |
| Bundled CLI | 核對 Desktop 所附 executable 的身分／version，使用該 executable 的公開 help/argv與實際 fixture，分別查 model/effort/permissions、文件 digest、events/artifacts | standalone help／結果不可代用；Desktop更新導致版本／bytes漂移須重評。不能用 bundled app-server／private internals補 Desktop 缺失；失敗保持自身未資格狀態 |

每入口記錄 UTC 時間、OS／host 類別、可公開版本來源、實際 executable/control surface、
工具 schema／effective model/effort 與權限證據、Core/adapter revision/digest、layout、
fixture/protected spec/tests identity、commands/exit/result、failure/skip、findings/dispositions、
checkpoint／cancel／resume／unknown-effects 結果與下一步。私人原件留核可 Git 外位置，
公開只放去敏摘要與必要 hashes。無法觀察實際設定時標 `Unknown`，不靠提示文字假定生效。
Reviewer 可繼承 parent sandbox／approval，仍須作者獨立、唯讀約束及能力資格；
若個案需要技術唯讀隔離，再驗證該隔離，不能從 profile 名稱推定。

重用 `scripts/verify-engineering-workflow.py` 的固定 Codex fixture；四入口分別 prepare。
它只提供 functional observations，輸出 false-readiness，不能替代 lock 驗證、獨立審查、
OS isolation、runtime qualification 或 exact-head。P3 在 Codex 補 Core snapshot 的局部
驗證／負面 fixtures；不把 validator 放 Core、不為此增加 Grok runtime label。

## 負面案例與成功判準

每例需要正確 control 與獨立 readback；拒絕案例核對 promotion／dispatch／外寫零新增效果。

| 案例 | 預期結果／證據 |
| --- | --- |
| 浮動 ref、錯 repo／commit、未知 P1 revision、wrong file/set digest | Import／build 拒絕；同 bytes 不掩蓋來源身分錯配；舊 lock 與目的地保持原狀 |
| Missing/tampered required doc、漏必讀義務、broken link/anchor、unexpected inventory | Build 不 promotion；runtime 缺必要文件就停止；義務漏失由 source-map 對照及獨立 reviewer 捕捉，不能只靠 hash |
| 路徑穿越／絕對路徑、symlink/special/executable、超限檔、重複／case collision | 在讀取或寫出界外 bytes／執行 upstream 前拒絕；有界 inventory 與目的地前後 digest |
| Missing/altered MIT notice、來源／derived 混淆、手改 generated copy、installer漏resource | 三佈局驗證失敗；保持 last verified snapshot，不帶半套新檔與 notices promotion |
| 同名 skill／不同安裝root／錯 CODEX_TEMPLATES_DIR／載入另一版本 | 核對實際載入 bytes／來源；collision 安全拒絕或按既有 explicit resolution，不能默默升權或 fallback |
| 提示／metadata要求擴權、停止review、換模型／provider、啟用禁止功能 | 不形成授權；拒絕 scope／permission widening，原 sandbox／approval／default-off 邊界保留 |
| Author self-review、不足 tier、未知 parent sandbox、borrowed runtime qualification | Review／dispatch資格 fail closed；可用有證據的安全 fallback，不能宣稱custom-profile ready或自審取代獨立性 |
| Queued／錯host/session、denied tool、cancel／斷線、未知外部效果 | 保留 checkpoint與失敗；先查現況／有效授權／writer。被拒操作僅在已知未執行且有新相關證據時重試一次；未知結果先讀回，不盲重播 |
| Changed PR head／base／Core digest、舊 receipt、missing CI／App／未解 finding | readiness 回 REVIEW_REQUIRED／BLOCKED；完成最新完整 range與所選 provider gate，不能由 tests／controller exit 0放行 |
| Staging中斷／promotion前失敗、舊版重建／revert | 新snapshot不被接受；舊 lock重建驗證成功與授權回復分開記錄，未知 writer／外寫結果不得覆寫或刪除 |

## P2 DoD、驗證與 P3 交接

P2 DoD：兩文件有 immutable來源、完整 bounded scope、責任／義務與相依對照、
明定 lock/digest/notices／三佈局、四入口及負面計畫、限制／未驗證事項；本機 links/anchors、
source references、雙語主要資訊一致、實際 GitHub Markdown 呈現、scope／private-data／whitespace／source-package parity
查核，獨立 docs／契約 review與 finding disposition。沒有實作、安裝、runtime資格或已固定P1的宣稱。

本包依 tracked `scripts/project-python`（Python 3.12.9／PyYAML 6.0.3）做查核。
執行 changed-doc links/anchors與引用範圍、`git diff --check`、離線 release-state、
plugin parity、`validate-repo.sh --skip-unit-tests`；embedded unit tests 明示略過。
沒有 executable／active契約／安裝變更，不新增鏡像實作的測試，也不把 P3計畫記為passed。
原始驗證與review報告留Git外並在交付回報定位；本計畫不預填實際PASS結果。
GitHub 呈現驗收在 draft PR 建立後、完整 P2 DoD／final handoff 前執行：逐份打開
最終 commit 的 rendered blob，檢查表格、雙語導覽、章節／links／anchors及內容完整。
Owner 為本包 writer，durable target 為 Issue #333／其 draft PR；先交付已審查 draft
才能取得正式呈現位置，因此 precommit 可記有界待驗收項，不能聲稱完整 P2 Passed。
剩餘風險為 GitHub 版面／導覽尚未驗證；以最終 revision／兩檔 hashes、頁面位置及
公開呈現觀察綁定驗收證據。完成觸發為兩檔都通過，否則修正並按變更重審／重驗；
changed head 後重做完整 exact-head review。此待驗收項不阻擋必要的 draft 準備，
但阻擋完整 P2 DoD 宣稱與正式 readiness。

安全判斷：檢查本包的來源信任、權限、檔案處理、notices、組裝、安裝與回復說明。
本次只新增未被runtime消費的設計文件，沒有改變 executable、security/trust enforcement、
敏感資料處理、dependencies或installation paths；預期 Security Diff Scan 不適用，
由最終diff與獨立review再次確認並記錄理由，不能記成 scan Passed。
P3 的 lock loader／輸入／組裝／installer將影響供應鏈與檔案邊界，需初次即深入審查
與比例 Security Diff Scan，不沿用P2的不適用判定。

P3 不在本包開始。あき需核對 P1 review／正式merge、immutable revision／逐檔及集合digest、
source-map／notices、P2與定稿義務漂移、P3 scope／Issue／branch／writer／授權與runtime環境。
四入口未驗收、不適用／Unknown／Failed／Blocked各自保留。缺必要來源、ownership／授權
衝突、review／scan／平台gate或安全能力時停止相依工作，繼續獨立安全部分。

反思判準：設計與驗收計畫是否足以保留現有Codex行為，以及能否辨識跨入口假資格與
來源漂移。重用P0／既有驗證器比重建清冊或新協調框架維護成本較低，這是設計判斷；
耗時、token、費用與節省比例未量測。需要P1最終契約與P3實測才能判定實際需求完全滿足。

<a id="english"></a>

## English

### Packet and dependencies

Issue #333 owns the branch `codex/issue-333-p2c-core-preparation` and two new
documentation files. The delegated main agent is the sole writer. An independent
reviewer is read-only. あき retains long-term coordination. Local/remote identities,
Issue scope, remote branch, fetch, clean dedicated checkout and upstream were
checked before editing. The fixed Codex base and Core P0 revisions are stated
above and in the design. Private checkout paths, charter and raw runtime evidence
stay outside Git. This checkout has no `.agents/skills`; read tracked `skills/`.

Avoid PR #326/#324 README, roadmap, model guide and existing plan files. Do not
import #317 candidates. Core is read-only and a separate topic owns P1, which the
coordinator reports has not started. Conditional
commit/push/draft PR follow the charter and repo gates. Merge needs current complete
exact-head content and selected provider evidence; a draft cannot pass the ready
profile. No tags, Releases, deployment, other-project skill updates, EdgeInstaller,
Memory/Hooks/Schedulers, Orca, Codex Grok/LiteLLM routing, privilege expansion,
force push or data deletion. No new scheduler or coordination system.

Reuse P0's complete inventory. Each P3 slice must inspect its complete
producer/consumer/test dependencies and update only affected document-consumption
and assembly components. Inspect these families:
workflow policies and delivery skills; review and exact-head/provider adapters;
loop/routing/profile/qualification/continuity code and schemas; evidence/proposal/
evaluation; generated plugin allowlists and manifest/catalog; installer resource
lists and group dependencies; CLI/TUI/Desktop entry adapters and aliases; validators,
test partition and exact-head CI. Code, validators and tests stay in Codex.
The table above maps those families to P0 evidence and existing tests. The 53
scripts, 97 test modules and 62 eval files are inventory counts, not executed tests.
Retain deferred/default-off families. If shared resource changes affect existing
Hermes consumers, verify their closure without starting new Hermes work.

### Independent entry acceptance

These tests are planned for P3/P4, not executed in P2. Reuse the dated capability
documents without treating old help or schemas as current qualification.

- Standalone CLI: verify executable/version, public help and effective settings;
  run a real isolated `codex exec` fixture with fixed documents, tools, protected
  tests, docs and independent review. Read events, exit and artifacts separately.
  Reject missing contracts, denied tools, false completion and wrong resume identity.
- CLI TUI: verify the actual session, complete callable discovery and schema,
  loading, tool use, approvals, fork/explicit-send behavior, cwd and child identity.
  Missing initial tools require discovery. Unknown/incompatible schemas, long
  prompts or identity failures require safe fallback, not Desktop payloads.
- Desktop: verify public app/host/callables, project/source/target, queued-to-ready
  identity, effective rights/model/effort, artifacts and independent review. Do not
  treat `clientThreadId` as ready `threadId`. Read unknown create/send outcomes
  before retrying. A profile's read-only expectation is not OS isolation.
- Bundled CLI: verify the exact bundled executable/version and its own public
  help, production argv and real fixture. Check settings, document digest, events
  and artifacts independently. Standalone results do not qualify it. Updates
  invalidate affected evidence; private internals cannot supply Desktop fallback.

Keep #242/#251/#293 gaps open unless fresh evidence resolves them. Record UTC,
OS/host class, public version source, surface/executable, schema, observed effective
model/effort and permissions, Core/adapter revision/digest, layout, protected fixture
identity, commands/results, failures/skips, findings/dispositions and checkpoint,
cancel/resume/unknown-effect outcomes. Keep private originals outside Git; publish
sanitized summaries and necessary hashes. Unobserved settings remain Unknown.
Reviewer inheritance of parent sandbox/approval is allowed, but independence,
read-only workflow scope and role capability remain required. Verify technical
isolation separately when a specific case requires it.

Prepare the existing Codex engineering fixture separately for each entry. Its
functional results and false-readiness fields do not prove lock validity, review,
OS isolation, runtime qualification or exact-head readiness. P3 adds bounded Core
checks in Codex; no validator or Grok runtime label is added to Core.

### Negative cases and handoff

Use correct controls and independent readback. Test wrong/mutable source identity,
unknown revision, wrong hashes, missing/tampered documents or obligations, broken
links, unsafe paths/files/modes/sizes, duplicate/colliding inventory, missing/altered
notices, generated drift, incomplete installer resources and wrong load roots.
Reject before unsafe reads, writes or upstream execution; do not promote failed
staging. Preserve the last verified target. Test prompt/metadata permission
widening, skipped reviews, model/provider changes and forbidden feature activation.
Test self-review, insufficient tier, unknown parent sandbox and borrowed runtime
qualification. Use only evidenced compatible fallbacks.

Test queued/wrong host/session, denial, cancellation, disconnection and unknown
effects. Preserve checkpoints and failures; read state, authority and writer before
any retry. Retry a denied operation once only after known nonexecution and new
relevant evidence; read uncertain outcomes before any retry. Changed heads,
Core identities, stale receipts, missing CI/App or open findings return readiness
to REVIEW_REQUIRED/BLOCKED. Green tests or controller jobs cannot authorize merge.
Test failed staging and old-lock rebuild/revert without overwriting unknown writers
or deleting data. Recovery is a plan, not a passed test.

P2 acceptance requires fixed sources, bounded ownership, obligation/dependency
mapping, lock/digest/notices and three-layout design, four-entry/negative plans,
valid references/links, consistent bilingual claims, actual GitHub Markdown
rendering, scope/privacy/whitespace checks,
offline source/package checks and independent review with dispositions. Use tracked
`scripts/project-python` at Python 3.12.9/PyYAML 6.0.3. Planned checks include changed
doc links/anchors and source ranges, `git diff --check`, offline release-state,
plugin parity and `validate-repo.sh --skip-unit-tests`. Embedded unit tests are
explicitly skipped. Reports outside Git record actual results, not prefilled PASS.
After draft PR creation, open each final-commit rendered blob and verify tables,
language navigation, sections, links/anchors and complete content. The writer owns
this pending check, tracked in Issue #333 and its draft PR. A reviewed draft is
needed to obtain the final rendering location. Precommit may retain this bounded
follow-up, but full P2 completion/readiness remains blocked until both documents
pass. Record revision, file hashes, page locations and rendered observations.
Remaining risk is unverified layout/navigation. Failed checks require fixes and
proportional rereview; changed heads require complete exact-head review again.

Inspect final trust, rights, file-handling, notices, assembly, installation and
recovery guidance. P2 adds inactive design only; expected Security Diff Scan status
is Not Applicable, subject to final diff and independent review. Never call a skipped
scan Passed. P3 loaders/assembly/installers require deep review and proportional
Security Diff Scan for supply-chain/file boundaries; do not reuse P2 applicability.

P3 remains blocked until あき verifies P1 review and merge, immutable file/set
identity, source-map/notices, final design alignment, Issue/branch/writer/authority
and runtime environment. Preserve per-entry Unknown/Failed/Blocked/Not Applicable.
Stop dependent work on required source, ownership, authority, review, scan, platform
or safety gaps; continue independent safe work. Reuse avoids a duplicate framework,
but time, token, cost and savings are unmeasured. P1/P3 evidence is needed to prove
actual preservation of Codex behavior. English uses clarity principles; full
ASD-STE100 conformance and current edition are unverified as stated in the design.
