import json
import tempfile
import unittest
from pathlib import Path

from ipc_stages import generate_channels, validate_index, validate_one


def fixture():
    return {
        'modules':[{'id':'MOD-01','title':'Host','interfaces_markdown':'Webview event bridge'}],
        'task_records':[{'id':'TASK-01','module_id':'MOD-01','title':'Bridge','layer':'frontend'}],
        'page_records':[{'id':'UI-01','module_id':'MOD-01','title':'Chat','user_actions':['receive']}],
    }


def spec(identifier,command):
    return {'id':identifier,'module_id':'MOD-01','task_id':'TASK-01',
            'transport':'vscode-webview','command':command,'page_ids':['UI-01']}


def channel(item,source='sequence'):
    return {'id':item['id'],'module_id':item['module_id'],'task_id':item['task_id'],
            'transport':item['transport'],'command':item['command'],
            'request':{'type':'object','properties':{
                'sequence':{'type':'integer','minimum':0},
                'payload':{'type':'object','properties':{'text':{'type':'string'}},
                           'required':['text'],'additionalProperties':False}},
                       'required':['sequence','payload'],'additionalProperties':False},
            'request_example':{'sequence':1,'payload':{'text':'delta'}},
            'response':{'type':'null'},'response_example':None,
            'error':{'type':'null'},'error_example':None,
            'bindings':[{'page_id':'UI-01','action':'consume event',
                         'request_mapping':[],
                         'response_mapping':[{'source':source,'target':'State.lastSeq'}],
                         'loading_behavior':'stream',
                         'error_behavior':'error panel',
                         'success_behavior':'update'}]}


