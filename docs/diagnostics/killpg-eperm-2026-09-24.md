# killpg EPERM 調查 — 2026-09-24

追蹤 [Issue #295](https://github.com/jeffery777/codex-dev-skills/issues/295)，沿用
`codex/issue-295-runtime-index-workflow`、HEAD `7100b3b` 及原有未提交成果。
本文件是 [CLI／Desktop 相容性工作](../codex-runtime-compatibility-evidence-2026-09-24.md)
的延伸；以下保留升級前觀測，不合併入口、不變更共享分層。
後續 [macOS 27 重測與 receipt 紀錄修正](killpg-eperm-macos27-2026-09-24.md)
另行記錄，不改寫本文件的歷史測試結果。

## 判定

**已重現自然 EPERM，也已取得一般 Terminal 對照；不能將它判定為 Codex
工具特有的權限拒絕。** 同一 Python 執行檔、同一最小程式與參數，在 Codex
工具 pipe、工具 PTY、使用者自行執行的一般 Terminal，均為 30／30 次 EPERM。
三者都在快速退出 child 的 stdout EOF 後、尚未 reap 時呼叫 `killpg(SIGTERM)`。

Apple 公開 XNU 的「group 存在但沒有符合條件的成員」路徑可以回傳 EPERM；
實驗的 `getpgid`／`getsid → ESRCH`、正 PID signal 0 成功、最後 exit 0 與它
一致。**最有力的原因是退出期間的 process-group 語意及觀測時序。** 尚未
直接觀測本機 kernel 內部採用哪條分支，因此不把這個機制推論升格為精確 syscall
內部因果證明；也不能回填最初缺少診斷資料的測試失敗。

現有證據不指向 OpenAI 特有執行缺陷，未建立指控該缺陷的對外回報，也沒有
對外提交。若後續同版本、同程式的受控對照出現工具特有差異，再以本文件與
repro 準備供審閱的回報草稿。

## 不同證據不可混同

| 證據 | 已知事實 | 不能推定 |
| --- | --- | --- |
| 最初 64 項 suite 中的失敗 | 預期 fallback，實際 stopped；舊 assertions 在 subtest 外，未保存完整 exception／receipt | 不能確定是 timeout 或 overflow，也不能直接認定 killpg 是該次原因 |
| 前次自然診斷的保留轉錄 | 同一 fake 快速退出；一次第 6 個 overflow 得到 signal failure receipt；另一輪第 8 次 stopped，累計記到兩個 errno 1／signal 15 | 當時錯誤陣列未逐 trial 清空，不能說兩次 EPERM 都屬於第 8 次；沒有可獨立讀回的完整 raw artifact |
| 本次自然重現 | 下表的逐 trial JSONL，有 signal exception、poll 時序及完整 adapter receipt | 重現不證明歷史事件完全同因；observer 仍可能影響機率 |
| 人工注入 | identity 或 killpg 被測試明確替換成 EPERM，仍 stopped／termination_error、無 session call | 只證明 fail-closed 分類，不證明 OS 真正回過 EPERM 或自然原因已修復 |

前次轉錄由原唯讀診斷代理回報；沒有為恢復歷史證據讀取私人 session、app database
或 runtime logs。缺少的資料明確保留缺口，不以現在的例外堆疊補稱歷史實測。

## 環境與執行界線

- macOS `26.6.2`，build `25G83`；Darwin `25.6.0`，
  `xnu-12377.161.14~5/RELEASE_ARM64_T6020`，arm64。
- Python `3.12.9`，Clang `16.0.0`；以 `scripts/project-python` 選取。
  對照的 interpreter bytes SHA-256 均為
  `f25cb98ed2850449cd21d0f7c8f54b49e3a5a48911027b7062d9a34a45722c26`。
- 相容性觀測為 Desktop `26.917.62051`／build `10789`、bundled CLI
  `0.155.0-alpha.16.3`、standalone CLI `0.156.1`。重現程式不啟動任何官方 CLI，
  只有自己建立的有限生命週期 Python child；CLI 版本不是本次 syscall 的執行主體。
- Codex 工具維持當次 `workspace-write` 與既有網路限制；沒有 privileged、
  `require_escalated`、sandbox 設定變更或替代 signal 來使診斷通過。
- Terminal UI 控制與對自己 child 的 `/bin/ps` 呼叫均被工具安全限制拒絕，
  未繞過。一般 Terminal 結果由使用者自行執行後回覆完成，再讀取其指定 JSONL；
  `environment_label` 是操作來源標籤，並非 sandbox attestation。
- 原始 JSONL 留在本機暫存區，沒有提交 runtime state、環境變數、憑證、機器
  名稱或私人 app 資料。只記自己與自建 child 的 PID／PPID／PGID／SID／UID、
  relative monotonic timestamps、signal、完整例外與必要 receipt。Traceback
  只遮蔽 repository／home 路徑前綴，保留所有 frames 和 cause chain。

### 升級前基準與續測條件

2026-09-24，使用者告知正在從 macOS 26.6.2 升級至 27；本次結果固定為
**升級前基準**。當時 macOS 27 尚未重測；之後使用者通知更新完成才執行
[macOS 27 重測](killpg-eperm-macos27-2026-09-24.md)。兩輪紀錄保持分開。

| 比對項目 | 升級前已驗證值 |
| --- | --- |
| macOS／build | 26.6.2／25G83 |
| Darwin／XNU | 25.6.0／12377.161.14~5，RELEASE_ARM64_T6020 |
| Python | 3.12.9；binary SHA-256 見上方 |
| EOF 對照參數 | `--layer minimal --case eof --child-metadata --iterations 30`；signal 為 SIGTERM、delay 為 0 |
| Codex 工具 pipe／PTY | 各 30／30 EPERM，child 最後 exit 0 |
| 一般 Terminal | 30／30 EPERM，child 最後 exit 0；使用者手動執行並確認完成 |
| 程式指紋 | 三組均為下節記錄的 `0dfbc525…b1ff4e` 完整 SHA-256 |

已核對的三份 EOF／SIGTERM 原始檔指紋：

| 本機 artifact 名稱 | SHA-256 |
| --- | --- |
| `eperm-minimal-eof-pipe-final-30.jsonl` | `228f83fb2c04ce01b7d14921d9e4ca84841bb5a2547cb980edc0243c87e04ab0` |
| `eperm-minimal-eof-pty-30.jsonl` | `4f715f2f450a31879534ab94e40132c1107d39c7a560bd6599f8b966a4d7c381` |
| `issue-295-terminal-eof.jsonl` | `876ed06bc59f5ae1be11da8f1a361be3bff2b6e650d341a7e99441b4c5d530e0` |

原始檔仍在 repository 外的本機暫存區，可能受系統清理影響；此文件保留版本、
參數、結果、時序摘要及指紋供跨重啟比對，不能用摘要冒充仍可讀回的原始檔。
重測時先查讀實際 macOS／build／kernel、Python binary 與程式 SHA-256，
再以同一程式、參數及真實執行環境分別產生新檔，不覆寫升級前資料。其他版本
或執行限制若同時改變，須列為混雜因素，不能把所有差異歸因於 OS 升級。

續作仍沿用 Issue #295 與目前分支、CLI／Desktop 獨立入口及共享分層。
獨立審查另確認失敗 receipt 的 `version_probe_performed` 可能錯誤保留為
`false`：probe 已啟動，但失敗路徑重新建立 base receipt。這是待修的紀錄缺陷，
當時尚未實作修正，後續 disposition 見 macOS 27 紀錄；須與 syscall EPERM 的原因及 stopped／termination_error 保護
分開處理。後續若使用 GitNexus，須先對目前 checkout 安全刷新索引並驗證，
保護 AGENTS.md 與既有修改；本次紀錄更新沒有查詢過期索引或同步遠端。

## 逐層縮減與結果

可重跑入口：[killpg_eperm_probe.py](../../scripts/diagnostics/killpg_eperm_probe.py)。
`adapter` 使用完整 synthetic fixture 與 `execute_handoff`；`probe` 只呼叫
`_probe_version`；`minimal` 完全不載入 fixture 或 adapter，只保留 stdlib
`Popen → pipe read → killpg → communicate`。

不含批次與觀測功能的核心重現如下；child 沒有等待終止、沒有 mock，也沒有
官方 CLI。完整診斷入口額外記錄版本、身分、時序與例外，供環境配對使用。

```python
import os, signal, subprocess, sys
p = subprocess.Popen(
    [sys.executable, "-c", 'import sys; sys.stdout.write("x"*8192); sys.stdout.flush()'],
    stdout=subprocess.PIPE, start_new_session=True,
)
try:
    p.stdout.read()  # EOF；尚未 poll/wait/reap
    os.killpg(p.pid, signal.SIGTERM)
finally:
    p.wait(timeout=3)
    p.stdout.close()
```

| 本次樣本 | trials | 有自然 EPERM 的 trials | 觀測 |
| --- | ---: | ---: | --- |
| 完整 adapter、保留快速退出 | 40 | 5 | 4 stopped／termination_error；36 fallback；全部無 session call |
| 單獨 version probe、保留快速退出 | 40 | 1 | 該次 termination_error，最終 child exit 0 |
| minimal，讀部分輸出即 signal | 30 | 0 | child 自報身分；signal 成功，exit -15 |
| minimal，child flush 後存活 0.5 秒 | 30 | 0 | 存活控制組；signal 成功，exit -15 |
| minimal，EOF 後 SIGTERM，工具 pipe | 30 | 30 | 同一最小程式指紋，child 最後 exit 0 |
| minimal，EOF 後 SIGTERM，工具 PTY | 30 | 30 | 仍是 Codex 工具，不冒充普通 Terminal |
| minimal，EOF 後 SIGTERM，一般 Terminal | 30 | 30 | 使用者完成；版本、binary、script、參數逐項比對 |
| minimal，EOF 後 group signal 0，工具 pipe | 30 | 30 | 無實際 signal 送出仍 EPERM；正 PID signal 0 成功 |

三環境 EOF／SIGTERM 對照的程式 SHA-256 均為
`0dfbc5252343c88684d2857c8b6b2ec644a680c57f2ed9bcb9c98d2825b1ff4e`。
這是當次程式指紋；未來修改腳本後須重新配對，不能沿用數字冒充同程式對照。

除了上述正式樣本，最初 stdlib 探索在讀部分輸出後立即送 signal 為 100／100
成功；改 EOF 後延遲 0、0.1、1、10 ms，每組 30／30 EPERM。它們僅是先導
工具輸出，沒有與正式 JSONL 混算。另有初版 harness 的 guard path-normalization
錯誤，修正後才取正式樣本；該錯誤不是自然 EPERM。

初版 harness 每次重建 shebang fake，adapter／probe 各 50 次都 fallback、
沒有 EPERM。檢查發現新 shebang path 的一次 cold launch 約 0.523 秒，明確
Python 執行同檔約 0.022 秒，超過原本 0.1 秒 probe deadline；只重建假程式的
做法改變了條件。此啟動差異的 OS 原因未查明。正式樣本改為像原調查一樣重用
同一個 fixture executable，保留完整 imports、8192 bytes、flush 與立即退出。
沒有把「改成等待終止」當作原問題的解決方法。

### 一次 stopped 的時序

完整 adapter 正式樣本的 trial 14，以該 trial 起點為相對時間：

| 事件 | 時間 ms | 結果 |
| --- | ---: | --- |
| `_signal_process_group` 的 signal 前 poll 返回 | 149.381875 | None |
| `killpg(SIGTERM)` | 149.446750–149.453000 | PermissionError，errno 1 |
| 同函式的錯誤後 poll 返回 | 149.457625 | None |
| 原始 group cleanup 再送 SIGTERM | 149.479917–149.482292 | 再次 EPERM |
| 後續 probe finally 的 poll 返回 | 150.804375 | 0 |

完整 receipt 是 `stopped / termination_error`，message 為
`The Codex process group could not be signaled.`，`session_call_performed: false`。
另一個 trial 的錯誤後 poll 已得到 0，因此走既有 fallback。可見 EPERM
與 stopped 不是一對一；不是只記一個總數便能解釋結果。

signal observer 只保存例外物件，待 adapter 返回後才格式化 traceback；不在
失敗 syscall 與第二次 poll 之間插入 identity 查詢或例外格式化。Poll wrapper
只觀察原有 calls，不額外 poll／reap。即便如此，observer overhead 仍是限制，
上述比例不作為自然發生率或版本回歸率。

## Apple 公開機制與未排除假設

查讀的 XNU 是公開 commit
`ac9718fb1af618d5ce8678d0dc6e8a58f252216f`（`xnu-12377.121.6`），與本機
`12377.161.14` **不是同一 build**。公開原始碼提供機制依據，沒有 kernel tracing
證明本機正在執行完全相同分支。

- [killpg1 的 group 查找、SZOMB filter 與 nfound 判定](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/kern/kern_sig.c#L1606-L1626)：
  group 查找失敗為 ESRCH；group 存在但沒有被計入的成員，POSIX 路徑可為 EPERM。
- [group iterator](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/kern/kern_proc.c#L4256-L4282)：
  filter 與逐 PID `proc_find` 之間亦有退出時序窗口。
- [正 PID kill 的 zombie 特例](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/kern/kern_sig.c#L1317-L1337)
  與 [getpgid／getsid 的 proc_find](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/kern/kern_prot.c#L210-L263)
  可解釋正 PID signal 0 成功、group identity 卻 ESRCH 的不對稱觀測。
- [cansignal](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/kern/kern_sig.c#L284-L356)
  仍含 MAC 與 UID 檢查；同 UID 並不能單獨排除政策拒絕。一般 Terminal
  的相同結果排除了「此最小現象只存在於 Codex 工具」的說法，沒有排除共享
  OS／host policy，也沒有證明歷史事件的每一次 EPERM 都是退出競態。

本次不支持官方 CLI 是這個最小現象的必要原因：程式從未執行官方 CLI。
Adapter 的終止處理負責觀測與安全分類；目前未確認應修改其 signal／終止行為。
另有上方記錄的 receipt 事實欄位缺陷，其後續修正不能稱 EPERM 已解決。
若第二次 poll 仍不能確認退出，保留 stopped／termination_error，不等待碰運氣、
不吞掉 EPERM、不把晚到的 exit 0 回填成當時已確認安全。

下一項最有辨識力的實驗是：在可用且另經核可的 macOS 原生診斷環境，以同一
無 adapter 程式及符合執行 build 的 XNU／非侵入式系統診斷，區分
`killpg1 nfound == 0` 與 MAC deny。若只需確認 portable 行為差異，可在另一台
已授權 macOS／Linux 主機先執行同一程式；本次未取得其他主機或 Linux 對照，
也沒有要求提權、改安全設定或安裝 kernel instrumentation。

## 重跑與驗證

```bash
./scripts/project-python scripts/diagnostics/killpg_eperm_probe.py --layer adapter --iterations 40 --environment codex-exec-pipe
./scripts/project-python scripts/diagnostics/killpg_eperm_probe.py --layer probe --iterations 40 --environment codex-exec-pipe
./scripts/project-python scripts/diagnostics/killpg_eperm_probe.py --layer minimal --case eof --child-metadata --iterations 30 --environment ordinary-terminal
./scripts/project-python scripts/diagnostics/killpg_eperm_probe.py --layer minimal --case partial --child-metadata --iterations 30 --environment codex-exec-pipe
./scripts/project-python scripts/diagnostics/killpg_eperm_probe.py --layer minimal --case live --child-metadata --iterations 30 --environment codex-exec-pipe
./scripts/project-python -m unittest tests.test_cli_session_handoff tests.test_killpg_eperm_probe
```

`ordinary-terminal` 命令由人於該環境執行；不能只換 label 當成環境對照。
JSONL redirect 到 repository 外的明確本機檔案。`minimal` 沒有 adapter receipt，
明列 null，不合成 fallback／stopped。診斷程式正常結束只代表完成收集，
不代表 signal 成功或 EPERM 已解決。

Regression checks 驗證快速退出 fixture 自然產生 8192 bytes 後 exit 0、
deferred observer 不增加 identity calls、真實固定 child 的身分與事件順序，
以及原有 injected-EPERM fail-closed。測試不要求 OS 必然回 EPERM，避免把
平台差異或競態頻率變成不穩定的 pass／fail 條件。
