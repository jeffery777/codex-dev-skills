# GitNexus 1.6.9 Qualification Receipt

## Scope And Runtime

- Platform: macOS arm64 (live local execution).
- CLI version output: `1.6.9`.
- Executable discovery returned one symlink entry. The qualification policy
  allows a symlink only by explicit opt-in when its resolved target is a regular,
  executable file and both link and resolved target remain bound to the current
  runtime observation. A machine-local path is intentionally omitted.
- Version output SHA-256: `081fc7e5bb2414d0c9ca544579db7e4e3302d82ccd647e256de1a7397694266a`.
- Resolved CLI entry SHA-256: `233ece3066020a9098aa7fa448e04beff8452169497248cb1e5c316e508bfbbc`.
- Package manifest SHA-256: `19b863bcd78488e174e251a1690ab69555caf0a669077771a701b62aa49b4fae`.

Machine-local executable, package, repository, index, and registry paths are
runtime control-plane evidence only and are not stored in this repository.

## Capability Evidence

Observed command-help digests:

| Surface | SHA-256 | Qualification |
| --- | --- | --- |
| `analyze --help` | `2872a472d6d3bd8739c9495388d0ec0d6cb17df13ff91befc6206f689fe76d53` | Required flags include `--index-only`, `--skip-agents-md`, `--skip-skills`, `--branch`, and `--name`. |
| `status --help` | `b3e271d64f187c6ce8ec681ec7bb9143aca459d3789767c9fb0cc3f6db15161f` | No structured/JSON option. Human status output is never parsed by the adapter. |
| `query --help` | `991a1cadbf5d206d0031e33205ac1f246566bbf1c7fa527811fc5a07b1c42542` | Direct CLI implementation emitted JSON during observation, but this interface is not qualified for adapter use. |

Source inspection of the installed 1.6.9 package established:

- primary metadata is `.gitnexus/gitnexus.json`;
- `.gitnexus/meta.json` is a legacy mirror/fallback;
- a present but corrupt primary must not fall back to the legacy mirror;
- fresh 1.6.9 analysis writes `schemaVersion: 5`;
- the direct `query` command emits a JSON object but can include volatile timing,
  degraded/partial warnings, and instruction-like text; V2c-A does not parse or
  adopt this output and declares `read_query` unsupported.

Live qualification evidence-bundle digest:
`4321890ed8c5f0dd95f2ab6d84a97d9c385b6caf23af4fe86fec7feda1cea4af`.
It binds the captured driver id, exact version, CLI/package bytes, help digests,
required flags, symlink policy, metadata filenames/schema, observed query
behavior, and lack of structured status. The production adapter separately
generates its runtime qualification fingerprint from executable bytes, exact
version, observed analyze flags, schema/filenames/capability policy, symlink
policy, and the bound Node runtime used by the npm entry. Any drift requires
requalification and V2b conformance.

## Existing Index Observation

The original checkout was inspected read-only. Its legacy-only metadata records
indexed revision `1e73dbee15d59cf231e75bf3039e0a3b7b124714`, while repository HEAD is
`a75728b15f5d15ba7bf1a7e6e3a2dd934915592e`; its metadata schema is `1`.
The driver therefore treats it as incompatible/stale evidence and does not
refresh or adopt it. No original index or registry state was changed.

## Isolated Index-Only Analysis

An isolated temporary Git repository and isolated HOME/registry were used. The
fixture tracked eight files, including root/nested AGENTS.md, another supported
assistant instruction file, `.codex/`, a skill file, workflow policy, source,
and tests.

First-build baseline:

- HEAD: `926e712f808fca8fbb8e414d8345c67f366f24a2`.
- clean diff digest: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- full tracked-content digest before/after:
  `9551d7510f48a16e105d978b55d69b33e5c663f4c0b87cdafad2fbfcb82914bc`.
- exact operation: qualified executable argv plus
  `analyze --index-only --name <isolated-unique-alias> <fixture-root>`.
- result: exit `0`, metadata schema `5`, indexed HEAD matched, primary and legacy
  metadata bytes matched, no incremental-dirty marker, and no tracked/protected
  worktree mutation.

The first run revealed two disallowed side effects outside the tracked view:

- analyze-specific optional-extension handling may attempt an FTS download when
  the environment does not explicitly forbid it; the sandbox blocked the
  connection and no external system was accessed or changed;
- a direct repository with a normal `.git` directory receives a local
  `.git/info/exclude` entry for `.gitnexus/` when that entry is absent.

The initial run is therefore fail-closed qualification evidence, not an accepted
refresh. The controller must force the offline extension policy and must not
write Git local exclude state. It requires the exclusion precondition to be
already satisfied when GitNexus would otherwise write it, and compares the
exclude digest before and after. A worktree whose `.git` is not a directory is
also handled explicitly rather than guessed.

Offline refresh baseline:

