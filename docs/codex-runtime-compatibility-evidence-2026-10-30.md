# Codex runtime compatibility evidence — 2026-10-30

Issue [#359](https://github.com/jeffery777/codex-dev-skills/issues/359).
Baseline `863db227dea38a828280d33bc6e40e5fd708226d`; branch
`codex/issue-359-runtime-compat-0166` was created and read back on GitHub before
local checkout selection and tracked edits. This is bounded interface evidence.

## 繁體中文

### 範圍與來源

本輪先唯讀核對 checkout／remote main／HEAD／未提交修改、工作樹及公開任務狀態。
主 checkout clean，未見同範圍活動 writer；程序／cwd、Git lock 與可見任務是
點時觀測，不能證明所有外部程式永久不會寫入。舊工作樹與 draft PR 保留。
唯讀參考本機 memory summary 的相關歷史，不修改或匯入記憶。

官方依據：[CLI commands](https://learn.chatgpt.com/docs/developer-commands)、
[non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)、
[worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees)、
[skills](https://learn.chatgpt.com/docs/build-skills)、
[configuration](https://learn.chatgpt.com/docs/config-file/config-advanced)。
官方 worktree 說明提供產品背景；下述精確 tool 欄位及限制以當輪完整公開
`codex_app` callable schema 為證據，不從文件背景推導未暴露參數。

| 入口／層 | 2026-10-30 直接證據 | 覆蓋與限制 |
| --- | --- | --- |
| Standalone CLI | `codex-cli 0.166.0`；SHA-256 `39acf979729dd290f9a24ee38b2914e036c91b65952872e28ae2a6b88a7db7c1` | 3 public-help tests PASS：exec／resume／fork、production argv、plugin list JSON。 |
| Desktop app | bundle ID `com.openai.codex`；`26.1027.30824`，build `22943` | 已安裝 bundle metadata；不假設產品仍位於舊 app basename。 |
| Bundled CLI | `codex-cli 0.166.0-alpha.5.1`；SHA-256 `58a91f6ea19bea477ae3a2ec48d619f0039afe75d3476260747e11d201fa7cea` | 另一 executable 的同 3 tests PASS；不能替代 Desktop native 驗收。 |
| Desktop native | 完整 create／attach／fork／create-thread schemas；`list_threads` schemaVersion 4 | 唯讀 registry 與 schema；未 create／attach／restore／fork／send 或 cloud dispatch。 |
| 共享 Core | v0.1.1，`7b66978a76597d09be1b55ad199a969b4ee59c0f` | 固定 14 檔離線 validator verified；共享完成／授權／review 契約不變。 |

兩個 CLI 測試各自使用 disposable config，將 production argv 的 prompt 換為
`--help`，並檢查沒有 session／JSONL 產物。Root help 與官方文件仍支持 executor
使用的 sandbox／approval／ignore-user-config／JSON 邊界。新版提供 managed
`--worktree`，但它與 `--ignore-user-config` 不相容；現有 executor 不使用該旗標，
保留既有 private clone，不為新增供應商功能改變其隔離或授權契約。
官方 skill discovery 仍含 `~/.agents/skills`；具名 CLI profile 採獨立 config file，
本次 adapter 不使用 `--profile`，也不修改使用者設定或既有角色 mapping。

### Findings 與集中修正

- **D359-01 — Fixed in candidate:** `create_worktree` 必填 `ref` 與 `allowAsync`；
  新 checkout detached。補 `sourceRoot` 的使用者選定／workspace 範圍、當輪
  明確使用回傳目錄與後續回合 cwd 更新；不把建立成功當作寫入權限。
- **D359-02 — Fixed in candidate:** 已建立但 attachment／cwd update 失敗時，
  使用 `attach_worktree(path)` 而非重建；保留 ownerless／unrelated-chat 限制、
  archived restore 分流與未知效果先讀回。
- **D359-03 — Fixed in candidate:** fork 依 backing kind 核對；ChatGPT-backed
  cloud Work 必須指定 Codex threadId，不能 fork ChatGPT conversation，即使
  executor 在本機。Fresh create 需已授權新任務與 history-loss 意圖。
- 同步兩份 active runtime contracts 的 `codexCloud` union：先列可用環境，
  選 runnable `environmentConfigId`，明確 cloud 授權；只補 schema，未取得 live 資格。

必要修正集中在既有 Desktop references、native contract、V2 boundary、測試與
generated mirrors。CLI executor、shared policies／Core、模型／effort、installer
執行邏輯、GitNexus、Memory、Hooks、Schedulers 及使用者實裝不改。
#242／#251／#293 不因 help 或 schema 成功而關閉。

### 驗證、風險與交付界線

首輪 native docs tests：48 PASS。版本先同步而新 note 尚未建立時，release-state
曾 FAIL（缺 `docs/releases/v0.35.2-split.md`）；本候選新增該 note，後續重驗另讀回。
CLI 兩組各 3 PASS 是 parser 證據；live lifecycle／模型／拒絕／取消／cloud 為
**NOT_RUN**。文件與 synthetic checks 不證明 live runtime 資格。

獨立深入設計／威脅審查提出上述三項 MUST-FIX；實作需獨立 diff 複審及比例
Security Diff Scan。此差異影響來源選取、cwd、ownership 與未知效果，不以
Markdown 身分免掃。當次 PATH 查無 semgrep、bandit、pip-audit、osv-scanner、
trivy；這些工具未執行，不能記 PASS。沒有新增依賴或可執行資料流，不自行
新增 SAST／SCA 義務；必要 SDS 的實際 preflight／coverage／阻礙由交付報告列明。
不安裝替代工具或更改全域設定以取得綠燈。

建議 patch `0.35.2`：修正既有薄 adapter 與公開供應商契約的偏差，沒有新增
技能、executor 或共享功能；不以中文「小版本」推定 minor。Catalog／installer／
plugin 與雙語 note 同版；完整 payload 須先固定 commit S，再以 data-only
mapping commit T 保留所有歷史來源並追加新 catalog digest。Mapping／隔離
安裝結果與 exact HEAD CI 另以實際輸出核對，候選紀錄不自行宣告發行。

英文依 ASD-STE100 原則編寫，尚未完成完整符合性驗證；繁中採簡明原則，
不宣稱符合該英文標準。沒有 live runtime mutation、安裝、全域權限／認證
變更或無關索引，不重啟 Reason Network、Agensi 或本地模型整合。

## English

Issue #359 starts from the clean baseline above. The Issue and remote branch
were created and read back before tracked edits. Visible task, process/cwd and
Git-lock observations found no competing writer for the checkout at that time;
they do not guarantee permanent exclusion of external writers. Old worktrees,
drafts and unresolved investigations remain. Local memory was advisory only.

Standalone 0.166.0 and bundled 0.166.0-alpha.5.1 each passed three public-help
checks with disposable configuration and no session/JSONL creation. They check
exec/resume/fork, production argv and plugin JSON. Desktop bundle metadata is
26.1027.30824/build 22943. Native tool schemas and the schema-version-4 registry
were checked separately. Fixed Core v0.1.1 passed fourteen-file verification.
None of these checks establishes live lifecycle, model, cancellation, denial,
or cloud qualification. Those live operations are NOT_RUN.

Correct the existing Desktop adapter: require explicit ref/allowAsync, detached
source selection and bounded sourceRoot; use the returned directory now and
respect later-turn cwd updates without granting permissions. Recover a known
created checkout through attach_worktree, preserving ownerless/unrelated-owner
limits and archived restore. Read back unknown outcomes before retrying.
Fork only supported Codex/local Work backing kinds; cloud Work needs an explicit
Codex source ID. A local executor does not make a ChatGPT conversation forkable.
Fresh creation requires authorized new-task/history-loss intent. Document the
codexCloud/environmentConfigId schema and explicit cloud gate without live claims.

The current-worktree and create/fork references, active native/V2 contracts,
focused tests and package mirrors form one maintenance slice. CLI executor,
shared Core/policies, model routing and installer logic stay unchanged. The CLI
managed-worktree flag conflicts with ignore-user-config, so the existing private
clone remains. Skills discovery and CLI profile documentation do not require an
adapter change. No installation or user configuration is changed.

Initial native-document checks passed 48 tests. Release-state initially failed
because the newly selected 0.35.2 note did not yet exist; this candidate adds it.
Final checks and CI must be read back separately. Independent deep design review
identified D359-01/02/03; their candidate fixes require independent diff review.
Proportional Security Diff Scan is required for source, cwd, ownership and retry
guidance. Semgrep, Bandit, pip-audit, osv-scanner and Trivy were absent from PATH;
they are NOT_RUN, not passed. No executable flow or dependency changed; no additional SAST/SCA requirement was
identified for this scope. Required SDS evidence remains blocking.

Recommend patch 0.35.2 for existing-adapter corrections, with aligned metadata,
bilingual changelog/note and immutable payload S/data-mapping T. No new skill,
executor or shared feature justifies a minor bump. Publication, merge, approval,
tag/Release and actual installation remain separate, unauthorized actions.
Keep #242/#251/#293 unresolved. Do not restart paused integrations. English follows
ASD-STE100 principles; full conformance is unverified.
