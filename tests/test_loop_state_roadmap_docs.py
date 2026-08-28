from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class LoopStateRoadmapDocsTests(unittest.TestCase):
    def test_completed_loop_state_baseline_is_not_future_work(self) -> None:
        roadmap = " ".join(read("docs/roadmap.md").split())
        for phrase in (
            "Issue #77 / PR #78 delivered repo-owned loop state and ledger support",
            "durable baseline, not a future task-selection target",
            "contract, templates, validator, tests, and v0.4.0 point-in-time release note",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, roadmap)

        self.assertNotIn(
            "Repo-owned loop state and ledger support is the next loop-engineering hardening step",
            roadmap,
        )


if __name__ == "__main__":
    unittest.main()
