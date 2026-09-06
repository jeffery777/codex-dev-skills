# Issue #225：G0 契約與合成驗證計畫

## 目標與基準

承接 [#213](https://github.com/jeffery777/codex-dev-skills/issues/213)，交付
MG1 G0 可審查格式及純離線 conformance checker；G1／G2 仍未實作。
[#225](https://github.com/jeffery777/codex-dev-skills/issues/225) 建立後才建立
`codex/225-memory-governance-g0` 隔離 worktree，基準為
`4524e2b4c7076c2c8afdbaaeab1cfd01379665e5`。
設計依據為 #212／PR #214 的 `e0ffeb4a271961b9b11a279713885f9985da2534`，
以及目前的 `AGENTS.md`、`docs/memory-governance-milestone.md`、M0／M1／V2b 契約。

## 工作包與所有權

1. 主 agent：新增 G0 規格、離線 checker、合成案例、測試及 repo validation 接入。
2. 唯讀 reviewer：獨立追溯 #222 的來源註記；主 agent 核對後記錄分析並修正已證實的私有 helper 註記。
3. 主 agent：合成與相容性驗證、文件同步、版本影響評估。
4. 獨立 reviewer：檢查資料／授權邊界、文件與實作一致性；主 agent 處置 finding。

主 agent 擁有 checker／fixtures／文件；測試 worker 僅擁有新增 unit-test module，
reviewer 唯讀。#188／PR #189 保持原有留存用途。

## 允許檔案

- `docs/memory-governance-g0-contract.md`
- `scripts/memory_governance_g0.py`
- `scripts/validate-memory-governance-g0.py`
- `tests/fixtures/memory-governance-g0/`
- `tests/test_memory_governance_g0.py`
- `scripts/validate-repo.sh` 及其必要的既有 test shard manifest
- `tests/test_validate_repo.py`：新增嵌入測試組後同步既有組數斷言。
- `scripts/eval-memory-pilot.py`：#222 來源分析證實的私有 helper tuple 註記最小修正。
- `docs/roadmap.md`
- `docs/loops/issue-225/`、`docs/loops/issue-222/source-analysis.md`

不改可安裝技能、M0／M1／V2b 資料格式、資料庫、私人設定或歷史收據。
新增 test module 依完整分割要求加入 `tests/test-shards.yaml`。

## 格式與選擇

- G0 獨立版本只描述合成案例；caller context 與 case 分開輸入。
- scope 使用 principal/root/item/identity_epoch 不透明身分；不把它當檔案路徑。
- 預覽綁定精確操作、revision、內容／線索、完整清除集合及確認窗口。
- 必填 profile 給定有限數量、byte、時間與維護預留；fixture 的值只供測試，
  不作產品預設，生產 profile 及 G0 契約接受仍待 maintainer 決定。
- 停止使用、內容清除、殘留處理與空間回收分開；不能由資料宣稱已授權或 runtime 成功。
- 無原文 proof 有界保留；裁剪先持久提高拒絕下限，未知時間／commit 不確定均拒絕成功聲明。
- 一般寫入保留 byte／proof 清理空間；marker 可到期回收，但舊 identity 受 epoch/floor 拒絕。
- 舊版依 retired_at 盤點並明確裁剪；pending proof 保留要求階段，只能經新確認繼續剩餘處理。
- audit 綁定固定 snapshot 並揭露部分涵蓋原因；上述全是合成狀態轉換，非真實執行。

## 驗證與審查

使用 tracked resolver 先核對 Python 3.12.9／PyYAML；所有 Python 驗證沿用它。

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest tests.test_memory_governance_g0
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_memory_contract tests.test_memory_operation tests.test_memory_qualification \
  tests.test_memory_sqlite tests.test_memory_pilot
PYTHONDONTWRITEBYTECODE=1 ./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/validate-release-state.py
./scripts/project-python scripts/sync-plugin-package.py
git diff --check
```

新增測試加入 repo shard 完整分割；必要時執行完整 discovery，以實際結果記錄完成範圍。
程式／文件使用 `code-review-deep`，安全邊界使用 Security Diff Scan。
實作驗證不替代 PR 的 exact-head Merge Review 或 GitHub enforcement。
使用者後續已授權通過正式 review／Security Diff Scan 後 commit、push、建立 PR，
完成 merge review 且無 findings 時合併；依各階段的精確 revision 執行 formal gate。

## 復原與剩餘決定

新增 checker 沒有狀態寫入能力；本機 patch 可逐檔檢查與撤回，沒有 runtime migration。
G0 接受與生產參數選擇是後續 G1 的條件。此交付不改 source/package 版本，
原因是 repository-only 設計／合成驗證尚未新增安裝能力；不回填歷史 release notes。
不由本機 catalog 一致性推論 GitHub tag／Release 發布狀態。
