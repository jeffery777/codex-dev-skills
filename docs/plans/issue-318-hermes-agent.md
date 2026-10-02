# Issue #318 Hermes Agent 交付計畫

## Objective

依 [需求](../requirements/hermes-agent.md) 與 [設計](../design/hermes-agent.md)
完成 Hermes 基礎支援，保留尚缺真實模型／runtime 資格，避免整套相容宣告。

## Source Of Truth

- `origin/main` 起始 revision：`73fd1a3072f43496403986511f1f490f75cfc4ec`。
- [Issue #318](https://github.com/jeffery777/codex-dev-skills/issues/318)。
- Hermes 公開 upstream revision `0a374d167424cdc730ce9761368b62255b551e58`。
- 當次本機公開版本 revision `5bba024d8ddd388f56f354c1f789be825e3d8a3c`。
- source/package version 依 `catalog.yaml`；平台、runtime 與模型狀態另讀回。

## Task Slices / Ownership

單一整合 writer；有界唯讀能力調查與獨立深入 reviewer 分離。
先遠端讀回 Issue-ID 分支，再寫 requirement/design，實作獨立 allowlist
installer、三個薄 adapters、focused negative tests，最後 runtime 驗證及 gate。
`#316` 僅從平台讀取正式範圍；本項不修改其 source interfaces 或 roadmap 分支。

## Verification

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python -m unittest tests.test_hermes_package
./scripts/project-python scripts/verify-hermes-runtime.py --help
./install-hermes.sh plan --skills-dir /absolute/isolated/skills
./install-hermes.sh install --skills-dir /absolute/isolated/skills
./install-hermes.sh diff --skills-dir /absolute/isolated/skills
./scripts/project-python scripts/test-shards.py validate
./scripts/project-python scripts/test-shards.py run-all
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python scripts/validate-release-state.py
./scripts/validate-repo.sh --skip-unit-tests
git diff --check
```

原生技能驗收在獨立臨時 `HERMES_HOME`，使用 Hermes 自己的 Python/runtime、
原生 `skills_list`／`skill_view`，不載入私人 config/auth、不發送模型請求。
此測試證明原生載入與依賴，不能證明真實模型、工具執行或獨立 reviewer 品質。
真實模型測試先完成使用者選定的獨立 subscription 登入，禁用自動借用
external login、API fallback 與 auxiliary 付費路由，再跑合成小型工程 fixture。
來源查讀、help、驗收、review／scan 原始輸出都留 `.work/review/issue-318/`
或 Git 外隔離目錄；先核對完整 bytes／revision 再重用。

## Review Plan

Installer／跨 runtime 契約用獨立 `code-review-deep`（適當 Astra baseline）、
必要 Security Diff Scan；commit／PR 用 `code-review-gate`。PR 後完整
base-to-head exact-head Merge Review、hosted CI、strict receipt／App／ruleset。
changed head 重新完整審查；單一邊界小修正先重驗與重審受影響範圍。

## Recovery / Historical Evidence

安裝拒絕覆蓋，失敗保留標記與新建 namespace；清理需精確 preview 和另行授權。
測試／inventory／digests 可重建；當次 UTC 時間、執行身分、平台 check／scan ID
及既有 runtime 版本是歷史證據，不能由重跑產生原事件的證明。
main 先合併 #316 時，在本 worktree 同步，保留雙方 roadmap 項目，重評
版本、狀態、依賴與完成宣告；無文字衝突仍做語意檢查。

## Release And Name Assessment

新增可安裝 runtime adapter 適合未來 additive minor；本輪先保持 source/package
版本；同步 main 後重查 #316 是否已有版本變更，避免衝突。基礎實作、runtime 驗收與
release readiness 分開記錄；缺真實驗收時不能宣稱完整 Hermes release ready。
正式發版候選於 main 整合及驗收後同案重評，不改歷史 release notes。
tag／Release、部署／清理未授權。

名稱 `codex-dev-skills` 對 Hermes 使用者辨識有限，但既有 package／plugin／
安裝與連結相容性優先。本輪不改 identifiers。後續可另開 Issue 評估中立名稱，
遷移範圍包括 repository redirects、catalog/plugin IDs、namespace、installer
state、update／backup ownership、文件連結與 alias 相容期；不是 H-01–H-07 的 DoD。

## Open Acceptance

使用者已確認並授權沿用 Hermes 自己的 OpenAI subscription OAuth；真實模型
已完成技能／工具 roundtrip、小型工程實作與 tests、exact session 接續及
checkpoint 讀回。公司環境不是必需；原始證據保留 Git 外。正式 delivery gate
依獨立深入 review、必要 scan 及 PR exact-head／平台證據判定。native reviewer
角色品質、OS sandbox、delegate isolation、自動 lifecycle 與其他 surfaces
仍未取得資格；有限基礎支援不得宣告整套相容。

## Reproducible Acceptance Packet

離線結果由上列命令重建。真實模型測試的原始 driver、query、stream-json、
stderr、fixture、native loader 輸出及 independent verification 保留於
Git 外 review root；檢查其 bytes、環境與來源再重跑，不提交私人 profile。

可在新獨立 playground 重建這個 fixture：`normalize_port(value)` 只接受
字串，strip 後必須全為 ASCII digits，轉成 1..65535 的 int，其他一律
ValueError。valid inputs 為 `1`、`65535`、` 80 `、`00080`；invalid 為
空字串、`0`、`65536`、`80.0`、`+80`、`-1`、`８０`、`a`、None、True、80。
先建立固定 tests 與未實作函式，要求模型 planning、實作、terminal 執行
pinned Python unittest；禁止改 tests、config/auth、network 或平台。
主代理獨立重跑 tests 並比較受保護 tests bytes。

接續測試先建立隨機非機密 sentinel 與 checkpoint，以該次 exact session ID
resume，核對 sentinel、cwd、owned paths 與未完成的獨立 review。Gate 負向
測試提供 tests 通過、但缺獨立 review／scan／PR／hosted checks 的 nongit
fixture，載入 Hermes review／continuation adapters 與專用 next-session
template，要求回報 BLOCKED 及缺件；不能把模型回答當平台或 OS enforcement。

raw timestamps、session identity、OAuth 執行身分與平台 scan/check IDs 是
不可重建的歷史事件；重跑只產生新事件。受控 fixture 不是公司環境驗收，
也不是 native delegation、sandbox 或完整任務 lifecycle 的資格。
