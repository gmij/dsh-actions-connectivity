"""Bounded, resumable DSH design stages; validate only the assembled V2 bundle.

Each stage emits a JSON object with exactly its allotted top-level fields.
Local checkpoints are trusted only within the same workflow artifact directory.
"""
import json
import re
from pathlib import Path

CORE = ("schema_version", "level", "summary_markdown", "design_markdown",
        "experience", "milestones", "modules", "decisions")
IPC_TRANSPORTS = frozenset(("vscode-webview", "vscode-command", "acp", "process-stdio", "ipc"))

STAGES = (
    ("core", CORE),
    ("tasks", ("task_records",)),
    ("pages", ("page_records",)),
    ("apis", ("apis",)),
    ("bindings", ("bindings",)),
    ("channels", ("channels",)),
    ("prototype", ("prototype_html",)),
)


def stage_prompt(original, name, keys, completed, level):
    preface = (
        "\n\n【分阶段输出协议，优先级高于范例中一次输出完整 JSON 的要求】\n"
        "你只能输出当前阶段字段组成的合法 JSON object，禁止围栏、说明、其他顶层字段。"
        "不得重复其他阶段已经生成的字段。每阶段产物由可信 Python 合并并完成全局校验。\n"
        "本任务是概要或详细设计，不声称已实现代码或部署。"
        "范围限定为一个最小纵向 MVP，最多 2 个模块、1 个里程碑、8 个任务、"
        "3 个页面、6 个 HTTP API；不适用 HTTP 的桌面 IPC/进程协议，"
        "必须使用内部接口契约明确说明，不能伪造 HTTP API。"
        "始终满足跨模块的 ID/引用一致性，避免冗余 Schema。\n"
    )
    guide = {
        "core": "只规划架构、MVP、模块职责、决策及全局文档。milestones.task_ids 必须预先分配"
                "后续 tasks 阶段真正产生的 TASK-ID；modules 暂不含 tasks/pages。"
                "overview 只含 CORE 字段，detailed 额外包含 overview_update_markdown。",
        "tasks": "仅输出 task_records 数组。每个任务必须有准确 inputs/outputs、depends_on、"
                 "里程碑归属及测试，ID 与 core.milestones.task_ids 完全一致。",
        "pages": "仅输出 page_records 数组。仅针对 core 模块中的 frontend_applicable=true 模块，"
                 "操作及绑定引用 delivery 阶段将生成的 API-ID；不是网页产品时允许空数组。",
        "apis": "仅输出 apis 数组，每一项都包含完整 HTTP 请求/响应 Schema 和示例。"
                "仅设计实际存在的 HTTP API，不把 VS Code IPC/ACP 伪装成 HTTP。"
                "不适用 HTTP API 时输出空数组。单次最多 3 个 API，控制输出体积。",
        "bindings": "仅输出 bindings 数组，引用已生成 apis 和 page_records。"
                    "没有适用 HTTP API 时输出空数组，页面内部交互在模块接口契约描述。",
        "channels": "仅输出 channels 数组，适用于 VS Code Webview、命令、ACP、stdio 和 IPC。"
                    "每条通道严格定义 id(IPC-01)、module_id、task_id、transport、command、"
                    "request/request_example、response/response_example、error/error_example、bindings。"
                    "三个消息 Schema 使用与 HTTP 相同的内联 JSON Schema 子集；bindings 每项含"
                    "page_id、action、request_mapping、response_mapping、loading_behavior、"
                    "error_behavior、success_behavior。字段映射 source/target 明确到 schema。"
                    "transport 字段只能是以下五个固定英文枚举之一：vscode-webview、vscode-command、acp、process-stdio、ipc。"
                    "不能在 transport 中写中文说明、协议推测或组合选择；无法证明更具体协议时选 ipc。"
                    "例如：{\"id\":\"IPC-01\",\"transport\":\"ipc\",\"command\":\"SessionBridge.open\",...}。"
                    "对于 Host→Webview 单向事件：request 为推送事件信封，response 和 error 可为 type=null、示例 null；"
                    "bindings.response_mapping 的 source 应指向 request 中真实事件字段（如 sequence/payload.textDelta），"
                    "因为通知没有响应消息。普通有响应通道的 response_mapping.source 才指向 response schema。"
                    "禁止把 UI 消费的推送事件字段虚构到 null response 中。"
                    "非 HTTP 交互必须在这里定义，不得用空 channels 掩盖缺失契约。",
        "prototype": "仅输出 prototype_html 字符串，必要时生成可本地运行的离线交互 HTML。"
                     "不要把 HTML 和 API Schema 放在一个 JSON 回复里。"
                     "使用 JSON 的正常转义；无需原型时返回空字符串。"
    }
    # Limit previous context; the stage is explicitly designed as a small MVP.
    previous = json.dumps(completed, ensure_ascii=False)
    if len(previous) > 50000:
        # Keep the complete, authoritative documents in checkpoints and output;
        # only the next stage's reference context needs an abbreviated view.
        # Preserve all keys, IDs, cross-references and short schema fields.
        def compact(value, limit):
            if isinstance(value, str):
                return value if len(value) <= limit else value[:limit] + "…[abbreviated for next stage]"
            if isinstance(value, list):
                return [compact(v, limit) for v in value]
            if isinstance(value, dict):
                return {k: compact(v, limit) for k, v in value.items()}
            return value
        for limit in (320, 160, 80, 32):
            previous = json.dumps(compact(completed, limit), ensure_ascii=False)
            if len(previous) <= 50000:
                break
    if len(previous) > 50000:
        # Very large generated arrays are summarized as lightweight references,
        # never discarded from assembled design or the stage artifacts.
        def references(value):
            if isinstance(value, list):
                return [references(v) for v in value]
            if isinstance(value, dict):
                important = ("id", "module_id", "task_id", "page_id", "name", "title",
                             "transport", "command", "method", "path", "depends_on",
                             "task_ids", "module_ids", "api_id", "channel_id", "action")
                return {k: references(v) for k, v in value.items() if k in important}
            if isinstance(value, str):
                return value[:120]
            return value
        previous = json.dumps(references(completed), ensure_ascii=False)
    if len(previous) > 85000:
        raise ValueError("Stage references exceed 85000 characters; split the MVP into separately linked issues")
    expected = list(keys) + (["overview_update_markdown"] if name == "core" and level == "detailed" else [])
    return (original + preface + "\n当前阶段：" + name + "\n当前顶层字段只能是：" +
            json.dumps(expected, ensure_ascii=False) + "\n" + guide[name] +
            "\n已完成的阶段（保持标识符与接口契约一致，不要在本阶段重复输出）：\n" +
            previous + "\n现在只输出本阶段的 JSON object。")


