import copy
import json
from pathlib import Path
import tempfile
import unittest

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
            'tasks': [task, consumer], 'decisions': [{'id': 'DEC-01', 'pattern': 'Adapter', 'problem': '不同供应商字段不一致', 'rationale': '隔离外部协议', 'alternatives': '直接调用较简单但字段转换分散', 'tradeoffs': '增加适配器维护成本，仅用于多协议', 'implementation': 'ISupplierAdapter.Map', 'tasks': ['TASK-01']}]}


class DesignTests(unittest.TestCase):
    def test_valid_contract_produces_only_fixed_files_and_readable_contracts(self):
        with tempfile.TemporaryDirectory() as folder:
            answer = write_bundle(json.dumps(example()), Path(folder), 'detailed')
            self.assertIn('为什么采用', answer)
            self.assertIn('TASK-01.batch', answer)
            self.assertEqual({p.name for p in Path(folder).iterdir()}, {'design.md', 'task-contracts.md', 'decisions.md', 'design.json', 'README.md'})

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
