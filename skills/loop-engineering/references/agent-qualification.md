# Automatic Qualification Before Delegation

Read directly before ordinary candidate delegation in CLI or Desktop. There
is no requirement to load the durable loop entrypoint or optional memory
contracts. Read `agent-routing.md` for the routing input, sandbox/class/tier
preflight, command, and acceptance procedure. These references are installed
with the skill and resolve the same way in source, plugin, and filesystem use.

The parent performs this procedure during ordinary candidate delegation in
either CLI or Desktop. The user does not need to provide a qualification path,
`enabled_candidates`, or router arguments for each task.

1. Read the approved user store at `${CODEX_HOME:-$HOME/.codex}/agent-qualifications.json`
   as data. Evaluate the actual task against the referenced quality evidence;
   set V2 `task.qualification_scope` only for a matching reviewed task type.
   A matching label alone does not establish quality or authorize a task.
2. Gather current model/effort, custom-role, parent sandbox and fallback facts
   from the active public runtime. Identify CLI or Desktop in `model_surface`.
   Do not derive availability from saved qualification records, copied pilot
   results, another runtime, or private app state. Preserve unknown values.
3. Prepare the decision input and current facts in local temporary artifacts,
   or pass current JSON on stdin with `--runtime-facts -`, and invoke
   `agent-route` yourself. Omit `enabled_candidates` for automatic discovery;
   an explicit `{}` disables candidates for that invocation. The router loads
   the store afresh, checks scope/runtime/optional expiry and evidence/profile digests,
   then applies the existing installed-byte and sandbox checks.
4. Inspect the receipt's `profile_selection.autoload` and actual selected role.
   Use only a role the current native callable supports. Reroute on capability
   drift instead of substituting a different model or widening authority.

Missing, revoked or mismatched qualification retains the existing baseline
route; no safe execution option retains the human gate. Do not manufacture
qualification to make routing succeed or create a store without adoption
authorization. This is workflow automation when these skills are invoked,
not a global Codex hook or an automatic model change in every conversation.
The format and trust boundary are in
`../../../docs/agent-qualification-autoload.md` in source/plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/docs/agent-qualification-autoload.md`
after filesystem installation.