class StagedIpcTests(unittest.TestCase):
    def test_invalid_field_is_repaired_only_for_failing_ipc(self):
        entries=[spec('IPC-01','host.snapshot'),spec('IPC-02','host.delta')]
        calls=[]
        def invoke(prompt,stage):
            calls.append((stage,len(prompt)))
            if stage=='channels-index':
                return json.dumps({'channels':entries})
            if stage=='channels-IPC-01':
                return json.dumps({'channel':channel(entries[0],source='notDeclared')})
            if stage=='channels-IPC-01-repair':
                self.assertIn('notDeclared',prompt)
                return json.dumps({'channel':channel(entries[0])})
            if stage=='channels-IPC-02':
                return json.dumps({'channel':channel(entries[1])})
            self.fail('Unexpected model call '+stage)
        with tempfile.TemporaryDirectory() as root:
            value=generate_channels('Design M1',fixture(),root,invoke)
            self.assertEqual(len(value['channels']),2)
            self.assertEqual([x[0] for x in calls],
                             ['channels-index','channels-IPC-01',
                              'channels-IPC-01-repair','channels-IPC-02'])
            self.assertLess(max(x[1] for x in calls),30000)
            self.assertTrue(Path(root,'stage-channel-IPC-01.json').exists())
            self.assertTrue(Path(root,'stage-ipc-metrics.json').exists())
            replay=generate_channels('Design M1',fixture(),root,
                lambda *_:self.fail('Model should not run on validated checkpoint'))
            self.assertEqual(replay,value)
            self.assertFalse(json.loads(Path(root,'stage-ipc-metrics.json').read_text())['channels'][0]['reused'] is False)

    def test_partial_resume_does_not_regenerate_completed_ipc(self):
        entries=[spec('IPC-01','host.snapshot'),spec('IPC-02','host.delta')]
        with tempfile.TemporaryDirectory() as root:
            Path(root,'stage-channels-index.json').write_text(json.dumps({'channels':entries}))
            Path(root,'stage-channel-IPC-01.json').write_text(json.dumps({'channel':channel(entries[0])}))
            calls=[]
            def invoke(prompt,stage):
                calls.append(stage)
                return json.dumps({'channel':channel(entries[1])})
            data=generate_channels('Design M1',fixture(),root,invoke)
            self.assertEqual(calls,['channels-IPC-02'])
            self.assertEqual(len(data['channels']),2)

    def test_integrated_stage_pipeline_switches_to_granular_mode(self):
        from staged_design import generate_staged
        data=fixture()
        entries=[spec('IPC-01','host.delta')]
        fragments={
            'core': {'schema_version':2,'level':'overview','summary_markdown':'Summary',
                     'design_markdown':'Design','experience':{'interaction_mode':'web','rationale':'Chat'},
                     'milestones':[],'modules':data['modules'],'decisions':[]},
            'tasks':{'task_records':data['task_records']},
            'pages':{'page_records':data['page_records']},
            'apis':{'apis':[]},'bindings':{'bindings':[]},
            'prototype':{'prototype_html':'<html>stub</html>'}
        }
        calls=[]
        def invoke(prompt,stage):
            calls.append(stage)
            if stage=='channels-index':return json.dumps({'channels':entries})
            if stage=='channels-IPC-01':return json.dumps({'channel':channel(entries[0])})
            return json.dumps(fragments[stage])
        with tempfile.TemporaryDirectory() as root:
            result=json.loads(generate_staged('Issue #11','overview',root,invoke,granular_ipc=True))
            self.assertEqual(result['delivery']['channels'][0]['id'],'IPC-01')
            self.assertEqual(calls,['core','tasks','pages','apis','bindings',
                                    'channels-index','channels-IPC-01','prototype'])
            self.assertTrue(Path(root,'stage-channels.json').exists())
            again=json.loads(generate_staged('Issue #11','overview',root,
                                              lambda *_:self.fail('must resume all stages'),granular_ipc=True))
            self.assertEqual(again,result)

    def test_actual_detailed_ipc03_notification_prefixes_are_canonicalized(self):
        from ipc_stages import normalize_notification_paths
        item=spec('IPC-03','session.update')
        c=channel(item)
        b=c['bindings'][0]
        b['response_mapping']=[
            {'source':'request.sequence','target':'Chat.order'},
            {'source':'request.payload.text','target':'Chat.append'}]
        normalize_notification_paths(c)
        self.assertEqual([m['source'] for m in b['response_mapping']],
                         ['sequence','payload.text'])
        validate_one(c,item,fixture())
        b['response_mapping'][0]['source']='request.unknown'
        normalize_notification_paths(c)
        with self.assertRaisesRegex(ValueError,'unknown'):
            validate_one(c,item,fixture())

    def test_ipc04_inverted_notification_ui_bindings_are_corrected(self):
        from ipc_stages import normalize_notification_paths
        item=spec('IPC-04','permission.request')
        c=channel(item)
        c['request']['properties']['options']={'type':'array',
            'items':{'type':'object','properties':{'optionId':{'type':'string'}},
                     'required':['optionId'],'additionalProperties':False}}
        c['request']['required'].append('options')
        c['request_example']['options']=[{'optionId':'allow_once'}]
        b=c['bindings'][0]
        b['request_mapping']=[
            {'target':'state.pendingPermission.requestId','source':'request.sequence'},
            {'target':'ui.optionButtons[].optionId','source':'request.options[].optionId'}]
        b['response_mapping']=[]
        normalize_notification_paths(c)
        self.assertEqual(b['request_mapping'],[])
        self.assertEqual(b['response_mapping'],[
            {'source':'sequence','target':'state.pendingPermission.requestId'},
            {'source':'options[].optionId','target':'ui.optionButtons[].optionId'}])
        validate_one(c,item,fixture())
        b['request_mapping']=[{'target':'invalidState','source':'request.notDeclared'}]
        normalize_notification_paths(c)
        with self.assertRaises(ValueError):
            validate_one(c,item,fixture())

    def test_unmapped_pages_and_unknown_field_fail_closed(self):
        items=[spec('IPC-01','host.snapshot')]
        data=fixture()
        data['page_records'].append({'id':'UI-02','module_id':'MOD-01','title':'Config'})
        with self.assertRaisesRegex(ValueError,'unmapped pages'):
            validate_index(items,data)
        with self.assertRaisesRegex(ValueError,'notDeclared'):
            validate_one(channel(items[0],'notDeclared'),items[0],fixture())

    def test_large_other_ipc_schema_not_passed_to_next_prompt(self):
        entries=[spec('IPC-01','host.snapshot'),spec('IPC-02','host.delta')]
        huge='a'*150000
        with tempfile.TemporaryDirectory() as root:
            Path(root,'stage-channels-index.json').write_text(json.dumps({'channels':entries}))
            first=channel(entries[0])
            first['request']['properties']['payload']['properties']['text']['description']=huge
            Path(root,'stage-channel-IPC-01.json').write_text(json.dumps({'channel':first}))
            sizes=[]
            def invoke(prompt,stage):
                sizes.append(len(prompt))
                self.assertNotIn(huge[:200],prompt)
                return json.dumps({'channel':channel(entries[1])})
            data=generate_channels('Design M1',fixture(),root,invoke)
            self.assertEqual(len(data['channels']),2)
            self.assertLess(max(sizes),30000)


if __name__=='__main__':
    unittest.main()
