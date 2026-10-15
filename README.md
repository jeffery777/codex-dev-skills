# codex-dev-skills

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Runtime: Codex CLI + Desktop](https://img.shields.io/badge/runtime-Codex%20CLI%20%2B%20Desktop-blue)](#runtime-compatibility)
[![Repo hygiene](https://img.shields.io/badge/hygiene-validate--repo.sh-informational)](#verification)

給 Codex CLI／Desktop 使用的開源工程工作流：把明確的任務帶過規劃、實作、驗證、
獨立審查、文件同步與交接。技能提供可重用步驟與證據要求；當次 runtime 提供工具，
使用者與專案決定授權。安裝成功、子代理摘要或測試綠燈都不等於可以發布或合併。

繁體中文預設顯示；[English](#english) 可展開。英文以清楚、一致為目標，
完整 ASD-STE100 符合性尚未驗證。

文中四個常用詞：

| 詞彙 | 意思 |
| --- | --- |
| runtime | 當次執行環境，包括可用工具、版本與權限 |
| profile | 可選的角色／model／effort 設定檔；檔案存在不證明當次可用 |
| DoD（完成條件） | 開工前約定、可查核的完成標準 |
| formal gate（正式關卡） | 根據證據判斷能否進入下一階段；不增加操作授權 |

<a id="who-it-is-for"></a>
## 適合誰、何時使用

適合維護開源或團隊 repository、需要明確驗收與人工決策邊界的使用者。
先選最小入口；一般有界交付不需要先建立 loop ledger。

<a id="usage-examples"></a>
<a id="choosing-an-entry-point"></a>
<a id="focused-implementation"></a>
<a id="routine-code-review"></a>
<a id="routine-documentation-review"></a>
<a id="orchestrated-review-closure"></a>
<a id="bounded-milestone-slice"></a>
<a id="task-continuation"></a>
<a id="merge-readiness"></a>

| 你的目標 | 入口 |
| --- | --- |
| 改一個已界定的小問題 | `implementation-slice`；不清楚下一步時先用 `planning` |
| 只讀審查程式或文件 | `code-review`／`docs-review`；高風險程式差異用 `code-review-deep` |
| 推進一個較大的有界目標 | `project-delivery`／`project-orchestrator` |
| 從已保存狀態接續 | `task-continuation`／`milestone-continuation` |
| 已明確選用 durable loop | `loop-engineering`；依 repo 的 loop spec／ledger 執行 |
| 評估 change request 的完整差異 | `merge-review`／`merge-review-deep`；正式決策另用適用 gate |

[完整技能選擇指南](docs/skill-selection-guide.md) 說明 primitive 與 formal gate 的差別。
[進階 reference](docs/guides/workflow-reference.md#prompt-examples) 保留原 prompt 範例；
單純要求 review 時保持唯讀，除非使用者另外要求修正。

<a id="quick-start"></a>
## 快速開始

從已核對的 source checkout 先查看可選群組：

```bash
./install.sh list
```

再於[安裝選擇](#installation)選 **plugin 或 filesystem 其中一條路徑**。
安裝後開新 chat/session，按名稱使用技能，例如：

```text
Use code-review on the current working tree.
Prioritize correctness bugs, regressions, missing tests, and contract risks. Stay read-only.
```

開始工作前讀目標專案的 `AGENTS.md`、規格、計畫及 Git 狀態，明定 scope、DoD、
writer 與驗證方法。已給定的明確授權持續有效；遇到新範圍、破壞性操作、風險決策
或未授權外寫才停下。Review／gate 本身不增加任何操作權限。

<a id="installation"></a>
## 安裝選擇

同一 Codex profile 只使用一種 distribution、一個技能 target，避免重複 selectors。
安裝不會改個人主代理設定或授權 live runtime 操作。

### Universal plugin

Repository marketplace 指向 `plugin/codex-dev-skills/` 的窄套件；不把整個 checkout
或未追蹤狀態放入 plugin cache。CLI 在 source checkout 執行：

```bash
codex plugin marketplace add .
codex plugin add codex-dev-skills@codex-dev-skills-local
codex plugin list --json
```

Desktop 使用 repository marketplace source。安裝後開新 chat/session；同一 profile
不要再疊加 filesystem 安裝。`/plugins` 是 CLI 互動瀏覽器，不是交付授權。

### Filesystem installer

依需要選一個群組；相依群組會自動帶入：

```bash
./install.sh install codex-review-workflow
```

需要實作與交付流程時改選：

```bash
./install.sh install codex-delivery-workflow
```

`shared-review-gates` 只提供正式 gates／templates；`desktop-delivery-workflow` 為
有意使用 Desktop 控制時的可選群組。`codex-cli-session-handoff` 與
`codex-agent-profiles` 都是額外選擇；profiles 不包含於 `--all`。
安裝 profiles 會寫入 runtime TOMLs，須先 preflight、再讀回身分；不會啟用 candidate routing，
也不會選取或改變目前 chat 的主代理設定。
`./install.sh install --all`／`./install.sh update --all` 也涵蓋 Desktop 群組，應先確認需要。

預設 skills 在 `~/.agents/skills`，templates 在 `~/.codex/templates`；
`CODEX_DEV_SKILLS_TARGET=legacy` 保留 `~/.codex/skills` 相容入口，不會搬移或刪除舊安裝。
自訂 `CODEX_SKILLS_DIR`／`CODEX_TEMPLATES_DIR` 必須明確設定
`CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES`。

先檢查 `status`／`diff` 再 update；uninstall 是刪除操作，須明確確認。
新安裝／force replacements 使用 `0700` directories、`0600` regular files、
`0700` source-executable files，可能影響其他本機帳號的讀取權。Unsafe paths／碰撞會拒絕，
不會偷偷修權限、搬移 imported/plugin state 或覆寫 `~/.codex/AGENTS.md`。
Force backup 與 rollback 有明確限制，並非所有失敗都原子回復；出現 `CRITICAL` 時保留
回報位置，先人工核對。詳細命令與前置見[進階安裝 reference](docs/guides/workflow-reference.md#installation-reference)
及[排錯指南](docs/troubleshooting.md)。

<a id="runtime-compatibility"></a>
<a id="codex-cli-session-handoff"></a>
<a id="codex-desktop-delegated-delivery"></a>
## 原生委派與獨立任務

**優先沿用當次已提供、語意相符的原生能力。** Subagents 與獨立 thread/session 是
兩種生命週期；不要為已原生的建立、派工、等待與結果回傳再加一層控制器。
`desktop-thread-delegation` 只處理共享編排已選定的任務去向，不負責選下一項工作。

| 需求 | 怎麼選、驗什麼 |
| --- | --- |
| 目前工作內的有界子任務 | 使用當次 native subagent 的 spawn／steer／wait／collect／interrupt；記錄 parent／child、scope 與 ownership，主代理整合實際產物 |
| 真正獨立的 task/thread/session | 明確有此需求與授權後，選當次 CLI/TUI 或 Desktop 的公開控制面，核對完整 namespace／schema、來源 cwd／host、ID、啟動與續行語意 |
| 缺能力或契約不相容 | 保留 `unknown`／`unavailable` 的實際搜尋範圍，使用手動 prompt 或相同契約的安全 fallback；不借用另一入口的 payload |

安裝 skill 不會注入 runtime 工具。初始清單沒有工具時，若有正式 deferred discovery
就先查核；無法完整觀察不能直接宣稱平台不支援。CLI `/app` 或 `codex app <path>`
只轉換操作入口，不改任務授權與完成標準；Desktop fork 可能包含 interrupted active turn，
應讀回 ownership 與狀態。以公開讀回確認 unknown dispatch
結果，再決定下一步，不盲目重播。

現有 CLI shell executor 的 private clone、expected HEAD、bounded patch、exact UUID、
replay／no-recursion 與 source readback 保障仍有效；沒有證據證明其他 native 路徑
與它等價。這次只澄清選擇與引用，沒有刪除 executor、改 routing defaults，
也沒有宣稱所有 fallback 冗餘已移除。

CLI、CLI TUI、Desktop、Bundled CLI 各自驗證版本、工具、有效 model／effort、權限、
來源與產物；一個入口成功不替其他入口取得資格。原生 subagents 可共享 parent sandbox；
唯讀角色指示不等於獨立 OS 隔離。命名 model／role mappings 依
[model policy](policies/model-selection-policy.md)／[主與子代理設定](docs/main-agent-and-subagent-settings.md)，
不把舊點時 compatibility 紀錄當作當次資格。

`shared` 是共享工程步驟，`cli` 是 CLI 入口，`desktop` 需要獨立 Desktop 控制，
`plugin-dependent` 需要指定 plugin／connector。`desktop` 相容標籤不把共用推理或
subagent delegation 限定為 Desktop。完整界線見
[native capability contract](docs/native-runtime-capabilities.md#thread-capability-discovery)、
[shared subagents](docs/native-runtime-capabilities.md#shared-subagents)、
[CLI adapter](skills/cli-session-handoff/SKILL.md) 與
[Desktop adapter](skills/desktop-thread-delegation/SKILL.md)。

<a id="safety-and-privacy"></a>
<a id="included-scope"></a>
<a id="excluded-scope"></a>
<a id="memory-m1-local-opt-in-pilot"></a>
## 安全、支援與預設關閉項目

- Repository／Git、驗證、獨立 review 與接受的 platform state 才支持完成結論。
  Worker summary、Goal／thread status、dispatch、exit 0 或單一 helper PASS 都不能取代。
  Commit／push／PR／merge／tag／Release／deploy、平台留言與 review submission 各自保留授權及 gates。
- 不把 credentials、private keys、私人 paths、runtime files、logs、sessions、app state、
  local databases 或 machine-specific config 提交公開 Git；例子只用無敏感 placeholders。
- Memory 與相關 opt-in 預設關閉。`memory-off` 是完整路徑；M0/M1 safety/conformance
  或 synthetic qualification 不證明效益或 production 資格。M2／V3-C 仍需新證據與人工決策；
  沒有自動 recall/write、服務、scheduler、hook 啟用或 PlugMem／Mem0 投入。
- GitNexus、hooks、profiles、qualification store 與本機模型映射各有明確 opt-in 與能力邊界。
  原生 runtime memory／imports 不等於本套 memory contract。Read-only 角色不是權限擴張；
  model 切換或設定檔也不證明既有對話已生效。[進階安全 reference](docs/guides/workflow-reference.md#advanced-boundaries)
  保留各功能限制。
- Hermes 使用獨立 `hermes/catalog.json`／`install-hermes.sh`，Codex plugin／installer
  不會自動裝 Hermes adapters；`shared` 不宣告 Hermes 相容。已有能力、未支援範圍與必要
  native 驗收依[Hermes 指南](docs/guides/hermes-agent.md)；本次沒有擴大 Hermes 支援。
- 不包含一般 presentation/PPTX、未驗證 UI packs、knowledge／vault capture、私人 runtime state
  或 legacy non-Codex workflows。現有 advisory graph 也不代表安裝／修改 Obsidian runtime。

<a id="how-projects-use-these-skills"></a>
## 三個 repository 與專案自己的規範

| Repository | 責任 |
| --- | --- |
| [engineering-workflow-core](https://github.com/jeffery777/engineering-workflow-core) | 純 Markdown 共用工程契約與來源／notices；不含 runtime、validator 或 installer |
| [codex-dev-skills](https://github.com/jeffery777/codex-dev-skills) | Codex 技能、工具、model／effort／profiles、session、驗證、組裝與安裝 |
| [grok-build-dev-skills](https://github.com/jeffery777/grok-build-dev-skills) | 獨立 Grok 接口及其設定、工具／權限／session、驗證與組裝；不由本套代為操作模型 |

兩端各自消費 immutable Core revision／digest，runtime 不追蹤 mutable Core `main`。
Codex 的固定來源、11 檔 snapshot／lock、兩種 digest 與 notices 見
[Core 接法](docs/core-contract-snapshot.md)；檔案缺失、身分／digest／root 不明或不符時，
停止相依工作。Digest 驗證是完整性證據，不自行證明來源信任、runtime 資格或操作授權。

使用本套的專案保留自己的 `AGENTS.md`、規格、計畫與 provider overlay。
GitLab／其他 provider 不會因安裝技能被套用本 repo 的 GitHub profile。
維護本 repo 才依 [CONTRIBUTING.md](CONTRIBUTING.md) 先 Issue/readback、遠端 ID branch/readback、
fetch、checkout／ownership 核對，再修改；該 repo 專屬流程不隨技能安裝。

<a id="verification"></a>
## 驗證與版本

從 source checkout 使用 tracked resolver：

```bash
# The resolver fails closed unless the tracked .python-version is honored.
./scripts/project-python --version
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/validate-repo.sh
```

Pinned Python 是 3.12.9，PyYAML 是唯一 Python runtime dependency。Resolver 會拒絕版本不符；
依序選 `CODEX_PROJECT_PYTHON`、repo `.venv`、`pyenv` 或已正確的 `python3`。
失敗先查環境，不改用另一個 Python 安裝依賴，也不複製 `.venv` 到 worktree。

Focused tests、affected shards 與完整 matrix 分別記錄；PR readiness 前需完整 shards，
hosted CI 的 required aggregate 為 `Validate repository`。`--skip-unit-tests` 只略過
embedded unit groups，仍跑 hygiene／validators／evals／catalog／plugin parity；SKIP 不當 PASS。
[進階驗證 reference](docs/guides/workflow-reference.md#verification-reference) 保留 shard 命令及完整 local equivalent。

Repository source/package version 以 `catalog.yaml` 為準，與 installer／plugin manifest 一致。
Release notes 是 point-in-time 準備／歷史紀錄；出版事實須另外查核 GitHub Release metadata
與 annotated tag。離線驗證不證明已出版。完整正式交付依
[exact-head contract](policies/exact-head-merge-review-contract.md) 及專案所選 provider profile；
本 repo 的 [GitHub profile](policies/github-exact-head-enforcement-profile.md) 保留 CI、strict receipt、
專用 App、native-latest 與 merge 前 live readback，check 不把自己算作上游 CI。

<a id="skills"></a>
<a id="workflows"></a>
<a id="examples"></a>
<a id="loop-engineering"></a>
<a id="gpt-6-daily-routing"></a>
<a id="contribution-guidelines"></a>
## 深入閱讀

- [技能選擇](docs/skill-selection-guide.md)、[使用模型與專案 artifacts](docs/usage-model.md)
- [進階操作、原命令／prompts 與內容 crosswalk](docs/guides/workflow-reference.md)
- [完整 skills 清單](docs/guides/workflow-reference.md#skills-and-workflows)、[examples](examples/loop-engineering.md)
- [主／子代理設定](docs/main-agent-and-subagent-settings.md)、[本機角色映射](docs/guides/local-model-mapping.md)
- [Loop Engineering](docs/loop-engineering.md)、[repo-owned ledger](docs/loop-state-ledger.md)、[Memory contracts](docs/external-memory-contract.md)
- [Runtime 相容與 fallback](docs/runtime-compatibility.md)、[context continuity](docs/context-continuity.md)
- [Release readiness](docs/release-readiness.md)、[roadmap](docs/roadmap.md)、[MIT LICENSE](LICENSE)

<details>
<summary>English — purpose, quick start, installation and safety</summary>

## English

`codex-dev-skills` is an open-source engineering workflow pack for Codex CLI and
Desktop. It takes a bounded objective through planning, implementation,
verification, independent review, documentation and handoff. Skills define
steps and evidence; the active runtime supplies tools. The user and project
retain authority. Installation, a worker summary or green tests alone do not
authorize publication or merge. Full ASD-STE100 conformance is unverified.

Here, **runtime** means the active environment, tools, version and permissions.
A **profile** is an optional role/model/effort configuration file; its presence
does not prove it works in the active environment. **DoD** means agreed,
verifiable completion conditions. A **formal gate** assesses evidence before
the next stage and grants no new action authority.

### Audience and entry points

Use the smallest entry that fits the work. Choose `implementation-slice` for a
clear change, `planning` for unclear scope, `code-review` or `docs-review` for
read-only feedback, and `code-review-deep` for high-risk code. Use
`project-delivery` / `project-orchestrator` for bounded delivery,
`task-continuation` / `milestone-continuation` for saved work, and
`merge-review` / `merge-review-deep` for the complete change-request range.
Formal gates make separate evidence decisions. `loop-engineering` is for an
explicitly chosen durable loop or a repo-required loop; ordinary delivery does
not require a ledger. See the [selection guide](docs/skill-selection-guide.md)
and the unchanged [prompt examples](docs/guides/workflow-reference.md#prompt-examples).
Review stays read-only unless the user asks for fixes.

### Quick start and installation

From a verified source checkout, run `./install.sh list`, then choose exactly
one distribution path for each Codex profile. The command examples above are
shared by both languages. For the plugin, use `codex plugin marketplace add .`,
`codex plugin add codex-dev-skills@codex-dev-skills-local` and
`codex plugin list --json`. The marketplace selects the narrow generated
`plugin/codex-dev-skills/` package; it excludes untracked checkout state.
Desktop uses the repository marketplace source. `/plugins` is the interactive
CLI browser. Start a new chat/session after installation.

For filesystem installation, choose `./install.sh install codex-review-workflow`
or `./install.sh install codex-delivery-workflow`; dependencies are automatic.
`shared-review-gates` supplies gates/templates without review primitives.
`desktop-delivery-workflow`, `codex-cli-session-handoff` and
`codex-agent-profiles` are explicit choices. Profiles are excluded from
`--all`. Installing profiles writes runtime TOMLs; preflight first and read back
installed identities. It does not enable candidate routing or select/change
the current chat's main-agent configuration. `./install.sh install --all` and `./install.sh update --all` include
Desktop workflows and need an intentional choice.

Default skills use `~/.agents/skills`, templates use `~/.codex/templates`, and
`CODEX_DEV_SKILLS_TARGET=legacy` retains `~/.codex/skills` without migration or
deletion. Custom skill/template roots require
`CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES`. Do not combine filesystem,
imported or plugin copies with the same skill names. Inspect status/diff
before update; uninstall deletes installed artifacts and requires explicit
confirmation. Fresh installs/force replacements use 0700 directories, 0600
regular files and 0700 source-executable files, which can remove other local
accounts' access. Unsafe paths/collisions fail closed without silent chmod,
import migration or an overwrite of `~/.codex/AGENTS.md`. Force backup/rollback
has bounded guarantees; preserve reported locations after `CRITICAL` and
review recovery manually. See [installation reference](docs/guides/workflow-reference.md#installation-reference)
and [troubleshooting](docs/troubleshooting.md).

Read project instructions, specs, plans and Git state before work. Define
scope, DoD, ownership and verification. Existing explicit authority remains
valid; stop for new scope, destructive actions, risk decisions or unauthorized
external writes. A review or gate grants no new authority.

### CLI And Desktop Entry Paths

Codex CLI enters the shared layer directly. Prefer the active native capability
when its semantics fit. Native subagents are bounded children of current work;
separate user-owned threads/sessions have their own lifecycle and identity.
Reuse native create/dispatch/wait/result operations rather than adding another
controller. The parent still integrates artifacts and verifies completion.
`desktop-thread-delegation` handles only the task already selected by shared orchestration;
it does not choose the next task.

For a truly independent task, first confirm intent and authority, then inspect
the actual CLI/TUI or Desktop namespace/schema, source cwd/host, returned IDs
and start/continuation semantics. Skill installation cannot add runtime tools.
Initial absence requires supported deferred discovery when available; an
incomplete observation stays unknown. Read back an uncertain dispatch before
retrying. Use a manual prompt or contract-preserving fallback when unavailable
or incompatible; do not exchange payloads between surfaces.

The CLI shell executor still requires its private clone, expected HEAD,
bounded patch, exact UUID, replay/no-recursion and source readback controls.
Equivalence with another native path has not been proved. This documentation
change removes no executor, changes no routing default and makes no claim
that all fallbacks are redundant. CLI `/app` or `codex app <path>` is a surface
transition; it does not change task authority or completion. A Desktop fork
may include an interrupted active turn, so read back ownership and state.

CLI, CLI TUI, Desktop and Bundled CLI each need their own effective tool,
model/effort, permission, source and artifact evidence. A subagent may inherit
the parent sandbox; read-only instructions are not separate OS isolation.
`shared` means common engineering steps, `cli` a CLI entry, `desktop` separate
Desktop controls, and `plugin-dependent` a named plugin/connector dependency.
Desktop compatibility labels do not restrict shared reasoning or subagents
to Desktop. Use the [capability contract](docs/native-runtime-capabilities.md#thread-capability-discovery)
for discovery/authority, and [model policy](policies/model-selection-policy.md)
plus [settings](docs/main-agent-and-subagent-settings.md) for named mappings.

### Safety, support and three repositories

Repository/Git state, verification, independent review and accepted platform
state support completion. Worker/Goal/thread status, dispatch, exit 0 and a
helper PASS do not replace them. Commit/push/PR/merge/tag/Release/deploy,
platform comments and review submissions retain their own authority/gates.
Keep credentials, keys, private paths, runtime files, logs, sessions, app state,
local databases and machine-specific configuration out of public Git. Use
generic nonsensitive examples.

Memory is optional and default-disabled. `memory-off` is complete. M0/M1
safety/conformance and synthetic qualification are not efficacy or production
qualification. M2 and V3-C require new evidence and a human decision. No
automatic recall/write, service, scheduler, hook activation, PlugMem or Mem0
adoption follows. GitNexus, hooks, profiles, qualification stores and local
model mapping have separate opt-ins. Runtime memories/imports are distinct;
model/config changes do not prove an existing conversation changed.

Hermes uses separate `hermes/catalog.json` / `install-hermes.sh` entrypoints.
Codex plugin/installer does not install its adapters, and `shared` does not
qualify Hermes. The [Hermes guide](docs/guides/hermes-agent.md) retains limited
support, unsupported capabilities and required native verification. This
change expands no Hermes support. General presentation/PPTX, unverified UI
packs, knowledge/vault capture, private runtime state and legacy non-Codex
workflows remain excluded; advisory graph output installs no Obsidian runtime.

[Core](https://github.com/jeffery777/engineering-workflow-core) owns Markdown
contracts/provenance/notices; this repository owns Codex skills, tools,
model/effort/profiles/session, validators, packaging and installation.
[Grok](https://github.com/jeffery777/grok-build-dev-skills) owns its independent
interface and qualification; this pack does not operate its models. Interfaces
consume immutable Core revisions/digests, not runtime Core `main`. See the
[11-file snapshot, lock and notices](docs/core-contract-snapshot.md). Missing or
unknown required files/root/trust metadata or mismatched identity/digests stop
dependent work. Integrity does not establish trust, authority or qualification.

Each adopting project keeps its own instructions/provider overlay. Installing
shared skills does not impose this repository's GitHub profile on GitLab or
another provider. Only maintenance here follows [CONTRIBUTING](CONTRIBUTING.md)'s
Issue/readback → remote ID branch/readback → fetch → checkout/ownership → edits.

### Verification and further reading

Use the tracked `project-python` resolver for source checks; Python 3.12.9 is
pinned and PyYAML is the only runtime dependency. It selects
`CODEX_PROJECT_PYTHON`, repo `.venv`, `pyenv`, then an already-correct `python3`,
and rejects mismatch. Diagnose environment resolution before installing
dependencies; do not switch interpreter or copy `.venv` into worktrees.
Record focused tests, affected shards and the full matrix separately. Before
PR readiness, all shards must pass; hosted CI exposes `Validate repository`.
`--skip-unit-tests` skips embedded unit groups, while structural/eval/parity
checks still run. SKIP is not PASS. [Verification reference](docs/guides/workflow-reference.md#verification-reference)
retains exact commands.

Repository source/package version comes from `catalog.yaml` and must match
installer/plugin manifest. Release notes are point-in-time records; GitHub
Release metadata and the annotated tag establish publication separately.
Offline checks do not prove publication. Follow the [exact-head contract](policies/exact-head-merge-review-contract.md)
and selected provider profile. This repository's [GitHub profile](policies/github-exact-head-enforcement-profile.md)
requires CI, strict receipt/readback, dedicated App/native-latest and final
live readback; readiness cannot count itself as upstream CI.

See [usage model](docs/usage-model.md), [advanced reference/crosswalk](docs/guides/workflow-reference.md),
[Loop Engineering](docs/loop-engineering.md), [ledger](docs/loop-state-ledger.md),
[memory](docs/external-memory-contract.md), [runtime compatibility](docs/runtime-compatibility.md),
[context continuity](docs/context-continuity.md), [release readiness](docs/release-readiness.md),
[roadmap](docs/roadmap.md) and [MIT license](LICENSE).

</details>

<details>
<summary>相容與歷史說明 / Compatibility and historical notes</summary>

以下保留舊 README 的點時歷史與舊連結。它們不代表當次 runtime 或出版狀態：
v0.13.0 的 V3-B、v0.14.0 的 default-disabled M0/M1、v0.15.0 的協調改進、
v0.16.2 的雙入口介面、v0.16.3 的 wrapper 退役準備、v0.17.0 的 context continuity、
v0.17.1 的文件一致性、v0.18.0 的 V1 正式退役及 v0.18.1 的後續狀態修正各保留原紀錄。
v0.18.2 的 CLI/MCP 與 CI orchestration 調整亦為歷史，不推定現在能力。
V3-B 的 `evaluationctl.py` 與獨立 replay 產物永久不具 promotion 權；
M0/M1 的 `loop-memory-operation/v0`、`loop-memory-qualification/v0` 各自保留權限界線，
出版不等於啟用、升級或效益證據。V3-A 只提出 evidence-to-proposal；
須另經 human/platform promotion gate，CLI 不能 apply、commit、push、建立 PR、approve、
activate、promote、merge、release、deploy 或外寫。下列 Issue／PR／commit／tag 是共同歷史識別碼。

These are historical records, not live runtime or publication pointers.
V3-B is the v0.13.0 evaluation baseline, with `evaluationctl.py` and independent
replay; its packet cannot promote. The default-disabled M0/M1 safety/conformance
baseline was published in v0.14.0: publication is not activation, promotion, or efficacy evidence.
`loop-memory-operation/v0` and `loop-memory-qualification/v0` retain separate
authority. V3-A is a proposal-only evidence-to-proposal layer behind a pending
human/platform promotion gate. The CLI cannot apply, commit, push, create a PR, approve, activate,
promote, merge, release, deploy, or write an external system.

v0.16.2, published through Issue #161 / PR #162, refreshed independent runtime
adapters. v0.16.3, published through Issue #163 / PR #164, prepared historical
wrapper retirement. v0.17.0, published through Issue #165 / PR #166, added
context continuity; its [paired-run evidence](docs/loops/issue-165/paired-run-evidence.md)
has explicit generalization limits. v0.17.1
published the documentation-coherence patch through Issue #167 / PR #168.
v0.18.0 published the Desktop Runtime Wrapper V1 retirement through Issue #174 / PR #173
at `3b789e2f9749f2643b6fe75397d22f6e21a71ce2`, with annotated `v0.18.0`
tag and non-draft, non-prerelease GitHub Release binding that commit.
Issue #175 / PR #176 published the post-release state-coherence patch at
`b5cb03ae467222215f42c3081cad796ad3a2ecf3`, with annotated `v0.18.1` and
corresponding GitHub Release. The v0.18.2 record preserves the later CLI/MCP
boundary and checks-only CI mode. This repository has no deployment target or publish/deploy workflow;
deployment is not applicable. GitHub Release publication is not deployment evidence.
The retired wrapper is non-executable context, never a runnable integration path.

原生 sidebar preferences／目前任務 worktree 操作仍依各自 reference；不同日期的
runtime evidence 各有界線。Native sidebar preferences and current-task worktree
actions retain their separate references; dated evidence does not qualify another surface.

- [Sidebar preferences](skills/desktop-sidebar-organization/references/preferences.md)
- [Current-task worktree](skills/desktop-project-delivery/references/current-worktree.md)
- Runtime evidence: [2026-10-14](docs/codex-runtime-compatibility-evidence-2026-10-14.md), [2026-09-29](docs/codex-runtime-compatibility-evidence-2026-09-29.md), [2026-09-25](docs/codex-runtime-compatibility-evidence-2026-09-25.md), [2026-09-24](docs/codex-runtime-compatibility-evidence-2026-09-24.md), [2026-09-19](docs/codex-runtime-compatibility-evidence-2026-09-19.md), [2026-09-17](docs/codex-runtime-compatibility-evidence-2026-09-17.md), [2026-09-16](docs/codex-runtime-compatibility-evidence-2026-09-16.md)
- [v0.15.0 historical record](docs/release-notes-v0.15.0.md), [V1 retirement](docs/desktop-runtime-wrapper-v1-deprecation.md)
- [完整內容與舊章節對照 / Complete content crosswalk](docs/guides/workflow-reference.md#content-crosswalk)

</details>
