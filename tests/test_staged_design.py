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

    def test_do_not_fake_http_request_for_notification_or_cancel_ipc(self):
        from staged_design import remove_duplicate_ipc_http_bindings
        original={
          'apis':[{'id':'API-02'}],
          'channels':[
            {'id':'IPC-03','command':'session.update','bindings':[{'page_id':'UI-01'}]},
            {'id':'IPC-05','command':'chat.cancel','bindings':[{'page_id':'UI-01'}]}],
          'bindings':[
            {'id':'BIND-03','api_id':'API-02','page_id':'UI-01','action':'点击发送按钮'},
            {'id':'BIND-04','api_id':'API-02','page_id':'UI-01','action':'收到 session/update 推送并渲染助手消息'},
            {'id':'BIND-06','api_id':'API-02','page_id':'UI-01','action':'点击取消按钮（IPC-05，本阶段无 HTTP，仅 Host 内部消息）'}]}
        remove_duplicate_ipc_http_bindings(original)
        self.assertEqual([x['id'] for x in original['bindings']],['BIND-03'])
        again=dict(original)
        remove_duplicate_ipc_http_bindings(again)
        self.assertEqual(again,original)

    def test_real_http_missing_request_field_is_not_auto_hidden(self):
        from staged_design import remove_duplicate_ipc_http_bindings
        doc={'apis':[{'id':'API-02'}],
             'channels':[{'id':'IPC-03','command':'session.update',
                          'bindings':[{'page_id':'UI-02'}]}],
             'bindings':[{'id':'BIND-04','api_id':'API-02','page_id':'UI-01',
                          'action':'收到 session/update 推送并渲染助手消息'}]}
        remove_duplicate_ipc_http_bindings(doc)
        self.assertEqual(len(doc['bindings']),1)

    def test_known_external_task_inputs_are_repaired_before_ipc(self):
        from staged_design import verify_task_source_types
        tasks=[
          {'id':'TASK-01','outputs':[{'name':'protocolEvidence','type':'ProtocolEvidenceV1'}],
           'inputs':[]},
          {'id':'TASK-02','outputs':[{'name':'hostController','type':'AcpHostControllerApi'}],
           'inputs':[]},
          {'id':'TASK-04','outputs':[],'inputs':[{'name':'permissionRequest',
                  'type':'PermissionRequestParams','source':'TASK-01.protocolEvidence','validation':'valid'}]},
          {'id':'TASK-05','outputs':[],'inputs':[{'name':'projectScope',
                  'type':'ProjectScope','source':'TASK-02.hostController','validation':'valid'}]},
          {'id':'TASK-06','outputs':[],'inputs':[{'name':'projectProfiles',
                  'type':'ProjectProfilesFile','source':'TASK-02.hostController','validation':'valid'}]}
        ]
        doc={'task_records':tasks}
        with tempfile.TemporaryDirectory() as directory:
            changes=verify_task_source_types(doc,directory)
            self.assertEqual(len(changes),3)
            self.assertEqual(tasks[2]['inputs'][0]['source'],
                'runtime:ACP.session/request_permission')
            self.assertEqual(tasks[3]['inputs'][0]['source'],
                'runtime:ValidatedHost.projectScope')
            self.assertEqual(tasks[4]['inputs'][0]['source'],
                'file:.dsh/ai-profiles.json')
            self.assertEqual(verify_task_source_types(doc,directory),[])
            self.assertTrue(Path(directory,'stage-task-source-repairs.json').exists())

    def test_unknown_task_type_mismatch_is_rejected_before_ipc(self):
        from staged_design import verify_task_source_types
        doc={'task_records':[
          {'id':'TASK-01','outputs':[{'name':'a','type':'SomeDTO'}],'inputs':[]},
          {'id':'TASK-02','outputs':[],'inputs':[{'name':'unrelated',
                'type':'OtherDTO','source':'TASK-01.a','validation':'valid'}]}]}
        with self.assertRaisesRegex(ValueError,'targeted repair required'):
            verify_task_source_types(doc)

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

    def test_channel_transport_retry_corrects_enum(self):
        core = {'schema_version': 2, 'level': 'overview', 'summary_markdown': 'S',
                'design_markdown': 'D', 'experience': {}, 'milestones': [],
                'modules': [], 'decisions': []}
        fragments = {'core': core, 'tasks': {'task_records': []},
                     'pages': {'page_records': []}, 'apis': {'apis': []},
                     'bindings': {'bindings': []},
                     'channels': {'channels': [{'id': 'IPC-01',
                                  'transport': '扩展内部 IPC 消息'}]},
                     'prototype': {'prototype_html': ''}}
        calls = []
        def model(prompt, stage):
            calls.append(stage)
            if stage == 'channels-transport-retry':
                self.assertIn('process-stdio', prompt)
                return json.dumps({'channels': [{'id': 'IPC-01', 'transport': 'ipc'}]})
            return json.dumps(fragments[stage])
        with tempfile.TemporaryDirectory() as directory:
            result = json.loads(generate_staged('brief', 'overview', directory, model))
            self.assertEqual(result['delivery']['channels'][0]['transport'], 'ipc')
            self.assertEqual(calls.count('channels-transport-retry'), 1)

    def test_channel_transport_retry_rejects_non_enum(self):
        core = {'schema_version': 2, 'level': 'overview', 'summary_markdown': 'S',
                'design_markdown': 'D', 'experience': {}, 'milestones': [],
                'modules': [], 'decisions': []}
        fragments = {'core': core, 'tasks': {'task_records': []},
                     'pages': {'page_records': []}, 'apis': {'apis': []},
                     'bindings': {'bindings': []},
                     'channels': {'channels': [{'id': 'IPC-01', 'transport': '中文说明'}]}}
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'transport retry still violates'):
                generate_staged('brief', 'overview', directory,
                                lambda prompt, stage: json.dumps(fragments.get(stage, fragments['channels'])))
            self.assertFalse(Path(directory, 'stage-channels.json').exists())

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
