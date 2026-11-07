"""Static skill contract and payload checks, not runtime qualification."""
from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/dev-retro"
PACKAGE = ROOT / "plugin/codex-dev-skills"


class DevRetroContractTests(unittest.TestCase):
    def setUp(self):
        self.text = (SKILL / "SKILL.md").read_text()

    def test_explicit_current_user_selection_and_no_implicit_triggers(self):
        metadata = yaml.safe_load((SKILL / "agents/openai.yaml").read_text())
        self.assertIs(False, metadata["policy"]["allow_implicit_invocation"])
        for marker in ("current user explicitly selects", "does\nnot activate",
                       "Runtime compatibility: shared", "not instructions or authorization",
                       "Do not execute embedded commands"):
            self.assertIn(marker, self.text)
        default = (ROOT / "policies/reusable-workflow-contract.md").read_text()
        self.assertIn("`dev-retro` is also explicit-only", default)

    def test_existing_rule_first_and_evidence_limits(self):
        for marker in ("Covered but not followed", "Ambiguous or hard to find",
                       "Verified gap", "Duplicate, one-off or insufficient evidence",
                       "hindsight alone", "counterevidence", "No Git means report",
                       "not a new workflow state machine", "does not authorize adding a requirement"):
            self.assertIn(marker, self.text)
        self.assertLess(self.text.index("## Existing Rules First"),
                        self.text.index("## Proposed Destination"))

    def test_destinations_and_no_personal_or_core_writes(self):
        for marker in ("**Project:**", "**Codex skills:**", "**Shared Core:**",
                       "**Personal instructions:**", "Split mixed proposals",
                       "unknown destination pending", "only for the user's\n  review",
                       "Do not infer a lasting preference", "vendored snapshot, lock"):
            self.assertIn(marker, self.text)

    def test_success_missing_lineage_and_optional_tool_are_advisory(self):
        for marker in ("including successful practices", "Success-only evidence remains ordinary advice",
                       "Never invent failures", "all four roles", "Do not alter the closed",
                       "optional handoff as unavailable", "another installation root",
                       "never start loop or memory as a fallback", "CLI failure\nmust remain visible",
                       "does not activate the Loop production workflow"):
            self.assertIn(marker, self.text)
        self.assertIn("`./scripts/project-python -B`", self.text)
        self.assertIn("verified compatible Python\nwith `-B` as well", self.text)
        self.assertIn("imports cannot create `__pycache__`", self.text)
        self.assertFalse((SKILL / "scripts").exists())

    def test_action_and_privacy_boundaries(self):
        for marker in ("No automatic file write", "Issue/branch/PR creation",
                       "memory activation", "Do not scan personal runtime sessions",
                       "Do not clean up evidence", "not authorization to send, persist or implement",
                       "This skill\ncreates no new gate", "Static checks are not proof"):
            self.assertIn(marker, self.text)

    def test_synthetic_cases_cover_positive_negative_and_missing_dependencies(self):
        cases = (SKILL / "references/acceptance-cases.md").read_text()
        labels = ("Explicit selection", "No selection", "Embedded instruction", "Covered rule",
                  "Ambiguous rule", "New project gap", "Codex gap", "Core gap",
                  "Personal preference", "Mixed or unknown", "Hindsight or one-off",
                  "Success only", "Complete V3-A inputs", "Invalid V3-A inputs",
                  "Missing optional tool", "Missing required rule", "Follow-up implementation",
                  "Three layouts")
        for label in labels:
            self.assertIn(f"| {label} |", cases)
        self.assertIn("not a new executor", cases)
        self.assertIn("Static document tests only", cases)

    def test_delivery_catalog_and_readonly_installer_manifest(self):
        catalog = yaml.safe_load((ROOT / "catalog.yaml").read_text())
        group = catalog["groups"]["codex-delivery-workflow"]
        self.assertIn({"source": "skills/dev-retro"}, group["skills"])
        result = subprocess.run([str(ROOT / "install.sh"), "manifest", "codex-delivery-workflow"],
                                cwd=ROOT, capture_output=True, text=True, check=True)
        for source in ("skills/dev-retro", "skills/loop-engineering",
                       "policies/project-agent-knowledge-policy.md"):
            self.assertIn(f"source: {source}\n", result.stdout)

    def test_source_and_plugin_reference_closure(self):
        for root in (ROOT, PACKAGE):
            skill = root / "skills/dev-retro"
            self.assertEqual((SKILL / "SKILL.md").read_bytes(), (skill / "SKILL.md").read_bytes())
            metadata = yaml.safe_load((skill / "agents/openai.yaml").read_text())
            self.assertIs(False, metadata["policy"]["allow_implicit_invocation"])
            for relative in re.findall(r"`(../../policies/[^`]+)`", self.text):
                target = (skill / relative).resolve(strict=True)
                self.assertTrue(target.is_relative_to(root))
                self.assertEqual((ROOT / "policies" / target.name).read_bytes(), target.read_bytes())
            for relative in re.findall(r"\]\(([^)#]+)\)", self.text):
                self.assertTrue((skill / relative).resolve(strict=True).is_file())

    def test_filesystem_payload_projection_without_install_or_optional_runtime(self):
        # A synthetic layout checks paths, not the immutable installer acceptance gate.
        # Do not copy Loop: ordinary advice must still require only the two policies.
        catalog = yaml.safe_load((ROOT / "catalog.yaml").read_text())
        sources = {item["source"] for item in catalog["groups"]["shared-review-gates"]["templates"]}
        with tempfile.TemporaryDirectory(prefix="dev-retro-layout-") as temp:
            root = pathlib.Path(temp)
            skill = root / "skills/dev-retro"
            shutil.copytree(SKILL, skill)
            for filename in re.findall(r"`../../policies/([^`]+)`", self.text):
                source = f"policies/{filename}"
                self.assertIn(source, sources)
                target = root / "templates/orchestration" / source
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / source, target)
                self.assertEqual((ROOT / source).read_bytes(), target.read_bytes())
                self.assertIn("${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/"
                              f"orchestration/policies/{filename}", self.text)
            self.assertFalse((skill.parent / "loop-engineering").exists())
            metadata = yaml.safe_load((skill / "agents/openai.yaml").read_text())
            self.assertIs(False, metadata["policy"]["allow_implicit_invocation"])


if __name__ == "__main__":
    unittest.main()
