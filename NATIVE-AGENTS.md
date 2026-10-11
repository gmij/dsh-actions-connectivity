# GitHub 原生 agent 下拉框

2026-10-11 已在 Issue 的 Assign to Agent → Custom agent 下拉框实际验证：

- Connectivity (Copilot)
- Reviewer (Copilot)

配置文件：
- .github/agents/connectivity.agent.md
- .github/agents/reviewer.agent.md

打开 Issue 右侧 Assign to Agent，展开 Custom agent，选择角色和模型后点击 Assign。
无需添加标签。当前仅验证配置被识别、选项可见；本轮没有提交原生任务进行执行测试。

## 执行引擎

这两个原生配置由 Copilot Cloud Agent 执行，并非此前的 DSH Actions 工作流。
Reviewer 仅开放 read/search；Connectivity 不开放工具。
GitHub 原生 Issue 指派会启动 Copilot 的云端任务，可能采用其 PR 交付流程。
不要将此入口运行的结果称为 DSH 结果。

此前 agents/registry.json 是 DSH 工作流清单；.github/agents 是 GitHub 原生自定义 agent 清单。
二者独立。仅把 DSH 角色放进 .github/agents 不能切换 GitHub 的执行引擎。

若要保留“原生下拉框 → DSH Actions”的完整链路，需要实现受控的调度桥接（例如自定义 agent 的 MCP dispatch 工具），
并验证认证权限、Issue 与角色传递、工作流触发以及结果关联。
该桥接尚未实现。不能把普通 GitHub App 直接等同于已启用 agent 功能的 GitHub agent app。

参考：
https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/create-custom-agents
https://docs.github.com/en/copilot/reference/custom-agents-configuration
