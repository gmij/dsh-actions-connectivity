# Issue 自动化验证

2026-10-11，默认分支已部署 Issue DSH agent 工作流。

| 验证 | 结果 |
|---|---|
| 新 Issue 的 Agent 表单字段选择 connectivity | 自动启动并回写 ISSUE_AGENT_AUTOMATION_OK |
| Issue 带 agent:reviewer 标签 | 自动选择 reviewer，指出示例代码的空列表除零并给出修复建议 |
| 相同 Issue 再出现 assigned 事件 | route 跳过相同任务，agent/publish jobs skipped，没有重复推理 |
| 未选择/未知/停用/多个 agent 标签、任务变更指纹 | 本地 6 个路由测试通过 |
| 本地 DSH 禁工具 overlay | 启动配置通过，执行到凭据缺失错误；云端真实推理通过 |

- [连通性 Issue #1](https://github.com/gmij/dsh-actions-connectivity/issues/1)
- [审查 Issue #2](https://github.com/gmij/dsh-actions-connectivity/issues/2)
- [connectivity 运行](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38107034759)
- [reviewer 运行](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38107063477)
- [assigned 去重运行](https://github.com/gmij/dsh-actions-connectivity/actions/runs/38107083477)

测试 #2 创建后很快添加标签，opened 的路由读取了最新 Issue 标签并启动 reviewer；后续 labeled 运行等待时被更新的 assigned 事件替换，符合 GitHub concurrency 一个等待运行的语义。
未测试实际代码修改/PR 交付；当前 Issue agent 工具禁用，仅输出分析。测试 Issue 保留作为证据。
