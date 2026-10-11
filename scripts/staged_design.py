"""Bounded, resumable DSH design stages; validate only the assembled V2 bundle.

Each stage emits a JSON object with exactly its allotted top-level fields.
Local checkpoints are trusted only within the same workflow artifact directory.
"""
import json
from pathlib import Path

CORE = ("schema_version", "level", "summary_markdown", "design_markdown",
        "experience", "milestones", "modules", "decisions")
STAGES = (
    ("core", CORE),
    ("tasks", ("task_records",)),
    ("pages", ("page_records",)),
    ("delivery", ("delivery",)),
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
        "delivery": "仅输出 delivery 对象，包含 apis、bindings、prototype_html。"
                    "严格对齐已确定页面、任务、模块及实际 API-ID。"
                    "需要界面时原型必须能本地运行，不能用静态截图代替交互。"
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
            try:
                fragment = json.loads(response)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Design stage {name} returned invalid/truncated JSON: {exc}") from exc
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
    return json.dumps(assembled, ensure_ascii=False)
