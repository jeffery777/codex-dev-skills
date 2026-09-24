# Contributing

Thanks for helping keep these Codex development workflows useful and public.

本文件只規範 `jeffery777/codex-dev-skills` repository 的開發與維護。
它不屬於安裝 catalog 或 universal plugin，不向使用本套技能的其他專案施加
GitHub、Issue 或分支命名要求。其他專案依自己的 repository 規範與 provider
（例如 GitLab）執行；共享技能仍保留 provider-neutral 的品質與授權契約。

## 實作前先建立 Issue 與遠端分支

適用於本 repository 的程式、技能、文件與測試變更：

1. 先唯讀確認目標、授權、Git status、branch、upstream、remotes、diff，
   以及最新遠端 base。查找可沿用的同範圍 Issue，避免重複開案。
2. 在 GitHub 建立或確認該 Issue，讀回 repository、Issue ID、狀態、範圍與
   驗收條件。只有需求草稿或預計使用的號碼不算完成。
3. 用真實 Issue ID 在 GitHub 建立 `codex/issue-<ID>-<topic>` 分支，從已核對的
   base SHA 起始，再讀回遠端 ref 與 SHA。平台操作依
   [GitHub control-plane policy](policies/github-control-plane-policy.md)；
   可用的 connector 優先。若既有分支已符合目標與來源，就讀回沿用，不覆寫 ref。
4. 取得該遠端分支後，準備本機 checkout／worktree，核對 exact branch、HEAD、
   upstream、乾淨度／既有修改與 ownership。**Issue 讀回、遠端分支讀回及本機
   身分核對都完成後，才能開始 tracked edits。** 本機分支存在、push 計畫或
   Desktop queued task 都不能替代遠端分支與 ready checkout 的證據。

已在相同 Issue／分支工作時，重新核對當前目標、範圍與來源即可，不重複建立。
純查讀、需求整理與診斷可在分支前進行；若轉為修改，先完成上述順序。
此流程不自行授權外部寫入；缺少建立 Issue／遠端分支的授權時，完成唯讀準備
後停在該寫入邊界。Commit、push、PR、merge、release、install、deploy 仍各自
核對授權及適用 gates；不得因已建立分支就推定全部獲准。

## GitNexus 索引新鮮度

GitHub 合併、本機 checkout 更新、索引刷新是三個不同事件。遠端 merge 不會
自動拉取本機程式或重建本機索引，也不是執行這兩項操作的指令。索引新鮮度
以目標 checkout 的實際內容為準；本機因工作需要停留在較舊 commit，只要
索引與它一致，就不能僅因遠端已有新提交而判定索引過期。
安裝套件只提供未啟用的 hook 範本，預設
notify-only；可選的 Codex hook 使用 `SessionStart` 與部分 `PostToolUse`
訊號，沒有完整 post-merge 攔截保證。不能從已安裝技能推定 hook 已啟用。

在本 repository 使用 GitNexus 查詢、影響分析或索引證據前：

1. 核對實際 checkout 路徑、branch、HEAD 與 dirty state。以精確 repository
   路徑選索引，避免同名 clone／worktree 指向另一份索引。讀取公開 status／
   metadata 與 freshness；HEAD 相同但內容已修改，也不能當作索引仍然精確。
2. 發現索引相對於該 checkout 過期或缺失時，確認沒有其他 writer 正在修改
   這份 checkout，再就地安全刷新，之後才執行依賴索引的查詢。刷新不要求先
   pull、merge、rebase 或切換分支。先確認已安裝版本的 `analyze --help`
   支援 `--index-only`。
3. 刷新前保存受追蹤檔案、既有未提交修改、`AGENTS.md`、其他 AI context
   檔案與 Git 設定／排除檔的存在狀態及內容 digest，並保存 Git status／diff
   與檔案清單作為基線。保護集合與基線未備妥前，不執行刷新命令。
4. 驗證 repository 設定並執行刷新：

   ```bash
   ./scripts/project-python scripts/validate-gitnexus-config.py
   gitnexus analyze --index-only
   ```

   使用既有已核對的 executable，不為刷新而自動安裝或升級工具。不執行
   `clean`、不新增 embeddings、不改全域 hook／runtime 設定。索引及必要的
   本機 registry 是衍生資料，不提交到 repository。
