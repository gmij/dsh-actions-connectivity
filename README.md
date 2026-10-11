# DSH + GitHub Actions + Copilot

这是 DSH 集成测试仓库，已验证 DSH headless 在 Actions 中使用 Copilot gpt-5.4-mini 完成推理。

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

仓库新增两个可选原生 Agent，仍由 MCP 调度到真实 DSH，模型沿用 `gpt-5.4-mini`。当前共 5 个角色；无需新增调度凭据。

| 下拉框名称 | DSH 角色 | 重心 |
|---|---|---|
| DSH Overview Design | overview | 架构、模块边界、领域模型、模块接口、关键流程、里程碑与概要级任务契约 |
| DSH Detailed Design | detailed | 可独立开发的逐任务输入输出、接口示例、实现落点、事务、异常/重试/幂等、验收与测试 |

在现有 Issue 右侧 Assign to Agent → Custom agent 选择相应角色。请把需求、概要设计及原型约束写入 Issue 或仓库设计文档；目前不会自动读取其他 Issue、附件或外部链接的内容，应粘贴相关正文或放入可读取的仓库文件。缺少概要时详细设计会标明最小概要与假设，不能假装已有确认。

输入契约包括名称、准确类型/字段、来源、必填与校验；输出包括名称、准确类型/字段、消费者与成功保证。下游引用格式 `TASK-01.outputName`，必须存在并列出依赖，生产者输出与消费者输入类型必须一致；依赖禁止循环。

详细设计还必须检查语义闭环：拟定方法的全部参数、状态推进信号及去重/幂等键，都要能从输入或上游输出字段取得；关键规则要给出明确暂定方案，不能把缺失字段留给开发补齐。分页累计/消息重放需说明事务与唯一约束，以及提交前后崩溃和并发重复的恢复测试。

每个实际模式/关键技术或模型选择写明：解决的具体问题、为什么采用、替代方案、取舍代价、适用边界、接口/类/模块落点，并与具体任务双向关联。简单任务允许直接实现；不强行加入模式。

交付回写 Issue，并提供 `design-deliverable`：`design.md`、`task-contracts.md`、`decisions.md`、`design.json`、`README.md`，保留 30 天。详细设计按实际职责拆为模块：跨职责、总设计及模块正文合计超过 20000 字符或达到 6 个任务时必须拆分，阈值只是兜底。每个任务恰好归属一个模块，跨模块依赖由任务契约生成。不能把一个混杂的大模块机械切成上下篇，也不为排版引入微服务。

同轮交付 `modules/MOD-xx.md` 独立模块详细设计和 `overview-update.md` 修订后概要模块章节，包含拆分/合并原因、模块职责与边界、接口/依赖、数据所有权及里程碑调整。以已提供概要为基线；未提供时明确按本次需求拟定。该章节可用于替换原概要相应部分，当前工作流交付修订文档，不自动覆盖仓库文件。

JSON 契约由可信脚本校验，失败不会冒充设计成功；正文和任务表来自同一份数据。首次契约不合格时，将具体错误反馈给 DSH，再生成并校验完整设计，最多修正一次；仍不合格则失败，保留两次输出及错误诊断。开发代码、创建子 Issue/PR、合并和部署均不属于这两个角色的执行范围。设计正文是提案，其业务正确性仍需结合实际需求评审。


### 设计角色验收（2026-10-11）

