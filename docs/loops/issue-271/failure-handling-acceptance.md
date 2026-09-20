# Issue #271：儲存失敗處理驗收

## 2026-09-20 的範圍決定

第四次觀察交付後，使用者明確提出將目標轉向「FULL 發生時應做的事」，並同意
同步修改 Issue，避免正式 review 仍使用舊條件。本文件與 Issue #271 的現行 DoD
取代本目錄先前以 physical FULL 為結案前提的規定；PR #272 的完整版本審查須以此
範圍重新判定，不沿用舊的 BLOCKED 或 PASS verdict。

本包驗收 repository-only、default-off 的 G1 核心與合成 host／fixture 在儲存失敗後
的安全行為。頁數限制產生的真實 SQLite FULL 可作為應用程式錯誤處理證據；它不
證明作業系統磁碟已滿。使用者進一步澄清，APFS 實體耗盡研究不是需求或後續待辦；
[範圍決定紀錄](https://github.com/jeffery777/codex-dev-skills/issues/273)已以 `not_planned` 結束。
保留未驗證的限制說明，不要求繼續試驗，也不宣稱已證明任意實體環境可恢復。

## 現行行為驗收

| ID | 必須證明的行為 | 現有來源與可重跑驗證 |
| --- | --- | --- |
| FH-01 | 實際 SQLite 回傳 FULL 13；quota FULL、CANTOPEN、OS ENOSPC 及 injected reply loss 分類分開，不冒稱 physical FULL。 | `StorageFaultTests.test_page_quota_full_preserves_revision_projection_and_proof_after_reopen`、`test_actual_cantopen_is_a_separate_missing_path_control`、`test_classification_never_substitutes_cantopen_quota_or_injected_errors`。 |
| FH-02 | 失敗後不重送 mutation、不復活舊 handle；妥善關閉 writer，讀回使用新 connection；新程序唯讀讀回不改檔案。 | `GovernanceCore.execute` 消耗 handle、finally 關閉 writer；page-quota／reply-loss tests、core 的 `test_tampered_preview_and_handle_replay` 與 `test_new_core_cannot_reuse_handle_and_readback_is_independent`。 |
| FH-03 | 根據 durable proof／狀態區分 applied、not-applied 與 state-unknown；例外、沒有 operation ID 紀錄或讀回失敗本身不能證明未執行。 | page-quota test 核對 revision／projection／proof；`test_reply_loss_never_turns_enospc_exception_into_not_applied`；core 的 `test_readback_authority_loss_after_commit_is_explicit_unknown`。 |
| FH-04 | caller 能處理結果或明確例外。control 的前置恢復、讀回或 writer 證據不足時不啟動 control；control 已執行但其量測／後續讀回未證實時保留 incomplete、不重試。不自行 repair 或刪除 journal。 | `test_reader_and_control_measurement_failures_cannot_report_observed`、`test_valid_read_event_cannot_hide_abnormal_exit_or_timeout`、`test_restoration_failure_stops_all_dependent_readback_and_control`、`test_process_loss_preserves_nonempty_journal_and_refuses_repair`。 |
| FH-05 | 在受控條件恢復並重新驗證後，以新的 preview／confirmation／operation ID 完成正常操作；舊授權不得重播。 | page-quota test 的 `recovery_control` 與其 fresh reader；core 的 `test_old_operation_id_is_rejected_even_with_fresh_host_confirmation`。 |

以上 tests 位於 [storage-fault tests](../../../tests/test_memory_governance_storage_faults.py)
與 [core tests](../../../tests/test_memory_governance_core.py)；實作為
[G1 core](../../../skills/loop-engineering/scripts/memory_governance_core.py) 與
[fixture coordinator](../../../tests/fixtures/memory-governance/storage_fault_case.py)。
此矩陣是驗收要求與證據入口，不以存在 test 名稱代替執行結果。

FULL 可能只中止當前 statement，也可能導致整個 transaction rollback；不能僅憑
錯誤碼推斷已完全回滾。現有核心選擇關閉 writer 後以新連線查證結果，而非自動
重送。依據：[SQLite 交易錯誤處理](https://www.sqlite.org/lang_transaction.html#response_to_errors_within_a_transaction)。

「回報」在本包指既有 caller 可讀取的結構化結果、明確例外及 fixture 診斷。
核心可能拋出 `ContractError("state-unknown")`／`ContractError("storage-unavailable")`，
caller 必須處理例外，不能假設每條路徑都返回 dict 或將例外當成 not-applied。這不代表已有
production UI 通知、背景告警或寫入滿載資料庫的可靠日誌。也不宣稱已有全域停止
所有 writer 的模式、各種 VFS 失敗點覆蓋、實際釋放磁碟容量或任意平台恢復能力。
這些能力若成為產品需求，須另外定義範圍，不能從本矩陣推定已完成。

## 交付與正式審查

1. 使用 worktree venv 與 tracked `scripts/project-python` 執行行為測試、核對 source
   與結果；不建立映像、不重掛前四次映像、不增加實體試驗。
2. 執行 repository checks、package parity、offline release-state、JSON／連結／隱私
   與 diff 檢查；程式未變且來源、環境與假設一致時可沿用先前完整回歸證據。
3. 獨立審查 Issue／PR／active docs 的一致性，完成相應 Security Diff Scan；新 head
   仍須完整 base-to-head Merge Review 和該 head 的 hosted CI。
4. content review 與 provider enforcement 分開記錄。範圍調整不豁免草稿狀態、
   成功 strict receipt、readback、dedicated App／ruleset 或 merge authority 的要求。
   未完成的 gate 仍保留，不以修改 DoD 宣告自動合併或結案。
5. 只有 repository-only fixtures/tests／文件，沒有可安裝行為變更，因此本包不另
   發版；catalog source/package 0.24.7、default-off／空 production registry 不變。
   這不代表完整 G1/MG1 qualification。

可重跑行為驗證：

```sh
PATH="$PWD/.venv/bin:$PATH" ./scripts/project-python -m unittest \
  tests.test_memory_governance_core \
  tests.test_memory_governance_storage_faults \
  tests.test_memory_governance_pressure_pool
```

## 原 finding 的處置與歷史角色

`MR-272-01` 與 `FOURTH-EVIDENCE-01` 作為本包驗收 blocker 的要求改為
**Rejected（不適用現行需求）**。使用者明確選擇驗收失敗處理，不要求實體耗盡研究；
[範圍決定紀錄](https://github.com/jeffery777/codex-dev-skills/issues/273)以 `not_planned`
結束，不再是 Deferred 待辦，也不指派續做研究或第五次試驗。

此處拒絕的是將實體證據列為本包必要條件，不是否認觀察事實或標記技術問題 Fixed。
四次均未觀察 physical SQLite FULL；第四次容量恢復 unproven，故沒有實體失敗後
獨立讀回／正常 control。這些限制保留，不能宣稱任意實體環境已驗證或完整 production
qualification。未來若另有實體環境資格需求，再另定範圍；本次沒有映像維護授權。

原 [delivery plan](delivery-plan.md)、三份追加方案、四次觀察／驗證紀錄及四份
observation JSON 均為各階段點時證據。其中「原 DoD 不變」「須 physical FULL 才能
結案」及當時的 Issue／PR gate 狀態，描述本次決定以前的範圍；不得用來覆蓋本文件。
四次觀察仍保持 incomplete，不回填為成功。舊 #245／#253／#265、release notes
與既有審查留言亦保持歷史原樣。
