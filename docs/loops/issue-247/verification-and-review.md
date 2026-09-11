# Issue #247：驗證與審查進度

此紀錄描述本次新建合成資料的開發驗證；不授權 production、發布或安裝。
本機測試、獨立審查與 Security Diff Scan 的證據分開記錄；PR 的完整 exact-head
Merge Review、hosted CI、strict receipt 與 App gate 另以該 PR 的當前平台讀回為準。
本文件本身不能證明 commit／PR／merge ready，也不授予合併權限。

## 基準與實作

基準 `2db0b29a5f20d6b7f342874f6a1d3d22cacbd288` 的 69 項 contract/core/faults/
local/local-faults 測試通過。修改後核心採 proof-v2 的固定 basis，詳見
[契約](process-loss-contract.md)。新版 reader 不接收原 preview、candidate、confirmation
或 handle；只讀 test-owned root 與固定 Git artifact，來源批准是獨立、非內容 descriptors。

焦點回歸 85 項通過，之後補驗 source Git 前進、完整 restore 序列及期限後新操作
共 3 項通過。當時新 test module 的 17 項納入全量 deterministic shards；完整結果
另列下方。實際 writer 在 before-transaction／after-item-write／before-commit／
after-commit 自行結束，另一個 reader 程序驗證 state-unknown 或 applied。
reply-loss 另在執行及讀回完成後丟棄回覆。以上僅涵蓋被測程序 checkpoint，
沒有 power-loss、SQLite 任意指令中斷或 journal recovery 的資格主張。

proof 最大寬度合成 encoding 為 1,324 bytes，低於 2,048；這是格式上界檢查，
不是 SQLite 實體容量或峰值測量。新增 metadata 仍佔原 proof 名額與保留期，
新 runtime/schema 指紋不沿用 #245 量測作資格。APFS 映像未操作，原 ENOSPC
incomplete 保持原判定；4 GiB worst-case lock time、完整 temp/J/T/G 仍未知。

## Changed files 與證據範圍

| 位置 | 變更 |
| --- | --- |
| `skills/loop-engineering/scripts/memory_governance_contract.py` | v2 basis／proof／readback 嚴格驗證，保留 v1 純契約。 |
| `skills/loop-engineering/scripts/memory_governance_core.py` | 原子保存 basis；新程序以 fresh ports 只讀判定。 |
| `skills/loop-engineering/scripts/memory_governance_storage.py` | 新建 synthetic root 家族／fingerprint、proof-v2 一致性及 host binding digest。 |
| `tests/test_memory_governance_process_readback.py`、`tests/fixtures/memory-governance/process_readback_worker.py` | 獨立 subprocess、正反案例與只讀檔案驗證。 |
| `tests/test_memory_governance_core.py`、`tests/test_memory_governance_local.py`、`tests/fixtures/memory-governance/synthetic_host.py`、`tests/test-shards.yaml` | 更新有 basis 時的期望、bulk seed 及全量測試分配。 |
| `skills/loop-engineering/references/memory-governance-v1.md`、`docs/roadmap.md`、`docs/memory-governance-milestone.md`、本 Issue 文件 | 新契約、相容性、保留成本與未完成資格。 |
| `plugin/codex-dev-skills/skills/loop-engineering/` 的三個 scripts 與 reference | 對應 source 的相同 bytes。 |

## 驗證指令

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_memory_governance_contract tests.test_memory_governance_core \
  tests.test_memory_governance_faults tests.test_memory_governance_local \
  tests.test_memory_governance_local_faults tests.test_memory_governance_process_readback
