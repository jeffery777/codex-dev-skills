# 單一 PR 文字發布／Bounded PR text publication

## 範圍與驗收

此選用、developer-only 流程回應 [Core #22](https://github.com/jeffery777/engineering-workflow-core/issues/22) 與 [Issue #367](https://github.com/jeffery777/codex-dev-skills/issues/367)。只處理自己明確獲准的同一個 open draft PR 標題／本文，不是新 Core 義務、一般秘密偵測器或全平台發布 gate。既有十個合成案例與 PR 留言讀回保留其原覆蓋；它們不代替原生標題／本文更新驗收。正式 Core／consumer pins、安裝 catalog／plugin、產品版本與已安裝技能均不改。

`scripts/pr_text_update.py` 凍結已檢查的 title/body 與 baseline，再依 `read → validate → UNKNOWN checkpoint → update once → independent readback` 執行。錯 repository／PR、過時 payload、基準漂移、未知 request 欄位或讀取失敗都在 update callback 前阻擋。只有 `repository_full_name`、`pr_number`、`title`、`body` 可交給原生更新；base、state、maintainer 權限等不在此流程內。文字不 trim、不變更 Unicode 或換行。Inspection binding 只證明同一內容，不提供操作授權或「無秘密」證明；當次內容檢查仍須有來源。

支援公開 metadata：repository full name／numeric ID、PR number／numeric ID、明確 API／HTML URL、open／draft、base/head SHA／ref、head repository、updated_at，以及 title/body。REST response 只擷取這個子集，不宣稱已檢查作者其他資訊、附件、labels、Git commits／簽章或其他 provider 欄位。Request 與正規化 snapshot 的額外欄位一律阻擋；未要求的 REST response 其他欄位不在覆蓋宣稱內。

核心輸入為 bounded strict UTF-8 JSON：256 KiB 總輸入、64 KiB body、256-character title；這是本工具支援界線，不是 GitHub 上限認證。不支援 null body、其他 host、ready／merged／closed PR 或多 PR。拒絕 duplicate keys、非有限數、無效編碼與未知欄位。結果只含安全代碼，不回貼本文或 provider 原始錯誤。

同一事件迴圈、同一 Attempt 在首次 await 前保留 PREPARING，阻止重入；UNKNOWN／VERIFIED 不重送。這不是跨程序鎖。Caller 必須先確定受控 UNKNOWN checkpoint 已保存；中斷後先讀該紀錄，不以建立新 Attempt 跳過未知狀態。`reconcile` 只接收 read callback，沒有更新入口；讀到預期文字只證明當下觀察，不證明誰執行了先前未知操作，也不授權重送。

## 原生 connector 接線

此 bridge 限具備 `functions.exec`、有界 PTY command session 與上述 GitHub connector 的當次 runtime。它不新增 HTTP／gh transport、Node 相依、認證讀取、持久服務或通用 broker。其他 runtime 不由此取得資格。

`scripts/pr_text_native_bridge.py --input <controlled-input.json>` 沿用同一核心 callback。Input keys 為 operation（publish／reconcile）、inspection（Inspected 的四個欄位）、proposed、attempt_phase。受控檔案與完整 checkpoint 放在探索根與 repository 之外，不提交私人執行資料。

固定 native dispatcher 應按以下順序操作；成功檢查是呼叫的前置，不是提醒文字：

1. 在啟動前固定已批准的 repository／PR、stable IDs、branch/head、原文、擬改 title/body、inspection 及受審 bridge 身分。Read-only roundtrip 先驗當次 PTY／frame／connector 路徑，不能拿 pipe 測試冒充。
2. 只解析行首 `I22_REQUEST ` 後的 strict JSON，限 sequence、kind、arguments。忽略 TTY echo 的 DATA／END，不能把它們當 request。Sequence 逐一相符；publish 的種類順序只有 read、checkpoint、update、read，reconcile 只有 read。未知種類、錯序、額外參數、錯目的地或第二次 update 都停止且不呼叫 mutation。
3. read 只呼叫原生 `github_fetch` 的固定 `https://api.github.com/repos/{repo}/pulls/{number}`。確認成功後回傳 `normalize_rest_pull` 所需的原始巢狀 REST 子集；不要和正規化 snapshot 混用。不改用另一控制面繞過拒絕。
4. checkpoint 限 UNKNOWN、當次 binding 與同一 repository／PR。用受控保存入口保存，再完整讀回核對，成功才 ACK True；保存失敗或不確定立即停止，不 ACK、不更新。保存不授權外寫。
5. update 前 dispatcher 再核對四個允許參數與當次固定 title/body 完全相等；update_seen 必為 false。將它先標為已嘗試，再只呼叫一次原生 `github_update_pull_request`。只有 isError 明確為 false，且回應 number／URL／title／body 對應，才能 ACK True。Error／timeout／不明結果不能轉為成功；不重送。
6. 核心仍要求新的獨立 read。Title/body 及受保護身分／metadata 不符就 UNKNOWN；不要只相信 mutation 回應。未知結果只走 read-only reconciliation，沒有自動修復或回復。

### 有界 framing

每個 request／response 都包含相同 sequence 與 kind。Response JSON 只有 sequence、kind、ok（boolean）、value。以 UTF-8 JSON → base64 分成每片最多512個ASCII字元：`I22_DATA <sequence> <zero-based-index> <chunk>`；最後送 `I22_END <sequence> <chunk-count>`。每片獨立一行，dispatcher 每次只送一行並收取有界輸出，避免一次灌入終端 input queue。Base64 只是 framing，不是保密。

Bridge 每行上限768 bytes、decoded response／單筆輸出16 KiB、累計輸出64 KiB、每筆等待45秒。此原生接線只支援當次小型已批准文字，不推定核心64 KiB body的所有大小都可經此接線。缺片、重複／錯序片、錯 sequence／kind、畸形、EOF 或超限立即失敗；update 發出後即保留 UNKNOWN。先前 PTY fixture 的1024-character片含標頭超過實際1024-byte canonical上限而失敗，修正為512片後重驗；原失敗保留。未修改 termios 或持久設定。

## 真實驗收與回復計畫

只用本次維護自己的 draft，包含實質 helper／tests／伴讀變更；不另開無意義 canary，不改既有使用者內容或已合併 PR。實際 PR number 從建立結果取得並讀回，不預猜。當次精確 baseline／測試值保存在受控證據，不把本機路徑或原始 logs 貼進公開 PR。

先做 read-only PTY roundtrip。再用相同 inspected input 的錯 repository／number、過時 title/body、未支援欄位及漂移 baseline 驗證零 mutation；不把故意錯的目的地真的送往平台。唯一正向變更是已核可的同一 draft title/body，先保存 UNKNOWN，更新一次並讀回。

回復是一筆新的 inspection／checkpoint／update／readback。只有當下文字及支援 metadata 完全等於剛才自己更新後獨立讀回的值，才回復 captured baseline。任何他人修改、source/head漂移或未知寫入就停止，不強蓋、不自動重播。最後仍保持 draft，#22 保持 open；合併、發行與安裝另核授權。

原生 callable 沒有 If-Match／expected-current-text／CAS。最後一次查讀到更新之間仍有競態；本流程不能宣稱完整防止同時編輯。Scope 是 Agent 正常誤操作／流程失效，不要求抵抗管理員故意改 callback、可信程式或證據。#23 不在本次範圍。

## English

This optional developer-only workflow binds one approved open draft PR's exact title/body, declared public metadata and destination. It adds no shared Core gate, installed adapter, secret detector or privileged-administrator defense. The existing fixtures/comment readbacks retain their original scope. Product version, catalog, plugin and Core pins do not change.

Use the same Python core for read, strict validation, a durably saved UNKNOWN checkpoint, one update and independent readback. Wrong destinations, changed requests, unsupported fields and baseline drift stop before update. A binding proves matching inspected text, not safety or authority. Preserve all whitespace/newline/Unicode bytes. A shared Attempt reserves execution before its first await; this does not lock different processes. Unknown effects permit read-only reconciliation, never automatic replay.

The runtime-specific stdio bridge does not contact GitHub or credentials. A trusted dispatcher pins the approved target and exact text, validates sequence/kind/argument fields, saves and reads back the checkpoint, then uses only the native connector. Never dispatch a second update or treat missing/error results as success. Normalize only the listed public REST subset; unlisted provider metadata is not inspected. The bridge's512-character indexed base64 chunks and768-byte line bound avoid the observed terminal canonical limit without setting changes. Responses/output/wait time are bounded as above. Pipe and PTY fixtures are separate from actual native evidence.

Use only this maintenance draft for one expressly authorized title/body update and guarded restoration. First qualify the current bridge with a read-only roundtrip and verify invalid inputs dispatch zero updates. Restore only after a fresh inspection confirms the PR still matches the test result, including protected metadata. Stop on drift or unknown effects. The native callable has no conditional-update precondition, so a pre-read/write race remains. Keep the PR draft and Core #22 open. No merge, release, installation or #23 sandbox retry follows. Written per ASD-STE100 principles; full conformance is unverified.
