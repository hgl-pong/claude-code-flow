# Claude Code Flow

通用开发工作流插件，通过模型分层 Agent 编排 Plan -> Implement -> Review 流水线，支持会话持久化、DAG 任务调度、动态重规划和自我演化。

## 特性

### 核心编排
- 模型分层 — Opus(规划/架构), Sonnet(实现/测试/审查/文档), Haiku(构建)
- 模式选择 — quick/standard/deep/autonomous 四种模式，按任务复杂度自动推荐
- DAG 任务图 — 依赖感知的并行调度，支持循环检测
- Plan Gate — 复杂任务生成 HTML 可视化方案，浏览器审阅确认
- Review Gate — 实现后自动代码审查，拦截问题再提交
- 状态机 — 严格的阶段转换规则，编排器通过状态文件协调 Agent

### 会话持久化
- 状态快照 — SessionStart/SessionEnd 自动快照，中断后可恢复
- 会话恢复 — `/workflow-resume` 从最近快照恢复工作流进度
- 上下文压缩 — PreCompact hook 在上下文压缩前保存关键状态摘要

### 可观测性
- 结构化日志 — JSONL 格式执行日志，支持 session_id 关联
- 指标收集 — Agent 调用次数、阶段耗时、完成率、审查通过率
- 执行时间线 — `/workflow-timeline` 查看完整会话时间线
- 跨会话趋势 — `/workflow-metrics` 查看历史完成率和效率趋势

### 智能恢复
- 动态重规划 — 失败后四级决策：Investigate/Fix/Note/Escalate
- 错误分类 — 语法/依赖/逻辑/环境自动分类处理
- 文件所有权 — 追踪每个文件的修改 Agent，便于冲突检测

### 自我演化
- 元提示词演化 — evolver agent 分析日志，提出 Agent prompt 改进建议
- 技能库自生长 — 从未匹配任务中自动检测新技能需求
- 规则累积 — 从纠错中提取通用规则，sentinel 审查时检查违规
- 评估门控 — 所有自演化变更必须通过 eval-gate 校验才能应用

### 安全与自动化
- Pre-commit Hook — 提交前检测未审查的更改
- Agent 编排验证 — PreToolUse(Agent) 验证阶段转换合法性
- Statusline — 底部状态栏显示工作流阶段、任务进度、Git 信息

## Agent

| Agent | 模型 | 职责 |
|-------|------|------|
| `oracle` | Opus | 实现规划, 分阶段路线图, HTML 可视化 |
| `atlas` | Opus | 架构设计, 模块拆分, API 设计 |
| `evolver` | Opus | 元代理, 分析日志提出 prompt 改进 |
| `forge` | Sonnet | 代码实现 |
| `prism` | Sonnet | 测试框架, 单元/集成/性能测试 |
| `sentinel` | Sonnet | 代码审查, 正确性/安全/架构合规 |
| `scout` | Sonnet | Web 调研, 文档查找, 技术对比 |
| `chronicler` | Sonnet | 文档生成, 变更日志, API 文档 |
| `anvil` | Haiku | 构建, CI/CD, 依赖管理 |

## Commands

| 命令 | 说明 |
|------|------|
| `/workflow-plan` | 启动规划流水线，支持 `--mode quick\|standard\|deep\|autonomous` |
| `/quick-fix` | 快速修复模式，跳过规划直接实现 |
| `/workflow-resume` | 从最近快照恢复中断的工作流 |
| `/workflow-review` | 启动审查流水线 |
| `/workflow-status` | 查看当前工作流状态、模式、指标 |
| `/workflow-timeline` | 查看当前会话的完整执行时间线 |
| `/workflow-metrics` | 查看跨会话的趋势指标 |
| `/workflow-evolve` | 分析执行日志，审批 prompt 改进提案 |
| `/workflow-skills` | 管理技能库，审批自动检测的新技能 |
| `/code-review` | 独立代码审查 |
| `/write-tests` | 独立测试编写 |
| `/build-check` | 独立构建检查 |

