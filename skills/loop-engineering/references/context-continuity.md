# Context Continuity And Fresh Rollover

Read when the configured unfinished review/fix threshold is reached, or
context evidence otherwise calls for assessment or ownership rollover. Follow
`../../../policies/context-continuity-policy.md` in source/plugin checkouts or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/context-continuity-policy.md`
after filesystem installation.

Context continuity follows the shared policy above.
After two unfinished review/fix rounds by default, or another configured
positive threshold, run `loopctl.py context-health` with the installed
`context-continuity.template.yaml` when executable evidence is needed. The
threshold starts assessment only and never authorizes a task mutation.

The assessment has five outcomes: continue the current context, reground it
from durable sources, delegate one disjoint high-noise packet to a shared
subagent, prepare a fresh rollover, or stop for a human gate. Token and
compaction signals are auxiliary only.

A fork preserves completed conversation history. A fresh rollover deliberately
does not: it starts from a canonical checkpoint that binds repository/objective,
exact Git state, completed and remaining work, verification, risk, next packet,
source/destination writers, and confirmed source stop-writing. Fresh rollover
is sequential same-objective ownership transfer; subagent delegation is
parallel packet ownership while the delivery owner remains responsible.

Require stable rollover/checkpoint lineage. Exact replay is a no-op, conflicting
reuse fails closed, and another rollover without material progress is forbidden.
Graph `continues_as`, checkpoint, or context-health projections are advisory
only and cannot create tasks, choose writers, satisfy gates, or prove
completion. The assessment itself performs no runtime action; Desktop/CLI
adapters retain separate exact mutation gates and IDE uses current-session or
prompt fallback when no qualified control plane exists.
