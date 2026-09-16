# Issue #259：固定輸入重建

此文件讓後續批次重建合成輸入，不表示能重現服務端模型取樣、cache、負載
或 private harness。原批次固定 bytes 以 [manifest](pilot-manifest.json) 為準；
不可用變動中的 main 取代指定版本。所有操作在新建的隔離工作目錄進行。

1. 複製 `pilot-fixture/` 的全部檔案至每個 run workspace 根目錄，不初始化 Git。
2. 從 source base `476d2437519965e44e97de3423041852104c80e5` 複製
   `.python-version` 與 `scripts/project-python`，保持 resolver executable。
   將 [workspace instructions](pilot-workspace-instructions.txt) 原樣存為該
   workspace 的 `AGENTS.md`；[task](pilot-task.txt) 原樣作為 stdin prompt。
3. 在 workspace 的 `instructions/` 下保留 repo 相對結構，複製
   `skills/code-review/SKILL.md`、`skills/code-review-deep/SKILL.md`、
   `templates/orchestration/agent-task-brief.template.md` 及三份共同 policy：
   `reusable-workflow-contract.md`、`code-mode-tool-orchestration-policy.md`、
   `model-selection-policy.md`。A 全取 source base；B 的 skills／template
   取本次候選，policy 不變，另加 `skills/code-review/references/integration-boundaries.md`。
4. 逐檔核對 manifest 中相應 condition 的 SHA-256；兩組除了以上 treatment
   bytes，其餘內容相同。不要向受試 context 注入 oracle 或其他 run 結果。
5. 由原 base 的 `agent-profiles/loop_v2a_deep_reviewer.toml` 讀取
   `developer_instructions`，作為 `codex exec -c developer_instructions=...`
   的單一字串參數。使用公開 CLI flags：`--ignore-user-config --ephemeral
   --json --sandbox read-only --model gpt-6-astra -c model_reasoning_effort="xhigh"
   --skip-git-repo-check -C <workspace> -o <final-path> -`。這不是 native role
   activation，也不修改任何 profile；以 subprocess argument array 傳遞，避免
   shell 插值。記錄 stdin、argv、stdout JSONL、stderr、exit、wall time、final。

原批次的 CLI、global instructions、profile、plan 與 task digest 均在 manifest。
公開資料不包含 private config 或 raw runtime logs；後續機器若身分不相同，
應建立新批次並明列差異，不能宣稱 exact-runtime replication。保留失敗與未知
用量，沿用 [原計畫](pilot-plan.md) 的停止條件；不要因結果較差補挑樣本。

read-only runtime 實際阻止 temporary outputs，見 [偏離](pilot-deviations.md)。
本批只能重建受限條件；若要完成磁碟整合，另選正式授權的 runtime 與對稱 A/B
條件，不能在既有批次中途放寬 sandbox。
