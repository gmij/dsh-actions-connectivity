# DSH + GitHub Actions + Copilot

这是私有测试仓库，已验证 DSH headless 在 Actions 中使用 Copilot gpt-5.4-mini 完成推理。

## 原生下拉框选择 agent

Issue 右侧 Assign to Agent → Custom agent：
- DSH Reviewer
- DSH Connectivity

配置位于 .github/agents/*.agent.md，无需标签。原生 Copilot 只负责调用 MCP 调度工具，实际任务交给 DSH Actions 执行。
原生指派端到端已验收通过：Reviewer（Issue #6 / run 38108796906）和 Connectivity（Issue #8 / run 38108953535）。
两项均通过真实 MCP 调度并由 DSH 完成，结果回写 Issue，无需标签。本地 13 项测试通过。
配置与证据见 [NATIVE-AGENTS.md](NATIVE-AGENTS.md)。原生 Model 选择的是调度层模型，DSH 模型由注册清单控制。
GitHub 会自动建立 Draft PR 容器；无需合并，DSH 结果以 Issue 回写为准。

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

## 原型设计智能体

在 Issue 的原生 Assign to Agent 下拉框中选择 **DSH Prototype**，继续复用现有 MCP 调度凭据，由 DSH Actions 执行。无需加标签。

智能体先判断是否需要界面，分析需求、用户流程、状态和验收条件；需要时生成可交互的单文件 HTML 原型，否则解释判断依据。默认采用极简舒适美学，居中紧凑布局，支持手机、平板和桌面，具体规范见 `agents/prototype-instructions.md`。可在 Issue 中提供品牌规范或参考。

结果回写 Issue，并附 `prototype-deliverable` 交付包：`decision.json`、`requirements.md`、`design.md`、`README.md`，需要原型时另有 `index.html`。下载并解压后用浏览器打开 HTML；交付包保留 30 天，可自行下载留存。当前交付是交互原型和演示数据，未连接真实业务后端。

DSH 引擎使用 registry 中的模型，当前为 GitHub Copilot API 的 `gpt-5.4-mini`；原生下拉框的调度模型不改变 DSH 实际模型。HTML 是模型输出的数据，校验后只写入固定 artifact 路径，不写回仓库代码，不在带凭据的 runner 中执行。
