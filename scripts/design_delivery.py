"""Structured HTTP contracts, UI bindings and offline prototype delivery."""
import json
import re
from prototype_output import write_bundle as prototype_bundle


def fail(message):
    raise ValueError('Design delivery: ' + message)


def schema_check(schema, example, where='schema', depth=0):
    if depth > 12 or not isinstance(schema, dict): fail(where + ': invalid schema')
    allowed={'type','properties','required','additionalProperties','items','enum','minimum','maximum','minLength','maxLength','format','description','default','pattern','minItems','maxItems'}
    if set(schema)-allowed: fail(where + ': unsupported schema fields')
    types=schema.get('type'); types=[types] if isinstance(types,str) else types
    if not isinstance(types,list) or not types or set(types)-{'object','array','string','integer','number','boolean','null'}: fail(where+': explicit type required')
    matches={'null':example is None,'object':isinstance(example,dict),'array':isinstance(example,list),'string':isinstance(example,str),'integer':type(example) is int,'number':type(example) in {int,float},'boolean':type(example) is bool}
    if not any(matches[t] for t in types): fail(where+': example type mismatch')
    for key in ['minimum','maximum']:
        if key in schema and type(schema[key]) not in {int,float}: fail(where+': invalid numeric bound')
    for key in ['minLength','maxLength','minItems','maxItems']:
        if key in schema and (type(schema[key]) is not int or schema[key]<0): fail(where+': invalid nonnegative bound')
    if 'enum' in schema and (not isinstance(schema['enum'],list) or not schema['enum']): fail(where+': enum must be nonempty')
    if 'enum' in schema and example not in schema['enum']: fail(where+': example outside enum')
    if type(example) in {int,float}:
        if 'minimum' in schema and example < schema['minimum']: fail(where+': below minimum')
        if 'maximum' in schema and example > schema['maximum']: fail(where+': above maximum')
    if isinstance(example,str):
        if 'pattern' in schema:
            try: matched=re.search(schema['pattern'],example)
            except (re.error,TypeError): fail(where+': invalid pattern')
            if not matched: fail(where+': example mismatches pattern')
        if len(example)<schema.get('minLength',0) or len(example)>schema.get('maxLength',100000): fail(where+': invalid length')
        if schema.get('format')=='uuid' and not re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',example): fail(where+': invalid UUID example')
    if 'object' in types:
        props=schema.get('properties'); required=schema.get('required')
        if not isinstance(props,dict) or not isinstance(required,list) or len(required)!=len(set(required)) or set(required)-set(props) or schema.get('additionalProperties') is not False: fail(where+': object needs properties, required and additionalProperties=false')
        if isinstance(example,dict):
            if set(required)-set(example) or set(example)-set(props): fail(where+': example misses required or has unknown fields')
            # Require an example for every field, including optional fields, to validate all nested schema declarations.
            if set(props)-set(example): fail(where+': example must demonstrate every property')
            for k,v in props.items(): schema_check(v,example[k],where+'.'+k,depth+1)
        elif example is None and props: fail(where+': object example must demonstrate fields')
    if 'array' in types:
        if 'items' not in schema: fail(where+': array items type required')
        if isinstance(example,list):
            if len(example)<schema.get('minItems',0) or len(example)>schema.get('maxItems',100000): fail(where+': invalid array length')
            if not example: fail(where+': array example must show an item')
            for v in example: schema_check(schema['items'],v,where+'[]',depth+1)


def field_schema(schema,path):
    for token in path.replace('[]','.*').split('.'):
        if token=='*': schema=schema.get('items',{})
        else: schema=schema.get('properties',{}).get(token,{})
        if not schema: fail('unknown mapped field '+path)
    return schema


