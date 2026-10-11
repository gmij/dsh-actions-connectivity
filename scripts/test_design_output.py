import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import issue_agent

from design_output import validate, write_bundle


def example():
    task = {'id': 'TASK-01', 'title': '导入供应商元数据', 'goal': '只负责验证与归一化输入', 'depends_on': [],
            'inputs': [{'name': 'payload', 'type': 'SupplierPayload', 'source': '供应商 HTTP 返回', 'required': True, 'validation': '外部 ID 必填，页码是正整数'}],
            'outputs': [{'name': 'batch', 'type': 'BookBatch', 'destination': '持久化任务', 'guarantee': '具有稳定供应商 ID 和外部 ID'}],
            'steps': ['验证协议后映射到 BookBatch'],
            'failure_handling': [{'scenario': '非法外部 ID', 'behavior': '拒绝记录并返回字段错误', 'retry': '不重试校验失败', 'idempotency': '相同输入获得相同映射结果'}],
            'acceptance': ['合法记录映射成功，非法 ID 被拒绝'], 'tests': ['单元：空 ID → 字段错误'], 'patterns': ['DEC-01']}
    consumer = copy.deepcopy(task)
    consumer.update(id='TASK-02', title='持久化书目', goal='按复合键幂等写入', depends_on=['TASK-01'], patterns=[])
    consumer['inputs'] = [{'name': 'batch', 'type': 'BookBatch', 'source': 'TASK-01.batch', 'required': True, 'validation': '批次内复合键唯一'}]
    consumer['outputs'] = [{'name': 'report', 'type': 'ImportReport', 'destination': '运营与监控', 'guarantee': '报告成功与拒绝数量'}]
    return {'level': 'detailed', 'summary_markdown': '供应商导入范围与假设', 'design_markdown': '复合唯一键为 supplierId/externalId，事务按批次划分。',
            'tasks': [task, consumer], 'decisions': [{'id': 'DEC-01', 'pattern': 'Adapter', 'problem': '不同供应商字段不一致', 'rationale': '隔离外部协议', 'alternatives': '直接调用较简单但字段转换分散', 'tradeoffs': '增加适配器维护成本，仅用于多协议', 'implementation': 'ISupplierAdapter.Map', 'tasks': ['TASK-01']}],
            'overview_update_markdown': '概要修订：供应商适配模块输出 BookBatch，持久化模块消费该契约；里程碑先适配再持久化。',
            'modules': [{'id': 'MOD-01', 'title': '供应商适配', 'responsibility': '隔离外部协议', 'boundary': '不写数据库', 'task_ids': ['TASK-01'], 'design_markdown': '验证并转换供应商输入。'},
                        {'id': 'MOD-02', 'title': '书目持久化', 'responsibility': '幂等写入', 'boundary': '不访问供应商', 'task_ids': ['TASK-02'], 'design_markdown': '消费 BookBatch 并提交短事务。'}]}


