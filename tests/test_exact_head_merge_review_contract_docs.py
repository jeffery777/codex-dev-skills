from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class ExactHeadMergeReviewContractDocsTests(unittest.TestCase):
    def test_roadmap_keeps_completed_rollout_out_of_future_task_selection(self) -> None:
        roadmap = " ".join(read("docs/roadmap.md").split())
        for phrase in (
            "Issues #185, #190, #192, and #186 are completed",
            "not future task-selection targets",
            "Issue #185 delivered the trusted default-branch collector",
            "Issue #190 repaired the completed-check lifecycle",
            "Issue #192 stabilized the Codex runtime compatibility baseline",
            "Issue #186 sharded repository tests",
            "Issue #188 / PR #189 is reserved as intentionally retained operational",
            "It is not pending product work and must stay unmerged",
            "Canary cleanup remains a separate destructive human gate",
            "rather than mirrored as mutable tracked current-state assertions",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, roadmap)

        self.assertNotIn(
            "Issue #185 defines the next platform-enforcement milestone",
            roadmap,
        )

    def test_roadmap_records_v0220_merge_review_baseline_as_completed(self) -> None:
        roadmap = " ".join(read("docs/roadmap.md").split())
        for phrase in (
            "Issue #205 / PR #206 completed the v0.22.0 provider-neutral exact-head Merge Review baseline",
            "Content readiness binds the final complete range",
            "Provider enforcement is reported separately",
            "installed shared skills no longer impose it on GitLab CE or another forge",
            "This completed baseline is not a future task-selection target",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, roadmap)

        self.assertNotIn(
            "Issue #205 owns the provider-neutral exact-head Merge Review and v0.22.0 candidate",
            roadmap,
        )

    def test_policy_separates_content_and_provider_readiness(self) -> None:
        policy = " ".join(
            read("policies/exact-head-merge-review-contract.md").split()
        )
        for phrase in (
            "their verdict does not satisfy exact-head Merge Review",
            "CHANGE_REQUEST_CREATED",
            "EXACT_HEAD_VERIFICATION_PASSED",
            "EXACT_HEAD_CONTENT_REVIEW_PASSED",
            "CONTENT_READINESS_READY",
            "HUMAN_MERGE_AUTHORIZED",
            "code, documentation, configuration, package, and version coherence",
            "content_review",
            "platform_enforcement",
            "NOT_CONFIGURED",
            "GitLab CE repository may use this content contract without GitHub",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, policy)

        profile = " ".join(
            read("policies/github-exact-head-enforcement-profile.md").split()
        )
        for phrase in (
            "optional provider profile",
            "EXACT_HEAD_CI_PASSED",
            "RECEIPT_PLATFORM_READBACK_CONFIRMED",
            "GITHUB_EXACT_HEAD_ENFORCEMENT_VERIFIED",
            "merge_authorized: false",
            "Each relevant evaluation creates a fresh check run",
            "older successes cannot substitute",
            "Historical same-context check runs are expected",
            "same ID and sequence from silently replacing",
            "Both success and failure publication require",
            "A malformed prior pointer is superseded by a fresh verified failure",
            "per-suite 1,000-run limit",
            "Fork pull requests may receive the same metadata evaluation",
            "A shared GitHub Actions identity is not an adequate trust source",
            "The upstream required-CI set excludes the readiness check itself",
            "zero open `MUST-FIX`, `SHOULD-FIX`, and `NIT` findings",
            "event-driven projection rather than an atomic transaction",
            "Approval-count policy remains a separate human decision",
            "Do not require the readiness check before the canary identifies its App",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, profile)

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

    def test_report_template_separates_content_and_provider_evidence(self) -> None:
        template = read("templates/review/merge-review-report.template.md")
        for field in (
            "Content Review",
            "Platform Enforcement",
            "Overall Formal Gate",
            "Change-request provider/type/number/URL",
            "Base revision",
            "Head revision",
            "Merge-base revision",
            "Diff/range digest",
            "Documentation claims compared",
            "Version/package/generated-artifact parity",
            "Finding ID/severity/disposition/evidence",
            "Selected profile",
            "GitHub Profile Details (only when selected)",
            "separate merge authority",
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
        for relative in (
            "policies/exact-head-merge-review-contract.md",
            "policies/github-exact-head-enforcement-profile.md",
        ):
            with self.subTest(relative=relative):
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
