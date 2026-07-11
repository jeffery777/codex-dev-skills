#!/usr/bin/env python3
"""Repository entrypoint for the installed Loop Engineering profile preflight."""

from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "skills" / "loop-engineering" / "scripts" / "profile_preflight.py"),
        run_name="__main__",
    )
