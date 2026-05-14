# Claude Code Flow

Claude Code 开发工作流插件。6 个专职 Agent + UI 设计 Skill、模型分层、门控流水线、会话持久化、关键词路由。

## 核心概念

- **Structured Plan State**: Plan 权威在 `.claude/flow/plan-state.json` 和 `workflow-state.json`，`plan_hash` 追踪方案身份，`plan-brief.md` 是 agent 交接层（含 Decisions/Rejected/Risks 字段）
- **Plan Mode Routing**: `/plan` 是唯一插件规划入口，`PreToolUse(EnterPlanMode)` 拦截内置 plan mode
- **Host-level plan transitions**: Shift+Tab / SDK `set_permission_mode` 等宿主转换无法被插件拦截，需退出后重跑 `/plan`
- **Quick-fix routing**: 按 `forge` / `prism` 任务域分发，非默认路由到 backend/general
- **Keyword routing**: UserPromptSubmit hook 自动检测任务模式关键词，推荐匹配 skill

## Agent

| Agent | 模型 | 职责 | Prompt Schema |
|-------|------|------|---------------|
| `oracle` | Opus xhigh | 规划 + 架构 + UI 设计决策 | Role → Iron Law → Guards → Process → Failure Modes → Self-Review |
| `forge` | Sonnet high | 全栈实现（后端 + 前端） | Role → Iron Law → Guards → Process → Failure Modes → Self-Review |
| `prism` | Sonnet high | 测试 + 构建 + 验收 | Role → Iron Law → Guards → Process → Failure Modes → Self-Review |
| `sentinel` | Sonnet high | 代码审查（两阶段） | Role → Iron Law → Guards → Process → Failure Modes → Self-Review |
| `artist` | Haiku | 图像生成与识别 | Role → Iron Law → Guards → Process → Failure Modes → Self-Review |

研究由 `research` skill 处理，通过 general-purpose subagent 调度，无需专用 agent。所有 agent 统一 prompt schema。`sentinel` 是只读 agent。UI 设计由 `ui-design` skill 处理。

## 工作流

```
模式选择 (quick / standard / deep / autonomous)
      |
      v
Research (general-purpose subagent + research skill) ──── 按需（quick 跳过）
      |
      v
Plan + Architecture (oracle)
  quick:    跳过或内联
  standard: 文本摘要 → 内联确认
  deep:     HTML 可视化 → 浏览器审阅
  auto:     自动批准
      |
      v
UI Design (ui-design skill) ── 仅前端任务 + standard 以上模式，oracle 决定
      |
      v
Implementation (forge) ── 全栈实现
      |
      v
Testing + Acceptance (prism) ── 测试、构建、验收
      |
      v
Review (sentinel) ── 两阶段审查
  quick: 可选 | standard/deep: 必须 | auto: 自动
      |
      v
完成
```

## Commands

### 核心流水线

| 命令 | 说明 |
|------|------|
| `/plan [--mode] <task>` | 插件规划入口，启动规划流水线 |
| `/quick-fix <task>` | 快速修复，跳过规划直接实现 |
| `/execute-plan <plan>` | 执行已批准的方案 |
| `/workflow-resume` | 恢复中断的工作流 |

### 独立命令

| 命令 | 说明 |
|------|------|
| `/code-review [files]` | 代码审查 |
| `/write-tests [target]` | 编写测试 |
| `/build-check` | 构建检查 |

### 诊断

| 命令 | 说明 |
|------|------|
| `/workflow-status` | 当前状态、模式、指标 |
| `/workflow-timeline` | 当前会话执行时间线 |
| `/workflow-metrics` | 跨会话趋势指标 |
| `/workflow-skills` | 技能库管理 |

### 自主模式

| 命令 | 说明 |
|------|------|
| `/ulw <task>` | Ultrawork — 单任务全自主 |
| `/uli <goal>` | ULI — 产品迭代循环 |

## Skills

Skills 使用渐进式披露：精简 SKILL.md（< 3000 词）+ `references/` 按需加载。所有 skill 支持 Standalone 模式（零工具可用）+ Enhanced 模式（连接 GitNexus/Tavily 等增强）。

| Skill | 触发场景 |
|-------|----------|
| `dev-orchestrator` | 多步开发任务编排、Agent 调度、流水线管理 |
| `using-claude-code-flow` | 未被命令或 hook 路由时做一次 workflow skill 选择 |
| `ui-design` | UI/UX 设计规格、组件设计、色彩/排版系统、design tokens |
| `brainstorming` | 将粗略想法细化为批准的设计 |
| `writing-plans` | 从设计创建实现计划（含 Decisions/Rejected/Risks） |
| `testing-strategy` | 测试策略、TDD、测试金字塔 |
| `code-quality` | 代码质量标准、最佳实践 |
| `systematic-debugging` | 系统化调试：复现 → 定位 → 证明 → 修复 |
| `verification-before-completion` | 完成前要求新鲜验证证据 |
| `web-search` | Tavily CLI 联网搜索 |

## 模式选择

