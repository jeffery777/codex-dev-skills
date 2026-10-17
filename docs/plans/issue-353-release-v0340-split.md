# Issue #353 — Codex v0.34.0 split release plan

## 範圍與階段 / Scope and stage

維護者同意重新使用 `0.34.0` 作獨立 Core 拆分發行；歷史候選及 #328/#330
決策保留。前一輪文件準備已完成。本階段已收到正式 Core v0.1.0，依既有授權
更新候選、完成必要 gates，再 commit／push／PR／merge／tag／正式 Release。
發布後先交付安裝方案，使用者實裝由主話題核對時序與資料保護後接續。

The maintainer agreed to reuse `0.34.0` for an independent Core split release.
The earlier preparation stage is complete. This stage consumes formal Core v0.1.0
and proceeds through the authorized commit, PR, merge and publication gates.
Report the release and installation plan before changing any user installation.

讀者為 release owner、獨立 reviewer 與後續安裝 operator。只有一位 source writer。
保留主 checkout、其他 worktrees、歷史證據及 draft #317/#324/#326 的獨立範圍。
如實記錄既有 local／第三方／Hermes／Memory 來源，不增加 Reason 或恢復新投入。
不新增外部 Markdown POST；本階段文件呈現依使用者指示採本地驗證。
長期協調仍由主話題負責，不建立排程或第二套協調。

Readers are the release owner, independent reviewer and later installation operator.
One source writer owns this package. Preserve unrelated work, draft scopes and
historical evidence. Disclose existing paused sources without new feature investment.
Use local document rendering as instructed; do not send new render POSTs or create schedules.

## 固定來源與影響 / Fixed sources and impact

Codex 基線為 `0bcc1568c5571e85807f6edeb1fb9e2c6043af87`，從共同 v0.33.0
核對完整 main 範圍；v0.33.1 是另一維護線，不宣稱為 main ancestor。
來源／套件版本、候選、發布事實、有效指引及歷史紀錄分別審查。

Core v0.1.0 的 annotated tag object 為
`e984c880a05065c8bcd0d78e83d78220b05bfc32`，peeled commit 為
`174df2af8dedf813b9bd4e3c184a627ee87d3cd8`；tag object 不是 commit。
完整 closure 為 13 檔、264,088 bytes，包含 12 份 Markdown 與 LICENSE。
其中九份既有檔案（包含四份 contracts）bytes 不變。Core CI 為
`NOT_CONFIGURED`，不得標成 PASS。

The Codex baseline is `0bcc1568c5571e85807f6edeb1fb9e2c6043af87`.
Review the full main scope from common v0.33.0 and compare the separate v0.33.1
maintenance fixes without claiming ancestry. Classify all five release-state roles.
The Core annotated tag peels to the exact commit above. Its full closure has
thirteen files and 264,088 bytes; nine existing files, including four contracts,
are unchanged. Core CI is `NOT_CONFIGURED`.

三種 digest 依各自算法保留，不互相代用：

| 集合 / Set | SHA-256 |
| --- | --- |
| Core raw 13-file set | `3c985420e8017bde6b59f2625d451686202e2f6a03d807a361df166634a88de9` |
| Core 12-Markdown set | `484923e7dc1407dde1702cf88e93afb5a279b25f79a2c6ff9631d58d7589ab13` |
| Codex canonical 13-file set | `91e3153d31f4096e21927e653b74010fbaa504c7f1550ecf56af687db288d482` |

These digests use separate defined algorithms. They prove content integrity,
not publisher identity, runtime qualification or authority.

## 有界設計 / Bounded design

1. 一般 loader／package 僅接受正式 13 檔 pin。Installer 明確選用目前 validator
   內的兩個靜態 descriptor，才可處理已審的舊 11 檔集合；不執行舊來源程式，
   不接受任意自述 hash，不因錯誤自動 fallback。回傳 identity 依實際 descriptor。
   正式總量上限 264,088 bytes；舊 descriptor 保持 256 KiB，單檔 128 KiB，
   固定 lock 16 KiB。先安全讀取有界 lock，再盤點，最後才讀文件。
2. Receipt 保留逐檔 inventory；交易層只將完整 Core root 合為一個 directory
   artifact，沿用既有 rename／backup／rollback。Lock 仍是另一受驗 artifact。
   這保留 13↔11 檔的精確目錄集合，不另加通用目錄 journal 或遷移框架。
   未管理的既存 root（包含空目錄）、symlink、未知內容與 identity drift 均拒絕。
3. `catalog.yaml` 的 `release_notes` 指向獨立 split record，使新來源 catalog
   identity 有意義且唯一。保留 v0.33.1、舊開發版 0.34.0 兩份 mapping，再加
   正式 split mapping；重複 catalog digest 拒絕。相同版本號的不同來源仍須
   全部 managed groups 一起換版；不重寫舊 receipt 或自動啟用新 opt-ins。
4. Release-state validator 僅接受該版本精確的 split 相對路徑；錯誤型別、逃逸、
   symlink 或缺檔不 fallback。保留歷史 notes 原文。更新完整 Core closure、
   notices、來源及 generated plugin／既有 Hermes resources，並對齊雙語文件。
   Hermes 只維持既有 closure，不新增 runtime 資格或功能。

