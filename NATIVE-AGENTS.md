# 原生下拉框 → DSH 引擎

## 当前状态（2026-10-11）

桥接代码与两个 Agent 配置已实现；本地 12 项测试通过（6 项桥接与 6 项原 Issue 路由）。
尚未完成端到端验收：缺少 Agents 调度凭据，没有以原生指派运行新的 DSH 任务。
不能把本地 API mock 或菜单显示当作端到端完成。

## 运行链路

Issue → Assign to Agent → Custom agent → DSH Reviewer / DSH Connectivity。
GitHub 原生入口仍先启动 Copilot Cloud Agent，但它仅调用受限 MCP dispatch_issue 工具。
工具角色固定在 profile 环境配置，只接受当前 issue_number。
它调度 issue-agent.yml，DSH headless 加载 agents/registry.json 的角色和 patch 完成任务。
DSH Actions 自己读取 Issue 正文、验证调度者写权限、执行并将状态/结果/运行链接写回 Issue。
不需要标签。Copilot 的回复只表示调度状态，不替代 DSH 结果。
原生 bot assigned 路由的跳过规则保留；MCP 使用 workflow_dispatch 明确选定角色。
相同内容由现有 DSH fingerprint 去重；MCP 不允许 force=true。

## 一次性认证配置

创建仅覆盖 gmij/dsh-actions-connectivity 的 fine-grained PAT：
- Actions: Read and write（用于 workflow_dispatch）
- Issues: Read-only（验证目标是开放 Issue）
- Metadata: Read-only（默认）
- 建议测试凭据有效期 7 天，验收后撤销或替换为仓库专用 GitHub App installation token。

在 Repository Settings → Agents → Secrets 创建：
COPILOT_MCP_DSH_DISPATCH_TOKEN。
旧版 UI 可能将此显示为 copilot environment secret；必须是原生 Agent 可读取的秘密，普通 Actions repository secret 不会自动传入 Agent MCP。
不要把 token 发到聊天、Issue、PR、配置文件或日志中。
这是调度凭据，不是模型 API key。DSH 模型推理继续使用 Actions 临时 github.token 与 copilot-requests:write。
内置 GitHub MCP 默认只读；当前 GitHub 连接器身份也不会自动变成原生 Agent 的调度凭据。

## 验收步骤（凭据配置后）

1. 创建全新 Issue，正文要求只输出 DSH_NATIVE_BRIDGE_OK；不加标签、不使用旧 Agent 表单。
2. 从 Assign to Agent 的 Custom agent 选择 DSH Connectivity 并提交。
3. 检查原生 session 确实调用 dispatch_issue 并成功返回，而不是自行输出标记。
4. 检查新的 Issue DSH agent run 的 route/agent/publish 全部成功，DSH JSONL 中有 final 与 completed turn_end。
5. 原 Issue 必须出现 github-actions[bot] 的 DSH 完成结果及该 run 链接，输出指定标记。
6. 新建代码审查 Issue，以同一路径选择 DSH Reviewer，验证运行 metadata 中角色 reviewer 与注册 patch 一致。

GitHub 原生会话仍可能建立自身 PR 容器；不要将该 PR 当作 DSH 的交付。
本仓库当前 DSH 角色为禁工具 analysis 模式，可执行连通性测试和审查建议，不修改仓库代码。

参考：
https://docs.github.com/en/copilot/reference/custom-agents-configuration

## 真实 API 测试记录

测试 workflow run: https://github.com/gmij/dsh-actions-connectivity/actions/runs/38107939477
同一 MCP tools/call 实现使用 Actions 临时 token 成功调用真实 workflow_dispatch API。
触发的下游 run: https://github.com/gmij/dsh-actions-connectivity/actions/runs/38107944673
下游 dispatch sender 是 github-actions[bot]，现有 writer 权限检查正确跳过，agent/publish 未执行。
因此这只证明 MCP → GitHub 调度 API 成功，不能称为 DSH 执行成功。
原生桥接应使用有该仓库写权限的用户所持、仅限此仓库的调度 PAT，其 sender 由 GitHub 身份认证决定，不能从工具参数伪造。
保留 writer 检查，不为此测试绕过认证。完整下拉框 → DSH 执行仍待配置 Agents secret 后验收。
测试工作流现为仅手动触发，避免后续文档更新重复调度。
