# 獨立審查與必要安全掃描契約

本契約定義品質證據與 blocking readiness；實際 reviewer、工具、資格、scan、validator 與 artifacts 由接口提供。正式文字為繁體中文；來源改寫與 license notices 見 [source-map](../docs/provenance/source-map.md) 及 [upstream-notices](../docs/provenance/upstream-notices.md)。

<a id="review-independent"></a>

## 審查獨立性與範圍

按實際風險選一般、深入或專門審查；文件亦以可遵循契約、正確性、缺前置、不安全指引、私有資料、過期路徑及未支持宣稱為重點。Review request 保持唯讀，只有明確轉為修正／實作才修改受審內容。作者不能用自審取代必要獨立 reviewer；reviewer 須有足夠能力及適用資格，與作者保持角色及工作責任獨立。

可使用同一 runtime 的另經驗證唯讀角色／session 或獨立服務。子代理可繼承 parent sandbox 與核准模式，無通用逐子代理技術隔離要求；唯讀 workflow expectation 不等於獨立 read-only sandbox，對話隔離、toolset 限縮及角色名稱也不能證明品質或必要技術限制。明定技術隔離的任務須另驗該條件。

Reviewer 依 DoD、spec、plan、當前內容與適用 gate 審查，先報風險、缺陷、regressions、漏驗證與 blocker，附檔案／位置、來源證據、影響及阻擋理由；測試通過不代表無 blocker。主代理讀回並驗證整合成果，子代理摘要只是協調資料。

<a id="review-findings"></a>

## Findings、修正與 formal gate

每項 MUST-FIX、SHOULD-FIX、NIT 或其他適用 finding 給穩定 ID 與一個 disposition：`Fixed`、`Deferred`、`Rejected`、`Needs Human Decision`。Fixed 附修正／驗證與重審證據；Rejected 附來源與理由；Deferred 必須有持久後續目標、owner、原因、剩餘風險、驗證計畫與 promotion trigger；Needs Human Decision 保留具體待決事項。NIT 只有明確 disposition 後才可非阻擋，不能從 gate 記錄消失。

實作流程先修正 blocker，再按受影響邊界重審；可安全修正的其他 finding 一併處理，其餘留下上述完整 disposition。修正後可選足以證明 fix 的最小普通／深入 code/docs review 範圍，記 unchanged 證據仍適用的理由；shared contract、data/trust、generated artifacts、packaging、文件宣稱或假設變動時擴大範圍。

Primitive review 提供品質證據；formal gate 在 commit、PR/MR、merge readiness 或明定專案政策時提供 blocking 判定。內容／範圍／來源假設／環境與驗證仍符合時可重用 primitive 結果，不為進 gate 重複同一次審查。Gate 必須阻擋未解 MUST-FIX、缺 disposition、Deferred 缺必填後續資訊或未解 Needs Human Decision；結果明列 PASS／BLOCKED／NEEDS HUMAN DECISION、findings、dispositions、evidence 與 required follow-up。

Pre-commit verdict 只證明所檢內容；已有 change request 後不能直接作 merge readiness。每個新 head 都須完整 base-to-head [exact-head Merge Review](exact-head-and-evidence.md)，比例 fix review 不構成例外。任何 review/gate 都不授權 commit、push、平台 comment/review、merge、publication 或 deploy。

<a id="review-security"></a>

## Security Diff Scan 適用性

從最終 diff、實際影響與仍存在的具體疑慮評估，不能只按檔案類別決定。Security/trust boundaries、permissions、authentication、敏感資料、具有安全影響的 executable、dependencies、installation paths 或未解具體 security concern，須完成比例適當的 Security Diff Scan。一般 code review 含基線安全檢查，但 clean review 不替代必要 scan。

不確定時先查受影響邊界；未解實質安全風險阻擋 readiness。沒有上述影響時，記錄 examined scope 與 rationale，結論為不適用；未執行或略過不得記為 Passed。Model/effort-only、documentation、generated files 既非自動必掃，也非 blanket exemption；scope／假設變動後重評。

必要 scan 的未執行、未完成、失敗或 coverage 不足均不可視為通過。結果記工具／方式、當前 diff 身分、完成與 coverage、findings/dispositions、限制；需要獨立安全 reviewer／深入審查時不得用作者自評替代。Credentials、permission/identity/tenant、敏感資料、付款、upload/parsing、external APIs、persistent data/migrations、deploy/infrastructure、supply chain、crypto/randomness 等實質變更須按風險升級審查，檢查 source-to-sink、failure modes、rollback、logging 與驗證充分性。

<a id="review-evidence"></a>

## 證據與續行

審查與 gate 明列當前 revision/diff、scope、來源假設、DoD、已執行／略過命令與結果、findings/dispositions、剩餘風險及驗證限制，即使零 findings 亦保留綁定資訊。可機械查核的事實使用 deterministic checks；人或模型審查不可替代，tests 也不可替代語意一致性審查。

Clean 內部 review/scan 可續行下一個唯讀或已授權階段；實際授權／環境／風險決策仍依 [授權與停止條件](authorization-and-stops.md)。共享 Markdown、synthetic eval、profile 安裝、service availability 或平台綠燈都不能單獨證明獨立審查、runtime 資格或工程完成。
