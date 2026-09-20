# Issue #276 錯誤驗收、啟用與發版評估

## 交付與證據種類

新增的實際 `AuditOnlyHost` 串接單次讀取授權、固定 Git reader、獨立來源接受與
精確 audit qualification；沿用既有 SQLite core 和報告。Tests 每次建立暫存 Git／
MG1 root，先由 fixture 建資料，再交給僅具 audit capability 的 adapter。
Git object bytes、SQLite、flock、唯讀連線與恢復讀取是真實行為；人類 grant、
source acceptance、qualification 是明確 synthetic，沒有 production 註冊。

本機使用 tracked `scripts/project-python`，獨立建立 3.12.9 venv 並檢查 PyYAML 6.0.3。
沒有複製 venv 或改用系統 Python。`.venv/` 排除於公共 Git。完整程式／包裝／審查
執行結果由交付報告補列，以下 test 名稱是可重跑證據入口，不單憑存在宣告通過。

## 故障驗收矩陣

2026-09-21 使用者確認本包以失敗處理與恢復為驗收目標，沿用 #271 現行
failure-handling acceptance。必要證據為受控故障經實際 adapter、SQLite／reader、
清理及報告路徑後的行為；不要求耗盡整台機器來製造錯誤。最大規模的耗時／RSS
量測、實體耗盡研究及硬記憶體／硬時間保證均不列為 blocker 或後續待辦。
若未來另有明確容量、效能或程序隔離需求，才另定驗收範圍。

測試位於 `tests/test_memory_audit_adapter.py`，未特別標示者皆使用實際 adapter。

| 情境 | 行為證據／test 方法 | 證據限制 |
| --- | --- | --- |
| 正常與單次要求 | `test_real_git_sqlite_adapter_end_to_end_and_single_request` | 真實 reader/SQLite，synthetic 接受來源。 |
| Off、audit-only | `test_off_zero_touch_and_no_mutation_capability` | 未註冊 production；不能提升為 initialize/write/recall。 |
| 直接 core 的 off／跨程序零接觸 | `test_direct_core_disabled_and_process_drift_never_touch_host` | 在 host property 求值前拒絕停用、缺 host 及 process drift。 |
| Scope/principal/request、期限、撤銷與時鐘 | `test_authority_scope_principal_request_expiry_revocation_rollback` | 撤銷集合與時鐘故障由 fixture 控制。 |
| 資格環境漂移 | `test_environment_qualification_rejects_every_changed_dimension` | 每個 environment/runtime 欄位分別漂移；不是正式環境資格。 |
| 缺少／敏感／不相符來源接受 | `test_independent_source_acceptance_and_sensitive_content_redaction` | hash 相符仍需獨立接受。 |
| Allowlist 與 config/worktree 隔離 | `test_allowlist_rejection_precedes_filesystem_and_git_config_is_not_executed` | 不執行 Git 或 config。 |
| 缺物件／symlink／來源 bytes 損壞 | `test_missing_object_symlink_corruption_and_new_authority_recovery` | 真實暫存 object 故障及還原；不碰真實專案。 |
| 來源 bytes／解壓／時間上限 | `test_source_byte_and_decompression_bounds_and_timeout`、`test_object_decompression_bomb_and_cooperative_read_deadline` | 真實壓縮 bomb；deadline 使用注入時間，非 OS 阻塞保證。 |
| Root/source identity、SQLite 損毀 | `test_root_source_identity_drift_and_corrupt_sqlite_never_repair` | 真實損毀暫存 DB；原資料 bytes 無 adapter 改寫。 |
| Reader 中途撤銷／fd 收束 | `test_mid_source_revocation_stops_io_and_closes_descriptors` | 在真實 os.read 後注入撤銷，逐 fd 驗已關閉。 |
| SQLite／協作鎖 | `test_real_coordination_and_sqlite_locks_release_without_retry` | 真實 BEGIN EXCLUSIVE／flock，無 retry。 |
| I/O／空間／資源不足 | `test_injected_io_enospc_enomem_no_leak_no_retry_and_recovery`、`test_memory_error_closes_connection_and_new_grant_recovers` | EIO/ENOSPC/ENOMEM/MemoryError 為注入，不宣稱物理 FULL。 |
| 同時 I/O 和撤銷、最後一頁失效 | `test_revocation_with_io_and_at_final_output_clears_disclosure` | 需清空內容，不因 I/O 分類保留。 |
| 已驗證來源被替換 | `test_source_replacement_after_valid_page_clears_content` | 真實暫存目錄 replacement。 |
| 同一來源先有效、後損壞 | `test_prior_valid_object_cannot_be_rebound_by_later_failed_read` | 固定首次成功的 signature；後續解壓超限／截斷不得覆寫，須清空並釋放 lock。 |
| CLI 報告整合 | `test_cli_uses_actual_adapter_and_requires_new_host_for_new_request` | 測試注入真實 adapter；不註冊 production。 |
| 舊 cursor／host 重播 | `test_closed_snapshot_cursor_and_grant_cannot_replay` | host instance 單次；新授權／新 snapshot 可恢復。 |
| 頁數／wire bytes、safe partial | `test_actual_adapter_page_output_limits_safe_partial_and_fresh_recovery` | 257 項真實 SQLite proof replay；fixture 建立資料。 |
| 部分頁 I/O／撤銷 | `test_partial_requires_live_authority_and_unchanged_integrity_even_with_io_error` | 安全時留 256 項，失效時清空。 |
| 讀取期限與收束 | `test_actual_snapshot_timeout_releases_reader_and_preserves_safe_page` | 注入 deadline 經真實 snapshot/page；新 grant 恢復。 |

