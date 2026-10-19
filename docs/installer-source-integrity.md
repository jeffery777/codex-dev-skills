# 固定來源安裝與回復 / Fixed-source installation and recovery

## 繁體中文

此 installer 使用目前程式碼，從明確選定的本機 Git checkout 讀取套件資料。
它不下載來源、不執行所選舊來源的 installer、validator、hooks 或 filters。
執行 installer 的程式根與 `--source` 的 payload 根可以不同。
需要 Bash、Git 與 Python 3 標準函式庫；installer 的完整性檢查不新增 PyYAML 相依。
技能本身的既有 runtime 相依仍適用。

### 支援來源與版本

受審資料清單接受以下固定 catalog 與完整 payload，包括檔名、內容與 executable bits：

| Source/package version | 已核對來源 commit | 內含 Core |
| --- | --- | --- |
| 0.33.1 | `6b5b0d0bf4e61119a5a87761fc4a6c4d35002e1c` | 無 |
| 0.34.0 開發基線 | `43c650e1196a3a702e2240bd79dd24539fa893a7` | `64b19bb5658432c42cd6a26aa357fd6b1d0fd857` |
| 0.34.0 split | `f18b202595aea27c9d872c480d2e1b067340b163` | `174df2af8dedf813b9bd4e3c184a627ee87d3cd8` |
| 0.35.0 | `e23e18ed0512ece04ca6b6dceba3a6a1cf59b9fd` | `174df2af8dedf813b9bd4e3c184a627ee87d3cd8` |
| 0.35.1 | `6cd58e3a776ef705a9cee17ba7e24c6b21181395` | `7b66978a76597d09be1b55ad199a969b4ee59c0f` |

`installer/source-catalogs.json` 是受審資料清單，並非通用歷史版本解析器。
未知 catalog 或不同 payload 會停止。後續固定 commit 若只有 installer／非 payload
文件改動，而 catalog、完整 payload 與清單一致，可以使用；receipt 記錄實際 HEAD。
可安裝 payload 或 catalog 有未提交修改、未追蹤額外檔、缺檔或 mode 差異時會停止。
Partial/promisor clones 不支援。Repository origin 字串與 digest 是來源／完整性檢查，
不是發行者簽章或 GitHub Tag／Release 已發布的證明。表列版本只表示來源／套件版本。

新安裝選一個群組，相依群組自動加入。以下是需操作人員另行授權的安裝範例，
不是閱讀本文件就執行的命令：

```sh
./install.sh install codex-review-workflow --source /trusted/fixed-checkout
./install.sh update --all --source /trusted/other-supported-checkout
```

跨固定 catalog 更新／降版必須明確選取所有既有管理群組（即使同為 0.34.0）；否則停止並提示使用 `--all`。
`--all` 不新加入 opt-in agent profiles，但會保留並更新先前已明確安裝的 profiles。
同版新增群組可保留其他管理群組，重跑同版 install／update 不認領額外檔案。
移除全部受管內容時，若已裝 profiles，先明選 `uninstall codex-agent-profiles --yes`，
再選 `uninstall --all --yes`。Uninstall 的 `--all` 不選 profiles；尚有相依就拒絕移除。
要降版，仍執行目前受審 installer，再用 `--source` 選舊 payload；不要執行舊 installer。
Core 隨套件固定攜帶，無獨立 installer。選無 Core 的舊版時，交易會退休新版 Core 檔。
Core 交易將完整受管目錄作為單一 rename／rollback 單位，receipt 仍逐檔驗證；
Core 退休時其完整 root 不殘留。其他非管理空父目錄可以保留。
普通 loader 僅接受正式 Core v0.1.1／14 檔；只有目前 installer 明選受審歷史 13／11 檔 descriptor，
仍逐項驗 metadata／bytes／mode／digest，不以任意 lock 或舊 validator 取代。

### 管理權與失敗邊界

