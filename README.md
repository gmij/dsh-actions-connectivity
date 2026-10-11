# DSH + GitHub Actions + Copilot

这是私有测试仓库，已验证 DSH headless 在 Actions 中使用 Copilot gpt-5.4-mini 完成推理。

## 原生下拉框选择 agent

Issue 右侧 Assign to Agent → Custom agent：
- DSH Reviewer
- DSH Connectivity
- DSH Prototype
- DSH Overview Design（概要设计）
- DSH Detailed Design（详细设计）

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

发布器只接收本仓库默认分支上成功的 `issue-agent.yml`（issues / workflow_dispatch），拒绝 PR/其他工作流来源。不执行模型 HTML，只发布固定路径的 HTML 与索引；需求文档、日志、提示词、Issue 正文和密钥不会包含在 Pages 发布目录。无需原型、未分派及其他角色任务跳过发布。所有 Issue 的归档和部署串行执行，使用 queue: max 保留最多 100 个等待运行，超出平台上限的任务可手动补发。部署或权限失败时可修复后重新运行 Prototype Pages，已有原型交付包仍可下载。

GitHub Pages 已启用，并兼容仓库所有者的自定义域名。23 项单元测试已通过；真实发布运行 38112267295 的 test、build、deploy 全部成功。Issue #14 已收到在线预览链接（评论 6105512319）。浏览器实际访问确认原型入口与原型文档可打开，并重定向至 https://gmij.win/dsh-actions-connectivity/previews/issue-14/ 。原型脚本的隔离逻辑测试涵盖添加、输入校验和进度更新；浏览器凭据保护阻止后续页面操作，因此完整的在线交互与视觉验收仍未完成。


### 原型渲染修复（2026-10-11）

真实在线截图发现样式和脚本未生效，页面呈浏览器默认样式，初始书单为空。页面环境处理后的 CSP 内容出现无效引号。交付器改用字面引号序列化同一离线安全策略，Pages 发布器同时兼容并迁移原有编码策略；未改变禁止网络请求、表单外发及 iframe 的约束。

修复发布运行 `38112794384` 的 test、build、deploy 均成功，25 项单元测试通过。已重新打开实际在线页面并截图核对，居中布局、字体、按钮、三本示例书及进度条恢复正常。此次完成首屏视觉检查；未声称完成全部在线交互或各移动尺寸验收。

原型智能体规范补充：首屏关键内容直接写入 HTML、正常产品文案、低干扰演示说明、优先页面内编辑、安全策略统一由可信交付脚本负责。


## 概要设计与详细设计智能体

仓库新增两个可选原生 Agent，仍由 MCP 调度到真实 DSH，模型沿用 `gpt-5.4-mini`。当前共 5 个角色；无需新增调度凭据。

| 下拉框名称 | DSH 角色 | 重心 |
|---|---|---|
| DSH Overview Design | overview | 架构、模块边界、领域模型、模块接口、关键流程、里程碑与概要级任务契约 |
| DSH Detailed Design | detailed | 可独立开发的逐任务输入输出、接口示例、实现落点、事务、异常/重试/幂等、验收与测试 |

在现有 Issue 右侧 Assign to Agent → Custom agent 选择相应角色。请把需求、概要设计及原型约束写入 Issue 或仓库设计文档；目前不会自动读取其他 Issue、附件或外部链接的内容，应粘贴相关正文或放入可读取的仓库文件。缺少概要时详细设计会标明最小概要与假设，不能假装已有确认。

输入契约包括名称、准确类型/字段、来源、必填与校验；输出包括名称、准确类型/字段、消费者与成功保证。下游引用格式 `TASK-01.outputName`，必须存在并列出依赖，生产者输出与消费者输入类型必须一致；依赖禁止循环。

每个实际模式/关键技术或模型选择写明：解决的具体问题、为什么采用、替代方案、取舍代价、适用边界、接口/类/模块落点，并与具体任务双向关联。简单任务允许直接实现；不强行加入模式。

交付回写 Issue，并提供 `design-deliverable`：`design.md`、`task-contracts.md`、`decisions.md`、`design.json`、`README.md`，保留 30 天。JSON 契约由可信脚本校验，失败不会冒充设计成功；正文和任务表来自同一份数据。开发代码、创建子 Issue/PR、合并和部署均不属于这两个角色的执行范围。设计正文是提案，其业务正确性仍需结合实际需求评审。
