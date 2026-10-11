# DSH + GitHub Actions + Copilot

这是 DSH 集成测试仓库。DSH 是执行引擎，推理模型由各角色的注册配置选择，通过 GitHub Copilot API 接入。

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

DSH 可用角色见 [agents/registry.json](agents/registry.json)，目前启用 connectivity、reviewer、prototype、overview 和 detailed。
新建 Issue 可选择“指派 DSH agent”模板，在 Agent 字段选择角色。
已有 Issue 推荐通过原生 Assign to Agent 下拉框选择角色；旧标签路由保留兼容。
状态、结果和运行链接回写 Issue；同一 Issue 串行，相同任务去重。
Issue 自动化使用禁执行工具的 DSH；按角色交付审查建议、交互原型或概要/详细设计，由可信脚本校验并回写。
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

结果回写 Issue，并附 `prototype-deliverable` 交付包：`decision.json`、`requirements.md`、`design.md`、`README.md`，需要原型时另有 `index.html`。在线预览通过 GitHub Pages 自动发布并回写 Issue；也可下载并解压后用浏览器打开 HTML。交付包保留 30 天，可自行下载留存。当前交付是交互原型和演示数据，未连接真实业务后端。

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

通过原生 Assign to Agent 选择 **DSH Overview Design** 或 **DSH Detailed Design**，仍由 MCP 调度到真实 DSH。实际模型由 `agents/registry.json` 的角色配置控制，调度层 Model 下拉框不会覆盖它。

模型选择：概要与详细设计现使用 `claude-haiku-5.5`，已通过真实 DSH、V2 契约校验与 Wiki 发布。采用显式 `anthropic-messages` 协议，概要输出预算 65,536 token，详细设计 128,000 token；每次设计推理最多 15 分钟，最多一次修复，Actions 作业上限 35 分钟。正式 `gpt-5.4` 的成功 Actions 记录保留为对照；无效输出不会替换 Wiki 成功版本。简单连通性与其他角色的模型配置独立；DSH 名称不代表调用 DeepSeek 推理模型。

### 设计顺序：MVP 里程碑 → 模块 → 模块内任务

先定义用户可操作的最小产品增量及版本路径，再完成模块整体设计，最后拆模块内任务。任务是实现单元；里程碑是集成验收和发布单位。模块可以跨里程碑迭代，不能用“完成数据库/适配器/前端骨架”代替一个可交互 MVP。

每个里程碑写清用户价值、从入口到结果的操作路径、前置里程碑、跨模块任务、集成测试的环境/数据/步骤/预期、发布门槛、部署和回滚。Web 产品每个里程碑必须包含前端、后端、集成验证、文档任务；API/CLI 产品明确交互入口及不做界面的理由。全部任务完成且里程碑验收通过后，才具备发布条件；设计 Agent 不会自动执行开发或发布。

模块先说明职责、边界、数据所有权、内部设计、前端页面、后端、接口与文档，再给模块内任务。前端包含路由、组件布局、操作、加载/空/错误/成功状态、API/DTO 映射及界面验收；后端包含请求响应、权限、持久化、事务、并发、重试固定上限和幂等。没有界面职责的后端模块明确由哪个模块负责页面，不给每个模块硬造 UI。

每项任务有层次和里程碑归属，以及准确输入输出、依赖、拟定实现落点、失败行为、验收及测试。生产者输出和消费者输入名称/类型匹配，依赖无环；模式/技术选择写清问题、采用理由、替代方案、代价及具体落点。校验器拒绝跨到未来或无关里程碑的依赖、缺前端/联调/文档的 Web 发布单元和任务归属不一致。

详细设计同步提供完整、与模块和里程碑一致的概要模块章节；作为独立同步文档，不在详细正文前拼接第二份概要。总体文档只保留架构和导航，不复制全量任务。按实际职责拆分，达到 6 项任务或总正文/模块正文超过 20000 字符时至少两个模块。

### 一体化交付与 Wiki 阅读

V2 JSON 的任务嵌套在 `modules[].tasks`；顶层不再有全局 tasks。产物统一生成：

