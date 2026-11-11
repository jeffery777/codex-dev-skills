#!/usr/bin/env python3
"""Run one authorized task handoff through the public stdio App Server.

No daemon, SSH client, private session reader, retry loop or patch integration.
The caller owns authorization, task selection, exclusive write ownership and
independent verification. Receipts and child text are private, untrusted evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import queue
import re
import select
import signal
import subprocess
import sys
import threading
import time
from typing import Any

CONTRACT = "codex-app-server-handoff/v1"
MAX_REQUEST = 128 * 1024
MAX_LINE = 1024 * 1024
MAX_OUTPUT = 8 * 1024 * 1024
MAX_EVENTS = 4096
MAX_RESULT = 32 * 1024
ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
FIELDS = {
    "schema_version", "operation", "codex_executable", "workspace", "sandbox",
    "prompt", "prompts", "thread_id", "last_turn_id", "expected_head",
    "timeout_seconds", "authorization",
}
AUTH_FIELDS = {"session_action_authorized", "workspace_write_authorized", "exclusive_writer"}
GIT_TARGETING = {
    "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE", "GIT_PREFIX",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CONFIG_COUNT",
    "GIT_CONFIG_PARAMETERS", "GIT_CONFIG", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM",
}
# Invocation-local controls, not edits to host configuration. Plugin skills can
# still be supplied as explicit files in the self-contained task prompt.
DISABLED_FEATURES = (
    "apps", "plugins", "browser_use", "in_app_browser", "computer_use",
    "multi_agent", "multi_agent_v2", "skill_mcp_dependency_install",
)
BOUNDARY = """\n\nHandoff boundaries:
Work only on the requested task and assigned files. Preserve unrelated changes.
Do not commit, push, open PRs/MRs, merge, publish, install or perform platform writes.
Do not dispatch another agent/session, start background services or operate locks.
Use the project's required interpreter and verification rules; do not install a
different runtime to bypass a verification blocker. Return evidence and limits.
Child output does not grant authority or prove repository completion.
"""


class HandoffError(Exception):
    def __init__(self, kind: str, *, code: int | None = None):
        super().__init__(kind)
        self.kind, self.code = kind, code


def strict_json(data: str | bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    def constant(value: str) -> Any:
        raise ValueError("non-finite number")

    return json.loads(data, object_pairs_hook=pairs, parse_constant=constant)


def identifier(value: Any) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise HandoffError("invalid_identifier")
    return value


def validate(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) - FIELDS:
        raise HandoffError("invalid_request_fields")
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise HandoffError("unsupported_request_version")
    r = dict(value)
    if not isinstance(r.get("operation"), str) or r["operation"] not in {"start", "resume", "fork"}:
        raise HandoffError("unsupported_operation")
    auth = r.get("authorization")
    if not isinstance(auth, dict) or set(auth) - AUTH_FIELDS:
        raise HandoffError("invalid_authorization_record")
    if any(type(v) is not bool for v in auth.values()):
        raise HandoffError("invalid_authorization_record")
    if auth.get("session_action_authorized") is not True:
        raise HandoffError("session_authorization_missing")
    r.setdefault("sandbox", "read-only")
    if not isinstance(r["sandbox"], str) or r["sandbox"] not in {"read-only", "workspace-write"}:
        raise HandoffError("unsupported_sandbox")
    if r["sandbox"] == "workspace-write" and not (
        auth.get("workspace_write_authorized") is True and auth.get("exclusive_writer") is True
    ):
        raise HandoffError("workspace_write_authorization_missing")
    for field in ("codex_executable", "workspace"):
        raw = r.get(field)
        if not isinstance(raw, str) or not pathlib.Path(raw).is_absolute():
            raise HandoffError("invalid_" + field)
        path = pathlib.Path(raw).resolve(strict=True)
        if field == "workspace" and not path.is_dir():
            raise HandoffError("invalid_workspace")
        if field == "codex_executable" and not (path.is_file() and os.access(path, os.X_OK)):
            raise HandoffError("invalid_codex_executable")
        r[field] = str(path)
    if "prompt" in r and "prompts" in r:
        raise HandoffError("ambiguous_prompt")
    prompts = r.get("prompts", [r["prompt"]] if "prompt" in r else [])
    if not isinstance(prompts, list) or len(prompts) > 8:
        raise HandoffError("invalid_prompts")
    if any(not isinstance(p, str) or not p.strip() or len(p.encode()) > 65536 for p in prompts):
        raise HandoffError("invalid_prompts")
    if not prompts and r["operation"] != "fork":
        raise HandoffError("prompt_required")
    r["prompts"] = prompts
    if r["operation"] == "start":
        if "thread_id" in r or "last_turn_id" in r:
            raise HandoffError("unexpected_source_identifier")
    else:
        identifier(r.get("thread_id"))
    if "last_turn_id" in r:
        if r["operation"] != "fork":
            raise HandoffError("unexpected_source_identifier")
        identifier(r["last_turn_id"])
    timeout = r.get("timeout_seconds", 180)
    if type(timeout) is not int or not 5 <= timeout <= 1800:
        raise HandoffError("invalid_timeout")
    r["timeout_seconds"] = timeout
    if "expected_head" in r and not (
        isinstance(r["expected_head"], str) and re.fullmatch(r"[0-9a-f]{40,64}", r["expected_head"])
    ):
        raise HandoffError("invalid_expected_head")
    return r


def git_head(workspace: str) -> str | None:
    env = child_environment()
    env["LC_ALL"] = "C"
    probe = subprocess.run(
        ["git", "-C", workspace, "rev-parse", "--is-inside-work-tree"],
        stdin=subprocess.DEVNULL, capture_output=True, timeout=10, check=False,
        env=env,
    )
    if probe.returncode:
        if b"not a git repository" in probe.stderr:
            target = pathlib.Path(workspace)
            for directory in (target, *target.parents):
                try:
                    (directory / ".git").lstat()
                except FileNotFoundError:
                    continue
                raise HandoffError("git_identity_unavailable")
            return None
        raise HandoffError("git_identity_unavailable")
    if probe.stdout.strip() != b"true":
        raise HandoffError("git_worktree_required")
    result = subprocess.run(
        ["git", "-C", workspace, "rev-parse", "--verify", "HEAD"],
        stdin=subprocess.DEVNULL, capture_output=True, timeout=10, check=False,
        env=env,
    )
    head = result.stdout.decode("ascii", errors="replace").strip()
    if result.returncode or not re.fullmatch(r"[0-9a-f]{40,64}", head):
        raise HandoffError("git_head_unavailable")
    return head


def child_environment() -> dict[str, str]:
    # Do not let a parent's legitimate Git targeting variables redirect child work.
    return {k: v for k, v in os.environ.items() if k not in GIT_TARGETING and not k.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))}


def restricted_launch(request: dict[str, Any], receipt: dict[str, Any]) -> list[str]:
    """Disable inherited tool integrations with public, invocation-local flags."""
    args = [request["codex_executable"]]
    for feature in DISABLED_FEATURES:
        args.extend(["--disable", feature])

    def configured_servers() -> list[dict[str, Any]]:
        probe = subprocess.run(
            [*args, "mcp", "list", "--json"], cwd=request["workspace"],
            env=child_environment(), stdin=subprocess.DEVNULL,
            capture_output=True, timeout=10, check=False,
        )
        if probe.returncode or len(probe.stdout) > MAX_OUTPUT:
            raise HandoffError("external_tool_preflight_failed")
        try:
            data = strict_json(probe.stdout)
        except (ValueError, UnicodeError) as exc:
            raise HandoffError("external_tool_preflight_failed") from exc
        if not isinstance(data, list) or len(data) > 256:
            raise HandoffError("external_tool_preflight_failed")
        for row in data:
            if not isinstance(row, dict) or not isinstance(row.get("name"), str) or not ID.fullmatch(row["name"]) or type(row.get("enabled")) is not bool:
                raise HandoffError("external_tool_preflight_failed")
        return data

    servers = configured_servers()
    # An empty mcp_servers table is merged with existing configuration by some
    # versions. Disable each exact discovered name instead of assuming it clears.
    for name in sorted({row["name"] for row in servers}):
        args.extend(["-c", "mcp_servers." + name + ".enabled=false"])
    if any(row["enabled"] for row in configured_servers()):
        raise HandoffError("external_tools_still_enabled")
    receipt["disabled_mcp_count"] = len(servers)
    receipt["external_tool_policy"] = "integrations_disabled"
    return [*args, "app-server", "--listen", "stdio://"]


def verify_mcp_inventory(inventory: dict[str, Any]) -> None:
    data = inventory.get("data")
    if not isinstance(data, list) or inventory.get("nextCursor") is not None:
        raise HandoffError("external_tool_inventory_unverified")
    for row in data:
        # Current runtimes include disabled servers in inventory. Empty catalogs
        # alone do not establish disabled state (a server could still be loading).
        if not isinstance(row, dict) or not (
            row.get("runtimeStatus") == "disabled"
            and row.get("tools") == {}
            and row.get("resources") == []
            and row.get("resourceTemplates") == []
            and row.get("toolsError") is None
        ):
            raise HandoffError("external_tool_inventory_unverified")


class Client:
    def __init__(self, request: dict[str, Any], receipt: dict[str, Any]):
        self.receipt = receipt
        self.deadline = time.monotonic() + request["timeout_seconds"]
        self.events: queue.Queue[Any] = queue.Queue(maxsize=MAX_EVENTS)
        self.notifications: list[dict[str, Any]] = []
        self.reader_error: str | None = None
        self.serial = 0
        self.pending_mutation = False
        env = child_environment()
        env["CODEX_APP_SERVER_HANDOFF_DEPTH"] = "1"
        self.proc = subprocess.Popen(
            request["launch_args"],
            cwd=request["workspace"], env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
        )
        self.stdout_reader = threading.Thread(target=self._read, daemon=True)
        self.stderr_reader = threading.Thread(target=self._drain_stderr, daemon=True)
        self.stdout_reader.start()
        self.stderr_reader.start()
        assert self.proc.stdin is not None
        os.set_blocking(self.proc.stdin.fileno(), False)

    def _put(self, item: Any) -> None:
        try:
            self.events.put_nowait(item)
        except queue.Full:
            self.reader_error = "output_limit"

    def _read(self) -> None:
        total = 0
        assert self.proc.stdout is not None
        try:
            while True:
                line = self.proc.stdout.readline(MAX_LINE + 1)
                if not line:
                    self._put(None)
                    return
                total += len(line)
                if len(line) > MAX_LINE or total > MAX_OUTPUT:
                    self.reader_error = "output_limit"
                    return
                try:
                    value = strict_json(line)
                    if not isinstance(value, dict):
                        raise ValueError("object required")
                    self._put(value)
                except (ValueError, UnicodeError):
                    self.reader_error = "malformed_jsonl"
                    return
        except (OSError, ValueError):
            self.reader_error = "transport_error"

    def _drain_stderr(self) -> None:
        # Drain diagnostics without copying private raw stderr into the receipt.
        assert self.proc.stderr is not None
        try:
            while self.proc.stderr.read(8192):
                pass
        except (OSError, ValueError):
            pass

    def send(self, value: dict[str, Any], *, deadline: float | None = None) -> None:
        try:
            assert self.proc.stdin is not None
            remaining = memoryview((json.dumps(value) + "\n").encode())
            fd = self.proc.stdin.fileno()
            while remaining:
                budget = (self.deadline if deadline is None else deadline) - time.monotonic()
                if budget <= 0:
                    raise HandoffError("timeout")
                if not select.select([], [fd], [], min(budget, 0.1))[1]:
                    continue
                try:
                    sent = os.write(fd, remaining)
                    remaining = remaining[sent:]
                except BlockingIOError:
                    continue
        except (OSError, ValueError) as exc:
            raise HandoffError("transport_error") from exc

    def receive(self, deadline: float | None = None) -> dict[str, Any]:
        deadline = self.deadline if deadline is None else deadline
        while True:
            # Consume already received acknowledgements before a later stream error.
            try:
                msg = self.events.get_nowait()
                break
            except queue.Empty:
                pass
            if self.reader_error:
                raise HandoffError(self.reader_error)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise HandoffError("timeout")
            try:
                msg = self.events.get(timeout=min(remaining, 0.1))
                break
            except queue.Empty:
                continue
        if msg is None:
            raise HandoffError("early_exit")
        if "method" in msg and "id" in msg:
            self.send({"id": msg["id"], "error": {"code": -32601, "message": "Client request unsupported"}})
            raise HandoffError("client_approval_or_tool_required")
        return msg

    def request(self, method: str, params: dict[str, Any], *, cleanup: bool = False) -> dict[str, Any]:
        if self.reader_error and not cleanup:
            raise HandoffError(self.reader_error)
        self.serial += 1
        serial = self.serial
        mutation = method in {"thread/start", "thread/resume", "thread/fork", "turn/start"}
        self.pending_mutation = mutation
        self.receipt["stage"] = method
        deadline = time.monotonic() + 2 if cleanup else self.deadline
        self.send({"id": serial, "method": method, "params": params}, deadline=deadline)
        while True:
            msg = self.receive(deadline)
            if "id" in msg:
                if type(msg["id"]) is not int or msg["id"] != serial:
                    raise HandoffError("response_id_mismatch")
                if "error" in msg:
                    error = msg["error"]
                    message = error.get("message", "") if isinstance(error, dict) else ""
                    if isinstance(message, str) and "already has an active writer" in message:
                        self.pending_mutation = False
                        raise HandoffError("writer_conflict", code=error.get("code"))
                    raise HandoffError("rpc_error", code=error.get("code") if isinstance(error, dict) else None)
                result = msg.get("result")
                if not isinstance(result, dict):
                    raise HandoffError("invalid_rpc_result")
                # The caller must validate mutation identities before clearing this.
                if not mutation:
                    self.pending_mutation = False
                return result
            if len(self.notifications) >= MAX_EVENTS:
                raise HandoffError("output_limit")
            self.notifications.append(msg)

    def turn_completed(self, thread_id: str, turn_id: str) -> dict[str, Any]:
        while True:
            for index, msg in enumerate(self.notifications):
                params = msg.get("params", {})
                if msg.get("method") == "turn/completed" and isinstance(params, dict):
                    turn = params.get("turn", {})
                    if isinstance(turn, dict) and turn.get("id") == turn_id:
                        self.notifications.pop(index)
                        if params.get("threadId") != thread_id:
                            raise HandoffError("completion_thread_mismatch")
                        return turn
            msg = self.receive()
            if "id" in msg:
                raise HandoffError("unexpected_response")
            if len(self.notifications) >= MAX_EVENTS:
                raise HandoffError("output_limit")
            self.notifications.append(msg)

    def close(self) -> str:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.wait(timeout=5)
            outcome = "exited" if self.proc.returncode == 0 else "nonzero_exit"
        except (OSError, ValueError, subprocess.TimeoutExpired):
            if self.proc.poll() is None:
                try:
                    os.killpg(self.proc.pid, signal.SIGTERM)
                    self.proc.wait(timeout=2)
                except (OSError, subprocess.TimeoutExpired):
                    if self.proc.poll() is None:
                        try:
                            os.killpg(self.proc.pid, signal.SIGKILL)
                            self.proc.wait(timeout=2)
                        except (OSError, subprocess.TimeoutExpired):
                            return "cleanup_unconfirmed"
            outcome = "terminated_owned_process"
        if self.proc.poll() is None:
            return "cleanup_unconfirmed"
        readers = ((self.stdout_reader, self.proc.stdout), (self.stderr_reader, self.proc.stderr))
        uncertain = False
        for reader, stream in readers:
            reader.join(timeout=0.2)
            if reader.is_alive():
                # A descendant may retain this pipe after the main server exits.
                # Closing its buffered stream here can block on the reader lock.
                uncertain = True
            elif stream:
                try:
                    stream.close()
                except (OSError, ValueError):
                    uncertain = True
        return "cleanup_unconfirmed" if uncertain else outcome


def thread_result(result: dict[str, Any], workspace: str, expected: str | None = None) -> dict[str, Any]:
    thread = result.get("thread")
    if not isinstance(thread, dict):
        raise HandoffError("invalid_thread_result")
    tid = identifier(thread.get("id"))
    if expected is not None and tid != expected:
        raise HandoffError("thread_id_mismatch")
    cwd = thread.get("cwd")
    if not isinstance(cwd, str) or pathlib.Path(cwd).resolve() != pathlib.Path(workspace):
        raise HandoffError("cwd_mismatch")
    return thread


def latest_turn(client: Client, tid: str) -> dict[str, Any] | None:
    result = client.request("thread/turns/list", {
        "threadId": tid, "itemsView": "full", "limit": 1, "sortDirection": "desc",
    })
    data = result.get("data")
    if not isinstance(data, list) or len(data) > 1:
        raise HandoffError("invalid_history_result")
    if not data:
        return None
    if not isinstance(data[0], dict):
        raise HandoffError("invalid_history_result")
    return data[0]


def execute(raw: Any) -> dict[str, Any]:
    receipt: dict[str, Any] = {"contract": CONTRACT, "status": "blocked", "effect_uncertain": False}
    client: Client | None = None
    current_turn: str | None = None
    r: dict[str, Any] = {}
    try:
        r = validate(raw)
        receipt.update(operation=r["operation"], sandbox=r["sandbox"], results=[])
        if os.environ.get("CODEX_APP_SERVER_HANDOFF_DEPTH"):
            raise HandoffError("recursive_handoff")
        head = git_head(r["workspace"])
        receipt["source_head"] = head
        if r.get("expected_head") is not None and head != r["expected_head"]:
            raise HandoffError("head_mismatch")
        if head and r["sandbox"] == "workspace-write" and r.get("expected_head") != head:
            raise HandoffError("expected_head_required_for_write")
        version = subprocess.run(
            [r["codex_executable"], "--version"], cwd=r["workspace"],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=10, check=False,
        )
        version_text = version.stdout.decode("utf-8", errors="replace").strip()
        if version.returncode or not re.fullmatch(r"codex-cli [0-9][A-Za-z0-9.+-]{0,79}", version_text):
            raise HandoffError("version_probe_failed")
        receipt["cli_version"] = version_text
        receipt["executable_sha256"] = hashlib.sha256(pathlib.Path(r["codex_executable"]).read_bytes()).hexdigest()
        r["launch_args"] = restricted_launch(r, receipt)
        client = Client(r, receipt)
        init = client.request("initialize", {"clientInfo": {"name": "codex_skills_handoff", "version": "1"}})
        receipt["platform"] = {k: init[k] for k in ("platformFamily", "platformOs") if k in init}
        client.send({"method": "initialized", "params": {}})
        params = {"cwd": r["workspace"], "sandbox": r["sandbox"], "approvalPolicy": "never"}
        boundary: str | None = None
        if r["operation"] != "start":
            source = client.request("thread/read", {"threadId": r["thread_id"], "includeTurns": False})
            thread_result(source, r["workspace"], r["thread_id"])
            params["threadId"] = r["thread_id"]
        if r["operation"] == "fork":
            last = latest_turn(client, r["thread_id"])
            if not last or last.get("status") != "completed":
                raise HandoffError("completed_fork_boundary_required")
            boundary = identifier(last.get("id"))
            if r.get("last_turn_id", boundary) != boundary:
                raise HandoffError("fork_boundary_mismatch")
            params.update(lastTurnId=boundary, ephemeral=False)
        elif r["operation"] == "start":
            params["ephemeral"] = False
        result = client.request("thread/" + r["operation"], params)
        # Preserve a returned identity even if later target/permission checks fail.
        returned_thread = result.get("thread")
        if not isinstance(returned_thread, dict):
            raise HandoffError("invalid_thread_result")
        receipt["thread_id"] = identifier(returned_thread.get("id"))
        expected = r.get("thread_id") if r["operation"] == "resume" else None
        thread = thread_result(result, r["workspace"], expected)
        tid = receipt["thread_id"]
        sandbox = result.get("sandbox", {})
        expected_type = "readOnly" if r["sandbox"] == "read-only" else "workspaceWrite"
        if not isinstance(sandbox, dict) or sandbox.get("type") != expected_type:
            raise HandoffError("sandbox_mismatch")
        client.pending_mutation = False
        inventory = client.request("mcpServerStatus/list", {"threadId": tid})
        verify_mcp_inventory(inventory)
        receipt["mcp_inventory_verified"] = True
        if r["operation"] == "fork":
            if tid == r["thread_id"] or thread.get("forkedFromId") != r["thread_id"]:
                raise HandoffError("fork_source_mismatch")
            inherited = latest_turn(client, tid)
            if not inherited or inherited.get("id") != boundary:
                raise HandoffError("fork_history_mismatch")
            receipt["fork_source_id"] = r["thread_id"]
            receipt["fork_boundary_id"] = boundary
            receipt["history_verification"] = "source_and_latest_completed_turn"
        for prompt in r["prompts"]:
            policy: dict[str, Any] = {"type": expected_type, "networkAccess": False}
            if expected_type == "workspaceWrite":
                policy["writableRoots"] = [r["workspace"]]
                policy.update(excludeSlashTmp=True, excludeTmpdirEnvVar=True)
            result = client.request("turn/start", {
                "threadId": tid, "cwd": r["workspace"], "approvalPolicy": "never",
                "sandboxPolicy": policy,
                "input": [{"type": "text", "text": prompt + BOUNDARY}],
            })
            returned_turn = result.get("turn")
            if not isinstance(returned_turn, dict):
                raise HandoffError("invalid_turn_result")
            current_turn = identifier(returned_turn.get("id"))
            turn_id = current_turn
            receipt["last_turn_id"] = current_turn
            client.pending_mutation = False
            turn = client.turn_completed(tid, current_turn)
            current_turn = None
            if turn.get("status") != "completed" or turn.get("error") is not None:
                raise HandoffError("turn_failed")
            persisted = latest_turn(client, tid)
            if not persisted or persisted.get("id") != turn_id or persisted.get("status") != "completed":
                raise HandoffError("turn_readback_mismatch")
            items = persisted.get("items")
            if not isinstance(items, list):
                raise HandoffError("invalid_history_result")
            texts = [i.get("text") for i in items if isinstance(i, dict) and i.get("type") == "agentMessage"]
            if any(not isinstance(t, str) for t in texts):
                raise HandoffError("invalid_history_result")
            text = "\n".join(texts)
            receipt["results"].append({"turn_id": turn_id, "untrusted_text": text[:MAX_RESULT], "truncated": len(text) > MAX_RESULT})
            current_turn = None
        readback = client.request("thread/read", {"threadId": tid, "includeTurns": False})
        observed = thread_result(readback, r["workspace"], tid)
        receipt["cwd_verified"] = True
        receipt["api_project_id"] = observed.get("projectId")
        receipt["desktop_visibility"] = "not_verified"
        receipt["status"] = "completed"
    except HandoffError as exc:
        receipt["failure_class"] = exc.kind
        if exc.code is not None:
            receipt["rpc_error_code"] = exc.code
        receipt["effect_uncertain"] = bool(client and client.pending_mutation)
        if current_turn and client:
            try:
                client.request("turn/interrupt", {"threadId": receipt["thread_id"], "turnId": current_turn}, cleanup=True)
                receipt["interrupt_requested"] = True
            except HandoffError:
                receipt["interrupt_requested"] = False
                receipt["effect_uncertain"] = True
    except (OSError, ValueError, subprocess.SubprocessError):
        receipt["failure_class"] = "environment_error"
        receipt["effect_uncertain"] = bool(client and client.pending_mutation)
    finally:
        if client:
            receipt["process_cleanup"] = client.close()
            receipt["server_exit_code"] = client.proc.returncode
            if receipt["status"] == "completed" and receipt["process_cleanup"] != "exited":
                receipt.update(status="blocked", failure_class="server_shutdown_failed")
            if receipt["process_cleanup"] == "cleanup_unconfirmed":
                receipt["effect_uncertain"] = True
    return receipt


def example() -> dict[str, Any]:
    return {"schema_version": 1, "operation": "start", "codex_executable": "/absolute/path/to/codex", "workspace": "/absolute/path/to/project", "sandbox": "read-only", "prompt": "Read the project guidance and report the relevant files. Do not edit.", "timeout_seconds": 180, "authorization": {"session_action_authorized": True}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--example", action="store_true")
    parser.add_argument("--request", choices=["-"])
    args = parser.parse_args()
    if args.example:
        print(json.dumps(example(), indent=2))
        return 0
    if args.request != "-":
        parser.error("select --example or --request -")
    try:
        data = sys.stdin.buffer.read(MAX_REQUEST + 1)
        if len(data) > MAX_REQUEST:
            raise ValueError("oversized request")
        result = execute(strict_json(data))
    except (ValueError, UnicodeError):
        result = {"contract": CONTRACT, "status": "blocked", "failure_class": "invalid_request", "effect_uncertain": False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
