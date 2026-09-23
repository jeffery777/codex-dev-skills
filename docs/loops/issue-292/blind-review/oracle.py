#!/usr/bin/env python3
"""Execute real-PyYAML, controlled-subprocess oracles for blind fixtures."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import yaml

ROOT = Path(__import__('os').environ['CODEX_REVIEW_PILOT_ROOT']).resolve()

def run(fixture: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "review_target.py", *args], cwd=fixture, text=True, capture_output=True, check=False)

def assert_true(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)

def child() -> subprocess.Popen[str]:
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], text=True)

def retention_control(fixture: Path) -> None:
    namespace: dict[str, object] = {}
    exec((fixture / "retention.py").read_text(encoding="utf-8"), namespace)
    records = [
        {"id": "active-old", "state": "active", "completed_at": 0},
        {"id": "completed-old", "state": "completed", "completed_at": 0},
        {"id": "completed-new", "state": "completed", "completed_at": 95},
    ]
    kept = namespace["retained"](records, now=100, ttl_seconds=10, latest_n=1)
    assert_true({r["id"] for r in kept} == {"active-old", "completed-new"}, "retention control failed")

def maintenance_control(fixture: Path) -> None:
    namespace: dict[str, object] = {}
    exec((fixture / "maintenance.py").read_text(encoding="utf-8"), namespace)
    assert_true(namespace["maintenance_label"]("timeout while converting") == "timeout-message", "maintenance control failed")
    assert_true(namespace["maintenance_label"]("converted twice") == "duplicate-conversion-message", "maintenance control failed")

def malformed_control(fixture: Path, variant: str) -> None:
    malformed = fixture / "data" / "review-sentinel-malformed.yaml"
    try:
        yaml.safe_load(malformed.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        if variant == "v2":
            assert_true(isinstance(exc, yaml.parser.ParserError), "v2 seed did not raise ParserError")
    else:
        raise AssertionError("seed malformed YAML did not raise real YAMLError")
    result = run(fixture, "config", str(malformed))
    assert_true(result.returncode != 2 and "Traceback" in result.stderr, "malformed YAML did not escape controlled summary with traceback")
    assert_true("error:" not in result.stdout and "review-sentinel" in result.stderr, "malformed YAML sentinel/control summary check failed")
    if variant == "v2":
        assert_true("yaml.parser.ParserError" in result.stderr, "v2 ParserError did not escape ScannerError-only handler")

def normal_config(fixture: Path) -> None:
    result = run(fixture, "config", str(fixture / "data" / "normal.yaml"))
    assert_true(result.returncode == 0 and result.stdout.strip() == "ok: configuration", "normal configuration control failed")

def v1_lock(fixture: Path, owner: int) -> None:
    lock = fixture / "data" / "owner.lock"
    lock.write_text(f"{owner}\n", encoding="utf-8")
    result = run(fixture, "acquire", str(lock), str(owner))
    assert_true(result.returncode == 0 and lock.read_text(encoding="utf-8") == str(owner), "v1 did not overwrite live child owner as expected")

def v2_lock(fixture: Path, owner: int) -> None:
    lock = fixture / "data" / "owner.lock"
    first = run(fixture, "run", str(lock), str(owner))
    assert_true(first.returncode == 4 and lock.exists(), "v2 did not retain newline-normalization lock")
    second = run(fixture, "run", str(lock), str(owner))
    assert_true(second.returncode == 3 and "active owner" in second.stdout, "v2 retained lock did not block next run")

def main() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert_true(set(manifest["variants"]) == {"v1", "v2"}, "manifest variants mismatch")
    for name in ("v1", "v2"):
        fixture = ROOT / "fixtures" / name
        normal_config(fixture)
        malformed_control(fixture, name)
        retention_control(fixture)
        maintenance_control(fixture)
        sleeper = child()
        try:
            assert_true(sleeper.poll() is None, "child owner exited early")
            (v1_lock if name == "v1" else v2_lock)(fixture, sleeper.pid)
        finally:
            sleeper.terminate()
            sleeper.wait(timeout=5)
            (fixture / "data" / "owner.lock").unlink(missing_ok=True)
        print(f"{name}: oracle passed")

if __name__ == "__main__":
    main()
