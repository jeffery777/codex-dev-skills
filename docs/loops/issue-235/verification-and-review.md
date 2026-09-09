# Issue #235：驗證與審查證據

以下為 2026-09-09 本地 v1/v2 審查、v3 修正及首次 PR exact-head 審查的點時紀錄。
最終正式 review、Security Diff Scan 與 exact-head 合併證據另綁
[Issue #235](https://github.com/jeffery777/codex-dev-skills/issues/235)的 PR／receipt；
此檔案不是合併授權或平台 gate 的替代品。

## 選用方式與範圍

主代理依 project-delivery／project-orchestrator／implementation-slice 契約執行；
獨立唯讀 reviewer 先檢查 G0 易漏邊界。此 advisory 不替代最終正式 code/deep/docs
review 或 Security Diff Scan。當前 Desktop 公開角色能力及 installed router 決策
採 baseline deep reviewer；CLI-only 資格不能套用到 Desktop。

v1 固定完整 diff SHA-256：
`9cd30d6e9b34be7ab588843d723798139d74908a83dc63995d640bc50769f0b0`。
23 個變更檔案含 6 個生成 counterpart；base/HEAD 為
`eed22ddf41ddb6b525e5f9455737218cd94c01a5`。獨立 reviewer 的 v1 code/deep/docs
gate 為 BLOCKED，並以 49 項 passing tests 未涵蓋的負例找出下列問題。

## Finding dispositions 與修正證據

下列項目由主代理依 G0 oracle 與實際 source 確認後修正，沒有 deferred finding。
`Fixed` 表示修正及負例已存在；最後重審 verdict 仍須另綁最終 diff。

| ID | Disposition 與修正 |
| --- | --- |
| CR-MF-01-capacity-result-exclusive | Fixed：後態容量正反條件互斥；完整容量不得標為 capacity-unproven，未知容量不得標為 applied。 |
| CR-MF-02-postflight-error-classification | Fixed：容量量測與 external-copy port 例外分開；副本觀察失敗回 state-unknown 並保留 proof。 |
| CR-MF-03-postflight-copy-binding | Fixed：applied 要有原 preview 且 fresh copies 精確相符；缺 preview 保留 proof/unknown，錯誤 caller digest 回 readback-binding。 |
| CR-MF-04-historical-proof-projection | Fixed：逐 proof replay item 存在、status、前後 revision 及該 revision projection；拒絕單筆歷史 proof 不一致。 |
| CR-SF-01-precommit-crash-oracle | Fixed：明確 precommit 中斷只容許 unknown/not-applied；只有 commit-vm 保留三態。 |
| CR-SF-02-confirmation-expiry-bool | Fixed：confirmation 到期值先驗嚴格整數，拒絕 True 等於 1 的型別混用；新增合法整數與 bool 負例。 |
| MR-MF-01-historical-state-digest | Fixed：首次 PR exact-head review 找到相鄰 proof 配對竄改 digest 可繞過鏈接檢查；補逐步完整 logical state 重算、當時版本退休狀態還原，以及跨 item／歷史 update／stop／resume 的四組配對負例。 |
| MR-MF-02-historical-restore-semantics | Fixed：歷史 restore proof 必須驗指定 retained source 與結果版本的語意／來源及新驗證，拒絕以合法較舊 revision 將不同內容的 update 偽裝成 restore。 |
| MR-MF-03-historical-proof-time-binding | Fixed：每筆 proof 時間不得早於對應版本驗證時間；負例在前一 proof 與版本驗證之間改寫時間，不能被單純遞增鏈掩蓋。 |
| MR-MF-04-integrity-readback-classification | Fixed：readback 以固定 schema/G1 snapshot 邊界將持久契約失敗分類為 integrity-failed；九組負例同時驗 audit 拒絕及 readback 完整性失敗，包含未列舉的 bool 型別診斷；host／clock／I/O 未知狀態仍分開。 |

初期 advisory 的 schema/runtime 分層已改為 `SCHEMA_OPERATIONS` 與 `g1_*` subset；
fresh connection/state/proof 要求由核心及上述四項補強落實。已接受契約允許 `stop`
使用 maintenance proof reserve，其餘 G1 mutation 不可；不沿用早期 advisory 的
「所有 G1 一律不可」表述。

v2 焦點測試 54 項、v3 焦點測試 55 項 PASS，包含六項 finding 的精確負例；v2
package parity 120 個生成檔案、offline validation、`git diff --check` 均 PASS。
完整 12 shards 共 1,133 項 PASS，其中 memory/package 在 v2 修正後執行；v3
只新增到期值型別 guard、對應測試與本紀錄，受影響 shard 重跑及最終內容身分另記於 PR。
這些 synthetic 測試不能替代真實 host、filesystem 或人類授權資格。

首次 PR head `49c7b4585fc76a83a0d109fd05be3bce92d74f36` 的完整內容審查為
BLOCKED；上述 MR-MF-01 不能由 pre-commit PASS 或零安全 findings 取代。
修正後必須形成新 head，重跑受影響測試、安全掃描及完整 base-to-head Merge Review；
最終證據綁新 head 的 PR receipt，不沿用首次 exact-head verdict。
後續 head `8b6ae36a3860c505a9bde132cc94ed51e4eee752` 已修 MR-MF-01，但完整
review 另確認 MR-MF-02/03；同一 proof/row 邊界的修正與負例完成後仍需新 head
的完整審查。上述 `Fixed` 不替代最終 gate。

## Security Diff Scan 的點時結果

v1 scan `a2fd999a-6313-4285-9356-79b1c662259d` 已成功封存並讀回：
coverage `complete`、23 個 surfaces、零 deferred、零可報告安全 findings。
固定 content digest：
`codex-security-snapshot/v1:sha256:c92f7ad35c75bfb2f8da12324e3e0c79d63086f075f86a674d4c4391ccd0cd59`。
原生 inventory 的 10 個 scripts 與其餘 13 個 tests/fixtures/docs/reference/manifest
均逐檔檢查；source/plugin 副本另驗 bytes 相同。獨立架構核對及主代理 source review
保留 host TCB、空 registry 與 synthetic-only 邊界。

上述 code contract findings 不因安全 scan 為空而被忽略；v2 變更仍須依影響重做
code/deep/docs review 與 Security Diff Scan。不存在 security candidate 時，
candidate validation／attack-path phase 不適用，不能稱為 penetration test。
TAC not_granted 只是 advisory；preflight 三項 capability checks 全通過。
v1 工具 usage 為 8,533,714 total tokens、8,172,544 cached input、31,509 output，
是工具三個 task 的累計口徑，並非這次掃描增量或費用。

## 可重跑驗證

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_memory_governance_contract tests.test_memory_governance_core \
  tests.test_memory_governance_faults tests.test_governancectl
./scripts/project-python scripts/test-shards.py run-all
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python scripts/validate-release-state.py
git diff --check
```

subprocess fixtures 只在 test-owned synthetic roots 強制結束程序；其測試父程序可
明確恢復／清理自己建立的暫存庫。G1 core 本身沒有 recovery 或 cleanup 入口。
來源／host acceptance／storage qualification 為 synthetic；不得聲稱真實授權、
power-loss、ENOSPC、temp peak 或維護預留已通過。

## 版本的五個角色

| 角色 | 本切片處置 |
| --- | --- |
| Source/package version | `catalog.yaml` 為 0.24.1，未變更；生成套件包含新增 allowlisted modules/reference 且與來源一致。 |
| Candidate preparation | 不建立新版本候選；無真實 adapter／G2／storage qualification，不把合成測試當可發行條件。 |
| Publication truth | 本切片未查證 tag/Release，不宣稱目前發布狀態；main 或 package parity 不提供此證據。 |
| Active guidance | 明示 G1 部分核心、default-off、synthetic 範圍及 G2/G3 缺口。 |
| Historical records | 保留 G0/既有 release notes 的點時紀錄，不事後改寫。 |

## 剩餘資格缺口

- 真實 CLI/Desktop source／confirmation／root registry adapter 及持久來源撤銷查核。
- 固定 SQLite build/OS/filesystem 的 temp 集合、J/T/G peak、ENOSPC、4 GiB 最壞鎖定時間。
- 維護 reserve 實體空間、G2 erase/prune/retention/compact/recovery 與殘留／外部副本覆蓋。
- 自然語言入口、使用者端完整操作／容量報告與完整 MG1 G3 資格。

這些是本切片不開放 production 的明確限制，不是已確認 production 缺陷的掩飾或
對外能力承諾。#222 的原始 finding 身分追溯仍未解，本切片沒有新的 M1 runtime 證據。
