# Optional GitNexus Runtime Integration

Read only before using or assessing the optional GitNexus hook/controller
path. Hooks are optional guardrails and are not complete enforcement; the loop
must remain safe when they are absent or miss an equivalent tool path.

The optional V2c-B GitNexus runner uses only documented `SessionStart` and
`PostToolUse` events for `Bash` and `apply_patch`. It is notify-only by default,
never parses the shell command, patch, tool response, or transcript, and
treats those events as incomplete repository-change signals. Auto-on-demand
requires separate machine-local opt-in and delegates only a clean eligible
revision in the exact configured checkout to the qualified V2c-A controller.
Each primary checkout or linked worktree requires its own exact machine-local
root and worktree-bound index identity; a config for one checkout must reject
events from another. Linked-worktree automatic refresh remains unqualified and
fails closed without updating the primary checkout's index. After a merge, the
primary checkout must first advance locally; its next `SessionStart` or
completed `Bash`-matched shell/unified-exec event can then refresh that clean
HEAD. A remote PR/MR result
alone cannot update a local index. Controller failure installs a durable
repository-bound circuit breaker so later hook events cannot retry
automatically without operator clearance. Installing its templates does not
activate hooks or grant trust. The shipped runner stays synchronous because
background hook invocations may overlap and finish out of order.

The GN-FU-01 `gitnexus-index-identity/v1` sidecar makes exactness content-bound,
not HEAD-only. A qualified refresh writes it only after metadata postconditions;
later status/hook checks require an exact repository, checkout/worktree,
branch/HEAD, complete relevant content, tool/configuration, and freshness match.
Missing/old evidence plus dirty tracked, untracked, mixed, detached, ignored-
content-drifted, or cross-worktree state is advisory. PR base/head pair identity
binds two clean committed contents but proves no review or gate. These documents
remain non-authoritative and do not enable linked automatic refresh.

For explicit local 1.6.12 index writes, use `qualify_local_1612` from
`../scripts/gitnexus_adapter.py`, then the existing `RefreshController` with
per-operation opt-in. The operator CLI continues to select 1.6.9. The local
entry reuses accepted version/help receipts without probes and binds accepted
entry/Node/package bytes, runner identity, self-contained dependency resolution,
nearest-lockfile guards and caller-owned coverage paths. Keep those values
private; metadata cannot supply its own trust or expected coverage.

The new profile performs a full rebuild with `--no-parse-cache`; it rejects
same-HEAD refresh, external dependencies and invalid existing metadata. It also
refuses any repository `.gitnexusrc` entry, including ignored files and links,
before execution and again immediately before launch. Those execution defaults
are outside this profile; source stability remains an operator prerequisite. A fresh
private HOME holds registry/tmp/identity cache. Coverage hashes, metadata,
registry, complete content/Git-control evidence and sidecar readback must pass.
Its sidecar cannot enable automatic refresh, hooks or queries. A02 verified this
accepted GitNexus 1.6.12/Node 25.9.0 installation on macOS arm64: the actual
controller handled stale revision -> refresh -> metadata/registry/sidecar and
internal freshness readback. The outer worker's early Git index stat-cache
baseline exception is retained; offline reconciliation found only cached ctime
changes, not staged content changes. No second outer freshness API or live retry
ran. Reaccept identity and repeat affected integration checks after tool/runtime
or dependency changes. A03/A04, read_query/MCP, other platforms
and Grok remain unqualified. Use source/Git when matching evidence is absent.
The current orchestrator assigns one writer and verifies stable source and
reader handoff; Codex is not the permanent index manager.

1.6.12 明確本機寫入使用 `qualify_local_1612` 接既有 controller；operator CLI
仍選 1.6.9。接受的本機 bytes／runner、獨立相依解析、較近 lockfile 與明定
coverage 都須綁定；重用 version/help 證據，不啟動 probes，不從 metadata 自授信任。
新 profile 使用 `--no-parse-cache` 完整重建，拒絕同 HEAD、外部相依與損壞 metadata；
執行前與啟動前重驗並拒絕任何 `.gitnexusrc` entry（含 ignored 檔與 links），
不接受該檔的執行設定；仍須協調全程來源穩定。
新 HOME 隔離 registry／tmp／identity cache，完整驗證後才寫入及讀回 sidecar。
它不啟用 automatic refresh、hooks 或 query。A02 已驗收接受的 GitNexus 1.6.12／
Node 25.9.0、macOS arm64 安裝：實際 controller 完成 stale→更新→metadata／
registry／sidecar 與內部 freshness 檢核。外層 worker 的早期 Git index stat-cache
baseline exception 保留；離線讀回只見 cached ctime 變動，staged 內容未變，
外層第二次 freshness API／live retry 未執行。Tool／runtime／相依更新後須
重綁接受身分並驗證受影響整合。A03／A04、其他平台與
MCP／Grok 未資格化；缺證據時回到 source／Git。編排方指定單一 writer 並交接，
Codex 不固定擔任索引管理者。