- HEAD: `06947e282d180d7d65696c7d22732c6093a152d7`.
- clean diff digest: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- full tracked-content digest before/after:
  `2b00fba9603d094b6c80124afdfa22f7de138e1d6857b5f3b43ffc1edb506211`.
- isolated environment forced `GITNEXUS_LBUG_EXTENSION_INSTALL=never` and did
  not expose credentials or embedding endpoints.
- result: exit `0`, one added file indexed incrementally, metadata schema `5`,
  indexed HEAD matched, file hash count `8`, primary/legacy bytes matched, no
  tracked/protected mutation, and no network install attempt.

Final accepted refresh with local-exclude precondition:

- HEAD: `a374a467f668d93b191b126f73929188bc92e21d`.
- clean diff digest: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- full tracked-content digest before/after:
  `976d1a999c540ad295c72bbf4e23d3938af98877d1fcbfda9fd82f3c37218771`.
- `.git/info/exclude` SHA-256 before/after:
  `8cb44cb1662f982c78a4380327d43bb261bff43b7cf4916655102f5fa495370c`.
- `.git/config` SHA-256 before/after:
  `bd1a3e8a733087d1a0c2293d1b8d2064fd1b00da55352b03abeb66b6e66c4c27`.
- `.git/HEAD` SHA-256 before/after:
  `28d25bf82af4c0e2b72f50959b2beb859e3e60b9630a5e8c603dad4ddb2b6e80`.
- exact isolated `GITNEXUS_HOME` and offline-extension environment were supplied;
  no credentials, proxy, embedding endpoint, or inherited GitNexus settings
  were exposed.
- result: exit `0`, metadata schema `5`, indexed HEAD matched, file hash count
  `9`, primary/legacy state converged, no network install attempt, no tracked,
  protected, local-exclude, Git config, or HEAD mutation. Only the qualified
  derived index and isolated registry changed.

## Production Controller Requalification

After integration, the production adapter's own discovery and refresh
controller were executed against a new isolated clone at the accepted base
revision. The npm entry's `env node` interpreter was resolved, invoked directly,
and bound into qualification rather than relying on inherited `PATH`.

- Runtime qualification fingerprint:
  `8106875b9184184ca7a7a8c788d6799f3c1c55ac72821f5a3a54893506da176d`.
- Symlink policy: explicit resolved-symlink opt-in; resolved CLI and Node runtime
  bytes/stat identity were stable before and after qualification.
- Exact controller operation: bound runtime plus bound CLI entry and
  `analyze --index-only --name <isolated-unique-alias> <canonical-fixture-root>`.
- Result: `refreshed`, reason `qualified-index-adoptable`; indexed revision
  matched expected HEAD. The final post-review rerun indexed 244 tracked-file
  hashes under schema `5` and emitted refresh receipt digest
  `489e21fe9da9e7b3ccb6fa220b2b51b6696ce24aa90807a6eaae5155894a07db`.
- Full tracked-state digest before/after:
  `f71ff4c3c53ba19931bb8f314824bd5cc010c5088a27fb2e037c394fd0453183`.
- Complete-status digest before/after:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Protected-state digest before/after:
  `3e4dc14220f747b41e90bbf6fd898953ed6e7418a859ee29f40074d027d28b2c`.
- Combined Git-control digest before/after:
  `30e24a5f5ed5353f147f596b7938f3e3bc7d14ba744341678df7cca538cbaa59`.
- Automatic refresh authority remained `false`; metadata, complete status,
  protected paths, Git-control files, executable/runtime, and repository
  identity postconditions all passed.

This fingerprint is specific to the current qualified runtime. Reinstallation,
runtime/entry byte changes, accepted-flag changes, or metadata capability-policy
changes require a new fingerprint and conformance evidence.

## Unqualified Query Observation

An exact 1.6.9 `query --query <text> --repo <canonical-root> --limit 3` operation
against the isolated fresh index returned JSON. FTS was unavailable, so the
payload contained a degraded warning with command-like remediation text and
volatile timing. The tracked-content and diff digests remained unchanged.

This observation does not qualify a JSON query driver. V2c-A declares
`read_query` unsupported and never parses, binds, or adopts this output. A future
read capability would require a separate stable-interface qualification,
bounded structured parser, full V2b request/repository/revision/fingerprint
binding, and negative conformance review.

## Portability And Limits

- macOS arm64: live CLI discovery, build, incremental refresh, metadata, and
  query evidence completed.
- Linux: not live-tested. Tests must exercise POSIX path/process behavior,
  regular-file and symlink policies, executable discovery, environment, timeout,
  lock, and metadata fixtures without claiming live Linux qualification.
- GitNexus human status/list output and machine-local registry paths are not a
  production data contract.
- FTS/vector unavailability narrows query capability; it never authorizes a
  repair, forced analyze, extension installation, or network access.
