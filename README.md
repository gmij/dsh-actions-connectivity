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

### 原型角色验收记录

- 原生选择 DSH Prototype 后，最终 [Issue #14](https://github.com/gmij/dsh-actions-connectivity/issues/14) 的 Copilot 调度会话完成，真实 [DSH run 38110990668](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38110990668) 的 route/agent/publish 全部成功，HTML 及需求说明回写到 Issue。
- [Issue #12](https://github.com/gmij/dsh-actions-connectivity/issues/12) 为纯后端任务，DSH 输出 needs_prototype=false，交付包没有 index.html。
- 15 项仓库单元测试通过；实际生成 HTML 的隔离逻辑测试覆盖初始列表、表单错误、安全输入展示、成功添加、进度更新、非法进度、完成及取消。
- 当前浏览器禁止打开本地 HTML，因此未完成现场视觉验收；交付包可下载后在用户浏览器打开。响应式和极简规范已写入角色指令，生成 HTML 中含相应 CSS。
- 首次原型验收的 Copilot 外层会话因 PR summary 格式显示失败，DSH 实际执行成功；已修正 prototype 的完成摘要要求，并在 #14 确认原生会话 Complete。GitHub 自动生成的调度 Draft PR 不是原型交付文件，无需合并它来获取 HTML。


## GitHub Pages 在线原型预览

选择 Issue 的 DSHPrototype 后，仍由真实 DSH 生成原型。生成工作流成功完成时，`Prototype Pages` 自动读取交付包、判断是否需要界面，再发布 GitHub Pages；发布成功后在原 Issue 回填「打开本次交互原型」与「此任务最新原型」链接，压缩包作为备用交付。

### 首次启用

仓库 Settings → Pages → Build and deployment → Source 选择 **GitHub Actions**。个人私有仓库需要支持私有仓库 Pages 的 GitHub 计划（Pro 或以上）；Copilot 订阅与此资格不同。Pages 站点公开可访问，原型只使用演示数据，请勿包含或输入真实、敏感数据。保持仓库本身为私有。

启用后，在 Actions → Prototype Pages → Run workflow 输入已有 DSH 成功运行 ID，可补发历史原型而无需再次调用模型。默认 ID `38110990668` 对应 Issue #14。页面发布后会自动把真实部署地址写回 Issue，尚未部署时不伪造预览链接。

### 路径与保存

- `previews/issue-<编号>/`：该任务最新原型。
- `previews/issue-<编号>/runs/<DSH运行ID>/`：本次生成的固定版本。
- 根页面：按 Issue 编号列出预览，不公开 Issue 标题或正文。

HTML 长期保存在独立的 `prototype-previews` 分支，持续部署时保留其他 Issue 与历史版本，不受 Actions 交付包 30 天保留期影响。旧运行重新补发不会把最新版本倒退。删除分支、站点或仓库会影响可用性；首次补发仍需源交付包未过期。

发布器只接收本仓库默认分支上成功的 `issue-agent.yml`（issues / workflow_dispatch），拒绝 PR/其他工作流来源。不执行模型 HTML，只发布固定路径的 HTML 与索引；需求文档、日志、提示词、Issue 正文和密钥不会包含在 Pages 发布目录。无需原型、未分派及其他角色任务跳过发布。所有 Issue 的归档和部署串行执行。部署或权限失败时可修复后重新运行 Prototype Pages，已有原型交付包仍可下载。

本次发布器新增 7 项测试，总计 22 项测试通过；在线部署需完成 Pages 设置后验收。
