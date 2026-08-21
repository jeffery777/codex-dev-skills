# Codex Runtime Compatibility Evidence — 2026-08-21

This is point-in-time compatibility evidence for Issue #161 and the v0.16.2
candidate. It records official OpenAI documentation, local public CLI help,
and callable schemas exposed to the active Codex Desktop task. It does not
read or commit Desktop databases, logs, sessions, caches, credentials, app
state, local plugin caches, memory files, or machine-local configuration.

## Observed Runtime

| Surface | Observation | Classification |
| --- | --- | --- |
| Codex CLI | `codex-cli 0.149.0` | Local public command output. |
| Desktop dependency bundle | `26.818.22352` | Active Desktop workspace dependency metadata; not a stable app API version. |
| Desktop task tools | Active callable schemas described below | Current-session contract evidence; schema version is unavailable unless noted by a result. |
| Public product naming | Codex runs in the ChatGPT desktop app | Official documentation. `Codex Desktop` remains this repository's compatibility label. |

Recorded versions are observations, not minimum-version declarations. Every
adapter must inspect its active surface and use the documented fallback when a
capability is absent.

## Official And Public CLI Facts

- [Codex changelog](https://learn.chatgpt.com/docs/changelog) records CLI
  0.149.0 with the interactive `codex agents` dashboard, `codex queue`, working
  directory commands, expanded `codex doctor` diagnostics, exact SDK config
  overrides, and permission-profile restoration fixes.
- Local `codex agents --help` describes an interactive dashboard over the
  shared local app-server daemon. The public command may search, start, open,
  rename, and stop tasks. The dashboard is a CLI control plane, not the shared
  subagent primitive or repository completion evidence.
- Local `codex queue --help` reports
  `codex queue --thread <THREAD> --message <TEXT>`. The target may be a UUID or
  exact session name, but this repository deliberately uses only a canonical
  UUID in prepared guidance and represents the complete message as one argv
  token rather than interpolating arbitrary text into a shell command. A queued
  message is a runtime-state mutation and wakeup signal, not proof that the
  destination processed the message or that repository work completed.
- Local `codex doctor --help` exposes redacted machine-readable diagnostics
  through `--json`. Diagnostics do not replace active-schema capability
  detection, authorization checks, or repository verification.
- The 0.149.0 changelog removes skill model delegation support. This repository
  does not encode model selection in skill frontmatter: opt-in custom-agent
  TOML profiles remain a separate runtime mapping over shared capability
  classes, so no profile or receipt migration is required.

## Active Desktop Callable Facts

The active callable schemas on 2026-08-21 preserve the existing creation,
fork, list, wait, message, handoff, archive, pin, title, navigation, panel, and
terminal-observation boundaries recorded in earlier evidence. In addition:

- `share_thread` creates an immutable share link for the calling thread or an
  exact accessible `threadId`, optionally using a preferred `hostId` while the
  runtime discovers other accessible hosts.
- The official changelog states that shared local Codex thread snapshots are
  read-only and do not update with the original. Personal-account links may be
  opened by anyone holding the link; workspace-account links are limited to
  the originating workspace. Known secret patterns are redacted, but users
  must still review the shared content because sensitive data may remain.
- The current callable exposes link creation but no revoke operation. Official
  guidance places link review and revocation in ChatGPT data controls. The
  adapter must not imply that it can revoke a link through `share_thread` or
  that link creation is automatically reversible.

These descriptions are current-session evidence, not a published stable schema
version. They do not authorize a live session/thread mutation, sharing action,
or private runtime-state inspection.

## Compatibility Decisions

1. Preserve shared orchestration, delivery, review, human gates, and completion
   authority beneath separate CLI and Desktop adapters.
2. Keep the private-clone executor limited to non-interactive `codex exec`
   start, resume, and fork. Add `codex agents` and UUID-only `codex queue` as
   explicit manual CLI control-plane routes rather than misrepresenting them as
   isolated executor operations.
3. Treat `codex doctor --json` as redacted diagnostics only and keep historical
   `desktop_runtime_*` wrappers inactive.
4. Add Desktop `share_thread` as an explicit privacy-sensitive mutation. Require
   audience evidence from current public product context, user confirmation of
   complete-thread review through the public UI or another complete exposed
   view, and inspection of available content. Recent, truncated, or paginated
   agent reads are insufficient. Keep link creation, revocation, and repository
   completion separate.
5. Preserve opt-in custom-agent profiles because removed skill model delegation
   is not part of this repository's skill or routing contract.
