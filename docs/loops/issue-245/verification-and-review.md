# Issue #245：驗證、觀察與剩餘資格

2026-09-10 的本機 synthetic 證據；此紀錄不授予 production、merge、發布或安裝權限。
正式 review／Security Diff Scan／PR exact-head receipt 另綁各自的內容身分。

## 交付與測試邊界

新增 `memory_governance_local.py`：實際 UTC／monotonic clock 與 PID 綁定、host-owned
單 root registry、初始化後獨立 device/inode/owner/mode 讀回，以及明確的
source／authority／qualification port 組合。RepositorySource 檢查固定 artifact
的完整 bytes、SHA-256 與 scope/revision/path，但不能以 bytes 相同代替來源支持或
敏感性審查。reader／reviewer／人類確認／儲存 qualification 仍屬受信任 host 邊界。
通用 Git reader 不交付；只有 fixture 會讀自己新建 tiny repository 的固定 blob。

兩個新 test modules 共 19 項，涵蓋 audit、preview、add、update、restore、stop、
resume、10 versions 上限、current-only projection、確認拒絕／過期／重播、來源
bytes／revision／repo/path／狀態／verifier 漂移、來源撤銷、revision conflict、
qualification／budget 漂移、readback authority 撤銷與三個獨立 SQLite connections。
原 production registry 仍是不可變空映射；CLI、G0/M1 public contract 未變。

新 subprocess fixture 在四個 checkpoint 以退出碼 73 結束自己的程序。父程序
僅收到 operation ID／preview digest／原 host 檔案 identities，不保存完整 preview
或 mutation handle。重新開啟不修改檔案、不恢復 journal；precommit 為 unknown，
after-commit 有 proof，但失去獨立來源接受後為 committed-but-not-adoptable。
另一個來源接受仍有效的 reopen 測試明確驗證：原 preview 遺失時只回 proof／unknown。
這保留 #235 的限制，沒有宣稱只靠 operation ID 即可恢復 applied。

## 固定環境的小型量測

[原始結構化觀察](local-observation.json)保留 SQLite source ID／compile options、
Python 3.12.9、Darwin 25.6.0、APFS、schema／SQL／profile digest。runtime digest：
`0287102d35e966ca473db24ed1c12144d02d7b1206937d48524c1ddd2e003207`。
workload 為 1 item、10 retained versions、12 proofs；不是完整容量壓力測試。

| 觀測 | 結果 | 可支持的結論 |
| --- | --- | --- |
| main 最大長度 | 217,088 bytes | 此 workload 的取樣最大值。 |
| DELETE journal 最大長度 | 57,968 bytes | 不等於 qualified J 上界。 |
| managed／total 同時峰值 | 258,672 bytes | 非各檔案獨立最大值相加；仍是取樣下界。 |
| test temp 目錄最大值 | 0 bytes | 只涵蓋此目錄；外部／unnamed temp unknown。 |
| 持鎖 context body 最大量測值 | 102,951,334 ns | 含 instrumentation 與 fresh readback；僅為完整持鎖時間下界。 |
| 取樣 | 216 次 | checkpoint 及每 50 SQLite VM operations；不是連續追蹤。 |

持鎖計時從 `db.locked` yield 後開始，在 context body 結束時停止；未涵蓋
鎖取得後的 entry inventory、exit inventory 及 unlock 前尾段。此值不是精確完整
duration，也不代表 4 GiB 最壞延遲上界。sampling metadata 的
`lock_timing_scope: context-body-only` 記錄這項限制，既有數值未改。

