"""One-shot stdio bridge to runtime-owned native GitHub connector callbacks.

No network/credentials/shell. Each response is bounded, correlated and explicit.
Only the runtime dispatcher can perform an authorized platform operation.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import binascii
import json
import os
from pathlib import Path
import select
import sys
import time

import pr_text_update as core

WIRE_LIMIT = 16 * 1024
# macOS PC_MAX_CANON/PC_MAX_INPUT are 1024 on the inspected PTY. Keep each
# ASCII frame (including its header/newline) below that bound without termios edits.
LINE_LIMIT = 768
OUTPUT_LIMIT = 64 * 1024
WAIT_SECONDS = 45


class Wire:
    def __init__(self, source=None, sink=None):
        self.source = sys.stdin if source is None else source
        self.sink = sys.stdout if sink is None else sink
        self.sequence = 0
        self.output_bytes = 0
        self.pending = b""

    def emit(self, marker, value):
        line = marker + " " + core.canonical(value) + "\n"
        size = len(line.encode("utf-8"))
        if size > WIRE_LIMIT or self.output_bytes + size > OUTPUT_LIMIT:
            raise core.Blocked("INPUT_SIZE_OR_TYPE")
        self.output_bytes += size
        self.sink.write(line)
        self.sink.flush()

    def receive(self, sequence):
        encoded = ""
        chunk_index = 0
        deadline = time.monotonic() + WAIT_SECONDS
        while True:
            while b"\n" not in self.pending:
                remaining = deadline - time.monotonic()
                if (len(self.pending) > LINE_LIMIT or remaining <= 0
                        or not select.select([self.source], [], [], remaining)[0]):
                    raise core.Blocked("INVALID_JSON")
                chunk = os.read(self.source.fileno(), LINE_LIMIT)
                if not chunk:
                    raise core.Blocked("INVALID_JSON")
                self.pending += chunk
            raw_line, self.pending = self.pending.split(b"\n", 1)
            if len(raw_line) + 1 > LINE_LIMIT:
                raise core.Blocked("INVALID_JSON")
            try:
                line = raw_line.decode("ascii")
            except UnicodeError:
                raise core.Blocked("INVALID_JSON") from None
            if line == f"I22_END {sequence} {chunk_index}":
                break
            prefix = f"I22_DATA {sequence} {chunk_index} "
            if not line.startswith(prefix):
                raise core.Blocked("INVALID_JSON")
            encoded += line[len(prefix):]
            chunk_index += 1
            if len(encoded) > 4 * ((WIRE_LIMIT + 2) // 3):
                raise core.Blocked("INPUT_SIZE_OR_TYPE")
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error):
            raise core.Blocked("INVALID_JSON") from None
        if len(decoded) > WIRE_LIMIT:
            raise core.Blocked("INPUT_SIZE_OR_TYPE")
        return core.strict_json(decoded)

    async def call(self, kind, arguments):
        self.sequence += 1
        sequence = self.sequence
        self.emit("I22_REQUEST", {"sequence": sequence, "kind": kind, "arguments": arguments})
        response = self.receive(sequence)
        if (not isinstance(response, dict)
                or set(response) != {"sequence", "kind", "ok", "value"}
                or type(response["sequence"]) is not int
                or response["sequence"] != sequence or response["kind"] != kind
                or type(response["ok"]) is not bool or not response["ok"]):
            raise core.Blocked("INVALID_JSON")
        return response["value"]


async def run(packet, wire):
    if not isinstance(packet, dict) or set(packet) != {"operation", "inspection", "proposed", "attempt_phase"}:
        raise core.Blocked("UNSUPPORTED_FIELDS")
    value = packet["inspection"]
    if not isinstance(value, dict) or set(value) != {"request_json", "baseline_json", "inspection_reference", "binding"}:
        raise core.Blocked("UNSUPPORTED_FIELDS")
    inspected = core.Inspected(**value)
    if packet["attempt_phase"] not in {"NOT_ATTEMPTED", "PREPARING", "UNKNOWN", "VERIFIED"}:
        raise core.Blocked("INVALID_VALUE")

    async def read(target):
        return core.normalize_rest_pull(await wire.call("read", target))

    async def update(arguments):
        return (await wire.call("update", arguments)) is True

    async def checkpoint(record):
        if (await wire.call("checkpoint", record)) is not True:
            raise core.Blocked("INVALID_VALUE")

    if packet["operation"] == "reconcile":
        return await core.reconcile(inspected, read=read)
    if packet["operation"] != "publish":
        raise core.Blocked("UNSUPPORTED_FIELDS")
    return await core.publish(inspected, packet["proposed"], read=read, update=update,
                              checkpoint=checkpoint, attempt=core.Attempt(packet["attempt_phase"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    wire = Wire()
    try:
        with args.input.open("rb") as stream:
            packet = core.strict_json(stream.read(core.MAX_INPUT_BYTES + 1))
        outcome = asyncio.run(run(packet, wire))
    except Exception:
        outcome = core.Outcome("BLOCKED", "BRIDGE_INPUT_OR_PROTOCOL_FAILED")
    wire.emit("I22_RESULT", {"phase": outcome.phase, "code": outcome.code})
    return 0 if outcome.phase in {"VERIFIED", "OBSERVED"} else 2


if __name__ == "__main__":
    sys.exit(main())
