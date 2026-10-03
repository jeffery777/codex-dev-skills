# Hermes Agent 使用與支援邊界

本項由 [Issue #318](https://github.com/jeffery777/codex-dev-skills/issues/318)
追蹤。Hermes 使用獨立 `hermes/catalog.json` 與 `install-hermes.sh`；Codex
`catalog.yaml`、installer、plugin 與 profiles 不因此取得 Hermes 相容性。

## 安裝與依賴

先自行安裝可信 Hermes runtime；本專案不安裝 Hermes、模型、MCP、PyYAML
或其他第三方依賴。從 source repo 執行的驗證／安裝使用 `scripts/project-python`
與 pinned Python／PyYAML；被安裝的 exact-head validator 僅需 Python 3.10+ standard
library，不提供平台讀取或 review。技能本身沒有必填 secret。

明確選擇目前 profile 的 skills directory，先 plan，再 install，最後 diff：

```bash
# 先建立自己擁有的獨立 skills 目錄，確認無同名 skill 或 writer。
./install-hermes.sh plan --skills-dir /absolute/hermes-profile/skills
./install-hermes.sh install --skills-dir /absolute/hermes-profile/skills
./install-hermes.sh diff --skills-dir /absolute/hermes-profile/skills
```

產物在 `<skills-dir>/codex-dev-skills/`，保留 `skills/` 及 sibling
`policies/`、`templates/`、`scripts/`、`docs/`。三個入口為
`hermes-project-delivery`、`hermes-review-gate`、`hermes-task-continuation`。
安裝只寫新 namespace，拒絕現有名稱、symlink／碰撞及不安全目錄。plan 不
建立目錄、diff 不修復。更新先在新隔離目錄驗證；沒有 overwrite、force 或
uninstall。failed install 的 incomplete marker 不可當成成功，保留供診斷。

Hermes 原生 `skills_list`／`skill_view` 與 `/hermes-project-delivery` 提供
發現／載入；用 read_file 或 terminal 明確讀已安裝 sibling dependencies。
不能用單一 SKILL.md Hub URL 安裝代替本套件，因 sibling 文件不保證被複製。
不建議讓 Hermes 掃描可寫的 source repo 或全量 Codex skills：external_dirs
也可能被 skill_manage 改寫，名稱碰撞與不相容 adapters 需獨立處理。

## 支援矩陣

本次基礎交付是**有限支援**。安裝／發現／載入這個指定子範圍有原生實測；
其他列不能由成功載入推定完整支援。以下分類適用於本文列出的 CLI source
revisions，升級需重驗。

| 能力 | 基礎範圍 | 不包含／必須另驗 |
| --- | --- | --- |
| 獨立安裝、依賴、diff | 可離線驗證的新安裝，拒絕覆蓋 | runtime 發現／載入另做原生驗收；不自動部署 |
| 共用 planning／implementation／verification | Hermes 專用指引與 repo source／DoD | 真實模型執行、工具品質與工程 fixture |
| 權限／credential 保護 | 保留動作授權，逐 backend 查證 | 不宣稱 approval／toolset 等同 Codex OS sandbox |
| Review／正式 gate | 獨立 review、finding dispositions、offline exact-head validation | 沒有 scan service／獨立 reviewer／hosted gate 不能 ready |
| 委派／模型／返工 | schema／角色／權限先 preflight；兩輪未完成重評 | 不匯入 Codex TOML／qualification；沒有自動 model router |
| Context／session／接續 | repo checkpoint 加 supervised 手動續行 | 原生 resume 的身分/cwd/歷史另驗；不自動 fork、schedule 或 lifecycle dispatch |
| Hermes Desktop／gateway／cron／Goal | 尚未支援 | 不能由 CLI 或 source inspection 推定其他 surfaces |
| Memory governance／GitNexus／Codex plugin | 尚未提供 Hermes adapter | native memory 是 advisory，不可當完成或 managed-memory authority |

此表描述交付能力，不宣告所有 runtime 已驗收。完整支援必須有版本／surface／
backend 綁定的原生驗收，有限支援保留缺口，source/help/synthetic 成功不補足
真實模型與品質證據。當次結果放 Git 外驗收報告，不將私人 runtime 狀態提交。

已實測的基礎子範圍：三個技能原生載入、OpenAI subscription provider 的
技能／read_file roundtrip、有界 planning／實作／terminal tests、exact-ID
session 接續與 checkpoint。缺 OS sandbox／delegate 角色品質證據的能力
保持有限或尚未支援；正式 gate 仍要求獨立 reviewer 與 scan／平台證據。

## 模型與測試

原生 loader 可重跑以下命令；從 Hermes 公開
`hermes --print-runtime-command` 查明其可信 interpreter／source，明確填入
隔離 profile，勿把 command output 當 shell code 執行：

使用該 runtime 正常管理的獨立 profile，先由其公開介面確認既有依賴可用。
本次 managed runtime 的 profiles 位於安裝根目錄的 `profiles/`；任意另設
HERMES_HOME 不一定繼承其依賴。probe 設定公開 source 支援的
`HERMES_DISABLE_LAZY_INSTALLS=1`，只跳過 `prepare_launch()` 的 lazy sync；
`recover_if_needed()` 仍可在 recovery marker／missing environment 時修復、
下載或改寫 runtime。此 probe **不提供唯讀／offline／禁止修復的執行邊界**。
執行前先用當次 runtime 的公開檢查介面及 source 確認既有依賴健康、沒有
pending recovery，並核對啟動副作用的精確授權。無法確認時不執行 probe；
需修復時另核對修復目標、範圍與授權，再從新證據重驗。技能或命令範例本身
不授權修復。升級／其他 runtime 重新查證旗標、recovery 與依賴繼承語意。

下列命令在 source repo 執行。consumer 安裝不附 repository Python resolver，
可用已驗證 Python 3.10+ 執行 `<namespace>/scripts/verify-hermes-runtime.py`。

```bash
./scripts/project-python scripts/verify-hermes-runtime.py \
  --runtime-python /absolute/trusted/hermes/python \
  --runtime-source /absolute/trusted/hermes/source \
  --hermes-home /absolute/isolated/hermes/profile
```

此腳本使用原生 loader、清除 ambient credential env、不直接呼叫模型或登入，不證明
獨立 reviewer、工具隔離或完整 runtime 資格；trusted runtime import 的副作用
仍需依當次 revision 查證，不能從 wrapper 推定不讀任何本機資料。模型測試另在同一受控 profile
使用 `hermes chat --query-file <synthetic-prompt> --provider openai-codex`
及明確 `--model`／`--toolsets`／`--in`／`--max-turns`／`--run-budget`
與 `--format stream-json`；保留原始結果、實際 tool calls 與最終產物，
主代理獨立重跑 fixture tests。接續以結果中的 exact session ID 使用
`--resume <id> --in <playground>`，核對 sentinel、cwd、權限與 checkpoint。
不要使用模糊 latest/title，也不要省略單次 query 的 approval 設定。

[Hermes 官方 model 文件](https://hermes-agent.nousresearch.com/docs/user-guide/configuration/)
與公開 `hermes_cli/auth_codex.py` 提供 `openai-codex` 路徑。Hermes 自己的
OpenAI subscription 登入來源需獨立確認；不要手動複製 Codex token，也不要
假定 Codex Desktop 的登入自動適用。採用既有 Hermes 登入前確認使用者意圖。
測試 profile 明確停用 external login adoption、API fallback／auxiliary 自動
路由；只選當次該 provider 實際支援的 model/effort，所有測試內容排除機密。
既有訂閱可用不代表全部模型、context 或 reviewer 品質都已合格。

測試使用隔離 playground／profile、合成工程 fixture；skills loading、工具
roundtrip、bounded edit/verify、delegation、review、resume 各自讀回。
模型 provider 使用 credential 不表示允許工具讀或輸出 auth；不在報告保存
token、私人 config 或 session DB。工具環境與 filesystem 隔離需另外核對。
rocky98 如選用，只在 `~/projects/playground` 工作，不改服務或模型設定。

公開 CLI `--oneshot` 的 approval bypass 不符合本 adapter；`--yolo`、approval
off 或 auto-accept hooks 也不採用。supervised CLI 仍須查實際 OS／backend
boundary。[官方 security 文件](https://hermes-agent.nousresearch.com/docs/user-guide/security/)
的 command approval、file sandbox、container 與 subagent 邊界不可互相替代。

## Source 與重驗

來源調查固定公開 upstream `0a374d167424cdc730ce9761368b62255b551e58`，
當次本機公開版本 revision `5bba024d8ddd388f56f354c1f789be825e3d8a3c`。
版本有差異，不能將最新網站直接當成 installed runtime 的證據。

- [技能 source](https://github.com/NousResearch/hermes-agent/blob/0a374d167424cdc730ce9761368b62255b551e58/tools/skills_tool.py)
- [委派 source](https://github.com/NousResearch/hermes-agent/blob/0a374d167424cdc730ce9761368b62255b551e58/tools/delegate_tool.py)
- [CLI source](https://github.com/NousResearch/hermes-agent/blob/0a374d167424cdc730ce9761368b62255b551e58/hermes_cli/main.py)
- [登入 source](https://github.com/NousResearch/hermes-agent/blob/0a374d167424cdc730ce9761368b62255b551e58/hermes_cli/auth_codex.py)

升級後重查 help/schema、source 差異、依賴讀回、權限／憑證、模型 roundtrip 與
受影響 lifecycle；版本/help 相同也不能代替實測。source tree／installer
bytes 可重建，驗收身分／時間、平台 checks／scan IDs 是當次歷史證據。

## 共用工程工作流

Issue #320 讓三個 Hermes 入口與 Codex 引用同一份
[工程階段與完成契約](../../policies/engineering-workflow-contract.md)。採用時先
讀當次需求與 repository 指令，經 planning → implementation → verification →
independent review/fix → docs sync → delivery gate；中斷以 checkpoint 接續。
小型工作可合併階段，必要證據不能省略。原生委派未資格時維持單一 writer，
由已驗證且獨立的 Hermes session／review service 提供審查；必要 scan 與
forge control plane 各自接入。任何一步都不要求安裝 Codex CLI/Desktop。
`openai-codex` 是 Hermes 的訂閱 provider identifier，不是執行 Codex 程式。

相同 fixed fixture 用以下 helper 準備；指向既有安全 parent 下的全新目錄，
保留 prepare 輸出的 `case_sha256` 在模型不可改寫的操作人員證據位置：

```bash
./scripts/project-python scripts/verify-engineering-workflow.py prepare --fixture-root /absolute/new-fixture --runtime hermes
```

讓 Hermes 用已安裝的 `hermes-project-delivery` 讀 SPEC.md，僅修改 port.py、
README.md 及 CHECKPOINT.md，原生工具執行 `python -B -m unittest test_port.py`，
避免 bytecode 產生額外檔案。由父代理／操作人員
檢查程式與 diff 後，以受核對的權限執行獨立 verify；helper 會執行 fixture
程式，它沒有 OS sandbox，不能作為不可信程式的隔離器：

```bash
./scripts/project-python scripts/verify-engineering-workflow.py verify --fixture-root /absolute/new-fixture --expected-case-sha256 <prepare-digest>
```

Consumer 可用已驗證 Python 3.10+ 執行安裝的 scripts helper。Codex 另在自己的
全新 fixture 使用 `--runtime codex`，相同 tests／spec／文件條件。Label 不是
實際 runtime 身分證明；另外保存 actual model/provider、instructions digest、
tool calls、權限、獨立 review、必要 scan／平台證據，以及 exact session 接續
讀回。Helper exit 0 只證明列出的 functional observations，不能放行正式 gate
或宣稱品質等價；其他資格與支援矩陣的限制保持不變。