def validate_delivery(data, required=False):
    delivery=data.get('delivery')
    if delivery is None:
        if required and data['experience']['interaction_mode']=='web': fail('web designs require structured apis, bindings and prototype_html')
        return
    if not isinstance(delivery,dict) or set(delivery) not in ({'apis','bindings','prototype_html'}, {'apis','bindings','channels','prototype_html'}): fail('delivery must contain apis/bindings/prototype_html and optionally typed channels')
    apis=delivery['apis']; bindings=delivery['bindings']
    if not isinstance(apis,list) or len(apis)>30 or not isinstance(bindings,list) or len(bindings)>60: fail('bounded APIs and bindings required')
    if bool(apis)!=bool(bindings): fail('HTTP APIs require HTTP bindings and vice versa')
    channels=delivery.get('channels',[])
    if not isinstance(channels,list) or len(channels)>30: fail('bounded typed channels required')
    if not apis and not channels: fail('at least one HTTP API or typed IPC channel required')
    modules={m['id']:m for m in data['modules']}; tasks={t['id']:(m['id'],t) for m in data['modules'] for t in m['tasks']}; pages={p['id'] for m in data['modules'] for p in m['frontend']['pages']}; ids={}; routes=set()
    for a in apis:
        if set(a)!={'id','module_id','task_id','method','path','title','auth','request','request_example','responses'} or not re.fullmatch(r'API-\d{2,3}',a['id']) or a['id'] in ids: fail('API identity/fields invalid')
        if a['method'] not in {'GET','POST','PUT','PATCH','DELETE'} or not a['path'].startswith('/api/') or '?' in a['path'] or (a['method'],a['path']) in routes: fail('unique HTTP method/path required')
        if a['module_id'] not in modules or a['task_id'] not in tasks or tasks[a['task_id']][0]!=a['module_id'] or tasks[a['task_id']][1]['layer']!='backend': fail(a['id']+': owner must be a backend task in the module')
        if not all(isinstance(a[k],str) and a[k].strip() for k in ['title','auth']): fail('API title/auth required')
        if set(a['request'])!={'path','query','body'} or set(a['request_example'])!={'path','query','body'}: fail('request path/query/body schemas and examples required')
        for k in ['path','query','body']: schema_check(a['request'][k],a['request_example'][k],a['id']+'.request.'+k)
        if set(re.findall(r'\{([A-Za-z][A-Za-z0-9_]*)\}',a['path'])) != set(a['request']['path'].get('required',[])): fail(a['id']+': path placeholders must match required path fields')
        if not isinstance(a['responses'],list) or not a['responses'] or len(a['responses'])>12: fail('responses required')
        statuses=set()
        for r in a['responses']:
            if set(r)!={'status','description','schema','example'} or type(r['status']) is not int or not 200<=r['status']<=599 or r['status'] in statuses or not r['description'].strip(): fail('response status/description invalid')
            schema_check(r['schema'],r['example'],a['id']+'.response.'+str(r['status'])); statuses.add(r['status'])
        if not any(200<=s<300 for s in statuses) or not any(s>=400 for s in statuses): fail(a['id']+': success and error responses required')
        ids[a['id']]=a; routes.add((a['method'],a['path']))
    used=set(); bound_pages=set(); binding_ids=set()
    for b in bindings:
        if set(b)!={'id','page_id','action','api_id','response_status','request_mapping','response_mapping','loading_behavior','error_behavior','success_behavior'} or b['id'] in binding_ids or not re.fullmatch(r'BIND-\d{2,3}',b['id']): fail('binding identity/fields invalid')
        if b['page_id'] not in pages or b['api_id'] not in ids: fail('binding must reference real page/API')
        a=ids[b['api_id']]; r=next((r for r in a['responses'] if r['status']==b['response_status']),None)
        if r is None or not 200<=r['status']<300: fail('binding must select a declared success response')
        targets=set()
        for mapping in b['request_mapping']:
            if set(mapping)!={'target','source'} or not mapping['source'].strip(): fail('request mapping needs source/target')
            location,sep,path=mapping['target'].partition('.')
            if not sep or location not in a['request']: fail('request target must be path/query/body.field')
            field_schema(a['request'][location],path); targets.add(mapping['target'])
        for location,s in a['request'].items():
            if any(location+'.'+k not in targets for k in s.get('required',[])): fail(b['id']+': required request fields unmapped')
        if not b['response_mapping']: fail('response field mappings required')
        for mapping in b['response_mapping']:
            if set(mapping)!={'source','target'} or not mapping['target'].strip(): fail('response mapping source/target required')
            field_schema(r['schema'],mapping['source'])
        for k in ['action','loading_behavior','error_behavior','success_behavior']:
            if not isinstance(b[k],str) or not b[k].strip(): fail('binding behavior required')
        used.add(b['api_id']); bound_pages.add(b['page_id']); binding_ids.add(b['id'])
    if used!=set(ids): fail('every public HTTP API must have bindings')
    channel_ids=set(); channel_pages=set()
    for c in channels:
        keys={'id','module_id','task_id','transport','command','request','request_example','response','response_example','error','error_example','bindings'}
        if not isinstance(c,dict) or set(c)!=keys or not isinstance(c['id'],str) or not re.fullmatch(r'IPC-\\d{2,3}',c['id']) or c['id'] in channel_ids: fail('typed IPC identity/fields invalid')
        if c['transport'] not in {'vscode-webview','vscode-command','acp','process-stdio','ipc'}: fail(c['id']+': unsupported IPC transport')
        if not isinstance(c['command'],str) or not c['command'].strip(): fail(c['id']+': command/event name required')
        if c['module_id'] not in modules or c['task_id'] not in tasks or tasks[c['task_id']][0]!=c['module_id']: fail(c['id']+': channel owner task/module invalid')
        for field in ('request','response','error'):
            schema_check(c[field],c[field+'_example'],c['id']+'.'+field)
        if not isinstance(c['bindings'],list) or not c['bindings']: fail(c['id']+': page/action bindings required')
        for b in c['bindings']:
            keys={'page_id','action','request_mapping','response_mapping','loading_behavior','error_behavior','success_behavior'}
            if not isinstance(b,dict) or set(b)!=keys or b['page_id'] not in pages: fail(c['id']+': page/action binding invalid')
            if not isinstance(b['request_mapping'],list) or not isinstance(b['response_mapping'],list) or not b['response_mapping']: fail(c['id']+': field mapping required')
            for mapping in b['request_mapping']:
                if not isinstance(mapping,dict) or set(mapping)!={'source','target'} or not isinstance(mapping['source'],str) or not mapping['source'].strip(): fail('IPC request mapping fields invalid')
                field_schema(c['request'],mapping['target'])
            for mapping in b['response_mapping']:
                if not isinstance(mapping,dict) or set(mapping)!={'source','target'} or not isinstance(mapping['target'],str) or not mapping['target'].strip(): fail('IPC response mapping fields invalid')
                field_schema(c['response'],mapping['source'])
            for field in ('action','loading_behavior','error_behavior','success_behavior'):
                if not isinstance(b[field],str) or not b[field].strip(): fail('IPC binding behavior required')
            channel_pages.add(b['page_id'])
        channel_ids.add(c['id'])
    if bound_pages | channel_pages != pages: fail('every page must be bound to HTTP or typed IPC')
    if not isinstance(delivery['prototype_html'],str) or len(delivery['prototype_html'])<500: fail('complete offline HTML prototype required')


