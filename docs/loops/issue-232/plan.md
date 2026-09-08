# Issue #232：契約相容的技能執行方式

## 範圍與基準

- Issue：<https://github.com/jeffery777/codex-dev-skills/issues/232>
- 分支：`codex/issue-232-capability-compatible-skills`
- 基準：`914f8a5c596d698bcd0ab1c389ff66091ec07259`。
- 2026-09-08 先建立並讀回 Issue，再建立隔離 worktree、推送未修改分支，最後編輯。
- 父代理為唯一實作者；獨立 reviewer 唯讀檢查最終差異與證據。

## 工作包與完成條件

1. 擴充既有 reusable-workflow contract，區分可替換方法與必要契約，保留
   使用者指定、較高優先指令、工具、獨立審查、模型資格、gate 與記憶邊界。
2. 六個一般技能、兩個共用編排入口與兩個 formal gate 加入薄引用；直接呼叫
   與編排選用一致，舊名稱及輸出格式保持相容。
3. 補入 plugin allowlist；驗證 source/plugin 引用及預設／自訂安裝位置的
   契約 bytes。既有 filesystem catalog 已包含此契約。
4. 選用案例逐項做語意審查；驗證器與安裝測試只能證明靜態／套件契約，
   不能宣稱模型已通過行為、品質或成本比較。
5. 更新選用指南、roadmap 順序，準備同 Issue 的 patch candidate。

## 版本判斷

建議 `0.24.1`：已安裝技能的必要契約不減少，允許在相同義務下重用執行結果，
修正選用歧義；不新增工作引擎、模型路由選項、儲存 backend 或資料 schema。
這是對既有行為的相容性修正，與新增執行能力的 minor release 不同。
需發布可識別的安裝內容，故不採用只合併文件而不準備版本。

Source/package 由 catalog、installer 與 plugin manifest 一致定義；新 release note
僅記候選準備。發布真相須核對 annotated tag 與 GitHub Release，既有 notes 不改。
本規劃不證明發布或部署完成，各操作沿用當時有效授權及 gate，不另建 release Issue。

## 驗證與風險

使用 `./scripts/project-python` 的 tracked interpreter；重點涵蓋 packaging、
installer、native runtime、review dispositions、release-state 與 roadmap。
完成 repository 離線驗證及必要完整 test shards、diff 檢查與獨立審查。
主要風險為指令被誤讀成可略過 gate、資料或方法限定，以及安裝後引用缺失；
以明確必要契約、反例及真實隔離安裝驗證處理。

本次不讀／寫真實記憶、不調整模型預設，不做付費跨模型實驗。
合併後的原生能力與本地技能選用仍屬模型遵循指引，沒有新增 runtime 強制攔截。