def parse_stage_json(response):
    """Accept one complete JSON code fence, never arbitrary prose or partial fences."""
    value = response.strip()
    match = re.fullmatch(r"```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n```", value, flags=re.IGNORECASE)
    if match:
        value = match.group(1).strip()
    return json.loads(value)

def remove_duplicate_ipc_http_bindings(assembled):
    """Remove only provably duplicate event/IPC bindings mislabeled as HTTP.

    Never synthesize missing HTTP request fields or remove a sole real API
    binding. Genuine HTTP actions still fail strict delivery validation.
    """
    bindings = assembled.get("bindings", [])
    channels = assembled.get("channels", [])
    apis = assembled.get("apis", [])
    if not isinstance(bindings, list) or not isinstance(channels, list):
        return
    by_id = {c["id"]: c for c in channels if isinstance(c, dict) and "id" in c}
    kept = []
    for b in bindings:
        if not isinstance(b, dict) or not isinstance(b.get("action"), str):
            kept.append(b)
            continue
        action = b["action"]
        linked = None
        match = re.search(r"IPC-\\d{2,3}", action)
        if match:
            linked = by_id.get(match.group(0))
        elif "session/update" in action and ("推送" in action or "事件" in action):
            linked = next((c for c in channels if c.get("command") in
                           ("session.update", "session/update")), None)
        if linked is not None and any(
                x.get("page_id") == b.get("page_id")
                for x in linked.get("bindings", [])):
            # Only the non-HTTP event/cancel action is redundant. Another
            # binding must still own the actual HTTP API.
            other = [x for x in bindings if x is not b and
                     x.get("api_id") == b.get("api_id")]
            api_exists = any(x.get("id") == b.get("api_id") for x in apis)
            is_non_http = ("推送" in action or "无 HTTP" in action)
            if other and api_exists and is_non_http:
                continue
        kept.append(b)
    assembled["bindings"] = kept


