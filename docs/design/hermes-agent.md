# Hermes Agent adapter 設計

依據 [需求](../requirements/hermes-agent.md)；工程順序與當次缺口由
[交付計畫](../plans/issue-318-hermes-agent.md) 記錄。

## 分層

共用層維持來源、ownership、授權、風險、驗證、findings disposition 與
exact-head 語意。Hermes 層只轉接技能載入、工具發現及 supervised 操作。
`hermes/catalog.json` 是獨立 allowlist；`hermes/skills/` 不進 Codex plugin。
不將 Codex custom-agent TOML、`functions.exec`、Desktop control plane 或
CLI session IDs 轉寫為 Hermes 設定。

安裝產物保留 `skills/`、`policies/`、`templates/`、`scripts/` layout。
技能用相對引用，可由原生 `skill_view` 讀主文件，依賴由本地 read tool／terminal
讀取。Hermes hub 單一 SKILL URL 安裝不是本套件交付方式；不可假設 hub
會補齊 sibling policies／templates。安裝器不安裝 Python、MCP 或模型依賴。

## 寫入與供應鏈邊界

`install-hermes.sh` 是新的獨立入口。plan／diff 唯讀，install 必須明確指定
Hermes `skills` 根目錄；目標 namespace 必須不存在，逐件拒絕 symlink、
非 regular source、非 allowlist 項目及同名技能碰撞。一次讀取預期 bytes，
用 exclusive namespace 建立避免覆蓋現有內容。失敗保留 incomplete marker
供診斷；diff 不可將不完整產物判為一致。沒有 force／uninstall／自動 update。
更新先在新隔離目錄驗證，再另行核對替換或清理授權。

同名判讀使用安全 YAML，支援 BOM／comments／quoted keys；malformed、
duplicate keys 或不確定 name type 一律拒絕，不以 last-key-wins 猜測 native
loader 的 fallback 語意。

不讀 `.env`／auth、沒有網路呼叫、不執行被安裝的腳本、不修改 runtime config。
目的地須由目前 user 擁有且不可 group/world writable；root ancestors 不得
有 symlink，且須由目前 user 或 root 擁有、不可由其他帳號改寫；root-owned
sticky temporary root 只在 child 受 sticky ownership 保護時例外。拒絕指向 source repo、Codex discovery root 或同名其他技能。
其他 installer／runtime 同時修改 skill roots 不在本版交易模型內；安裝前
停止該目的地 writer，再讀回 inventory。技能內容是指引，不能作 OS containment。

## Runtime 邊界

`--oneshot`／`--yolo`／approval off／自動接受 hooks 不符合本 adapter。
優先 supervised CLI；不因容器或自動模式忽略精確動作授權。`chat -q`
也必須核對版本行為與 single-query approval 設定，不能由名稱推定。
工具／backend 權限未知則不使用相依能力。

Hermes 子代理的 context 隔離不等同 filesystem／network 隔離；read-only
reviewer 必須有實際 enforcement 或交由已驗證獨立 reviewer。只縮小 toolsets
或在 prompt 寫唯讀不能證明 shell 無寫入權。沒有合格獨立審查即停止正式 gate。

模型選擇逐目的地核對使用者授權、費用、credential source、tool roundtrip
與品質。認證／環境／權限失敗不靠換模型，工具結果不明不自動重播；能力
返工在兩輪持續失敗時重評假設與方法，只升至已驗證同範圍目標。
repo checkpoint 保存 branch/head、未提交 diff 身分、scope、phase、驗收、
findings、證據路徑與下一步；runtime session 只提供協調資訊。
