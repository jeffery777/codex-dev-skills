# Issue #253：儲存故障證據與未完成條件

2026-09-11 的有界合成驗證。source/package 為 `catalog.yaml` 的 0.24.2；
沒有 production code 變更、正式來源／人類確認入口或新的 qualification。
[#245 歷史物理觀察](../issue-245/enospc-observations.json)及
[#247 readback 契約](../issue-247/process-loss-contract.md)保持原貌。

## 實際結果

[結構化對照](controlled-observations.json)綁 Python 3.12.9、SQLite source ID／compile
options、schema／SQL、實際 source SHA-256，以及每個案例的前後 digest、proof、
current projection、回覆分類、只讀檔案摘要與程序分離。
每個案例建立自己的 Git repository／SQLite root；正常 add 後嘗試更新為不同 cue
與較大 payload。這些 ports 的 source approval／confirmation／budget 是明確的
synthetic TCB，不能作為正式 host 資格。

| 情境 | 實際錯誤與結果 | 新程序讀回及一致性 |
| --- | --- | --- |
| 正常對照 | 無 SQLite error；更新 applied | 最新 proof／revision 2／green projection 一致；舊 add 保留 proof、回 unknown。 |
| Page quota | 真正 SQLite error 13 `SQLITE_FULL`；降低該 writer 的 max_page_count，沒有填滿 filesystem | 原程序有 preview，回 not-applied；fresh ID-only reader 沒有 proof，維持 state-unknown。完整前態、revision 1、blue projection 與原 normal proof 一致。 |
| Missing-path 對照 | 真正 SQLite error 14 `SQLITE_CANTOPEN`，原因是測試自己的不存在路徑 | 前態及原 proof 一致；不稱為物理空間不足或 FULL。 |
| 提交後回覆遺失 | checkpoint 注入 errno 28，不是 OS 容量實驗 | commit 的 proof／revision 2／green projection 一致，fresh readback applied；不因例外推定未提交。 |
| Before-commit 程序中斷 | 自己的子程序退出 73，留下非空 journal | readback unknown；audit 在開 DB 前拒絕 recovery-required；讀回前後所有 managed/source files 的 identity／mode／mtime／完整 bytes digest 不變。未證明資料恢復。 |

所有已觀察完成的案例都拒絕原程序 consumed handle，以及 fresh core 上以 operation
ID 建造的無效 handle。quota／CANTOPEN 後另外取得**新 preview 與新 confirmation**，
以不同 operation ID 完成 revision 2 的正常更新，再由另一程序只讀驗證。這是故障後
的正常對照，不是重播原請求；readback 本身不呼叫 accept、不產生變更權限。

「實驗核對前態相同」與 core 的 ID-only result 分開：fixture 擁有自己的前態證據，
可檢查無部分寫入；fresh caller 沒有原 preview，不能因此把 unknown 改成 not-applied。
非空 journal 情境則連完整前態都不可讀，保留 incomplete，沒有手動刪 journal、
RW reopen、repair 或 G2 maintenance。
Synthetic CLI 現在保留每次新建的 fixture，輸出 `retained_fixture` 並以 exclusive
create 寫入 `observation.json`；程序退出後仍保留 incomplete journal。單元測試的
外層 `TemporaryDirectory` 只管理自己新建的測試資料，生命週期與 CLI 分開。

## 物理 APFS 實驗

[物理實驗報告](physical-observation.json)記錄一次新建 256 MiB APFS image 嘗試：

- Host 可用空間在建立前為 337,946,185,728 bytes，通過至少 1 GiB 保留加映像預算。
- `hdiutil create -size 256m -fs APFS -layout NONE ... -type UDIF` 回 exit 1，
  stderr 為 `hdiutil: create failed - 尚未設定裝置`。
- attachment_state 為 not-attempted；沒有映像、mount、Git／SQLite root 或 filler
  寫入，保留目錄內只有 observation.json。不存在需要 detach 的已確認 attachment。
- 本輪沒有實際 OS ENOSPC，也沒有物理 SQLite FULL、CANTOPEN 或釋放容量後的
  readback 證據。不能用上述 quota、missing-path、注入或舊 #245 樣本替代。

失敗發生在 image-create；精確底層原因未確認，不能直接歸因於 sandbox、權限或
APFS。未重試、未提高映像上限、未更換 filesystem、未擴權或操作舊映像。
實作預設 dry-run；成功 attach 後還須驗證回應中的 device node、diskutil 的
filesystem／mount／容量、獨立 device 與 inode，才將自己的 filler fd 傳給 worker。
filler 總寫入最多 256 MiB，固定三種 block size、30 秒 loop deadline／90 秒
worker timeout；回收子程序與 fresh reader 各 30 秒，hdiutil／diskutil 各 60 秒。
只截短同一個已核對 filler，正常 detach 一次、保留映像；不 force、repair 或 broad kill。

下一個有界物理驗證由後續 G1 storage owner 負責：先釐清這個環境的受支援 image
建立條件與必要授權，再在**全新**映像執行同一 fixture 一次。若仍須擴大資源或改變
恢復策略，先交回具體取捨。若留下非空 journal，另交 G2 maintenance 契約，不擅自
取得讀寫開庫或清除授權。這些是 production qualification 的 blocking 缺口。

## J／T／G 與鎖定量測

正常對照為 1 item、2 retained versions、2 proofs，294 次取樣：

| 量測 | 測得最大值／區間 | 能支持的範圍 |
| --- | ---: | --- |
| Main logical length／allocated bytes | 61,440／61,440 bytes | 該 workload 的觀測，包含 payload、projection、proof、metadata／SQLite pages。 |
| Rollback journal length | 41,552 bytes | J 的取樣最大值；不是已證明上界。 |
| 去重的 file-size aggregate | 90,704 bytes | 逐筆 stat／fstat 的單次取樣加總；非 atomic snapshot，不能聲稱連續時間的同時峰值。 |
| Named temp、其他 named sidecar、unlinked fd、其他 fd | 各 0 bytes | 受測程序的取樣結果；不表示從未建立或不存在記憶體 temp。 |
| Add 完整持鎖區間 | 114,117,250 … 114,125,583 ns | 該次鎖的上下界，包含 instrumentation；非 workload 最壞時間上界。 |
| Update 完整持鎖區間 | 191,117,667 … 191,126,083 ns | 同上；包含 source 查核、entry／exit inventory 與獨立 readback。 |

Observer 包裝成功的 flock 呼叫與該 lock fd 的 close 呼叫，不改 production lock
程式。真正取得／釋放位於各 syscall 前後 timestamps 之間，因此下界為
release-before − acquire-after，上界為 release-after − acquire-before。
測試在 post-acquire entry inventory 與 exit inventory 內用另一 file description
實際競爭鎖，兩處皆 busy；兩段受控延遲均包含於量測區間。
這補足 #245 context-body-only 的缺口，不改寫舊數字。只測此兩個 mutation 與其
preview 的完整鎖區間；初始化、任意 workload、4 GiB 與 power-loss 不在量測中。

所有大小值來自 checkpoint、connection 邊界、lock 邊界及每 50 SQLite VM operations。
新的獨立 worker 將自身 fd soft limit 限為 128，close_fds 僅留下 stdio 及物理模式的
own filler；逐次 census 查自己 3…127 的 regular-file metadata，包含已 unlink 但仍
開啟的檔案，不讀內容或查其他程序。main／journal 的 named 與 fd identities 去重。
filler 不屬 SQLite envelope，明列 excluded。Sampler 發生錯誤不准回乾淨 observed。
回歸用已知 17／23／31／47 bytes 的 WAL、SHM、named temp 與 unlinked own file
驗證計數。這些是 instrumentation 正例，不是合法 production WAL／SHM。

| SQLite 類別 | 本包 coverage／限制 |
| --- | --- |
| Rollback journal | Named stat + fd census，觀察到 DELETE journal；短暫峰值仍可能漏取樣。 |
| WAL／SHM | 固定 DELETE profile 排除，managed inventory 遇到它們即拒絕；observer 另有精確 byte 計數對照。 |
| Super-journal | 固定 SQL 不 ATTACH，連線 attached limit=0；不測多庫交易。 |
| Statement journal | 視 statement／build 而可能使用；named temp + own fd census，記憶體與取樣間隙未覆蓋。 |
| TEMP database | 固定 SQL 沒有 CREATE TEMP；未另跑 TEMP workload。 |
| View／subquery materialization、transient index | 查詢可能需要暫存；目前樣本沒有觀察到 disk temp，記憶體與短生命週期仍未知。 |
| VACUUM transient database | G1 固定 SQL／能力排除，不以其他工作負載補造本包 coverage。 |

SQLite 對暫存檔實作不作跨版本承諾；writer 的 temp_store=MEMORY 也不能排除所有
磁碟暫存。唯讀 connection 沒有在本包改寫 pragma，不能假設每個 connection 都
採 MEMORY。來源：[SQLite temporary files](https://www.sqlite.org/tempfiles.html)、
[result codes](https://www.sqlite.org/rescode.html)及
[max_page_count](https://www.sqlite.org/pragma.html#pragma_max_page_count)。
尚缺完整連續 temp 集合、完整 J/T/G 上界、profile 最大負載、maintenance reserve、
4 GiB worst-case lock time 與 power-loss qualification；不將觀測寫入 qualification registry。
獨立 `sqlite-temp` 環境設定及 observer 只涵蓋 create worker。fresh reader／control
另起程序並繼承 coordinator 環境，其 temp 路徑與 temporary 資源沒有在本包量測。
`runtime_facts` 的 `temp_store=memory` 是 writer profile 宣告，不是所有 connection
的有效 pragma 讀回；因此不以該欄位消除上述缺口。

## 重跑命令與 gates

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_memory_governance_contract tests.test_memory_governance_core \
  tests.test_memory_governance_faults tests.test_memory_governance_local \
  tests.test_memory_governance_local_faults tests.test_memory_governance_process_readback \
  tests.test_memory_governance_storage_faults
./scripts/project-python tests/fixtures/memory-governance/storage_fault_case.py --fault page-quota
./scripts/project-python tests/fixtures/memory-governance/storage_fault_case.py --fault missing-path-cantopen
./scripts/project-python tests/fixtures/memory-governance/storage_fault_case.py --fault none
./scripts/project-python tests/fixtures/memory-governance/storage_fault_case.py --fault reply-loss
./scripts/project-python tests/fixtures/memory-governance/storage_fault_case.py --fault precommit-loss
./scripts/project-python tests/fixtures/memory-governance/enospc_image.py
./scripts/project-python scripts/test-shards.py run-all
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python scripts/validate-release-state.py
git diff --check
```

Precommit-loss 預期 exit 2／incomplete，禁止為取得零退出碼移除 journal。
物理 --run 是另外的資源操作；上述 dry-run 不會建立映像。
新測試已加入 memory shard；首次 run-all 在執行任何 shard 前拒絕未排序的 module
清單，修正排序後重新執行。focused 101 tests 通過（45.118 秒）。
主代理自查後補上 quota 分類證據必須為正整數且原 profile quota 較大的條件，
拒絕缺失／None／bool／未降低 quota 的來源推定；相關 14 tests 再次通過
（10.385 秒），當時五個對照以全新 synthetic roots 重跑。物理 image driver
未變更，沒有重跑物理實驗；本頁數值採下述審查修正後的新觀察。
審查前完整 deterministic shards 已通過：12 shards／1,206 tests，程序 exit 0。
[本機驗證紀錄](local-verification.json)列出各 shard 結果、耗時、log digest 與
相關 fixture／test／manifest 的 source digest。memory shard 在分類修正後開始，
其 337 tests 包含當時的程式與回歸案例；這些本機結果不代替獨立 review 或 hosted CI。

## 審查修正與 gate 證據

離線 `validate-repo.sh --skip-unit-tests`、122 份 generated package parity、
source/package 0.24.2 release-state 與 diff hygiene 已通過；對照報告綁定的
11 份來源 SHA-256 與本 worktree 相符。審查前完整 deterministic 12 shards／1,206 tests 通過。

獨立 code/deep/docs review 的三項意見皆已修正，保留原 ID 與處置：

| Finding | Disposition | 修正與驗證 |
| --- | --- | --- |
| SR-253-01（MUST-FIX） | Fixed | 三次 fresh reader 統一要求 exit 0、未 timeout、獨立程序、事件存在及檔案不變。新確認 control 自身也要求未 timeout；負例在真實合成讀回事件後，分別注入非零退出及 timeout，三個位置都維持 incomplete。 |
| SR-253-02（SHOULD-FIX） | Fixed | Physical FULL 分類要求三個 quota 欄位都是正整數、effective 等於 profile 且餘裕大於 256 pages；缺失／None／bool／零／負值／字串維持來源未證明。 |
| SR-253-03（SHOULD-FIX） | Fixed | CLI 保留新建目錄及報告；新 subprocess 回歸確認 exit 2 後 journal 仍存在且非空，報告與 stdout 一致。 |

修正後 focused 16 tests 通過（22.485 秒）；五個控制案例以全新 synthetic roots
重跑，更新 source digest 與本頁數值，並保留本次證據目錄。首次 12-shard 結果保留
原 digest；修正後 memory shard 的 339 tests 通過（77.836 秒），另記於
`local-verification.json`，不將舊驗證重綁為新程式。未受影響的其他 11 shards
沿用原證據，共覆蓋目前 1,208 tests；離線 validation 也再次通過。

第一輪 Security Diff Scan 已完成，15 份變更、零 reportable findings，且明確保留
上述內容審查修正需求。原生與文件化 helper 預設排除 tests／docs／Markdown，
主代理核對原因後用 live Git 與 content-bound manifest 補入完整授權清單並讀回。
這個掃描結果只對應修正前的固定差異；修正後仍須相應重審及 Security Diff Scan。

正式 commit gate 以當次 diff 綁定的獨立 review／Security Diff Scan artifact 判定。
PR readiness 另須完整 base-to-head exact-head content review、hosted CI、strict
receipt／readback、dedicated App 與平台 gate。本頁的歷史觀察與測試不是 gate receipt。

Source/package 0.24.2 不變；candidate preparation 不新增；publication truth 未查核且
不宣稱發布狀態；active guidance 維持 partial G1；historical records 保留。
本包唯一 implementation writer，commit／PR／receipt 已授權，merge／tag／Release／
安裝／部署未授權。production registry 仍不可變空映射、default-off；G2/G3 尚未完成。
