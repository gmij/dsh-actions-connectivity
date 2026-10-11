import json
import tempfile
import unittest
from pathlib import Path

from staged_design import generate_staged, stage_prompt, parse_stage_json


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

    def test_json_code_fence(self):
        self.assertEqual(parse_stage_json('```json\n{"core":true}\n```'), {'core': True})
        self.assertEqual(parse_stage_json('```JSON\r\n{"core":true}\r\n```'), {'core': True})
        self.assertEqual(parse_stage_json(' {"core":true} '), {'core': True})
        for value in ('before\n```json\n{}\n```', '```json\n{}', '```json\n{}\n```\nafter'):
            with self.assertRaises(json.JSONDecodeError):
                parse_stage_json(value)

    def test_redundant_matching_envelope_is_ignored(self):
        fragments = {
            'core': {'schema_version': 2, 'level': 'overview',
                     'summary_markdown': 'S', 'design_markdown': 'D', 'experience': {},
                     'milestones': [], 'modules': [], 'decisions': []},
            'tasks': {'schema_version': 2, 'level': 'overview', 'task_records': []},
            'pages': {'page_records': []}, 'apis': {'apis': []},
            'bindings': {'bindings': []}, 'channels': {'channels': []},
            'prototype': {'prototype_html': ''},
        }
        with tempfile.TemporaryDirectory() as directory:
            data = json.loads(generate_staged('brief', 'overview', directory,
                                              lambda prompt, name: json.dumps(fragments[name])))
            self.assertEqual(data['task_records'], [])
            self.assertEqual(json.loads(Path(directory, 'stage-tasks.json').read_text()), {'task_records': []})

    def test_missing_core_experience_is_retried_once(self):
        core = {'schema_version': 2, 'level': 'overview', 'summary_markdown': 'S',
                'design_markdown': 'D', 'milestones': [], 'modules': [], 'decisions': [],
                'overview_update_markdown_placeholder': ''}
        fragments = {'tasks': {'task_records': []}, 'pages': {'page_records': []},
                     'apis': {'apis': []}, 'bindings': {'bindings': []},
                     'channels': {'channels': []}, 'prototype': {'prototype_html': ''}}
        calls = []
        def model(prompt, name):
            calls.append(name)
            if name == 'core':
                return json.dumps(core)
            if name == 'core-schema-retry':
                self.assertIn('experience', prompt)
                return json.dumps({**{k: v for k, v in core.items()
                                       if k != 'overview_update_markdown_placeholder'},
                                   'experience': {'interaction_mode': 'web', 'rationale': 'VS Code Webview'}})
            return json.dumps(fragments[name])
        with tempfile.TemporaryDirectory() as directory:
            result = json.loads(generate_staged('brief', 'overview', directory, model))
            self.assertEqual(result['experience']['interaction_mode'], 'web')
            self.assertEqual(calls.count('core-schema-retry'), 1)
            self.assertTrue(Path(directory, 'stage-core.json').exists())

    def test_schema_retry_must_not_accept_still_missing_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            def model(prompt, name):
                calls.append(name)
                return json.dumps({'schema_version': 2, 'level': 'overview'})
            with self.assertRaisesRegex(ValueError, 'schema retry fields mismatch'):
                generate_staged('brief', 'overview', directory, model)
            self.assertEqual(calls, ['core', 'core-schema-retry'])

    def test_conflicting_envelope_is_rejected(self):
        fragments = {
            'core': {'schema_version': 2, 'level': 'overview',
                     'summary_markdown': 'S', 'design_markdown': 'D', 'experience': {},
                     'milestones': [], 'modules': [], 'decisions': []},
            'tasks': {'schema_version': 1, 'level': 'overview', 'task_records': []},
        }
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'conflicting schema_version'):
                generate_staged('brief', 'overview', directory,
                                lambda prompt, name: json.dumps(fragments[name]))

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