def schema_table(s,prefix='',required=True):
    rows=[]
    types=s['type']; types=[types] if isinstance(types,str) else types
    if prefix:
        constraints={k:v for k,v in s.items() if k not in {'properties','items','required','additionalProperties','type'}}
        rows.append('| '+prefix+' | '+','.join(types)+' | '+('是' if required else '否')+' | '+('是' if 'null' in types else '否')+' | '+json.dumps(constraints,ensure_ascii=False).replace('|','\\|')+' |')
    if 'object' in types:
        for k,v in s['properties'].items(): rows+=schema_table(v,(prefix+'.' if prefix else '')+k,k in s['required'])
    if 'array' in types: rows+=schema_table(s['items'],prefix+'[]',True)
    return rows


def table(s):
    return '\n'.join(['| 字段 | 类型 | 必填 | 可空 | 约束与说明 |','|---|---|---|---|---|']+schema_table(s))


def json_block(value):
    return '```json\n'+json.dumps(value,ensure_ascii=False,indent=2)+'\n```'


def write_delivery(data,destination):
    delivery=data['delivery']; api_index=['# HTTP 接口契约\n\n每个接口独立成页；表格是字段契约，JSON 是合法示例。\n']; bindings=['# 页面操作与后端接口映射\n']; module_api={m['id']:[] for m in data['modules']}
    (destination/'apis').mkdir(exist_ok=True)
    apis={a['id']:a for a in delivery['apis']}
    for a in apis.values():
        link=f"[{a['id']} · {a['method']} {a['path']}](apis/{a['id']}.md)"; api_index.append('- '+link);module_api[a['module_id']].append('- '+link)
        p=[f"# {a['id']} · {a['title']}\n",f"**{a['method']} `{a['path']}`**\n",f"后端模块：[{a['module_id']}](modules/{a['module_id']}.md)；实现任务：{a['task_id']}\n",'权限：'+a['auth']]
        for k,label in [('path','路径参数'),('query','查询参数'),('body','请求体')]:p+=['\n## '+label+'\n',table(a['request'][k]),'\n示例：\n',json_block(a['request_example'][k])]
        for r in a['responses']:p+=['\n## 响应 '+str(r['status'])+' · '+r['description']+'\n',table(r['schema']),'\n示例：\n',json_block(r['example'])]
        (destination/'apis'/(a['id']+'.md')).write_text('\n\n'.join(p))
    for b in delivery['bindings']:
        a=apis[b['api_id']]; bindings += [f"\n## {b['page_id']} · {b['action']}\n",f"调用 [{a['id']} · {a['method']} {a['path']}](apis/{a['id']}.md)；后端 [{a['module_id']}](modules/{a['module_id']}.md) / {a['task_id']}；成功响应 {b['response_status']}。",'\n### 请求赋值\n','| 后端参数 | 前端来源 |\n|---|---|']
        bindings += ['| '+m['target']+' | '+m['source']+' |' for m in b['request_mapping']] or ['无请求参数。']
        bindings += ['\n### 返回值消费\n','| 返回字段 | 前端控件或状态 |\n|---|---|']+['| '+m['source']+' | '+m['target']+' |' for m in b['response_mapping']]
        bindings += ['\n加载：'+b['loading_behavior'],'\n成功：'+b['success_behavior'],'\n错误：'+b['error_behavior']]
    for c in delivery.get('channels',[]):
        api_index.append('- ['+c['id']+' · '+c['transport']+' · '+c['command']+'](ipc-contracts.md)')
        module_api[c['module_id']].append('- ['+c['id']+' · '+c['command']+'](ipc-contracts.md)')
        bindings.append('\n## '+c['id']+' · '+c['command']+' ('+c['transport']+')')
        for b in c['bindings']:
            bindings.append('\n### '+b['page_id']+' · '+b['action'])
            bindings.append('请求映射：'+json.dumps(b['request_mapping'],ensure_ascii=False))
            bindings.append('响应映射：'+json.dumps(b['response_mapping'],ensure_ascii=False))
            bindings.extend([b['loading_behavior'],b['success_behavior'],b['error_behavior']])
    (destination/'ipc-contracts.md').write_text('# IPC / ACP 消息契约\n\n'+'\n\n'.join('## '+c['id']+' · '+c['command']+' ('+c['transport']+')\n\n处理模块 '+c['module_id']+' / '+c['task_id']+'\n\n'+ '\n\n'.join('### '+field+'\n\n'+table(c[field])+'\n\n'+json_block(c[field+'_example']) for field in ('request','response','error')) for c in delivery.get('channels',[])))
    (destination/'api-contracts.md').write_text('\n\n'.join(api_index));(destination/'frontend-bindings.md').write_text('\n'.join(bindings))
    for m in data['modules']:
        p=destination/'modules'/(m['id']+'.md');body=p.read_text(); old=m['interfaces_markdown'];new='\n\n'.join(module_api[m['id']])+'\n\n[完整接口目录](../api-contracts.md) · [页面参数映射](../frontend-bindings.md)\n\n### 内部程序接口\n\n'+old
        # Root-relative links are used throughout this bundle and rewritten by the Wiki publisher.
        new=new.replace('../api-contracts.md','api-contracts.md').replace('../frontend-bindings.md','frontend-bindings.md')
        body=body.replace(old,new);p.write_text(body)
    links='\n\n[逐接口契约](api-contracts.md) · [页面请求与响应映射](frontend-bindings.md)\n'
    for n in ['design.md','ui.md']:
        p=destination/n;p.write_text(p.read_text()+links)
    prototype_bundle(json.dumps({'needs_prototype':True,'decision_reason':'Web 设计必须交付同轮可运行原型','requirements_markdown':data['summary_markdown'],'design_markdown':'原型依据同轮页面与接口契约，使用模拟数据；实际业务后端尚未开发。','prototype_html':delivery['prototype_html']}),destination.parent/'prototype')