所有 adapter report tests 均核對 DB/lock bytes、inode、mtime 未被 adapter 改動，
並在返回後重新取得 exclusive lock。Fault mutation 與還原只在 fixture 自有暫存資料。
#271 的真實 SQLite page-quota FULL／fresh-process readback 是相關回歸，不等同
本包 readonly reader 必然會遇到 SQLITE_FULL。#273 APFS 實體耗盡研究不重啟。

## 啟用方案與未完成資格

可安裝元件、建構順序與允許欄位見
[adapter reference](../../../skills/loop-engineering/references/memory-audit-adapter.md)。
尚缺正式 principal/repository/root、讀取 scope、artifact allowlist、受信任接受／撤銷
控制面及環境資格。這些不是程式自行猜測的值，也不能由測試 fixture 提供。

本包的具體可審查結果是可注入 host 的唯讀組合元件與隔離端到端驗收；一般 CLI
仍不可讀取真實資料。正式 CLI factory/registry diff 要在目標與 authority source
確定後，連同單次要求 dispatch、canary、停用復原再審查。沒有 activation payload
就不將 placeholder 變成 production registry。

正式啟用仍需接受實際 filesystem／host control ports、相容環境、既有資源限制
及故障處理證據。256 MiB 是資料庫 profile；10 秒是合作式讀取期限，非最大資料量
完成保證。整體 RSS／硬時間上限不在本包能力承諾內，合作式 deadline 不能強制
中斷 hung syscall；這些限制不構成繼續做耗盡實驗的要求。只接受固定 loose SHA-1
Git objects，packed-only、worktree `.git` file、網路 filesystem 均不在本包支援範圍。
不作正式 Linux 合格宣稱、不承諾 shared-host 隔離、purge、repair 或維護能力。

## 發版判斷（2026-09-21 點時）

建議本包不單獨發版。它新增可安裝 adapter 元件並補強 partial safety，但一般入口
仍缺指定的可信 host factory、真實讀取權與環境接受；目前沒有「安裝後即可在
明確正式環境使用」的唯讀入口。這符合 Issue 的內部準備不硬發版原則。
待正式唯讀整合與資格完成後，再評估 pre-1.0 minor；`v0.25.0` 僅是候選方向。

- Source/package：`catalog.yaml`／installer／plugin manifest 保留 `0.24.7`。
- Candidate：不新增 candidate release note，不修改歷史發行 notes。
- Publication truth：本次重新透過 GitHub connector 查得 `v0.24.7` annotated tag
  object `934d1c0aa985e3a3568a914bbcf19287cf182866` 指向
  `aedfdb124b996eb1626999bcbdda0f31abe2382d`；[Release](https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.24.7)
  的 target 同 SHA，draft=false、prerelease=false。這是指定 tag 的點時查核，
  不是永續的「最新版本」指標，也不證明本包已發布。
- Active guidance：README／skills 描述實際可用元件與未啟用邊界。
- Historical records：#274／#271 舊紀錄及既有 notes 保持原貌。

使用者已授權更新 Issue、完成必要正式審查及 Security Diff Scan，通過後
commit／push／建立 PR，且完整 Merge Review 無 findings 並通過適用 gate 後合併。
Pre-commit review 不替代新 PR head 的完整 Merge Review、hosted CI、strict
receipt/readback 與 dedicated App。真實 memory activation、tag／Release／deploy
不在本次授權範圍。
