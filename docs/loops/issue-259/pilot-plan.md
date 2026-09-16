# Issue #259：配對 pilot 預先計畫

此計畫在第一次 model trial 前凍結。沿用
[#223 paired trial](../issue-223/model-evaluation-follow-up.md) 與
[#255 語意 oracle](../issue-255/prompt-cases.md)，不建立資格流程。

## 固定條件

- A：v0.24.3 的 code-review／code-review-deep＋task brief；B：本次更新後相同
  檔案與按需 reference。比較整組提示，無法拆分各項效果。
- 同一個合成 fixture snapshot，每次新目錄與 fresh `codex exec` context；
  不 resume/fork。相同 task、tool／sandbox、developer profile、驗收與限制。
- 目的 runtime：本機 standalone Codex CLI 0.154.0，公開 `--help` 支援
  `--ignore-user-config --ephemeral --json`、明確模型與 sandbox。固定
  `gpt-6-astra`／`xhigh`，使用現有 baseline deep-reviewer 的 developer
  instructions（不修改 profile）。實際 model／effort 綁 invocation；若事件
  無獨立 resolved-model attestation，另列 unknown，不猜測 private harness。
- Python：來源 repository `./scripts/project-python` 選出的 pinned 3.12.9；
  fixture 複製 resolver 與 `.python-version`，不安裝依賴。
- read-only sandbox、禁止外部寫入、遞迴派送、讀其他 run／oracle／個人環境；
  可執行受控本地測試與產生新 temporary reproduction outputs。
- 記錄完整 prompt／profile／skill／policy bytes digest、CLI executable digest、
  OS/shell/Python 身分與當次可觀測版本；不公開 private runtime state。

五組配對依序 AB、BA、AB、BA、AB；五組無法各半，明示 3/2 order imbalance。
每個 run 都做同一 packet 的 bundle review、display control、offline/skip control。
目標各五次 completed runs；completed 指取得 terminal response，不等於品質通過。
上限 12 attempts，僅啟動／環境失敗可在分類後補跑；每次 12 分鐘、整批
90 分鐘。Subscription limit 出現就停止量測，不購買用量；逾時不宣稱遠端
processing 已停止。不因品質失敗挑選補樣本。

## 獨立 oracle 與品質

oracle 先由獨立 reviewer 提出、主代理用真實 Python／shell／subprocess 驗證。
它不送入受試 prompt；共同 filesystem 的不主動注入不等於讀取隔離。
grade 使用隱去 A/B 標籤的 run output，由獨立 reviewer 評分後才揭露條件。

| Oracle | 必須辨識的事實 |
| --- | --- |
| F1 | `run` 的 version subprocess 繞過注入 runner；wrapper fake 仍依賴主機工具。 |
| F2 | launcher source startup profile 清除 caller 的 route；直接執行環境不等價，script 主要工作尚未開始就拒絕。 |
| F3 | input locator 不符合 strict builder，dry-run 卻回報 validated，未穿過 builder。 |
| F4 | 真實 producer 會輸出非 UTF-8 binary；consumer 與文字-only fake 不一致；部分產物留存。 |
| C1 | 純 display 字串與獨立測試，不需要 Runner、整合矩陣或額外 gate。 |
| C2 | remote publishing suite 不適用，保留 skip reason，繼續其餘必跑檢查及報告。 |

F1–F4 各評 0=漏報／錯因／空泛，1=相關位置但缺因果，2=正確位置＋觸發＋
影響與契約鏈，3=另有實際受控重現。分別記 false positive、錯誤完成、越權、
完整性、返工、不必要讀取／停止／核准要求。正確靜態 finding 不假報成實測。
所有 material 漏報、越權、false completion 或控制退步先調查，不能用速度
抵銷；只對有足夠證據的有限結果下結論。

## 觀測與成本

保存每次 stdout JSONL、stderr、terminal/exit、命令與結果、final report、
wall time、input/cached/output/reasoning tokens。只採公開事件，缺欄位填
unknown；不加總重疊的 cached/reasoning 子欄位。保留失敗 attempts、重試及
主代理、設計 reviewer、grader、整合驗收成本；未能逐包歸因者 unknown。
報告逐次值、median 與 min/max；總成本不完整就不宣稱節省。

不量 API dollars、不換算 subscription credit；credit 未可靠觀測。
單一合成家族的小樣本不證明長任務、真實 Runner、跨 runtime、其他 effort
或模型排名，不啟用 qualification／預設設定。

CLI 觀测介面來源：2026-09-16 讀取官方
[Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)，
實際 flags 另由本機 help 核對。原始 logs 留本機，公開只放去識別事件與結果。
