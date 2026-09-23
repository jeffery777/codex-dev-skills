# Heredoc／公開事件流根因調查

**狀態：本專案已緩解，上游問題仍未解決。** 本次沒有修補或替換 Codex CLI。

| 判定 | 狀態與界線 |
| --- | --- |
| 根因已定位 | 固定 CLI 0.156.0 的最小案例，實際 tool request/result、直接 shell 結果與官方 source 共同指向 command event 產生前的 early return。 |
| 本專案防止錯誤判讀 | 嚴格解析原始 JSONL、核對 final、分離 stream integrity／tool coverage；合成診斷比對可辨識本次漏項。這些措施不補造事件。 |
| 原始事件缺口已修復 | **否**。本專案修改後，重跑相同 heredoc 仍缺 command event；上游修復及同案例通過證據尚無。 |
| 發行資格 | 依使用者決定列為已知問題，可於本專案 gates 通過後發行；由 [#293](https://github.com/jeffery777/codex-dev-skills/issues/293) 保留上游未解狀態。模型配置、單元測試或診斷器通過都不代表此問題結案。 |

## 固定條件與原始證據

2026-09-23，macOS 26.6.2 / arm64；CLI `codex-cli 0.156.0` SHA-256
`6b42db4d33fd53516162bd76a0e2d07e0567287c44e036d4e4c06cb555a432f9`。
`/bin/zsh` 5.9、login=true、同一 owned temporary cwd、requested Luna/low、
read-only sandbox、fresh ephemeral process。每次只換唯一無敏感 marker；兩次
heredoc 主對照的 command template、prompt template、權限、model/effort 與 CLI
均相同，執行前後 binary hash 不變。沒有升級 sandbox 或修改全域規範。

```sh
cat <<'EOF'
R292_<unique>_HEREDOC
EOF
```

另一次工具呼叫執行 `printf '%s\n' 'R292_<unique>_AFTER'` 作正常 control。
直接對照使用同一 CLI 的 `sandbox -P :read-only -C "$RCA_ROOT/workspace"`
執行 `/bin/zsh -lc <相同命令>`；模型使用 `exec --ignore-user-config --ephemeral
--json --sandbox read-only --model gpt-6-luna -c model_reasoning_effort='"low"'`。

原始 stdout、stderr、exit code、prompt、exact argv、final 與 metadata 全量保留
於本機私有 run 目錄，未先經 jq、grep 或摘要過濾。公開 [results.json](results.json)
只含白名單事實、hash 與索引，**沒有完整 runtime logs、帳號資訊或公司資料**。

| 相同 heredoc 案例 | 本專案措施前 `baseline-before` | 本專案措施後 `baseline-after` |
| --- | --- | --- |
| 直接 shell exit / stderr | 1 / zsh heredoc temp permission error | 1 / 相同 error |
| 實際 nested tool args | 與 requested command 逐字元相同；shell/login/cwd 相同 | 同左 |
| 實際 nested tool result | exit 1、相同 error、diagnostic preview 未截斷 | 同左 |
| outer code-mode result | 保存 exit 1 與 error | 保存 exit 1 與 error |
| 原始 JSONL | 7 行皆可解析；只有 printf control 的 command item | 7 行皆可解析；仍只有 printf control |
| heredoc completed command items | **0** | **0** |
| final 與 `-o` | 一致；報告 heredoc exit 1 | 一致；報告 heredoc exit 1 |
| 本專案判讀 | 曾以缺事件誤判 fabrication；此確定性結論已撤回 | `confirmed_event_gap`；不判模型虛構、不補事件、不宣稱修復 |

「措施前」指診斷器與 strict evaluator 納入 repository 之前的相同案例；不是
上游 patched/unpatched binary 對照。**目前不存在原始事件缺口的修復後 PASS。**

## 假設與最早不一致環節

| 假設 | 此最小案例的判定 | 直接證據與限制 |
| --- | --- | --- |
| 未呼叫工具卻宣稱失敗 | 排除 | `codex.tool_result` 同時有 exact args、call ID、exit 1、完整短 output；open_session span 亦有 sandbox denial。不是只採模型 final。 |
| 工具收到請求，shell/heredoc 暫存檔失敗，未產生 command event | **成立** | 相同命令的直接 read-only shell 與 nested tool response 一致；官方 source 在 session 開啟失敗後、Begin 前返回。 |
| JSONL 匯出／本專案解析過濾遺失既有 command event | 本次排除本地解析遺失；source 定位為產生前早退 | 未處理的 stdout 就缺項且全部可解析；16 份歷史原始 JSONL 也都可解析。source 的 Begin 尚未到達，非本地 evaluator 吃掉該事件。 |

最早分歧是 **unified_exec 建立 session 的失敗路徑與 command lifecycle
emitter 之間**，早於 JSONL exporter 及本專案 parser：

1. [0.156.0 process_manager.rs:530](https://github.com/openai/codex/blob/rust-v0.156.0/codex-rs/core/src/unified_exec/process_manager.rs#L530)
   `open_session_with_sandbox` 出錯即返回；[Begin 在第 587 行](https://github.com/openai/codex/blob/rust-v0.156.0/codex-rs/core/src/unified_exec/process_manager.rs#L587)
   才執行。
2. [process.rs:307](https://github.com/openai/codex/blob/rust-v0.156.0/codex-rs/core/src/unified_exec/process.rs#L307)
   將早退及 denial 分類成 `SandboxDenied`；這是公開 code path 與 runtime
   診斷的交叉證據，沒有另作 kernel syscall trace。
3. [exec_command.rs:448](https://github.com/openai/codex/blob/rust-v0.156.0/codex-rs/core/src/tools/handlers/unified_exec/exec_command.rs#L448)
   仍把 output／exit code 回給工具；[JSONL exporter](https://github.com/openai/codex/blob/rust-v0.156.0/codex-rs/exec/src/event_processor_with_jsonl_output.rs#L477)
   則依 canonical item lifecycle 輸出。
4. [0.155.1](https://github.com/openai/codex/blob/rust-v0.155.1/codex-rs/core/src/unified_exec/process_manager.rs#L503)
   也有相同控制流，但沒有替每筆舊評測補出當時未保留的 tool response。
   未建立 tag source 與本機 binary 的 reproducible-build attestation。

zsh 在 read-only 下無法建立 heredoc 暫存檔是預期拒絕；**事件漏項才是上游
觀測問題**，不是 sandbox bypass，也沒有證據支持這次模型虛構失敗。

## 本專案措施與驗證

- [event_evidence.py](../event_evidence.py) 拒絕 malformed／truncated／非 object
  JSONL、失敗或缺 terminal、缺／空／不一致 final，保留錯誤行號、raw hash 與
  CLI exit；runner 仍寫 result 後非零退出。舊版 silent `ValueError: pass` 可被
  合成壞行重現，新版回歸會拒絕。它不是本次原始缺事件的根因。
- Stream 可解析與 turn completed **不等於** tool coverage 完整；預設 coverage
  仍是 `not_assessed`。不得把缺 command item 自動標成未執行或 fabrication。
- [analyze.py](analyze.py) 在固定 synthetic case 才比對 exact request、shell、
  login、cwd、直接 exit/output、公開 command item；修正後同 heredoc 仍辨識
  `confirmed_event_gap`。這驗證偵測有效，**不是修復上游**。
- 改用 temp-free `printf` 的窄對照 exit 0 且有兩個 command items；模型加了一個
  末尾 newline，另以實際 observed argv 做直接重跑後 exit/output 相同。這只
  緩解這種暫存檔需求，不是同 heredoc 的修復證據，不能用來結案。
- `--disable unified_exec` 嘗試仍缺項。[0.156.0 會重新啟用已移除替代 backend
  的 flag](https://github.com/openai/codex/blob/rust-v0.156.0/codex-rs/core/src/config/managed_features.rs#L153)；
  不稱為 legacy-shell 對照，也不改 managed requirements 來繞開它。

歷史評測的 findings／獨立 oracle 與可見操作證據仍有效；缺失的個別呼叫鏈不能
回填為 PASS，也不再用原先 fabrication 判讀作模型排名。成本僅保留原始 usage
及條件估值；此次診斷不是品質／成本比較。高風險仍直接 Astra/xhigh，與此問題
是否修復是兩個獨立判斷。

## 公開介面與資料保護

依官方 [RUST_LOG diagnostics](https://learn.chatgpt.com/docs/config-file/environment-variables#diagnostics)
在 synthetic run 啟用限定 targets。`codex_otel.log_only` 的 `codex.tool_result`
可補 request/result；`success=true` **不是 exit 0**，實際取 response header。
2048-byte preview 若截斷，或格式不符，就保留 unknown，不當證明。

此 logger 會附帳號 metadata，不能將完整 stderr 貼入 Issue／公開 repo。
本機 raw evidence 私有保留；公開資料只白名單匯出 synthetic facts/hash。
parser 只理解本次固定版本，metadata 邊界缺失會拒絕；它不是穩定 structured API，
也不是一般 production audit 的完整證明。不讀私人 sessions、SQLite 或 Desktop internals。

Desktop 公開更新檢查回報 `26.917.51856`（build `10492`，prod，up_to_date）；
相關 CLI start/resume/fork/sandbox 及 Desktop callable 介面未發現本次 adapter
破壞，119 項相容性相關測試通過。當次 `debug models` 缺 Sol/Luna 不能用來
證明可用或不可用；JSONL 也沒有 resolved-model/native-role attestation。
目前 task role schema 是啟動時快照，不能證明新版 profiles 已安裝。安裝／fresh
runtime qualification 仍是另一項授權與證據，不在此次發布準備中偷渡。

## 重跑與上游交付

手動執行 [run.py](run.py)；必須明確指定已查核的 CLI path、version、hash 與
私有 repo 外 root。以 repo `./scripts/project-python` 執行；不由普通 CI 啟動模型。
root 下保留相同 workspace、每 run 唯一 marker／目錄，不覆寫原 attempt。
`analyze.py <private-run>` 只將白名單核對結果存於該本機 run；缺口不是 exit 0
或 `turn.completed` 可以消除的狀態。

[英文上游問題報告](upstream-report.md) 已送出並讀回：[openai/codex #47433](https://github.com/openai/codex/issues/47433)。本專案以 [#293](https://github.com/jeffery777/codex-dev-skills/issues/293) 獨立追蹤。
最低下一步是上游讓這條 early-denial 路徑也發出可關聯的失敗 command item，
提供已修 CLI 的版本與 binary hash，再保持目前 read-only sandbox 重跑同一
heredoc。退出仍應是 1，但 tool request、失敗 tool result、JSONL failed command
與 final 都必須相符。沒有該修復後證據前，狀態維持：
**本專案已緩解，上游問題仍未解決。** 發行採已知問題揭露，不代表上游已修復；正式發行仍須通過本專案 CI、獨立審查及 exact-head gates。
