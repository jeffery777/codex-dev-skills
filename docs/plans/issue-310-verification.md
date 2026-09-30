# Issue #310 驗證與審查紀錄

日期：2026-09-30。狀態：自動驗證、独立審查與使用者委派的正式入口五操作驗收完成；沒有 commit／PR／發布。
Repository：`jeffery777/codex-dev-skills`；branch：
`codex/issue-310-memory-maintenance-local-entry`；base／HEAD：
`4da847604ba4713a1a4f36b742395bf8fc09026a`。未提交 working-tree 內容另行綁定。

## 已接受的交付界線

Operator CLI 與同 UID 信任限制、可追溯官方 source 的隔離 runtime，以及
`mg1-local-operation/v1` 容量不足安全拒絕均已由使用者接受。
使用者再次確認：不要求製造實體滿庫、不要求滿庫停止保證；驗證重點是錯誤
處理行為。受控 `SQLITE_FULL` 注入是行為證據，不是實體 FULL 資格。

首次寫入前的容量拒絕回 `not-applied` 且不執行 mutation；五操作 mutation
之後的錯誤依獨立新 reader 判定 `applied`／`not-applied`／`unknown`。初始化若
已部分建立後才失敗（包括等待後容量重查），保留 partial 並回 `unknown`，
不冒充五操作的獨立讀回。錯誤本身不證明 rollback；unknown 不重播，輸出或
terminal teardown 失敗亦不得改寫已讀回的結果。沒有自動修復／清理。

## 獨立審查與 finding 處置

深審 round 2 綁定 patch SHA-256：
`07f208a2d1b384e391b89b50c9cbe5b392f89a8d658b9e0f6563d7934b69216b`。
此識別限當時完整 patch；後續用量與本紀錄是文件補充，不能冒充同一 diff。

| Finding | 風險 | 處置 | 修正與重審證據 |
| --- | --- | --- | --- |
| D310-R01 / P1 | terminal teardown 錯誤把已 applied 結果改成 not-applied | Fixed | main 保留已回傳 outcome/proof；獨立 round 2 重審與 teardown fault test 通過 |
| D310-R02 / P2 | initialize 尚未建立時的失敗誤列 unknown | Fixed | 第一個 mutation attempt 前分類 not-applied；低容量 main test 通過 |
| D310-R03 / SHOULD-FIX | 新拒絕原因未列入既有 reason allowlist | Fixed | 補 reason whitelist；獨立 8 項 reason-code 查核通過 |
| D310-DOC01 / P2 | 把容量拒絕與新 reader 分類寫成涵蓋所有初始化的保證 | Fixed | 限定首次寫入前拒絕、五操作 fresh readback，以及初始化 partial／unknown 三種情況；文件比例重審 |

唯讀深審 round 2：PASS，無新增 blocker。另有獨立安全 finding discovery，
涵蓋六個正式 production sources 與六個逐 bytes 相同的 generated mirrors，零 findings。
Exact source／build／容量推導由獨立 storage reviewer 核對；不是以成功測試代替推導。

Security Diff Scan：`27ee0d0e-37df-4365-939b-47c29421edf9`，已由 native completion
與 completed-scan readback 確認封存，26 surfaces、零 findings、零 deferred。
封存時間 `2026-09-30T05:03:08.734697Z`。原始 snapshot：
`codex-security-snapshot/v1:sha256:93f8d6fd1a49d90af6785d675e5a43d8e452965862e5f19cc37156a832e112e0`。
原始 snapshot 早於上述修正；scan 明示以 round 2 immutable patch 作人工補充重審，
不宣稱原始 snapshot 已包含新 revision。此後文件補充需比例審查。

## 已執行驗證

