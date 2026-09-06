# Issue #225：驗證與審查紀錄

## 範圍與版本

[#225](https://github.com/jeffery777/codex-dev-skills/issues/225) 建立後，才建立
`codex/225-memory-governance-g0` 隔離 worktree。基準為
`4524e2b4c7076c2c8afdbaaeab1cfd01379665e5`。本紀錄固定於 commit 前的實作驗證階段；
下列測試與審查結果本身不表示 commit、push、PR、merge、Issue 關閉或發行完成。

交付包括 G0 合成契約、checker／CLI、固定案例、獨立 unit tests、repo validation
與 shard 接入、既有驗證器測試組數同步，以及 #222 私有 evaluator tuple 註記的來源分析與一行修正。
#213 保留整體里程碑接受用途；#188／PR #189 的既有留存用途未更動。
具體格式與限制見 [G0 契約](../../memory-governance-g0-contract.md)，
#222 的事實與推論見 [來源分析](../issue-222/source-analysis.md)。

repository-only checker 沒有安裝入口、backend、網路或持久化；不修改 M0／M1／V2b
格式／資料庫／authority chain。source/package 版本仍為 catalog 的 0.24.0。
這不是 GitHub tag／Release publication 證據，也不改寫歷史 release notes。

## 驗證

所有 Python 指令使用 tracked `scripts/project-python`，已選定 Python 3.12.9、
PyYAML 6.0.3；未安裝或切換其他 Python 環境。

| 檢查 | 實際結果 |
| --- | --- |
| 初版焦點回歸 | 88 tests 通過；後續 schema 修正後不沿用其 G0 結論。 |
| 修正後 M0／M1 相容性與 evaluator 回歸 | 78 tests 通過。 |
| source/package parity | 113 generated files 通過。 |
| offline release state | source/package 0.24.0 結構通過。 |
| shard 完整分割 | 12 shards、67 modules 通過，初版 lexical sorting 已修正。 |
| 新固定案例 | 11 組 case，包含 off、audit partial、history／marker 裁剪、pending／complete continuation。 |
| 最終 G0 焦點 | 22 tests 通過，包含三輪固定上限循環與各種拒絕情境。 |
| 全庫結構驗證 | `validate-repo.sh --skip-unit-tests` 通過；11 fixtures 仍有執行。 |
| 完整 discovery | 執行 968 tests；950 個未受影響測試通過，其餘兩模組經下述凍結版重跑。 |
| 凍結版受影響模組 | G0 與 validator 共 24 tests 通過。 |
| 最終完整測試 inventory | 974 個不重複 test IDs = 950 個未受影響 + 24 個重跑；不是一次全綠的 discovery 宣稱。 |
| Diff／新檔 whitespace | tracked diff 與所有新檔均通過。 |

## 審查與處置

第一輪獨立 deep review 找到五項 MUST-FIX：shard 排序、滿額時清理被封鎖、
marker 無回收模型、缺少明確歷史裁剪，以及 pending proof 無法保留待處理的回收要求。
另指出 partial audit 缺少涵蓋證據、核心拒絕情境測試不足。

修正引入 growth／cleanup 的 byte 與 proof 預留差異、identity_epoch／marker_seconds、
retired_at 與 prune-history、proof.reclaim_space 與有新確認的 continuation，
以及 audit snapshot／reason／count。新增反例與循環測試由獨立 test worker 維護。
第二輪另找出 continuation 確認早於原 proof、retention／continuation 未綁 profile、
retention 未檢查外部工作空間，以及 unmanaged copy 重複值。以上均修正並加入反例；
retention 更以確認時刻判定到期資格，避免先確認未到期集合後等待生效。
獨立 deep review 已核對最新程式、契約、fixtures 與 22 個 G0 測試，結論 PASS，
沒有剩餘可行動 finding。

初版 Security Diff Scan 已完整檢視四個變更 source files 及必要 supporting consumers，
未形成可成立的安全漏洞候選；這不消除上述一般契約缺陷，也不覆蓋修正後 snapshot。
修正後已重新執行完整四檔 Security Diff Scan，結論為 0 個已確認安全問題、
4/4 source surfaces 完成，沒有未驗證候選或未覆蓋的變更 source file。
新的獨立架構 review 與主 agent 檢視共同確認無 backend/authority consumer。
安全掃描完成後只補上 argparse 診斷範圍的文件說明、此驗證紀錄，以及既有 test
組數的 17→18 斷言；執行程式沒有再變動，這些收尾差異另作唯讀核對。

原生工具記錄本次修正後安全掃描用量為 4,510,090 tokens，其中 4,374,272 為
cached input；這是兩個 task 的工具聚合紀錄，不是新增輸出量或費用換算。

完整 discovery 啟動時載入的是較早 G0 module；修正期間 fixture 改為新格式，
造成同一 golden-case test 的四個 subtest 出現 invalid-fields／unaccepted-continuation。
另發現 `tests/test_validate_repo.py` 的組數斷言仍為 17，新增 G0 後實際為 18。
已同步斷言並凍結程式／fixtures，重新執行完整 G0＋validator 兩模組，24 tests 全數通過。
其餘 950 個 test IDs 與程式、政策、環境及支援依賴未受收尾修正影響，沿用該完整
run 的通過證據；未重跑耗時的無關 installer 測試，也未隱去初次 run 的錯誤。

驗證的核心 SHA-256：

| 檔案 | SHA-256 |
| --- | --- |
| `scripts/memory_governance_g0.py` | `953566d39390beff825424361d32d3223be85b4a94dc486ad8f4a83cebf3b805` |
| `tests/test_memory_governance_g0.py` | `3183df651223af92183c8a08199c7717a45c7fc6836fb864940ab0c638780591` |
| `scripts/validate-memory-governance-g0.py` | `c3055d3c17a2f82b0f7d2323b482bcdb979151559c583a69361951f8f7f283a4` |

## 可重跑指令與接受界線

```bash
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest tests.test_memory_governance_g0 tests.test_validate_repo
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_memory_contract tests.test_memory_operation tests.test_memory_qualification \
  tests.test_memory_sqlite tests.test_memory_pilot tests.test_sqlitectl tests.test_eval_memory_sqlite
PYTHONDONTWRITEBYTECODE=1 ./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/test-shards.py --manifest tests/test-shards.yaml validate
# 完整 discovery；本次採上述完整 run 加受影響模組重跑的證據組合。
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest discover -s tests
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python scripts/validate-release-state.py
git diff --check
```

G0 conformance 不提供真實授權、寫入、清除或 runtime 證明。
生產 profile、可信 authority/readback、真實清除與空間量測、crash ordering 及 G1／G2
仍待獨立實作與資格驗證；POSIX path protection 不代表 Windows 等價支援。
G0 契約接受仍是進入 G1 的條件。此份 pre-commit 紀錄不含後續 exact-head Merge Review
或 GitHub enforcement；後續 gate 見 [正式 code review gate](code-review-gate.md)，
PR 上的 exact-head receipt 才記錄當次平台讀回與 merge review，本紀錄不替代它。
