# 在目前 Desktop 任務使用隔離工作樹

本 reference 僅在已授權工作需要隔離 checkout，且當次 Desktop 正式工具清單
提供 `create_worktree` 時載入。共享工作流仍負責範圍、ownership、驗證與完成；
這是目前任務的 checkout 操作，不是新 task、history fork 或 handoff。

## 操作與前置

先核對目前 repository、Git status／branch／HEAD／remotes、修改範圍、單一
writer 與當次 callable。沿用涵蓋該隔離工作的既有授權，不從工具可見性推導
額外操作權限。需要新任務或保留歷史的子任務時，回到
`desktop-thread-delegation` 的 create／fork reference。

- `create_worktree` 接受選填 `name` 與 `ref`；不傳 Desktop task 的 `prompt`、
  `target`、`projectId`、`environment` 或 `startingState`。
- 省略 `ref` 從目前 repository 的 HEAD 建立；指定時先核對 branch、tag 或
  commit 的精確目標。未提交修改不會複製。若工作必須包含那些修改，先解決
  來源與移轉方式，不能宣稱工作樹包含它們，或自動 commit／stash 以湊齊前置。
- `name` 可省略；指定時使用最多 64 字元的小寫連字號名稱。四字元以上全
  十六進位名稱及 Windows device names 為保留值。重名或封存工作樹保留的
  名稱會由 runtime 加上後綴；名稱不是最終路徑或成功證據。
- 這個操作不選 environment，也不執行 environment setup scripts。不要沿用
  新任務 worktree 設定流程會自動執行的假設。

## 結果、執行位置與部分失敗

依當次 schema 驗證回應並使用 runtime 回傳的 Git root 與 workspace directory，
不猜測未公開的 response 欄位名稱。工作樹會附加到目前 task，但不改變目前
task 的 cwd 或 sandbox permissions。後續工具明確使用回傳目錄；必要時依
實際 filesystem 權限提出該目錄的授權，不能把建立成功當作自動擴權。

在回傳目錄唯讀核對 Git root、HEAD、worktree identity 與預期來源。依 repo
環境規則完成必要設定／驗證；有 tracked interpreter resolver 時必須使用，
不能假設原 checkout 的 virtual environment 已沿用，也不複製 `.venv`。
本專案使用 `scripts/project-python`；缺少 pinned runtime 時標示驗證未完成。

若工作樹已建立但 task registration 失敗，保留並使用已回傳且驗證過的工作樹；
不要為登錄失敗再次呼叫 `create_worktree`。若成功狀態或路徑不明，先以公開
讀回核對，不猜測路徑、不重建、不自動清理。工作樹建立、附件登錄、環境
設定、驗證與 repository 完成是不同狀態。

## Fallback 與回報

能力不存在或不相容時，回到共享工作流決定目前 checkout 續行或準備明確的
手動 Git worktree 步驟；CLI 依其 Git／shell 路徑處理，不套用 Desktop payload。
不得以 private state、app-server、daemon 或 wrapper 模擬此能力。

回報來源 ref／HEAD、回傳目錄及其驗證、附件登錄狀態、後續執行 cwd、環境與
權限缺口。範例、tests 與 CI 使用 synthetic 契約，不自動建立 live 工作樹。
