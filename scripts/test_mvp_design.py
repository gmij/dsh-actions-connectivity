import copy
import json
from pathlib import Path
import tempfile
import unittest
from design_output import validate, write_bundle
from test_design_output import example


def example2():
    old = example()
    backend = dict(old['tasks'][0], layer='backend', milestone_id='MS-01')
    backend['outputs'] = [{'name': 'api', 'type': 'SyncApiContract', 'destination': '同步页面与集成测试', 'guarantee': '同步接口和状态查询契约完整'}]
    def task(identifier, layer, goal):
        t = copy.deepcopy(backend)
        t.update(id=identifier, title=goal, goal=goal, layer=layer, patterns=[], depends_on=['TASK-01'])
        t['inputs'] = [{'name': 'api', 'type': 'SyncApiContract', 'source': 'TASK-01.api', 'required': True, 'validation': '包含同步和状态查询接口'}]
        t['outputs'] = [{'name': 'result', 'type': layer.title() + 'Artifact', 'destination': 'MS-01 发布验收', 'guarantee': goal + ' 可验收'}]
        return t
    frontend = task('TASK-02', 'frontend', '同步管理页可操作')
    integration = task('TASK-03', 'integration', '验证页面到持久化完整闭环')
    documentation = task('TASK-04', 'documentation', '使用部署指南完整')
    page = {'id': 'UI-01', 'title': '供应商同步', 'route': '/sync', 'layout_markdown': '居中紧凑列表、供应商选择、同步按钮与状态区域', 'user_actions': ['选择供应商→同步→显示状态'], 'states': ['loading', 'empty', 'error', 'success'], 'api_bindings': ['POST /api/sync → SyncApiContract'], 'acceptance': ['按钮点击后能看到结果'], 'prototype_reference': '本次拟定，尚未生成原型'}
    def module(mid, title, tasks, has_ui):
        return {'id': mid, 'title': title, 'responsibility': title, 'boundary': '只负责本模块契约，其他职责由相邻模块承担', 'design_markdown': '先描述模块整体，再定义任务。', 'interfaces_markdown': 'POST /api/sync 返回 batchId；GET /api/batches/{batchId} 返回状态与计数。', 'frontend': {'applicable': has_ui, 'reason': '页面由 MOD-02 承担', 'design_markdown': '状态与操作一致，加载时按钮禁用', 'pages': [page] if has_ui else []}, 'backend': {'applicable': not has_ui, 'reason': 'API由 MOD-01 承担', 'design_markdown': '复合唯一键与事务落库，结构化错误响应'}, 'documentation': {'deliverables': ['docs/sync.md 使用与配置指南'], 'acceptance': ['按文档可复现同步闭环']}, 'tasks': tasks}
    return {'schema_version': 2, 'level': 'detailed', 'summary_markdown': '一版可操作的供应商同步 MVP', 'design_markdown': '页面、API、数据库贯通，未来供应商不阻塞第一版。', 'experience': {'interaction_mode': 'web', 'rationale': '运营需要点击同步并查看结果'}, 'milestones': [{'id': 'MS-01', 'title': '第一个可用同步版本', 'user_value': '运营看到同步后的书目和批次结果', 'user_journey': ['打开页面→选择供应商→同步→查看书目和计数'], 'depends_on': [], 'task_ids': ['TASK-01', 'TASK-02', 'TASK-03', 'TASK-04'], 'integration_tests': [{'scenario': '页面到持久化闭环', 'preconditions': ['种子供应商及空数据库'], 'steps': ['点击同步', '查询批次与书目'], 'expected': ['有书目和正确成功计数']}], 'release_criteria': ['四类任务完成并通过端到端验收'], 'release_plan': '部署API及前端，初始化数据库与种子，按文档点击验证', 'rollback_plan': '回滚前后端版本，保留兼容数据'}], 'modules': [module('MOD-01', '同步服务', [backend], False), module('MOD-02', '操作体验与交付', [frontend, integration, documentation], True)], 'decisions': old['decisions'], 'overview_update_markdown': '完整概要模块章节：MOD-01提供API；MOD-02负责界面；共同交付MS-01。'}


