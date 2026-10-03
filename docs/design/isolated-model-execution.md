# 隔離模型執行與可信接手

Issue #316 的 N1–N4 設計候選。此文件定義待實作及待資格化的邊界，
不代表 runtime adapter 已啟用；production 清冊仍須維持空，直到完整驗收。

## 控制面與寫入面

可信監督器持有 packet ledger、generation、已封存 checkpoint 與成果整合權。
模型服務與官方訂閱的登入由控制面處理；模型可呼叫的寫入工具只能作用於
當次 attempt 的隔離副本。官方訂閱入口不能改成付費 API fallback。

候選 bridge 使用固定 stdio MCP 協定接收工作操作，再交給本機 Docker 或
rootless Podman 的受限 worker。MCP 只是 transport，不提供隔離保證。
bridge 不接受模型指定 host command、engine socket、mount、credential path、
container flags 或動態工具清冊；shell 文字只在固定 worker 邊界內執行。
既有 packet ledger 與 generation 契約仍是唯一接手狀態，不另建重試狀態機。

Host client 的模型工具須受獨立的作業系統 enforcement 限制：來源副本僅唯讀，
控制面、登入資料與其他 attempt 不可由模型工具讀寫。預設 deny，再逐項給予
必要權限；不得把授權給 provider client 的登入能力同時給 worker。
這是待驗證要求，named profile 的設定值本身不能證明成立。

若無法證明上述控制面與工具隔離，bridge 只能進行無憑證的合成實驗，不能
接入真實 provider。另一候選是 provider client 本身也放在受隔離環境，並由
可信 credential broker 提供最小登入能力；其公開介面與訂閱支援須另行資格化。
此設計不預設未公開的訂閱 API 或任意 credential forwarding 可用。

## 公開 CLI 限制

以下呼叫鏈核對固定 `openai/codex@01fc69f4026735edfdf6789820549727a4867b11`
（0.159.3），不推定其他版本、bundled CLI 或 Desktop 同樣成立：

