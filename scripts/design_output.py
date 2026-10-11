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


def validate_legacy(data, level):
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


def write_legacy_bundle(raw, destination, level):
    if len(raw) > 350000:
        raise ValueError('Design output too large')
    raw = raw.strip()
    if raw.startswith('```'):
        match = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```', raw, re.S)
        if not match:
            raise ValueError('Expected one design JSON object')
        raw = match[1]
    data = validate_legacy(json.loads(raw), level)
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

# V1 remains render-stable for already published immutable Wiki versions.
V2_MODULE = {'id', 'title', 'responsibility', 'boundary', 'design_markdown', 'interfaces_markdown', 'frontend', 'backend', 'documentation', 'tasks'}
V2_TASK = TASK | {'layer', 'milestone_id'}
MILESTONE = {'id', 'title', 'user_value', 'user_journey', 'depends_on', 'task_ids', 'integration_tests', 'release_criteria', 'release_plan', 'rollback_plan'}
PAGE = {'id', 'title', 'route', 'layout_markdown', 'user_actions', 'states', 'api_bindings', 'acceptance', 'prototype_reference'}
LAYERS = {'frontend', 'backend', 'integration', 'documentation'}


def normalize_wire(data):
    """Compile flat transport records to module-owned canonical V2; never infer ownership."""
    if not isinstance(data, dict) or 'task_records' not in data:
        return data
    fields = {'schema_version', 'level', 'summary_markdown', 'design_markdown', 'experience', 'milestones', 'modules', 'decisions', 'task_records', 'page_records'}
    if data.get('level') == 'detailed': fields.add('overview_update_markdown')
    if 'delivery' in data: fields.add('delivery')
    if set(data) != fields: raise ValueError('Wire fields must exactly match the supplied V2 transport schema')
    keys = {'id', 'title', 'responsibility', 'boundary', 'design_markdown', 'interfaces_markdown', 'frontend_applicable', 'frontend_reason', 'frontend_markdown', 'backend_applicable', 'backend_reason', 'backend_markdown', 'documentation_deliverables', 'documentation_acceptance'}
    if not isinstance(data['modules'], list) or not 1 <= len(data['modules']) <= 20: raise ValueError('Expected bounded modules')
    modules = {}
    for m in data['modules']:
        if not isinstance(m, dict): raise ValueError('Wire module must be an object')
        if set(m) != keys:
            raise ValueError(f"Wire module {m.get('id', '?')}: missing {sorted(keys - set(m))}; extra {sorted(set(m) - keys)}. Use the exact flat module fields from the complete wire example, not nested frontend/backend/documentation/tasks objects.")
        if not isinstance(m['id'], str) or m['id'] in modules: raise ValueError('Invalid wire module ID or duplicate ID')
        modules[m['id']] = {k: m[k] for k in ['id','title','responsibility','boundary','design_markdown','interfaces_markdown']} | {
            'frontend': {'applicable': m['frontend_applicable'], 'reason': m['frontend_reason'], 'design_markdown': m['frontend_markdown'], 'pages': []},
            'backend': {'applicable': m['backend_applicable'], 'reason': m['backend_reason'], 'design_markdown': m['backend_markdown']},
            'documentation': {'deliverables': m['documentation_deliverables'], 'acceptance': m['documentation_acceptance']}, 'tasks': []}
    for field, required, target, limit in [('task_records',V2_TASK,'tasks',30),('page_records',PAGE,'pages',40)]:
        records = data[field]
        if not isinstance(records,list) or len(records)>limit: raise ValueError('Invalid wire records')
        for record in records:
            if not isinstance(record,dict) or set(record) != required | {'module_id'} or not isinstance(record['module_id'],str) or record['module_id'] not in modules:
                raise ValueError('Wire record must explicitly reference one existing module_id')
            value = {k: record[k] for k in required}
            module = modules[record['module_id']]
            (module['tasks'] if target=='tasks' else module['frontend']['pages']).append(value)
    return {k:v for k,v in data.items() if k not in {'task_records','page_records','modules'}} | {'modules':list(modules.values())}


def validate_v2(data, level):
    fields = {'schema_version', 'level', 'summary_markdown', 'design_markdown', 'experience', 'milestones', 'modules', 'decisions'}
    if level == 'detailed': fields.add('overview_update_markdown')
    if isinstance(data, dict) and 'delivery' in data: fields.add('delivery')
    if not isinstance(data, dict) or set(data) != fields or type(data['schema_version']) is not int or data['schema_version'] != 2 or data['level'] != level:
        raise ValueError('V2 requires milestone-first, module-owned tasks; no top-level tasks')
    experience = data['experience']
    if not isinstance(experience, dict) or set(experience) != {'interaction_mode', 'rationale'} or experience['interaction_mode'] not in {'web', 'api', 'cli'}:
        raise ValueError('Explicit user interaction mode is required')
    text(experience['rationale'])
    if not isinstance(data['modules'], list) or not 1 <= len(data['modules']) <= 20:
        raise ValueError('Expected 1–20 responsibility-based modules')
    flat, legacy_modules, page_ids = [], [], set()
    for module in data['modules']:
        if not isinstance(module, dict) or set(module) != V2_MODULE:
            raise ValueError('V2 module must own frontend/backend/docs design and its tasks')
        text(module['interfaces_markdown'], 30000)
        frontend, backend, docs = module['frontend'], module['backend'], module['documentation']
        if not isinstance(frontend, dict) or set(frontend) != {'applicable', 'reason', 'design_markdown', 'pages'} or type(frontend['applicable']) is not bool:
            raise ValueError('Explicit frontend applicability and page contracts are required')
        text(frontend['reason']); text(frontend['design_markdown'], 30000)
        if not isinstance(frontend['pages'], list) or len(frontend['pages']) > 20 or bool(frontend['pages']) != frontend['applicable']:
            raise ValueError('Frontend pages must match applicability')
        for page in frontend['pages']:
            if not isinstance(page, dict) or set(page) != PAGE or not isinstance(page['id'], str) or not re.fullmatch(r'UI-\d{2,3}', page['id']) or page['id'] in page_ids:
                raise ValueError('Page IDs must be unique UI-01 identifiers')
            page_ids.add(page['id'])
            for key in ['title', 'route', 'layout_markdown', 'prototype_reference']: text(page[key])
            for key in ['user_actions', 'states', 'api_bindings', 'acceptance']: strings(page[key])
            if not {'loading', 'empty', 'error', 'success'} <= set(page['states']):
                raise ValueError('Every web page needs loading/empty/error/success states')
        if not isinstance(backend, dict) or set(backend) != {'applicable', 'reason', 'design_markdown'} or type(backend['applicable']) is not bool:
            raise ValueError('Explicit backend design is required')
        text(backend['reason']); text(backend['design_markdown'], 30000)
        if not isinstance(docs, dict) or set(docs) != {'deliverables', 'acceptance'}:
            raise ValueError('Module documentation deliverables and acceptance are required')
        strings(docs['deliverables']); strings(docs['acceptance'])
        if not isinstance(module['tasks'], list) or not module['tasks']:
            raise ValueError('Tasks must be nested in their owning module')
        for task in module['tasks']:
            if not isinstance(task, dict) or set(task) != V2_TASK or task['layer'] not in LAYERS:
                raise ValueError('Each task needs explicit layer and MVP milestone_id')
            if task['layer'] == 'frontend' and not frontend['applicable']:
                raise ValueError(f"{module['id']}/{task['id']}: frontend task requires this module frontend.applicable=true and actual page contracts; move the task to the UI module or supply its page design")
            if task['layer'] == 'backend' and not backend['applicable']:
                raise ValueError('Backend task requires applicable backend design in its module')
            flat.append(task)
        legacy_modules.append({k: module[k] for k in ['id', 'title', 'responsibility', 'boundary', 'design_markdown']} | {'task_ids': [t['id'] for t in module['tasks']]})
    # Reuse the proven IO/type/DAG/pattern validation without changing V1 rendering.
    legacy = {k: data[k] for k in ['level', 'summary_markdown', 'design_markdown', 'decisions']}
    legacy['tasks'] = [{k: t[k] for k in TASK} for t in flat]
    if level == 'detailed': legacy.update(modules=legacy_modules, overview_update_markdown=data['overview_update_markdown'])
    validate_legacy(legacy, level)
    if len({m['id'] for m in legacy_modules}) != len(legacy_modules): raise ValueError('Duplicate module ID')
    for m in legacy_modules:
        if not re.fullmatch(r'MOD-\d{2,3}', m['id']): raise ValueError('Invalid module ID')
        for key in ['title', 'responsibility', 'boundary']: text(m[key])
        text(m['design_markdown'], 30000)
    milestones = data['milestones']
    if not isinstance(milestones, list) or not 1 <= len(milestones) <= 10: raise ValueError('Expected 1–10 MVP milestones')
    tasks = {t['id']: t for t in flat}
    indexed, owned = {}, set()
    for milestone in milestones:
        if not isinstance(milestone, dict) or set(milestone) != MILESTONE or not re.fullmatch(r'MS-\d{2,3}', milestone['id']) or milestone['id'] in indexed:
            raise ValueError('Invalid or duplicate milestone')
        indexed[milestone['id']] = milestone
        for key in ['title', 'user_value', 'release_plan', 'rollback_plan']: text(milestone[key])
        for key in ['user_journey', 'task_ids', 'release_criteria']: strings(milestone[key])
        strings(milestone['depends_on'], required=False)
        for identifier in milestone['task_ids']:
            if identifier not in tasks or identifier in owned or tasks[identifier]['milestone_id'] != milestone['id']:
                raise ValueError('Every task must belong to exactly one consistent milestone')
            owned.add(identifier)
        layers = {tasks[t]['layer'] for t in milestone['task_ids']}
        needed = {'backend', 'integration', 'documentation'} | ({'frontend'} if experience['interaction_mode'] == 'web' else set())
        if not needed <= layers: raise ValueError(f"{milestone['id']}: MVP release must include {sorted(needed)} tasks, got {sorted(layers)}")
        tests = milestone['integration_tests']
        if not isinstance(tests, list) or not tests: raise ValueError('Milestone integration tests are required')
        for test in tests:
            if not isinstance(test, dict) or set(test) != {'scenario', 'preconditions', 'steps', 'expected'}: raise ValueError('Invalid milestone integration test')
            text(test['scenario']); strings(test['preconditions']); strings(test['steps']); strings(test['expected'])
    if owned != set(tasks): raise ValueError('Unassigned milestone tasks')
    done, active = set(), set()
    def visit(mid):
        if mid in active: raise ValueError('Cyclic milestone dependency')
        if mid in done: return
        active.add(mid)
        deps = indexed[mid]['depends_on']
        if len(deps) != len(set(deps)): raise ValueError('Duplicate milestone dependency')
        for dep in deps:
            if dep not in indexed: raise ValueError('Unknown milestone dependency')
            visit(dep)
        active.remove(mid); done.add(mid)
    for mid in indexed: visit(mid)
    def ancestors(mid):
        result = set(indexed[mid]['depends_on'])
        for dep in list(result): result |= ancestors(dep)
        return result
    for task in flat:
        allowed = ancestors(task['milestone_id']) | {task['milestone_id']}
        if any(tasks[dep]['milestone_id'] not in allowed for dep in task['depends_on']):
            raise ValueError('Task cannot depend on a future/unrelated milestone')
    if experience['interaction_mode'] == 'web' and not page_ids: raise ValueError('Interactive web MVP requires page design')
    return data


def validate(data, level):
    return validate_v2(normalize_wire(data), level) if isinstance(data, dict) and 'schema_version' in data else validate_legacy(data, level)


def render_milestones(data):
    parts = ['# MVP 里程碑与集成发布\n', '交付单位是可交互的里程碑；模块内任务是实现单元，单任务完成不代表 MVP 已验收或发布。\n']
    for m in data['milestones']:
        parts += [f"## {m['id']} · {m['title']}\n", '用户价值：' + m['user_value'], '\n前置里程碑：' + ('、'.join(m['depends_on']) or '无'), '\n### 用户操作闭环\n']
        parts += [f'{i}. {s}' for i, s in enumerate(m['user_journey'], 1)]
        parts += ['\n### 跨模块交付任务\n\n| 模块 | 任务 | 层次 | 目标 |\n|---|---|---|---|']
        for module in data['modules']:
            for task in module['tasks']:
                if task['milestone_id'] == m['id']:
                    parts.append('| ' + ' | '.join(cell(v) for v in [module['id'], task['id'], task['layer'], task['goal']]) + ' |')
        for test in m['integration_tests']:
            parts += ['\n### 集成验收：' + test['scenario'], '\n前置条件：' + '；'.join(test['preconditions']), '\n操作：']
            parts += [f'{i}. {s}' for i, s in enumerate(test['steps'], 1)]
            parts += ['\n预期：'] + ['- ' + s for s in test['expected']]
        parts += ['\n### 发布门槛\n'] + ['- ' + s for s in m['release_criteria']]
        parts += ['\n### 发布方案\n', m['release_plan'], '\n### 回滚方案\n', m['rollback_plan'], '\n']
    return '\n'.join(parts)


def render_frontend(module):
    f = module['frontend']
    parts = ['## 前端与界面设计\n', f['reason'], f['design_markdown']]
    for page in f['pages']:
        parts += [f"\n### {page['id']} · {page['title']}\n", '路由：' + page['route'], '\n布局与组件：\n' + page['layout_markdown'], '\n原型依据：' + page['prototype_reference']]
        for key, heading in [('user_actions', '操作与数据流'), ('states', '界面状态'), ('api_bindings', 'API/任务契约映射'), ('acceptance', '界面验收')]:
            parts += ['\n#### ' + heading + '\n'] + ['- ' + s for s in page[key]]
    return '\n'.join(parts)


def write_v2_bundle(data, destination, level):
    validate_v2(data, level)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'modules').mkdir(exist_ok=True)
    all_tasks = [t for m in data['modules'] for t in m['tasks']]
    owners = {t['id']: m['id'] for m in data['modules'] for t in m['tasks']}
    title = '概要设计' if level == 'overview' else '详细设计'
    index = '## 模块导航\n\n| 模块 | 职责与边界 | 涉及里程碑 | 上游模块 |\n|---|---|---|---|\n'
    module_summaries = []
    ui = ['# 界面与交互设计\n']
    documentation = ['# 文档交付与验收\n']
    task_index = ['# 任务索引（按模块）\n\n逐任务完整契约在所属模块中；里程碑是集成验收与发布单位。\n']
    for module in data['modules']:
        deps = sorted({owners[dep] for t in module['tasks'] for dep in t['depends_on'] if owners[dep] != module['id']})
        mids = sorted({t['milestone_id'] for t in module['tasks']})
        index += '| ' + ' | '.join(cell(v) for v in [f"[{module['id']} · {module['title']}](modules/{module['id']}.md)", module['responsibility'] + '；' + module['boundary'], '、'.join(mids), '、'.join(deps) or '无']) + ' |\n'
        contracts, decisions = render({'tasks': module['tasks'], 'decisions': [d for d in data['decisions'] if set(d['tasks']) & {t['id'] for t in module['tasks']}]})
        frontend = render_frontend(module)
        docs = '\n'.join(['## 文档交付\n'] + ['- ' + s for s in module['documentation']['deliverables']] + ['\n验收：'] + ['- ' + s for s in module['documentation']['acceptance']])
        body = f"# {module['id']} · {module['title']}\n\n职责：{module['responsibility']}\n\n边界：{module['boundary']}\n\n里程碑：{'、'.join(mids)}\n\n上游模块：{'、'.join(deps) or '无'}\n\n## 模块整体设计\n\n{module['design_markdown']}\n\n{frontend}\n\n## 后端设计\n\n{module['backend']['reason']}\n\n{module['backend']['design_markdown']}\n\n## 前后端与跨模块契约\n\n{module['interfaces_markdown']}\n\n{docs}\n\n## 模块内任务\n\n"
        # Task ownership and milestone/layer headings accompany the detailed contracts.
        body += '\n'.join(f"- {t['id']}：{t['title']}；{t['layer']}；{t['milestone_id']}" for t in module['tasks']) + '\n\n' + contracts + '\n\n' + decisions
        (destination / 'modules' / (module['id'] + '.md')).write_text(body, encoding='utf-8')
        ui += [f"\n## {module['id']} · {module['title']}\n", frontend]
        documentation += [f"\n## {module['id']} · {module['title']}\n", docs]
        task_index += [f"\n## [{module['id']} · {module['title']}](modules/{module['id']}.md)\n", '| 任务 | 层次 | MVP 里程碑 | 依赖 |\n|---|---|---|---|']
        task_index += ['| ' + ' | '.join(cell(v) for v in [t['id'] + ' · ' + t['title'], t['layer'], t['milestone_id'], '、'.join(t['depends_on']) or '无']) + ' |' for t in module['tasks']]
        module_summaries.append(f"### {module['id']} · {module['title']}\n\n{module['responsibility']}；{module['boundary']}")
    milestone_index = '## MVP 里程碑\n\n' + '\n'.join(f"- {m['id']} · {m['title']}：{m['user_value']}" for m in data['milestones'])
    nav = '## 阅读导航\n\n- [MVP 里程碑、集成验收与发布](milestones.md)\n- [界面与交互](ui.md)\n- [文档交付](documentation.md)\n- [按模块的任务索引](task-contracts.md)\n- [设计决策](decisions.md)\n'
    if level == 'detailed': nav += '- [同步后的概要模块章节](overview-update.md)\n'
    root = f'# {title}\n\n{data["summary_markdown"]}\n\n{milestone_index}\n\n{index}\n\n## 跨模块总体设计\n\n{data["design_markdown"]}\n\n{nav}'
    _, decisions = render({'tasks': all_tasks, 'decisions': data['decisions']})
    outputs = {'design.md': root, 'milestones.md': render_milestones(data), 'ui.md': '\n'.join(ui), 'documentation.md': '\n'.join(documentation), 'task-contracts.md': '\n'.join(task_index), 'decisions.md': decisions, 'design.json': json.dumps(data, ensure_ascii=False, indent=2), 'README.md': '设计提案。阅读顺序：design.md → milestones.md → modules/MOD-xx.md → 模块内任务。ui.md 和 documentation.md 汇总界面及文档交付。开发、测试及发布尚未执行。\n'}
    if level == 'detailed': outputs['overview-update.md'] = data['overview_update_markdown']
    for name, body in outputs.items(): (destination / name).write_text(body, encoding='utf-8')
    if 'delivery' in data:
        from design_delivery import validate_delivery, write_delivery
        validate_delivery(data)
        write_delivery(data, destination)
    # Issue feedback introduces the whole plan; detailed contracts stay in modules/Wiki.
    return re.sub(r'\[([^\]]+)\]\((?:modules/)?[^)]+\.md\)', r'\1', root) + '\n\n' + render_milestones(data) + '\n\n' + '\n\n'.join(module_summaries)


def write_bundle(raw, destination, level, require_current=False):
    if len(raw) > 350000: raise ValueError('Design output too large')
    cleaned = raw.strip()
    if cleaned.startswith('```'):
        match = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```', cleaned, re.S)
        if not match: raise ValueError('Expected one design JSON object')
        cleaned = match[1]
    data = json.loads(cleaned)
    if require_current and (not isinstance(data, dict) or data.get('schema_version') != 2):
        raise ValueError('New designs must use schema_version=2, milestones and module-owned tasks; V1 is only for historical Wiki artifacts')
    if isinstance(data, dict) and 'schema_version' in data:
        data = normalize_wire(data)
        from design_delivery import validate_delivery
        validate_delivery(data, required=require_current)
        return write_v2_bundle(data, destination, level)
    return write_legacy_bundle(raw, destination, level)