新增的 `managed-<canonical-roots-digest>.json` 綁定技能、templates、profiles 根目錄、
群組、實際固定 source revision/version/Core，以及每檔 SHA-256／executable bit。
`installed.jsonl` 保留相容操作歷史，不能單獨證明管理權。舊 receipt 沒有 target-root
binding，因此本版不自動遷移它；`--previous-source` 會明確停止。
即使檔案同 bytes，也不認領缺少管理證據的 imported／unknown 安裝。
真實舊安裝遷移需另行取得可查證的 target ownership 證據與決策；本候選不完成此事。
Receipt 綁定完整三個根目錄；先選定整組 targets。既有安裝若只切換 profile root，
目前不會從另一組 receipt 自動認領共用 dependencies，會停止。新鮮 custom／project
安裝可使用，但多組根共享 dependencies 的管理尚不支援；不要刪 receipt 來繞過。

更新、降版與 uninstall 先核對全部既有管理檔，再確認 plan 身分未漂移。
自訂 bytes、exec bit、額外檔／空目錄、symlink、hardlink、unsafe owner/mode、缺檔或
不完整 receipt 都會停止。`--force` 保留為相容旗標，不豁免這些條件。
非管理 sibling 不被移動或刪除；碰到 planned destination 時停止。
已啟用／保留的 local model mapping destination 仍受既有 guard 保護。

三種操作重用既有 transaction、lock、反向 rollback 與 receipts 替換。
先驗目標 payload／內含 Core，暫存完整新內容，再 promotion，讀回完整 inventory、
退休檔缺席、Core 及 receipt，才報成功。跨 filesystem rename 不可確立時停止。
普通失敗嘗試回復本次 originals；回復失敗報非零與 `CRITICAL`，保留精確位置。
不要把殘留 receipt 或 history row 當作成功；必須重新核對完整 payload。
完整 commit 後清理／unlock 失敗也以非零與 cleanup pending 回報。

### 暫存與回復

Staging 與本次必要 originals 放在 owner-safe state 的交易目錄：
`${XDG_STATE_HOME:-$HOME/.local/state}/codex-dev-skills/backups/v1/transaction.*`。
Receipt 暫存在同一安全 state namespace。已知標準技能、commands、plugins、bundled
skills、相容技能根，以及明選 custom targets，會做 canonical overlap 與有界直系
symlink entry 檢查。範圍由 `install.sh` 的 protected roots 定義；不保證排除任意手填
runtime search paths，也不做全機設定掃描。安全 state 不可放在這些探索根內。

交易成功後，只清理本次建立且身分仍吻合的可重建 originals；不強制永久整包備份。
歷史 backups、未知資料及回復失敗原件不會自動清理。可自行保存固定來源供離線重裝；
cache 不是必要條件，也不能保證來源日後一直可得。來源不可取得時，離線重建不可用。

遇到失敗，先保留輸出的 transaction／receipt recovery 位置與現況，再核對哪一步完成。
確認沒有 installer 運作後，才由操作人員針對精確 originals／targets 決定回復。
若回復完成且 inventory 再次吻合，可以用目前 installer 加原固定 `--source` 重裝／降版。
若管理狀態不完整，先人工釐清，不刪 receipt 來繞過保護，不用 `--force` 強蓋。
本流程不保證 SIGKILL／斷電的跨根原子性、敵對 same-UID 隔離，或不同 state namespace
對同 target 的互斥。Lock 只協調使用相同 canonical state 的合作程序。

開發核對使用 repo 的 `./scripts/project-python -B scripts/sync-installer-catalogs.py --check`。
支援新來源需先審其不可變來源與完整 inventory，再更新產生器的固定 revisions。
不要只改版本字串。此文件採 STE100 原則；未驗證完整標準符合性。

## English

The current installer reads package data from a selected complete local Git checkout.
Its program root stays separate from the `--source` payload root. It does not download
sources or execute the selected source's old installer, validator, hooks or filters.
It requires Bash, Git and Python 3 stdlib. Integrity checks add no PyYAML dependency;
existing skill runtime dependencies still apply.

The table above identifies five fixed catalogs/payloads: 0.33.1, distinct
development and formal-Core split snapshots with the same 0.34.0 version, 0.35.0,
and 0.35.1.
The data allowlist binds the full file set, bytes and executable bits.
Unknown catalogs or payloads stop.
A later fixed HEAD with only installer or other non-payload changes is supported when
its catalog and complete payload still match. The receipt records that actual HEAD.
Dirty payloads, extra untracked skill files, missing files and mode drift stop.
Partial/promisor clones are unsupported. Origin text and digests do not authenticate
a publisher or prove GitHub Tag/Release publication. The listed versions describe
source/package versions only.