5. 完成後比對步驟 3 的保護集合、Git status／diff 與新增檔案，
   必須確認 index-only 沒有注入或改寫這些檔案。
   發生非預期修改時保留證據並停止，不自動 restore／reset 覆蓋使用者內容。
6. 讀回索引的 checkout／HEAD 與新鮮度，執行一個有界查詢並對照實際來源。
   CLI exit 0、metadata HEAD 或非空搜尋結果，各自都不足以證明完整覆蓋。
   dirty checkout 的人工刷新只供當前探索，不能冒充 V2c controller 的
   `gitnexus-index-identity/v1` exact qualification 或 PR review 證據。
7. 同一 checkout／內容未變時重用這次證據；不每個查詢都重建。修改內容、切換
   分支或更新 HEAD 後，重新評估新鮮度。若缺工具／權限、索引損壞或保護條件
   不成立，明示缺口並採精確來源查讀 fallback，不使用過期圖譜宣稱已驗證。

遠端 merge 後只重新評估狀態，不直接同步本機或重建索引。是否同步是另一項
決策，須核對目標分支／upstream、工作進度與尚未完成的提交、checkout 的
owner／其他 writer、既有修改、使用者授權及適當的整合時機。Working tree
乾淨或可以 fast-forward，都不單獨證明現在適合／獲准同步。

若目前工作仍需原始 revision，保留 checkout，依它的內容維護索引；必要時
在已授權的獨立 worktree 檢查遠端版本，不改動正在使用的 checkout。
只有同步條件與授權均成立、且本機更新成功後，才針對更新後內容刷新並讀回
索引。尚未同步遠端時，分別回報本機 revision 與索引新鮮度，不能把刻意保留
本機 revision 說成索引維護失敗。這個流程不啟用自動 pull 或全域同步 hook。

直接人工刷新與可選的 qualified controller 是不同途徑；後者的 opt-in、
worktree 邊界、鎖、資格與 circuit breaker 仍依
[GitNexus runtime reference](skills/loop-engineering/references/gitnexus-runtime.md)。
本規範不啟用它。索引可縮小查讀範圍，但 token／耗時是否降低須量測，不作保證。

## 驗證與交付

使用 `scripts/project-python`，依 `AGENTS.md` 與當次風險完成必要測試、diff
檢查、獨立審查和 gate。修改可安裝來源時同步 generated plugin，保持 CLI／
Desktop 入口獨立及共享分層。PR 的 Issue linkage 依
[PR-to-Issue policy](policies/pull-request-issue-linkage-policy.md)；ready PR 的
closing reference 不取代實作前的 Issue／遠端分支順序，也不證明該順序曾發生。

將驗證、略過項目、findings disposition、索引維護與剩餘授權邊界如實交接。

## Historical Desktop Wrapper Retirement Boundary

Desktop Runtime Wrapper V1 is retired. Its helper scripts, focused tests,
machine-readable inventory, and legacy validator are no longer retained. Do not
reintroduce them as active consumers, runnable guidance, installer entries,
catalog entries, hooks, or plugin entrypoints. Current behavior is owned by the
[native capability contract](docs/native-runtime-capabilities.md); the
[retirement record](docs/desktop-runtime-wrapper-v1-deprecation.md) is
non-executable historical evidence only.

## Ground Rules

- Keep changes scoped to software development workflows.
- Mark runtime compatibility as `shared`, `cli`, `desktop`, or `plugin-dependent`.
- Prefer repository-owned policy files over runtime-local assumptions.
- Do not add credentials, private paths, local runtime files, logs, local databases, or machine-specific config.
- Do not add legacy provider-specific workflow references.
- Do not add unverified workflow packs as first-class public skills.

## Skill Changes

Every skill should include:

- frontmatter with a concise description
- a runtime compatibility line
- purpose and trigger guidance
- read-before-write expectations
- human gate and destructive action rules
- expected output
- verification or evidence expectations

## Review Expectations

Review changes as workflow contracts, not as prose only. Check whether a new rule can be followed by both Codex CLI and Codex Desktop, and whether runtime-specific behavior is clearly labeled.