## 模式选择

| 模式 | 适用场景 | Research | Design | Plan 审批 | Review | 自动重试 |
|------|----------|----------|--------|-----------|--------|----------|
| `quick` | Bug 修复、单文件改动、配置变更 | 跳过 | 跳过 | 跳过 | 可选 | 否 |
| `standard` | 功能开发、多文件改动 | 按需 | 跳过 | 需要 | 需要 | 否 |
| `deep` | 新系统、架构重构、复杂集成 | 需要 | 需要 | HTML 审批 | 需要 | 是 |
| `autonomous` | 给定目标，完全自主交付 | 自动 | 自动 | 自动 | 自动 (3 轮) | 是 |

## Skills

| Skill | 触发场景 |
|-------|----------|
| `dev-orchestrator` | 主编排, 分析任务、选择模式、DAG 调度、分发 Agent |
| `code-quality` | 代码质量标准, 最佳实践 |
| `testing-strategy` | 测试策略, TDD, 测试金字塔 |

## Hooks

| 事件 | 功能 |
|------|------|
| SessionStart | 检查 git 分支和未提交更改, 快照当前状态 |
| PostToolUse(Write/Edit) | 跟踪已修改文件列表 + Agent 所有权记录 |
| PreToolUse(Bash) | 拦截 git commit，提示未审查的更改 |
| PreToolUse(Agent) | 编排验证，确保正确的阶段转换 |
| PreCompact | 上下文压缩前保存状态摘要到 `pre-compact-context.md` |
| SubagentStop | 记录 Agent 完成日志 (txt + JSONL) |
| Stop | 持久化工作流状态摘要 (txt + JSONL) |
| SessionEnd | 快照当前工作流状态 |

## 工作流

```
模式选择 (quick / standard / deep / autonomous)
      |
      v
Research (scout)  -- 按需 (quick 模式跳过)
      |
      v
Plan Gate (oracle)
  quick:   跳过或内联
  standard: 文本摘要 -> 内联确认
  deep:    HTML 可视化 -> 浏览器审阅
  auto:    自动批准
      |
      v
Design Gate (atlas)  -- 仅 deep 模式 / 新系统
      |
      v
Implementation (forge + prism + anvil)
  DAG 感知调度, 依赖感知并行
      |
      v
Review Gate (sentinel)
  quick: 可选  |  standard/deep: 必须  |  auto: 自动处理
      |
      v
Documentation (chronicler)  -- 按需
      |
      v
报告 & 完成
```

## 自我演化

系统通过以下机制持续改进：

```
工作流执行 -> 结构化日志 (exec-log.jsonl)
      |
      v
evolver (Opus) 分析日志
  - 识别失败模式 (哪个 Agent 最常失败、哪种任务审查轮次最多)
  - 生成 prompt 改进提案 -> evolution-pending.md
      |
      v
用户审批 (/workflow-evolve)
      |
      v
eval-gate 校验 (PASS/WARN/FAIL)
      |
      v
应用改进 -> Agent prompt 文件更新
```

同时支持：
- **技能库自生长**: 未匹配任务自动记录，同一类出现 3+ 次自动生成技能提案
- **规则累积**: 每次纠错后判断是否应成为通用规则，sentinel 审查时检查违规

## 使用示例

```
# 快速修复
/quick-fix Fix the null pointer in auth middleware

# 标准功能开发
/workflow-plan Add user authentication with OAuth and JWT

# 深度架构重构
/workflow-plan --mode deep Refactor the database layer to use repository pattern

# 自主交付
/workflow-plan --mode autonomous Build a REST API for user management

# 恢复中断的工作流
/workflow-resume

# 查看状态和指标
/workflow-status
/workflow-timeline
/workflow-metrics

# 自我演化
/workflow-evolve
/workflow-skills

# 独立命令
/code-review src/auth/
/write-tests src/api/handlers.ts
/build-check
```

