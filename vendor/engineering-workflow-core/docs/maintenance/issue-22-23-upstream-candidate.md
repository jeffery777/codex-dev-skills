# #22／#23 上游規則候選／Upstream rule candidate

## 繁體中文

### 新決策、範圍與版本

使用者於 2026-11-04 釐清 Core 是上游：Core 完成自身必要評估、測試與審查後，可以先採納及發布；Codex 在後續採用時自行驗證，Grok 的驗證、修改與部署等使用者另行通知。這項新決策取代本次 #22／#23 工作先前「Codex 與 Grok 各自 pin 同一候選並通過 eval，Core 才能正式採納」的時點要求，不改寫其他工作包的歷史，也不免除 Core 自身必要審查或公開操作授權。

本工作包把 [PR #31](https://github.com/jeffery777/engineering-workflow-core/pull/31) 的伴讀推進為純 Markdown 權威規則候選。基準 main 為 `7efe4eea59031ed5f9ff9c4a8aef5b8f7d2be02e`，已審伴讀來源為 `521041f413a4020c859c7847eef2ed0415af311b`；本包同時保留兩個基準的每個舊字與完整行序。只有 review-and-security 新增義務，其餘三契約、LICENSE、完整 notices 與既有 release notes 保持原 bytes，不加入 Core executable、validator、runtime API、設定或 consumer 實作。

依 [CHANGELOG 的版本方式](../../CHANGELOG.md)，新增資格與公開檢查義務採下一 minor，準備 [v0.4.0](../releases/v0.4.0.md)，不以只含伴讀的 patch 宣稱兩案原需求完成。版本準備、正式合併、annotated tag、Release、下游採用與安裝分開驗證；本機候選及使用者調整時點，不代表已獲這些公開動作的特定授權。

### 原需求與權威新增

| 項目 | 本包新增與保留邊界 |
| --- | --- |
| [#23 本文](https://github.com/jeffery777/engineering-workflow-core/issues/23)的必要 reviewer 條件 | 在 [review-required-read-only](../../contracts/review-and-security.md#review-required-read-only) 定義所有計入必要 review 的路徑，包含首選與替代者，均不得有能改動受審內容或任務明定受保護資源的有效寫入通道；資格仍不代替實際當前 review。 |
| #23 的有效限制與停止 | 以當次可信控制與生效證據查相關直接及實際暴露 shell／broker 路徑；工具未提供或操作前強制拒絕均須有證據，不能靠角色／brief、Git 未變或另一工具的拒絕。缺必要條件只阻擋相依 gate，不要求全主機不可寫、逐子代理 OS sandbox 或惡意管理員防護。 |
| [#22 本文](https://github.com/jeffery777/engineering-workflow-core/issues/22)及[10/30 補充](https://github.com/jeffery777/engineering-workflow-core/issues/22#issuecomment-6514971936)的公開資料檢查 | 在 [review-publication-data](../../contracts/review-and-security.md#review-publication-data) 定義每次相關操作前的有界檢查，涵蓋內容、原始身分／message／trailers、完整 range、merge／squash 預期結果、commit／tag 的簽章／證書公開資訊，以及實際目的地。 |
| 實際可行的 commit 查核時點 | 建立前查 staged 與預定序列化的公開 metadata／簽署設定，不取得私鑰或密碼；建立後查實際 raw object，差異須在相依公開動作前補查，不能倒稱事前已查到尚未產生的資料。 |
| 原始檢視及目的地 | 不以 mailmap、replace refs 或美化／隱藏簽章的檢視代替原始資料；核對實際所有 push URL／refspec 及 rewrite，非 Git payload 另查。必要預期結果未知則阻擋相依公開，不用 HEAD 檢查或公開後讀回填補事前缺口。 |
| 安全方法與資料 | 有界公開檢查不等同每次跑完整 Security Diff Scan；正式掃描仍依實際風險。保留授權、獨立 review、受控證據與遮蔽，不刪除有來源支持的合法公開身分／完整 notices，不宣稱完整秘密偵測。 |

Core 是文件契約，不提供上述限制的執行器。這次上游驗收檢查規則是否明確、一致且可遵循，不把 Codex #370／#368 的有限交付、工具 help 或文字案例稱為技術控制已生效；下游採用時須另外核對實際介面、資料／權限與相容性。

### 風險與早期設計審查

本包涉及共享 reviewer 資格、敏感資料及公開 gate，按高風險語意變更處理，不能因只有 Markdown 就略過深入審查或必要安全差異掃描。早期獨立深入設計／安全分析已檢查四契約及候選方向：ED-01 要求簽章檢查不得引導取得簽署秘密，ED-02 要求明列所有必要 reviewer 路徑，避免首選／替代者漏洞；兩點已納入候選文字，須由後續完整內容審查核對 closure，不能僅靠作者標示 Fixed。

實際差異出現後，安排新的正式 Security Diff Scan 與完整獨立內容／深入審查，舊 PR #31 的伴讀掃描不能覆蓋新義務。證據綁定實際完整範圍、當前候選及限制；若進入公開 PR 新 HEAD，另做完整 base-to-head Merge Review。正式結果置於受控交接證據，不為在受審檔寫上自身 verdict 而反覆改動內容。

### Core 有界驗收

以下是合成文字契約案例的涵蓋面；獨立判讀以固定候選與案例輸入為準，預期決策在取得回答前固定。這是 Core 自身規則的有限走查，不是 Codex／Grok 的執行驗證、模型等價或技術隔離測試，不能宣稱所有實際接口均可用。

| 案例組 | 必查情境與判準 |
| --- | --- |
| R1–R4 | 只有 brief／名稱、patch 拒絕但 shell 可寫、未知控制、路徑不可用等不能解除必要 gate；無相依安全工作仍可續。 |
| R5–R8 | 有效受限的共用 parent 路徑、尚未實際 review、非受保護 cache 可寫、changed head 等須按所問操作分開判讀，不增全主機限制或沿用舊 verdict。 |
| P1–P4 | 預定 commit metadata、實際新增簽章資料、未查 range／merge 結果、顯示轉換等須分清建立前檢查、原始物件與公開前剩餘缺口。 |
| P5–P8 | 目的地／payload 漂移、單一 PR 文字範圍、不確定寫入、一般低風險修改等，須保留逐次資料檢查、只讀對帳與按風險決定正式掃描。 |
| P9–P11 | 有來源的合法公開 notices、tag 簽章內的未查私人資訊，以及只有發布授權但必要檢查未知等，須區分核定公開、敏感資料及授權與驗收。 |
| A1 | Core 已通過自身必要評估／檢查時，Grok 未驗證本身不阻擋上游內容 readiness；正式公開仍另核操作權，Grok 相容性保持未知。 |

機械檢查對 main 的二十三檔及 PR #31 的二十四檔分別做 raw bytes／完整行序、mode／type 保留；三份未改契約、LICENSE、完整 notices 與歷史 release notes 另驗 equality。比較器的刪字、換字、空白、LF／CRLF、Unicode 正規化、行序、末尾 LF、missing／mode／type 負例須能失敗，正例只新增完整行；語意與完整句子另由獨立 reviewer 核對。新清冊為二十六檔，即二十五份 Markdown 與原 LICENSE，仍須逐檔核對，不能只憑數量認定完整。

公開準備另查完整差異、擬發 PR／Release 文字、實際新 commit 範圍及原始 metadata，不把機械保留或語意測試當成秘密偵測。檢查只在已授權的來源與實際操作範圍內進行，不搜尋或讀取無關憑證／機密文件；可疑值只回報安全位置與類別，原資料留在受控證據。

### 完成標準與下游狀態

本包 Core 完成標準是明確覆蓋原需求、舊字保留、有限規則走查、完整性／引用／保密檢查、必要獨立深入審查與安全掃描，以及每個實際公開階段匹配的授權與讀回。只交付伴讀或僅改版號不滿足這個標準；文件候選審查通過也不等於已合併或發布。

Codex 對 v0.4.0 的正式採用與相容性驗證尚未進行；Grok 的驗證、修改、發行／部署暫緩，其相容性未知。這些狀態不再是本次 Core 上游接受前的雙端 gate，也不能被改記為通過。下游各自採用正式 immutable 版本時，仍須依 [exact-pinning](../../contracts/exact-head-and-evidence.md#exact-pinning) 查來源、清冊、digest、引用閉包、完整 notices、組裝及自身必要驗證，不由 Core 發行自動更新。

### 一次性環境接受與本次授權

使用者後續指定的[具體例外](../../contracts/review-and-security.md#review-required-read-only)限定前述必要 reviewer 有效唯讀前置及相依停止，原本嚴格預設仍保留全部字句。必要用途使通道無法移除時，須有可追溯的使用者接受、特定環境／規則與通道、理由、替代偵測及未涵蓋範圍紀錄，才能沿例外計入必要 review，不建立技術唯讀。每次核對接受仍適用且執行偵測／實際審查，同環境及規則未變不逐次確認；改變則重新接受，偵測到受審內容改動使該次審查作廢。作者獨立、必要安全、資料保護、exact-head 與操作權均保留。

本次核對的 Claude 固定來源為 `c818e4dfd59a92650ba09d3f5d71c6da6a29ee01`：[DL-004／DL-009](https://github.com/jeffery777/claude-dev-skills/blob/c818e4dfd59a92650ba09d3f5d71c6da6a29ee01/skills/dev-core/deltas.md)及 [CB-4／CB-5](https://github.com/jeffery777/claude-dev-skills/blob/c818e4dfd59a92650ba09d3f5d71c6da6a29ee01/skills/dev-core/SKILL.md)明列 Bash 保留、唯讀靠指示，以及前後 HEAD／status／diff hash 比對。來源明列未涵蓋已存在的 untracked 檔內容、ignored 檔、Git metadata 與 repo 外效果；未觀測的改後還原等改動仍可能漏掉，並非技術隔離。它只作使用者指定的有界案例，不移植為 Core 固定工具；使用者表示 Claude 將補一次性接受紀錄，本包未驗證該紀錄完成，不修改 Claude 或代其接受風險。

舊二十案及結果保留；新案例修訂明列 R1／R2／R4 缺有效例外接受，增加接受完整性、同環境重用、環境／規則變更、跨環境／consumer 不轉移、偵測改動作廢與未偵測限制的正反案例。這是新候選有限判讀，不是舊案例 bytes 未變或 runtime 驗證。原字比較另對例外前完整二十六檔查 raw bytes／完整行序保留，並保留既有負例及兩個 Git 基準。

例外改變接受路徑與信任假設，須對完整八檔新候選重做深入內容／安全評估與正式安全差異掃描；先前封存掃描不倒記為覆蓋例外。使用者已授權本次擴充候選 commit、push 及更新現有 draft PR31，新 HEAD 仍須完整 Merge Review；前述缺公開授權的文字保留早期準備階段，不再重問同一授權，亦不授予 merge 或正式發行。Grok 暫緩、相容性未知。

## English

### Decision, scope and version

On 2026-11-04 the user clarified the upstream order: Core may adopt and publish after its own required evaluation, tests and review. Codex validates later adoption; Grok validation, changes and deployment wait for further instruction. This replaces the earlier dual-consumer-before-Core timing for the current #22/#23 work, preserving its historical text and all Core review/publication-authority duties.

This packet advances PR #31's optional guidance into a Markdown authority candidate. Main is `7efe4eea59031ed5f9ff9c4a8aef5b8f7d2be02e`; the reviewed companion is `521041f413a4020c859c7847eef2ed0415af311b`. Preserve every earlier byte and line order at both baselines. Only review-and-security gains duties; the other three contracts, LICENSE, complete notices and earlier release notes remain exact. Add no Core executable, validator, runtime API, setting or consumer implementation.

New qualification and publication duties call for the next minor, v0.4.0, under CHANGELOG. A companion-only patch cannot complete the original requests. Version preparation, merge, annotated tag, Release, consumer adoption and installation remain separate evidence and authority. The timing correction does not grant those public mutations automatically.

### Requirements and security design

The new reviewer section covers every route credited toward required independent review, including primary and substitute routes. Effective writes to reviewed content or task-defined protected resources must be absent or forcibly denied before mutation, supported by current controls and evidence for relevant exposed direct/shell/broker paths. Names, briefs, clean Git state or another tool's denial are insufficient. The scope permits inherited sandboxes, unrelated writable directories and normal supported interfaces; it does not require separate OS sandboxes, whole-host no-write or hostile-administrator resistance. Missing/unknown controls block dependent gates, not independent authorized safe work. Qualification still requires actual current-content review and fresh evidence on drift.

The publication section requires bounded checks before each applicable commit, push, merge, tag and PR/Issue publication. Check content, necessary raw identity/message/trailer/signature metadata and actual destinations. Before commit inspect staged content and intended serialized public signer data/configuration, never signing secrets; afterward inspect the real raw object before dependent publication. Cover complete ranges, prospective merge/squash results and tag/signature/certificate public data, without claiming cryptographic verification from visibility. Display transformations cannot replace raw objects. Check actual push URLs/refspecs/rewrites and non-Git payloads separately. Drift or missing required data blocks dependent publication; post-publication readback cannot satisfy an earlier missing gate. Uncertain writes require read-only reconciliation rather than replay or overwriting others.

Bounded data inspection is separate from risk-based formal Security Diff Scan applicability. Preserve authorization, independent review, controlled evidence, masked public summaries and complete approved notices. Do not claim universal detection or runtime enforcement. Core supplies obligations only; consumer compatibility and actual control verification are separate.

This is high-risk shared security semantics. Early independent deep design/security review raised ED-01 (avoid accessing signing secrets) and ED-02 (cover all required reviewer routes); both are incorporated for later independent closure. The new authority diff needs its own complete deep/content review and formal Security Diff Scan. PR #31's earlier companion scan does not cover it. New public heads still require complete base-to-head Merge Review. Retain final evidence outside the reviewed text rather than creating verdict-only heads.

### Core acceptance and downstream limits

Use fixed synthetic inputs and expectations for R1–R8, P1–P11 and A1. R cases distinguish briefs, relevant writable channels, unknown controls, availability, restricted inherited routes, actual review, unrelated cache writes and changed heads. P cases distinguish intended/actual commit data, unchecked ranges/results/signatures, altered views, destination/payload drift, bounded PR text, uncertain effects, routine low-risk changes, legitimate public notices and authority without completed checks. A1 separates Core readiness from unknown Grok compatibility and from actual publication authority. These are finite normative walkthroughs, not downstream runtime, model-equivalence or technical-isolation tests.

Verify all 23 main-baseline and 24 PR31-baseline files for raw line order/mode/type retention, with exact equality for the three unchanged contracts, LICENSE, full notices and historical releases. Positive insertion and deletion/substitution/whitespace/newline/Unicode/reorder/final-LF/missing/mode/type negative cases check the comparator; independent review checks sentence meaning. Verify the full 26-file inventory (25 Markdown plus LICENSE), links and confidentiality; counts or preservation alone are insufficient. Inspect actual publication payloads and new raw commit metadata without accessing unrelated credentials or confidential sources. Public results use safe locations/categories only.

Core completion requires original-request coverage, preservation, bounded contract walkthroughs, integrity/links/privacy checks, independent deep review/security scan and the authority/readback required at each actual public stage. Guidance or version naming alone is insufficient; reviewed candidates are not publication evidence. Codex v0.4.0 adoption/compatibility has not run. Grok work remains deferred and compatibility unknown. Neither is a pre-adoption Core gate under the revised instruction; neither is passed. Consumers later verify their own fixed source, inventory, digests, closure, notices, assembly and compatibility. Written per ASD-STE100 principles; full conformance is unverified.

### Later environment acceptance and authorized PR update

The user's specific exception qualifies the preserved effective-read-only prerequisite and dependent stop. A necessary retained channel requires traceable user acceptance for a specific environment/rules, recording channels, reasons, alternative detection and gaps. It may credit required review without technical-read-only qualification. Each review checks applicability and performs detection and actual review. Unchanged environments/rules need no repeated confirmation; changes require renewed acceptance. Detected reviewed-content modification invalidates that review. Preserve independence, necessary security, privacy, exact-head and operation authority.

The fixed Claude sources linked above document retained Bash with instructions-only read-only use and pre/post HEAD/status/diff hashes. Documented gaps include existing untracked-file contents, ignored files, Git metadata and outside-repository effects; undetected change-and-restore remains possible. This is the user-designated example, not a Core tool prescription or runtime qualification. The user says Claude will add an acceptance record; completion is unverified here. Change no Claude source or acceptance on its behalf.

Retain the original twenty cases/results. The revised suite explicitly gives R1/R2/R4 no valid exception and adds acceptance completeness/reuse, environment/rule drift, cross-environment/consumer non-transfer, invalidation and detection-limit cases. This is a new finite normative suite, not unchanged inputs or runtime testing. Preserve the frozen twenty-six-file pre-exception candidate, both Git baselines and corruption negatives. Fresh full eight-file deep/security review and formal scanning cover the new trust assumptions; earlier sealed results do not cover the exception.

The user authorized this expanded candidate's commit, push and existing draft PR31 update, followed by complete new-head Merge Review. Earlier missing-authority statements retain their preparation stage; do not ask again for those actions. Merge and official release remain unauthorized. Grok remains deferred with unknown compatibility.
