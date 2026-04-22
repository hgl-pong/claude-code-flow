# Claude Code Flow

通用开发工作流插件，通过模型分层 Agent 编排 Plan -> Implement -> Review 流水线。

## 特性

- 模型分层 — Opus(规划/架构), Sonnet(实现/测试/审查/文档), Haiku(构建)
- Plan Gate — 复杂任务生成 HTML 可视化方案，浏览器审阅确认
- Review Gate — 实现后自动代码审查，拦截问题再提交
- 状态机 — 严格的阶段转换规则，编排器通过状态文件协调 Agent
- 上下文保持 — 阶段间通过 `phase-context.md` 传递上下文
- 错误恢复 — Agent 超时重试、输出格式修正、阶段转换校验
- 混合编排 — 流水线自动编排 + 独立命令按需使用
- SessionStart — 启动时自动检查 git 状态并清理工作流状态
- Pre-commit Hook — 提交前检测未审查的更改
- Agent 编排验证 — PreToolUse(Agent) 验证阶段转换合法性
- Statusline — 底部状态栏显示工作流阶段、任务进度、Git 信息

## Agent

| Agent | 模型 | 职责 |
|-------|------|------|
| `oracle` | Opus | 实现规划, 分阶段路线图, HTML 可视化 |
| `atlas` | Opus | 架构设计, 模块拆分, API 设计 |
| `forge` | Sonnet | 代码实现 |
| `prism` | Sonnet | 测试框架, 单元/集成/性能测试 |
| `anvil` | Haiku | 构建, CI/CD, 依赖管理 |
| `sentinel` | Sonnet | 代码审查, 正确性/安全/架构合规 |
| `chronicler` | Sonnet | 文档生成, 变更日志, API 文档 |

## Commands

| 命令 | 说明 |
|------|------|
| `/workflow-plan` | 启动规划流水线 |
| `/workflow-review` | 启动审查流水线 |
| `/workflow-status` | 查看当前工作流状态 |
| `/code-review` | 独立代码审查 |
| `/write-tests` | 独立测试编写 |
| `/build-check` | 独立构建检查 |

## Skills

| Skill | 触发场景 |
|-------|----------|
| `dev-orchestrator` | 主编排, 分析任务并分发 Agent |
| `code-quality` | 代码质量标准, 最佳实践 |
| `testing-strategy` | 测试策略, TDD, 测试金字塔 |

## Hooks

| 事件 | 功能 |
|------|------|
| SessionStart | 检查 git 分支和未提交更改, 清理工作流状态 |
| PostToolUse(Write/Edit) | 跟踪已修改文件列表 |
| PreToolUse(Bash) | 拦截 git commit，提示未审查的更改 |
| PreToolUse(Agent) | 编排验证，确保正确的阶段转换 |
| SubagentStop | 记录 Agent 完成日志 |
| Stop | 持久化工作流状态摘要 |
| SessionEnd | 清理工作流状态文件 |

## Statusline

底部状态栏显示当前工作流状态。

显示内容:
- 工作流阶段 (plan/design/impl/review/idle)
- 任务进度 (x/y)
- Git 分支和 ahead/behind 计数
- 已修改文件数

配置方法 — 在项目的 `.claude/settings.json` 中添加：

```json
{
  "statusLine": {
    "type": "command",
    "command": "bash path/to/claude-code-flow/scripts/statusline.sh"
  }
}
```

> 注意: 工作流运行时状态存储在 `.claude/flow/` 目录中，建议将其添加到项目的 `.gitignore`。

## 安装

```
/plugin marketplace add hgl-pong/claude-code-flow
/plugin install claude-code-flow@claude-code-flow
/reload-plugins
```

## 工作流

所有任务经过 Plan -> Implement -> Review 流水线。

```
Plan Gate (oracle, Opus)
  复杂: HTML 可视化 -> 浏览器审阅
  简单: 文本摘要 -> 内联确认
  [等待用户确认]
      |
      v
Design Gate (atlas, Opus)  -- 仅新系统/架构变更
  [等待用户确认]
      |
      v
Implementation
  forge + prism + anvil (并行)
      |
      v
Review Gate (sentinel, Sonnet)
  通过 -> 完成
  未通过 -> 返回修改 -> 重新审查 (最多 3 轮)
      |
      v
Documentation (chronicler, Sonnet)  -- 按需
      |
      v
报告 & 完成
```

## 使用示例

```
/workflow-plan Add user authentication with OAuth and JWT
/workflow-plan Refactor the database layer
/code-review src/auth/
/write-tests src/api/handlers.ts
/build-check
/workflow-review
/workflow-status
```

## 结构

```
claude-code-flow/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── agents/
│   ├── oracle.md          # Opus — 规划 + HTML
│   ├── atlas.md           # Opus — 架构设计
│   ├── forge.md           # Sonnet — 代码实现
│   ├── prism.md           # Sonnet — 测试
│   ├── anvil.md           # Haiku — 构建
│   ├── sentinel.md        # Sonnet — 审查
│   └── chronicler.md      # Sonnet — 文档生成
├── commands/
│   ├── workflow-plan.md
│   ├── workflow-review.md
│   ├── workflow-status.md
│   ├── code-review.md
│   ├── write-tests.md
│   └── build-check.md
├── skills/
│   ├── dev-orchestrator/
│   ├── code-quality/
│   └── testing-strategy/
├── hooks/
│   ├── hooks.json
│   └── scripts/
│       ├── session-check.sh
│       ├── track-changes.sh
│       ├── flow-state.sh
│       ├── on-agent-complete.sh
│       └── on-workflow-stop.sh
└── scripts/
    └── statusline.sh
```