- 原生下拉框确认出现 Overview/Detailed 两个角色，分别指派 Issue #16/#17 后，Copilot 会话通过 MCP 返回 dispatch_accepted 并完成；不添加标签。
- 概要设计 [Issue #16](https://github.com/gmij/dsh-actions-connectivity/issues/16) 的真实 [DSH run 38114770873](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38114770873) route/agent/publish 全部成功，交付架构、4 个里程碑任务、逐任务契约与模式依据。
- 模块化详细设计 [Issue #17](https://github.com/gmij/dsh-actions-connectivity/issues/17#issuecomment-6105854744) 的真实 [DSH run 38115050536](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38115050536) route/agent/publish 全部成功。交付供应商适配、幂等持久化、批次汇总 3 个独立模块，修订后的概要模块章节、模块依赖与对应任务契约。现场核对生产者/消费者 DTO、pageId/hasMore 传递、事务内页去重与批次统计、崩溃重放及 Adapter 决策依据。
- 38 项单元测试通过，含任务依赖、类型一致性、决策关联、模块唯一归属、过大设计必须拆分、概要修订必填、一次修正上限与固定文件路径。首次试验中的无效契约均被校验器拒绝；修复提示结构、错误反馈及文档长度预算后重新完成真实验收。
- 本次模块化运行期间修复了 Issue 中模块相对链接的格式，并用同一已校验 JSON 补全该条 Issue 回写；未来运行会自动包含模块正文。交付包内部模块相对链接保持有效。

## Discussions、Issues 与 Wiki 的协作约定

| 位置 | 保存内容 | 进入执行的条件 |
|---|---|---|
| Discussions | 需求澄清、方案比较、过程交流、开放问题和共识 | 人确认后，将结论整理到 Issue，并互相链接 |
| Issues | 已确认需求、输入约束、Agent、依赖、验收条件、执行状态及结果证据 | 在原生 Assign to Agent 下拉框指派指定 DSH 角色 |
| Wiki | 概要和模块详细设计、任务输入输出、模式依据、概要修订及历史版本 | 可信发布器读取成功的 DSH 设计交付 |

共享规则见 [agents/collaboration-instructions.md](agents/collaboration-instructions.md)，已注入实际 DSH 工作提示词，规则变更会更新任务指纹。讨论或 Wiki 更新本身不启动执行；模型提案不等于业务批准。当前不会自动创建或回复 Discussion，也不会自动读取其链接正文，请将关键已确认结论粘贴到 Issue。日常聊天不会自动整段搬运到仓库。

## GitHub Wiki 设计文档同步

`Design Wiki` 在 Issue DSH agent 成功结束后校验本仓库默认分支上的来源，跳过非设计角色，再把设计交付同步为可直接阅读的 Wiki 页面：文档目录、侧栏、概要/详细设计、逐任务契约、设计决策、独立模块、概要同步修订与历史版本。保留人工页面及 Home/侧栏中的人工内容；不执行模型输出。最新页面与按 DSH run 固定的版本同时保存，补发旧运行不会倒退最新版本。Wiki 的设计完成不代表业务验收通过。

发布成功后才在原 Issue 写入真实 Wiki 链接。同步失败时仍保留可检查的 `design-wiki-preview`，修复后重跑发布工作流即可，无需重新调用模型。Actions → Design Wiki → Run workflow 可输入逗号分隔的成功运行 ID；dry_run 只生成预览。首次启用 Wiki 后，需要在 Wiki 中创建首个 Home 页面以初始化 Wiki Git 后端。默认使用本仓库 GITHUB_TOKEN；若 Wiki 写权限不支持该身份，可配置仅覆盖本仓库的 `WIKI_PUBLISH_TOKEN`。发布器正常推送，不强制覆盖历史。

### Wiki 与协作规范验证（2026-10-11）

42 项单元测试已在本地和 Design Wiki 的真实 Actions 测试阶段通过，包含协作规范注入/任务指纹、目录及模块导航、人工页面保留、版本不可变、旧版本补发及模块调整后的侧栏。真实补发运行 [38115868477](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38115868477) 从概要 #16 和模块详细设计 #17 的成功 DSH 交付生成了 26 个预览文件。仓库 has_wiki/has_discussions 均为 true；但 Wiki Git 后端返回 repository_unavailable，匿名 Git 读取返回 401，发布尚未完成，未回写成功链接。请先在 Wiki 中保存首个 Home 页面，然后重跑此工作流；若 Home 已存在，应检查发布身份权限。当前预览已保留为 design-wiki-preview artifact，不能将其描述为已上线 Wiki。
