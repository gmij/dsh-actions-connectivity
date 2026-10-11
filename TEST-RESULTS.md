# DSH + GitHub Actions 实测

2026-10-11，测试仓库为 gmij/dsh-actions-connectivity（private）。

## 已验证
- DSH npm 版本：@deepseek-ai/dsh@0.2.1-alpha.2；运行环境 Node.js 24。
- Actions 临时 GITHUB_TOKEN + permissions.copilot-requests: write 可以完成推理，无需另存个人 PAT。
- 原生 DSH headless -> llm-pi-ai -> github-copilot -> gpt-5.4-mini 调用成功。
- [成功运行](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38106083101)：final 为 DSH_COPILOT_OK；inputTokens=4042，outputTokens=11。
- 此测试只覆盖文本推理，不覆盖工具执行、修改代码、PR 发布。

## 关键配置
Provider 的 apiKeyEnv 为 GITHUB_TOKEN，baseURL 为 https://api.githubcopilot.com，
headers 为 {"Copilot-Integration-Id":"agentic-workflows"}。
DSH 默认目录中的 vscode-chat 请求头与 Actions 安装令牌不匹配；首次运行返回 HTTP 400，修改上面两项后成功。
这条链路没有借用浏览器会话 cookie 或导出账号令牌。

## 使用
Actions -> Run DSH agent -> Run workflow，选择 model、agent 和 task。
默认 connectivity agent + gpt-5.4-mini + 默认任务用于重复验证。
reviewer 是代码审查角色，可通过 task 提供审查对象。
agent 由 agents/*.patch.json 注入 system-prompt.config.personaPrefix；
它是 headless 角色配置，不是 Web UI 的 agent preset，也不是独立的工具权限隔离。
模型独立由 agent-default-model 与 llm-pi-ai 路由配置。
更换模型要求 Actions 可用清单和当前 DSH 内置目录都支持该 ID/协议，不能假设所有模型都走 Anthropic Messages。

## DeepSeek 的边界
Copilot 网页选择已配置的 deepseek-v4-flash，返回 DEEPSEEK_CONNECTIVITY_OK。
但 [Actions 模型清单](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38105804748) 中 DeepSeek candidates 为 []，
[CLI 指定 DeepSeek 测试](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38105742891) 返回 model not available。
所以当前个人仓库 Actions 身份不能直接沿用网页中组织提供的 DeepSeek；
需要后续验证承载该 BYOK 的组织运行环境/身份，或给 DSH 单独配置 DeepSeek API 凭据。
不要把网页测试成功当作 Actions 中 DeepSeek 成功。

## 参考
- https://github.com/deepseek-ai/deepseek-harness
- https://github.github.com/gh-aw/reference/auth/
- https://github.com/github/gh-aw-firewall/blob/main/docs/auth-matrix.md