- `design.md`：完整设计入口、MVP 路径、模块导航与跨模块架构。
- `milestones.md`：用户闭环、跨模块任务、集成验收、发布及回滚。
- `modules/MOD-xx.md`：模块整体设计、前端/后端/接口/文档，随后是所属任务完整契约。
- `ui.md`：页面布局、交互、状态、实际桌面截图、手机截图与本轮 Pages 入口。
- `api-contracts.md` 和 `apis/API-xx.md`：逐接口独立文档，路径/查询/请求体字段类型、必填、可空、边界与示例，各成功/错误状态的响应契约、所属后端模块和任务。
- `frontend-bindings.md`：逐页面动作到 API、请求字段来源、响应字段去向，以及加载/成功/失败处理。
- `documentation.md`：使用/接口/运行/部署文档交付与验收清单。
- `task-contracts.md`：按模块组织的任务索引；完整任务契约位于模块内。
- `decisions.md`、`design.json`，详细设计另有 `overview-update.md`。

Web 设计必须同轮交付结构化 HTTP 契约、页面字段映射及可运行 HTML。可信脚本校验后，隔离浏览器生成桌面与手机 PNG；Pages 实际部署成功后才发布 Wiki、回填真实链接和截图。契约或截图失败不会发布缺项文档。

设计成功后自动发布 Wiki，原 Issue 回填目录、最新设计和固定版本链接。阅读顺序为设计入口 → MVP 里程碑 → 模块 → 模块内任务；界面与文档可从侧栏进入。不要求下载 Markdown。

请把需求、已确认讨论结论、概要和原型约束写进 Issue 或仓库可读文档；目前不自动抓取其他 Issue、Discussion 或外部链接正文。缺原型/基线时明确拟定与待确认；不能伪造已读取、已批准或已修改的事实。

新 DSH 输出必须符合 V2。首次失败有一次带具体错误的契约修正，仍不合格则失败并保留诊断；不伪造成功。历史 V1 制品保留原有渲染，以保持已发布 Wiki 固定版本不变，旧版本补发不会覆盖最新 V2。此前原生调度及真实 DSH 设计验收记录见 Issue #16/#17 和 Wiki 版本历史。

## Discussions、Issues 与 Wiki 的协作约定

| 位置 | 保存内容 | 进入执行的条件 |
|---|---|---|
| Discussions | 需求澄清、方案比较、过程交流、开放问题和共识 | 人确认后，将结论整理到 Issue，并互相链接 |
| Issues | 已确认需求、输入约束、Agent、依赖、验收条件、执行状态及结果证据 | 在原生 Assign to Agent 下拉框指派指定 DSH 角色 |
| Wiki | 概要和模块详细设计、任务输入输出、模式依据、概要修订及历史版本 | 可信发布器读取成功的 DSH 设计交付 |

共享规则见 [agents/collaboration-instructions.md](agents/collaboration-instructions.md)，已注入实际 DSH 工作提示词，规则变更会更新任务指纹。讨论或 Wiki 更新本身不启动执行；模型提案不等于业务批准。当前不会自动创建或回复 Discussion，也不会自动读取其链接正文，请将关键已确认结论粘贴到 Issue。日常聊天不会自动整段搬运到仓库。

## GitHub Wiki 设计文档同步

`Design Wiki` 在 `Prototype Pages` 部署成功后校验本仓库默认分支上的来源，跳过非设计角色，再把设计交付同步为可直接阅读的 Wiki 页面：文档目录、侧栏、概要/详细设计、逐任务契约、设计决策、独立模块、概要同步修订与历史版本。保留人工页面及 Home/侧栏中的人工内容；不执行模型输出。最新页面与按 DSH run 固定的版本同时保存，补发旧运行不会倒退最新版本。Wiki 的设计完成不代表业务验收通过。

