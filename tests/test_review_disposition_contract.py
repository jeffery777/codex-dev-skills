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



class ReviewerSelectionContractCoverageTests(unittest.TestCase):
    """Seven wording checks, not a reviewer classifier or runtime evaluation."""

    SCENARIOS = (
        ("author-self-review", ("independent of the author",
                               "Do not count the author's self-review")),
        ("writable-brief-or-name", ("A writable general-purpose agent does not qualify",
                                    "its role name says reviewer")),
        ("reviewer-unavailable-or-unknown", ("unknown, keep the required review incomplete",
                                            "block only its dependent gate",
                                            "independent, authorized safe work may continue")),
        ("eligible-but-not-reviewed", ("Qualification alone does not complete a review",
                                       "actual review, evidence, findings and dispositions")),
        ("current-complete-review", ("current reviewed revision or diff",
                                     "under the existing gate")),
        ("express-isolation-requirement", ("Verify technical isolation only where the task expressly requires it",
                                           "a whole-host no-write rule or an inventory of unrelated tools")),
        ("stale-target-or-conditions", ("A stale target or changed required condition returns to the affected checks",)),
    )

    def test_seven_scenarios_have_contract_wording(self) -> None:
        policy = read("policies/agent-delegation-policy.md")
        self.assertEqual(7, len(self.SCENARIOS))
        for scenario, fragments in self.SCENARIOS:
            with self.subTest(scenario=scenario):
                for fragment in fragments:
                    self.assertIn(fragment, policy, scenario)

    def test_runtime_reference_keeps_evidence_limits(self) -> None:
        runtime = read("docs/native-runtime-capabilities.md")
        policy = ROOT / "policies/agent-delegation-policy.md"
        self.assertTrue(policy.is_file())
        self.assertIn("../policies/agent-delegation-policy.md#codex-required-independent-reviewer-selection",
                      runtime)
        self.assertIn("## Codex Required Independent Reviewer Selection", policy.read_text())
        self.assertIn("that claim remains unverified", runtime)
        self.assertIn("Contract-coverage tests check wording and references only", runtime)
        self.assertIn("model behavior, runtime enforcement, or a qualified live reviewer route", runtime)


if __name__ == "__main__":
    unittest.main()
