# DSH + GitHub Actions + Copilot

这是私有测试仓库。已实测 DSH 原生 headless 模型调用成功：Actions → DSH → GitHub Copilot gpt-5.4-mini → DSH JSON 输出。

## Issue 自动指派与后台运行

可用角色清单见 [agents/registry.json](agents/registry.json)，目前启用 connectivity 和 reviewer。

- 新建 Issue：选择“指派 DSH agent”模板，在 Agent 下拉框选择角色，填写 Task，提交即自动执行。
- 已有 Issue：添加 `agent:reviewer` 或 `agent:connectivity` 标签自动启动。
- 状态、结果和 Actions 链接自动回写 Issue；同一 Issue 串行，相同任务去重。
- 这两个角色目前执行分析/审查，工具在 Issue 工作流中被禁用，不改代码、不创建 PR。
- DSH 角色通过表单/标签选择，不是 GitHub 原生 Assignee 账号。

新增角色、停用、并发和重试说明见 [agents/README.md](agents/README.md)。

## 手动运行指定 agent

1. 打开 [Run DSH agent](https://github.com/gmij/dsh-actions-connectivity/actions/workflows/run-agent.yml)。
2. 点击 Run workflow。
3. 选择 `model`（默认 gpt-5.4-mini）、`agent`（connectivity / reviewer），填写 `task`。
4. 打开运行记录，查看 Show result 的 JSONL 和 final 输出。

只使用 Actions 临时令牌，workflow 声明 `copilot-requests: write`，没有保存个人 PAT。
模型 ID 需要同时被当前 Actions 身份及 DSH 的 pi-ai 目录支持。
agent 通过 `agents/*.patch.json` 配置系统提示词；headless CLI 的配置 overlay 支持重复 `--patch`，没有直接 `--agent` 参数。
角色提示词不等同于工具权限隔离。

## 测试记录

见 [TEST-RESULTS.md](TEST-RESULTS.md)。你在 Copilot 网页配置的 DeepSeek 可回复，但当前个人仓库 Actions 身份列出的模型不含 DeepSeek。
目前仅验证文本推理，未测试修改代码、执行工具或发布 PR。
