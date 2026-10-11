# 原生下拉框 → DSH：端到端验收记录

2026-10-11 已验证原生自定义 Agent 调度到真实 DSH Actions。无需 agent 标签或 Issue 表单。

## 使用方式

1. 新建或打开一个 Issue，正文写实际任务。
2. 点击右侧 Assign to Agent → Custom agent。
3. 选择 DSH Connectivity 或 DSH Reviewer，点击 Assign。
4. 原生会话回复调度状态；最终执行状态、结果和 Actions 链接由 github-actions[bot] 回写同一 Issue。

当前两个角色均为禁工具的 analysis 模式：连通性输出、代码分析与建议。DSH 不修改代码、不创建 PR。
GitHub 原生入口仍会启动 Copilot 会话及自动建立 Draft PR 容器；Copilot 只调用 MCP 调度工具，不替代 DSH 执行。该空 PR 不需要合并，DSH 结果以 Issue 回写为准。
原生 Model 下拉框选择的是调度层模型，DSH 推理模型由 agents/registry.json 设定，目前为 gpt-5.4-mini。

## 已验证的链路

原生 profile → dsh-dispatch/dispatch_issue → issue-agent.yml workflow_dispatch → DSH headless → publish。
Profile 固定 DSH_AGENT_ID，工具只接受 issue_number。
MCP 的 dispatch_accepted 不代表任务完成；下游 DSH 必须产生 final 和 completed turn_end，publish 才写完成状态。
相同 Issue 同一任务 fingerprint 去重，Issue 内串行，MCP 不允许 force=true。
原生 bot assigned 的自动路由跳过规则保留，明确角色的 workflow_dispatch 正常执行。

| 原生选择 | Issue | DSH run | 验收结果 |
|---|---|---|---|
| DSH Reviewer | #6 | 38108796906 | route/agent/publish 全部成功；输出 DSH_NATIVE_REVIEWER_OK，指出空输入导致 ZeroDivisionError 并给出修复建议 |
| DSH Connectivity | #8 | 38108953535 | route/agent/publish 全部成功；精确输出 DSH_NATIVE_BRIDGE_OK |

Reviewer 原生会话：
https://github.com/gmij/dsh-actions-connectivity/sessions/14ce83f7-c667-4f28-b3f1-cd5ae7fe15f8
其 MCP 调用 Input 是 {"issue_number": 6}，返回 engine=DSH、agent=reviewer。
任务答案来自 DSH job 日志和 github-actions[bot] 回写，不是 Copilot 会话自行生成。

连通性：
https://github.com/gmij/dsh-actions-connectivity/issues/8
https://github.com/gmij/dsh-actions-connectivity/actions/runs/38108953535

审查：
https://github.com/gmij/dsh-actions-connectivity/issues/6
https://github.com/gmij/dsh-actions-connectivity/actions/runs/38108796906

## 配置与身份

.github/agents/*.agent.md：原生菜单角色与受限 MCP 工具。
agents/registry.json：DSH 角色、persona patch、模型、是否启用。
scripts/dsh_dispatch_mcp.py：固定仓库、固定工作流的调度桥接。
scripts/issue_agent.py：可信路由、输入快照、DSH 运行及结果发布。

调度凭据由用户保存为 Agents secret COPILOT_MCP_DSH_DISPATCH_TOKEN，已通过真实原生 MCP 调用验证可用。没有读取或记录凭据值，也没有核验其具体失效日期。
建议 fine-grained PAT 仅限 gmij/dsh-actions-connectivity，Actions read/write、Issues read、默认 Metadata read。
它只用于 GitHub API 调度；DSH 模型推理继续使用 Actions 临时 github.token + copilot-requests:write。
普通 Actions repository secret 不会自动提供给原生 MCP；应使用 Agents secret。
不在聊天、Issue、PR、源码、日志中保存 token。

## 验收中修正的问题

首次连通性 Issue #4 含调度层说明，DSH 将它误当成自身职责，虽成功执行但输出未满足精确标记要求，不能计入功能验收。
已修正 worker 提示：调度阶段已完成，DSH 只处理实际任务。快照排除 .github/agents 中的原生 profile，connectivity 不加载无关仓库快照。
新增回归测试；本地共 13 项测试通过。
Reviewer #6 已在修改前完成正确审查，Connectivity #8 通过修正后的默认分支重新原生指派。

早期 API smoke run 38107939477 证明真实 dispatch 调用成功，但下游 38107944673 的 github-actions[bot] sender 被 writer guard 跳过，没有执行 DSH。该记录不当作端到端成功，未绕过身份校验。
测试工作流现为手动触发。

参考：
https://docs.github.com/en/copilot/reference/custom-agents-configuration
https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/configure-secrets-and-variables
