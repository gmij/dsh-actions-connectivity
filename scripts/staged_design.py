"""Bounded, resumable DSH design stages; validate only the assembled V2 bundle.

Each stage emits a JSON object with exactly its allotted top-level fields.
Local checkpoints are trusted only within the same workflow artifact directory.
"""
import json
import re
from pathlib import Path

CORE = ("schema_version", "level", "summary_markdown", "design_markdown",
        "experience", "milestones", "modules", "decisions")
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
                    "非 HTTP 交互必须在这里定义，不得用空 channels 掩盖缺失契约。",
        "prototype": "仅输出 prototype_html 字符串，必要时生成可本地运行的离线交互 HTML。"
                     "不要把 HTML 和 API Schema 放在一个 JSON 回复里。"
                     "使用 JSON 的正常转义；无需原型时返回空字符串。"
    }
    # Limit previous context; the stage is explicitly designed as a small MVP.
    previous = json.dumps(completed, ensure_ascii=False)
    if len(previous) > 85000:
        raise ValueError("Stage context exceeds 85000 characters; narrow MVP before continuing")
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

def generate_staged(original, level, out_dir, invoke):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    assembled = {}
    for name, fields in STAGES:
        checkpoint = out / ("stage-" + name + ".json")
        if checkpoint.exists():
            fragment = json.loads(checkpoint.read_text())
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
        if name != "core" and isinstance(fragment, dict):
            # Models sometimes repeat the common wire envelope in later stages.
            # It is safe to ignore ONLY values matching the authoritative core.
            for envelope in ("schema_version", "level"):
                if envelope in fragment:
                    if fragment[envelope] != assembled.get(envelope):
                        raise ValueError(f"Design stage {name} conflicting {envelope}")
                    fragment.pop(envelope)
        required = set(fields)
        if name == "core" and level == "detailed":
            required.add("overview_update_markdown")
        if not isinstance(fragment, dict) or set(fragment) != required:
            raise ValueError(f"Design stage {name} fields mismatch: expected {sorted(required)}, got {sorted(fragment) if isinstance(fragment, dict) else type(fragment).__name__}")
        if name == "core" and (fragment.get("level") != level or fragment.get("schema_version") != 2):
            raise ValueError("Invalid design schema/version or level in core stage")
        assembled.update(fragment)
        if not checkpoint.exists():
            checkpoint.write_text(json.dumps(fragment, ensure_ascii=False, indent=2))
    assembled["delivery"] = {key: assembled.pop(key) for key in ("apis", "bindings", "channels", "prototype_html")}
    return json.dumps(assembled, ensure_ascii=False)