class MvpDesignTests(unittest.TestCase):
    def test_nested_module_design_then_tasks_and_mvp_navigation(self):
        data = example2()
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            answer = write_bundle(json.dumps(data), p, 'detailed', require_current=True)
            self.assertIn('MS-01', answer)
            self.assertFalse('tasks' in json.loads((p/'design.json').read_text()))
            body = (p/'modules/MOD-02.md').read_text()
            self.assertLess(body.index('## 前端与界面设计'), body.index('## 模块内任务'))
            self.assertIn('UI-01', (p/'ui.md').read_text())
            self.assertIn('发布门槛', (p/'milestones.md').read_text())
            self.assertNotIn('TASK-02 · 同步管理页可操作', (p/'design.md').read_text())
            self.assertIn('docs/sync.md', (p/'documentation.md').read_text())
        data['level']='overview'; data.pop('overview_update_markdown')
        validate(data, 'overview')

    def test_release_cannot_be_backend_only_or_skip_e2e_docs(self):
        for layer in ['frontend', 'integration', 'documentation']:
            data=example2()
            next(t for m in data['modules'] for t in m['tasks'] if t['layer']==layer)['layer']='backend'
            with self.assertRaises(ValueError): validate(data,'detailed')
        data=example2(); data['milestones'][0]['integration_tests']=[]
        with self.assertRaises(ValueError): validate(data,'detailed')
        data=example2(); data['milestones'][0]['release_plan']=''
        with self.assertRaises(ValueError): validate(data,'detailed')

    def test_milestone_ownership_future_dependencies_and_cycles(self):
        data=example2(); data['modules'][1]['tasks'][0]['milestone_id']='MS-99'
        with self.assertRaises(ValueError): validate(data,'detailed')
        data=example2(); data['milestones'][0]['task_ids'].append('TASK-01')
        with self.assertRaises(ValueError): validate(data,'detailed')
        data=example2(); data['milestones'][0]['depends_on']=['MS-01']
        with self.assertRaises(ValueError): validate(data,'detailed')

    def test_pages_require_full_state_design_and_legacy_not_new_delivery(self):
        data=example2(); data['modules'][1]['frontend']['pages'][0]['states'].remove('error')
        with self.assertRaises(ValueError): validate(data,'detailed')
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'new'
            with self.assertRaises(ValueError): write_bundle(json.dumps(example()),p,'detailed',require_current=True)
            self.assertFalse(p.exists())


class MilestoneDependencyTests(unittest.TestCase):
    def test_task_cannot_pull_a_future_milestone_into_first_release(self):
        data = example2()
        second = copy.deepcopy(data['milestones'][0])
        second.update(id='MS-02', depends_on=['MS-01'], task_ids=['TASK-05','TASK-06','TASK-07','TASK-08'])
        data['milestones'].append(second)
        for module in data['modules']:
            extra=[]
            for task in module['tasks']:
                t=copy.deepcopy(task)
                t['id']='TASK-' + str(int(t['id'][5:])+4).zfill(2)
                t['milestone_id']='MS-02'; t['patterns']=[]
                t['depends_on']=[d.replace('TASK-01','TASK-05') for d in t['depends_on']]
                for v in t['inputs']: v['source']=v['source'].replace('TASK-01.','TASK-05.')
                extra.append(t)
            module['tasks'] += extra
        validate(data, 'detailed')
        data['modules'][1]['tasks'][0]['depends_on'].append('TASK-05')
        with self.assertRaisesRegex(ValueError, 'future/unrelated'): validate(data,'detailed')


def wire_example():
    data=example2()
    result={k:v for k,v in data.items() if k!='modules'}
    result.update(modules=[],task_records=[],page_records=[])
    for m in data['modules']:
        result['modules'].append({k:m[k] for k in ['id','title','responsibility','boundary','design_markdown','interfaces_markdown']} | {'frontend_applicable':m['frontend']['applicable'],'frontend_reason':m['frontend']['reason'],'frontend_markdown':m['frontend']['design_markdown'],'backend_applicable':m['backend']['applicable'],'backend_reason':m['backend']['reason'],'backend_markdown':m['backend']['design_markdown'],'documentation_deliverables':m['documentation']['deliverables'],'documentation_acceptance':m['documentation']['acceptance']})
        result['task_records'] += [dict(t,module_id=m['id']) for t in m['tasks']]
        result['page_records'] += [dict(p,module_id=m['id']) for p in m['frontend']['pages']]
    return result


class WireContractTests(unittest.TestCase):
    def test_transport_records_compile_to_module_owned_canonical_design(self):
        from design_output import normalize_wire
        self.assertEqual(normalize_wire(wire_example()),example2())
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)
            write_bundle(json.dumps(wire_example()),p,'detailed',require_current=True)
            self.assertEqual(json.loads((p/'design.json').read_text()),example2())
            self.assertIn('UI-01',(p/'modules/MOD-02.md').read_text())
        data=wire_example();data['task_records'][0]['module_id']='MOD-99'
        with self.assertRaises(ValueError):validate(data,'detailed')
        data=wire_example();data['modules'][1]['frontend_applicable']=False
        with self.assertRaises(ValueError):validate(data,'detailed')
