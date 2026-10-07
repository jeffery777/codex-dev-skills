from __future__ import annotations

import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class ExactHeadMergeReviewContractDocsTests(unittest.TestCase):
    def test_contract_local_links_resolve_independently_of_historical_prose(self) -> None:
        for relative in ('policies/engineering-workflow-contract.md',
                         'policies/exact-head-merge-review-contract.md',
                         'policies/reusable-workflow-contract.md'):
            links = re.findall(r'\]\(([^)]+)\)', read(relative))
            self.assertTrue(links, relative)
            for target in links:
                path, _, anchor = target.partition('#')
                if '://' in target:
                    continue
                destination = (ROOT / relative).parent / path
                with self.subTest(source=relative, target=target):
                    self.assertTrue(destination.is_file())
                    if anchor:
                        headings = re.findall(r'^#+ (.+)$', destination.read_text(), re.M)
                        slugs = {re.sub(r'[^\w -]', '', heading.lower()).replace(' ', '-')
                                 for heading in headings}
                        self.assertIn(anchor, slugs)

    def test_draft_state_is_consistent_across_common_consumers_and_templates(self) -> None:
        for relative in ('policies/exact-head-merge-review-contract.md',
                         'skills/project-delivery/SKILL.md',
                         'skills/project-orchestrator/SKILL.md',
                         'skills/loop-engineering/SKILL.md',
                         'templates/orchestration/implementation-plan.template.md',
                         'templates/orchestration/loop-iteration-report.template.md'):
            with self.subTest(relative=relative):
                self.assertIn('REVIEW_REQUIRED', read(relative))
        # Draft checkpoints do not extend the formal verdict schema.
        template = read('templates/review/merge-review-report.template.md')
        self.assertNotIn('REVIEW_REQUIRED', template)

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
        for state in ('EXACT_HEAD_CI_PASSED', 'RECEIPT_PLATFORM_READBACK_CONFIRMED',
                      'GITHUB_EXACT_HEAD_ENFORCEMENT_VERIFIED', 'merge_authorized: false',
                      'MUST-FIX', 'SHOULD-FIX', 'NIT'):
            with self.subTest(state=state):
                self.assertIn(state, profile)

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
