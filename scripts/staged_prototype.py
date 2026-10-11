"""Bounded prototype stages, assembled into the original trusted prototype contract."""
import json
from pathlib import Path

def generate_prototype(original, out_dir, invoke):
    out=Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stages=[
      ('brief', {'needs_prototype','decision_reason','requirements_markdown','design_markdown'}),
      ('html', {'prototype_html'}),
    ]
    result={}
    for name,keys in stages:
        file=out/('stage-prototype-'+name+'.json')
        if file.exists():
            part=json.loads(file.read_text())
        else:
            if name=='brief':
                prompt=original+'\n\n分阶段协议：现在只输出 JSON 对象，且只有 needs_prototype、decision_reason、requirements_markdown、design_markdown 四个字段。不要包含 HTML；设计说明应包含交互与状态。'
            else:
                prompt=(original+'\n\n分阶段协议：只输出一个 JSON 对象，唯一字段 prototype_html。禁止重复需求与设计说明。'
                        '\n前一阶段的已确定分析：\n'+json.dumps(result,ensure_ascii=False)
                        +'\n若 needs_prototype=false，prototype_html 必须是空字符串；否则生成完整可运行内联 HTML。')
            raw=invoke(prompt,'prototype-'+name)
            try: part=json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f'Prototype stage {name} invalid/truncated JSON: {exc}') from exc
        if not isinstance(part,dict) or set(part)!=keys:
            raise ValueError(f'Prototype stage {name} fields mismatch')
        if name=='brief' and type(part['needs_prototype']) is not bool:
            raise ValueError('needs_prototype must be boolean')
        result.update(part)
        if not file.exists(): file.write_text(json.dumps(part,ensure_ascii=False,indent=2))
    return json.dumps(result,ensure_ascii=False)
