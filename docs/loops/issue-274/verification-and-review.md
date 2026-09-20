# 驗證與審查紀錄

本文件記錄 #274 的 pre-commit 證據；不代替 PR 建立後對完整 base-to-head
範圍的 exact-head Merge Review、當次 hosted CI 或 GitHub enforcement readback。
後三者以 PR 的精確版本審查與 strict JSON receipt 為準。

## 已完成的驗證

- 使用 tracked `scripts/project-python` 選定 Python 3.12.9；PyYAML 6.0.3。
- `tests.test_memory_audit`、`tests.test_memory_governance_core`、
  `tests.test_memory_governance_local`、`tests.test_governancectl` 共 71 項通過。
- `PATH="$PWD/.venv/bin:$PATH" ./scripts/validate-repo.sh --skip-unit-tests`
  通過 repository、catalog、schema、policy、eval 與 source/package parity 檢查。
- 新增 skill 通過 skill-creator 的 `quick_validate.py`；`git diff --check` 通過。

測試以隔離目錄中的真實 Git blob、SQLite snapshot、完整性驗證及分頁列舉
覆蓋正常／空庫／停用／來源失效／busy／I/O 失敗／timeout／權限撤銷／root 漂移。
來源接受、人類 authority 及環境 qualification 為 synthetic ports；沒有接觸
真實使用者 memory，也未執行 G2 maintenance 或實體清除實驗。

## 獨立審查與處置

混合 code、data、packaging、docs diff 使用獨立 `code-review-deep` 與文件審查。
第一次完整審查後，三項 MUST-FIX 經修正、相關測試及獨立比例複審確認關閉：

| Finding | 風險與修正 | 處置 |
| --- | --- | --- |
| CR274-01 | CLI JSON 的 ASCII escaping 可能超出 canonical 報告預算；改用相同 canonical UTF-8 encoder，測試實際 stdout bytes。 | Fixed |
| CR274-02 | 引述文字仍可保留 C1／Unicode 行分隔控制；統一轉義 Cc、Cf、Zl、Zp，新增顯示 regression。 | Fixed |
| CR274-03 | reader 的 temp_store 未實施已宣告的 memory 設定；連線設定 MEMORY 並讀回驗證，測試設定與唯讀性。 | Fixed |
| CR274-04 | adapter 評估的繁體字誤植；修正「後續」。 | Fixed |

Codex Security Diff Scan 完整覆蓋原始 diff，再對上述修正與受影響邊界比例複查；
兩次均已完成並讀回 sealed artifacts，沒有已驗證漏洞，也沒有 deferred candidate。
第二次掃描 ID：`3924fa16-7128-4386-9455-8c3bd1d920ba`。此 ID 只是本次紀錄，
不是其他版本、正式 host 或完整 MG1 的安全資格。

## 殘餘界線

Production registry 仍為空，預設 disabled；CLI enabled 保持 unavailable。
Timeout 為 cooperative deadline，無法中止任意 host code 或 blocking syscall；
可信 ports 需自行限制 I/O。容量、外部副本與完整 temp 峰值資格仍為 unknown。
合併、正式啟用、tag／Release 及使用者層級安裝未由本文件授權。
