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

Contributor、設定 guard 與 source/readback 差異另見
[工具註冊與設定對帳設計](app-server-tool-inventory.md)。該清冊是固定 source 的
工程設計，不能替代當次完整 registry 或 production qualification。

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

此 probe 不使用現有登入、自架或官方模型，也不提供 worker bridge、完整工具
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
不能由此宣稱來源不可達時的完整官方 fallback 或自架來源最佳模型品質驗收完成。真實 reader、
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
自架模型實際能力與 context、CLI／Desktop／bundled／Linux 入口及訂閱登入安排
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

## R2 完整執行模式（saved fixture 接線）

實體 backend 的非空 checkpoint／存活 quarantine／唯一整合器控制另見下方
[N3 固定接手控制](#n3-非空-checkpoint存活舊-worker-與唯一整合器控制)。兩條模式
不能互換 authority 或把 saved runtime proof 升成 OS 證據。

`SyntheticExecutedLifecycle` 在新 packet 使用 `admit-bootstrap`、固定 R2 protocol／
recipe／domain 與 explicit phase 閉集合；flat／R1／B1 journal 均拒絕。共用 private
hooks 的預設行為不改舊模式；B1 仍只到 bootstrapped。R2 原六類 evidence、
execution schema 1／2／3 與 acquire binding 原樣封存。只有新的 launch-intent
將 supervisor binding 推導成完整鏈，另保留 acquisition binding；鏈包含原
plan／descriptor／input／bootstrap intent／receipt 及 actual committed launch ref
digests。沒有 descriptor 回填或任意 worker command 入口。

Launch 先保存 immutable artifact，再由同一次效果獨占建立 running／excluded
genesis。只有此 running genesis 與完整 saved chain 才構成 fixture 已啟動；
launch artifact 單獨存在時 inspect／後續 state observation 拒絕，不補造 genesis。
這是 saved fixture 定義，不是 OS process 或 model service 啟動證據。模型 outcome
須已有 independently read-back、authenticated runtime observation；bootstrap／
partial launch 的 infra 不確定狀態不改成 service／quality failure。

可信 host 另保存 bounded immutable runtime events，最多 64 筆。每筆綁完整
runtime binding、launch artifact、sequence 與 predecessor；inspection 讀取全部
實際檔案，拒絕 gap／分叉／partial／偽造 genesis，不採 writable head。
獨立 schema 2 runtime proof 使用 R2 domain、ordered event hashes 與最新 digest；
observe／publish／finish 的原始 proofs 都在 journal 投影建立 monotonic frontier。
目前及 retained-writer inspection 必須包含此完整 frontier，不能以尾端遺失後的
舊 stopped prefix 產生新鮮 authority。Archive replay 仍只用原 bytes／原時間，
frontier 欄位篡改會因 projection 不符拒絕。Fixture inspection 的 host clock 與
60 秒 expiry 不代表 OS 停止租約或自架模型 freshness。

Prepare／bootstrap／launch／export 都先持久化 intent，再重新檢查 source、目前
authority／qualification／context 與真正 journal 歷史能力。在同一 packet fence
和 backend FD／inode／identity 下執行固定檔案效果；lost reply 只 reconcile，
新 operation 不能重做 phase。Export 只建立固定空 patch，publish／finish 在其他
reader gates 後再獨立核對當前 runtime exact bytes；running／unknown／未排除外部
效果不能發佈或釋放 owner。沒有原生 source 整合器接線或實際 source adoption。

Stopped 且 independently sealed output 才能保存 checkpoint；failed 且 isolated 的
fixture 僅 quarantine 並沿用 predecessor。既有治理 event／safe finish／下一次
actual acquire 保持同 journal、預算、stage／tier floors 與 source identity。
Schema 3 HSG 使用所有真實原 acquire 六類 bytes 及其最高 tier，不接受 B1／flat
歷史匯入或手製 acquire ref；schema 2 first-official unused TTL 例外仍受目前完整
destination／context／authority gate 約束。原模型恢復不奪取既有 owner。

本模式固定建立 private fixture files／空 patch，不啟動 worker、Docker 或任何
模型，不載入憑證、不調用 provider。OS containment、production reader／canonical
objective uniqueness、sole-integrator 續作、完整工具與 credential 邊界、CLI／
Desktop／bundled／Linux 及真實模型品質／context qualification 仍分開驗收；不能
用合成完整鏈宣稱 production 或 release readiness。

## N1 脫離程序及再次啟動的固定控制

`verify-model-isolation.py --lifecycle` 在既有檔案／FD／socket 正反控制外，
另使用固定 Python supervisor 留住 container PID 1。Launcher double-fork／setsid
後退出，脫離 writer 重新由 PID 1 收養；host 讀回完整 image／command／mount／
policy，並以 engine process inventory 核對唯一 supervisor 與其 Python child。
Writer marker、supervisor 的 live check 與 host inventory 是不同觀察；缺任一
控制或未完成實際嘗試不視為通過。Writer 先成功寫 private copy，再實際嘗試
source／checkpoint／sibling 的固定 path write；每輪完成後核對 host canary。

只對本 probe 新建且已讀回 exited 的 exact container ID 再次 start。第二輪
需新的實際 StartedAt、process inventory、執行標記與完整靜態 policy readback；
不以 RestartCount 或 PID 數字單獨證明新啟動。程序有期限並自行退出，沒有
stop／remove、daemon restart、image pull 或使用者 repository 效果。

Receipt 綁 probe／engine executable／image 及觀察到的 engine 身分，保存
兩輪 runtime／process readback。Inspect artifacts 只保存驗證所需的白名單欄位，
排除 `Config.Env`、labels 及不必要的 diagnostics。Writer 自己讀 private cgroup v2 的 CPU／memory／
PID 數值，與 engine inspect 交叉核對；缺失保持 unknown。這只證明讀回數值，
不是資源耗盡／壓力測試或完整祖先限制證明。Own-write positive 驗證相同 write
primitive 可用，但沒有將 protected exact paths 刻意 mount 的獨立 positive。

這些固定控制不能證明任意 descendant、Docker daemon／host 重啟、Codex native
tools／config／credential 或 production 接手資格。Production registry 仍空，
正式 N1／N2／N3／N4 仍須完整證據；實測收據與 inspect artifacts 保存在 Git 外。

## 匿名原生 CLI 的容器候選

N2 另採固定 image／binary 的乾淨容器執行 `codex exec`，以容器內 loopback
合成 Responses provider 驅動 native dispatcher。Host 不掛載 source、登入資料或
daemon socket；唯讀 executable 與該次 private scratch 分開。入口先用 `env -i`
清除 image environment，再提供固定匿名 HOME／CODEX_HOME。這不需要真實自架模型
或訂閱登入，也不由 host app-server 缺少全工具 deny 入口推定不可行。

此路徑仍須在啟動前盤點 image 內 system／managed／project 設定；exec 的兩個
ignore flags 不代表忽略全部 layers。Synthetic Direct model entry 可在固定完整 catalog
中新增專用 fixture entry，保留官方 entries；不修改官方 context defaults，亦不將
fixture 的 context 值當作自架來源容量證據。真實 target 仍須核對 input／output／total、
reasoning 與 handoff payload 預算，不能因合成 provider 接受 request 就取得資格。

Inventory 必須同時綁定 source-derived registration、有效 model／features／environment、
MCP／extensions／dynamic contributors、每輪 structured advertisement 與實際 dispatch。
Hidden、deferred、namespace advertisement 過濾與 Code Mode 的工具可能仍保留於
registry；namespace 省略、空字串與 `functions` 的 canonical identity 另須對帳。
此外 native exec 內的 `apply_patch`／`applypatch` interception 與 argv0 路徑必須列為
可達能力，不能從獨立 patch handler 未廣告推定沒有 patch 能力。
來源：[組裝](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/spec_plan.rs#L123-L187)、
[dispatch](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/registry.rs#L491-L600)、
[exec interception](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/tools/handlers/unified_exec/exec_command.rs#L378-L404)、
[argv0](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/arg0/src/lib.rs#L97-L120)。

資格矩陣逐項包含允許工具正控制、canonical／carrier 負控制、native session、巢狀
CLI、hooks／project config 與 escalation。Container 內沒有額外 CLI sandbox 的固定
測量僅適用該 synthetic scratch；不能弱化正式 runtime 的權限契約。Provider 與 CLI
共用 fixture UID 的 observer 不能充當可信 production exporter。版本／help 或少量
exec／patch 成功均不完成 N2；unknown 與未測項保留，production registry 仍空。

`verify-model-container-native.py` 是 opt-in macOS Docker 的固定匿名 CLI 測量，
只接受已存在的固定 Linux arm64 binary 與 image；不下載、登入、拉取、停止或
刪除資源。Host 在啟動前建立固定 28-case recipe，拒絕 worker 回報的空案例、
子集合、重排或篡改 expectations；逐筆核對 exact continuation、scratch bytes、
精確拒絕與每輪三工具 advertisement，並核對前後 engine／policy／mount 身分。
Context 名稱不能證明本機目標；程式先讀回並核對目前使用者的標準 Desktop
Unix socket，以該 endpoint 固定 transport，拒絕 SSH／TCP、socket 或 engine
身分漂移。證據根目錄僅允許 owner／mode 已核對的系統 `/private/tmp`，不接受
共享子目錄或 symlink 祖先；每次新建的 private 目錄保留，不覆寫舊結果。
來源 binary 以有界 regular-file descriptor 讀取，只有固定公開 SHA 符合的 bytes
才保存至新 private 目錄的單一唯讀副本；container 掛載副本而非原輸入路徑。
Create／start 前再核對副本身分與內容，原檔後續替換不影響本次測量；host owner、
root 與 Docker daemon 屬可信邊界，這不宣稱能抵抗它們改寫副本。
它涵蓋 exec／custom patch 的四種 default namespace、排除名稱、非預設 namespace、
exec heredoc patch、明確 argv0／hidden-arg patch 及升權拒絕。這不是完整 registry
或 startup config fence；此 CLI 使用預設 `local` environment，不能與 app-server
候選的明確 `environments: []` 混用。Provider 與 CLI 仍共用 fixture UID。

測試程式與 recipe 是 tracked 工程產物；實測 inputs／outputs、inspect、收據與
advertisement 在 Git 外的獨立 private temporary directory。重跑產生相同 28 個
語意 assertions，container IDs、路徑、時間及相關 hashes 可改變。使用既有固定
官方 0.159.3 Linux arm64 executable 的絕對路徑：

```bash
./scripts/project-python -m unittest tests.test_model_container_native
./scripts/project-python scripts/verify-model-container-native.py --binary /absolute/path/to/codex --evidence-root /private/tmp
```

此命令只適用已核對的 Mac Docker 測量 tuple；不推定 bundled CLI、Desktop、
Linux host、其他 image／binary 或官方登入支援。完整有效 layers、nested CLI、
hooks、sessions 與可信 observer 仍須各自驗證；既有 session 局部測量不由本
28-case probe 取得完整資格。所有 qualification flags 維持 false。

## N1 exact-path 讀寫對照

`verify-model-isolation-path-controls.py` 另建固定 Mac Docker 控制：三份全新 synthetic
canary 分別代表 source／checkpoint／sibling，全部留在經核對的 private temporary
root；不掛載實際 repository 或使用者資料。兩個不同 own containers 使用同一
image、UID、program、target arguments 及政策。正控制僅額外掛載三個 canary file
至其 host exact absolute paths；host 核對實際 read、write、readback 及自然退出，
才可用核對過的 descriptor 重設原 synthetic inodes。負控制使用相同 paths 與
read/write primitive，但不掛載 canaries；每項都實際嘗試 read 與 write，僅
boundary errno 可接受，EIO／ENOMEM 等未知結果不可算通過。兩輪各有獨立 workspace
讀寫正控制，host 再核對 canary bytes／identity、精確 mount／policy 與 engine。

未知正控制結果不得 reset 或啟動負控制；create／start 不重播，receipt 保留在
Git 外。既有 isolation probe 的單 workspace mount 契約不變。這只補三個固定
paths 的 read/write 對照，不代表 rename／link、resource enforcement、daemon／
host restart、native Codex、credentials 或完整 N1／production qualification。

```bash
./scripts/project-python -m unittest tests.test_model_isolation_path_controls
./scripts/project-python scripts/verify-model-isolation-path-controls.py --evidence-root /private/tmp
```

## N1 固定 PID 上限控制

`verify-model-isolation-pid-limit.py` 使用同一已核對的本機 Docker transport 與固定
image，另建沒有 host mounts 的 own container；固定 UID1000、private PID／cgroup、
network none、唯讀 root、PID 上限 32、memory／CPU 上限及 restart no。它不是任意
負載工具，上限控制階段最多嘗試 32 次 fork，含正控制整輪最多 33 次；不做 host
process exhaustion 或 memory／CPU 壓測。

Python PID1 明確安裝 30 秒 deadline handler，逾時 exit 124 不算成功。先核對單一
task、private cgroup v2 與 `pids.max=32`／`pids.current=1`，再以 readiness 管道、
單一 child 正控制及 EOF／wait 回收確認 `1 → 2 → 1`、events 不變。正控制不完整
不得開始上限控制。上限控制須有 31 個不同且已回報 readiness 的 children、第
32 次 fork 精確 Linux EAGAIN（11，不使用 Mac host errno）、current 32、
`pids.events` 與 `pids.events.local` 的 max
各增加一次；EAGAIN 單獨不足以通過。釋放所有 children 後逐一 wait exit 0、回到
current 1，計數不得再變。計數表示 tasks；本 fixture 是單執行緒的固定程式。

Host 核對 exact CID、前後完整 policy、沒有 host bind／volume mounts、自然退出／PID0／非 OOM 與
engine 身分。缺 counter、異常格式、清理不完整、逾時或 unknown 都不得算通過；
create／start 不重播，結果留在 Git 外的全新 private 目錄。此觀察不歸因是哪層
cgroup 導致拒絕，也不宣稱完整資源隔離、restart、native CLI／credentials 或 N1／
production qualification；全部資格 flags 仍 false。

```bash
./scripts/project-python -m unittest tests.test_model_isolation_pid_limit
./scripts/project-python scripts/verify-model-isolation-pid-limit.py --evidence-root /private/tmp
```

重跑重建固定 fork／counter／wait assertions，CID、PID、時間與路徑可不同；測試
程式及反例 tracked，實測收據、inspect 與 outputs 不納入 Git。

## N2 匿名 project config／hook 正反控制

`verify-model-project-hook.py` 另用固定 Mac Docker／Linux arm64 CLI tuple 測量一個
project-local `PreToolUse` 路徑。兩個新 own containers 共用固定 image／public binary
副本／程式／UID／CLI argv，各自只掛載唯讀 binary 與全新 synthetic scratch，
network none，HOME／CODEX_HOME 留在容器內。沒有登入、自架來源設定或真實 provider。
Fixture source 以單次 bounded regular-file descriptor 擷取；host recipe 由同一份
bytes 載入，兩輪執行與最後收據的 program hash 都使用該 immutable memory snapshot，
不在每輪或結束後重新讀來源檔。Host owner／root 與 daemon 仍為可信邊界。

先逐項盤點固定 Linux system／managed、CODEX_HOME、cwd 與 ancestor config 位置的
metadata；有既存檔案、symlink 或非 canonical 路徑時，在執行 CLI 前停止。這份
清單只涵蓋固定 local candidates，沒有完整 cloud layer／effective config readback。
受控 user config 提供匿名 loopback provider、fixture-only Direct entry、project
trust 與 `features.hooks=true`；保留官方 catalog entries／context defaults。
不使用 `--ignore-user-config`，`--strict-config` 只對未知欄位 fail，不代表全 layer
隔離。`--sandbox danger-full-access` 只用於此無登入的固定容器 scratch，不能用於
正式派工或降低其 sandbox ceiling。

Project config 的單一 matcher `^Bash$` hook 執行固定 Python 程式，寫出 bounded
stdin event。Hook 的 registry 名稱與 `tool_name=Bash` 為不同層；預期事件是
`PreToolUse`、`tool_input={"command": <固定命令>}`。Host 固定唯一 exec call、兩次
Responses requests／exact continuation、每輪三工具 advertisement、tool marker，
並對照實際 project config bytes、前後 CID／mounts／policy／engine／自然退出。

兩輪 project hook 與其 self-trust state 完全相同；user state 的 normalized
trusted hash 在正控制精確相符，在負控制則刻意不相符。沒有 hook-trust bypass。
正控制須觀察一次 hook event 與 tool 效果；負控制須沒有 hook event，但原 tool
仍執行成功。這只支持本 tuple 的 user trust 正反樣本，以及 project state 不能
替自己的 hook 建立信任；未信任 hook 是略過，不是拒絕原 tool 的 deny gate。
Hash 依固定公開 source 的 normalized handler／TOML／canonical JSON 計算，不能
用原 TOML bytes 的 hash 代替。來源：[state layers](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/hooks/src/config_rules.rs#L8-L29)、
[hash](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/hooks/src/engine/discovery.rs#L775-L791)。

未知 positive 不啟動 negative；create／start 不重播。這不完成 startup closure、
完整 registry、其他 hook failure modes、native sessions／nested CLI、credentials
或可信 production observer；provider／CLI／hook 共用 fixture UID，所有 qualification
flags 保持 false。Source 與反例 tracked；inputs／outputs、收據、inspect 位於 Git
外的 private temporary root，重跑重建等價 assertions，ports／CID／時間可不同。

```bash
./scripts/project-python -m unittest tests.test_model_project_hook
./scripts/project-python scripts/verify-model-project-hook.py --binary /absolute/path/to/codex --evidence-root /private/tmp
```

## N2 匿名 native terminal session 控制

`verify-model-native-session.py` 在新的固定匿名容器中啟動兩個獨立 CLI，
分別使用不同 loopback provider、HOME／CODEX_HOME。只有同一份已擷取的公開
binary 唯讀掛載及本次 private scratch 可寫；沿用固定 image、UID、pids 64、
memory 512 MiB、network none 與 exact policy。無自架模型、登入或其他 host mounts。
此固定測量仍使用既有匿名容器的 `danger-full-access`，不是正式 CLI 權限預設
或 sandbox 失敗時的 fallback。

工具 `session_id` 是當前 CLI Session 的 process manager ID，不是 `thread.started`
的對話 UUID。它可在釋放後重用；只接受本輪固定 exec call 原始 continuation
的 header 所帶 ID，再對帳各 CLI 的 UUID、固定 call sequence、當輪 continuation、
model 與工具宣告；不宣稱完整 request 或所有 input 的 byte 對帳。
只解析第一個 `Output:` 之前的 native string header，不從正文的假 header
擷取身分；非本包的 MCP carrier 拒收。工具宣告完整比對既有三項 identity、
namespace、type 與 schema，不能把 advertisement 當作完整 registry。

A 只啟動一個有 20 秒期限的 TTY 程式，先產生 `SESSION_READY` 並等待固定一行。
B 在尚無 terminal 的另一個 CLI 中，實際嘗試向 A 的 ID 寫入不同控制字串，
須收到 exact unknown-process error。A 隨後空 poll，不能再收到已消耗的 READY；
只傳送一次核准的固定輸入，要求唯一 ACK 與 scratch marker。若該回應仍 running，
只允許一次有界 final poll；必須讀回 exit 0 且無 running ID，下一次同 ID poll
才要求 unknown。不能以 ACK、背景 end event 或 CLI shutdown 取代自然工具退出。
Parser 保留原始正文；chars 與 final poll 合併後只正規化一次 CRLF，包含換行
或 ACK 跨回應切分；額外的 CR 必須在所有切分位置一致拒絕。
合併內容只能是一次固定 ACK，及至多一次固定輸入的 TTY echo。

`--mode non-tty` 使用另一個固定程式：先確認 stdin EOF，產生 READY 並等待
scratch 中的固定 release。B 仍須拒收 A 的 process ID；A 空 poll 後嘗試一次
固定非空輸入，要求 exact closed-stdin error。下一次空 poll 須讀回同一 running
ID 且沒有重複 READY，確認拒收輸入沒有被誤解為程序結束。匿名 provider 此時
才把固定 release 完整寫入同目錄 staging file、flush／fsync，再用 hardlink 單次
發布 final path；既存 final path 不覆寫，失敗不重播，兩個 links 保留。Host 核對
完整固定 bytes、長度與同一 inode，避免 worker 讀到尚未寫完的檔案。
程式產生唯一 ACK／marker 並自然退出；允許一次 final poll，
最後要求 closed-ID unknown。Non-TTY 不能包含輸入 echo，release 也不是模型
工具或可信 production control。來源：[non-TTY input guard](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/unified_exec/process_manager.rs#L983-L991)、
[closed-stdin error](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/unified_exec/errors.rs#L20-L22)。
Schema 2 把 terminal mode 納入收據與 host 預期；不能用 TTY 證據替代 non-TTY，
舊 Schema 1 證據保留為原版本的局部紀錄，不由新版 validator 重新背書。

B 先到達 provider，A 身分與 B exact continuation 以有界 barrier 交接；
不依 assistant 完成文字解開 barrier。A／B subprocess 分別限 35／30 秒，
整個 fixture 的 PID 1 使用明確 SIGALRM handler，50 秒即失敗退出；SSE idle
15 秒不是整體期限。TTY 至多八個 requests；non-TTY 至多十個，增加拒收輸入後的
live poll 與固定 release 後的 poll。每種模式至多一次 final poll，不重送 exec、
chars 或未知結果。Create／start unknown 只記錄及讀回 exact CID，不 replay。

這只量測固定 TTY／non-TTY、消耗式 poll、一次輸入或 closed-stdin 拒收、自然退出、
跨 CLI 與 closed-ID 正反控制。Non-TTY interrupt、nested CLI、截斷、完整 config／registry、credentials、
restart 與可信 production observer 仍另行驗證；provider／CLI／terminal 共用 UID，
`native_session_qualified` 與 `production_qualified` 固定 false。工程 source、
反例與方法 tracked；raw requests／outputs、收據及 inspect 留在 Git 外。重跑
重建同一組 assertions，session／thread IDs、ports、CID 與時間可不同。

```bash
./scripts/project-python -m unittest tests.test_model_native_session
./scripts/project-python scripts/verify-model-native-session.py --binary /absolute/path/to/codex --evidence-root /private/tmp
./scripts/project-python scripts/verify-model-native-session.py --mode non-tty --binary /absolute/path/to/codex --evidence-root /private/tmp
```

## N2 匿名 nested CLI 配置與環境局部控制

`verify-model-nested-cli.py` 沿用已驗證的 public CLI bytes、固定本機 Docker
image／policy，只有 read-only binary 與本次 synthetic workspace 兩個 mounts。
Parent P 的原生 `exec_command` 啟動固定 wrapper；wrapper 先 READY 等待，
provider 從原始 header 取得 live ID 後，完整寫入／fsync staging file，再以
不覆寫 hardlink 單次發布 release。兩個 child C+／C− 依序各啟動一次新
`codex exec`，使用不同匿名 HOME／CODEX_HOME、cwd、provider port 與 thread UUID。
Wrapper 原樣保留實際收到的原生環境，只修改 child 的 HOME 身分；未知鍵先
停止查明，不剔除 guard、重送 spawn 或偽裝 argv0。

C+ 由受控 user `config.toml` 取得唯一 model canary，argv 不覆寫 model；
C− 保持同一 user config，由固定 argv 覆寫成另一 fixture model。實際 Responses
request 必須讀回對應 model。安全設定、匿名 loopback provider、catalog、feature
開關及工具 recipe 由固定 argv 約束。這只核對選定 user model 與 argv precedence，
不宣稱完整 effective layers；startup candidates 的 absence 也不是完整 config inventory。

Parent 與 C+ 用 `inherit="all"`、明確 `include_only`、`exclude=[]`、`set={}`，
保留 default sensitive-name exclusion；C− 只改 `inherit="none"`。固定 synthetic
marker 僅由 parent 啟動環境提供，wrapper 不補值。兩個 child 的原生 tool 各自
讀回 marker 存在／缺席及自己的 `CODEX_THREAD_ID`，不能把 launch intent 當成
實際 tool env。`include_only` 之後仍有原生身分與 unified-exec 固定鍵注入，
因此不宣稱 tool env 恰好只有 allowlist。Source-derived 規則綁定
[pinned TOML schema](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/config/src/shell_environment_policy.rs)、
[環境建構](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/protocol/src/shell_environment.rs) 與
[原生 tool 注入](https://github.com/openai/codex/blob/01fc69f4026735edfdf6789820549727a4867b11/codex-rs/core/src/unified_exec/process_manager.rs)。
這是固定 source contract 的查讀，不是 package build attestation 或完整 nested guards 清冊。

每個 child 在建立自己的 terminal 前，先空 `write_stdin` 使用 P 的 live ID，
要求 exact unknown-process error，再實際執行固定 probe。Probe 先完成自身 scratch
讀寫，才以相同 open/read/write primitive 嘗試三個未掛載的 host source／control／
sibling canary paths；write 不用 `O_CREAT`／`O_TRUNC`。Host 保存並重讀 canary
identity／mode／size／hash。這只測量本次未掛載 paths，不能推定任意 filesystem
或所有 descendant 的隔離。Parent tool 僅回短 ACK；host 另讀 child 原始 JSON
stdout／stderr、user-config bytes 記錄、exact call-ID/output continuation、
per-turn advertised schema 與 container inspect。Advertisement hash 不稱為 registry hash。

PID 1 整體 50 秒，parent CLI 35 秒，wrapper 32 秒，每個 child 12 秒，release 等待
六秒；parent 至多一次 exec 加 24 次空 poll，各 child 固定兩次 tool calls。
這些固定期限包含自然退出驗證；timeout、spawn unknown、截斷、缺原始證據或
自然 exit 未確認均不通過，unknown 不 replay。已觀察到 canary 變更／開啟或
marker 控制違規保留 failed，另記生命週期 unknown。Create／start intents 先
保存，結果未知只能讀回 exact own CID；不刪除資源或重啟 daemon。
Probe 以逐筆 flush／fsync 的有界 observation journal 保存原始 marker 與每次
canary 操作；後續 EIO、截斷或期限不能抹去已綁定的先前反例。Host 讀回 unavailable
保持 unknown，只有確切 identity／bytes mismatch 或已記錄違規才標 failed。
父層 wrapper 也先 flush／fsync 保存原始 marker、source／call 與 native thread 綁定，
才判定 marker；缺席／錯值造成早期停止時，不因尚無 child journals 而降為 unknown。
缺觀察、錯誤 source／thread／call 或讀回 unavailable 不能製造 failed 或 pass。

Provider、CLI、wrapper、probe 共用 UID，都是固定 fixture evidence，不能作為
可信 production observer。`handler_inventory_complete`、`startup_isolation_qualified`、
`nested_cli_qualified`、`production_qualified` 固定 false；窄欄位
`fixed_nested_cli_controls_passed` 只表示上述 controls。Credentials、restart／revocation、
完整 registry／config、Desktop 與 N1–N4／production 資格仍另行驗證。工程方法與
離線反例 tracked，原始 readbacks、host-only receipt／canaries 留 Git 外；重跑
重建同一組 assertions，UUID、SID、ports、CID、路徑與時間可不同。

```bash
./scripts/project-python -m unittest tests.test_model_nested_cli
./scripts/project-python scripts/verify-model-nested-cli.py --binary /absolute/path/to/codex --evidence-root /private/tmp
```

## N3 非空 checkpoint、存活舊 worker 與唯一整合器控制

`verify-model-packet-integrator.py --checkpoint-overlap-only` 明確選取新的固定
匿名案例；不改既有八個 B2 案例，也不把 R2 saved backend 換成 Docker。
Host 只建立本次 private synthetic Git source、packet、三個 attempt 的獨立
workspace／control volume／own CID。沿用 host 選定且已安裝的 image、固定
root-latch launcher 與降權 worker，沒有登入、provider、使用者 repository 或
production registry；資源及原始收據保留 Git 外，不 cleanup 或重啟 daemon。

Seed 用 `add-update` 封存非空 checkpoint C，尚不整合 source。A 從 C 執行固定
35 秒 `hold-overlap`，host 核對 exact physical identity／policy、實際 `holding` 效果及
running state，才能 quarantine；quarantine 不宣稱停止 A，也不擷取其活躍半成品。
B 用 `noop`，但保留同一 `add-update` scope／驗收，只能從 C 的 immutable bytes
建立新副本。B 的累積 patch、workspace files、predecessor 與 C 的原始 manifest／
patch bytes 須相符，CID／workspace identity／control volume 須與 A 不同。
因此錯用空 baseline，或把 A 的 `holding` 帶入 B，均不能通過。

B 成為 candidate、整合前及整合後仍須由 host 讀回同一個非 zombie／dead 的 A worker。
Container init running 不等於 worker 存活；每次以 exact CID 的 bounded `top`
對帳 root PID、唯一 child 的 PID／PPID／UID／process state／固定 command，要求
四次 worker PID 相同、實際 `holding` 階段及 root control 的 input／claim 原始
綁定相符且無 completion。Control tar 僅接受固定 USTAR directory 與兩份 regular
files，拒絕 links、額外 entries、metadata／JSON 漂移，不解壓至 host。
每次 readback 前後核對 physical policy；有八秒期限，底層同步呼叫可能跨期限，
但到期結果只能 unknown，不能通過。固定 hold 不 fork／替換 worker、可信 host
無其他 exec／signal，是這個有限存活證明的前提。沒有建立時間
重疊就回報未完成，不把停止後結果稱為存活接手。原有 15 秒 `hold` 不變；新的
35 秒固定 recipe 只供本匿名 overlap 測量，低於既有 launcher 的 40 秒 alarm；
僅核對實際讀回期間的重疊，超出窗口只能 unknown，不宣稱永久存活。不接受任意
timeout／命令，亦不重啟已退出的 worker。固定
FixtureGovernance 讀回 host-issued source authority；唯一 PacketIntegrator 才
能將 B 合格累積 patch 寫入 synthetic source。A 的晚到 reconcile、admit、publish
與 integrate 分別要求確切 gate 拒絕；原 source 在 B 整合前須保持 baseline。
整合結果及完整 postimage 另讀回，reconcile 禁止再次 source write。

未知 prepare／start／export／write 不重送；缺 top、格式／phase／completion 未知、
child 已結束而 root 尚 running、隔離失效、checkpoint 漂移、未建立
重疊或 authority 撤銷不能取得成功收據。Root ledger 保留原 intent／結果，不因
此測量失敗而 rollback 或重做原 operation。離線反例不在 host fork 或連 Docker。

```bash
./scripts/project-python -m unittest tests.test_model_packet_integrator_runner tests.test_model_packet_integrator
./scripts/project-python scripts/verify-model-packet-integrator.py --synthetic-qualified-container-fixture --checkpoint-overlap-only --endpoint unix:///absolute/path/to/approved.sock --image sha256:APPROVED_INSTALLED_IMAGE --evidence-root /absolute/path/to/private-evidence-root
```

這是固定 recipe 的實體合成組合控制，不是完整 N3、真實模型／原生 CLI 接線、
全域 objective authority 或 production qualification。Fixture validation/review
artifacts 不代替正式 review；formal gate 仍獨立執行，qualification 維持 false。

## N1 Mac 原生 socket 正反控制

`verify-model-permissions.py --network-controls` 在既有原生背景程序案例後，
分別測量 TCP、UDP 與私有 Unix socket。它不需要 Docker、provider 或登入；
controller 以專案 Python 執行，固定 C client 由已存在的 system compiler 建立。
Mac client 的 linked libraries 只接受 `/System/` 或 `/usr/lib/`，不擴充原
filesystem profile 的可讀路徑。缺 compiler、編譯失敗、未知 linked library 或
Unix socket 路徑過長都保留 unknown。

可信 host 為每個 transport 建立同一個 listener：TCP／UDP 僅綁定 loopback
的 ephemeral port，Unix socket 留在允許寫入的私有 workspace。正、負階段
使用不同 nonce 與單調時鐘期限；兩階段的固定 client、binary、工作目錄、
環境及 filesystem 設定相同，只切換 `network.enabled`。Mac client 使用
`mach_absolute_time` 與所選 Python 的時間域對齊；Linux 控制測試使用
`CLOCK_MONOTONIC`。這些輸入由 host 固定產生，不接受模型提供的程式或目的地。

正控制須由 host 獨立收到一次 nonce、回傳精確 ACK，且 client 在期限前核對
成功，才執行負控制。TCP／Unix 的負控制只接受 `connect`、UDP 只接受
`sendto` 本身的 `EACCES`／`EPERM`；connection refused、reset、timeout、
程序失敗、重複／逾期 nonce 或缺 readback 不能當成隔離成功。Host 保持觀察
到負階段期限並完成 observer 停止讀回；負階段任何 stream accept 或 nonce
收件都是 counterexample。Observer lifecycle 不明時保留 unknown 並停止
建立後續 listener。Receipt 同時核對固定 client／CLI 的 bytes identity。

執行時應使用已存在、Git 外且路徑長度足以容納 Unix socket 的私有 evidence
目錄；原始收據與診斷留 Git 外。重跑重建相同 assertions，nonce、port、
timestamp、私有路徑及 build identity 須重新核對，不要求逐 byte 相同。
純邏輯反例另涵蓋錯誤分類、缺失／重複／過期證據、觀察期限不足及設定漂移；
無 sandbox 的實際 client 必須因 host 收到負控制而失敗。

這只測量固定 no-fork client 的本機 socket 操作，不涵蓋任意 IPC、CLI builtin
tools、credentials、daemon／host restart、完整資源限制或其它 runtime。
七項原生背景程序控制與三種 transport 的局部成功均不建立完整 N1；
production registry 與 qualification flags 不由此開啟。
方法及反例 tracked，raw readbacks／ledger／receipt 位於 private Git 外位置；重跑
重建相同 assertions，CID、nonce、時間與各次授權身分不要求相同。