- `shell_tool=false` 阻止 shell handler 註冊；`unified_exec=false` 單獨使用
  不能證明所有 exec 停用。patch 的註冊另由 environment 與 model metadata
  控制，不能靠這兩個旗標排除。
  [工具註冊](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/spec_plan.rs#L1079-L1116)。
- 此版本的 feature normalization 在沒有 managed requirement pin 時強制
  啟用 `UnifiedExec`；普通 `features.unified_exec=false` 仍會讀回 `true`。
  因此，要求所有指定 features 為 false 的嚴格驗證須保留 unknown，不靠
  調整參數順序或修改全域 managed 設定放行。
  [固定版本 normalization](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/config/managed_features.rs#L153-L161)。
- `PreToolUse` 有效 deny 在 patch handler 之前執行；但 hook 的執行錯誤、
  無效 JSON、逾時等失敗不保證阻擋工具。hook 僅作額外防護，不能承擔唯一
  隔離邊界。必須測試 hook 失敗時 host sentinel 仍不變。
  [失敗語意](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/hooks/src/events/pre_tool_use.rs#L193-L290)、
  [工具呼叫順序](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/registry.rs#L603-L655)。
- `--ignore-user-config` 不會同時設為忽略 project configuration。Host client
  不以可寫 worker checkout 為配置探索根；啟動前核對固定 CWD、祖先配置、
  instructions、plugins、hooks 與有效設定層，漂移時拒絕啟動。
  [CLI overrides](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/exec/src/lib.rs#L364-L370)、
  [project layers](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/config/src/loader/mod.rs#L337-L407)。

不能只依送給模型的 tools schema 判定 handler 已移除；native metadata 未解析
時尤其不能建立完整工具清冊。須驗證 provider 強制回傳未宣告或已停用工具時，
runtime 仍拒絕副作用；未資格入口不能放行。

Native request 的工具宣告也可能位於 `input[].type="additional_tools"` 中，並以
namespace 包住 function／custom tools。驗證器須解析此結構與頂層 `tools`，
不能從一般文字或 TypeScript 描述推定 handler 已登錄。Receipt 分別保留
advertised tools、固定 forced calls 與實際 dispatch outcomes；Code Mode 或 agent
即使仍出現在 native 宣告中，也不能因 feature flag 值而略過。公開的
model-visible input 不是完整 runtime handler inventory；缺乏完整讀回時保留
`handler_inventory_complete: false`，有限負向矩陣不開放 production adapter。

另行明確啟用的無憑證合成觀測，可以記錄該固定版本強制啟用的
`UnifiedExec` 及其餘指定 features 的實際狀態，再量測固定呼叫的 dispatch
結果與檔案副作用。它不能取得原本「全部停用」契約的資格，也不證明完整
handler inventory、Code Mode、agent 或登入資料隔離；嚴格模式不自動切入此觀測。

## 公開 app-server 的受控工具候選

另一條候選使用公開 `codex app-server --stdio`，由 host 接收固定 dynamic tool
呼叫，再交給隔離 worker。固定 0.159.3 schema 的 `thread/start` 與 `turn/start`
均明確傳入 `environments: []`；省略此欄位不能作為沒有執行環境的證據。
Dynamic tools 仍是 experimental API；必須先 `initialize` 並宣告能力，再送出
`initialized`。此候選不依賴 Desktop 私有介面。
[公開協定與版本化 schema](https://developers.openai.com/codex/app-server)。

`model_app_server_transport.py` 提供 host-only、有界 stdio primitive：限制 frame、
總 bytes、messages、notifications、outbound bytes 及 I/O 等待；嚴格關聯 RPC ID，
拒絕重複 JSON keys、非有限數字、未知 server request、額外工具及重播 call。
已知 approval request 回覆 deny 後仍鎖定 unknown，不自動續行。未知結果不
重試、重啟或推定停止；`close()` 只觀察 direct child，descendants 永遠保留
unknown。Callback 必須是可信且有界的 host code；同步 primitive 不能中斷
任意 Python callback。它不提供 JSON loader、sandbox 或 production adoption。

公開的唯讀設定、requirements、feature 與 MCP status 方法另可用於匿名觀察。
`model_app_server_metadata.py` 限制頁數、列數及 cursor，拒絕重複或未知結構；
只保留固定來源類別計數、指定公開 feature 的實際 boolean 及必要狀態，不保留
完整配置、路徑、provider secrets 或 requirements 內容。MCP 配置非空或未知時
在 status/discovery 前停止，不能把空 overlay 當成已清除 lower layer。
Feature 缺席不補為 false；即使列舉完成，仍不證明全部 handler 已停用。

`verify-model-app-server.py` 使用獨立匿名 HOME／CODEX_HOME、本機 Responses
fixture、唯讀 client directory 及單一固定 `packet_probe` 正控制。它驗證真正
function／custom carrier 的十個負控制，包含 Code Mode、agent、權限請求、
stdin 與未知 dynamic tool；使用精確拒絕文字及相同 turn 身分核對結果，亦核對
CLI version、binary digest、thread configuration、sentinel 及 direct child exit。
工具仍出現在 model-visible 宣告時，不能以宣告取代實際 handler 拒絕證據。
Probe 亦停用 legacy `notify` 及 `agents.enabled`，CodeMode 使用單一
`features.code_mode_host={enabled=false,disable_in_process_fallback=false}` override；
不能使用不存在的頂層 `code_mode` key，或先 boolean 後 dotted key 而遺失
`enabled=false`。上述只適用固定版本，須由有效 readback 另行查證。

此 probe 不使用現有登入、公司或官方模型，也不提供 worker bridge、完整工具
清冊、配置／resume 漂移、credential broker 或 production authority reader。
Receipt 固定保留 `handler_inventory_complete: false`、`production_qualified: false`；
不得將有限矩陣提升為正式隔離資格。真實訂閱接入前，仍須逐項驗證所有 host
callback、MCP／extensions／hooks、Code Mode helper、子代理、網路與憑證入口。

固定版本的 app-server 不提供 exec 的 `--ignore-user-config`／`--ignore-rules`。
獨立 `CODEX_HOME` 只切開 user config／auth storage；system、managed／MDM、cloud、
project 與祖先設定仍須啟動前盤點。事後 `config/read` 排除 package defaults，
thread feature readback 又可能重新載入配置，故 receipt 保留
`startup_isolation_qualified: false` 與 `thread_snapshot_verified: false`。
不能將有效設定觀察提升成啟動前防線或既有 thread 快照證明。

正式訂閱接入的候選是由官方登入流程直接 provision host 管理的專用
`CODEX_HOME`，讓設定與 worker 可寫範圍分開；不複製、symlink、抽取或轉送
既有 `auth.json`／keyring token。公開介面未提供另一個獨立 auth root，專用
登入與管理設定盤點尚待採用者確認及資格驗證；匿名程序不需要登入。
來源：[固定 CLI dispatch](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/cli/src/main.rs)、
[公開設定 schema](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/config.schema.json)、
[原生 auth storage](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/login/src/auth/storage.rs)。

可重跑命令（須允許啟動本機 loopback fixture）：

```bash
./scripts/project-python -m unittest tests.test_model_app_server_transport tests.test_model_app_server_metadata tests.test_model_app_server_probe
./scripts/project-python scripts/verify-model-app-server.py --evidence-root /private/tmp --case code_mode
```

其他固定案例由 `--help` 的 `--case` 列表選取。Evidence root 必須在 Git 外；
每次建立獨立私有目錄，保留 raw synthetic requests 與 receipt，不覆寫舊失敗。
重跑可重建同一組 assertions；臨時路徑、port、IDs、時間與 hash 可因輸入變化。

## 準備與啟動契約

1. 從核准 source／checkpoint 建立獨立副本；不以硬連結或共享 Git 可寫資料
   複製。核對 symlink、inode aliases、路徑與機密排除，不能只比較目錄名稱。
2. 在啟動前固定完整隔離條件及目標身分。關閉非必要 inherited FD，worker
   environment 不包含 provider 登入或 host ambient credentials。
3. Worker 不掛載 engine socket、控制面、其他副本或憑證；預設無網路、唯讀
   root filesystem、最小身分與 capabilities，並有可讀回的資源及生命週期限制。
4. Bridge 每次派工重新核對 packet、attempt、generation、target、隔離身分
   與撤銷狀態。回覆遺失或逾時保留 `unknown`，不推定未執行、不盲目重播。
5. 無法確認停止時，只能隔離舊 attempt 並拒收晚到結果；隔離及外部效果排除
   讀回合格後，新副本從上一個可信 checkpoint 接手，不讀舊環境即時半成品。
6. 封存、驗證及 review 後，由唯一整合器核對 source HEAD、scope、generation
   與 artifact digest，才採用成果。模型恢復不搶占目前工作單元。

## 最小資格矩陣

| 面向 | 必測案例與通過條件 |
| --- | --- |
| Hook 故障 | 有效 deny、runner error、timeout、invalid JSON；host 資料皆受 OS 邊界保護 |
| Handler | shell、exec、write_stdin、patch、Code Mode、agent、額外 MCP；禁止入口無副作用 |
| 配置 | 祖先及巢狀 `.codex`、AGENTS、symlink、plugins、額外 hooks；有效設定及輸入無漂移 |
| Bridge | path traversal、額外欄位、任意 mount／argv、動態工具；拒絕未知或超範圍請求 |
| Worker | nested CLI、socket、網路、FD、hardlink、background child；無 host 或 sibling 權限 |
| 恢復 | crash、lost reply、舊 generation、未停止 writer；不重播、不發布 stale 成果 |
| 登入與資料 | 先用合成 canary；worker env、stdio、logs、artifacts 不含登入資料；實際訂閱與 provider 另驗 |

先以合成 provider／canary 完成最小案例，再擴大到 N1–N4 正式資格。
每次變更只重驗受影響邊界，重用內容及假設未變的證據；不逐項重跑全量。
最終 latest head 的完整 base-to-head Merge Review 及專案 gate／CI 不省略。
原始證據與 review 收據不進 Git，位置與重建規則見
[工程計畫](../plans/issue-316-local-model-mapping.md)。

## N3-A 的持久監督介面

`model_packet_supervisor.py` 使用由可信 host 注入的 backend，不從模型 JSON
載入 module、command 或停止證明。Runtime 身分及 launch intent 先寫入既有
packet ledger；launch 與 quarantine 使用同一 fence。恢復只 inspect 該身分，
不重新 launch；export 回覆遺失時只讀回原封存 artifact，不重新 export。

Unknown observation 與查證後 resolution 保存在同一 ledger，綁定 attempt、
generation、runtime 與 revision。紀錄有界且不保存敏感診斷全文，容量滿時拒絕
繼續發布。Candidate 讀回在同一鎖內重新核對 canonical checkpoint、sealed
bytes 及當前 fence；空 patch 也適用相同身分、隔離及停止條件。

`integration-candidate` 是受控封存成果，不代表品質審查通過或 source apply
授權。後續 N3-B1 提供固定合成 recipe 的本機 Docker backend：先 create，將
physical container descriptor 封存於同一 ledger，才 start exact ID。恢復不
重新 create／start，created、missing、running 或身分漂移不視為已停止。
Export 由可信 host 受限走訪 regular files，不執行 worker Git；連續 checkpoint
保留相對原 source 的完整成果。Host-only isolation adapter 僅供 opt-in fixture，
production 清冊及一般 dispatcher 的預設維持空。

共享 daemon 的首次 `StartedAt` 讀回不能證明原始那次 execution；手動 restart
也不能只靠 `RestartCount` 偵測。缺乏可信原始執行身分或單次執行控制時，保留
physical-container／隔離觀察與 unknown，不以首次時間觀察發布 candidate。
單次執行 qualifier 須有獨立驗證，不能由新 flag 或自填證明開放。

這一階段尚未提供任意模型工作、唯一來源整合器、daemon／Desktop restart、
credential broker 或 provider 資格；固定 container recipe 的實測不能替代它們。

## N3-C 單次執行候選設計

以下是固定合成候選實作的設計，仍待完整資格化。可信 root launcher 在每個 attempt 的獨立
持久 volume 建立 root-only claim，再降權啟動 worker。Claim 使用固定 dirfd、
`O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`，完成檔案及目錄 fsync 後才允許
worker 動作。已有 claim、部分寫入、fsync 失敗或回覆遺失均不能刪除後重試。
這只能保證 worker body 至多執行一次，不保證一定執行或一定完成。

Claim 與 completion 分別封存，綁定 packet／attempt／generation、source、scope、
acceptance、launcher、image、policy、volume 及 physical descriptor。手動 restart
必須在 worker body 前拒絕，不採用首次 `StartedAt` 作為原始 execution 身分。
此邊界不防護具有 Docker 管理權限的惡意 host 修改 volume 或 root exec；可信
host 的權限與控制介面仍須排除於模型可用工具之外。

Physical descriptor 先封存，再由 host 建立含其 digest／CID 的固定 input。
Input digest 另記於同 ledger 的 bootstrap receipt，不能回寫 descriptor 形成
循環。對從未啟動的 exact container，先持久化 bootstrap intent，核對空的
root-owned control volume，寫入固定 input 並讀回完整 bytes／metadata，再
持久化 input-ready／start-intent，最後重查 generation 與隔離身分才啟動。
`docker cp` 不是 exclusive create；此準備階段依賴同 packet lock、單一 host
writer、尚未啟動的 worker 與可信 daemon。任一階段結果不明只允許查讀，不
補送 cp 或 start。Launcher 自讀 input 中的 CID 不構成獨立證明，必須由 host
封存 descriptor、input 讀回及 receipt 鏈共同驗證。

Worker 的 supplementary groups、real／effective／saved UID/GID 與 capabilities
均須清除，關閉控制 FD，設 `no-new-privileges`。清除 capability bounding set
需要 launcher 暫時持有 `CAP_SETPCAP`，不能只加入 `CAP_SETUID`／`CAP_SETGID`
便宣稱完整降權。Launcher 只使用固定 image、絕對程式路徑、isolated Python、
argv、environment 與工作目錄；不載入 worker workspace 的 module 或設定。

Volume 必須有唯一 attempt 身分、固定 local driver、空 options 與 `volume-nocopy`；
恢復時缺失或被替換不能重建。停止後讀回 completion 只允許 exact container 的
固定路徑，輸出以有界單一 regular-file tar parser 解析，不解壓縮到 host，拒絕
link、額外 entries、路徑逸出、重複 JSON keys 與截斷內容。

Launcher 等待直接 child 不等於背景程序已停止。Candidate 仍須有完整 container
停止、隔離、外部效果排除及 generation fence；缺 completion、duplicate-start
拒絕或任一 binding 漂移均不能發布。必要測試包含 lost reply 後首次 inspect 前
restart、claim／fsync／fork／completion crash、worker 控制檔存取與 FD 逸出、
child／grandchild 降權、volume／image／policy 漂移，以及 detached child 未停止。

`OneShotSyntheticContainerBackend` 與 `model_container_launcher.py` 提供上述固定
recipe 候選；同一 ledger 的 supervisor schema 4 與 descriptor schema 2 保存
bootstrap 三階段 immutable chain。恢復須讀回實際各階段 artifact、input、
claim 與 completion；舊 schema 可讀，但不能補造新證據或升級既有 attempt。
`model_control_archive.py` 僅解析固定 USTAR／JSON 結構，不授予 candidate 或
整合權限。實際 launcher／隔離／停止證據仍由 backend 與 generation fence 核對。
此候選尚不包含真實 provider、daemon restart、一般模型工具或 production adoption。

## B2 唯一成果整合器的最小驗證範圍

`model_packet_integrator.py` 已實作下列有限 fixture，不能直接用於使用者的工作目錄。可信 host 建立
clean、獨占的 synthetic Git source；首包只接受有界 regular text files 的新增或
更新，拒絕刪除、rename、binary、symlink、hardlink、submodule 與特殊檔案。
整合權來自 host 注入的 source-writer capability，綁定固定 source、scope、
ownership 與可撤銷授權；模型或 JSON 的 `approved: true` 不能建立此能力。

整合器須讀回實際 canonical checkpoint／sealed patch、當前 generation、source
HEAD 與完整 preimage，並驗證綁定同一成果的固定驗收及 review fixture artifacts。
這些合成 artifacts 不代替正式 code review，也不建立 production 採用權。先在
trusted staging 算出 expected postimage，再固定 source lock／packet fence 的
取得順序，將 operation identity、candidate／authority digest、preimage／postimage
與 integration intent fsync 到同一 ledger，才寫入 source。不同 packet 指向
相同 source 時也必須共享 source-level 單一 writer；advisory lock 本身不防護
未受管控的其他 writer，所以初始 fixture 必須排除它們。

恢復只讀回原 operation，不重新 apply。確認原 writer 已無法繼續修改後，
完整 postimage 可證明 applied；完整 preimage 加上可信未套用證據才可證明
not-applied；其他狀態保留 unknown。多檔案寫入不是檔案系統交易，部分完成
不能自動 rollback 或覆寫 dirty files。空 patch 也須保留相同授權與綁定收據。
必要案例包含 authority／review 偽造、撤銷、source drift、generation 漂移、
不同 packet 競爭、回覆遺失、中途 crash、path aliases 與未知結果不重播。

整合狀態使用同一 packet ledger 的 schema4；intent、write intent 與結果保留
原 observations。公開讀回須核對 canonical binding 的型別與 bytes、實際
checkpoint／patch digest，以及當前 host／backend／policy，不能只核對 artifact
自己的 digest。恢復只 inspect／read，不重播 apply。任何 integration record
均阻擋下一次 claim，包括 applied；整合後的新來源續作契約仍須另行資格化。

## 未知結果的規劃讀回

`ResolvedUnknownGuard` 是 host-only advisory seam。它在同一 packet lock 內
核對原事件、完整 ledger、隔離或 descriptor-backed 停止證據、實際封存 bytes，
並另讀可信失敗原因。Quarantined attempt 使用 predecessor checkpoint；沒有
predecessor 時須有獨立保存的初始 source bytes 與 canonical manifest。取得
封存成果或確認隔離不等於已確認可重試服務錯誤或能力不足。External effects
仍未知、缺失原因、任何 source integration record 或證據漂移均保留 blocked。

判斷用 cause overlay 不修改原 events、時間、correction 與預算。HSG 回放
schema3 dispatch artifact 時核對原 request digest 及獨立封存的 exact prior
resolution bytes；現在的讀回不能事後補造原 dispatch 的合法性。任一已查證
原因屬於 auth、permission、config、context 或 secret，現在與歷史回放都拒絕
fallback。Schema2 不補造 unknown-prefix resolution。此 seam 沒有 JSON loader、
production reader 或 dispatcher；規劃通過仍為 `dispatched: false`。


## C1 持久治理的首包契約

`model_packet_governance.py` 已實作同一 objective 的 host-only evidence／read／projection；
已通過限定範圍的獨立深入審查；不接 public dispatcher，也不建立另一份 retry journal。Objective 綁定 canonical repository、
原 task／scope／acceptance 及可信 authority；work unit、model 或 HEAD 不建立
新預算，HEAD 漂移沿用既有 conflict。不同 task ID 不自動視為新 objective。
Module 只保證單一 ledger 內的治理；跨 task aliases／packets 的 canonical
objective 唯一性與新 objective 採認，必須由外部可信 authority reader 獨立
保證。Production reader 尚不存在；另建 packet 不能自行取得新預算或派工權。

原 outcome、resolution、V2 classification、ownership 及 health 證據均保存
實際 immutable bytes，綁定 request／attempt／generation／policy。在同一
PacketStore lock 內核對 prefix、CAS，先 fsync artifact 再更新 ledger pointer；
孤兒 artifact 不採認，重複 operation ID 只在 bytes 完全一致時冪等。
Projection 從完整證據重建；它不是新 authority，也不延長資格或授權 TTL。
服務失敗、返工、缺陷 lineage 與 elapsed budget 沿用完整原 events；cause
resolution 只疊加已驗證原因，不改事件、時間或計數。

Capability class 保持不變；累積 required-tier floor、quality-tier floor、品質
stage floor 與既有 forward-only stage 下限分別保留。完整有效 V2 prefix 中
較高的 required tier 在 release、health 更新及重啟後仍是後續 acquire 的下限。
服務 fallback 不提高品質 floor；同 tier 也不能退回已確認不足的 stage。
單一 ledger 最多一個 active unit，綁定 owner epoch 與 attempt generation；
跨 packet 的同 objective 排他性仍依賴上述可信 reader。
健康恢復只更新證據，不更換 owner；結束或接手仍須停止／隔離、effects 及
有效 authority，timeout 或 cooldown 到期不能奪取寫入權。

Cooldown 綁定 exact target identity、原觸發事件、policy、開始及截止時間。
到期只產生 recheck-required；新鮮 healthy 證據不能清零預算、降低 floor 或
解除 active writer。時鐘倒退、未來時間、撤銷、unknown 及禁止 fallback 的
原因均保守拒絕，較晚 health 不能遮蔽它們。

治理狀態使用 ledger v5；dispatch-envelope version 另行管理。
首包只採認既有空 schema2 packet；v5 的 top-level generation 保持 0，attempts
保持空。Owner reservation 不代表實際 executor claim，不能拿來證明已派工。
舊 reader／writer／supervisor 拒絕 v5，專用治理 API 才能讀回或追加；artifact
及 ledger write 均在效果前核對，不能降版以繞過治理。
Schema2／3 dispatch 與 proof bytes 保持唯讀，不補造治理 snapshot。Legacy
缺證據回報 unavailable，不能視為零次失敗或建立替代 packet。所有能修改新
ledger 的舊入口必須遵守 ownership／CAS，否則拒絕；整合後續作 blocker 保留。
首包排除跨 packet 共享 health、反向 stage 恢復及既有非空 packet 治理遷移。


## 交易持鎖的規劃接口

`PacketStore.planning_context(fd)` 提供 host-only、交易限定的 legacy snapshot。
Caller 必須持有該 store 的既有 lock；V2 classifier、unused／historical source
與 resolved-unknown guards 在同一 context 規劃，不另取鎖。每次入口及完成後
重新走完整 root／ancestor nofollow，核對有效 lock lease、仍持有的 lock FD／
inode、當前 lock path、directory identity 與原始 ledger bytes；copy 回傳值不能
更改 snapshot。離開交易、同 operation 的 prefix 漂移、換 store 或 path 置換
均拒絕。Context 不是 authority，也不進 JSON、公開 CLI 或 production registry。

這個前置接口仍只讀既有 v2–v4。v5 保守拒絕；v6 實際接線須有完整原始 journal
回放與 projection 比對後的新 context。Acquire 必須在唯一一次持鎖交易內核對
完整 history、目前權限／資格／floors／cooldown，使用原 actual execution request
選模，再 fsync 原始 bytes 並原子提交 owner、attempt、supervisor。不能在鎖內
呼叫會自行取鎖的 claim、reserve_runtime 或 governance append。

v6 首包必須包含 acquire → once-launch → unknown reconcile → checkpoint →
release → qualified successor，並驗證 lost reply／crash 不重播 launch 或 export。
原治理 request 與 actual execution request 有各自 digest；歷史以明確 attempt ID
及原 acquire prefix 關聯，不用 failure events 的 list index 代替 generation。
正常 completed 為 objective terminal，不造 failure 或重設預算。撤銷後可信 host
仍能記錄 containment／unknown，不能啟動新模型或採用結果。非空 v2–v5、dirty
source、未知 external effects、缺失隔離或原始 evidence 都保留 blocked。


## v6 完整 synthetic lifecycle 候選

`model_packet_lifecycle.py` 將原治理 evidence 與實際 execution claim 接在同一
ordered journal。Attempts、supervisors、checkpoint 均從原始 artifact 完整回放，
核對 canonical projection bytes；任一缺檔、symlink、digest、request、prefix 或 projection
漂移都拒絕。V6 使用獨立 code-only write token；舊 reader、writer、supervisor、
integrator 與 v5 治理 API 不能據此取得執行能力，也不能降版繞過。

`admit_new` 只接受獨立採認的空 v2 packet，保存可信 host 的初始 source bytes
及 canonical objective locator。不同 alias 必須讀回同一 root／packet／objective／
authority，不能另建 packet 重設預算；真實全域 authority reader 仍未資格化。
Source dirty 或 baseline 漂移先阻擋，不 stash、reset 或 clean。

`acquire_attempt` 在唯一一次持鎖交易中回放完整治理，核對目前權限、V2
classification、服務預算、quality／required floors、health、原始 events、目前
隔離／停止及逐模型 context，選模後一次提交 owner、實際 attempt 與 supervisor。
治理 request 和實際 execution request 各自保存原始 bytes；後者綁定 acquire 前
prefix、目標、前一 checkpoint、host／backend／runtime policy 及 runtime ID。
啟動只消費這份已封存的 execution bytes。

Launch／export 先提交 intent，再做至多一次 backend 呼叫。Intent commit 或回覆
遺失後，重試與重啟僅讀回原 operation；reconcile 只 inspect，不重新 launch 或
export。停機證據與失敗原因各自核對；原 unknown event 保留，resolve 只提供經
驗證的 cause overlay。未排除 external effects 不釋放 owner，也不採用成果。
Stopped runtime 的 sealed patch 與 checkpoint 先 fsync 再發佈 pointer；隔離仍活著
的 writer 只可 quarantine，保留前一 checkpoint 或已保存的初始 source，不能
採用它持續變動的最新成果。新 acquire 重新確認全部 retained writers 的停止／
隔離仍有效。

Acquire 通過不延長來源、權限或隔離的有效期限。Launch／export 的 backend 效果前，
以及 publish／finish 提交前，重新核對來源 baseline／dirty／scope／acceptance、
完整 prefix 的 sticky revocation 及全部 retained writers 的新鮮停止／隔離證據。
隔離失效或 effects 未排除時保留 owner，禁止新效果與成果採用；snapshot／
containment observation 仍可讀回。Export intent 已提交但未取得封存成果時，
可透過獨立 isolated observation 與原 failure outcome 丟棄本輪成果、quarantine
並沿用 predecessor；不重播 export，也不補造 checkpoint。

`finish_attempt` 將 release 與實際 attempt 結果一起提交。Failed 結果必須有原始
outcome；正常 completed 是此 objective 的 terminal，不偽造 failure、不清除
lineage／floor／budget，也不表示 repository DoD、review、merge 或 release 已完成。
Revoked 模型權限仍允許有效 host recording authority 做 snapshot／containment
observation，禁止新啟動、export、採用與 release。Health 恢復不能搶占 owner。

此包僅接受 host 注入的 synthetic reader／backend，descriptor 與 bootstrap 關閉；
沒有 CLI／JSON loader、production registry、Docker／app-server worker 接線或 OS
隔離資格。Execution schema 1 要求來源資格新鮮；後述 schema 2 接線僅提供
V6 未使用來源的 TTL 例外，legacy unused／historical tier 例外仍保守阻擋，
不能由此宣稱回家時的完整官方 fallback 或公司最佳模型品質驗收完成。真實 reader、
provider、credential broker、原工具 inventory 與跨入口 qualification 仍需後續接線。


## v6 未使用來源的交易契約（合成接線）

這個擴充處理 source slot 0 從未 actual acquired、其能力資格僅 TTL 過期，且
availability 仍為新鮮 unavailable 的情況。它涵蓋第一次 official acquire 與
同 official stage 的後續 retry；不是只要求整個 packet 的 generation 為 0。
原始 source ID／identity 固定於 admission 與各份 execution；任何原 acquire
以相同 ID 或 identity 使用來源，即使未 launch、沒有 outcome 或已 quarantine，
都不能採用這個例外。缺少原 execution、owner 仍存在或 isolation 未確認均拒絕。
這個來源錨定限制只用於 schema 2 的例外邊界；schema 1 不新增 admission target
等於 planning source 0 的要求，也不因此拒讀既有合法 journal。

沿用 V2 classifier／selector；legacy unused guard 不變。新私有 V6 guard 僅
接受 forward replay 產生的不可變 prefix capability，綁定真正 store、交易 lease
及 full-ledger fence。它只表示特定 source 尚未 acquired，不替換實際 ledger
snapshot，不可由 JSON、structural token 或 validated=true 建立。每份原 execution
按其 acquire 前的 owner／完整 journal 事實回放，不以 failure index 代替 generation。
Legacy／V6 unused guards 同時提供時拒絕。

Execution schema 2 內保存一份 canonical UTF-8 原 proof；schema 1 不接受新增
欄位。Proof 有獨立 V6 domain，綁 packet／objective／policy、pre-acquire prefix、
operation／attempt／runtime、治理 request、原 planning／effective decision、source
identity／qualification／availability、destination、authorization 及 secret check。
Execution core digest 排除 proof 欄位，避免自我雜湊；外層 authority 再綁含 proof
的完整 execution bytes。Proof 與整份 execution 均有大小限制及嚴格型別。

每次新 claim 都由獨立 host reader 讀回自己的新原始 proof，與 execution 內
bytes 完全相等；第一次 proof 不授權第二次 acquire。Historical replay 只讀原
archive、按原時間驗證，不查今天的 proof、不遞迴 full replay、不再次取鎖。
新效果仍使用目前的 destination 資格／availability／executor／context 與 authority
讀回，綁實際 execution request、當前 prefix 及原 task；source proof 不延長
目的地資格，也不以單一 qualified boolean 取代完整 context budget 檢查。
目前來源 qualification 的 observed_at 必須不晚於 now；TTL 豁免不能接受未來證據。

例外僅略過 source 的 qualification TTL。Revocation、identity／scope／class／tier、
authority 漂移仍阻擋；source 成為 destination 或沒有 candidate 時不使用例外。
Destination 的授權、訂閱 billing、公開 executor 及完整 input／output／reasoning／
margin／client context 限制仍須新鮮通過。Official retry、service count／elapsed、
quality lineage／floors、predecessor 與 retained-writer gate 保留；耗盡照原政策停止，
不藉此重設預算。此契約不處理 historical-tier exception 或 production qualification。


## v6 歷史能力需求的交易契約（合成接線）

Execution schema 3 擴充前述 schema 1／2：只對已 actual acquired、且不再作為
本次 destination 的來源，使用當時同一 objective／class 的最高原能力需求。
來源曾被 admission、events 或 health 提及不構成使用證據；未 launch、被 quarantine
或沒有 outcome 不會抹除 actual acquire。Owner 未釋放、completed terminal 或
品質返工尚未達門檻時仍拒絕接手。提高分類 tier 本身不改變 stage。

Forward replay 在原始 acquire 驗證通過後，保存六份原始 evidence bytes 與完整
ordered acquire references；私有不可變 capability 以真實 store、lease、full-ledger
fence 及 acquire 前 prefix 綁定這份歷史。逐來源核對原 request、V2 classification、
identity、stage、原時間下完整 destination qualification 與 authority，包含目前
已符合新 tier、不需要例外的所有原 acquired targets；使用同來源
所有原 acquire 的最高需求，不能選較早較低的一輪。Aggregate 原 acquire bytes
上限為 8 MiB；proof 上限 16 KiB，execution 維持 256 KiB 上限。缺檔或漂移拒絕，
今天的 callback 不能補造原證據；回放不遞迴 full replay 或再次取鎖。

Schema 3 的 `historical_source_bytes` 保存 canonical 原 proof；domain 為
`v6-historical-source/1`。Proof 綁定原 acquire manifest、來源需求與 qualification、
本次 classification、planning／effective decision、完整 prefix、operation／attempt／
runtime、execution core、destination、authorization 及 secret exclusion。
只有 own proof 欄位不納入 core digest；authority 仍綁含 proof 的完整 execution。
每次新 claim 都要求 `readback_v6_historical_sources` 獨立讀回相同 canonical bytes，
完整 coverage、新鮮 granted／qualified 證據；前一輪 proof 不授權 successor。
未被 selector 消費的 proof 拒絕。Schema 3 不與 unused／legacy guard 混合；
舊 schema 1／2 與 legacy selector 契約保留。

Source exception 僅調整能力 tier 比較，不豁免 freshness／future time、revocation、
identity、scope、class、authorization 或 secret check。Schema 3 不延用 schema 2
source slot 0 的 TTL 例外。Destination 一律符合目前完整分類需求、公開 executor、
訂閱 billing 與 input／output／reasoning／margin／client context 限制；live context
reservation 不可縮小原估算。Claim、launch／export 前後、publish／finish 的目前
qualification gate 只接受 replay 產生且綁 exact execution 的私有 typed capability，
不接受 JSON 的 old-tier map。服務 attempt／elapsed、quality／required floors、
未知 cause overlay、predecessor、retained writer containment 與 recovered model
不得 preempt 的規則維持不變。

此接線仍限 synthetic host／backend，沒有 production registry、真實 credential
broker、provider／Docker writer 或使用者 source integrator。測試可重建固定案例
與 assertions；安全分析／獨立 review 結論另由原生收據保存，不能宣稱可逐 byte 重建。
公司模型實際能力與 context、CLI／Desktop／bundled／Linux 入口及訂閱登入安排
仍需各自驗收。

## R1 執行準備模式（合成接線）

`SyntheticPreparedLifecycle` 是 host 明確建構的獨立模式，首筆 immutable
`admit-prepared` 綁固定 protocol／recipe／runtime policy／saved backend instance。
同一 v6 journal 的 structural validator 依首筆選擇閉集合；flat host 拒絕 prepared
模式，prepared host 拒絕 flat 模式，沒有既有工作包遷移、JSON backend registry
或 v4 capability flags 包裝。只有已驗證的 admission entry 副本正規化為治理
`admit`／空 payload；保存的 record、ref、digest 與六類 evidence artifacts 不變。

R1 順序限定為 `admit-prepared → acquire → prepare-intent → prepared`。
Acquire 仍只是 owner／generation reservation，不建立資源。Host 先產生 canonical
plan，將 operation／prefix、actual execution／request／runtime binding、固定 mode、
nonce／logical control、source／objective／scope／acceptance／predecessor 保存到
原 authenticated record 的 payload；每段 artifact 上限 16 KiB。Intent 必須先
durable commit 並讀回，再通過同一 full-ledger fence 與目前完整 source／destination／
authority／context gate，才至多一次呼叫固定 saved backend 的 `prepare`。
Physical instance descriptor 只能在建立資源後，依實際保存的檔案獨立讀回。

Saved backend instance identity 綁 private root inode 與持久 nonce；重新建構同一
host instance 可核對，其他實例、寬鬆權限、symlink／hardlink artifact 拒絕。
每次效果及 readback 都在持有的同一 backend directory FD 驗證原 inode／identity，
並在效果後核對 path 與 identity；原 bytes 被複製到替換目錄也不被接收。
Descriptor 綁原 plan／runtime／mode／control／nonce 與實際 fixture instance。
`prepared` 再獨立讀回 descriptor 及新鮮 observation 的 exact bytes，核對所有
binding 後保存。Observation 可另產生 immutable receipt 更新觀察時間，不覆寫
原證據、不重新 prepare；callback 的回傳值本身不構成確認。

已提交 operation 只以 actual immutable archives、原時間與完整 fence 回放；不
呼叫今日的 locator／authority／evidence／destination／backend。新 operation ID
不能重做同一 phase。提交後讀回或效果失敗、lost reply、partial／absent resource
都保留 intent 與 owner；descriptor 只代表 `created`，不證明 stopped／isolated／
never-started。原始 bytes 缺失或漂移不能由今日 readback 補造。

共用 execution schema 1／2／3 parser 與原歷史規則保留；prepared 模式的 schema 1
也必須通過目前完整 destination／source gate，schema 2 僅保留核可 unused TTL
例外。R1 沒有 release／多次 acquired 歷史鏈，因此不宣稱 schema 3 的完整正向
prepared 續作已驗收；新工作包缺 actual history 時仍拒絕。

Bootstrap、launch、runtime observation、outcome、export、publish、finish、cancel
及 successor 在 R1 全部拒絕，infra 不確定狀態不換成模型失敗或清空預算／floors。
本包只建立 private saved fixture files，不啟動 worker／Docker／provider，也沒有
credential broker、source integrator、OS／CLI／Desktop／bundled／Linux 或 production
qualification；完整準備／啟動／接手鏈仍需後續接線。

## B1 固定 bootstrap 模式（合成接線）

`SyntheticBootstrapFixtureLifecycle` 使用獨立 `admit-bootstrap-fixture`、固定
`synthetic-bootstrap-fixture-journal/B1` protocol 與 `saved-bootstrap-fixture/B1`
recipe。六類 phase 為 admission、acquire、prepare-intent、prepared、
bootstrap-intent、bootstrapped；與 flat／R1 的 admission、backend exact type
及 protocol 閉集合互斥。不升級既有 journal，也不預先開放 inherited launch 或
治理入口。後續完整執行模式必須使用新 mode 與新 packet，重新建立完整證據鏈；
B1 的 descriptor／receipt 不能直接作為新 packet 的 bootstrap authority。

Input 是已封存 plan＋descriptor 的純函式，保存有界 canonical raw bytes，沒有
任意 command、path 或 recipe 入口。先在原 ordered journal 保存 authenticated
bootstrap-intent，完整 readback 後，在同一 packet fence 下重建目前 gates／
historical capability，再至多一次執行固定 saved backend。Backend 在同一 private
directory FD 依序獨占保存 input、actual committed intent ref、receipt；receipt
綁 input 與 intent ref digest，不回寫 descriptor 造成循環。這三份檔案的任一
寫入失敗、partial 或 lost reply 均保留 intent／unknown／owner，不補送 bootstrap。

獨立 observation 綁 input／intent／receipt 與新鮮度，另保存 immutable artifact。
`bootstrapped` 必須將 backend 實際保存的四份 exact bytes 與原 journal projection
比對；成功回傳值不構成 confirmation。新觀察可以另存，不改寫既有 artifacts；
舊 operation 仍只按原 bytes／原時間 replay，不呼叫今日 callback 或重做效果。
Backend inode／identity、private file metadata 與 packet full-ledger fence 均沿用
R1 實體核對，新的 phase ID 不能重做效果。

到 bootstrapped 為止是目前支援的 phase 範圍，不是治理 terminal 或任務完成。
Attempt 保持 unknown、owner 保留；created／bootstrapped／absent 不證明 writer
未啟動或已停止。Launch、runtime observation、model outcome、export、publish、
finish、infra cancellation／successor 均拒絕。沒有 worker、Docker、provider、
credential 或 source adoption 效果；完整同 journal HSG 多次 acquire 正向鏈、
OS containment 及各 CLI／Desktop／bundled／Linux 入口仍待後續完整模式驗收。
