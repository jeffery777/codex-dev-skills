# Issue #278：異常處置驗收與交付

## 範圍與實際行為

可信程式入口現在可將 `AuditRequest`／`AuditDispatch` 交給固定
`AuditHostFactory`，經獨立 `take_grant` 控制面建立新 `AuditOnlyHost`，再由 CLI
輸出 JSON 或文字。關閉模式零接觸；同 dispatch 先消耗再呼叫 provider，失敗也不
恢復可用性。factory 核對完整 binding、principal、request 與 scope。
新 dispatch 及 CLI 納入資格 fingerprint。沒有新增 shell／JSON／環境變數載入器。

隔離資料由 fixture 建立；執行時使用實際 adapter、SQLite、Git loose-object reader、
flock、fd 與 CLI。人類授權、來源接受、資格及 provider 是 synthetic，不能作正式
接受。provider 的原子消耗及跨 factory/process 防重播是可信控制面的必要契約；
套件不提供持久 authority store。測試中的 pop 只驗證整合是否遵守這個契約。

## 必要故障驗收

使用者指定重點為異常後的妥善處置，無須實體製造錯誤。下表測試位於
`tests/test_memory_audit_dispatch.py`，錯誤注入經實際處理／清理路徑。

| 情境 | 觀察與預期 |
| --- | --- |
| off／未配置／錯誤 dispatch | off 不驗 dispatch、不消耗、不 discovery；未配置仍不可用。 |
| 重播／併發／程序漂移 | 同 dispatch 拒絕再次取得；provider 只被呼叫一次；跨 dispatch 重播由 synthetic provider 拒絕。 |
| principal/scope/grant 不匹配 | 拒絕讀取；回傳 grant 的完整 binding、principal/request 皆需匹配。 |
| 過期／撤銷／資格失效 | 要求失敗且不可重播；新要求另取新授權。 |
| provider RuntimeError/MemoryError/EIO | 固定 unavailable/resource-limit/storage-io；沒有原始例外、路徑或 traceback。 |
| SQLite FULL/BUSY/IOERR/NOMEM、OS ENOSPC/ENOMEM | 在實際 connection 已開啟後注入，驗安全結果、connection 關閉、鎖可重取、資料 bytes/inode/mtime 未改及新要求恢復。 |
| reader I/O | 實際 fd 讀取後注入；fd 已關閉、來源內容遮蔽，新要求恢復。 |
| 第二頁 FULL／同時撤銷 | 授權有效時保留安全第一頁；撤銷時整份內容清空。 |
| 合作式期限 | 停止剩餘讀取，安全 partial、釋放資源、新要求恢復。 |
| 最後揭露檢查的一般例外 | 已完成 2 頁／257 項並關閉 snapshot 後注入，內容及 digest 清空、connection 關閉、新要求恢復。 |

這些是受控 fault handling 證據，不是物理磁碟／RAM 耗盡、硬時間或最大 RSS
資格；本包不要求那些研究。`BaseException` 不被報告入口吞掉，也不宣稱 OS
強制終止／不可中斷 syscall 時可保證清理。

## 驗證與審查

- 使用 tracked `scripts/project-python` 選定 Python 3.12.9，PyYAML 6.0.3；
  未複製其他 worktree 的 venv，也未安裝依賴。
- 新入口 13 tests PASS；相關 audit／adapter／CLI 56 tests PASS。
- 首輪新增測試的 connection observer 錯包為 contextmanager，未走到注入點；
  修正為返回真實 connection 後整組通過。未把該次失敗當作 production bug。
- R278-01（SHOULD-FIX）：最終揭露測試原先在 snapshot 初始化時觸發。
  Disposition：Fixed。改成 close 後注入並驗證頁數／內容清空／connection；
  主代理單項 PASS，獨立 reviewer 回審 PASS。其他 17 檔 hashes 未變。
- 獨立 code-review-deep／docs-review 已完成；修正後無未處置 findings。
  父代理核對內容與測試 hash，`agent-integrate` 結果 accepted；此結果本身不證明完成。
- `validate-repo.sh --skip-unit-tests`、132 generated files parity、offline
  release-state `0.24.7` 與 diff check PASS。embedded units 明確 SKIP，另由全套 shards 驗證。

- Security Diff Scan `8971b92c-2025-4618-9d84-c453a936cc6c` 已封存並讀回：
  8 個 native source inventory 項目，加 10 個文件／測試逐檔補查，共 18 檔；
  人工檢查 0 candidates／0 findings；但封存 coverage 為 partial，保留前期 pending
  discovery checkpoint，所以該份封存不能作完整通過證據。Daybreak advisory
  為 granted／Daybreak Blue；沒有修改設定或執行實體耗盡。
- Scan 期間只有 R278-01 測試修正，因此平台保留 original-snapshot warning；
  八份 production source bytes 未變，獨立 security reviewer 已補查更新後測試，
  SHA-256 `d7a731818b73c0f8df29bc2d108813939ac1e17bb94a86740787e80d0f7689cc`。
  此文件是在 scan 後新增的證據摘要，另做比例文件／安全補查，不能宣稱平台
  snapshot 自動包含新增文件。後續 exact-head review 必須核對這項適用性。
- 工具回報用量：total 7,530,573 tokens，其中 cached input 7,331,968；
  source=codex_rollout、threadCount=2。這是工具聚合讀值，不是隔離 scan 成本量測。

修正後固定內容的掃描與全套測試結果另由 PR 證據提供；PR 後的 exact-head 內容審查、
required CI、strict receipt/readback 與 dedicated App 必須另外完成，不由本文件
或 pre-commit verdict 推定。

## 啟用與發版

本包不需要真實專案即可驗收。正式啟用仍需 host owner 指定 root/repository/
principal/scope、來源 accepts、環境資格及可信 provider／撤銷 backend。
可審查的 activation payload 必須包含精確整合 diff、唯讀 canary、停用與回退：
停止供應 dispatch、撤銷已核發要求即可停用，不刪資料。

- Source/package：維持 `0.24.7`；本包僅新增可信整合元件，普通 CLI 仍未啟用。
- Candidate：不新增發行候選或 release notes。
- Publication：本包未建立 tag／Release，也不宣稱改動已發布。
- Active guidance：技能、adapter reference、README、roadmap、milestone 同步。
- Historical records：既有驗收及發行紀錄保留原貌。

production registry 維持空值；不讀真實／原生記憶、不做 G2、安裝或部署。
正式啟用與 merge／Release 仍保留各自授權及適用 gates。
