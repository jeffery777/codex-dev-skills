"""Pipe and PTY contract tests; no GitHub mutation or credentials."""
import base64
import copy
from dataclasses import asdict
import importlib.util
import io
import json
import os
import pathlib
import pty
import select
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pr_text_update as core
import pr_text_native_bridge as bridge

BRIDGE = ROOT / "scripts" / "pr_text_native_bridge.py"


def raw_pull():
    return {
        "base": {"repo": {"full_name": "example/workflow-fixture", "id": 100},
                 "sha": "a" * 40, "ref": "main"},
        "head": {"repo": {"full_name": "example/workflow-fixture"},
                 "sha": "b" * 40, "ref": "fixture/issue-22"},
        "number": 22, "id": 200,
        "url": "https://api.github.com/repos/example/workflow-fixture/pulls/22",
        "html_url": "https://github.com/example/workflow-fixture/pull/22",
        "state": "open", "draft": True, "updated_at": "2026-11-02T00:00:00Z",
        "title": "Before", "body": "Public baseline.\n",
    }


def packet():
    proposed = {"repository": "example/workflow-fixture", "pr_number": 22,
                "title": "After", "body": "Public update.\n"}
    review = core.inspect(proposed, core.normalize_rest_pull(raw_pull()),
                          verdict="clear", inspection_reference="fixture-inspection")
    return {"operation": "publish", "inspection": asdict(review),
            "proposed": proposed, "attempt_phase": "NOT_ATTEMPTED"}


def frame(response):
    encoded = base64.b64encode(json.dumps(response, ensure_ascii=False).encode()).decode()
    chunks = [encoded[i:i+512] for i in range(0, len(encoded), 512)]
    sequence = response["sequence"]
    return "".join(f"I22_DATA {sequence} {i} {part}\n" for i, part in enumerate(chunks)) + f"I22_END {sequence} {len(chunks)}\n"


class Tests(unittest.TestCase):
    def run_bridge(self, input_packet=None, *, mode="pipe", fault=None, live_mutation=None):
        request = packet() if input_packet is None else input_packet
        live = raw_pull()
        if live_mutation:
            live_mutation(live)
        calls, transcript = [], []
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "input.json"
            path.write_text(json.dumps(request), encoding="utf-8")
            command = [sys.executable, "-B", "-u", str(BRIDGE), "--input", str(path)]
            master = None
            if mode == "pty":
                master, slave = pty.openpty()
                child = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=subprocess.PIPE)
                os.close(slave)
                read_fd = master
            else:
                child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                read_fd = child.stdout.fileno()
            pending = b""
            deadline = time.monotonic() + 8
            try:
                while True:
                    while b"\n" not in pending:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0 or not select.select([read_fd], [], [], remaining)[0]:
                            self.fail(f"bounded bridge did not finish: kinds={transcript}, buffered_bytes={len(pending)}, child_status={child.poll()}, prefix={pending[:80]!r}, suffix={pending[-80:]!r}")
                        try:
                            chunk = os.read(read_fd, 4096)
                        except OSError:
                            chunk = b""
                        if not chunk:
                            self.fail("bridge ended without result")
                        pending += chunk
                    line, pending = pending.split(b"\n", 1)
                    line = line.rstrip(b"\r").decode("utf-8")
                    if line.startswith("I22_RESULT "):
                        result = json.loads(line[len("I22_RESULT "):])
                        break
                    if not line.startswith("I22_REQUEST "):
                        # PTY echoes DATA/END; echoed replies are never requests.
                        continue
                    item = json.loads(line[len("I22_REQUEST "):])
                    transcript.append(item["kind"])
                    kind, args = item["kind"], item["arguments"]
                    response = {"sequence": item["sequence"], "kind": kind, "ok": True, "value": True}
                    if kind == "read":
                        response["value"] = copy.deepcopy(live)
                    elif kind == "checkpoint":
                        self.assertEqual(args["phase"], "UNKNOWN")
                    elif kind == "update":
                        self.assertEqual(set(args), {"repository_full_name", "pr_number", "title", "body"})
                        self.assertEqual(args["repository_full_name"], "example/workflow-fixture")
                        self.assertEqual(args["pr_number"], 22)
                        calls.append(args)
                        live.update(title=args["title"], body=args["body"])
                    else:
                        self.fail("unknown operation")
                    if fault:
                        fault(item, response)
                    data = frame(response).encode()
                    if master is not None:
                        # Drain PTY echo between bounded lines; do not bulk-write
                        # a large response into the terminal's finite input queue.
                        for part in data.splitlines(keepends=True):
                            offset = 0
                            while offset < len(part):
                                offset += os.write(master, part[offset:])
                            while select.select([master], [], [], 0.01)[0]:
                                pending += os.read(master, 4096)
                    else:
                        child.stdin.write(data)
                        child.stdin.flush()
                child.wait(timeout=2)
                return result, calls, transcript
            finally:
                if child.poll() is None:
                    child.terminate()
                    child.wait(timeout=2)
                if master is not None:
                    os.close(master)
                for stream in [child.stdin, child.stdout, child.stderr]:
                    if stream is not None:
                        stream.close()

    def test_pipe_exact_native_arguments_and_single_update(self):
        result, calls, transcript = self.run_bridge()
        self.assertEqual(result["phase"], "VERIFIED")
        self.assertEqual(len(calls), 1)
        self.assertEqual(transcript, ["read", "checkpoint", "update", "read"])

    def test_real_pty_echo_and_multiple_chunks_do_not_dispatch_twice(self):
        value = packet()
        value["proposed"]["body"] = "Public multibyte fixture. 測試文字。\n" * 100
        value["inspection"] = asdict(core.inspect(value["proposed"], core.normalize_rest_pull(raw_pull()),
                                                  verdict="clear", inspection_reference="larger-fixture"))
        result, calls, transcript = self.run_bridge(value, mode="pty")
        self.assertEqual(result["phase"], "VERIFIED")
        self.assertEqual(len(calls), 1)
        self.assertEqual(transcript, ["read", "checkpoint", "update", "read"])

    def test_stale_body_or_wrong_destination_emits_no_update(self):
        for key, val in [("body", "Unreviewed"), ("repository", "example/other"), ("pr_number", 23)]:
            value = packet()
            value["proposed"][key] = val
            result, calls, transcript = self.run_bridge(value)
            self.assertEqual(result["phase"], "BLOCKED")
            self.assertEqual(calls, [])
            self.assertEqual(transcript, [])

    def test_live_drift_stops_before_checkpoint_or_update(self):
        result, calls, transcript = self.run_bridge(live_mutation=lambda live: live.update(body="Third-party change"))
        self.assertEqual(result["phase"], "BLOCKED")
        self.assertEqual(calls, [])
        self.assertEqual(transcript, ["read"])

    def test_mismatched_sequence_or_kind_blocks_before_update(self):
        for key, val in [("sequence", 99), ("kind", "update")]:
            result, calls, _ = self.run_bridge(fault=lambda item, response: response.update({key: val}))
            self.assertEqual(result["phase"], "BLOCKED")
            self.assertEqual(calls, [])

    def test_checkpoint_denied_prevents_update(self):
        def deny(item, response):
            if item["kind"] == "checkpoint":
                response["ok"] = False
        result, calls, transcript = self.run_bridge(fault=deny)
        self.assertEqual(result["phase"], "BLOCKED")
        self.assertEqual(calls, [])
        self.assertEqual(transcript, ["read", "checkpoint"])

    def test_update_result_unknown_is_never_replayed(self):
        def lose_response(item, response):
            if item["kind"] == "update":
                response["ok"] = False
        result, calls, transcript = self.run_bridge(fault=lose_response)
        self.assertEqual(result["phase"], "UNKNOWN")
        self.assertEqual(len(calls), 1)
        self.assertEqual(transcript, ["read", "checkpoint", "update"])

    def test_unknown_attempt_cannot_start_another_update(self):
        value = packet()
        value["attempt_phase"] = "UNKNOWN"
        result, calls, transcript = self.run_bridge(value)
        self.assertEqual(result["phase"], "BLOCKED")
        self.assertEqual(calls, [])
        self.assertEqual(transcript, [])

    def test_reconciliation_has_only_read(self):
        value = packet()
        value["operation"] = "reconcile"
        value["attempt_phase"] = "UNKNOWN"
        result, calls, transcript = self.run_bridge(value)
        self.assertEqual(result["phase"], "UNKNOWN")
        self.assertEqual(calls, [])
        self.assertEqual(transcript, ["read"])


