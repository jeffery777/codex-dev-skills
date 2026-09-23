# Early sandbox denial returns a tool result but omits command_execution from codex exec --json

## Environment

- Codex CLI 0.156.0, macOS 26.6.2 arm64, `/bin/zsh` 5.9, login shell.
- CLI binary SHA-256: `6b42db4d33fd53516162bd76a0e2d07e0567287c44e036d4e4c06cb555a432f9`.
- Fresh `codex exec --ignore-user-config --ephemeral --json --sandbox read-only --model gpt-6-luna -c 'model_reasoning_effort="low"'`.
- Fixed working directory, shell, requested model/effort, and permissions; a unique synthetic marker per attempt. No sandbox relaxation.

## Reproduction

Ask the model to execute this exact command through the shell tool using `/bin/zsh`, `login=true`, and the fixed working directory:

```sh
cat <<'EOF'
R292_<unique>_HEREDOC
EOF
```

Then execute a separate control command:

```sh
printf '%s\n' 'R292_<unique>_AFTER'
```

Ask for each actual tool result and exit code. Capture unfiltered stdout JSONL, stderr, process exit code, and `--output-last-message` separately. Run the exact same command directly with `codex sandbox -P :read-only -C <same-cwd> /bin/zsh -lc <exact-command>`.

For this synthetic diagnostic only, enable targeted `RUST_LOG=warn,codex_core::unified_exec=trace,codex_sandboxing=debug,codex_otel.log_only=info,codex_otel.trace_safe=info`. The log-only tool-result record includes request arguments, call ID, result, and truncation status. It also appends account metadata: **do not publish raw stderr**. No HTTP/API body tracing is required.

## Expected

The read-only sandbox should continue denying the heredoc temporary-file write. The failed command should also produce a correlated command lifecycle item in JSONL, including its nonzero exit and error output. The request, failed tool response, public event stream, and final answer should agree.

## Actual

The nested `exec_command` diagnostic contains the exact requested heredoc bytes, `/bin/zsh`, `login=true`, and the same cwd. Its actual result is exit 1 with:

```text
zsh:1: can't create temp file for here document: operation not permitted
```

The diagnostic preview is not truncated. The outer code-mode result also contains this exit/output. Direct sandbox execution produces the same failure.

However, the complete seven-line stdout JSONL stream contains only the successful printf command's started/completed items. There is no heredoc command_execution item. The final answer correctly reports the heredoc tool failure. Every JSONL line parses, so this is not a local parser/filter dropping malformed input.

A second fresh run of the same heredoc with the same CLI binary, shell, cwd, model/effort, and read-only sandbox reproduced exit 1 with zero corresponding command items. No fixed-version result has been verified.

## Source investigation

In rust-v0.156.0, [process_manager.rs:530](https://github.com/openai/codex/blob/rust-v0.156.0/codex-rs/core/src/unified_exec/process_manager.rs#L530) returns on `open_session_with_sandbox` failure before [Begin is emitted at line 587](https://github.com/openai/codex/blob/rust-v0.156.0/codex-rs/core/src/unified_exec/process_manager.rs#L587). [exec_command.rs:448](https://github.com/openai/codex/blob/rust-v0.156.0/codex-rs/core/src/tools/handlers/unified_exec/exec_command.rs#L448) nevertheless converts SandboxDenied into an output/exit-bearing tool result, without emitting the missing command lifecycle item.

The same ordering exists in [rust-v0.155.1](https://github.com/openai/codex/blob/rust-v0.155.1/codex-rs/core/src/unified_exec/process_manager.rs#L503), although our fully instrumented reproduction used 0.156.0. We have not established reproducible-build attestation between tag source and the installed binary.

`--disable unified_exec` did not resolve the gap. The current [managed feature normalization](https://github.com/openai/codex/blob/rust-v0.156.0/codex-rs/core/src/config/managed_features.rs#L153) re-enables that backend; this was not a successful legacy-backend workaround.

## Impact and requested behavior

JSONL consumers can incorrectly infer that a command was never attempted or that a model invented a failure. This is an observability issue; the sandbox denial itself is expected and remains effective.

Please preserve a correlated failed command lifecycle item on early denial/startup-error paths, with regression coverage for direct and code-mode calls and JSONL export, without duplicate or unfinished items. This report does not request broader sandbox permissions.

The diagnostic format is version-specific and is not a complete structured audit API. This reproduction uses diagnostic request/result evidence to distinguish a missing lifecycle event from a command that was never attempted.

All examples are independently synthetic. No private source code, private URLs, credentials, or raw runtime logs are attached.
