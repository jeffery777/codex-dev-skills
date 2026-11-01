# 使用端回饋維護工作包／Consumer feedback maintenance packet

[繁體中文](#zh) · [English](#en) · [確定性重跑命令](#preservation-check)

<a id="zh"></a>

## 繁體中文

這是 2026-10-31 的階段評估，不是七項已全部實作的聲明。Core 基準為 `7b66978a76597d09be1b55ad199a969b4ee59c0f`（v0.1.1）；本包只新增非權威伴讀與維護記錄，四份正式契約及 LICENSE 原 bytes 保留。修改型候選與正式義務分開。正式合併、tag／Release 與已安裝技能更新未授權執行。

### 已讀來源與現況

- 完整背景：[claude-dev-skills docs/core-feedback.md@071c1a7ff1f2ce67a605d54ce5c3e85480852b69](https://github.com/jeffery777/claude-dev-skills/blob/071c1a7ff1f2ce67a605d54ce5c3e85480852b69/docs/core-feedback.md)，包括 CF-001–012 與不回饋項目。CF-010／011／012 未在本次七個 Issue 提出，不擴大成新義務。
- 逐一讀取 #25 → #27 → #24 → #26 → #21 → #23 → #22 全文及全部留言。GitHub 讀回 #27 有兩則留言，含 [10 月 22 日讀法](https://github.com/jeffery777/engineering-workflow-core/issues/27#issuecomment-6337432192) 與 [10 月 30 日補充](https://github.com/jeffery777/engineering-workflow-core/issues/27#issuecomment-6514972689)；#21、#22 各一則 10 月 30 日補充；#25、#24、#26、#23 各零則留言。使用者概述的「每項都有留言」與此讀回不同；不捏造缺少的留言，相關新證據從固定背景讀取。
- [Claude #91](https://github.com/jeffery777/claude-dev-skills/issues/91) 的 10 月 30 日更新要求只加句子、原規則一字不改，並以確定性比對驗證。本包採更嚴的原始 bytes／完整行序比對，不 strip、忽略空白或 Unicode 正規化。新增是否為完整句子及語意有無衝突，另由獨立 reviewer 檢查。
- Core 原本停在乾淨的 Issue #15 分支 `8b546d8c27a3db416ef7021a01fdae3ffa572ec6`，已保留；從核對的遠端 main 建立本工作分支。Core checkout 無 AGENTS.md、.agents 或 .codex 技能目錄。使用同層 Codex 的 project-delivery／docs-review 技能，沒有把 Codex repository 專屬 CI／App／Issue 規則套到 Core。
- Codex 本機 checkout 是乾淨的 Issue #359 分支 `34872c6343e880c2fea1e60f371fd1dbf8afa9ba`，遠端 main 讀回 `9eef3c298da97ad5c72c8a099258487783149d70`，不是同一 revision。Grok 本機與遠端 main 均為 `789af96b9652de3a2a31ae3e9adaf719f4da5b03`。Claude 本機 main `51f9fd344e5a06c55748fe969cedc917a56ff7da` 只查讀，指定背景另以 Git object 讀取。未清理歷史 worktrees。
- Core 無既有 open PR、hosted CI 或明選 enforcement profile；查讀主分支 PR-triggered workflow 清單回傳空集合，不能稱 CI Passed。Codex 的其他 open draft PR #317／#324／#326 是不同範圍，未接管。未能在 sandbox 列舉程序；單一 writer 是本工作包 ownership 安排，不聲稱已用程序清冊證明整台主機無其他 writer。

### 依指定順序的判定

| 次序／Issue | 分類與判定 | 本包實際處理；修改部分未接受的理由 |
| --- | --- | --- |
| 1／[#25](https://github.com/jeffery777/engineering-workflow-core/issues/25) | 增量，採用選用範本 | 新增 [決策卡](../companion/decision-cards.md)，保留問題、必要決策原因、各選項做法／結果／風險／成本、建議、未決後果、事實／推論／證據；不變成強制卡片或授權來源。 |
| 2／[#27](https://github.com/jeffery777/engineering-workflow-core/issues/27) | 增量導讀；會新增最低義務的讀法仍屬修改型 | 新增 [十點伴讀與階段索引](../companion/core-reading-guide.md)。第 4／5 點交叉引用既有 fallback／保存義務；第 8 點保留字面 preview／dry-run 區別；第 1／2／9／10 點不假裝已解決原文未定部分；第 7 點按完整原檔讀取，保留 subagent 可讀全文與 CF-007／008 的量測限制。 |
| 3／[#24](https://github.com/jeffery777/engineering-workflow-core/issues/24) | 修改型，準備獨立候選，尚未接受 | 欄位與 severity／disposition 正交；REQ-GAP 不授權擴需求；Core 安全、資料遺失、授權、完整性 blocker 不因分類解除。須在 Codex 以固定候選實跑案例；Grok 暫緩意味雙 consumer gate 未滿足。 |
| 4／[#26](https://github.com/jeffery777/engineering-workflow-core/issues/26) | 修改型，與 #24 共用需求來源邊界的候選 | 新機制須追溯已確認需求與獨特作用；既有 Core 必要義務可作需求，不強制另建需求系統或把範圍內小選擇改成人類 gate。僅 finding ID 不創造新需求。未通過雙 consumer gate 前不接受。 |
| 5／[#21](https://github.com/jeffery777/engineering-workflow-core/issues/21) | 混合；第 4 點採增量，其餘修改型 pending | [決策伴讀](../companion/review-decisions.md) 提供使用者重訂範圍／限定一輪／follow-up 的選項，涵蓋 PR 前紀錄也會進 diff。第 1 點嚴重度門檻需驗證既有 gate 相容性；第 2 點強制停止與原文「並非自動停工」有張力；第 3 點一律禁止 commit 紀錄可能與保存政策衝突；第 5 點規格／設計失敗的新分類需實際案例 eval。不以新增相反句子或移出 blocker 冒稱解決。 |
| 6／[#23](https://github.com/jeffery777/engineering-workflow-core/issues/23) | 修改型 pending，不能用文件宣稱工具已受限 | CF-003 新證據包含 host 與宣告 toolset 不同、shell 仍有寫入能力。現有 Core 明許共用 sandbox，無通用逐 reviewer 技術隔離；採用工具能力限制前須定義範圍、證明當次 effective tools／限制及 fail-closed 路徑。未建立或擴大指紋框架，也未把本包 reviewer 宣稱為已符合新提案。 |
| 7／[#22](https://github.com/jeffery777/engineering-workflow-core/issues/22) | 混合；遮蔽格式採增量，掃描義務 pending | [公開記錄伴讀](../companion/review-decisions.md) 保留種類／位置／必要類別、email／路徑代號與 hash 可猜測風險。修改型候選仍須涵蓋每次 commit／push／PR／Issue、全 range／merge／squash、commit／tag 簽章、不受 mailmap／replace refs 等設定影響的掃描視圖及 fetch／push 目的地一致。這些是尚待驗證的義務，不自行擴張 runtime 掃描功能。 |

### 風險、候選與兩端相依

伴讀會影響讀者對授權、保存及 reviewer 的理解，已安排早期獨立深入設計／安全分析，逐點避免用說明新增義務。修改型 #24／#26 的風險是錯誤分類解除 blocker、把需求缺口默默實作、或讓原本小型修正陷入新需求制度；先做相同情境的正反 eval，而非先更動正式 loader。

Codex 的 `scripts/validate-core-contract-snapshot.py` 及 Grok 的 `scripts/core_snapshot.py` 都把正式 revision、清冊及集合 digest 固定在程式。只改 lock 不構成候選採用，普通 snapshot checks 也不證明規則的行為遵循。Codex 相依工作包將從已核對的 main 建 Issue／分支，以隔離的固定候選文件與明確 eval 入口試驗；不修改已安裝技能、不接受任意候選、不把未發行 revision 標成正式 tag。候選 SHA、Codex pin／diff、實跑結果與限制記在該工作包，不能用此規劃代替成功。

兩端正式 pin 均仍為 `7b66978a76597d09be1b55ad199a969b4ee59c0f`。Codex 既有 snapshot 的本機 baseline 驗證回傳 verified（14 檔、Python 3.12.9）；這只是舊正式版完整性，不是新候選 eval。Grok 依使用者最新指示不改程式／pin、不跑新實作包，已查重並建立 [Grok #36](https://github.com/jeffery777/grok-build-dev-skills/issues/36) 追蹤候選 pin、eval、驗收與未完成門檻。Grok pending 時，不宣稱原雙 consumer gate 滿足，修改型 Core 義務維持 candidate，不 merge。

候選 eval 至少覆蓋：範圍內小修正可續；推測新需求交人決定；使用者納入後重新確認 scope 才進後續輪次；unrelated 的資料遺失／授權 blocker 仍阻擋；無需求的新 wrapper／validator 不加入；可引用具體 Core 安全義務但不以標籤證明必要；原 severity／disposition／gate 不變。逐字檢查含刪改、空白、換行、Unicode、檔案遺失、mode／type 漂移負例。

### 驗證與交接

下方命令是本工作包的離線重跑範例，不是 Core 新增的 validator、runtime gate 或執行套件。它從固定 Git object 取基準，查所有既有檔的完整行序與 raw bytes、mode／type，以及四 contracts／LICENSE equality；新增句子是否完整、是否不改語意仍需獨立審查。檔案完整性／連結檢查、docs review、必要安全檢查、最新完整 base-to-head review 與平台狀態應分別記錄。正式審查結果綁定精確候選，存交接／PR 證據，不為附上 verdict 而反覆製造新 head。本記錄不自行宣稱 PASS 或 merge readiness。

<a id="en"></a>

## English

This is a staged assessment dated 2026-10-31, not a claim that all seven Issues are implemented. The baseline is Core v0.1.1 at `7b66978a76597d09be1b55ad199a969b4ee59c0f`. This packet adds non-authoritative companions and maintenance records, preserving the bytes of all four contracts and LICENSE. Modifying candidates are separate from accepted obligations. No formal merge, tag/Release, or installed-skill update is authorized here.

All Issue bodies and available comments were read in the requested order. GitHub returned two comments for #27, one each for #21/#22, and none for #25/#24/#26/#23. The fixed Claude background supplies the additional evidence; missing comments were not invented. The complete CF-001–012 record and Claude #91 were read. Unproposed CF-010/011/012 are not added obligations. Raw-byte preservation is stricter than a normalized word comparison; semantic review still checks complete new sentences and conflicts.

The ordered decisions are: (1) #25 adopts an optional decision card; (2) #27 adopts ten reading notes and a stage map, separating existing duties, suggestions, and pending interpretations; (3) #24 prepares an unaccepted requirement-relation candidate; (4) #26 prepares the related mechanism-to-requirement candidate; (5) #21 adopts only optional human scope-decision guidance, leaving severity, mandatory stopping, record-location rules, and spec/design failure classification pending; (6) #23 remains pending effective read-only capability evidence; (7) #22 adopts optional masking formats while mandatory publication-scan scope remains pending. The Chinese table gives per-point reasons, source links, and files; the companions provide equivalent bilingual details.

Original text is retained in every existing file. Existing P1 provenance, all 107 units, release history, and license notices remain. Added Claude-source adaptations have a complete MIT notice. No runtime framework or generic candidate bypass is added. Core has no AGENTS.md or checkout .agents/.codex skills. The sibling Codex delivery/docs-review workflows were selected without importing its repository-only App/CI rules into Core.

The clean starting checkouts and remote identities are listed above. Core's old Issue #15 branch is preserved. Codex's local Issue #359 branch differs from remote main; the follow-up starts from verified main, preserving that checkout's work. Grok and Claude were read only. Historical worktrees were not pruned. Process enumeration was unavailable in the sandbox; writer ownership is the packet's coordination arrangement, not a verified whole-machine process inventory. Core has no open PR or configured hosted CI/profile at discovery; an empty PR-workflow list is not CI PASS. Other Codex drafts are unrelated and untouched.

Both consumers hard-code their accepted Core snapshot identity and digests. Changing only a lock cannot adopt a candidate. Codex's existing 14-file v0.1.1 snapshot passed its local baseline integrity check under Python 3.12.9; this is not a new-candidate eval. A separate Codex Issue/branch will pin an isolated candidate and execute positive/negative scenarios, without changing installed skills, accepting arbitrary snapshots, or inventing a released tag. Its evidence must record the actual candidate SHA, pin/diff, results, and limits.

The user deferred Grok implementation. [Grok #36](https://github.com/jeffery777/grok-build-dev-skills/issues/36), created after duplicate checks, tracks its future fixed candidate, pin/evals, and acceptance. No Grok code, pin, or new implementation run is made. The original dual-consumer gate is unsatisfied while Grok remains pending; modifying Core rules stay candidate and must not merge.

The candidate scenarios cover an in-scope fix, a proposed new requirement, user-approved later scope, unrelated safety blockers, unsupported new wrappers, traceable existing safety duties, unchanged severity/dispositions/gates, and deterministic corruption cases. Early independent design/security analysis addresses the risk that classification waives blockers or creates a new requirement bureaucracy. A planned or integrity-only check cannot count as behavioral success.

The command below is an offline reproduction example, not a new Core product validator or runtime gate. It checks original bytes, complete line order, file existence/type/mode, and equality for contracts/LICENSE. It cannot prove complete sentences or semantic consistency. Record content checks, reviews, necessary scans, exact-head full-range review, and platform status separately. Bind final review evidence to the exact candidate outside the reviewed head to avoid a verdict-only head loop. This record grants no readiness. Written per ASD-STE100 principles; full conformance is not verified.

<a id="preservation-check"></a>

## 確定性重跑命令／Deterministic reproduction

在 Core checkout 根目錄，以既有 Python 3 執行；不安裝套件。Run from the Core checkout root with an existing Python 3. No dependency installation is needed. All comparisons use raw bytes without normalization. The in-memory negative cases create no files.

本節原始命令只適用於固定伴讀 tree `709454e96c1b41362fe8840dc4e4dbc8d4fe2cf8`，其四契約應與 v0.1.1 equality。本版合法的 #24／#26 增句會使該 equality 檢查失敗；請改用 [v0.2.0 三基準重跑命令](../releases/v0.2.0.md#preservation-reproduction)。保留本段原命令作為歷史重現，不拿它驗新版。

The original command below applies only to companion tree `709454e96c1b41362fe8840dc4e4dbc8d4fe2cf8`, whose contracts equal v0.1.1. The lawful #24/#26 additions fail that historical equality check. Use the linked v0.2.0 three-baseline command for the new packet; retain this command unchanged for historical reproduction.

```python
import hashlib
import os
from pathlib import Path
import stat
import subprocess

BASE = "7b66978a76597d09be1b55ad199a969b4ee59c0f"
ENV = dict(os.environ, GIT_NO_REPLACE_OBJECTS="1")

def git(*args):
    return subprocess.check_output(["git", *args], env=ENV)

def inserted_only(before, after):
    # LF bytes remain in each line; no stripping, decoding, or normalization.
    old = before.splitlines(keepends=True)
    pos = 0
    for line in after.splitlines(keepends=True):
        if pos < len(old) and old[pos] == line:
            pos += 1
    return pos == len(old)

def retained(before, after, old_mode, new_mode, regular=True):
    return (after is not None and regular and old_mode == new_mode
            and inserted_only(before, after))

sample = "甲 must stay.\nKeep  two spaces.\ncafé\n".encode()
positive = [sample, b"New complete sentence.\n" + sample + b"Added sentence.\n"]
negative = [
    sample.replace("甲".encode(), b""),              # deleted character
    sample.replace(b"must", b"may"),               # replacement
    sample.replace(b"  ", b" "),                  # whitespace
    sample.replace(b"\n", b"\r\n"),                # newline normalization
    sample.replace("é".encode(), "e\u0301".encode()), # Unicode normalization
    b"".join(reversed(sample.splitlines(keepends=True))), # reordered lines
    sample[:-1],                                   # missing final LF
]
for value in positive:
    if not retained(sample, value, "100644", "100644"):
        raise SystemExit("positive preservation case failed")
for value in negative:
    if retained(sample, value, "100644", "100644"):
        raise SystemExit("negative preservation case escaped")
for value, mode, regular in [(None, "100644", True),
                             (sample, "100755", True),
                             (sample, "120000", False)]:
    if retained(sample, value, "100644", mode, regular):
        raise SystemExit("missing/mode/type case escaped")

rows = git("ls-tree", "-rz", BASE).split(b"\0")
checked = exact = 0
for row in filter(None, rows):
    meta, raw_name = row.split(b"\t", 1)
    mode, kind, oid = meta.decode("ascii").split()
    name = raw_name.decode("utf-8")
    path = Path(name)
    before = git("cat-file", "blob", oid)
    try:
        info = path.lstat()
    except FileNotFoundError:
        raise SystemExit("baseline file missing: " + name)
    regular = stat.S_ISREG(info.st_mode)
    actual_mode = "100755" if info.st_mode & 0o111 else "100644"
    after = path.read_bytes() if regular else None
    if kind != "blob" or not retained(before, after, mode, actual_mode, regular):
        raise SystemExit("original bytes/order/mode/type changed: " + name)
    if name.startswith("contracts/") or name == "LICENSE":
        if before != after:
            raise SystemExit("protected file differs: " + name)
        exact += 1
        print(name, hashlib.sha256(before).hexdigest(), "EXACT")
    checked += 1
print("PASS", checked, "baseline files;", exact, "protected exact;",
      len(positive), "positive;", len(negative) + 3, "negative cases")
```


## 後續接受準備／Later acceptance preparation

本頁前述未實作／未驗證及 Grok 延後狀態保留為初始伴讀工作包的點時歷史。後續 #24／#26 固定候選已由 Codex 及 Grok 各 pin 並完成一次九案文字 eval，各9/9；[v0.2.0 準備紀錄](../releases/v0.2.0.md) 定義本次正式接受草案、完整二十檔清冊與待出版身分的 consumer adoption。#25／#27／#21／#22 的選用伴讀維持非權威；原表其餘修改型未採納部分繼續 pending，沒有由這九案涵蓋。完整 runtime、正式 publication、loader／安裝及所有操作授權仍分開驗證。

Earlier unimplemented/unverified and Grok-deferred statements describe the initial companion packet. Later, both consumers pinned the #24/#26 candidate and passed one nine-case text evaluation each. The v0.2.0 record defines this formal-acceptance draft, twenty-file inventory and publication-dependent adoption work. Optional companions remain non-authoritative; all other modifying proposals in the original table remain pending and are not covered by these nine cases. Full runtime qualification, publication, loaders/installations and action authority remain separate.
