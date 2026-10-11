# DSH + GitHub Actions + Copilot

这是私有测试仓库，已验证 DSH headless 在 Actions 中使用 Copilot gpt-5.4-mini 完成推理。

## 原生下拉框选择 agent

Issue 右侧 Assign to Agent → Custom agent：
- Reviewer (Copilot)
- Connectivity (Copilot)

两个选项已在 GitHub 页面实际验证可见，无需标签。配置位于 .github/agents/*.agent.md。
它们由 Copilot Cloud Agent 执行，不启动 DSH；本轮只验证了选项显示，没有运行原生任务。
参见 [NATIVE-AGENTS.md](NATIVE-AGENTS.md)。“原生指派 → DSH Actions”调度桥接尚未实现。

## DSH Issue 自动化

DSH 可用角色见 [agents/registry.json](agents/registry.json)，目前启用 connectivity 和 reviewer。
新建 Issue 可选择“指派 DSH agent”模板，在 Agent 字段选择角色。
已有 Issue 可添加 agent:reviewer 或 agent:connectivity 标签自动运行。
状态、结果和运行链接回写 Issue；同一 Issue 串行，相同任务去重。
Issue 自动化为禁工具的 analysis 模式，输出审查建议，不修改代码或创建 PR。
原生 bot agent 的 assigned 事件会跳过 DSH 路由，避免同一次指派重复启动两套引擎。
详见 [agents/README.md](agents/README.md) 和 [ISSUE-AUTOMATION-VERIFIED.md](ISSUE-AUTOMATION-VERIFIED.md)。

## 手动运行 DSH

Actions → Run DSH agent → Run workflow，选择 model、agent、task。
只使用 Actions 临时 GITHUB_TOKEN 和 copilot-requests:write，无个人 PAT。
DSH 通过重复 --patch 选择模型配置和角色；模型 ID 必须被 Actions 身份及 DSH 目录支持。
原先的手动模板没有应用 Issue 自动化的禁工具 overlay。
见 [TEST-RESULTS.md](TEST-RESULTS.md) 和 [AGENT-RUN-VERIFIED.md](AGENT-RUN-VERIFIED.md)。
Copilot 网页的 DeepSeek BYOK 在当前个人仓库 Actions 身份下不可见。