发布成功后才在原 Issue 写入真实 Wiki 链接。同步失败时仍保留可检查的 `design-wiki-preview`，修复后重跑发布工作流即可，无需重新调用模型。Actions → Design Wiki → Run workflow 可输入逗号分隔的成功运行 ID；dry_run 只生成预览。首次启用 Wiki 后，需要在 Wiki 中创建首个 Home 页面以初始化 Wiki Git 后端。默认使用本仓库 GITHUB_TOKEN；若 Wiki 写权限不支持该身份，可配置仅覆盖本仓库的 `WIKI_PUBLISH_TOKEN`。发布器正常推送，不强制覆盖历史。

### Wiki 与协作规范验证（2026-10-11）

42 项单元测试已在本地和 Design Wiki 的真实 Actions 测试阶段通过，包含协作规范注入/任务指纹、目录及模块导航、人工页面保留、版本不可变、旧版本补发及模块调整后的侧栏。首次发布因 Wiki 未初始化失败；用户创建 Home 后，重新运行 [38115868477（attempt 2）](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38115868477/attempts/2)，test/publish 均成功。概要 #16 与模块详细设计 #17 已真实推送到 Wiki，使用本仓库 GITHUB_TOKEN，无需新增个人 PAT；保留首页人工内容。共生成 26 个预览/索引文件，含目录、侧栏、任务契约、模式依据、3 个模块、概要修订及固定历史版本。两个 Issue 均已回填 Wiki 链接：[概要回填](https://github.com/gmij/dsh-actions-connectivity/issues/16#issuecomment-6105999843)、[详细设计回填](https://github.com/gmij/dsh-actions-connectivity/issues/17#issuecomment-6105999950)。

阅读入口：[Wiki 文档目录](https://github.com/gmij/dsh-actions-connectivity/wiki/DSH-Documents)。从这里进入 [概要设计](https://github.com/gmij/dsh-actions-connectivity/wiki/Issue-16-Overview) 或 [模块详细设计](https://github.com/gmij/dsh-actions-connectivity/wiki/Issue-17-Detailed)。以后成功的设计交付会自动发布并在原 Issue 引导到 Wiki；无需下载 Markdown。此次复用了已有成功 DSH 设计，不是重新调用模型，未声称完成浏览器视觉检查。


### 本轮可视原型与接口契约验收（2026-10-11）

重新生成前，清理运行 [38128465180](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38128465180) 删除 41 个 Wiki 文件，只保留原 Home 并验证逐字节不变；一次性清理工作流已移除。随后真实 DSH 使用 Claude Haiku 5.5 重新生成概要与详细设计：

- 概要源运行 [38128528526](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38128528526) 的 route/agent/capture/publish 全部成功；Pages [38129381834](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38129381834) 与 Wiki [38129427814（attempt 2）](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38129427814/attempts/2) 成功。源运行的汇总状态曾延迟，发布器仅在全部必需作业已完成并成功时允许人工补发。
- 详细源运行 [38129771299](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38129771299) 成功，交付 1 个 MVP、4 个模块、6 个模块内任务、5 个独立 HTTP 接口与 5 组页面动作映射。Pages [38130255180](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38130255180) 和 Wiki [38130298379](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38130298379) 均成功，Issue #17 已回填真实链接。
- 58 项单元测试通过；隔离 Chromium 实际生成 1100×900 桌面与 390×844 手机全页 PNG，检查脚本错误、关键控件与横向溢出；两种截图已人工查看。未声称完成在线浏览器全流程交互测试。

阅读入口：[Wiki 目录](https://github.com/gmij/dsh-actions-connectivity/wiki/DSH-Documents) · [详细界面设计及截图](https://github.com/gmij/dsh-actions-connectivity/wiki/Issue-17-Detailed-UI) · [逐接口契约](https://github.com/gmij/dsh-actions-connectivity/wiki/Issue-17-Detailed-APIs) · [页面到接口字段映射](https://github.com/gmij/dsh-actions-connectivity/wiki/Issue-17-Detailed-Bindings) · [本轮交互原型](http://gmij.win/dsh-actions-connectivity/previews/issue-17/runs/38129771299/)。

原型使用本地演示数据；业务后端、数据库迁移与里程碑集成验收仍待实际开发和执行。模型输出的设计提案不会自动发布业务产品。
