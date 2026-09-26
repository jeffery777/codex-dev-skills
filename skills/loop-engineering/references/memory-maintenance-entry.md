# 單專案 memory-maintenance 受控入口

Runtime compatibility: shared。Issue #304 新增一般單次可信程式串接；既有
[synthetic pilot](memory-maintenance-pilot.md) 與五操作 core 的接受結果保留。

## 可信 host 邊界

限定 POSIX 本機、既有 initialized host-owned 單 root、固定
`PinnedGitReader` Git loose commit/tree/blob permits。沒有 root/import/config
loader。Production registry 保持空；CLI argv 及 Desktop 自然語言都不能建立
可信 host。真正 runtime source review、確認 UI 與 operation qualification
尚未整合，正常入口回 `adapter-unavailable`。不宣稱完整 G1／MG1 qualification。

Host 整合順序：

1. 明確接受單 root 的身分與讀取範圍（preview、proof／projection、current-only
   recall 驗證可能掃描該專案的庫；不授權其他專案）。使用既有 core schema、
   profile 與安全 filesystem identity，不進行初始化或 migration。
2. 提供 `MaintenanceAuthorityProvider(binding, clock, accept_request, accept_preview,
   request_revoked)` 的 keyword arguments。`accept_request(binding, intent_bytes)`
   是 host 的明確要求接受，只准備 preview，不能授權 mutation。
3. Host 獨立接受每個完整 version 的 `SourceAcceptance`、固定 Git permits 及
   `MaintenanceQualification`。Qualification 綁 root digest、五操作之一、
   `maintenance_environment` 的 code/runtime/profile/filesystem facts、evidence
   與期限；`authorize`／`readback`／`recall` 等階段不擴大原操作資格。Work budget
   由既有可信 storage port 提供，preview/core 重新驗證 J/T/G。
4. `provider.accept(intent)` 建立新的 `MaintenanceRequest`。Intent 恰含
   `operation`、`item_id`、`candidate`、`restore_revision`。Stop/resume 的 candidate
   為 null；僅 restore 指定 retained revision。Restore 的 candidate 是新的 revision
   及新的 source/validation acceptance，不能把舊 validation 當作新的接受。
5. `MaintenanceHostFactory` 固定 binding/repository/permits/accepted_sources/
   qualification/provider/source_revoked/qualification_revoked/storage，配合 request
   建立一個 `MaintenanceDispatch`。Factory 原子消耗原 owner provider 已登錄的
   request，無效／複製／反序列化 request 不能創造 grant。Audit `ReadGrant` 型別
   及 authority 不相容，不能升格。
6. CLI trusted embedder 使用 `governancectl.main(['maintenance', '--enabled'],
   maintenance_dispatch=dispatch)`；Desktop trusted adapter 使用
   `desktop_maintenance(enabled=True, dispatch=dispatch)`。沒有正式 ports 時不注入。
   Shared `maintenance_report` 產生 preview，將其原樣送入 host confirmation，
   經一次 core.execute，再建新 core 與 source reader 做獨立讀回。

`accept_preview(binding, preview_bytes)` 必須把完整 canonical bytes 呈現到真正
當前接受介面，回 `AcceptedPreview` 的同 bytes 與精確 confirmation。Core 綁定
scope、operation/item、candidate／target revision、before/after digest、nonce、
期限、storage budget 與 digest。等待期間沒有 DB／provider 鎖；返回後重查 request、
資格、來源及 TTL，執行時重新核對 state 與 proof replay。Stop 不採用內容，允許
source ports 缺失／撤銷；這不恢復 stopped item 的 recall。

## 防重播與失敗分類

Provider 只保存 RAM object identity；take 對同 instance 跨 factory／dispatch 原子
消耗。確認 callback 也只使用一次。Grant 綁原 owner、PID 與 clock process ID，
fork 拒絕、restart 空登錄、複製或 JSON 重建拒絕。Host shutdown 呼叫 `close()`。
沒有持久 authority store 或跨程序 mutation 恢復。新程序必須重新接受全新要求；
SQLite proof 是 durable 操作證據，不能當新權限。任意同 OS 使用者 Python 的
host 篡改不在此 TCB 隔離保證內。

| Outcome | 必要證據 |
| --- | --- |
| applied | 新 reader 驗證最新 proof、當前 state/revision/projection、retained versions 及 current-only recall 一致。 |
| not-applied | Execute 尚未呼叫，或新 reader 帶原 preview 證明沒有該 proof 且完整 state 仍等於 before。 |
| unknown | 已嘗試 execute，但讀回不可用、合法並行前進、完整性／容量／adoption 不足；保留細分類 reason。 |

輸出是獨立階段；emit/flush 失敗回 `output-unavailable`，保留已驗證 outcome。
不得再送 mutation 或声稱 rollback。讀回結果不明需 host 另行授權唯讀診斷；
本入口不自動重試、恢復 journal、清理或重建資料。

## Preflight 與 canary

`memory_maintenance_preflight.preflight_report` 預設 off；需要 host 獨立
`inspection_allowed(binding, request)` 後才查 advisory facts。檢查要求仍 pending、
scope、operation-specific qualification、source acceptance 與 confirmation port。
不消耗 grant、不建立 preview、不讀 DB；PASS 不驗證正式 UI／人工意圖、Git
內容、before-state 或交易容量。這些仍由正式 host 與 core 在執行路徑查核。

`canary_report` 必須由 host 的 `isolation_accepted(dispatch)` 核對新建隔離資料，
且沿同一入口取得新接受。結果只證明當次 isolated E2E，不提供 production 資格。
此 callback 是 TCB 契約，不是 CLI `--isolated=true` 權限。

## 驗證

`tests/test_memory_maintenance_entry.py` 使用新建 synthetic Git／SQLite，驗證五
操作、各層重播／撤銷／TTL、等待不持鎖、來源與 state drift、process boundary、
真實 core 交易故障、新 reader 及輸出失敗。既有 governance、audit 與 pilot
tests 繼續回歸。Physical FULL、production ports 與完整 G1 qualification 不在本包。
