"""Validate design contracts and produce fixed Markdown/JSON deliverables."""
import json
import re

IO = {'name', 'type', 'source', 'required', 'validation'}
OUTPUT = {'name', 'type', 'destination', 'guarantee'}
TASK = {'id', 'title', 'goal', 'depends_on', 'inputs', 'outputs', 'steps', 'failure_handling', 'acceptance', 'tests', 'patterns'}
DECISION = {'id', 'pattern', 'problem', 'rationale', 'alternatives', 'tradeoffs', 'implementation', 'tasks'}
MODULE = {'id', 'title', 'responsibility', 'boundary', 'task_ids', 'design_markdown'}


def text(value, max_length=15000):
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError(f'Required design text is missing or exceeds {max_length} characters')
    return value


def strings(values, required=True):
    if not isinstance(values, list) or len(values) > 50 or (required and not values):
        raise ValueError('Expected design list')
    for value in values:
        text(value)


def validate(data, level):
    fields = {'level', 'summary_markdown', 'design_markdown', 'decisions', 'tasks'}
    if level == 'detailed':
        fields |= {'modules', 'overview_update_markdown'}
    if not isinstance(data, dict) or set(data) != fields or data['level'] != level or level not in {'overview', 'detailed'}:
        raise ValueError('Invalid design output contract')
    text(data['summary_markdown']); text(data['design_markdown'], max_length=100000)
    tasks = data['tasks']
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 30:
        raise ValueError('Expected 1 to 30 bounded tasks')
    indexed = {}
    for task in tasks:
        if not isinstance(task, dict) or set(task) != TASK or not re.fullmatch(r'TASK-\d{2,3}', task['id']):
            raise ValueError('Invalid task contract')
        if task['id'] in indexed:
            raise ValueError('Duplicate task ID')
        indexed[task['id']] = task
        for key in ['title', 'goal']:
            text(task[key])
        for key in ['depends_on', 'patterns']:
            strings(task[key], required=False)
        for key in ['steps', 'acceptance', 'tests']:
            strings(task[key])
        for key, fields in [('inputs', IO), ('outputs', OUTPUT)]:
            values = task[key]
            if not isinstance(values, list) or not 1 <= len(values) <= 20:
                raise ValueError('Every task needs explicit inputs and outputs')
            names = set()
            for value in values:
                if not isinstance(value, dict) or set(value) != fields:
                    raise ValueError('Invalid input/output fields')
                for field in fields - {'required'}:
                    text(value[field])
                if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', value['name']) or value['name'] in names:
                    raise ValueError('Input/output names must be unique contract identifiers')
                names.add(value['name'])
                if key == 'inputs' and type(value['required']) is not bool:
                    raise ValueError('Input required must be boolean')
        failures = task['failure_handling']
        if not isinstance(failures, list) or not failures:
            raise ValueError('Task failure/retry/idempotency contract is required')
        for failure in failures:
            if not isinstance(failure, dict) or set(failure) != {'scenario', 'behavior', 'retry', 'idempotency'}:
                raise ValueError('Invalid failure contract')
            for value in failure.values():
                text(value)
    for task in tasks:
        if len(set(task['depends_on'])) != len(task['depends_on']) or any(dep not in indexed or dep == task['id'] for dep in task['depends_on']):
            raise ValueError(f"{task['id']}: depends_on must contain existing task IDs only, not output references; got {task['depends_on']}")
        for value in task['inputs']:
            source = value['source']
            if source.startswith('TASK-'):
                match = re.fullmatch(r'(TASK-\d{2,3})\.([A-Za-z][A-Za-z0-9_]*)', source)
                if not match or match[1] not in task['depends_on']:
                    raise ValueError(f"{task['id']}.{value['name']}: source {source} must reference an output of a task ID listed in depends_on")
                producer = next((o for o in indexed[match[1]]['outputs'] if o['name'] == match[2]), None)
                if producer is None or producer['type'] != value['type']:
                    raise ValueError(f"{task['id']}.{value['name']}: source {source} has type {producer['type'] if producer else 'MISSING OUTPUT'} but consumer declares {value['type']}; consume the exact producer DTO as a separate input, not a wrapper/request/interface derived from it")
    visited, active = set(), set()
    def visit(identifier):
        if identifier in active:
            raise ValueError('Cyclic task dependency')
        if identifier in visited:
            return
        active.add(identifier)
        for dep in indexed[identifier]['depends_on']:
            visit(dep)
        active.remove(identifier); visited.add(identifier)
    for identifier in indexed:
        visit(identifier)
    if level == 'detailed':
        text(data['overview_update_markdown'], max_length=30000)
        modules = data['modules']
        if not isinstance(modules, list) or not 1 <= len(modules) <= 20:
            raise ValueError('Detailed design requires a module plan and revised overview chapter')
        module_ids, assigned = set(), set()
        for module in modules:
            if not isinstance(module, dict) or set(module) != MODULE or not re.fullmatch(r'MOD-\d{2,3}', module['id']):
                raise ValueError('Invalid module fields or ID; use MOD-01 identifiers')
            if module['id'] in module_ids:
                raise ValueError('Duplicate module ID')
            module_ids.add(module['id'])
            for key in ['title', 'responsibility', 'boundary']:
                text(module[key])
            text(module['design_markdown'], max_length=30000)
            strings(module['task_ids'])
            for identifier in module['task_ids']:
                if identifier not in indexed or identifier in assigned:
                    raise ValueError(f'Module {module["id"]}: task {identifier} must exist and belong to exactly one module')
                assigned.add(identifier)
        if assigned != set(indexed):
            raise ValueError(f'Every task must have a module; missing {sorted(set(indexed) - assigned)}')
        size = len(data['design_markdown']) + sum(len(m['design_markdown']) for m in modules)
        if (size > 20000 or len(tasks) >= 6) and len(modules) < 2:
            raise ValueError('Large detailed design must split into responsibility-based modules and update overview; do not merely expand one document')
    decisions = data['decisions']
    if not isinstance(decisions, list) or len(decisions) > 30:
        raise ValueError('Invalid decisions')
    decision_ids = set()
    for decision in decisions:
        if not isinstance(decision, dict) or set(decision) != DECISION:
            raise ValueError('Invalid design-pattern decision')
        for key in DECISION - {'tasks'}:
            text(decision[key])
        if decision['id'] in decision_ids:
            raise ValueError('Duplicate decision ID')
        decision_ids.add(decision['id'])
        strings(decision['tasks'])
        if any(identifier not in indexed for identifier in decision['tasks']):
            raise ValueError('Decision references unknown task')
        missing = [identifier for identifier in decision['tasks'] if decision['id'] not in indexed[identifier]['patterns']]
        if missing:
            raise ValueError(f"Decision {decision['id']} lists tasks {decision['tasks']} but {missing} lack {decision['id']} in their patterns arrays; add the ID to those task.patterns or remove genuinely unused tasks from decision.tasks")
    for task in tasks:
        if any(identifier not in decision_ids for identifier in task['patterns']):
            raise ValueError('Task references unknown pattern decision')
        missing = [identifier for identifier in task['patterns'] if task['id'] not in next(d for d in decisions if d['id'] == identifier)['tasks']]
        if missing:
            raise ValueError(f"Task {task['id']} uses decisions {missing} but those decision.tasks arrays omit {task['id']}; repair the reciprocal task mapping")
    return data


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', '<br>')


