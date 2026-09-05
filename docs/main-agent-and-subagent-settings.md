# Main-agent and subagent settings

This repository owns reusable configuration sources and routing policy. Those
sources are not necessarily the files a running Codex client loads. Installation
and explicit client settings determine the effective runtime configuration.

| Concern | Repository source | Runtime location or control |
| --- | --- | --- |
| Main-agent recommendation | `examples/project-main-agent.config.toml` | Trusted project `.codex/config.toml`, or user `~/.codex/config.toml` for a cross-project default |
| Explicit conversation choice | No repository-owned current value | Desktop model/effort picker or CLI `--model` and configuration overrides |
| Child role model, effort and sandbox | `agent-profiles/*.toml` | Installed custom-agent profiles, for example `~/.codex/agents/` or a selected project agent root |
| Classification and fallback | `policies/model-selection-policy.md`, `skills/loop-engineering/scripts/agent_routing.py`, `loopctl.py` | The invoked workflow and its installed scripts |
| Canonical role contracts | `skills/loop-engineering/references/agent-profile-registry.json` | The canonical registry shipped with the invoked skill |
| Availability and quality opt-in | Caller-supplied runtime facts | Current destination/runtime evidence, not a permanent repository assertion |

The main-agent example selects Astra-high for demanding delivery, decomposition,
integration and acceptance. It is a project recommendation, not an OpenAI-wide
default or a measured equivalence claim. Routine bounded work may use medium;
Sol-high is an explicit alternative when Astra is unavailable. Do not silently
substitute a model or infer capability from its name alone.

For CLI/IDE, official precedence is explicit CLI overrides, trusted project
configuration, a selected configuration profile, user configuration, system
configuration, then built-in defaults. A user config is therefore not inherently
project-specific. Desktop conversation selections must be verified through the
active public client control; copying a file does not prove an existing Desktop
conversation changed model or effort. See the official
[configuration basics](https://learn.chatgpt.com/docs/config-file/config-basic)
and [model controls](https://learn.chatgpt.com/docs/models).

## Adoption

Read and merge the example's two keys into the intended configuration layer;
do not overwrite an existing file or copy secrets and machine-local settings
into this repository. The installer does not install this example or change
personal main-agent defaults. This Issue does not apply it to the current chat.
Confirm the selected model/effort in the destination before delegating work.

Child roles should receive explicit model/effort settings from their selected
profile. Otherwise native inheritance can make a small child task inherit the
main agent's expensive configuration. An explicit spawn override or configured
subagent default can change native resolution; this repository cannot assume
which wins without checking the actual runtime. See the official
[subagent settings](https://learn.chatgpt.com/docs/agent-configuration/subagents#choosing-models-and-reasoning).

The installed baseline profiles remain Luna-low mechanical, Terra-low explorer,
Terra-medium everyday, Terra-high senior, Sol-medium advanced, Sol-high
deep/security and Sol-xhigh exceptional. Astra-medium advanced and Astra-high
deep/security profiles remain separately qualified opt-ins. Main-agent selection
does not qualify these child profiles or bypass their gates.

## Escalation is a workflow decision

The main agent first gathers repository evidence, records task factors and uses
the existing class/tier classifier. Security, data, migration, public-contract
and broad-write risk cannot be offset by a desire for speed. Use high-effort
review for those boundaries; implementation still requires the appropriate
scope and authority.

Reassess after a reasonable correction fails the same core check, when a root
cause cannot be explained, or when authoritative evidence conflicts. Update the
bounded task assessment and select a supported, sufficient profile. Examples:

- Clear extraction or mechanical work starts at Luna-low. Ambiguous cross-file
  reasoning should move to an appropriate Terra or stronger role.
- Exploration starts at Terra-low; ordinary implementation at Terra-medium;
  complex bounded implementation may require the Terra-high senior tier.
- Advanced work starts at Sol-medium or a qualified Astra-medium candidate.
  If deeper reasoning is needed, use an explicitly supported high-effort task
  configuration only where the runtime and workflow permit it. It is not an
  existing high-effort implementation profile in the canonical registry.
- Deep/security review starts at high. Multiple interacting trust boundaries,
  unresolved cross-system causes or major architecture tradeoffs can justify
  xhigh. Max/Ultra are not default escalation targets.
- A delivery main agent starts at Astra-high under this optional preset; xhigh
  requires the same concrete depth triggers and a supported client control.

These conditions are decision guidance, not an implemented automatic retry or
effort-changing controller. Do not alter a fixed profile's bytes/effort in place
and retain its old qualification digest. The current classifier chooses existing
profiles; new combinations require an explicit supported override outside that
fixed-profile route, or a separately validated profile change. Neither route may
lower the required class/tier or widen sandbox and authority. Missing data,
permissions or environment support require resolving those constraints rather
than increasing reasoning effort.