SQLite 文件區分 [page-count 限制造成的 SQLITE_FULL](https://www.sqlite.org/limits.html)
及[多種暫存檔行為](https://www.sqlite.org/tempfiles.html)。temp_store=MEMORY 不能
單獨證明全部 temp 集合有界。本次數值不會寫入 production qualification registry。

## 空間不足與恢復結果

deterministic 測試分開驗 fstatvfs 准入前拒絕、test-only max_page_count 導致真正
SQLite error 13／SQLITE_FULL，以及 checkpoint 注入 errno 28。page quota 並非
物理磁碟耗盡；after-commit reply loss 仍需獨立 readback，不能盲重播。

手動 macOS fixture 預設 dry-run；明確 `--run` 才新建 256 MiB APFS image。
不接受既有 volume，先核對獨立 device／mount、至少 1 GiB host headroom；只填
自己的 filler，總上限 256 MiB；不 force detach、不修復或刪除 managed files。
[兩次結構化結果](enospc-observations.json)已去除機器私有暫存路徑。

| 實驗 | 已觀察結果 | 判定 |
| --- | --- | --- |
| 1 MiB filler allocations | errno 28；SQLite applied、有 proof；正常 detach | 不能證明 SQLite 空間失敗，incomplete。 |
| 逐步降至 4 KiB | 各級 errno 28；SQLite CANTOPEN 14、not-applied、無 proof、前態匹配 | 實際 ENOSPC 已觀察，但物理 SQLITE_FULL 及完整恢復未證明。 |
| 第二次恢復 | 截短自身 filler 也回 errno 28；仍正常 detach | 映像保留、未 force／repair，整體 incomplete。 |

最初另有一次 `hdiutil create -format` 參數錯誤，在 attach 前失敗；依本機 help
改成空白可讀寫映像的 `-type UDIF`。這不是 ENOSPC 樣本。沒有將任何失敗試驗改記 PASS。
SQLite CANTOPEN 的底層 errno 沒有直接捕捉，不能推論所有同類 CANTOPEN 都由空間造成。

## 審查與再驗證

獨立 advisory 修正三項 image fixture MUST-FIX：只認可確切 SQLite FULL 才算
預期空間失敗、filler recovery 例外不跳過 detach/report、attach 回覆不明時保留
unknown 及 recovery-required。之後的實測 CANTOPEN 因此正確保留 incomplete。
正式 code/deep/docs gate、Security Diff Scan 與其 finding dispositions 另記固定 diff。

`CR245-SF-LOCK-TIMING-SCOPE` 的修正僅補上述 context-body-only 範圍與結構化
sampling 註記，不重跑映像、不改量測數值，也不將下界升為完整持鎖 duration。

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_memory_governance_local tests.test_memory_governance_local_faults
./scripts/project-python scripts/evaluate-memory-governance-local.py
./scripts/project-python tests/fixtures/memory-governance/enospc_image.py
./scripts/project-python scripts/test-shards.py run-all
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python scripts/validate-release-state.py
git diff --check
```

## 剩餘工作與版本判定

| 後續目標 | Owner／觸發條件 | 所需證據 |
| --- | --- | --- |
| G1 production host qualification | 後續 G1 delivery owner；任何真實入口前 blocking | 正式 human preview acceptance、source reader/reviewer/revocation、受保護 registry 與 readback authority。 |
| G1 process-loss contract | 後續 G1 contract owner；要承諾 ID-only applied 恢復前 blocking | 接受的 external-copy/preview 恢復契約；不得偷偷保存 synthetic preview 補造。 |
| G1 storage qualification | 後續 G1 storage owner；任何 production qualification 前 blocking | 完整 temp／J/T/G 上界、實際 ENOSPC/recovery、power-loss、4 GiB 最壞 lock time 與 maintenance reserve。 |
| G2／G3 | 各獨立交付 owner；實作／整體資格前 | 接受的 erase/purge/compact/recovery、殘留與外部副本覆蓋；不在本切片開啟。 |

上述是範圍外的資格缺口，採 default-off／空 registry 控制風險，不是假稱已關閉的
finding。M1 logical delete、#222 原始 finding、#188 cleanup 與 #242／PR #244 無變更。

Source/package 的 canonical version 為 catalog.yaml 0.24.2，本切片不改版。
Candidate preparation 不新增；publication truth 未查 tag/Release、不聲稱發布狀態；
active guidance 明示部分 G1／未 qualified；historical records 保持原點時內容。
發版價值為開發用整合與可重跑故障證據，尚不足單獨宣稱 production memory 功能。
實際 merge、tag／Release、安裝／部署另核對當次授權與適用 gates。
