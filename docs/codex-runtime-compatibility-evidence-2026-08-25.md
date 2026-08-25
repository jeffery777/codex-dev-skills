# Codex Runtime Compatibility Evidence — 2026-08-25

This is point-in-time compatibility evidence for Issue #179. It records public
OpenAI documentation and local public Codex CLI help. It does not read or
commit Desktop databases, logs, sessions, caches, credentials, app state, local
plugin caches, memory files, or machine-local configuration.

## Observed Public CLI And Documentation

| Surface | Observation | Classification |
| --- | --- | --- |
| Codex CLI | `codex-cli 0.149.1` | Local public command output. |
| `codex mcp-server` | Still appears in local public help | Deprecated command; not removed in this observed CLI. |
| Removal date | No published date found | Unknown; do not infer one. |

On 2026-08-24, the public [Codex changelog](https://learn.chatgpt.com/docs/changelog)
and [deprecated MCP server guidance](https://learn.chatgpt.com/docs/mcp-server)
marked `codex mcp-server` deprecated. The deprecated command ran Codex itself as
an MCP server for an integration. It is not the general MCP ecosystem, an
external MCP server configured for Codex, a Codex app connector, or a native
ChatGPT desktop task/thread tool.

For an integration that formerly ran Codex as an MCP server, use the public
[Codex app server](https://learn.chatgpt.com/docs/app-server); use the Codex SDK
for automation or CI as directed by that documentation. The app-server API has
stable and opt-in experimental boundaries, and its documented command and
WebSocket transports remain experimental. Replacing the deprecated command
does not authorize this repository to start an app-server daemon or to call
app-server endpoints directly.

Codex remains an MCP client: public
[MCP client configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
continues to document `codex mcp add`, `codex mcp list`, and external-server
configuration. This deprecation does not apply to those commands, external MCP servers,
connectors, or native thread tools.

## Desktop Evidence Boundary

No Desktop callable schema was re-read for this update. The Desktop capability
table and callable observations in the 2026-08-21 evidence remain point-in-time
records and must not be treated as a current schema assertion. These descriptions are current-session evidence, not a published stable schema. They do not authorize a live session/thread mutation, sharing action, or private runtime-state inspection.

Historical `desktop_runtime_*` wrappers are inactive. They are not a replacement
or migration path for `codex mcp-server`.

## Compatibility Decisions

1. Preserve the existing 2026-08-21 Desktop table as historical, point-in-time
   capability evidence.
2. Keep native Desktop thread tools, external MCP client configuration, and
   connectors distinct from the deprecated `codex mcp-server` command.
3. Keep repository adapters on their documented native callable or public CLI
   boundaries; no adapter gains an app-server, SDK, or daemon control path.
