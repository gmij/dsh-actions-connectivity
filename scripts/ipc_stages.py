"""Granular IPC design: index once, validate each immutable channel checkpoint.

The aggregated stage-channels.json remains the canonical V2 wire contract.
A bad IPC only retries its own output, never other validated IPCs.
"""
import json
import re
from pathlib import Path
from design_delivery import validate_ipc_channel

TRANSPORTS = {"vscode-webview", "vscode-command", "acp", "process-stdio", "ipc"}
INDEX_FIELDS = {"id", "module_id", "task_id", "transport", "command", "page_ids"}

def parse(text):
    text=text.strip()
    fence=re.fullmatch(r"```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n```",text,re.I)
    return json.loads(fence.group(1).strip() if fence else text)

def index_context(done):
    modules=[{"id":m["id"],"title":m["title"],"interfaces":str(m.get("interfaces_markdown",""))[:800]}
             for m in done.get("modules",[])]
    tasks=[{"id":t["id"],"module_id":t["module_id"],"title":t["title"],"layer":t["layer"]}
           for t in done.get("task_records",[])]
    pages=[{"id":p["id"],"module_id":p["module_id"],"title":p["title"],
            "actions":p.get("user_actions",[])[:10]}
           for p in done.get("page_records",[])]
    return {"modules":modules,"tasks":tasks,"pages":pages}

def validate_index(items,done):
    if not isinstance(items,list) or not 1<=len(items)<=30:
        raise ValueError("IPC index: expected 1 to 30 channels")
    expected=index_context(done)
    modules={m["id"] for m in expected["modules"]}
    tasks={t["id"]:t["module_id"] for t in expected["tasks"]}
    pages={p["id"] for p in expected["pages"]}
    ids=set();covered=set()
    for i,item in enumerate(items):
        if not isinstance(item,dict) or set(item)!=INDEX_FIELDS:
            raise ValueError(f"IPC index row {i}: expected {sorted(INDEX_FIELDS)}")
        ident=item["id"]
        if not isinstance(ident,str) or not re.fullmatch(r"IPC-\d{2,3}",ident) or ident in ids:
            raise ValueError(f"IPC index: invalid or duplicate id {ident!r}")
        if item["module_id"] not in modules or tasks.get(item["task_id"])!=item["module_id"]:
            raise ValueError(f"{ident}: task/module ownership mismatch")
        if item["transport"] not in TRANSPORTS or not isinstance(item["command"],str) or not item["command"].strip():
            raise ValueError(f"{ident}: invalid transport or command")
        target=item["page_ids"]
        if not isinstance(target,list) or not target or any(p not in pages for p in target) or len(target)!=len(set(target)):
            raise ValueError(f"{ident}: page references invalid")
        ids.add(ident);covered.update(target)
    if covered!=pages:
        raise ValueError(f"IPC index: unmapped pages {sorted(pages-covered)}, extra {sorted(covered-pages)}")

def validate_one(channel, spec, done):
    if not isinstance(channel,dict):
        raise ValueError(f"{spec['id']}: channel must be an object")
    for key in ("id","module_id","task_id","transport","command"):
        if channel.get(key)!=spec[key]:
            raise ValueError(f"{spec['id']}: {key} changed from channel index")
    modules={m["id"]:m for m in done["modules"]}
    tasks={t["id"]:(t["module_id"],t) for t in done["task_records"]}
    pages={p["id"] for p in done["page_records"]}
    bound=validate_ipc_channel(channel,modules,tasks,pages)
    if bound != set(spec["page_ids"]):
        raise ValueError(f"{spec['id']}: bound pages {sorted(bound)} differ from manifest {spec['page_ids']}")

def prompt_for_index(original,done):
    return (original[:16000]+
      "\n\n【IPC 拆分索引阶段】仅输出 JSON object：{\"channels\":[{\"id\":\"IPC-01\","
      "\"module_id\":\"MOD-01\",\"task_id\":\"TASK-01\",\"transport\":\"vscode-webview\","
      "\"command\":\"chat.send\",\"page_ids\":[\"UI-01\"]}]}。"
      "\n仅列通道身份和页面绑定，不输出任何 JSON Schema、字段或实现。"
      "\n每种异构 Host→Webview 事件单独使用 IPC ID，避免巨大复合事件 schema。"
      "\n遵循真实 ACP/VS Code 协议，禁止捏造 HTTP API。至少覆盖每个 UI 页面。"
      "\n所有通道必须是本 MVP 所需；最多 30 个。对象字段只能是 id/module_id/task_id/transport/command/page_ids。"
      "\n当前模块/任务/页面标识及操作："+json.dumps(index_context(done),ensure_ascii=False)+
      "\n现在输出索引 JSON。")

