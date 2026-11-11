#!/usr/bin/env python3
"""Offline App Server double. State/log paths must be test-owned temporary files."""
import copy
import json
import os
import pathlib
import subprocess
import sys
import time

if "--version" in sys.argv:
    print("codex-cli 0.167.0")
    raise SystemExit(0)

store = pathlib.Path(os.environ["FAKE_APP_SERVER_STORE"])
state = json.loads(store.read_text()) if store.exists() else {"threads": {}, "calls": []}
case = os.environ.get("FAKE_APP_SERVER_CASE", "normal")
if "mcp" in sys.argv:
    if case == "malformed_mcp":
        print("not-json")
    elif case in {"inherited_mcp", "override_ignored", "mcp_bad_name"}:
        name = "local.tools" if case == "mcp_bad_name" else "local-tools"
        override = "mcp_servers." + name + ".enabled=false"
        print(json.dumps([{"name": name, "enabled": override not in sys.argv or case == "override_ignored"}]))
    else:
        print("[]")
    raise SystemExit(0)


def emit(value):
    print(json.dumps(value), flush=True)


def save():
    store.write_text(json.dumps(state))


state["server_argv"] = sys.argv[1:]
for line in sys.stdin:
    request = json.loads(line)
    method, params, serial = request.get("method"), request.get("params", {}), request.get("id")
    if method is None:
        continue
    state["calls"].append({"method": method, "params": params})
    save()
    if method == "initialized":
        continue
    result = {}
    if method == "initialize":
        result = {"platformFamily": "unix", "platformOs": "fixture"}
    elif method == "mcpServerStatus/list":
        result = {"data": [{"name": "unexpected"}] if case == "inventory_tools" else [], "nextCursor": "more" if case == "inventory_cursor" else None}
        if case in {"inventory_disabled", "inventory_loading"}:
            result["data"] = [{"name": "local-tools", "runtimeStatus": "disabled" if case == "inventory_disabled" else "loading", "tools": {}, "resources": [], "resourceTemplates": [], "toolsError": None}]
    elif method == "thread/read":
        result = {"thread": state["threads"][params["threadId"]]}
        if case == "readback_wrong" and state["threads"][params["threadId"]]["turns"]:
            result = copy.deepcopy(result)
            result["thread"]["id"] = "wrong_readback"
    elif method in {"thread/start", "thread/resume", "thread/fork"}:
        if case == "writer":
            emit({"id": serial, "error": {"code": -32600, "message": "thread already has an active writer"}})
            continue
        if method == "thread/resume":
            tid = params["threadId"]
        else:
            tid = "thread_" + str(len(state["threads"]) + 1)
            history = copy.deepcopy(state["threads"][params["threadId"]]["turns"]) if method == "thread/fork" else []
            state["threads"][tid] = {"id": tid, "cwd": params["cwd"], "projectId": None, "status": {"type": "idle"}, "turns": history}
            if method == "thread/fork":
                state["threads"][tid]["forkedFromId"] = params["threadId"]
        save()
        result = {"thread": copy.deepcopy(state["threads"][tid]), "sandbox": {"type": "readOnly" if params["sandbox"] == "read-only" else "workspaceWrite"}}
        if case == "bad_cwd":
            result["thread"]["cwd"] = "/wrong-target"
        if case == "bad_sandbox":
            result["sandbox"]["type"] = "dangerFullAccess"
        if case == "fork_source_wrong" and method == "thread/fork":
            result["thread"]["forkedFromId"] = "other_source"
    elif method == "thread/turns/list":
        turns = state["threads"][params["threadId"]]["turns"]
        result = {"data": list(reversed(turns))[:params.get("limit", 1)], "nextCursor": None}
    elif method == "turn/start":
        if case == "early_exit":
            raise SystemExit(1)
        if case == "malformed":
            print("not-json", flush=True)
            continue
        if case == "oversized":
            print("x" * (1024 * 1024 + 1), flush=True)
            continue
        if case == "timeout":
            time.sleep(10)
            continue
        if case == "approval":
            emit({"id": 800, "method": "item/commandExecution/requestApproval", "params": {}})
            continue
        tid = params["threadId"]
        prompt = params["input"][0]["text"]
        turn = {"id": "turn_" + str(len(state["threads"][tid]["turns"]) + 1), "status": "failed" if case == "failed_turn" else "completed", "error": None, "items": [{"type": "agentMessage", "text": "fixture result"}]}
        if "write-fixture" in prompt and params["sandboxPolicy"]["type"] == "workspaceWrite":
            pathlib.Path(params["cwd"], "result.txt").write_text("intended fixture result\n")
        state["threads"][tid]["turns"].append(turn)
        save()
        completion = {"method": "turn/completed", "params": {"threadId": "other_thread" if case == "wrong_completion" else tid, "turn": turn}}
        if case == "event_before_ack":
            emit(completion)
        emit({"id": serial, "result": {"turn": {"id": turn["id"], "status": "inProgress", "error": None}}})
        if case != "event_before_ack":
            emit(completion)
        continue
    elif method == "turn/interrupt":
        pass
    else:
        emit({"id": serial, "error": {"code": -32601, "message": "unsupported fixture method"}})
        continue
    emit({"id": serial + 1 if case == "wrong_response" else serial, "result": result})

if case == "held_pipe":
    # Test-owned, self-expiring child retains both output pipes after server EOF.
    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(12)"], stdin=subprocess.DEVNULL)
