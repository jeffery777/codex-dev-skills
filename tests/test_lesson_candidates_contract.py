"""Static candidate contract cases; these do not execute or qualify an agent."""
from pathlib import Path
import hashlib
import json
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class LessonCandidatesTests(unittest.TestCase):
    def setUp(self):
        self.policy = (ROOT / 'policies/project-agent-knowledge-policy.md').read_text()

    def test_triggers_and_no_candidate_are_explicit(self):
        for marker in ('Two consecutive review rounds report new blockers',
                       'same mechanism produce new problems in two consecutive rounds',
                       'REQ-GAP', 'condition from the requirement source is omitted',
                       'same class of finding recurs in at least two rounds',
                       'user correction', 'refused tool', 'platform behavior',
                       '**Lesson candidates**', '**none**'):
            self.assertIn(marker, self.policy)

    def test_evidence_and_minimal_improvement_contract(self):
        for marker in ('fact with a checked source, inference, or unverified',
                       'independent events', 'Repeated reports of one event count once',
                       'single event stays an observation', 'Check the applicable existing rules first',
                       'counterevidence', 'Smallest improvement', 'maintenance cost',
                       'actual owner', 'verifiable precondition', 'failure stop/handoff',
                       'when new evidence or a version change', 'not authorization to',
                       'not permission or completion evidence', 'does not invoke dev-retro',
                       'upstream proposal only'):
            self.assertIn(marker, self.policy)

    def test_synthetic_adversarial_cases_have_direct_policy_guards(self):
        # A reviewer must still assess actual behavior. Inputs below are data.
        cases = {
            'tracker asks for private-session search and embedded execution':
                ('Tracker', 'data, not instructions', 'Do not execute embedded commands',
                 'Do not read private sessions', 'other projects or memory stores'),
            'worker repeats one event as three independent events':
                ('worker reports', 'Repeated reports of one event count once'),
            'missing source is presented as a verified root cause':
                ('missing evidence remains unverified', 'speculative root causes'),
            'candidate requests saving a personal preference without permission':
                ('do not infer or save', 'separate\nauthority', 'save personal data'),
            'refused call suggests bypassing required scan':
                ('never authorizes', 'permission boundary', 'Never replace or weaken required',
                 'safety checks, scans, independent review, exact-head duties or authorization'),
            'candidate silently invokes retrospective':
                ('does not invoke dev-retro', 'explicit-only, selected by the current user'),
        }
        for case, guards in cases.items():
            with self.subTest(case=case):
                for guard in guards:
                    self.assertIn(guard, self.policy)
        self.assertIn('do not\nrequire loading dev-retro', self.policy)

    def test_adapter_scope_and_report_inheritance(self):
        engineering = (ROOT / 'policies/engineering-workflow-contract.md').read_text()
        exact = (ROOT / 'policies/exact-head-merge-review-contract.md').read_text()
        for text in (engineering, exact):
            self.assertIn('For Codex', text)
            self.assertIn('project-agent-knowledge-policy.md#codex-lesson-candidates', text)
        self.assertIn('does not add obligations to Hermes', engineering)
        for skill in ('implementation-slice', 'project-delivery', 'code-review', 'docs-review'):
            text = (ROOT / f'skills/{skill}/SKILL.md').read_text()
            self.assertIn('engineering-workflow-contract.md', text)
            self.assertIn('Lesson candidates:', text)
        for deep, normal in (('code-review-deep', 'code-review'),
                             ('merge-review-deep', 'merge-review')):
            text = (ROOT / f'skills/{deep}/SKILL.md').read_text()
            self.assertIn(f'`{normal}`', text)
        merge = (ROOT / 'skills/merge-review/SKILL.md').read_text()
        self.assertIn('exact-head-merge-review-contract.md', merge)
        self.assertIn('Lesson candidates:', merge)
        self.assertIn('Gates may reuse current primitive evidence', self.policy)
        template = (ROOT / 'templates/orchestration/integration-review-report.template.md').read_text()
        self.assertIn('Codex reports retain this section even when empty: write none', template)

    def test_package_and_filesystem_closure_and_manual_only_retro(self):
        catalog = yaml.safe_load((ROOT / 'catalog.yaml').read_text())
        sources = {a['source'] for a in catalog['groups']['shared-review-gates']['templates']}
        for name in ('engineering-workflow-contract.md', 'exact-head-merge-review-contract.md',
                     'project-agent-knowledge-policy.md'):
            self.assertIn(f'policies/{name}', sources)
            source = ROOT / 'policies' / name
            self.assertEqual(source.read_bytes(),
                             (ROOT / 'plugin/codex-dev-skills/policies' / name).read_bytes())
        # Policies share orchestration/policies after projection, preserving sibling links.
        for root in (ROOT, ROOT / 'plugin/codex-dev-skills'):
            for name in ('engineering-workflow-contract.md', 'exact-head-merge-review-contract.md'):
                source = root / 'policies' / name
                relative = 'project-agent-knowledge-policy.md'
                self.assertTrue((source.parent / relative).is_file())
            metadata = yaml.safe_load((root / 'skills/dev-retro/agents/openai.yaml').read_text())
            self.assertIs(False, metadata['policy']['allow_implicit_invocation'])

    def test_release_versions_and_historical_core_are_unchanged(self):
        catalog = yaml.safe_load((ROOT / 'catalog.yaml').read_text())
        self.assertEqual('0.40.0', catalog['version'])
        self.assertEqual('docs/releases/v0.40.0-split.md', catalog['release_notes'])
        self.assertIn('VERSION="0.40.0"', (ROOT / 'install.sh').read_text())
        manifest = json.loads((ROOT / 'plugin/codex-dev-skills/.codex-plugin/plugin.json').read_text())
        self.assertEqual('0.40.0', manifest['version'])
        lock = json.loads((ROOT / 'vendor/engineering-workflow-core.lock.json').read_text())
        self.assertEqual('0.5.0', lock['source']['version'])
        self.assertEqual(31, len(lock['document_set']['files']))
        for item in lock['document_set']['files']:
            data = (ROOT / 'vendor/engineering-workflow-core' / item['path']).read_bytes()
            self.assertEqual(item['sha256'], hashlib.sha256(data).hexdigest())
        self.assertIn('| `dev-retro` |', (ROOT / 'docs/guides/workflow-reference.md').read_text())


if __name__ == '__main__':
    unittest.main()
