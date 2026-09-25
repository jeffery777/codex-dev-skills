# Issue #299 驗收紀錄

## 實作與固定邊界

新增 `--create-synthetic --scenario add-update-restore`，沿用 shared
GovernanceCore、原 schema 與 pinned Git source reader。沒有修改核心或
production registry；CLI／Desktop 入口分層不變，原兩個情境保持相容。
歷史只由本次固定 fixture 的還原預覽揭露，不進入一般 recall。

## 本機驗證

使用 `scripts/project-python` 選定 Python 3.12.9／PyYAML 6.0.3：

- 新增 13 項 restore tests：完整 snapshot-bound current/history/candidate、
  revision 3／三版保留／current-only、各步取消、同秒重新驗證、來源與候選
  替換、前態／TTL／root／lock 漂移、舊 digest 與 handle 重播拒絕。
- 受控 ENOSPC／SQLite／MemoryError 覆蓋交易前後；proof insert 失敗保持兩版
  與原 projection；提交後 readback／audit／輸出失敗或中斷保留 unknown。
  POSIX child 提交後退出，由新 core 讀回 applied，不能恢復舊 grant。
- focused 與受影響回歸共 155 項通過，包括原 maintenance/content 情境、
  G1 contract/core/local/process-readback、audit/pilot 與 test shard 契約。
- 12 shards／91 modules 完整列舉；140 個 generated plugin 檔案 parity 通過。
- 在隔離 custom targets 分別新安裝及從發布的 v0.28.0 升級；兩者 `diff --all`
  無差異，安裝後入口無 opt-in 回 disabled，實際 CLI 互動逐步確認得到
  revisions 1/2/3，blue/green current-only 核對一致。未部署至使用者技能目錄。

完整 repository 結構檢查及正式 review/scan 結果由當次
主代理驗證與正式 gate 記錄補充；本節測試紀錄不取代那些完成證據。

## 審查與發行狀態

實作前獨立唯讀設計查核要求讀取實際 retained document，不以固定 ADD 候選
冒充完整歷史；本實作使用相同 snapshot 的唯讀讀回，並於確認等待前釋放鎖。
正式 deep review 與 Security Diff Scan 必須綁定最終內容。若修正造成內容變動，
重新核對受影響驗證與審查，不以此文件自證 no-findings。

Source/package 候選為 0.29.0；v0.28.0 與更早 release notes 保持歷史紀錄角色。
本文件不宣稱 0.29.0 已發布；tag／正式 Release 與部署需要各自授權及讀回。
本輪 synthetic／受控故障不構成真實記憶、G2、完整 G1/MG1、物理耗盡或
power-loss qualification。Production registry 保持空，未讀寫既有／原生記憶。
