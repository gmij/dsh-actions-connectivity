import json
import tempfile
import unittest
from pathlib import Path

from staged_design import generate_staged, stage_prompt


class StagedDesignTests(unittest.TestCase):
    def test_four_stages_merge_and_checkpoint(self):
        fragments = {
            'core': {'schema_version': 2, 'level': 'overview',
                     'summary_markdown': 'S', 'design_markdown': 'D', 'experience': {},
                     'milestones': [], 'modules': [], 'decisions': []},
            'tasks': {'task_records': []},
            'pages': {'page_records': []},
            'apis': {'apis': []},
            'bindings': {'bindings': []},
            'channels': {'channels': []},
            'prototype': {'prototype_html': ''},
        }
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            def model(prompt, name):
                calls.append(name)
                self.assertIn('只能是', prompt)
                return json.dumps(fragments[name])
            merged = json.loads(generate_staged('Design brief', 'overview', directory, model))
            self.assertEqual(set(merged), set(fragments['core']) | {'task_records', 'page_records', 'delivery'})
            self.assertEqual(calls, ['core', 'tasks', 'pages', 'apis', 'bindings', 'channels', 'prototype'])
            # Checkpoints must not invoke the model twice for identical run directory.
            again = json.loads(generate_staged('Design brief', 'overview', directory,
                                                lambda *_: self.fail('unnecessary model call')))
            self.assertEqual(again, merged)
            self.assertTrue(Path(directory, 'stage-core.json').exists())

    def test_invalid_stage_does_not_advance(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            def model(prompt, stage):
                calls.append(stage)
                return '{'  # simulate max-token truncation
            with self.assertRaisesRegex(ValueError, 'core.*non-JSON/incomplete'):
                generate_staged('prompt', 'overview', directory, model)
            self.assertEqual(calls, ['core'])

    def test_stage_is_not_allowed_to_smuggle_other_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'fields mismatch'):
                generate_staged('prompt', 'overview', directory,
                                lambda *_: '{"task_records": []}')

    def test_detailed_requires_overview_update_in_core(self):
        message = stage_prompt('brief', 'core', ('level',), {}, 'detailed')
        self.assertIn('overview_update_markdown', message)


if __name__ == '__main__':
    unittest.main()
