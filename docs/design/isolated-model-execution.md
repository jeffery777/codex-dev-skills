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