class FrameTests(unittest.TestCase):
    def receive(self, raw):
        read_fd, write_fd = os.pipe()
        try:
            os.write(write_fd, raw)
            os.close(write_fd)
            write_fd = None
            with os.fdopen(read_fd, "rb", buffering=0) as source:
                read_fd = None
                return bridge.Wire(source, io.StringIO()).receive(1)
        finally:
            if read_fd is not None:
                os.close(read_fd)
            if write_fd is not None:
                os.close(write_fd)

    def test_duplicate_missing_wrong_order_and_end_count_fail_closed(self):
        valid = frame({"sequence": 1, "kind": "read", "ok": True, "value": True}).encode()
        first, end = valid.splitlines(keepends=True)
        for data in [first + first + end, end, first.replace(b"1 0 ", b"1 1 ") + end,
                     first + b"I22_END 1 2\n", first + b"I22_END 2 1\n"]:
            with self.subTest(data=data[:25]):
                with self.assertRaises(core.Blocked):
                    self.receive(data)

    def test_invalid_base64_eof_and_line_limit_fail_closed(self):
        for data in [b"I22_DATA 1 0 !\nI22_END 1 1\n", b"I22_DATA 1 0 AAAA\n",
                     b"I22_DATA 1 0 " + b"A" * bridge.LINE_LIMIT + b"\n",
                     b"I22_DATA 1 0 \xff\nI22_END 1 1\n"]:
            with self.assertRaises(core.Blocked):
                self.receive(data)

    def test_wait_and_total_limits_are_enforced(self):
        with mock.patch.object(bridge, "WAIT_SECONDS", 0):
            with self.assertRaises(core.Blocked):
                self.receive(b"")
        with mock.patch.object(bridge, "WIRE_LIMIT", 8):
            with self.assertRaises(core.Blocked):
                self.receive(frame({"sequence": 1, "kind": "read", "ok": True, "value": True}).encode())
        wire = bridge.Wire(sink=io.StringIO())
        with mock.patch.object(bridge, "OUTPUT_LIMIT", 8):
            with self.assertRaises(core.Blocked):
                wire.emit("I22_REQUEST", {"sequence": 1})

    def test_frames_fit_declared_protocol_line_bound(self):
        # fpathconf may report a portable constant rather than the driver's
        # actual line capacity (Linux/glibc 255 versus canonical driver 4096).
        # Host capability is exercised by the separate real PTY roundtrip.
        data = frame({"sequence": 1, "kind": "read", "ok": True, "value": "x" * 4000})
        self.assertTrue(all(len(line.encode()) <= bridge.LINE_LIMIT
                            for line in data.splitlines(keepends=True)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
