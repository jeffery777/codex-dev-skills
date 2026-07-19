# GitNexus 1.6.9 Qualification Receipt

## Scope And Runtime

- Platform: macOS arm64 (live local execution).
- CLI version output: `1.6.9`.
- Executable discovery returned one symlink entry. The qualification policy
  allows a symlink only by explicit opt-in when its resolved target is a regular,
  executable file. Qualification and every later verification bind the resolved
  target bytes/stat identity plus the explicit final-symlink policy; parent and
  multi-hop symlinks are rejected. A machine-local path is intentionally omitted.
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

- Historical pre-P5 runtime qualification fingerprint:
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

The P5 executable-boundary and lock/filter hardening changed the fingerprint
schema by binding the CLI and Node symlink policies independently. The current
production adapter was therefore requalified live on macOS against a new
two-file isolated repository with a new empty local home/registry and lock
boundary:

- GitNexus version: `1.6.9`; required flags include `--index-only`,
  `--skip-agents-md`, `--skip-skills`, `--branch`, and `--name`.
- Historical post-boundary runtime qualification fingerprint:
  `faad158749423e34fa1123f4cb004b71a18c850032ed7f920f7cb74f58cab640`.
- GitNexus CLI policy: `resolved-symlink`; Node runtime policy:
  `resolved-symlink`; both were explicit opt-ins and independently
  fingerprint-bound.
- Exact controller operation remained bound runtime plus bound CLI entry and
  `analyze --index-only --name <isolated-unique-alias> <canonical-fixture-root>`.
- Result: `refreshed`, reason `qualified-index-adoptable`, schema `5`, indexed
  revision equal to the expected typed fixture HEAD; refresh receipt digest
  `e5e41e0460770fd5e2cbec61f8d307225461ae521dc17934b2c8114ba9edf270`.
- Full tracked-state digest before/after:
  `2d295c3dc6be1190606008b1308bf7cc44ca60d516f468abb3afdb2905b9fc34`.
- Complete-status digest before/after:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Protected-state digest before/after:
  `ec8a351da306a763cbfa955fd944d2a6e7138445f23dd29e12dd7685ab3d8714`.
- Worktree-state digest before/after:
  `a20df7fa0b13ff106f56c6eae2282c92d230583b12922df9b16be28f126e48dd`.
- Combined Git-control digest before/after:
  `7874f205c0df6393dd6c57e2d43047b2d0142326665c4cfc180920748474822c`.
- The independently repeated tracked status/diff remained empty and the
  protected `AGENTS.md` digest remained unchanged. Only `.gitnexus/` and the
  isolated machine-local registry/home received derived state.
- Automatic refresh, repository mutation, external-write, gate, and completion
  authority all remained `false`.

This fingerprint was specific to the then-qualified runtime. Reinstallation,
runtime/entry byte changes, accepted-flag changes, or metadata capability-policy
changes require a new fingerprint and conformance evidence.

## Historical Round-15 Controller Refresh

After the canonical-lock and final descriptor/replay corrections, the current
production controller was run once more against a new two-file isolated macOS
fixture, empty local home/registry, explicit native Git, pre-existing local
exclude, and a separate instance lock. The exact operation remained bound
runtime plus bound CLI entry and
`analyze --index-only --name <isolated-unique-alias> <canonical-fixture-root>`.

- GitNexus version/fingerprint: `1.6.9` /
  `faad158749423e34fa1123f4cb004b71a18c850032ed7f920f7cb74f58cab640`;
- result: `refreshed / qualified-index-adoptable`;
- schema state: fresh; indexed revision matched typed fixture HEAD;
- refresh receipt:
  `0de43413239d5db2bc9917f24b547b697be93a543d505b6cc4b846eba30338fe`;
- tracked-state before/after:
  `e01054843e9ff187fe4a7f62c3b427ebb3c044ad36dd34562cef98816df7a394`;
- complete-status before/after:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- protected-state before/after:
  `96b2a061150f78f36d6f79b9df63aebb51b7286faf4cc2146ecf40e4badf7605`;
- worktree-state before/after:
  `fb5620eb224f81d3eaeaffb5f7ece175db76fd428247a8aeca839a094f19681a`;
- Git-control before/after:
  `af75bc6a0a2218d7c9dcdbd7ba0becc896286443357ad577a0298bfb053e173b`;
- independent status/diff before and after were empty; the protected
  instruction digest was unchanged; only fixture-local derived paths changed;
- all authority flags remained false, and no restore or staging occurred.

The fixture was local and synthetic. No external target was scanned or changed,
and no machine-local path is persisted here. Linux remains portability-fixture
evidence only.

## Post-Finding Caller-Owned Provenance Requalification

After the immutable diff review identified that launcher-only identity did not
cover imported package code, the adapter was changed to require caller-owned
accepted entry, interpreter, and complete package-tree digests before invoking
the CLI. Contained relative package-file symlinks are bound by link target and
target bytes; escaping, absolute, directory, or special-file targets fail
closed. Qualification and every later use rehash the complete package tree.

The installed macOS arm64 GitNexus `1.6.9` runtime was requalified with the new
production path. Machine-local paths were supplied only through the runtime
control plane and are omitted here.

- resolved CLI entry SHA-256:
  `233ece3066020a9098aa7fa448e04beff8452169497248cb1e5c316e508bfbbc`;
