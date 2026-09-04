"""Memory M1 pilot's default-off path.

This deliberately has no backend import and performs no filesystem work.
"""

from __future__ import annotations


def no_memory() -> dict[str, object]:
    """Return the only default result: no advisory memory was consulted."""
    return {
        "profile": "memory-m1-local-pilot/v1",
        "status": "memory-off",
        "backend_touch_count": 0,
        "records": [],
        "authority": "advisory-only",
    }
