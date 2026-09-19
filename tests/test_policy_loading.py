from __future__ import annotations

import hashlib
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT / 'docs/policy-loading-baseline.json').read_text())


def sections(text: str) -> dict[str, str]:
    return dict(part.split('\n', 1) for part in text.split('\n## ')[1:])


class PolicyLoadingTests(unittest.TestCase):
    """Static source/trigger evidence only; no assertion about model behavior."""

    def test_original_full_section_bodies_remain_available(self) -> None:
        detail = sections((ROOT / 'policies/reusable-workflow-details.md').read_text())
        self.assertEqual(set(BASELINE['section_body_sha256']), set(detail))
        for title, digest in BASELINE['section_body_sha256'].items():
            with self.subTest(section=title):
                self.assertEqual(digest, hashlib.sha256(detail[title].encode()).hexdigest())

    def test_trigger_links_and_legacy_anchors_resolve_in_source_and_plugin(self) -> None:
        for root in (ROOT, ROOT / 'plugin/codex-dev-skills'):
            core = root / 'policies/reusable-workflow-contract.md'
            text = core.read_text()
            self.assertTrue(set(BASELINE['section_body_sha256']) <= set(sections(text)))
            links = re.findall(r'\]\(([^)]+)\)', text)
            self.assertGreaterEqual(len(links), 10)
            for link in links:
                with self.subTest(root=root, link=link):
                    relative, _, anchor = link.partition('#')
                    target = (core.parent / relative).resolve(strict=True)
                    self.assertTrue(target.is_relative_to(root.resolve()))
                    if anchor:
                        headings = {s.lower().replace(' ', '-') for s in sections(target.read_text())}
                        self.assertIn(anchor, headings)

    def test_required_scenarios_keep_discoverable_obligations(self) -> None:
        text = (ROOT / 'policies/reusable-workflow-contract.md').read_text()
        rows = [line for line in text.splitlines() if line.startswith('| ')]
        scenarios = {
            '正式 commit': ('#review-and-merge', '#decision-and-stop-conditions', 'dispositions'),
            '已有 change request': ('exact-head-merge-review-contract.md', 'base-to-head', 'GitHub profile'),
            '驗收失敗': ('model-selection-policy.md', '#decision-and-stop-conditions', '資格'),
            '委派': ('#contextual-prompt-composition', '#shared-phases', 'ownership'),
            'thread／session': ('#protected-boundaries', '#runtime-differences', '#contract-preserving-capability-selection'),
            '批次／並行': ('code-mode-tool-orchestration-policy.md', 'sequential fallback', 'wait/resume'),
        }
        for trigger, obligations in scenarios.items():
            row = next(line for line in rows if trigger in line)
            for obligation in obligations:
                with self.subTest(trigger=trigger, obligation=obligation):
                    self.assertIn(obligation, row)
        for required in ('必要技能或能力仍缺失', '較高優先指令', '驗證新鮮度', '獨立審查', '未成立的列不載入'):
            self.assertIn(required, text)

    def test_simple_entry_required_bytes_decrease_against_named_section_baseline(self) -> None:
        core_bytes = (ROOT / 'policies/reusable-workflow-contract.md').stat().st_size
        for skill in ('docs-review', 'implementation-slice'):
            path = f'skills/{skill}/SKILL.md'
            entry = (ROOT / path).read_text()
            self.assertIn('完整核心與觸發表', entry)
            self.assertIn('before batching/concurrent tool calls or substantial', entry)
            old = BASELINE['bytes'][path] + BASELINE['bytes']['policies/code-mode-tool-orchestration-policy.md']
            old += BASELINE['named_section_bytes']['Contract-Preserving Capability Selection']
            if skill == 'implementation-slice':
                old += sum(BASELINE['named_section_bytes'][title] for title in ('Contextual Prompt Composition', 'Decision And Stop Conditions'))
            self.assertLess(core_bytes + len(entry.encode()), old)


if __name__ == '__main__':
    unittest.main()
