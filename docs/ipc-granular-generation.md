# 分粒度 IPC 契约生成与可恢复工作流

## 背景与证据

M1 设计产生过一个约 110 KB 的复杂 `IPC-10 host.event`，以及上下文累计超过 85,000 字符的失败。单向事件误映射到 null response 的问题已在 PR #37 修正。重复传递完整 IPC Schema、一个字段错误导致整个 channels 阶段重做，是另外两个独立的效率瓶颈。

**本方案保留完整且严格的交付格式，不靠放宽 Schema 来改善模型输出成功率。** 具体实现于共享 Engine PR #38。

## 新流程

启用 `DSH_GRANULAR_IPC=1` 后：
1. 之前的 core/tasks/pages/apis/bindings 按原逻辑执行。
2. `channels-index` 首先输出轻量通道目录（IPC ID、所属模块、任务、协议、命令、UI 页面），并验证引用和完整页面覆盖。
3. 每个 `channels-IPC-xx` 使用只包含当前所有者、相关页面、全局通道名录的提示词生成**单独完整的 JSON Schema/示例/字段映射**；不同推送事件应拆为独立 IPC 通道，不产生巨型复合 Schema。
4. 每条 IPC **直接调用与最终 delivery 相同的严格单通道校验函数**。失败时只将当前 IPC 的错误详情和截断后的本条输出送入一次 `channels-IPC-xx-repair`；其他有效通道不会重生成。
5. 验证成功立即写 `stage-channel-IPC-xx.json`；聚合后写传统 `stage-channels.json`，继续 prototype 和最终全局交付校验。
6. 记下 `stage-ipc-metrics.json` 中的 Prompt 字符数量、输出字符数量、检查点复用及单条修复信息。

未开启标志或已有 `stage-channels.json` 时完全沿用之前的流程。恢复来源 Run 需要显式提供并验证所属 Issue/仓库/设计等级。

## 恢复方式

在 `gmij/dsh-vscode` → Actions → **Issue DSH agent** → **Run workflow** 中选择：
- `issue_number`：目标 Issue
- `agent`：`overview` 或 `detailed`
- `resume_run_id`：希望恢复的**同一个 Issue、同一个设计等级**的已完成 Actions Run ID

编排器先核验来源工作流、运行状态、main 分支与 Issue 编号，再从 `issue-agent-result` Artifact 下载阶段 JSON。恢复脚本会检查 `stage-core.json` 的 `level`，只导入符合名称模式的 JSON 文件。不要把其他 Issue 或其它设计等级的检查点作为恢复源。

**注意**：GitHub Artifact 具有保留期（当前中间结果为 7 天）。过期时无法恢复，系统必须明确失败而非隐式重生成已消耗内容。

## 回归测试与边界

共享仓库 `tests/test_staged_ipc.py` 覆盖：
- 模型输出错误的字段映射只重试出错 IPC
- 多条 IPC 只恢复缺失检查点
- 不存在的 Schema 字段、无归属页面等情况严格拒绝
- 超大兄弟 IPC Schema 不会进入新 IPC 的 Prompt
- `generate_staged` 的完整模拟执行与再次运行零模型调用

下游 `test/recover_design.test.js` 覆盖跨 Issue、跨设计级别的恢复拒绝与正常复制。

**性能判读**：这些测试验证“不会把全部相邻 IPC Schema 放到单条 Prompt”及“已有 IPC 不会重复调用”，并记录实际 Prompt 字符数。尚未使用真实详细设计工作负载测量输入/输出 Token、成本与响应质量；不应据此报出节省百分比。详细设计实跑后，将结合 `stage-ipc-metrics.json`、DSH 用量日志和成功率比较前后开销。

## 仍需演进

- 设计接口消息类型可以再单独加一个显式 `request-response / notification` 鉴别字段（届时必须版本化升级 Schema，不能悄悄改变 V2）。
- 若通道清单本身不合格，目前会明确失败；后续可对清单本身增加限次定向修复。
- PR #38 的 IPC 粒度恢复仅保证阶段产物一致性，最终整份设计的业务/集成验收仍由外层契约与人工评审负责。
