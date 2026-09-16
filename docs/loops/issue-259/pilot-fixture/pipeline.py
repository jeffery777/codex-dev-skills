"""Synthetic bundle builder and exporter."""
import json
import os
from pathlib import Path
import subprocess
import sys


def build(config, destination, strict=True):
    locator = config["locator"]
    if strict and not locator.startswith("bundle://"):
        raise ValueError("locator requires bundle://")
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "summary.txt").write_text("bundle complete\n")
    (destination / "payload.bin").write_bytes(b"\xff\x00\xfe")


def export(destination):
    return {p.name: p.read_text(encoding="utf-8") for p in destination.iterdir()}


def run(config_path, destination, runner=subprocess.run, dry_run=False):
    subprocess.run(["bundle-tool", "--version"], check=True, capture_output=True)
    config = json.loads(Path(config_path).read_text())
    if dry_run:
        return {"validated": True}
    runner([sys.executable, "producer.py", str(config_path), str(destination)], check=True)
    return export(Path(destination))


if __name__ == "__main__":
    if os.environ.get("BUNDLE_ROUTE") != "fixture-route":
        raise SystemExit("route unavailable")
    print(run(sys.argv[1], sys.argv[2], dry_run="--dry-run" in sys.argv[3:]))
