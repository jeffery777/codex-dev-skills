# Manual Dashboard, Queue, And Diagnosis

Inspect the selected command's current public help. `codex agents` and
`codex queue --thread <THREAD> --message <TEXT>` were observed in CLI 0.149.0;
that observation is not a future capability guarantee. The private-clone executor
does not automate either command because they do not share the isolated
`codex exec --json` terminal-turn contract.

For `agents-dashboard`, return `codex agents` and identify the authority needed
for the exact later dashboard mutation. Existing explicit authorization remains
valid while target, scope, and effect stay unchanged.

For `manual-queue`, preview the exact canonical UUID and complete bounded,
nonsensitive message. Reject credentials, private paths, customer/incident
details, shell-control text, further-dispatch requests, destructive behavior,
or scope expansion. Return an exact argv token list with the message as one
token. Do not send it from this manual adapter.


- `codex agents` is an interactive CLI control plane over the runtime's shared
  local app-server daemon. Using the public command does not authorize starting
  an app-server or remote-control daemon directly.
- Dashboard discovery or viewing is observation. Starting, opening, renaming,
  or stopping a task is a distinct runtime-state action and requires exact
  authority at selection time.
- Prepare `codex queue` only with a canonical UUID. Do not use a session name,
  `--last`, private state, or dashboard display text as identity authority.
- Preview and validate the full queued message. It must be bounded,
  nonsensitive, non-destructive, free of shell-control text, and within the
  already selected task scope.
- Represent the queue invocation as an argv token list. Never concatenate or
  interpolate the message into a shell command. If an executable shell command
  is explicitly requested, require a known shell and verified literal quoting
  for the complete message; otherwise keep the argv-only boundary.
- Queue acceptance proves only that delivery was requested. It does not prove
  the destination woke, processed the message, changed files, passed checks, or
  completed repository work.
- Do not pass model, sandbox, approval, remote endpoint, profile, extra
  directory, or bypass flags unless a separately reviewed future adapter
  defines and verifies those semantics.


A prepared command is not execution evidence. A successful queue result is
dispatch/wakeup evidence only, not processing or completion evidence.

`codex doctor --json` is a read-only, redacted diagnostic fallback for requested
runtime diagnosis. It cannot prove operation support or replace active public
help/schema inspection. It grants no private-state or daemon authority.

`codex mcp-server` was removed in standalone CLI 0.154.0; the observed Desktop
bundled CLI 0.153.4 still exposes it. It is outside this session adapter. Check
the selected executable's exact subcommand help shape, not just exit status:
0.154.0 can return root help with exit 0 for the removed command. Its public
migration boundary is app server for product integrations or the SDK for
CI/automation; neither authorizes this skill to start a daemon or make direct
app-server calls. Codex external MCP client configuration is a separate surface.