| 範圍 | 結果與限制 |
| --- | --- |
| Round 2 focused | 11 local-entry + 31 maintenance/local tests 通過 |
| 共用 core/storage/fault | 獨立深審共 85 tests 通過；修正後另做 42 tests 與 12 main fault cases |
| SQLITE_FULL 行為 | 提交前回 not-applied；提交後 fresh readback 回 applied；at-most-one mutation；unknown 行為沿用 core/fault 回歸 |
| 官方隔離 runtime | Python 3.12.9、SQLite 3.53.4 exact source、必要 compile options、actual pragmas 與 qualification 通過；FTS5 補入以支援既有 repo M1 檢查 |
| Repo hygiene | `validate-repo.sh --skip-unit-tests` 通過；不代表 unit shards 全通過 |
| Package／版本 | 153 generated files parity、offline release-state 0.32.0、diff whitespace checks 通過；未發布 |
| 隔離安裝 | 第一個目標的 fresh install／force upgrade／installed 11 mechanism tests 通過；最後文件更新遇既有備份槽碰撞而拒絕，保留全部備份。另從 frozen round 2 source 建立新隔離目標，fresh install／最後 upgrade／`diff --all` 通過；17 個入口相依程式檔與已審查 source 逐 bytes 相符 |
| Default-off／非 TTY | installed entry disabled 零接觸；非 TTY 明確拒絕；不作人工授權證據 |
| 替代固定環境全量 run | 在 FTS5／interpreter 修正完成後跑完 12 shards／93 modules／1462 tests，11 shards 通過；agent-profile shard 曾有 1 failure，單項重驗與完整 66 tests 重驗均通過。回歸覆蓋已通過，但原完整 run exit 1，不能改稱單次整套成功 |

先前混用 interpreter 的舊 run 執行期間隔離 runtime 補入 FTS5，正式操作必需
flags/source 不變；該舊 run 未完成且已中止，不能宣稱全程不可變 runtime 或
整套通過。上表是修正後另起的替代固定環境 run，兩者不可混用。
沒有進行實體 FULL、ENOSPC 或 ENOMEM 耗盡試驗。

安裝器以 `PATH` 的 `python3` 啟動子程序，單設 `CODEX_PROJECT_PYTHON` 只固定
測試 runner，不能證明子程序使用同一 interpreter。原環境選到 pyenv shim，
隔離 runtime 的 `make altinstall` 又只提供 `python3.12`；僅將該 bin 加入 PATH
仍不能選到隔離 `python3`。新 run 使用本任務私有 test-bin 的單一 executable
symlink 指向已核對隔離 interpreter，啟動前驗證實際 resolved path 與 SQLite
3.53.4，沒有更動系統 PATH、shell 設定或 timeout 門檻。原失敗與無效 PATH
調整的失敗紀錄保留；新 run 的 production source/build/環境保持固定，不覆寫原紀錄。
完成替代回歸後，已核對並以 SIGINT 停止原先混用 interpreter 的舊測試 group，
保留其失敗與中止紀錄；不將未完成的原 run 計為通過，也未刪除安裝備份或驗收資料。

Memory／evaluation shard 的 545 tests 與 installer-runtime 的 53 tests 均在新固定
環境通過。Agent-profile 的完整重驗按 manifest 載入三個原 modules，執行 66 tests；
只為先前失敗的案例增加 stderr 觀察，不 mock installer、改 assertions 或門檻。

## 殘餘驗證風險

`D310-V02`：一次 agent-profile user/project ownership 安裝回 nonzero，原測試
未保留該次 stderr，原因仍 unknown。單項重驗及完整 66 tests 重驗均成功；
`install.sh` 與 agent profiles 沒有本包修改，不推定為已修復的產品 bug。
後續依使用者決策，受影響 ownership 測試的四次安裝／移除 assertion 已加入
階段標籤及 captured stdout／stderr，失敗時直接呈現在測試輸出；不改回傳碼
要求、assertions 的成功條件、安裝行為或重試次數。本次本機受限契約暫視為通過，
該安裝異常仍未解，依下述條件重開阻擋。
診斷修改後的 ownership 單項實際重驗通過；受控 project install 失敗檢查
亦確認 assertion 同時包含階段、stdout 與 stderr，沒有吞掉失敗。
此 test-only 診斷改動不影響已封存 scan 的 production source 或入口 fingerprint。
處置：Deferred（非本機入口內容 blocker）。負責人：本專案維護者；持久追蹤目標：
本節及 Issue #310 的後續 PR verification。理由：保留失敗，現有完整範圍重驗已通過，
沒有可重現且可歸因於此 patch 的缺陷。剩餘風險：安裝器仍可能間歇失敗。
驗證計畫：後續 PR 的 hosted CI 必須通過，重現時保留 stderr、實際 interpreter、
target/state identity 並重新審查。升為 blocking 的條件：相同固定環境的串行
重驗再次失敗、CI 失敗，或證據顯示與本包產品改動有關；不得忽略或提高 timeout。

## 委派 actor 模式的比例驗證與正式驗收