Normal loaders and packages accept only the formal snapshot. Only an explicit
installer choice enables the two static reviewed descriptors in the current validator.
Keep exact identities, limits and lock-before-inventory-before-document read order.
Receipts remain per-file; only the Core transaction becomes a whole-directory move
using the existing engine. Retain a separate lock operation, ownership checks and
recovery originals. Refuse unknown or unowned roots, even empty ones.

A meaningful split-record catalog field distinguishes the new source. Keep all three
reviewed mappings, reject duplicate digests and require all managed groups for a
source replacement even when both versions say 0.34.0. Do not execute old programs,
rewrite old receipts, adopt legacy ownership or activate new profiles. Constrain
release-note selection, preserve history and synchronize exact package/notices closure.

## 驗證與交付順序 / Verification and delivery order

1. 讀回 Issue／遠端 branch／本機 identity／ownership，唯讀核對 Core tag、peeled
   commit、正式 Release、13 檔原文與獨立重算 digests。
2. 完成早期獨立深入設計／code review，按實際新 diff 做必要 Security Diff Scan。
   固定完整 payload，先完成此階段適用檢查與 pre-commit review，再建立 immutable
   payload commit。Registry generator 只讀 Git blobs，不能假造未來 SHA。
3. 依真實 payload commit 產生第三份 mapping，保留舊兩份。之前受 registry
   相依限制的 installer/source-integrity 驗證明記 pending。產生後完成所有相依
   驗證；最終 HEAD 的 catalog／installed payload 必須逐檔吻合固定 snapshot。
   Payload 若再變，重新固定並產生 mapping，不繞過 dirty-source 拒絕。
4. 使用 tracked Python resolver。驗證 source/plugin/filesystem/Hermes closure、
   LICENSE／notices／modes／links、release-state negatives、catalog／registry
   regeneration、全部受影響 tests 及完整 12-shard equivalent。
5. 隔離 fixture 驗證新裝、舊 0.34→正式 0.34→舊 0.34、maintenance 0.33.1、
   no-op、profiles 保留、部分換版拒絕、部分／全部 uninstall。確認檔案、實際
   目錄集合與 receipts；Core retirement 後 root 不可殘留。
6. 注入 staging／Core backup／root promotion／lock／各 receipt／postverify、
   reverse restore／cleanup／signal／identity drift 故障。失敗不得假稱成功；
   保存未知內容及 recovery originals。不能只以 regular-file snapshot 證明目錄回復。
7. 固定最終候選後完成獨立深入 code/docs 與五角色 release review、本地雙語呈現；
   新 diff 安全 coverage 必須明確，不將舊候選 SDS 自動套用。完整 STE 符合性未驗證。
8. 適用 pre-commit gates 通過後 commit／push／PR。每個 changed head 都做完整
   base-to-head exact-head Merge Review，核對 required CI／closing Issue／threads、
   strict receipt 與專用 App/native-latest，全部滿足才按 expected head 正常 merge。
9. 從最終核驗 commit 預覽 tag／Release payload，重查名稱衝突與身分。建立新
   annotated tag，不覆寫既存 tag；讀回 tag object／peeled commit，再發布正式
   非 draft、非 prerelease Release，讀回 target／body／metadata。
10. 同步 Codex 空間專案文件至最終 GitHub 事實並讀回。先回報 Release URL、
    tag commit、bundled Core、digests 與安裝方案。主話題核對兩端安裝時序、
    實際 target／ownership／舊 receipt／資料保護後接續實裝；本階段不直接安裝。

Verify upstream and checkout identities first. Complete early independent review
and a new proportional scan. Freeze and review an immutable payload before generating
its registry mapping from real Git blobs. Dependent checks remain pending until that
mapping exists. Any later payload change requires a new fixed snapshot.

Complete isolated transition and failure tests, exact directory/receipt checks,
package parity, all affected tests and the shard matrix. Review the final bilingual
candidate independently and render it locally. Keep scan coverage and STE limits explicit.
Each PR head needs full exact-head review plus current CI, Issue, thread, receipt and App
gates. Merge only the expected head after all required gates pass.

Preview publication conflicts and payloads. Create a new annotated tag from the verified
final commit, read it back, then publish and read back the formal Release. Synchronize
Codex Space to those final facts. Hand off the installation plan without changing user
targets in this stage. Historical legacy installations need a separate ownership inventory;
there is no automatic migration framework or mandatory permanent package cache.

## Gate 紀錄 / Gate record

本計畫記錄設計與順序，不替代結果。各階段以綁定 revision／diff 的實際驗證與
獨立報告判定；pending／failed／unknown 不記為 PASS。不可因已有 release 授權
而跳過正式 gates，也不需為已授權正常階段重複詢問。

This plan defines the design and sequence, not a PASS result. Bind each verdict to
actual source identity and evidence. Preserve pending, failed and unknown outcomes.
Existing publication authority does not waive any gate.

English follows ASD-STE100 principles; full conformance is unverified.
繁體中文依簡明原則撰寫，不宣稱 STE 符合性。
