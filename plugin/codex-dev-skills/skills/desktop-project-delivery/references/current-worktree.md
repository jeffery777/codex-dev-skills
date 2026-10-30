# 在目前 Desktop 任務使用隔離工作樹

本 reference 僅在已授權工作需要隔離 checkout，且當次 Desktop 正式工具清單
提供 `create_worktree` 時載入。共享工作流負責範圍、ownership、驗證與完成；
這是目前任務的 checkout 操作，不是新 task、history fork 或 handoff。
以下為 2026-10-30 當次 schema；操作前仍須重驗完整 callable。

## 操作與前置

先核對來源 repository、Git status／branch／HEAD／remotes、修改範圍與單一
writer。沿用涵蓋該隔離工作的既有授權；工具可見性不授予操作權。

- 先呼叫 `list_artifacts`，核對目前 task 的附件與使用狀態；優先重用來源合適、
  既有修改已妥善處理且沒有其他工作依賴的 active worktree。名稱不同不是重建
  理由；archived worktree 使用 `restore_worktree`，不能以 attach 繞過 restore。
- `create_worktree` 必填 `allowAsync: true` 與明確 `ref`。先取得需要的遠端來源，
  再核對該 local Git revision；不省略來源或推定 remote default／目前 HEAD。
  新工作樹從指定 ref 以 detached HEAD 開始。只搬未提交修改時選排除無關提交
  的 default-branch base；只有來源提交也在本次範圍內才使用 source HEAD。
- `sourceRoot` 是選填的來源 repository 絕對路徑。Projectless chat 只可使用
  使用者選定的 repository；project chat 使用 cwd 或 workspace folders。
  多個已選 repository 分別呼叫，不以 path 猜測、同名 repo 或工具存在擴大範圍。
- `name` 可省略；指定時使用最多 64 字元的小寫連字號名稱。四字元以上全
  十六進位名稱及 Windows device names 為保留值。runtime 可為重名加後綴；
  名稱不是路徑或成功證據。不傳 task 的 `prompt`、`target`、`projectId`、
  `environment` 或 `startingState`。
- 未提交修改不會複製；需要搬移時先辨識本次 edits／新檔、staged／unstaged
  狀態及來源提交。只套用本次修改到目的版本並驗證，保留其他修改與 staging。
  沒有保留來源的要求時，驗證後才移除來源中同一組 edits；無法安全分離則
  保留來源並回報。不能自動 commit／stash 以湊齊前置。
- 此操作不選 environment，也不執行 environment setup scripts。

## 結果、執行位置與部分失敗

快速建立可回傳路徑；收到 pending `operationId` 時，以同一 ID 呼叫
`get_worktree_creation_status`，確認 `completed` 與目錄後才使用。
`preparing`、`creating`、`registering` 不是完成；失敗或未知結果先正常讀回，
不要為登錄失敗再次呼叫 `create_worktree`。進度未變時拉長查詢間隔；Git phase
百分比不是整體百分比或 ETA。不以 operationId 或 queued task ID 推測路徑。

依當次 schema 驗證回應，不猜測未公開的 response 欄位名稱。後續工具明確使用回傳目錄，
在 active turn 核對 Git root、ref／HEAD、worktree identity 與預期來源。
成功 attachment 會讓回傳的 workspace directory 成為後續回合的 cwd，除非
回應要求繼續明確指定。不能假設當輪所有工具已自動切換 cwd；每次續行重驗
實際目錄。建立或附加成功不會自動授予 sandbox permissions；寫入遭拒時循
公開 permission／command approval 程序處理，不換路徑繞過。

建立已成功但 registration 或 working-directory update 失敗時，先驗證回傳目錄，
再用 `attach_worktree` 的 `path` 指定該目錄，重試附件與 cwd 更新，不重建。
Attach 不 reset 檔案或跑 setup；已附加的工作樹可安全再次附加。Ownerless
checkout 必須已是本 task 的 attachment，或是本 app session 最近為本 task
建立；不得附加 unrelated chat 擁有的工作樹。缺 ownership／來源證據則停止。
Attach 也可能回傳 `operationId`，依同一 status 流程確認。結果未知時先查核，
不自動清理。Subagent 工作樹附件可能顯示在原 parent chat，不能據此假設無 owner。

依 repo 環境規則驗證；有 tracked interpreter resolver 時必須使用，不能假設
原 virtual environment 已沿用或複製 `.venv`。本專案使用 `scripts/project-python`；
缺 pinned runtime 時標記驗證未完成。工作樹建立、附件、cwd、權限、環境驗證
與 repository 完成是不同狀態。

## Fallback 與回報

能力不存在或不相容時，回到共享工作流決定目前 checkout 續行或準備明確的
手動 Git worktree 步驟；CLI 依其 Git／shell 路徑處理，不套用 Desktop payload。
不得以 private state、app-server、daemon 或 wrapper 模擬此能力。

回報來源 ref／HEAD、sourceRoot 的適用範圍、回傳目錄及其驗證、attachment／cwd
狀態、後續執行目錄、環境與權限缺口。範例、tests 與 CI 使用 synthetic 契約，
不自動建立 live 工作樹或執行 attach／restore。
