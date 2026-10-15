from __future__ import annotations

import hashlib
import json
import pathlib
import re
import unittest
from urllib.parse import unquote, urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT / 'docs/policy-loading-baseline.json').read_text())


def sections(text: str) -> dict[str, str]:
    return dict(part.split('\n', 1) for part in text.split('\n## ')[1:])


class PolicyLoadingTests(unittest.TestCase):
    """Static source/trigger evidence only; no assertion about model behavior."""

    def test_legacy_detail_headings_keep_fixed_core_and_codex_overlays_discoverable(self) -> None:
        detail = sections((ROOT / 'policies/reusable-workflow-details.md').read_text())
        self.assertEqual(set(BASELINE['section_body_sha256']), set(detail))
        text = (ROOT / 'policies/reusable-workflow-details.md').read_text()
        for required in ('core-contract-loading.md', 'wf-capability', 'wf-delegation',
                         'native-runtime-capabilities.md', 'model-selection-policy.md',
                         'context-continuity-policy.md', 'review-artifact-policy.md',
                         'security-review-escalation-policy.md', 'github-exact-head-enforcement-profile.md'):
            self.assertIn(required, text)
        # #267 is historical measurement, not permission to preserve a competing
        # common contract after #335 switches authority to immutable Core.
        self.assertEqual('b3c195b69a0f5c948627d16cfd5fb154dcaf609e', BASELINE['source_revision'])

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
                        target_text = target.read_text()
                        headings = {s.lower().replace(' ', '-') for s in sections(target_text)}
                        headings.update(re.findall(r'<a id="([^"]+)"', target_text))
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

    def test_complete_adapter_policy_link_closure_is_available_in_source_and_plugin(self) -> None:
        entries = ('core-contract-loading.md', 'engineering-workflow-contract.md',
                   'reusable-workflow-contract.md', 'reusable-workflow-details.md',
                   'exact-head-merge-review-contract.md')
        for root in (ROOT, ROOT / 'plugin/codex-dev-skills'):
            pending = [root / 'policies' / name for name in entries]
            seen = set()
            while pending:
                path = pending.pop()
                if path in seen:
                    continue
                seen.add(path)
                for raw in re.findall(r'\]\(([^)\s]+)\)', path.read_text()):
                    url = urlsplit(raw)
                    if url.scheme or url.netloc:
                        continue
                    with self.subTest(root=root, path=path, link=raw):
                        target = (path.parent / unquote(url.path)).resolve(strict=True) if url.path else path
                        self.assertTrue(target.is_relative_to(root.resolve()))
                        self.assertTrue(target.is_file())
                        if target.parent == root / 'policies':
                            pending.append(target)

    def test_simple_entries_preserve_core_loading_and_conditional_policy_triggers(self) -> None:
        contract = (ROOT / 'policies/reusable-workflow-contract.md').read_text()
        self.assertIn('core-contract-loading.md', contract)
        loading = (ROOT / 'policies/core-contract-loading.md').read_text()
        for required in ('validate-core-contract-snapshot.py', 'workflow.md',
                         'authorization-and-stops.md', 'review-and-security.md',
                         'exact-head-and-evidence.md', 'source/plugin', 'filesystem'):
            self.assertIn(required, loading)
        for skill in ('docs-review', 'implementation-slice'):
            path = f'skills/{skill}/SKILL.md'
            entry = (ROOT / path).read_text()
            self.assertIn('完整核心與觸發表', entry)
            self.assertIn('before batching/concurrent tool calls or substantial', entry)


if __name__ == '__main__':
    unittest.main()