class DesignTests(unittest.TestCase):
    def test_long_design_body_is_allowed_with_a_document_size_limit(self):
        data = example(); data['design_markdown'] = '详细设计正文' * 4000
        validate(data, 'detailed')
        data['design_markdown'] = 'x' * 100001
        with self.assertRaises(ValueError):
            validate(data, 'detailed')

    def test_repair_consumes_error_feedback_and_revalidates_whole_design(self):
        from test_mvp_design import example2
        invalid = example2()
        invalid['modules'][1]['tasks'][0]['inputs'][0]['type'] = 'WrapperRequest'
        with tempfile.TemporaryDirectory() as folder, patch.object(issue_agent, 'OUT', Path(folder)), patch.object(issue_agent, 'invoke_dsh', return_value=json.dumps(example2())) as invoke:
            answer = issue_agent.design_with_repair(json.dumps(invalid), ['dsh'], 'original requirements', 'detailed')
            self.assertIn('MS-01', answer)
            self.assertNotIn('](modules/', answer)
            invoke.assert_called_once()
            self.assertIn('WrapperRequest', invoke.call_args.args[1])
            self.assertIn('SyncApiContract', invoke.call_args.args[1])
            self.assertTrue((Path(folder) / 'contract-error.txt').is_file())

    def test_json_syntax_repair_receives_position_and_complete_schema(self):
        from test_mvp_design import example2
        with tempfile.TemporaryDirectory() as folder, patch.object(issue_agent, 'OUT', Path(folder)), patch.object(issue_agent, 'invoke_dsh', return_value=json.dumps(example2())) as invoke:
            answer = issue_agent.design_with_repair('{"modules":[}', ['dsh'], 'requirements', 'detailed')
            self.assertIn('MS-01', answer)
            self.assertIn('错误位置附近', invoke.call_args.args[1])
            self.assertIn('重建并正确序列化', invoke.call_args.args[1])
            invoke.assert_called_once()

    def test_failed_repair_is_bounded_and_never_delivers_invalid_contract(self):
        from test_mvp_design import example2
        invalid = example2()
        invalid['modules'][1]['tasks'][0]['depends_on'] = ['TASK-01.batch']
        with tempfile.TemporaryDirectory() as folder, patch.object(issue_agent, 'OUT', Path(folder)), patch.object(issue_agent, 'invoke_dsh', return_value=json.dumps(invalid)) as invoke:
            with self.assertRaises(ValueError):
                issue_agent.design_with_repair(json.dumps(invalid), ['dsh'], 'requirements', 'detailed')
            invoke.assert_called_once()
            self.assertFalse((Path(folder) / 'design').exists())

    def test_valid_contract_produces_only_fixed_files_and_readable_contracts(self):
        with tempfile.TemporaryDirectory() as folder:
            answer = write_bundle(json.dumps(example()), Path(folder), 'detailed')
            self.assertIn('为什么采用', answer)
            self.assertIn('TASK-01.batch', answer)
            self.assertEqual({p.name for p in Path(folder).iterdir()}, {'design.md', 'task-contracts.md', 'decisions.md', 'design.json', 'README.md', 'modules', 'overview-update.md'})
            self.assertIn('TASK-01.batch', (Path(folder) / 'modules/MOD-02.md').read_text())
            self.assertIn('MOD-01', (Path(folder) / 'design.md').read_text())

    def test_modules_require_complete_unique_task_ownership_and_overview_sync(self):
        for change in ['missing', 'duplicate', 'unknown', 'overview', 'large']:
            data = example()
            if change == 'missing': data['modules'].pop()
            if change == 'duplicate': data['modules'][1]['task_ids'] = ['TASK-01', 'TASK-02']
            if change == 'unknown': data['modules'][0]['task_ids'] = ['TASK-99']
            if change == 'overview': data['overview_update_markdown'] = ''
            if change == 'large':
                data['modules'] = [data['modules'][0]]
                data['modules'][0]['task_ids'] = ['TASK-01', 'TASK-02']
                data['modules'][0]['design_markdown'] = 'x' * 21000
            with self.assertRaises(ValueError): validate(data, 'detailed')

    def test_consumer_name_and_type_must_match_producer(self):
        for field, value in [('source', 'TASK-01.missing'), ('type', 'DifferentType')]:
            data = example(); data['tasks'][1]['inputs'][0][field] = value
            with self.assertRaises(ValueError):
                validate(data, 'detailed')

    def test_missing_self_and_cyclic_dependencies_are_rejected(self):
        for dependencies in [['TASK-99'], ['TASK-01'], ['TASK-02']]:
            data = example(); data['tasks'][0]['depends_on'] = dependencies
            with self.assertRaises(ValueError):
                validate(data, 'detailed')

    def test_each_task_requires_io_failure_acceptance_and_tests(self):
        for field in ['inputs', 'outputs', 'steps', 'failure_handling', 'acceptance', 'tests']:
            data = example(); data['tasks'][0][field] = []
            with self.assertRaises(ValueError):
                validate(data, 'detailed')

    def test_pattern_requires_rationale_tradeoffs_and_bidirectional_task_mapping(self):
        for field in ['rationale', 'alternatives', 'tradeoffs', 'implementation']:
            data = example(); data['decisions'][0][field] = ''
            with self.assertRaises(ValueError):
                validate(data, 'detailed')
        data = example(); data['decisions'][0]['tasks'] = ['TASK-02']
        with self.assertRaises(ValueError):
            validate(data, 'detailed')

    def test_direct_design_needs_no_unnecessary_pattern(self):
        data = example(); data['decisions'] = []; data['tasks'][0]['patterns'] = []
        validate(data, 'detailed')
        data['level'] = 'overview'
        data.pop('modules'); data.pop('overview_update_markdown')
        validate(data, 'overview')

    def test_invalid_json_level_or_extra_path_never_writes(self):
        for change in [{'level': 'overview'}, {'path': '../../outside'}]:
            data = dict(example(), **change)
            with tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / 'output'
                with self.assertRaises(ValueError):
                    write_bundle(json.dumps(data), target, 'detailed')
                self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
