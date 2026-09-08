# Issue #231：驗證與審查紀錄

日期：2026-09-08。以下保留初次本地交付的 point-in-time 紀錄。
Gate Result：**PASS（當時本地 pre-commit code/docs 範圍）**。
Review Mode：mixed diff／獨立 deep review，加上 Security Diff Scan。
此結論只涵蓋 repository-only 設計與 synthetic metadata oracle；
沒有真實 backend、授權、刪除、原生管理或自然語言品質的完成聲明。

後續使用者已授權：修正後重新通過正式 review 及 Security Diff Scan，
無 findings 後可 commit／push／建立 PR；exact-head Merge Review 無 findings
且必要平台檢查通過後可直接合併。後續最終九檔審查、安全掃描與 merge 證據
另綁定該次 scan／PR receipt；以下舊八檔 inventory 不代表後續內容。

## 版本與範圍

[Issue #231](https://github.com/jeffery777/codex-dev-skills/issues/231)
已讀回為 open、無留言，設計範圍仍適用。
依 Issue-first 從 `6ab5ee2982637c78e80d723e5b6310885d02f5e0`
建立並推送 `codex/issue-231-memory-scope-lifecycle` 後才修改。
本地 HEAD 與起始 upstream 仍為該 SHA；變更尚未 commit。

審查固定八檔：oracle、其測試、shard manifest、設計、治理里程碑、
原生共存、roadmap、[plan](plan.md)。
下方 SHA-256 inventory 以路徑排序，JSON indent=2 加尾端換行的 digest 為
`be1f512be1f14614b59858541206919c77df07ea18b9025a7482811269cc331b`。
本紀錄為安全快照完成後新增的第九檔，只接受最終文件／敏感資訊／一致性檢查，
不宣稱包含在先前八檔獨立審查或安全快照中。

## 實作與驗證

- 分離 scope/backend；native 保留 runtime-management-required，不與 MG1 雙寫。
- discover 限定明列 store、principal/project、unique root 與 coverage；
  不可讀或缺席資訊不轉為不存在。
- preview/confirmation 綁定精確集合、完整 snapshot、版本、digest、principal、
  request 與期限；seen request 只回 reconciliation-required。
- summarize 綁定原 preview/confirmation/execution snapshot 與每目標版本；
  missing/unknown 先 reconciliation，failed/not-executed 只列 retry candidates。
- retirement 只有 explicit-retirement 可列候選；UI 移除、改名、離線與 worktree
  移除不提供清理權限，native／共享或跨專案關係另行檢視。
- 所有結果保持 `operation_authorized=false`、
  `runtime_proven=false`、`write_performed=false`。

使用 tracked resolver 選定 Python 3.12.9／PyYAML 6.0.3：

| 驗證 | 結果與限制 |
| --- | --- |
| focused unittest | 46 項 PASS |
| 完整 12 shards | 1,079 項 PASS；包含上述 46 項，不重複計數 |
| validate-repo --skip-unit-tests | PASS；unit tests 由完整 shards 獨立涵蓋 |
| plugin generated parity | 114 個檔案 PASS；oracle 未納入安裝 allowlist |
| release-state offline validation | PASS；source/package 0.24.1 未變，未查 publication truth |
| diff hygiene／八檔 SHA-256 | PASS；修正後內容與審查 inventory 相同 |

完整 shards 執行期間完成修正，但受影響 memory shard 在最終內容固定後執行，
該 shard 的 230 項包含本次 46 項；其他 shard 無受影響內容漂移。
新增本紀錄後只重跑 repository offline validation 與 diff hygiene。

## Finding dispositions

獨立 reviewer 完成兩次 review、一輪修正；最終 MUST-FIX、SHOULD-FIX、NIT 均為空。
主代理比對逐檔 hash 並檢查修正；agent integration receipt 為 accepted，
只作協調證據，不以其 status 取代測試或完成證明。

| ID | 問題 | Disposition |
| --- | --- | --- |
| F1 | 重複 root ID 可別名同一 store | Fixed：拒絕重複 supplied root ID；實體 alias 仍須未來 host 驗證 |
| F2 | 缺席 outcome 不應直接重試 | Fixed：missing/unknown 列 reconciliation，保留目標 metadata |
| F3 | 結果缺少原始 preview 與 execution binding | Fixed：綁定原 confirmation/snapshot/time 與逐目標 revision/digest |
| F4 | seen map 不足以證明重播已成功 | Fixed：回 reconciliation-required，不回已成功 no-op |
| S1 | snapshot freshness 未完整固定 | Fixed：有界有效期及 preview 後 fresh snapshot；仍是 supplied clock |
| N1 | 文件繁體用字 | Fixed：統一繁體文字 |

沒有 deferred findings 或尚待人類決策的本輪審查項目。
後續 production prerequisite 列於[設計](../../memory-scope-lifecycle-design.md)，
由 MG1 後續 host/backend 工作負責；加入真實副作用入口前須重新接受及驗證，
不能用此 PASS 跨越該邊界。

## Security Diff Scan

Scan ID：`62462995-1a35-468b-bfe3-42bb061063bb`。
固定 snapshot：
`codex-security-snapshot/v1:sha256:448163adf085998b38c6d1a27278fdcd48819fc6dfe76e2b3aaed3b8993565bb`。

掃描涵蓋八個變更檔案，以及必要的 G0 純函式 helper、package allowlist 與
SECURITY.md；獨立架構核對唯一實際 caller 為單元測試，沒有 production sink。
原生 review inventory 的一個 source item 與其餘七個測試／文件／manifest
均已逐項處理，沒有把全 repository 檔案計數當成審查覆蓋。

封存與讀回成功，findings 為空；**canonical coverage 為 partial**。
最終 complete:true draft 已提交完整覆蓋及空 deferred，但工具仍保留早先
`independent-architecture` 暫存項目，理由為「獨立架構回執尚在完成」。
該回執其實已完成並納入封存 threatModel；這是 final readback 與最後提交內容
不一致的紀錄限制，不能把 report 標示改述為完整安全 gate PASS。
未改寫 sealed artifacts、未另建掃描或再次 completion。

後續使用安全 gate 前，須透過受支援的工具流程處理此 coverage 紀錄差異；
不以本地 code/docs PASS 略過。
工具回報 usage 為 totalTokens=10,487,800，其中 cachedInputTokens=10,128,768、
outputTokens=50,576；此為工具的三個 task 累計口徑，非本次增量或費用。

Preflight capability checks 通過；TAC 為 not_granted，已顯示其 advisory。
此狀態不取代 source evidence，也不提供較高權限。
canonical threat model 保留 caller-supplied metadata、unkeyed digest、可信 clock、
真實 root mapping、relation provenance、durable replay、executor/readback 等邊界。
無候選時不另行執行 candidate validation 或 attack-path phase；
這不是 runtime penetration test 或真實資料清除驗證。

## 可重跑驗證與下一個 gate

```sh
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python -m unittest tests.test_memory_scope_lifecycle
./scripts/project-python scripts/test-shards.py run-all
./scripts/validate-repo.sh --skip-unit-tests
git diff --check
```

未 commit、未推送實作、未建立 PR、未 merge、未發布、未安裝或修改 runtime 設定。
若後續授權 commit／push／PR，先確認本紀錄的 inventory 與當時工作樹仍相符；
PR 建立後須另跑完整 exact-head Merge Review 與所選 GitHub enforcement，
本地 gate 不能替代 hosted CI、receipt、review threads 或 dedicated App 證據。

## 固定八檔 inventory

```json
[
  {
    "path": "docs/loops/issue-231/plan.md",
    "sha256": "299b2e03165e87588815aa4a58d5a2122dd7a3d2e865ba9a0bc9a95b2a9846fb"
  },
  {
    "path": "docs/memory-governance-milestone.md",
    "sha256": "de7fae8689083d36837592ed5abd96ea86906940c214f403e7387084f34716c5"
  },
  {
    "path": "docs/memory-scope-lifecycle-design.md",
    "sha256": "471b0b7d8e90c7350fb799aba8b04ba1c97509bc8e222c78d664293ef6399646"
  },
  {
    "path": "docs/native-memory-coexistence.md",
    "sha256": "0b24e6fff8248915586839bd4c0f653c9f053c37fcdbcd86135d70f6da7016a5"
  },
  {
    "path": "docs/roadmap.md",
    "sha256": "2a05eb716053de625415077502e1eeb35eadd1793ef3874470bec963003a65a5"
  },
  {
    "path": "scripts/memory_scope_lifecycle.py",
    "sha256": "baa3a4221c507a57a3b97a2cacf954d92fb6b4807f45867e10db0cf158c92140"
  },
  {
    "path": "tests/test-shards.yaml",
    "sha256": "12e95f383f6a46024a5b6da830af82e83f70270cc8ac2bba26be072bf77aea17"
  },
  {
    "path": "tests/test_memory_scope_lifecycle.py",
    "sha256": "dd84ce67f3e20ae65e8b49f552f8bace43900486b60b283c43fece165bdb26c5"
  }
]
```
