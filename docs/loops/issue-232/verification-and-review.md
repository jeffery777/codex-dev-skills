# Issue #232：驗證與審查紀錄

## 範圍與證據身分

2026-09-08 的 pre-commit working-tree 審查，repository 為
`jeffery777/codex-dev-skills`，分支為
`codex/issue-232-capability-compatible-skills`，基準 HEAD 為
`914f8a5c596d698bcd0ab1c389ff66091ec07259`。

核心審查涵蓋 32 個 changed artifacts：共用契約、十個 skill 入口及其
generated copies、plugin supporting policy、allowlist、版本三處、安裝測試、
選用指南、roadmap、計畫、十二個語意案例與 release note。本文件是之後加入的
第 33 個報告文件；安全掃描 snapshot 不包含本文件。

核心輸入 inventory 是依 path 排序的 `{path, sha256}` 陣列，以
`json.dumps(..., indent=2) + "\n"` 序列化為 UTF-8；檔案 SHA-256：
`46e4811c31148c1636ba98ebe73ba20315e881203bbe0a816cabfcf36dd47225`。
主代理在掃描封存前逐一重算 32 個檔案，與審查輸入一致。

## 驗證結果

所有 Python 檢查使用 `./scripts/project-python` 選取的 Python 3.12.9；
已先確認 PyYAML 6.0.3 可匯入。

| 檢查 | 結果與範圍 |
| --- | --- |
| `./scripts/validate-repo.sh --skip-unit-tests` | Exit 0；repository 離線驗證通過。內嵌 unit-test groups 明確略過，由完整 shards 執行 |
| `./scripts/project-python scripts/test-shards.py run-all` | Exit 0；12 個 shards、1,033 個 tests 全數通過 |
| 四組 focused unit modules | 35 tests 通過：release-state、review disposition、roadmap、plugin packaging；與完整 shards 有重疊，不另加到總數 |
| `./scripts/project-python scripts/sync-plugin-package.py` | 114 個 generated package files parity 通過 |
| `./scripts/project-python scripts/validate-release-state.py` | Source/package `0.24.1` 與 candidate 結構通過 |
| `git diff --check` | 通過 |

新增測試驗證十個 source/plugin 入口能解析相同契約 bytes，以及 delivery group
在預設／自訂 templates root 安裝後的契約可達性。自訂位置需在使用時保留
相同 `CODEX_TEMPLATES_DIR`；沒有宣稱新增測試已逐項涵蓋 legacy target、
review group 的所有 filesystem consumers 或 runtime discovery。

## 審查與 Gate

- Review Mode：獨立 `code-review-deep` 與 `docs-review`，再由主代理核對結果、
  diff identity、驗證與限制，整合為 pre-commit code/docs gate。
- 路由採已驗證可用的 baseline `loop_v2a_deep_reviewer`；沒有匹配的 Desktop
  candidate qualification，未以模型可用性作為品質資格證明。
- Findings：MUST-FIX 0、SHOULD-FIX 0、NIT 0。
- Finding Dispositions：空集合，沒有待處置或被省略的 finding。
- Gate Result：PASS（pre-commit content scope）。
- Required Follow-up：PR 存在後，依當時完整 base-to-head diff 執行 exact-head
  Merge Review，另核對 repository 選定的 GitHub CI、receipt、App 與 threads。
  本紀錄不提供 merge readiness 或外部寫入授權。

十二個[選用案例](selection-cases.md)經語意審查，均保留指定方法、必要工具、
資格、權限與 gate。這是契約一致性證據，不是模型行為 benchmark。

## Security Diff Scan

- Scan ID：`12db3989-6e70-43d0-99fe-eb1e350bd26f`。
- Snapshot：`codex-security-snapshot/v1:sha256:72ae8269146ce4c5f8c6abf95c2fdf5761ba885d6601190786d7dd6180662b8e`。
- 狀態：completed；32 個 changed artifacts、六個安全面向，reportable findings 0。
- 工具 source inventory 的四個檔案之外，依 `SECURITY.md` 納入其餘指引、
  測試與 generated artifacts；沒有將 repository 全部檔案數當成已審查數量。
- 已檢查契約／方法替換、資格／gate／adapter、Memory M1/MG1、套件 allowlist、
  安裝位置與版本／文件主張。沒有候選漏洞，因此不需要逐候選 validation 或
  attack-path 分析；封存成功後由工具產生 canonical report。
- 限制：bounded diff scan，非全 repository audit；不測量模型遵循、品質或成本，
  不讀寫真實記憶、不驗證 hosted enforcement 或發布狀態。新增報告文件另做
  文件與敏感資料檢查，不能回溯宣稱包含在既有 snapshot。

## 版本角色與後續順序

| 角色 | 此次判定 |
| --- | --- |
| Source/package version | Catalog、installer、plugin manifest 一致為 `0.24.1` |
| Candidate preparation | 值得 patch release：修正既有選用歧義，必要契約與 public schema 不變；release note 留在 #232 |
| Publication truth | 2026-09-08 的唯讀 provider 查核：`v0.24.0` annotated tag 指向 `4524e2b4c7076c2c8afdbaaeab1cfd01379665e5`，對應非 draft／非 prerelease Release；`v0.24.1` tag 與 Release 尚不存在。這是點時證據，發布前須重查 |
| Active guidance | 選用指南與 roadmap 指向共同契約；先交付 #232，再完成 #231 設計，之後 G1 → G2 → G3 |
| Historical records | 既有 release notes 不修改；本次不宣稱 memory runtime 已完成 |

部署前的唯讀 `install.sh status`／`diff --all` 顯示預計 11 個內容差異：十個
技能入口及共用契約。每個目前安裝檔的 SHA-256 都與基準 source bytes 相同，
未發現這 11 個檔案有使用者自訂內容。實際更新仍需依當時有效授權，備份後
執行並讀回；此紀錄不是安裝完成證明。

## 可重跑指令

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/test-shards.py run-all
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python scripts/validate-release-state.py
git diff --check
```