| 模式 | 适用场景 | Research | Architecture | Plan | UI Design | Review | Auto-retry |
|------|----------|----------|-------------|------|-----------|--------|------------|
| `quick` | Bug 修复、单文件改动 | 跳过 | 跳过 | 跳过 | 跳过 | 可选 | 否 |
| `standard` | 功能开发、多文件改动 | 按需 | 按需 | 需要 | UI 任务需要 | 需要 | 否 |
| `deep` | 新系统、架构重构 | 需要 | 需要 | HTML 审批 | UI 任务需要 | 需要 | 是 |
| `autonomous` | 给定目标，完全自主 | 自动 | 自动 | 自动 | 自动 | 自动 (3 轮) | 是 |

## Hooks

| 事件 | 功能 |
|------|------|
| UserPromptSubmit | ULW/ULI/plan 模式检测 + 关键词 skill 路由 |
| SessionStart | git 状态检查、session_id 生成、状态快照 |
| PostToolUse(Write/Edit) | 文件修改追踪 + Agent 所有权 |
| PostToolUse(Bash) | 验证证据追踪（test/build/lint 分类） |
| PreToolUse(Bash) | 拦截 `git commit`（未审查文件时） |
| PreToolUse(Agent) | sentinel 前置检查（需有修改文件） |
| PreToolUse(EnterPlanMode) | 拦截内置 plan mode → 路由到 `/plan` |
| PreCompact / PostCompact | 上下文压缩前后保存/恢复状态 |
| SubagentStart / SubagentStop | Agent 启停日志 |
| Stop | ULW/ULI 完成检测 + 工作流状态持久化 |
| SessionEnd | 状态快照 + GitNexus 索引更新 |

## 结构

```
claude-code-flow/
├── agents/                # 5 个专职 Agent
│   ├── oracle.md          # Opus — 规划 + 架构 + UI 设计决策
│   ├── forge.md           # Sonnet — 全栈实现
│   ├── prism.md           # Sonnet — 测试 + 构建 + 验收
│   ├── sentinel.md        # Sonnet — 代码审查
│   ├── artist.md          # Haiku — 图像生成
│   └── references/        # Agent 共享知识库
├── commands/              # Slash 命令
├── skills/                # 技能（渐进式披露：SKILL.md + references/）
├── hooks/                 # Hook 脚本
│   ├── hooks.json         # Hook 注册
│   └── scripts/           # Python/Bash 脚本（含 keyword-router.py）
├── .claude/flow/          # 运行时状态（gitignored）
└── scripts/
    └── statusline.sh      # 底部状态栏
```

## 安装

### 必需

```bash
# GitNexus（代码索引）
npm install -g gitnexus
gitnexus analyze .

# Tavily（联网搜索）
pip install tavily-python
echo "your-api-key" > ~/.tavily
cp skills/web-search/tavily-cli ~/bin/tavily && chmod +x ~/bin/tavily
```

### 可选

```bash
# img-cli（artist agent）
cd vendor/img-cli && pip install -e . && cd ../..
```

### 安装插件

```
/plugin marketplace add hgl-pong/claude-code-flow
/plugin install claude-code-flow@claude-code-flow
/reload-plugins
```

```cmd
claude plugin uninstall claude-code-flow@claude-code-flow
claude plugin marketplace remove claude-code-flow
claude plugin marketplace add hgl-pong/claude-code-flow
claude plugin install claude-code-flow@claude-code-flow
```

## Statusline

底部状态栏显示：模型名称、上下文用量（进度条）、会话花费、限额使用率、工作流阶段、任务进度、Git 分支、验证状态。

**自动安装**：插件安装后首次启动 Claude Code 时，`SessionStart` hook 会自动将 statusline 写入 `~/.claude/settings.json`，无需手动配置。重载插件后即生效：

```
/reload-plugins
```

**手动配置**（如需覆盖）：编辑 `~/.claude/settings.json`：

```json
{
  "statusLine": {
    "type": "command",
    "command": "bash /path/to/claude-code-flow/scripts/statusline.sh"
  }
}
```

**效果预览：**

```
Sonnet myproject  main*↑1 │ ▓▓▓▓▓░░░░░ 47% │ $0.012 │ 5h:23% 7d:41%
flow:impl 3/5 ✓
```

| 字段 | 说明 |
|------|------|
| 模型名 | 当前模型（蓝色） |
| 目录名 | 项目目录 |
| Git 分支 | 绿色=clean，黄色=dirty，红色=behind；`↑N`/`↓N` 显示 ahead/behind |
| 进度条 | 上下文用量（绿 <70%，黄 70–89%，红 ≥90%） |
| `$N.NNN` | 当前会话花费（为 0 时隐藏） |
| `5h:N% 7d:N%` | Pro 用量（≥60% 黄色，≥80% 红色；非 Pro 用户不显示） |
| `flow:impl 3/5 ✓` | 工作流阶段 + 任务进度 + 验证状态 |
| `⚡ulw:refactor 2/5 #1` | ULW 自主模式状态 |

依赖：`python3`（必须）或 `jq`（可选，解析更快）。

## 测试

```bash
# 快速回归测试
python tests/run-tests.py

# E2E 测试（可选，消耗 token）
bash tests/claude-code/run-e2e-tests.sh
```
