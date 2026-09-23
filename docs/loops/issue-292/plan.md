# Issue #292：GPT-6 日常預設與漸進載入

## 目標與範圍

先建立並讀回 [Issue #292](https://github.com/jeffery777/codex-dev-skills/issues/292)，
再推送 `codex/issue-292-gpt6-routing`，最後建立隔離 worktree；起點為
`75c2568b5f9b84dd9937f2b869c145f56090030d`。修改僅限本專案。
2026-09-23 重新查讀 46 行全域規範，確認已承載操作邊界、技能按需載入與委派
原則；不修改全域檔案、已安裝 runtime、個人設定或 qualification store。

使用者明確選擇本次改用 GPT-6 日常預設，完成代表性驗證後發行。
最終設計收斂為 9 baseline＋3 既有 Astra opt-in profiles，不發布重複的 GPT-6
候選角色。官方依據見 [模型與成本說明](../../gpt6-cost-routing.md)。
官方費率及能力定位支持遷移決策；它們不是本專案實測品質或成本結論。

## 設計與相容

- 五個既有日常角色改用 GPT-6：mechanical Luna-low、explorer Luna-high、
  balanced／advanced Sol-medium、senior Sol-high；保留原角色 instructions。
- 新增 `loop_v2a_routine_reviewer`：Sol-high、deep-reviewer class、everyday
  tier、read-only；deep/security/exceptional 仍使用 Astra-xhigh。
- 新 route builder 固定使用 `v2-2026-09-23`；驗證器分別理解無 revision 與
  `v2-2026-09-06` 的 frozen 歷史語意，不用新預設重算舊 receipt。
- Current profile registry 不含 5.5/5.6 mappings；model-neutral parent/default
  與 sequential fallback 仍要求已驗證能力，不由缺少 model ID 推論其世代。
- 檢查 model/effort、class/tier、sandbox、installed bytes/digest 與權限。既有
  Astra candidate 保留 exact runtime/scope/evidence qualification；舊安裝不
  自動合格，必須另行明確 update；profile 選擇不授予外部操作權限。
- 技能按當次階段讀取 context、qualification 與工具編排細節；返工沿用核心
  驗收失敗後的分類與能力重評門檻，不建立固定最高 effort 或盲目重試。

## 代表性驗證

固定六個獨立 CLI packets，各含五個驗收點：reader（latest-event extraction）、
explorer（四檔 precedence/call-chain）、balanced（chunker）、senior（typed layered
config）、advanced（staged artifact export）、routine reviewer（兩個 seeded bugs、
正確 control 與 not-applicable backend）。Oracle 由獨立 reviewer 先提出，父代理
建 fixture 並以真實檔案、命令及隱藏斷言驗收，不能只接受模型的完成宣稱。

使用 fresh ephemeral CLI、固定 profile developer instructions／model／effort／
sandbox、相同 fixture 與明確 ownership。模型遷移案例不混入不同 skill 載入版本。
另外以相同 explorer／senior packet 檢查一個較低 effort，保留中性或不利結果；
不能從單包通過推論較低 effort 已普遍合格。每 run 最多 10 分鐘，沒有 quota
購買、反覆補挑好結果或 production 操作。失敗先分類，保留原 attempt。

保存 request、公開 JSONL/stderr、terminal/exit、final、profile/prompt/fixture digest、
wall time 與公開 usage。CLI explicit configuration 不是 native custom-role activation；
缺 resolved-model attestation 保留 unknown。Desktop 公開模型／effort 可用性與 CLI
品質證據分開，不建立 Desktop production qualification。這六包只支持本次明確
範圍的採用，不宣稱完整 ME-01/ME-02/ME-03、長任務優勢或實測成本降低。

## 補充：審查漏報與風險評測

同 Issue／branch 補足首次風險分類與 parser／subprocess／外部函式庫邊界。
細節放在既有 integration-boundaries reference，入口僅保留適用觸發條件；
全域規範不擴張。新增獨立合成 reviewer 評測，固定一般審查提示，不揭露
預期缺陷；真實缺陷、維護性建議與符合文件的 retention controls 分開評分。
對實際 parser、exit code、summary、舊產物及安全診斷做父代理驗收，記錄
各模型／effort 的漏報、誤報與用量後決定適用邊界。合成案例不包含外部專案
程式、URL、附件或環境資料，不用它推論其他審查的模型或上下文。

## 交付與發行

聚焦歷史 receipt、反向 tier/sandbox/runtime/digest 與安裝回歸；完成所有 test
shards、offline repo/release validators、package parity、隔離 fresh/upgrade、獨立
code/deep/docs 與 Security Diff Scan。PR 後另做完整 exact-head review、hosted CI、
strict receipt、App/ruleset 與即時 readback。

本次變更日常預設及 installed routing 能力，適合 pre-1.0 minor `0.27.0`。
2026-09-23 準備期讀回既有 v0.26.1 non-draft/non-prerelease Release、annotated tag
object `37aeb56cfb8a36b6a7b484627c03209578bcc79d` dereference 至起點 commit；
當次 v0.27.0 matching-ref 為空，正式發布前需重查。Connector 未提供 tag/Release
操作時，使用 `connector-operation-unavailable` 的 scoped gh fallback。

正式 payload：annotated tag/title `v0.27.0`、本版 release note 正文、draft=false、
prerelease=false，target 於 PR 合併後精確核對。使用者已授權適合的發行；各階段
仍須當前 gate。保留歷史 release notes；不在 active guidance 維護 mutable
publication pointer。安裝、部署及全域設定不在本次交付範圍。

## Heredoc RCA 與已知問題

同 Issue／branch 完成固定 CLI 0.156.0 的直接 shell／模型工具／JSONL 比對；
根因定位上游 early-denial 在 command Begin 前返回。本專案 strict parser 與
診斷比對已補強；相同 heredoc 在措施後仍缺事件，沒有上游修復後 PASS。
詳見 [RCA](heredoc-rca/README.md)。依使用者決定列已知問題發行；
[上游 #47433](https://github.com/openai/codex/issues/47433) 與
[本專案 #293](https://github.com/jeffery777/codex-dev-skills/issues/293) 持續追蹤，
本次 #292 關閉或發行都不代表上游已修復。CLI／Desktop 公開接口另作有界
相容審计，不更新個人安裝或讀取私有 internals。