def prompt_for_channel(original,done,index,item):
    context=index_context(done)
    context["modules"]=[m for m in context["modules"] if m["id"]==item["module_id"]]
    context["tasks"]=[t for t in context["tasks"] if t["id"]==item["task_id"]]
    context["pages"]=[p for p in context["pages"] if p["id"] in item["page_ids"]]
    return (original[:16000]+
     "\n\n【IPC 单通道精确生成】只能输出 {\"channel\":{...}}，不得输出 channels 数组、其他 IPC 或文字。"
     "\n此 IPC 的身份字段 id/module_id/task_id/transport/command 严格照清单，不得改变。"
     "\nchannel 必须且只能包含 id/module_id/task_id/transport/command/"
     "request/request_example/response/response_example/error/error_example/bindings。"
     "\nrequest/response/error 都使用内联 JSON Schema（type、properties、required、additionalProperties=false、items 等），"
     "每个 example 与 Schema 严格吻合，数组必须有非空示例；不能使用 $ref、oneOf、anyOf。"
     "\nbindings 每项只包含 page_id/action/request_mapping/response_mapping/loading_behavior/error_behavior/success_behavior，"
     "每个页面动作的 source/target 必须匹配已定义字段。"
     "\n对于单向 Host→Webview 事件，request 是事件数据，response={\"type\":\"null\"}、response_example=null，"
     "UI response_mapping.source 必须指向 request 中的字段。普通请求响应则指向 response 中的字段。"
     "\n仅本通道的目标和上下文："+json.dumps({"item":item,"context":context},ensure_ascii=False)+
     "\n其他通道仅用于去重（不得重复它们的内容）："+
     json.dumps([{"id":i["id"],"command":i["command"]} for i in index if i["id"]!=item["id"]],ensure_ascii=False)+
     "\n现在只输出本 IPC 的完整 JSON。")

def generate_channels(original,done,out_dir,invoke):
    out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    manifest=out/"stage-channels-index.json"
    metrics={"mode":"granular","index_reused":manifest.exists(),"channels":[]}
    if manifest.exists():
        parsed=json.loads(manifest.read_text())
    else:
        prompt=prompt_for_index(original,done)
        parsed=parse(invoke(prompt,"channels-index"))
        metrics["index_prompt_chars"]=len(prompt)
    if not isinstance(parsed,dict) or set(parsed)!={"channels"}:
        raise ValueError("IPC index: expected only channels field")
    index=parsed["channels"]
    validate_index(index,done)
    if not manifest.exists():
        manifest.write_text(json.dumps(parsed,ensure_ascii=False,indent=2))
    result=[]
    for spec in index:
        filename=out/("stage-channel-"+spec["id"]+".json")
        reused=filename.exists()
        info={"id":spec["id"],"reused":reused}
        if reused:
            fragment=json.loads(filename.read_text())
        else:
            prompt=prompt_for_channel(original,done,index,spec)
            info["prompt_chars"]=len(prompt)
            value=invoke(prompt,"channels-"+spec["id"])
            info["response_chars"]=len(value)
            try:
                fragment=parse(value)
            except (ValueError,TypeError) as ex:
                fragment=None
                problem=str(ex)
            else:
                problem=None
            if problem is None:
                try:
                    if not isinstance(fragment,dict) or set(fragment)!={"channel"}:
                        raise ValueError("Expected only channel object")
                    validate_one(fragment["channel"],spec,done)
                except (ValueError,KeyError,TypeError) as ex:
                    problem=str(ex)
            if problem is not None:
                # Only this IPC is retried. Do not re-feed other bulky channels.
                repair=(prompt+"\n[仅修正当前 "+spec["id"]+"；不能修改清单或别的 IPC]\n"
                        +"可信校验错误："+problem+"\n上次输出前 16000 字符：\n"+value[:16000]
                        +"\n再次输出严格的 {\"channel\":{...}} JSON。")
                info["repair_prompt_chars"]=len(repair)
                fragment=parse(invoke(repair,"channels-"+spec["id"]+"-repair"))
        if not isinstance(fragment,dict) or set(fragment)!={"channel"}:
            raise ValueError(f"{spec['id']}: invalid channel envelope")
        validate_one(fragment["channel"],spec,done)
        if not reused:
            filename.write_text(json.dumps(fragment,ensure_ascii=False,indent=2))
        info["checkpoint_chars"]=len(json.dumps(fragment,ensure_ascii=False))
        metrics["channels"].append(info)
        result.append(fragment["channel"])
        (out/"stage-ipc-metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2))
    return {"channels":result}
