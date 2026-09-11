# CLI fork EPERM 調查 — 2026-09-11

追蹤：[Issue #251](https://github.com/jeffery777/codex-dev-skills/issues/251)。
本次核對 main `b7d245646568c0397f5c516e2f6972f1b4e91fa1`，
[PR #250](https://github.com/jeffery777/codex-dev-skills/pull/250) 已合併、
Issue #249 已關閉。保留 [#249 的點時證據](codex-runtime-compatibility-evidence-2026-09-11.md)
及 [09-04 歷史紀錄](codex-runtime-compatibility-evidence-2026-09-04.md) 原貌。

## 結論與證據層級

**根因未確認，standalone fork 尚未完成本輪 live qualification。**
公開資料有 macOS 沙箱／程序觀測回報，但沒有與本案失敗位置一致、且已確認
修復版本的證據。沒有找到 fork 棄用公告，也沒有證據支持修改 production
adapter 的拒絕政策；本次僅補測試失敗診斷及調查文件。

- 使用者回憶：「之前其實沒有這問題，而是更新之後才出問題」。這是回歸假說，
  缺少相同 OS、外層 context、adapter、binary 的更新前後配對量測。
- 已保存的舊 fork receipt 確認 `termination_error`、
  `stage=child-identity; errno=1`；session call 已開始，UUID／exit／terminal
  均未知。不能視為未建立 session、模型 turn 失敗或已完成。
- 本輪新 fixture 的 start 收到 `nonzero_exit`、exit 1，UUID／terminal
  未取得；程序觀測沒有回報相同錯誤。首個失敗後停止，未執行 resume／fork。
  Receipt 不保留原始 stderr，不能將此 exit 1 歸因於 installation ID、網路
  或先前 EPERM，也不能聲稱已重現原 fork 故障。
- 所有成功樣本只證明其量測範圍；後續成功不抹除失敗，公開 help 不等於 live
  completion，較新版本或 bundled 成功也不替另一入口建立資格。

## 版本時間線與可比較矩陣

本輪直接量測於 2026-09-11：macOS `26.6.2`（`25G83`）、
Darwin `25.6.0` arm64；Desktop `26.903.71938`（build `8576`）。
Standalone `0.154.0`、bundled `0.153.4` 的 version／digest 與 #249 相同。

| 證據時間／adapter | Standalone | Bundled | Desktop／外層 context | 操作與觀測 |
| --- | --- | --- | --- | --- |
| 09-04 歷史紀錄 | 0.153.2 | 0.153.0 | 26.901.22334／7746；OS、同等外層證據不足 | 公開 help 通過；明載未跑 live session，不能當更新前成功對照 |
| #249 原 adapter `ecd5ac31` | 0.154.0 | 0.153.4 | 26.903.71938／8576；保存的 receipt 未綁定完整外層 context | standalone start/resume/fork PASS；bundled start PASS、resume generic termination_error、fork 未跑 |
| #249 補強後 `eb60cb6c` | 0.154.0 | 0.153.4 | 同上；read-only child/private clone | bundled 三項 PASS；standalone start/resume PASS、fork child-identity EPERM；該 fork UUID／exit／terminal 未知 |
| #251，未改 production adapter `eb60cb6c` | 0.154.0 | 0.153.4 | Desktop `exec_command` use_default、外層 workspace-write；上述 OS | standalone 64 tests 最終 PASS；bundled 3 項公開 help PASS；新 standalone start exit 1，後續兩項未跑 |

`#249` 兩組使用同一 standalone 版本卻有不同觀測；這不支持「該版本必定無法
fork」的推論，也不足以排除間歇性回歸。沒有安裝或切換舊 binary，因此沒有
控制其他變因的升／降版實驗。外層 sandbox 與 CLI child 的 read-only sandbox
是兩層；不能因 child 參數相同就假定外層也相同。

完整 SHA-256：

| 對象 | SHA-256 |
| --- | --- |
| standalone executable | `4f85982624b3898c8991cb80c0981b2aa71070e3537046c9a95950318a95afcc` |
| bundled executable | `87a08119b8effa519f0ecb552dc98043f58a8200bf2ec5da60f76890c33e9c3a` |
| 本輪 production adapter | `eb60cb6ce74e0e39ee1ebbef0112fbe873e33412d77ea5e89275d123637d198a` |
| 舊 standalone fork receipt | `311264172860b89ef55d8d9cbf041a42b7fc7edb28039294ab708e10376d1332` |
| 本輪 standalone start receipt | `1b64b9f5d8d0db0ac7d2dcc8dbde790d015c1b34cb00609122dfe62557699866` |

Receipt digest 是點時稽核識別，並非可取得私人 session 的索引或重試授權。

## 公開回報與維護者處置

2026-09-11 06:18 UTC 透過 GitHub connector 查核 Issues、comments、timeline、
releases 及 PR patches。涵蓋 open／closed；搜尋 `EPERM`、`fork`、`libproc`、
`sysmond`、`proc_pidinfo`、`proc_pid`。後兩個精確詞未找到 Issue，
不能據此推定不存在未提報或不同措辭的回歸。以下均為第一手回報；提報者的
根因推論與 proposed fix 不自動成為維護者確認。

| 來源 | OS／版本／失敗位置 | 狀態與本案關係 |
| --- | --- | --- |
| [#23505](https://github.com/openai/codex/issues/23505) | Darwin 25.3 arm64、CLI 0.131.0；`ps/pgrep` 報 sysmond service not found | open；單一非維護者留言，沒有已接受修復。程序觀測相關，但 Mach service lookup 與直接 `proc_pidinfo` 的同根因未建立 |
| [#35482](https://github.com/openai/codex/issues/35482) | Darwin 25.5 arm64、Desktop 26.721.41059／bundled 0.146.0-alpha.3.1；exec 遺失仍存活 child，後續 pgrep 失敗 | open；留言未提供維護者修復結論。支持保留生命週期 unknown；原操作是 zip，並非 session fork |
| [#42398](https://github.com/openai/codex/issues/42398) | macOS 27 arm64、CLI 0.151.0；nested exec startup 的 installation_id writable open EPERM，尚未 JSON／model turn；0.152.0 僅 source inspection | open；三則留言均非維護者。有人[自述個人 fork 修正](https://github.com/openai/codex/issues/42398#issuecomment-5520095365)，沒有 upstream merged fix；失敗階段不同 |
| [#6960](https://github.com/openai/codex/issues/6960) | macOS/Homebrew，使用者描述 0.59→0.60 後 login-shell 的 ps 被拒 | closed/completed；[維護者說明](https://github.com/openai/codex/issues/6960#issuecomment-4150516517) 是久無新回報並認為已處理，未指定修復版本。確有更新後案例，但不能套用到本案 |
| [#22405](https://github.com/openai/codex/issues/22405) | macOS，版本未提供；ProcessPoolExecutor spawn 前 sysconf 的 errno 1 | closed/completed，沒有連結修復 commit；不同 syscall |
| [#28894](https://github.com/openai/codex/issues/28894) | macOS 26.5.1、CLI 0.141.0；workspace 外 stat/open EPERM | 提報者自行 closed，後續仍有人回報；不同檔案讀取階段，closed 不等於已修 |

[Windows #37458 的已修公告](https://github.com/openai/codex/issues/37458#issuecomment-5287557175)
明指 extension startup watchdog 與版本 `26.810.41047`，OS／操作／位置不符，
不列為本案修正版。Linux pids.max/EAGAIN、fork cache、TUI backtrack 回報同樣
不能僅因搜尋包含 fork 就視為 EPERM 證據。

## 官方版本與候選 PR 的實際範圍

[0.153.4](https://github.com/openai/codex/releases/tag/rust-v0.153.4)
於 09-04 23:25:48Z 發布 stable；說明為 model picker／async-question hotfix。
[0.154.0](https://github.com/openai/codex/releases/tag/rust-v0.154.0)
於 09-09 22:35:38Z 發布，查核時 releases/latest 指向此版，
`draft=false, prerelease=false`。仍列 fork/worktree 功能與修復；移除的是
deprecated `codex mcp-server`。
[0.155.0-alpha.3](https://github.com/openai/codex/releases/tag/rust-v0.155.0-alpha.3)
於 09-11 02:35:52Z 發布 prerelease，說明沒有本案修復證據；不是已驗收替代品。
這些是查核時的出版狀態，不改 `catalog.yaml` 的 source/package 版本。

[官方 changelog](https://learn.chatgpt.com/docs/changelog) 與
[CLI reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
已讀取；docs MCP 的 changelog markdown 回 404 後改讀官方網頁。
Reference 缺列某個 exec 子命令不等於棄用；本機兩個 binary 的 exact fork
Usage shape 均通過公開 help 檢查，穩定性承諾仍依既有 CLI reference 區分。

已逐檔讀取下列 patches，並分頁核對
[0.153.4...0.154.0 compare](https://github.com/openai/codex/compare/rust-v0.153.4...rust-v0.154.0)。
Compare 為 diverged、249 個 head-side commits；五個候選均在該範圍，不能將其
描述成單純直線升版。它們沒有直接修改 adapter 或 proc_pidinfo：

| PR | 實際修改位置／判讀 |
| --- | --- |
| [#42590](https://github.com/openai/codex/pull/42590) | `cli/src/debug_sandbox.rs` 的 sandbox command 加 TIOCSTI file-ioctl deny；沒有改 shared Seatbelt 程序查詢 allowlist |
| [#42192](https://github.com/openai/codex/pull/42192) | `rmcp-client/src/macos_stdio.rs` 的 bare MCP child native posix_spawn／PATH 搜尋；不等於外部 Python 啟動絕對路徑 CLI 的觀測路徑 |
| [#43330](https://github.com/openai/codex/pull/43330) | TUI remote resume/fork 的 saved permission overrides；不是 noninteractive exec 的 native process inspection |
| [#43355](https://github.com/openai/codex/pull/43355) | TUI SessionSelection::Fork／ThreadForkParams 的 implicit model/effort；沒有 PID/errno 邏輯 |
| [#43478](https://github.com/openai/codex/pull/43478) | history／rollout reconstruction 保留 Guardian instructions；standalone root thread 不等於 standalone 安裝通道，也不是 OS fork |

這排除了「僅由上述 PR 標題即可確定根因」的推論，沒有排除其他 upstream
變更或間歇性時序問題。0.154.0 的
[installation ID resolver](https://github.com/openai/codex/blob/rust-v0.154.0/codex-rs/core/src/installation_id.rs#L19-L32)
仍先要求可寫 open；只支持 #42398 的 source 假說，不證明本輪 exit 1 原因。

## 本機觀測路徑與最小診斷

`ProcessTreeTracker.capture → _direct_child_pids → _process_identity` 在
child-identity 呼叫 helper；helper 於 macOS 載入 libproc、呼叫 flavor 3
`PROC_PIDTBSDINFO`，取得 parent PID 與 start token。Helper 的載入／查詢錯誤
都可能保存 errno，因此舊 receipt 本身不能進一步唯一定位某個 helper 或 syscall。
既有程式遇 EPERM 且 PID 仍存在便停止；原 adapter 也會拒絕同一條件。
本次沒有忽略 errno、跳過 identity、重試未知 fork 或換成 private API。

[Apple libproc wrapper](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/libsyscall/wrappers/libproc/libproc.c)
將 proc_pidinfo syscall 失敗轉為 0 並保留 errno；
[XNU proc_info.c](https://github.com/apple-oss-distributions/xnu/blob/f6217f891ac0bb64f3d375211650a4c1ff8ca1ea/bsd/kern/proc_info.c)
對 PROC_PIDTBSDINFO 執行 MACF 及 same-user policy。這說明權限類候選，但該
公開 revision 日期為 2025-10-16，未映射到本機 kernel build，不能當實際拒絕原因。

本輪在外層 workspace-write 內，僅啟動一個 synthetic Python parent 和兩秒
sleep child，對自己及該已知子孫執行現有 observer：self identity 可讀、追蹤
一個 descendant、程序 exit 0。沒有全機 process scan。這也不支持「本環境
所有 libproc query 都不可用」；不證明複雜 CLI 子孫生命週期全程可觀察。

新的 live fixture 維持 read-only、private clone、240 秒 timeout、無額外 flags
及既有 no-recursion boundary。公開 login status 為 ChatGPT；未直接讀 auth。
首個 start 失敗後保存 receipt，synthetic HEAD／兩檔 digest／clean status
重驗不變。沒有 private logs/session/DB 讀回，沒有 raw transcript 落盤；
舊 fork 與新 start 的未知 session 狀態各自保留，未變更外層權限來重試。

## 驗證、交付範圍與後續

Python resolver 選擇 `3.12.9`，PyYAML `6.0.3`。本次執行：

```bash
CODEX_PUBLIC_HELP_EXECUTABLE=/opt/homebrew/bin/codex ./scripts/project-python -m unittest discover -s tests -p 'test_cli_session_handoff.py'
CODEX_PUBLIC_HELP_EXECUTABLE=/Applications/ChatGPT.app/Contents/Resources/codex ./scripts/project-python -m unittest discover -s tests -p 'test_cli_session_handoff.py' -k CodexPublicHelpCompatibilityTests
```

第一輪 64 項中 `test_version_probe_timeout_and_output_are_bounded` 一項失敗，
僅留下 stopped/fallback 差異，缺 failure_class/message 與 mode；不能判為 EPERM。
獨立取回兩個 fake 模式的 receipt 均為預期 capability_unavailable/fallback。
修改該測試後完整 64 項 PASS，bundled 的 3 項公開 help PASS。
修改僅將斷言放入 mode subtest 並輸出安全的 status/failure_class/message，
使下次失敗可分類；沒有降低預期、吞掉錯誤或修改 production 行為。
首次失敗的原因未確認，後續 PASS 不能證明它已修復。

一般測試仍只使用 fake executable／synthetic mocks／public help；不自動呼叫
live session。文件與測試變更另依 repository gates 執行 deterministic checks、
獨立 review 與 Security Diff Scan；PR 階段的 hosted CI／exact-head receipt
另行讀回，不以本紀錄預先宣稱 readiness 或授權合併。

目前安全 fallback 是在目前任務續行或交回已準備的 prompt。不得把 bundled
舊成功、放寬 sandbox、忽略 EPERM、省略 identity 或新 daemon 當已修好。
沒有安裝、升降級、release/deploy、使用者配置或 qualification store 變更。

後續 owner 為專案維護者，追蹤目標為 #251：原 fork EPERM、新 start exit 1、
首次 fake-probe 測試失敗均需各自保留。缺少同 context 的前後量測及更精確
的失敗觀測，故不推測修正。若要宣稱 live qualification 或推薦切換版本，
這些缺口即成為 blocker；先取得可審查、去識別、有界且不變更安全邊界的
診斷方式，再核對新 fixture／操作授權及收尾可觀測性。向上游發文需另有
明確授權；本次沒有發文。
