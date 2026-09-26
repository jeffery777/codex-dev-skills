# Sidebar Sorting And Grouping Preferences

Runtime compatibility: desktop

只在使用者要求修改側邊欄排序偏好或分組時讀取。本 reference 是
`desktop-sidebar-organization` 的操作分支；不新增 CLI executor、共享選路
或 task 控制。以當次完整 callable schema 為準，以下為 2026-09-25 的
`update_sidebar_preferences` 契約基線，不是永久 API 保證。

## 欄位與作用範圍

| 欄位 | 當次允許值 | 語意 |
| --- | --- | --- |
| `sorting.chats` | `manual` / `priority` / `updated_at` | 專案以外的任務排序；共用於 Codex／Work。 |
| `sorting.projects` | `manual` / `priority` / `updated_at` | 專案內任務排序；不是專案項目的排列；共用於 Codex／Work。 |
| `sorting.pinned` | `manual` / `priority` / `updated_at` | 釘選任務與專案排序；共用於 Codex／Work。 |
| `grouping.mode` | `project` / `connection` / `list` | 依專案、依連線或單一清單分組。 |
| `grouping.surface` | `codex` / `work` | 分組只作用於指定 surface；callable 省略時預設 active surface。 |

`manual` 使用已儲存順序；`priority` 將需要輸入或未讀的任務優先顯示；
`updated_at` 按最近更新排序。工具沒有 sort direction 或每個專案的設定欄位，
不能把「最舊優先」或「只改某一專案」轉成近似 payload。
這與 `reorder_section`／`reorder_sidebar_projects`／`reorder_sidebar_sections`
的項目重排不同。不得為 reorder 自動切換 sorting，也不得為偏好更新補送
reorder；選擇 `manual` 不授權另寫一份項目順序。

## Discovery、意圖與最小更新

1. 讀當次 schema，再以 `list_threads` 取得新鮮的 `sidebarPreferences`。
   當次 registry 形狀為 `sorting.{chats,projects,pinned}` 與
   `grouping.{mode,surface}`；依實際公開回傳核對，不猜測缺值或預設值。
   偏好不依賴任務清單完整性，不為此查 `list_projects` 或要求 section IDs。
2. 解析使用者指定的欄位、值與範圍。具體請求可直接授權這項可逆操作，
   不因 callable 名稱或原始 JSON 再次詢問。動作摘要須說明排序共用於
   Codex／Work，或分組的確切 surface。「整理一下」不能決定任意偏好；
   明確要求「只改 Codex 的排序、Work 保持不變」與共用排序契約不相容，
   停止該修改並說明限制，不能悄悄擴大範圍。
3. 分組的目標須來自使用者明確指示，或已讀回的目前 active surface。
   本 adapter 在 grouping payload 明確傳入已確認的 `surface`，避免依賴
   call 時可能改變的預設目標；不能僅由執行環境叫 Codex 就推定 surface。
   必須能觀察該目標的既有分組才能準備修改與 no-op 判定。
   當次 `list_threads` 沒有 surface selector；若只回傳 Codex 分組，不能拿它
   當 Work 的 snapshot。沒有其他已暴露且可驗證的公開讀回路徑時，停止
   相依修改並提供手動 fallback，不臆造參數、自動切換 UI 或讀取私人設定。
4. 只傳明確指定且需要改變的欄位；省略欄位保持不變。不把完整 snapshot
   回送成 payload，不用 `null`、空物件或未知欄位模擬重設。Sorting-only
   請求省略整個 grouping；grouping-only 請求省略整個 sorting。
   對包含兩類偏好的請求，先確認整個請求的意圖、authority 與觀測條件，
   不在另一部分尚未釐清時先套用一半。
5. 新鮮 snapshot 若已符合全部指定值且 surface 正確，回報 `no-op`，
   不呼叫 mutation，也不宣稱已套用變更。Snapshot 過期或在 call 前出現
   衝突時重新讀取與規劃；只有新效果超出原授權才重新取得決策。

Dry-run 保留偏好欄位、既有值、要求值、共用排序範圍／目標 surface、
省略欄位、snapshot 新鮮度、預期 response 與 readback。這些是操作證據，
不要要求使用者提供或核准工具語法。

## 回應與讀回

- Call 前重新核對 schema、目標、最小 payload、新鮮度與授權。解析當次
  公開 response 的 applied preferences，不假定固定外層 envelope；必須沒有
  tool error 且能識別指定欄位的結果。Transport acknowledgement 不算成功。
- 然後透過 `list_threads` 或當次已驗證的公開能力取得 fresh readback，
  確認指定值與 grouping surface，並比對 preflight 中可觀察的未指定欄位。
  Sorting 的共用欄位讀回可證明偏好設定，不證明兩個 UI 已完成重新渲染。
  只看到另一個 surface，不能宣稱目標分組已驗證；沒有公開資料也不能
  宣稱另一 surface 的分組保持不變。
- 未指定欄位出現漂移，或回應／讀回未知、不完整、矛盾、過期、不符時，
  回報 `unverified`。保留已觀察事實與原因未知，不推定是哪個 writer 或
  runtime 造成。不自動重送、不補償性還原，也不把回應成功當作讀回成功。
- 必須分開報告 no-op、dispatch response 與 readback；偏好設定成功不等於
  任務移動、導航或 repository completion。失敗使用具體手動 fallback，
  不走 private state、UI scraping、app-server、daemon 或另一個相似 callable。

## Synthetic 範例與驗收案例

以下都是離線範例，不是本機偏好，也不得由測試或 CI 發送。

使用者要求「專案外任務依最近更新排序」，已確認共用作用範圍及現況需變更：

```json
{"sorting":{"chats":"updated_at"}}
```

使用者要求「Work 改為依連線分組」，且已取得 Work 分組的公開 snapshot：

```json
{"grouping":{"mode":"connection","surface":"work"}}
```

| 案例 | 預期處理 |
| --- | --- |
| 只改專案內任務排序 | 只更新 `sorting.projects`；不移動 project IDs。 |
| 只改目前 Codex 分組 | 確認 snapshot 的 surface 後只送 grouping；不修改 sorting。 |
| 已符合全部指定值 | `no-op`；沒有 mutation。 |
| 明確要求只改一個 surface 的排序 | 不相容；不送出跨 Codex／Work 更新。 |
| 目標 Work，但只讀到 Codex 分組 | 缺少目標觀測；不送出，不把兩者混用。 |
| 回應符合，但 fresh readback 不符或缺值 | `unverified`；不重送、不還原。 |
| 未指定欄位在讀回時改變 | `unverified`；不歸因、不覆寫並行修改。 |
| 只要求重排區塊 | 使用既有 reorder 分支，不呼叫偏好更新。 |

這些案例與文件檢查只驗證 adapter 指引及 payload 範例；不證明 live mutation
或所有 surface 的實際可觀察性。