- bound Node runtime SHA-256:
  `2e3f1286a7eb3736346ed1803e458a0ff909e2b2d5bc746144dcb76970e9b99d`;
- complete package-tree SHA-256:
  `feecb1748b8fbd24dc54921269e815a65725d808269152283ffc459604f6b603`;
- caller-owned provenance digest:
  `913250fb63f63c94839c5027fdab7306c8685d3f4896e046ee06126c2a49dd42`;
- historical pre-version-bump qualification fingerprint:
  `78572c8674046e93fd4a2271e34764c451ad8be86d51bb5a0dc1e3c02116319d`;
- current `gitnexus-v2c-a/2` qualification fingerprint:
  `eed36a35ea944bf494f788212ce01a1b401d8e5a6a7a095cbbd67bebb63faa2d`;
- CLI and Node policies: explicit final-symlink opt-in with resolved targets;
- exact required flags remained present, including `--index-only`,
  `--skip-agents-md`, `--skip-skills`, `--branch`, and `--name`.

The requalified controller then ran one new local isolated fixture refresh with
a clean direct Git worktree, pre-existing local exclude, fresh empty local home,
separate lock directory, explicit native Git, and exact expected HEAD. The
operation remained bound runtime plus bound entry and
`analyze --index-only --name <isolated-unique-alias> <canonical-fixture-root>`.

- fixture HEAD: `b88bf209f664e35b925c588bac9767bd3c98dcf5`;
- result: `refreshed / qualified-index-adoptable`;
- refresh receipt:
  `2c26daa0fa03e0d95e7f8cff8fcd4a092b3618c3f453588b8d31c4ab7a78626b`;
- tracked-state before/after:
  `b5da48baae5894917fbd2ab4e424aa039c6bbd794059d2bdada89795acd9744c`;
- complete-status before/after:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- protected-state before/after:
  `96b2a061150f78f36d6f79b9df63aebb51b7286faf4cc2146ecf40e4badf7605`;
- worktree-state before/after:
  `3fdc01e59e7e4fa098bdd9e17171490eb5c927394de604402dc02aa78f9b5651`;
- Git-control before/after:
  `b19892fd23194abb7ab9b6b3d3535bf345666390205f881c7bcfd36c6a870226`;
- all mutation, external-write, gate, completion, automatic-refresh,
  repository-restore, and repository-stage authority flags remained false.

The tracked status and diff remained empty. Only fixture-local derived index
and isolated runtime state changed. No external target was accessed or changed,
and no machine-local path is persisted in this receipt. Linux remains
portability-fixture evidence only.

## Final Post-Scan Controller Requalification

After the isolated-home lifecycle and final review fixes, the complete current
controller was qualified again on macOS arm64. This current-session
qualification detected Node runtime byte drift from the historical evidence,
so the old runtime fingerprint was not reused. Caller-owned local measurements
were regenerated and the full GitNexus `1.6.9` version/flag/package conformance
path was rerun. Machine-local paths remain outside this receipt.

- resolved CLI entry SHA-256:
  `233ece3066020a9098aa7fa448e04beff8452169497248cb1e5c316e508bfbbc`;
- bound Node runtime SHA-256:
  `4255a388254ca4319e2f95f1da375d5deaddf25baf9c7c85070b67f9543b15d0`;
- complete package-tree SHA-256:
  `feecb1748b8fbd24dc54921269e815a65725d808269152283ffc459604f6b603`;
- caller-owned provenance digest:
  `6ef47281b9d31fa4e299f076583f8c23830c672e2adecef892158acd9e9dab92`;
- qualification fingerprint:
  `86c6ec65b0b207a591759b35650acd914a812139327b9efe5933983b04d6029e`;
- GitNexus policy: explicitly allowed single final symlink; Node policy:
  explicit canonical regular file;
- exact version `1.6.9` and required `--index-only`, `--skip-agents-md`,
  `--skip-skills`, `--branch`, and `--name` capabilities were observed.

The current production controller then performed one new synthetic local
refresh. The exact child operation remained the structured argv equivalent of
`analyze --index-only --name <isolated-unique-alias>
<canonical-fixture-root>` with a fresh empty home, separate lock directory,
offline extension policy, explicit native Git, clean direct worktree, local
exclude protection, and exact expected HEAD.

- fixture HEAD and indexed revision:
  `0942e0c6b28022b2568aa0b0a1486a74286a9854`;
- result: `refreshed / qualified-index-adoptable`;
- refresh receipt:
  `3a15f4f71f6e70e867f8844eb82dddf815a52c21e87d225552604cdb9009ad78`;
- tracked-state before/after:
  `2d7583ae11355d872dcae576f6c150bd17f3dff6716df2597c4c9758a5de216b`;
- complete-status before/after:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- protected-state before/after:
  `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`;
- complete worktree-state before/after:
  `f1484f1a1a1a35e05171bac2ed08d4f205f6715efa9457c226ba6d94a8846558`;
- Git-control before/after:
  `1f268340987dbede2330ddbd311cd0d97bd28b77f3d036cd2afc3c14e38c6bdb`;
- metadata schema/indexed file hashes: `5` / `2`;
- all mutation, external-write, gate, completion, automatic-refresh,
  repository-restore, and repository-stage authority flags remained false.

Independent postflight showed unchanged tracked file digests, empty tracked and
staged diffs, and only the expected ignored derived index plus isolated local
registry/home state. No external target was accessed or changed. Linux remains
portability-fixture evidence only.

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
