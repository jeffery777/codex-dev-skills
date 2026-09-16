# GitHub Control Plane Policy

Use this policy whenever a shared workflow reads or mutates GitHub state. It
applies equally to Codex CLI and Codex Desktop entrypoints; runtime adapters
must not duplicate or weaken it.

## Control Plane Order

1. Read local repository state with local `git`: checkout, branch, upstream,
   remotes, worktrees, index, working tree, commits, and base-to-head diffs.
2. Use the installed GitHub plugin or connector as the primary GitHub control plane
   for repository metadata, Issues, pull requests, comments, reviews,
   labels, checks, workflow metadata, and every platform mutation it exposes.
3. Use `gh` only when the GitHub plugin or connector does not expose the exact
   required operation, or when that operation fails because the connector's
   granted permission is insufficient.

A repository habit, an existing shell snippet, convenience, or familiarity
with `gh` is not enough to bypass an available connector operation.

## Fallback Classification

Before using `gh`, record one of these reasons:

- `connector-operation-unavailable`: the active GitHub plugin has no callable
  for the exact required operation;
- `connector-permission-insufficient`: the callable exists but the connector
  reports that its granted GitHub permission cannot perform the operation.

Do not treat target mismatch, ambiguous repository identity, validation
failure, authentication conflict, rate limit, transient service failure, or an
unreviewed schema change as permission insufficiency. Classify those failures
and stop or retry through the same control plane only when that is safe.

After a justified fallback, verify the same exact owner/repository, Issue or
pull-request number, branch/head SHA when relevant, authentication context,
and result that the connector path would have required. Report the fallback
reason in the delivery or readiness evidence.

## Shell Shape And Repeated Approval Prompts

After a justified `gh` fallback, prefer one simple command for each API call.
Keep the API call separate from saving its returned output locally. Shell
redirection (`>`, `>>`, `<`), substitutions, environment assignments, or other
compound syntax can change the command submitted for policy matching. A
previously approved `gh` prefix may then no longer match the shell invocation.
This is a possible cause, not a diagnosis of every approval prompt.

When saving evidence, use a separate authorized local file operation on the
complete returned output. Preserve its bytes and verify completeness; a
truncated tool response is not a complete API artifact. Do not reconstruct
missing JSON, embed untrusted output in executable shell text, or repeat a
GitHub mutation merely to recover or save its response. Unknown mutation
results require readback before any retry.

If approval prompts recur, stop repeating the same command shape and inspect:

1. The exact executable and argument vector, including basename versus
   absolute path, flag order, shell wrapper, redirection, and substitutions.
   Do not change executable identity solely to obtain a different rule match.
2. The relevant saved rules and their source, plus which layers the current
   runtime actually loads when observable. A saved rule is not proof that an
   already-running or different session loaded it. Keep secrets, private
   paths, and unrelated saved commands out of public evidence.
3. The active runtime's public diagnostic interface. When supported, use
   `codex execpolicy check --rules <rule-file> -- <exact-command-arguments>`
   with the relevant rule files. Inspect `matchedRules` and any decision;
   absence of a match is not an explicit denial or permission to run.
   A direct-argv check does not reproduce the shell parser or the complete
   Desktop approval path. Do not infer live approval solely from this check.
4. Remaining controls: sandbox and network restrictions, managed rules,
   approval mode/reviewer, GitHub authentication and permissions, and the
   exact operation's user authorization. If their effective state cannot be
   observed, retain that uncertainty rather than blaming `AGENTS.md` or
   promising that a command rewrite will remove prompts.

Keep necessary approvals. Do not widen a prefix rule, add blanket `gh api` or
shell allowances, modify saved rules or global instructions, disable the
sandbox, or conceal side effects to avoid prompts. `gh api` can perform both
reads and writes; its prefix alone does not establish read-only intent.
Command simplification changes execution shape, not operation authority.

The [official Codex rules documentation](https://learn.chatgpt.com/docs/agent-configuration/rules)
describes argument-prefix matching and conservative treatment of shell
redirection. These runtime details remain version-scoped; inspect the current
public help and reported behavior before relying on them.

## Exact-Head Provider Evidence

For provider-neutral exact-head content review, follow
`policies/exact-head-merge-review-contract.md`. Only when repository policy selects
the GitHub hosted enforcement model, also follow
`policies/github-exact-head-enforcement-profile.md`. Read the current PR base,
head, merge base, diff identity, hosted CI, findings or reviews, unresolved
threads, and platform-visible receipt through this control plane. Normalize
that state for offline validation; do not let the validator access GitHub
itself. Repeat the live readback immediately before an authorized merge because
an earlier receipt or successful check can become stale.

When that profile is selected, the hosted v2 collector is a trusted
default-branch control-plane client, not
an executor of PR code. It resolves the live PR and explicitly targets the
custom check at `pull_request.head.sha`; it must not infer that SHA from a
default-branch event context. It reads the single App-pointer-selected
whole-body strict JSON issue comment as the receipt and verifies its digest.
It must not treat rendered
Markdown, an arbitrary comment fragment, workflow artifacts, or a shared
GitHub Actions check identity as the authoritative receipt or dedicated-App
identity. Upstream hosted CI uses an exact trusted workflow ID/name/path/event
and associated live PR head, and excludes `Exact-Head Merge Readiness` itself.

## Mutation And Authority Boundary

Connector-first does not authorize a GitHub write. Creating or editing Issues,
opening or updating pull requests, posting comments or reviews, changing
labels, rerunning checks, merging, tagging, and publishing Releases still
require the exact authority and human gate defined by the active workflow.

Local `git` remains the normal control plane for branch creation and working
tree state. Commit, push, force updates, tag creation, and destructive Git
operations retain their separate authority and safety requirements.

Registering or installing a GitHub App, configuring a protected environment or
secret, changing a ruleset, activating a ruleset, and modifying bypass actors
are separate high-impact platform mutations. Require an exact reviewed payload
and post-mutation readback for each. A ruleset rollout first remains disabled
until a canary check identifies the dedicated App integration ID; activation is
a later, independently authorized mutation. Do not grant the collector merge,
auto-merge, tag, Release, deployment, comment, review, or arbitrary content
write authority.

## Dependency Unavailable

If neither an applicable GitHub connector operation nor an authenticated,
authorized `gh` fallback is available, continue only with local Git evidence
that is sufficient for the current read-only task. Mark GitHub metadata as
unverified and stop before any platform-dependent claim or mutation. Do not
scrape browser UI or inspect private application state as a substitute.
