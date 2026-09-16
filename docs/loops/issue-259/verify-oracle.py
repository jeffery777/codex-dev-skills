"""Verify the synthetic oracle; run with the repository's project-python."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import patch

FIXTURE = Path(__file__).resolve().parent / "pilot-fixture"
sys.path.insert(0, str(FIXTURE))
import pipeline  # noqa: E402


def verify():
    results = {}
    with tempfile.TemporaryDirectory(prefix="integration-oracle-") as temporary:
        root = Path(temporary)
        with patch.dict(os.environ, {"PATH": temporary}):
            try:
                pipeline.run(FIXTURE / "input.json", root / "out", runner=lambda *a, **k: None)
            except FileNotFoundError:
                results["F1"] = "version probe bypasses injected runner with isolated PATH"
        env = dict(os.environ, PYTHON=sys.executable, BUNDLE_ROUTE="fixture-route")
        launch = subprocess.run(["/bin/sh", "launch.sh", str(root / "launch")],
                                cwd=FIXTURE, env=env, capture_output=True, text=True)
        assert launch.returncode == 1 and launch.stderr.strip() == "route unavailable"
        assert not (root / "launch").exists()
        results["F2"] = "startup clears route before bundle work"
        with patch("pipeline.subprocess.run"):
            assert pipeline.run(FIXTURE / "input.json", root / "dry", dry_run=True) == {"validated": True}
        try:
            pipeline.build(json.loads((FIXTURE / "input.json").read_text()), root / "strict")
        except ValueError as exc:
            assert str(exc) == "locator requires bundle://"
            results["F3"] = "dry-run accepts input rejected by strict builder"
        pipeline.build({"locator": "bundle://sample"}, root / "valid")
        try:
            pipeline.export(root / "valid")
        except UnicodeDecodeError:
            assert sorted(p.name for p in (root / "valid").iterdir()) == ["payload.bin", "summary.txt"]
            results["F4"] = "producer binary breaks UTF-8 consumer; both artifacts remain"
        controls = subprocess.run([sys.executable, "-B", "verify_control.py"], cwd=FIXTURE,
                                  capture_output=True, text=True)
        assert controls.returncode == 0 and "skipped=1" in controls.stderr
        results["controls"] = "2 passed; remote publish skipped as not applicable"
    assert set(results) == {"F1", "F2", "F3", "F4", "controls"}
    return results


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