./scripts/project-python scripts/test-shards.py run-all
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python scripts/validate-release-state.py
git diff --check
```

離線 `validate-repo.sh --skip-unit-tests` 通過；package parity 122 個 generated files
通過；release-state structural checks 對 source/package 0.24.2 通過；diff hygiene 通過。
此離線 validation 的 embedded unit groups 明確 skipped，單元測試由獨立完整 shards
承擔，不能把 SKIP 當 PASS。2026-09-10 全量 12 個 shards 完成，合計 1,180 項
測試全數通過，run-all exit code 0；其中 memory shard 包含本次 17 項新測試。

| Deterministic shard | 通過項數 |
| --- | ---: |
| exact-head-merge | 78 |
| gitnexus | 138 |
| installer-agent-profiles | 60 |
| installer-runtime | 53 |
| loop-context | 100 |
| loop-control | 87 |
| memory-m0 | 67 |
| memory-m1-and-evaluation | 322 |
| native-runtime | 96 |
| operational-improvement | 87 |
| plugin-packaging | 16 |
| repository-policy | 76 |

全量 run 包含 source Git／restore／期限後新操作測試。2026-09-11 重新核對全量 run
當時候選的 19 檔內容及完整 patch hash 相符；原 temporary logs 已不存在，不能
稱為當日重跑。之後的 R1 修正與受影響範圍重新驗證另列下方，不把舊全量結果
宣稱為修正後的完整 run。以上均不替代 hosted CI、exact-head receipt 或 App gate。

## 獨立審查與 R1 修正

當次 router 回報 installed profile/name conflict。2026-09-11 使用者確認 model/effort
差異是刻意設定，本輪沿用現有 Astra/xhigh 唯讀 reviewer；developer instructions
與唯讀契約保持一致。不修改全域 profiles/router/config，不宣稱 canonical router
通過；後續用量與配置評估不併入此 Issue。

獨立 code/deep/docs review 發現 G1-247-R1：add A → stop B → resume C 時，state
digest 可回到 A 的後態，舊 A 被誤判 applied；再 stop D 也可復活舊 B。主代理及
reviewer 都以新 subprocess fixture 重現。修正以 snapshot 已驗明的連續 proof
sequence 判斷該 operation 是否為最新提交，不新增 schema／proof 欄位。

| Finding ID | Severity | Disposition | Owner | Evidence |
| --- | --- | --- | --- | --- |
| G1-247-R1 | MUST-FIX / P2 | Fixed；獨立 code/deep/docs 再審 PASS，無新增 findings | 本 Issue delivery owner | core 的 latest-sequence guard；`test_lifecycle_round_trips_do_not_revive_historical_operations` 驗證兩次同 digest 往返、proof 保留及最新操作成功。 |

2026-09-11 修正後驗證：18 項 process tests（44.047 秒）及完整
memory-m1-and-evaluation shard 323 項（81.121 秒）通過。offline validation、
122 個 generated files parity、release-state 0.24.2 及 diff hygiene 重新通過。
獨立 reviewer 另執行 5 項焦點回歸（7.630 秒），並補验跨 item 狀態往返、非 stop
歷史 proof 的 source/capacity 失效組合，確認舊 proof 不復活、最新操作分類保留。
R1 沒有改到其他 shards 的 runtime；未重跑其餘 11 shards，本機沿用原有界證據，
修正後完整各 shard 的 hosted 驗證另由 PR CI 執行。

初始固定候選 Security Diff Scan `0feeeb16-b121-44ac-b40b-57fb0de8c431` 已封存，
六個 source/package Python 檔與其餘 13 個變更檔案均 accounted，零可信安全候選。
R1 未觀察到繞過 fresh read/source 或產生 mutation handle 的路徑，仍以功能缺陷
阻擋初次 code review，不能由零安全候選解除。修正後的獨立再審已閉合 R1；
初始及修正後第二份 scan 的 canonical readback 均保留了較早的 discovery-pending
checkpoint，coverage 因此為 partial；不能把工具的 completed 狀態當成完整安全 gate。
原封存紀錄保持不變。後續掃描必須明確閉合完整 coverage，再與 exact-head Merge
Review、平台 gate 一起綁實際候選及 PR head，不以本段取代。

## 版本與剩餘範圍

source/package 沿用 catalog.yaml 0.24.2；candidate preparation 不新增；publication
truth 未查 tag/Release、不聲稱發布狀態；active guidance 區分本切片、剩餘 G1 資格
及 G2/G3；historical records 不改。M0/M1/V2b、production registry empty/default-off
及 native/dual-write/migration 排除不變。