使用者於 2026-09-30 明確授權 agent 操作與驗收；D310-01b 取代人工限定，
不取消完整 preview、當次 action/digest、來源與環境審查、TTL／撤銷、單次 mutation
及獨立讀回。`--actor` 只是紀錄種類，不自行證明上游委派。

- 47 focused tests 通過；獨立 reviewer 的 22 個 mock／記憶體檢查通過。
- actor 程式深審 PASS；原四個未變來源逐 bytes 核對後明示重用 round 2 證據。
- 新 Security Diff Scan `ee723513-212d-4c5b-a0d9-29ec774047a7` 已封存並讀回：
  inventory 的 12 個 production files 完整覆蓋，0 findings、0 deferred。
  新 actor 邊界重新審查；未變的 storage/core 證據明示重用，不冒稱整包重新掃描。
  Snapshot 為 `codex-security-snapshot/v1:sha256:3402447550ff9b544c981be24c6cc61d62e2cd615d6567b4a33a400c07ba4935`。
  Findings SHA-256 `c34024b5d631a3604e3ae3dcf833fd4e3e27289fbe39dac8f5e9fd06704d1f21`；
  coverage SHA-256 `4e56bfd3899387f8361315052bb6ccf42f8b21c37c28c159551158c535644715`。
- D310-DOC02：舊混合環境 run 與替代固定環境 run 的文字界線已釐清；
  前者未完成且中止，後者完整執行但 exit 1，兩者均不宣稱單次全套通過。
- D310-ACTOR-DOC01：roadmap 的人工限定文字已修正為 operator／兩種 actor。
  此非 source 文件修正晚於 scan snapshot，作明示比例補充；未改 production bytes。
- repo hygiene（略過已另行執行的 unit tests）、153 generated files parity 通過。
- 新隔離目標從 frozen round 2 fresh install，review diff 後 managed update／force
  升級通過，保留備份；`install.sh diff --all` 通過。17 相依程式逐 bytes 與 source 相符。

正式入口以真實 controlling／foreground TTY，由已受委派 agent 每次完整查讀
preview 後輸入當次 action/digest，未使用 mock、測試 callback 或盲目 token feeder。
只有固定 revision 的公開 `catalog.yaml` 版本事實；沒有既有真實 memory。
Sandbox 初次拒絕 `/dev/tty` 時回 not-applied 且 root 未建立；正常權限提升後才執行。

| 步驟 | 正式入口結果與獨立讀回 |
| --- | --- |
| init／enable | applied；新 root 初始 disabled，再另次接受 enable |
| add | applied；active revision 1、保留 1 版、current-only verified |
| update | applied；active revision 2、保留 2 版、current-only verified |
| stop | applied；stopped revision 2、保留 2 版、空 current projection |
| resume | applied；active revision 2、保留 2 版、current-only verified |
| restore retained 1 | applied；建立 active revision 3、保留 3 版、新 validation evidence |
| disable | applied；descriptor enabled=false，保留資料與 proofs |

最後另起唯讀 connection 核對恰有五個 distinct operation proofs，皆為
`agent-operator-` evidence；retained revisions 為 1/2/3，current projection 只有 3，
final state 與最後 proof 一致，restore 的 body 等於 retained 1 且 validation evidence
不同。私有 root、資料庫與完整 transcript 不同步進 repository。
Source adapter fingerprint：`b7f60360a52791793cb7b0572506641210bc8cb8f178dc8d5c40e82b7554d6a6`。

既有 `LocalAuthorityPort` 的 human docstring 屬原 generic port；本次入口使用
`OperatorTerminal`／`MaintenanceAuthorityProvider`，不以該文字宣稱 agent 是人類。
這份驗收不證明背景／跨專案、native Desktop confirmation、完整 MG1 或滿庫 stop。

## Gate 與後續交付

本機受限契約的實作／驗證 DoD 完成；沒有待決產品問題或人工驗收步驟。
D310-V02 保留 Deferred，原完整 shards exit 1 與後續完整 affected shard 重驗通過
均保留，不能改稱單次全套成功。Formal commit／PR readiness 尚未簽發；若後續
建立 PR，仍需完整 exact-head Merge Review 與 hosted CI。本紀錄不授予外部寫入。

新增功能符合 pre-1.0 minor 版本評估方向，候選準備屬後續交付；本包保持
catalog 0.32.0，不修改歷史 release notes，不聲稱 publication。Commit、push、
PR、receipt、merge、tag／Release、deploy 仍各核對有效授權。
