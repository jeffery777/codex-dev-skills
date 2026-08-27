from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class ExactHeadMergeReviewContractDocsTests(unittest.TestCase):
    def test_policy_separates_review_roles_and_requires_ordered_transition(self) -> None:
        policy = " ".join(
            read("policies/exact-head-merge-review-contract.md").split()
        )
        for phrase in (
            "their verdict does not satisfy exact-head Merge Review",
            "PR_CREATED",
            "EXACT_HEAD_CI_PASSED",
            "EXACT_HEAD_MERGE_REVIEW_PASSED",
            "RECEIPT_PLATFORM_READBACK_CONFIRMED",
            "MERGE_READINESS_READY",
            "HUMAN_MERGE_AUTHORIZED",
            "returns the flow to `REVIEW_REQUIRED`",
            "merge_authorized: false",
            "Each relevant evaluation creates a fresh check run",
            "older successes cannot substitute",
            "Historical same-context check runs are expected",
            "same ID and sequence from silently replacing",
            "Both success and failure publication require",
            "per-suite 1,000-run limit",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, policy)

    def test_all_merge_readiness_consumers_require_exact_head_contract(self) -> None:
        consumers = (
            "skills/merge-review/SKILL.md",
            "skills/merge-review-deep/SKILL.md",
            "skills/merge-readiness-gate/SKILL.md",
            "skills/project-delivery/SKILL.md",
            "skills/project-orchestrator/SKILL.md",
            "skills/loop-engineering/SKILL.md",
            "skills/desktop-pr-merge-gate/SKILL.md",
            "workflows/merge-readiness-workflow.md",
            "workflows/loop-engineering-workflow.md",
        )
        for relative in consumers:
            with self.subTest(relative=relative):
                text = read(relative)
                self.assertIn("exact-head-merge-review-contract.md", text)
                self.assertIn("pre-commit", text.lower())

    def test_report_template_binds_platform_evidence_without_merge_authority(self) -> None:
        template = read("templates/review/merge-review-report.template.md")
        for field in (
            "Pull request number and URL",
            "Base SHA",
            "Head SHA",
            "Merge-base SHA",
            "Diff digest",
            "Required hosted CI name/run ID/head SHA/conclusion",
            "Required CI policy source/reference/exact required-name set",
            "Unresolved review threads",
            "Finding ID/severity/disposition/evidence",
            "Receipt ID and URL",
            "Receipt digest",
            "Connector readback time",
            "Merge authorized: `false`",
        ):
            with self.subTest(field=field):
                self.assertIn(field, template)

    def test_fix_reviews_are_proportional_but_new_head_repeats_merge_review(self) -> None:
        combined = "\n".join(
            (
                read("policies/exact-head-merge-review-contract.md"),
                read("skills/project-delivery/SKILL.md"),
                read("skills/loop-engineering/SKILL.md"),
            )
        )
        self.assertIn("smallest scope", combined)
        self.assertIn("complete base-to-head", combined)
        self.assertIn("Clean internal", combined)

    def test_policy_is_distributed_by_catalog_installer_and_plugin_sync(self) -> None:
        relative = "policies/exact-head-merge-review-contract.md"
        self.assertIn(relative, read("catalog.yaml"))
        self.assertIn(relative, read("install.sh"))
        self.assertIn(relative, read("scripts/sync-plugin-package.py"))

    def test_validator_is_distributed_by_catalog_installer_and_plugin_sync(self) -> None:
        relative = "scripts/validate-exact-head-merge-review.py"
        self.assertIn(relative, read("catalog.yaml"))
        self.assertIn(relative, read("install.sh"))
        self.assertIn(relative, read("scripts/sync-plugin-package.py"))
        self.assertEqual(read(relative), read(f"plugin/codex-dev-skills/{relative}"))


if __name__ == "__main__":
    unittest.main()
