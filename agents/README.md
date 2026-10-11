# 仓库可用 agent 与 Issue 工作流

## 当前清单

权威清单是 [registry.json](registry.json)。目前启用 2 种角色：

| ID | 指派标签 | 用途 |
|---|---|---|
| connectivity | agent:connectivity | 连通性验证 |
| reviewer | agent:reviewer | 代码审查与修复建议 |

一个角色可为多个 Issue 创建独立实例。角色数量不等于并发实例数。
同一个 Issue 串行执行；不同 Issue 可同时执行，并发上限由 GitHub Actions runner/账号配额决定。
这版没有额外实现仓库级的固定并发上限，也没有多 agent 协同编排。

## 指派方式

**新 Issue：** Issues → New issue → “指派 DSH agent”，在 Agent 下拉框选角色并填写 Task，提交后自动后台启动。

**已有 Issue：** 添加一个 `agent:reviewer` 或 `agent:connectivity` 标签，立即自动启动。
切换角色时先移除旧 agent 标签，再添加新标签，不能保留多个 agent 标签。
Issue 的 agent 标签优先于创建时表单里的 Agent。
Assignees 是 GitHub 账号/已接入 agent 的原生指派入口，这里的 DSH 角色通过表单和标签选择，不会伪装成 GitHub 账号；
GitHub Copilot 的云端 agent 指派是另一条执行链路。

监听 opened、labeled、assigned、reopened。普通 Issue 未选 agent 时跳过。
assigned 事件会沿用当前选中的 DSH agent，并做去重，不会将任意被指派账号自动当作 DSH agent。
仅仓库具有 write/maintain/admin 权限的人能触发实际 agent 调用。

## 结果和重试

Issue 中会出现 github-actions[bot] 的“已启动”状态，结束后同一条评论更新为结果/失败及 Actions 链接。
模型、任务、角色配置相同的重复指派不重新消耗推理 tokens；同一 Issue 的并发事件串行处理。
去重标记包含 Issue 标题/正文和所选角色配置。编辑正文不会自动运行，以免每次编辑都耗费 tokens。
修改任务后，移除并重新添加 agent 标签，或手动运行 Issue DSH agent。
失败或取消后，在 Actions → Issue DSH agent → Run workflow 填写 issue_number，force=true 重新执行。
GitHub Actions concurrency 同组只保留一个等待中的运行，高频重复事件以最新等待运行为准。
若其他 Actions 用内置 GITHUB_TOKEN 创建 Issue/添加标签，GitHub 通常不会再触发 issues 工作流；需显式 workflow_dispatch。

## 执行范围

当前两种角色均为 analysis 模式：处理 Issue 内容与受限大小的仓库文本快照（快照可能截断），返回分析结果。
Issue 自动化的 overlay 在运行时禁用了文件/终端/子 agent 等工具，不会修改代码、创建 PR 或合并。
推理 job 只有 contents:read 和 copilot-requests:write；独立的 publish job 才持有 issues:write，模型不获得发布权限。
手动 Run DSH agent 是之前的独立连通性模板，不受此 Issue 自动化的 analysis overlay 约束。
当前模型是已验证的 gpt-5.4-mini；不自动继承 Copilot 网页的 DeepSeek BYOK。

## 新增/停用 agent

1. 新增 agents/<id>.patch.json，定义 system-prompt.config.personaPrefix。
2. 在 registry.json 的 agents 中登记 ID、显示名、用途、enabled、label、patch、model、mode。
3. 更新 .github/ISSUE_TEMPLATE/agent-task.yml 下拉选项。
4. 合并到默认分支；setup job 自动创建相应 agent 标签。
5. 新建测试 Issue 验证。
6. enabled=false 可停用角色。新增可执行开发角色需要另行实现工具策略、分支与 PR 交付路径。

不必预先确定未来全部角色；但每个可指派角色必须先在仓库登记，未知/停用/多重选择会拒绝运行。