## 结构

```
claude-code-flow/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── agents/
│   ├── oracle.md          # Opus — 规划 + HTML 可视化
│   ├── atlas.md           # Opus — 架构设计
│   ├── evolver.md         # Opus — 元代理, prompt 演化
│   ├── forge.md           # Sonnet — 代码实现
│   ├── prism.md           # Sonnet — 测试
│   ├── sentinel.md        # Sonnet — 审查
│   ├── scout.md           # Sonnet — 调研
│   ├── chronicler.md      # Sonnet — 文档生成
│   └── anvil.md           # Haiku — 构建
├── commands/
│   ├── workflow-plan.md   # 规划流水线 (支持 --mode)
│   ├── quick-fix.md       # 快速修复
│   ├── workflow-resume.md # 恢复中断工作流
│   ├── workflow-review.md # 审查流水线
│   ├── workflow-status.md # 当前状态 + 指标
│   ├── workflow-timeline.md # 执行时间线
│   ├── workflow-metrics.md  # 跨会话指标
│   ├── workflow-evolve.md   # prompt 演化
│   ├── workflow-skills.md   # 技能库管理
│   ├── code-review.md     # 独立审查
│   ├── write-tests.md     # 独立测试
│   └── build-check.md     # 独立构建检查
├── skills/
│   ├── dev-orchestrator/  # 主编排 (v2.0 — 模式选择 + DAG + 动态重规划)
│   ├── code-quality/
│   └── testing-strategy/
├── hooks/
│   ├── hooks.json
│   └── scripts/
│       ├── flow-state.py       # 状态机 (快照/恢复/归档/富状态)
│       ├── log-event.py        # 通用结构化日志工具
│       ├── session-check.py    # git 状态 + session_id 生成
│       ├── track-changes.py    # 文件修改追踪 (txt + JSONL 所有权)
│       ├── task-graph.py       # DAG 任务图 (循环检测/并行调度)
│       ├── on-agent-complete.py # Agent 完成日志
│       ├── on-workflow-stop.py  # 工作流停止日志
│       ├── on-compact.py       # 上下文压缩前保存状态
│       ├── metrics.py          # 指标聚合 (collect/aggregate/raw)
│       ├── pre-commit-guard.sh # 提交拦截 + 拦截记录
│       ├── pre-agent-guard.sh  # Agent 编排验证 + 拦截记录
│       ├── eval-gate.py        # 演化评估门控 (PASS/WARN/FAIL)
│       ├── rule-evaluator.py   # 规则累积 (propose/check/evaluate)
│       ├── skill-detector.py   # 技能匹配 + 自动检测
│       └── apply-evolution.py  # 应用已批准的演进提案
├── .claude/flow/              # 运行时数据 (建议 .gitignore)
│   ├── workflow-state.json    # 工作流状态
│   ├── phase-context.md       # 阶段上下文
│   ├── exec-log.jsonl         # 结构化执行日志
│   ├── modified-files.txt     # 已修改文件列表
│   ├── modified-files.jsonl   # 文件所有权日志
│   ├── task-graph.json        # DAG 任务图
│   ├── rules.json             # 累积规则库
│   ├── skill-seeds.json       # 技能种子库
│   ├── snapshots/             # 状态快照
│   └── archive/               # 已归档快照
└── scripts/
    └── statusline.sh
```

## 安装

```
/plugin marketplace add hgl-pong/claude-code-flow
/plugin install claude-code-flow@claude-code-flow
/reload-plugins
```

## Statusline

底部状态栏显示当前工作流状态。

显示内容:
- 工作流阶段 (plan/design/impl/review/idle)
- 工作模式 (quick/standard/deep/autonomous)
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

> 注意: 工作流运行时数据存储在 `.claude/flow/` 目录中，建议将其添加到项目的 `.gitignore`。
