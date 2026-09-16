from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class ReviewDispositionContractTests(unittest.TestCase):
    def test_formal_gates_require_disposition_for_every_severity(self) -> None:
        combined = "\n".join(
            (
                read("skills/code-review-gate/SKILL.md"),
                read("skills/docs-review-gate/SKILL.md"),
                read("workflows/review-workflow.md"),
            )
        )
        for severity in ("MUST-FIX", "SHOULD-FIX", "NIT"):
            self.assertIn(severity, combined)
        self.assertIn("durable disposition", combined)
        self.assertIn("promotion trigger", combined)
        self.assertIn("must not disappear", combined)

    def test_follow_up_template_carries_durable_ownership(self) -> None:
        template = read("templates/review/review-follow-up.template.md")
        for field in (
            "Finding ID",
            "Severity",
            "Owner",
            "Durable target",
            "Promotion trigger",
            "Remaining Risk",
            "Disposition verified",
        ):
            with self.subTest(field=field):
                self.assertIn(field, template)

    def test_integration_reference_resolves_in_source_and_plugin(self) -> None:
        import re

        for prefix in ("", "plugin/codex-dev-skills/"):
            targets = []
            for skill in ("code-review", "code-review-deep"):
                entry = ROOT / prefix / "skills" / skill / "SKILL.md"
                links = re.findall(r"\]\(([^)]+integration-boundaries\.md)\)", entry.read_text())
                self.assertEqual(1, len(links), str(entry))
                target = (entry.parent / links[0]).resolve()
                self.assertTrue(target.is_file(), str(target))
                self.assertTrue(target.is_relative_to((ROOT / prefix / "skills").resolve()))
                targets.append(target)
            self.assertEqual(targets[0], targets[1])

    def test_issue_81_tracks_every_review_disposition_during_closure(self) -> None:
        disposition = read("docs/loops/issue-81/review-disposition.md")
        self.assertIn("## MUST-FIX", disposition)
        self.assertIn("## SHOULD-FIX", disposition)
        self.assertIn("## NITS", disposition)
        table_rows = [line for line in disposition.splitlines() if line.startswith("| `")]
        self.assertGreaterEqual(len(table_rows), 44)
        for row in table_rows:
            self.assertTrue(
                "| Fixed |" in row
                or "| Implemented; pending final re-review |" in row
            )
            self.assertNotIn("| Deferred |", row)
            self.assertNotIn("| Rejected |", row)
            self.assertNotIn("| Needs Human Decision |", row)


if __name__ == "__main__":
    unittest.main()