def render(data):
    parts = ['# 任务输入输出与执行契约\n']
    for task in data['tasks']:
        parts += [f"## {task['id']} · {task['title']}\n", task['goal'] + '\n', '依赖：' + ('、'.join(task['depends_on']) or '无') + '\n',
                  '### 输入\n\n| 名称 | 类型 | 来源 | 必填 | 校验 |\n|---|---|---|---|---|']
        for value in task['inputs']:
            parts.append('| ' + ' | '.join(cell(value[k]) for k in ['name', 'type', 'source', 'required', 'validation']) + ' |')
        parts += ['\n### 输出\n\n| 名称 | 类型 | 去向 | 成功保证 |\n|---|---|---|---|']
        for value in task['outputs']:
            parts.append('| ' + ' | '.join(cell(value[k]) for k in ['name', 'type', 'destination', 'guarantee']) + ' |')
        for key, title in [('steps', '处理步骤'), ('acceptance', '验收条件'), ('tests', '测试场景')]:
            parts += [f'\n### {title}\n'] + [f'{i}. {value}' for i, value in enumerate(task[key], 1)]
        parts += ['\n### 异常、重试与幂等\n']
        for failure in task['failure_handling']:
            parts.append(f"- 场景：{failure['scenario']}；行为：{failure['behavior']}；重试：{failure['retry']}；幂等：{failure['idempotency']}")
        parts.append('\n设计决策：' + ('、'.join(task['patterns']) or '直接实现，无额外设计模式') + '\n')
    decisions = ['# 设计决策与模式选择\n']
    for decision in data['decisions']:
        decisions += [f"## {decision['id']} · {decision['pattern']}\n"]
        for key, title in [('problem', '解决的问题'), ('rationale', '为什么采用'), ('alternatives', '替代方案及取舍'), ('tradeoffs', '代价与适用边界'), ('implementation', '具体落点')]:
            decisions += [f'### {title}\n', decision[key] + '\n']
        decisions += ['关联任务：' + '、'.join(decision['tasks']) + '\n']
    if not data['decisions']:
        decisions.append('本方案采用直接实现；不为了模式而增加抽象。适用理由见设计正文。')
    return '\n'.join(parts), '\n'.join(decisions)