def generate_staged(original, level, out_dir, invoke, granular_ipc=False):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    assembled = {}
    for name, fields in STAGES:
        checkpoint = out / ("stage-" + name + ".json")
        if checkpoint.exists():
            fragment = json.loads(checkpoint.read_text())
        elif name == 'channels' and granular_ipc:
            from ipc_stages import generate_channels
            fragment = generate_channels(original, assembled, out, invoke)
        else:
            prompt = stage_prompt(original, name, fields, assembled, level)
            response = invoke(prompt, name)
            if not response.strip():
                raise ValueError(f"Design stage {name} returned empty final text; inspect stage-{name}-result.jsonl for model termination reason")
            try:
                fragment = parse_stage_json(response)
            except json.JSONDecodeError as exc:
                prefix = response.lstrip()[:80].replace("\\n", " ")
                raise ValueError(f"Design stage {name} returned non-JSON/incomplete text ({len(response)} chars; leading={prefix!r}): {exc}") from exc
        required = set(fields)
        if name == "core" and level == "detailed":
            required.add("overview_update_markdown")

        def normalize_fields(value):
            if name != "core" and isinstance(value, dict):
                value = dict(value)
                for envelope in ("schema_version", "level"):
                    if envelope in value:
                        if value[envelope] != assembled.get(envelope):
                            raise ValueError(f"Design stage {name} conflicting {envelope}")
                        value.pop(envelope)
            return value

        fragment = normalize_fields(fragment)
        if not isinstance(fragment, dict) or set(fragment) != required:
            got = set(fragment) if isinstance(fragment, dict) else set()
            if checkpoint.exists():
                raise ValueError(f"Design stage {name} checkpoint fields mismatch: expected {sorted(required)}, got {sorted(got)}")
            # Retry only this stage once, with exact field corrections. Keep DSH
            # event logs separate using a distinct invocation stage name.
            correction = (
                stage_prompt(original, name, fields, assembled, level)
                + "\\n上次阶段输出未通过契约校验。缺失字段："
                + json.dumps(sorted(required - got), ensure_ascii=False)
                + "；多余字段：" + json.dumps(sorted(got - required), ensure_ascii=False)
                + "。请重新生成此阶段的完整 JSON，必须且只能包含指定字段。"
                + "\\n上次的内容（供纠错参考）：\\n"
                + json.dumps(fragment, ensure_ascii=False)[:35000]
            )
            corrected = invoke(correction, name + "-schema-retry")
            try:
                fragment = normalize_fields(parse_stage_json(corrected))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Design stage {name} schema retry returned invalid JSON: {exc}") from exc
            if not isinstance(fragment, dict) or set(fragment) != required:
                got = sorted(fragment) if isinstance(fragment, dict) else type(fragment).__name__
                raise ValueError(f"Design stage {name} schema retry fields mismatch: expected {sorted(required)}, got {got}")
        if name == "channels":
            def invalid_transports(value):
                channels = value.get("channels") if isinstance(value, dict) else None
                if not isinstance(channels, list):
                    return ["channels: expected list"]
                return [f"{item.get('id', 'unknown')}: {item.get('transport')!r}" if isinstance(item, dict) else f"invalid channel item: {type(item).__name__}"
                        for item in channels
                        if not isinstance(item, dict) or item.get("transport") not in IPC_TRANSPORTS]
            invalid = invalid_transports(fragment)
            if invalid:
                if checkpoint.exists():
                    raise ValueError("Invalid saved channel transports: " + "; ".join(invalid))
                repair_prompt = (
                    stage_prompt(original, name, fields, assembled, level)
                    + "\\n上一版 channels 有不符合枚举的 transport："
                    + json.dumps(invalid, ensure_ascii=False)
                    + "。transport 只能严格从 "
                    + json.dumps(sorted(IPC_TRANSPORTS))
                    + " 中选一个。无法证明更具体协议时使用 ipc。不要把协议解释放进 transport。"
                    + "保留所有通道的业务设计与完整 Schema/字段映射，重新输出整个 channels JSON。"
                    + "\\n上一版 channels（修订参考）：\\n"
                    + json.dumps(fragment, ensure_ascii=False)[:85000]
                )
                try:
                    fragment = normalize_fields(parse_stage_json(invoke(repair_prompt, name + "-transport-retry")))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Design stage channels transport retry invalid JSON: {exc}") from exc
                if not isinstance(fragment, dict) or set(fragment) != required or invalid_transports(fragment):
                    raise ValueError("Design stage channels transport retry still violates fields/transport enum")
        if name == "core" and (fragment.get("level") != level or fragment.get("schema_version") != 2):
            raise ValueError("Invalid design schema/version or level in core stage")
        assembled.update(fragment)
        if not checkpoint.exists():
            checkpoint.write_text(json.dumps(fragment, ensure_ascii=False, indent=2))
    remove_duplicate_ipc_http_bindings(assembled)
    assembled["delivery"] = {key: assembled.pop(key) for key in ("apis", "bindings", "channels", "prototype_html")}
    return json.dumps(assembled, ensure_ascii=False)
