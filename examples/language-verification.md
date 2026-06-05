# Language Verification Examples

Use these examples when Codex needs to choose the smallest relevant verification for a language-specific repository.

The commands below are examples, not universal requirements. Always read the target repo first and prefer its documented scripts, CI configuration, Makefile targets, or package manager commands.

## Selection Flow

1. Read repo instructions, current git state, changed files, package manifests, and test or CI configuration.
2. Identify the changed surface: docs-only, parser, API, CLI, package metadata, migration, or cross-module behavior.
3. Choose the smallest command that proves the changed surface.
4. Prefer focused tests before broad suites when the change is narrow.
5. Escalate to broader verification when the diff changes shared contracts, packaging, generated files, migrations, or release-sensitive behavior.
6. Report commands run, skipped checks, missing dependencies, and residual risk.
7. Stop before commit, push, release, deploy, merge, or external writes unless the user explicitly authorizes that step.

## Python

Read first:

- `pyproject.toml`
- `setup.cfg`
- `tox.ini`
- `noxfile.py`
- `.github/workflows/`

Focused examples:

```bash
pytest tests/test_parser.py
python -m pytest tests/test_parser.py::test_empty_config
ruff check src tests
mypy src
```

Use broader checks when packaging, shared API, or multiple modules changed:

```bash
pytest
tox
python -m build
```

If the repository does not define a tool, do not invent one. Report the missing command and choose the closest documented verification.

## Node Or TypeScript

Read first:

- `package.json`
- lockfile
- `tsconfig.json`
- test runner config
- `.github/workflows/`

Focused examples:

```bash
npm test -- parser.test.ts
npm run test -- --run parser
npm run typecheck
npm run lint
```

Use broader checks when package exports, build output, or shared types changed:

```bash
npm test
npm run build
npm pack --dry-run
```

Prefer the package manager already used by the repo, such as `npm`, `pnpm`, `yarn`, or `bun`.

## Go

Read first:

- `go.mod`
- `go.work`
- package paths touched by the diff
- CI configuration

Focused examples:

```bash
go test ./internal/parser
go test ./cmd/tool -run TestEmptyConfig
go vet ./internal/parser
```

Use broader checks when shared packages, public APIs, or module metadata changed:

```bash
go test ./...
go vet ./...
```

## Rust

Read first:

- `Cargo.toml`
- `Cargo.lock`
- workspace members
- `.cargo/config.toml`
- CI configuration

Focused examples:

```bash
cargo test -p parser
cargo test empty_config
cargo clippy -p parser --all-targets
```

Use broader checks when workspace contracts, features, or packaging changed:

```bash
cargo test --workspace
cargo clippy --workspace --all-targets
cargo package --allow-dirty --list
```

## Docs-Only Changes

For docs-only changes in any language repository, start with documentation validation and link or formatting checks when the repo defines them.

Examples:

```bash
git diff --check
markdownlint docs
vale docs
```

If no docs tooling exists, inspect links and referenced paths manually, then report that no repo-owned docs checker was found.

## Verification Report Shape

Report verification in a way another maintainer can rerun:

```text
Verification:
- `pytest tests/test_parser.py`: passed
- `git diff --check`: passed

Skipped:
- `tox`: skipped because the focused parser test covered the changed file and no packaging files changed.

Residual risk:
- Did not run integration tests; change was limited to parser validation.
```

When dependencies are missing, classify the failure instead of changing tools blindly. For example, distinguish missing package install, network access, unsupported runtime version, and an actual test failure.
