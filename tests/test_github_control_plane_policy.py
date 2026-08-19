from __future__ import annotations

import pathlib
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class GitHubControlPlanePolicyTests(unittest.TestCase):
    def test_common_skills_reference_one_connector_first_policy(self) -> None:
        reference = "../../policies/github-control-plane-policy.md"
        for relative in (
            "skills/project-delivery/SKILL.md",
            "skills/project-orchestrator/SKILL.md",
            "skills/merge-readiness-gate/SKILL.md",
        ):
            with self.subTest(relative=relative):
                self.assertIn(reference, read(relative))

    def test_policy_limits_gh_to_classified_connector_gaps(self) -> None:
        policy = read("policies/github-control-plane-policy.md")
        for expected in (
            "primary GitHub control plane",
            "connector-operation-unavailable",
            "connector-permission-insufficient",
            "Use `gh` only when",
            "Local `git` remains the normal control plane",
            "does not authorize a GitHub write",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, policy)
        self.assertIn(
            "A repository habit, an existing shell snippet, convenience, or familiarity",
            policy,
        )

    def test_policy_is_packaged_with_common_workflows(self) -> None:
        catalog = yaml.safe_load(read("catalog.yaml"))
        templates = {
            entry["source"]
            for entry in catalog["groups"]["shared-review-gates"]["templates"]
        }
        self.assertIn("policies/github-control-plane-policy.md", templates)

    def test_example_does_not_allow_repository_habit_as_gh_fallback(self) -> None:
        example = read("examples/github-workflow-guidance.md")
        self.assertIn("plugin does not expose the exact needed operation", example)
        self.assertIn("insufficient permission", example)
        self.assertNotIn("repository workflow already relies on it", example)


if __name__ == "__main__":
    unittest.main()
