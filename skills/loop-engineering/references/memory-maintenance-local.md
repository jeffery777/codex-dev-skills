# Operator CLI 首用與五操作

固定 adapter `memory_maintenance_local.py`，採 `mg1-local-operation/v1` 受限契約。
default-off、單次操作、single project/host，同 OS 帳號為可信邊界。操作者在
controlling terminal 審查完整 canonical JSON，輸入當次 action/digest。
預設 `--actor human` 由使用者親自接受；`--actor agent` 只適用使用者已明確委派
project/root／操作範圍的 agent，由 agent 逐次審查與接受。結果的 `acceptance_actor`
及 evidence ID prefix 明示 actor，不把 agent 驗收記成人工驗收。Actor flag 只是標籤，
不證明上游授權，也不繞過 digest、TTL、來源或環境檢查；操作者須另核對有效委派。
不接受 --yes、stdin 管線或保存確認。TTY 不能證明人類身分或抗惡意 same-UID。
沒有可驗證的上游委派時，不從要求、proposal、actor flag 或測試結果推定可執行。

先準備已審查的 [隔離 runtime／storage 資格](memory-maintenance-local-storage.md)。
Source checkout 所有驗證與操作經 tracked resolver；以下絕對路徑需換成使用者
核對的實際值，不用 system Python 或任意 Python loader：

```sh
CODEX_PROJECT_PYTHON=/absolute/isolated-runtime/bin/python3.12 ./scripts/project-python \
  skills/loop-engineering/scripts/memory_maintenance_local.py init --enabled \
  --workspace /absolute/private-parent/new-workspace \
  --repository /absolute/repository --repository-id project-id
```

安裝後使用同一 qualified interpreter 執行安裝套件的
`loop-engineering/scripts/memory_maintenance_local.py`。套件更新後 adapter fingerprint
改變，舊 descriptor 安全拒絕；本版沒有自動 rebind／migration。已綁 root 的版本
升級須先以舊版明確 disable，再安排另外審查的遷移工作；fresh install 與一般
套件升級不會探索或修改既有 root。不得手編 fingerprint 來繞過拒絕。

## 首用

Parent 須為目前 UID 擁有的實際目錄，無 group/world write；workspace 必須完全
不存在、絕對路徑、無 symlink。Git repository／.git／objects 亦核對 owner、mode
與 identity；僅支援本機 loose SHA-1 commit/tree/blob，不支援 packed Git、worktree
.git file、alternates、fetch、外部 loader 或 human-confirmed-decision provenance。

1. `INSPECT` 接受精確讀取範圍；尚未採納來源、授權初始化或五操作。
2. `CREATE` 完整顯示 parent/repo 身分、scope/profile/policy、runtime/code、容量
   准入及將建立的檔案。拒絕／低容量不建立 root。
3. `INITIALIZE` 對 exclusive 新建後的實際 root 身分重新接受；核心強制初始
   64-page ceiling，再獨立 schema/scope/empty-state 讀回。失敗保留 partial，
   不覆寫、不重試、不清理。建立成功的 binding.json 是 disabled metadata，非 grant。
4. 執行 `enable --enabled --workspace /absolute/private-parent/new-workspace`，
   由選定 actor 接受 `INSPECT`、`ENABLE`。當前 root/runtime/descriptor 重新核對後才啟用。
   `disable` 同語法，接受 `DISABLE`；原子 replacement 撤銷 pending descriptor。

## 五操作

```sh
CODEX_PROJECT_PYTHON=/absolute/isolated-runtime/bin/python3.12 ./scripts/project-python \
  skills/loop-engineering/scripts/memory_maintenance_local.py run --enabled \
  --workspace /absolute/private-parent/new-workspace --proposal /absolute/private/proposal.json
```

Proposal 是 UID 擁有、0600、單一 hardlink 的 bounded JSON（≤20000 bytes），不是
authority。恰含 `operation`、UUID `item_id`、`candidate`、`restore_revision`。
Add/update candidate 沿既有 [version contract](../scripts/memory_governance_contract.py)；host 重建
created_at／validation evidence，再由 operator 審查實際內容與完整固定 artifact。
Stop/resume candidate=null、restore_revision=null；restore candidate=null，指定
正整數 retained revision，host 從真實 retained 內容產生新的 revision／evidence。
未知 operation、extra fields、duplicate keys、無效 revision 均拒絕。

每次新程序依序接受 `INSPECT`、內容採納操作的 `REVIEW`、`QUALIFY`、`REQUEST`，
以及核心完整 preview 的 `ADD/UPDATE/RESTORE/STOP/RESUME` digest。Stop 不採納
內容，不要求 Git source 可用；resume／restore 重新審查來源。每次準備最長 300秒，
UTC／monotonic／PID 皆重查；等待不持 DB 或 provider lock。輸入 digest 前應完整
核對內容、適用前提、敏感性、operation/item/revision、容量與 before/after state。

Agent 操作時每次命令均明示 `--actor agent`，透過真正 foreground terminal 完整
讀取 preview 後才輸入當次 action/digest，不能注入 test callback、盲目匹配 token
或重播保存的答案。有效使用者委派可涵蓋一個有界操作序列，仍逐操作接受與讀回；
委派不代表模型必然判斷正確，也不授予無限期、背景或跨專案權限。

因 current-only recall 驗證可能涉及相同 cue 的其他 active item，本版內容操作
最多審查 16 active items、17 versions、16 distinct artifacts；超限明示拒絕，不
宣稱能在整個 10000-item profile 全負載下操作。Stop 不受來源 review 限制。

以新 reader/core/read-only connection 讀回 proof、最新 state/revision、retained
versions 和 current-only projection。`applied`、`not-applied`、`unknown` 分開；
`local_entry_qualified` 只標本次受限成功，`full_mg1_qualified=false`，通用
`production_qualified=false` 保留未取得完整 MG1 資格的語意。容量不足安全拒絕，
不保證滿庫 stop。SQLITE_FULL 等錯誤處理使用獨立讀回，不重播或推定 rollback。
輸出遺失不自動再執行；本版無持久 confirmation／跨程序 handle 恢復。

Generic `governancectl maintenance`／Desktop Python adapter 仍只接 trusted dispatch；
static production host registry 保持空。本固定 CLI 在選定 actor 當次接受後建立本次 RAM
host，而非從 registry JSON 升權。Desktop 使用公開互動終端執行同一 CLI；沒有
native 人類確認 port 時不宣稱原生 Desktop mutation 已驗收。
