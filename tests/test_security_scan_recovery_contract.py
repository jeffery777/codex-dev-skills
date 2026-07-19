from __future__ import annotations

import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import loop_yaml  # noqa: E402


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


class SecurityScanRecoveryContractTests(unittest.TestCase):
    def test_skill_keeps_scan_goal_and_worker_state_separate(self) -> None:
        skill = read("skills/loop-engineering/SKILL.md")
        for phrase in (
            "## Security Scan Recovery",
            "scan-native status",
            "Goal status",
            "worker status",
            "safety_refused",
            "--parent-security-scan-fallback-authorized",
            "must not fail or abandon the scan",
            "canonical JSON bytes",
            "sealed-manifest",
            "fixed neutral heartbeat",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)

    def test_repo_decision_template_has_no_trusted_authority_channel(self) -> None:
        template = loop_yaml.load_yaml(
            ROOT / "templates" / "orchestration" / "loop-decision-input.template.yaml"
        )
        self.assertNotIn("authority", template["input"])
        self.assertIn("security_scan", template["input"]["state"])
        self.assertIn("goal_status", template["input"]["state"])
        self.assertIn("protected_history_sha256", template["input"]["state"])

    def test_protected_event_docs_separate_replay_from_live_write(self) -> None:
        combined = "\n".join(
            (
                read("skills/loop-engineering/SKILL.md"),
                read("docs/loop-engineering.md"),
                read("docs/loop-state-ledger.md"),
                read("workflows/loop-engineering-workflow.md"),
            )
        )
        for phrase in (
            "Replay is not authentication",
            "--authorize-action",
            "--authorization-receipt-sha256",
            "--protected-history-sha256",
            "current-session",
            "Repository YAML",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, combined)

    def test_native_capability_contract_preserves_running_scan(self) -> None:
        contract = read("docs/native-runtime-capabilities.md")
        self.assertIn("### Security scan workbench", contract)
        self.assertIn("remains `running`", contract)
        self.assertIn("terminal scan-failure operation", contract)
        self.assertIn("neutral fixed-format heartbeat", contract)


if __name__ == "__main__":
    unittest.main()
