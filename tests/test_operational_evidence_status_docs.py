from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class OperationalEvidenceStatusDocsTests(unittest.TestCase):
    def test_active_status_docs_agree_on_released_memory_boundary(self) -> None:
        active = {
            "README.md": read("README.md"),
            "program README": read("docs/programs/operational-evidence/README.md"),
            "continuation": read(
                "docs/programs/operational-evidence/continuation.md"
            ),
            "roadmap": read("docs/roadmap.md"),
        }
        expectations = {
            "README.md": (
                "v0.14.0",
                "default-disabled",
                "safety/conformance",
                "not activation, promotion, or efficacy evidence",
                "M2 and V3-C",
            ),
            "program README": (
                "v0.14.0",
                "default-disabled",
                "safety/conformance",
                "inactive, non-promotional",
                "efficacy evidence",
                "M2 and V3-C",
            ),
            "continuation": (
                "v0.14.0",
                "default-disabled",
                "safety/conformance",
                "not activation,",
                "promotion, efficacy evidence",
                "authorized Issue before M2, V3-C",
            ),
            "roadmap": (
                "v0.14.0",
                "default-disabled",
                "safety/conformance",
                "no efficacy",
                "M2 and",
                "V3-C release targets remain TBD",
            ),
        }
        for document, expected_phrases in expectations.items():
            for expected in expected_phrases:
                with self.subTest(document=document, expected=expected):
                    self.assertIn(expected, active[document])

        combined = "\n".join(active.values())

        for forbidden in (
            "The future Agent Memory track is planning-only",
            "An Issue #147 M1 delivery or continuation task should",
            "current v0.13.0 tag/Release",
            "Agent Memory remains disabled and has no backend",
            "V3-B, M1, M2, and V3-C release targets are TBD",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, combined)

    def test_continuation_requires_current_discovery_and_new_authority(self) -> None:
        continuation = read("docs/programs/operational-evidence/continuation.md")
        for expected in (
            "current release, open Issues, milestones",
            "does not activate or promote M1",
            "authorized Issue before M2, V3-C",
            "verify current platform",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, continuation)


if __name__ == "__main__":
    unittest.main()