def write_bundle(raw, destination, level):
    if len(raw) > 350000:
        raise ValueError('Design output too large')
    raw = raw.strip()
    if raw.startswith('```'):
        match = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```', raw, re.S)
        if not match:
            raise ValueError('Expected one design JSON object')
        raw = match[1]
    data = validate(json.loads(raw), level)
    contracts, decisions = render(data)
    destination.mkdir(parents=True, exist_ok=True)
    title = '概要设计' if level == 'overview' else '详细设计'
    module_index = ''
    module_prose = ''
    if level == 'detailed':
        owners = {identifier: module['id'] for module in data['modules'] for identifier in module['task_ids']}
        module_index = '\n## 模块索引与依赖\n\n| 模块 | 职责与边界 | 任务 | 上游模块 |\n|---|---|---|---|\n'
        (destination / 'modules').mkdir()
        for module in data['modules']:
            deps = sorted({owners[dep] for task in data['tasks'] if task['id'] in module['task_ids'] for dep in task['depends_on'] if owners[dep] != module['id']})
            module_index += '| ' + ' | '.join(cell(v) for v in [f"[{module['id']} · {module['title']}](modules/{module['id']}.md)", module['responsibility'] + '；' + module['boundary'], '、'.join(module['task_ids']), '、'.join(deps) or '无']) + ' |\n'
            subset = {**data, 'tasks': [t for t in data['tasks'] if t['id'] in module['task_ids']], 'decisions': [d for d in data['decisions'] if set(d['tasks']) & set(module['task_ids'])]}
            module_contracts, module_decisions = render(subset)
            body = f"# {module['id']} · {module['title']}\n\n职责：{module['responsibility']}\n\n边界：{module['boundary']}\n\n上游模块：{'、'.join(deps) or '无'}\n\n{module['design_markdown']}\n\n{module_contracts}\n\n{module_decisions}"
            (destination / 'modules' / f"{module['id']}.md").write_text(body, encoding='utf-8')
            module_prose += f"\n\n## {module['id']} · {module['title']}\n\n{module['design_markdown']}"
        (destination / 'overview-update.md').write_text(data['overview_update_markdown'], encoding='utf-8')
    (destination / 'design.md').write_text(f'# {title}\n\n{data["summary_markdown"]}\n{module_index}\n{data["design_markdown"]}', encoding='utf-8')
    (destination / 'task-contracts.md').write_text(contracts, encoding='utf-8')
    (destination / 'decisions.md').write_text(decisions, encoding='utf-8')
    (destination / 'design.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    (destination / 'README.md').write_text('设计提案，尚未执行代码开发。design.md 为正文与模块索引，task-contracts.md 为逐任务输入输出及验收，decisions.md 为选择理由，design.json 为可校验契约。详细设计的 modules/ 为各模块独立文档，overview-update.md 为同步修订后的概要模块章节（未自动覆盖仓库文件）。\n', encoding='utf-8')
    overview = '\n\n' + data['overview_update_markdown'] if level == 'detailed' else ''
    issue_index = re.sub(r'\[([^\]]+)\]\(modules/MOD-\d{2,3}\.md\)', r'\1', module_index)
    return f'# {title}\n\n{data["summary_markdown"]}\n{issue_index}{overview}\n\n{data["design_markdown"]}{module_prose}\n\n{decisions}\n\n{contracts}'
