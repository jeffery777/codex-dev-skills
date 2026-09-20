# Issue #271：實體容量恢復與未完成驗收

## 結果與限制

本包實際完成一次新建 256 MiB APFS image 的 OS ENOSPC、own filler 截短、
容量釋放與 fresh readback；正常 detach 後保留映像。SQLite 在該次條件下
成功提交，沒有 physical SQLite FULL，因此整體驗收仍為 **incomplete**。
[去識別實體摘要](physical-observation.json)與本地原始觀察分開保存。
不能以 OS ENOSPC、page quota FULL 或合成測試代替缺少的 physical FULL。

## 環境與最小修正

獨立 worktree 依原專案 venv 的 interpreter 來源，新建自己的 Python 3.12.9 venv，
經 tracked resolver 確認版本後安裝 requirements 的 PyYAML 6.0.3；沒有複製 venv
或修改全域設定。測試入口均使用 `./scripts/project-python`；完整 shards 初跑仍發現
installer 內部呼叫 `python3` 時選到系統 Python 3.9.6，因缺 `tomllib` 等依賴失敗。
驗證程序以本 worktree 的 `.venv/bin` 作 PATH 前置後重跑受影響 shards；
installer-agent-profiles 的 62 項已通過。這是子程序環境修正，不是本包修改 installer。

相同公開唯讀查詢在一般執行環境回報無法使用 DiskManagement framework，
透過正常核准介面則成功；後者的 `hdiutil info` 亦返回有效結構。
這是本次執行環境差異的證據，不是 #265 歷史初始化失敗的完整根因證明。
沒有重播 #265 的 create，沒有重啟服務、修改 sandbox 設定或切換 host。

`enospc_image.py --preflight` 新增唯讀服務／headroom 檢查；`--run` 先做相同檢查，
失敗在建立新 trial root 前返回 incomplete。preflight ready 只表示查詢可用，
不保證 image create 成功。command timeout、完整參數與有界 stdout/stderr 診斷
沿用既有本地證據格式。截斷 XML 也回 incomplete，不以未捕捉例外遺失結構化結果。
沒有 production core、installed package 或 qualification registry 變更。

## 唯一一次物理觀察

先保存精確 resource preview，核對新 image／mount 不存在。沿用 GPTSPUD、APFS、
UDIF 配置；create、attach 成功後核對 image inode、exact-image attachment、
獨立 device、mount inode、APFS type 與容量上限，再建立 own filler。
本次總共一次試驗，沒有擴容、retry、repair、force detach 或舊 volume 操作。
host headroom 的建立前／後及最終取樣均符合門檻；這些取樣不保證連續容量下界，
也沒有為 host 預留不可被其他 writer 使用的空間。

| 觀察 | 可支持的結論 |
| --- | --- |
| filler 寫入 260,046,848 bytes；1 MiB、64 KiB、4 KiB 各遇 errno 28 | OS 對 own filler 寫入回報 ENOSPC；不是 SQLite error 13。 |
| SQLite errors 空集合；max_page_count 維持 profile 1,048,576，原 page_count 12 | 沒有 page-quota 注入；本次 update applied，不能宣稱物理 FULL。 |
| own filler 截短至零並 fsync；可用容量增加 | 容量釋放已觀察，未做 DB／journal repair。 |
| fresh readback applied、revision 2、green 1／blue 0、proof 與完整 state digest 相符 | 提交內容與 current projection 一致；讀回前後 fixture 檔案未變。 |
| 歷史 add 為 state-unknown 且保留原 proof；原／重建 handle 均拒絕 | 未把較早操作錯判為當前 applied；沒有重播。 |
| 正常 detach 成功；事後 exact-image attachment 零匹配，image inode 及大小符合 | 本包映像保留，沒有仍附掛的 exact-image 關聯。 |

writer 90 秒、fill loop 30 秒、restore／reader 各 30 秒、外部命令各 60 秒的既定
上限未放寬。writer／restore／reader 均未 timeout。fresh reader 有自己的 authority，
不呼叫 accept；沒有非空 journal。因為原交易沒有失敗，既有協調器不啟動
「失敗後取得新 preview／confirmation 的 control」，此項明確未測。
本次沒有證明為何 SQLite 在 filler ENOSPC 後仍可提交，不能把推測當成 APFS 保證。

## 驗證與審查

- 原有 storage-fault focused tests：23 項通過。
- 新 preflight focused tests：完整模組 26 項通過；修正 XML 回報後的
  `ImageSafetyTests` 11 項通過。
- 獨立試驗前 deep review：1 項 SHOULD-FIX（PR-271-01：損壞 XML 未捕捉）已修正，
  再審無新增 finding；沒有阻止既定一次試驗的 safety blocker。
- checks-only repo validation、126 檔 package parity、offline release-state 與 diff hygiene 通過。
- Security Diff Scan 對七個變更檔案完成審閱，無安全 findings；自動 inventory 的
  tests/docs 排除已依明確範圍補入，沒有把零項清單當成完整覆蓋。
- 完整 shards、最終文件再審與 PR head 結果保存在 PR 的精確版本證據；
  本試驗紀錄不替代 commit／merge gate，尤其不把初跑的環境失敗算作通過。

可重跑的無物理故障檢查：

```bash
export PATH="$PWD/.venv/bin:$PATH"
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python tests/fixtures/memory-governance/enospc_image.py
./scripts/project-python tests/fixtures/memory-governance/enospc_image.py --preflight
./scripts/project-python -m unittest tests.test_memory_governance_storage_faults
./scripts/project-python scripts/test-shards.py run-all
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python scripts/validate-release-state.py
git diff --check
```

preflight 在服務不可用時預期 exit 2。`--run` 不屬以上重跑集合，本包一次額度已用完。
原始診斷、host capacity、OS／device／mount／inode／PID／私有路徑只留本地。
公開 summary 採固定白名單，含 source digests 與 SQLite runtime facts；局部取樣
不證明完整 J/T/G、temp envelope、4 GiB 最壞延遲、maintenance reserve 或 power-loss。

## 發版與剩餘責任

不另發版：本包只有 repository-only fixture／tests／證據，沒有可安裝行為或
對使用者開放的新能力。source/package 依 catalog 保持 0.24.7；不新增 candidate、
不改寫 historical release notes。bootstrap 平台讀回的 annotated v0.24.7 tag object
`934d1c0aa985e3a3568a914bbcf19287cf182866` 解參照至基準
`aedfdb124b996eb1626999bcbdda0f31abe2382d`，同名正式 Release target 相同且
draft/prerelease 皆 false；此為點時 publication evidence，非 active guidance 的最新版本指標。

Issue #271 保持 open／部分完成。G1 storage owner 尚須取得 physical SQLite FULL
與該失敗後的 fresh-authority 正常 control；下一次物理試驗需先有新的有界方法、
資源／風險預覽及明確新增試驗授權，不重設本包 attempt limit。非空 journal 的
recovery 仍屬 G2。完整 G1/MG1 qualification、真實 host/source authority、完整
容量與延遲上界均未完成，default-off／空 production registry 不變。

repository 的 ready-PR gate 要求關閉 Issue 的引用；本包不能宣稱 #271 完整完成，
因此交付以 draft PR 保留可審查成果，不添加會自動關閉 #271 的文字、不繞過 gate。
這是部分交付與 merge gate 的限制，不表示可以省略內容審查或安全掃描。