Use the current installer with `--source /trusted/fixed-checkout` to select a supported
version. The examples above require a separate operator decision before execution.
Cross-catalog update or downgrade, including the same version, must explicitly select all managed groups, or stop.
`--all` adds the normal groups. It does not newly opt into agent profiles, but updates
profiles that were already installed deliberately. Same-version group additions preserve
other groups. Repeated install/update does not adopt unknown identical files. For a
downgrade, run the current installer against old payload data. To remove all managed
content when profiles are installed, explicitly select `uninstall codex-agent-profiles --yes`
before `uninstall --all --yes`. Uninstall's `--all` excludes profiles and refuses to remove
their remaining dependencies. Core travels inside the
package; it has no separate installer. Downgrade to 0.33.1 retires the new Core files;
The transaction moves the complete managed Core root as one directory unit,
while receipts remain per-file; retired Core leaves no Core root. Other unmanaged
empty parents can remain. Ordinary loading accepts only the formal Core v0.1.1 fourteen-file pin. Only
the current installer explicitly selects fixed reviewed thirteen/eleven-file historical descriptors,
with full metadata/byte/mode/digest checks and no old validator execution.

The small `managed-<canonical-roots-digest>.json` receipt binds canonical target roots,
groups, actual source revision/version/Core and per-file hashes/executable bits. The
legacy `installed.jsonl` is history, not sufficient ownership evidence. Its old rows lack
target-root binding. This version refuses automatic legacy migration, including requests
with `--previous-source`. A matching source does not establish ownership of imported
files. A real legacy migration needs separately verified ownership evidence and a
decision; this candidate does not complete it.
Receipts bind all three target roots. Select that tuple before installation. Switching
only the profile root does not adopt dependencies owned under another tuple and stops.
Fresh custom/project installs work; sharing dependencies across root tuples is unsupported.
Do not delete a receipt to bypass this boundary.

Update, downgrade and uninstall verify all managed content before mutation and retain
the verified identities through apply. Custom bytes, modes, extra files/empty directories,
links, unsafe ownership/permissions, missing files or incomplete receipts stop. `--force`
does not waive these checks. Unmanaged siblings stay in place; occupied new destinations
stop. Existing local model mapping destination reservations remain protected.

The existing transaction engine stages new content, retains originals until payload/Core
and receipt readback pass, and rolls back failures. New and retired files participate in
the same transaction. A cross-filesystem rename stops. A failed restore returns nonzero,
reports `CRITICAL` and preserves exact recovery locations. A receipt/history row alone
is not a success proof: verify the full payload again. Cleanup or unlock failure after
commit returns nonzero and reports pending work.

Staging/originals use owner-safe state `backups/v1/transaction.*`; receipts stage in the
same safe state namespace. Canonical overlap and bounded direct symlink-entry checks
cover known standard skill/command/plugin/bundled/compatibility roots and selected
custom targets. `install.sh` defines that set. This does not cover arbitrary manually
configured search paths or scan all machine settings. Keep state outside discovery.

After success, cleanup removes only this transaction's verified reconstructible originals.
It does not require a permanent whole-package backup, delete historical backups or
remove unknown/recovery-failed data. You may retain a fixed source for offline recovery;
a cache is optional. Future source availability is not guaranteed. Without that source,
offline reconstruction is unavailable.

After failure, preserve the reported recovery paths and inspect completed steps. Confirm
no installer is active before an operator chooses exact original/target moves. Once the
original inventory is restored, use the current installer with its fixed `--source` to
reinstall/downgrade. Incomplete management state needs investigation; deleting a receipt
or adding `--force` is not a recovery procedure. There is no cross-root atomicity guarantee
for SIGKILL/power loss, hostile same-UID isolation, or lock coordination across different
state namespaces targeting one destination. The lock coordinates cooperating processes
with the same canonical state only.

Developers check generated data with the pinned repository resolver and the `--check`
command above. Review each new immutable source and inventory before adding a supported
revision; changing a version label is insufficient. This text follows STE100 principles;
full standard conformity is unverified.
