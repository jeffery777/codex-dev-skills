# macOS 27 的 killpg EPERM 重測 — 2026-09-24

沿用 [Issue #295](https://github.com/jeffery777/codex-dev-skills/issues/295)、
`codex/issue-295-runtime-index-workflow`、HEAD `7100b3b` 與既有未提交成果。
升級前依據為 [macOS 26.6.2 調查紀錄](killpg-eperm-2026-09-24.md)。

## 結果

**macOS 27.0 仍可穩定重現 EOF 後的自然 `killpg EPERM`。** 相同 Python、
相同程式、相同參數，在 Codex 工具 pipe、工具 PTY、使用者自行執行的一般
Terminal，均為 30／30 次 EPERM。每次 child 最後 exit 0；錯誤後
`getpgid`／`getsid` 為 ESRCH，正 PID signal 0 成功。120 次 EOF 樣本
（三組 SIGTERM 加一組 group signal 0）逐筆符合相同觀測。

這次 OS 升級沒有消除該最小現象。不能把完整 adapter／probe 的這輪零 EPERM
樣本視為修復，也不能因此把升級前最初缺少 receipt 的 suite 失敗回填成同因。

## 環境與配對

| 項目 | 升級前 | 升級後 |
| --- | --- | --- |
| macOS／build | 26.6.2／25G83 | 27.0／26A428（`sw_vers` 實讀） |
| Darwin | 25.6.0 | 27.0.0 |
| XNU | 12377.161.14~5 | 13432.1.9~1 |
| architecture | arm64 | arm64 |
| Python | 3.12.9，Clang 16.0.0 | 相同版本及 binary SHA-256 |
| 最小重現程式 | `killpg_eperm_probe.py` | 相同 bytes，沒有改成等待終止 |
| synthetic adapter fake | 輸出 8192 bytes、flush、快速退出 | 相同 fake SHA-256 |

升級後 kernel 字串為
`Darwin Kernel Version 27.0.0: Tue Aug 11 21:20:40 PDT 2026; root:xnu-13432.1.9~1/RELEASE_ARM64_T6020`。

共同 SHA-256：

- Python binary：`f25cb98ed2850449cd21d0f7c8f54b49e3a5a48911027b7062d9a34a45722c26`。
- 診斷程式：`0dfbc5252343c88684d2857c8b6b2ec644a680c57f2ed9bcb9c98d2825b1ff4e`。
- adapter／probe fake：`5dd4023640ca246dcb1b013a679bed363cfff686439646c0810f7c7c1ba9b8ba`。

三環境 EOF 主對照參數為
`--layer minimal --case eof --child-metadata --iterations 30`，預設 SIGTERM、
delay 0。一般 Terminal 由使用者執行並確認完成，並非把工具結果換 label。
工具 PTY 以原生 `tty: true` 執行，JSONL 仍導向檔案。保留 workspace-write
與既有執行限制，沒有提權或改安全設定來執行診斷；沒有啟動官方 CLI session。

升級前暫存原始檔已不在原路徑，跨版本比較依先前保存的診斷文件、已核對
計數與指紋；不能宣稱本輪重新讀回舊 raw JSONL。升級後原始資料在 repository
外，逐筆重算計數、檢查 identity、事件順序、完整例外及 receipt，並產生 manifest。
沒有蒐集私人 runtime state、環境變數、credentials 或其他程序清單。

## 逐案例比較

所有數字均為「含自然 EPERM 的 trial 數／總 trial 數」。升級後主對照是在
receipt 修正之前、production adapter 尚未變更時執行。

| 案例 | macOS 26.6.2 | macOS 27.0 | 升級後其他觀測 |
| --- | ---: | ---: | --- |
| minimal EOF、SIGTERM、工具 pipe | 30／30 | 30／30 | 全部 exit 0 |
| minimal EOF、SIGTERM、工具 PTY | 30／30 | 30／30 | 全部 exit 0 |
| minimal EOF、SIGTERM、一般 Terminal | 30／30 | 30／30 | 全部 exit 0 |
| minimal EOF、group signal 0 | 30／30 | 30／30 | 未送實際 signal，仍 EPERM |
| minimal partial read 後 SIGTERM | 0／30 | 0／30 | 全部 signal 成功，exit -15 |
| minimal flush 後存活 0.5 秒控制組 | 0／30 | 0／30 | 全部 signal 成功，exit -15 |
| 完整 adapter、快速退出 fake | 5／40 | 0／40 | 40 fallback／capability_unavailable；10 次 signal 成功，30 次自然 exit 0 |
| 單獨 probe、快速退出 fake | 1／40 | 0／40 | 40 capability_unavailable；全部自然 exit 0，沒有呼叫 killpg |

完整 adapter 的升級前結果含 4 次 stopped／termination_error；本輪沒有。
但單獨 probe 本輪甚至未走到 signal，無從驗證該路徑是否改變。時間敏感的
40 次樣本不是發生率估計，也不能把其差異全歸因於 OS 升級。三環境相同的
minimal EOF 結果仍不支持「Codex 工具特有拒絕」或「官方 CLI 是必要原因」。

升級後原始檔指紋：

| artifact 名稱 | SHA-256 |
| --- | --- |
| `eof-pipe-30.jsonl` | `090ec613aa3dafd1dbdbaafefb607b10b1ff0f52aefc13117d9744c22611f967` |
| `eof-pty-30.jsonl` | `89c8779ffa00defcbad7905dfde949d5b1846e1aa5b5cf25604e91e9b96e2538` |
| `issue-295-macos27-terminal-eof.jsonl` | `2b6cb8e9059b7f9bf3c3b178644395847de1d34d7a97959734071cfe815f28a0` |
| `eof-zero-30.jsonl` | `0b1128f62cff6102bb62fe83dc0d468ccbbf8d8ecafb9380dd214ac684e6927b` |
| `partial-30.jsonl` | `36a91eb2dda9b545a1cbda9d23fa9849ce10a8d2e5d7d63904e2dc1d2af8b5be` |
| `live-30.jsonl` | `16d5b9caff103defe0651f24e2891445a86c343619c365f401cd37d871a9a177` |
| `adapter-original-40.jsonl` | `67abd50d892f270a8712ea631af333bc6fb879aded73d382014a5900d88b6477` |
| `probe-original-40.jsonl` | `f2f0634a2ebc14822686aa6e367d64edb9c7ea4fc08124af7918b799530c2675` |

## 本專案修正與尚未定位的部分

重測完成後，另修正先前獨立審查確認的 receipt 紀錄缺陷：probe process 已啟動，
失敗 receipt 卻重新使用 base 值，錯誤顯示 `version_probe_performed: false`。
現在以成功啟動事件記錄該事實；啟動前 validation 拒絕或 Popen 失敗仍為 false，
後續 probe 或 rollover 拒絕保留已觀測欄位。`cli_version` 只在接受版本後填入。

此修正只修復紀錄，沒有修改 signal、poll、termination 或 sandbox 決策，亦未
改寫上述原始 receipt。CLI／Desktop 各自入口與共享分層維持原架構。
人工 EPERM 驗證仍要求 stopped／termination_error，不能冒充自然原因已解決。

退出中的 process-group 語意與時序仍是有力假設；沒有符合此 XNU build 的
kernel trace，尚未區分精確 `nfound == 0` 分支與共享 OS／host policy。
下一個辨識力較高的實驗仍是，在可用且另經核可的原生診斷環境，觀測同一
最小程式的 syscall 分支；本輪不提權、不安裝 instrumentation、不弱化安全設定。
未對 OpenAI 或 Apple 提交回報，也沒有以未知原因製作上游缺陷指控。
