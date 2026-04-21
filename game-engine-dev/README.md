# Game Engine Dev Plugin

Claude Code 工作流插件，专为通用/自研游戏引擎开发设计。通过模型分层策略将不同复杂度的任务分配给不同模型层级的 Agent，实现自动化编排。

## 特性

- **模型分层编排** — 根据任务复杂度自动选择模型（Opus/Sonnet/Haiku）
- **自动化任务拆分** — 分析用户需求，拆解为子任务并分发到对应 Agent
- **可视化规划** — Plan Agent 生成 HTML 可视化方案，浏览器中审阅确认后再实施
- **自动代码审查** — 实现完成后自动插入 Review Agent，提交前拦截问题
- **混合编排模式** — 简单任务直接 Agent tool 分发，复杂项目 Team + TaskList 协调
- **引擎架构知识库** — ECS、渲染管线、内存管理、性能优化等专业知识内置

## Agent 角色

| Agent | 模型 | 职责 | 颜色 |
|-------|------|------|------|
| `plan-agent` | Opus | 实现规划、分阶段路线图、HTML 可视化方案生成 | Cyan |
| `architect` | Opus | 系统架构设计、ECS 设计、模块拆分、性能优化方案 | Magenta |
| `core-developer` | Sonnet | C++/Lua/HLSL 代码实现、内存管理、并发编程 | Blue |
| `test-engineer` | Sonnet | 测试框架搭建、单元/集成/性能测试编写 | Green |
| `build-engineer` | Haiku | CMake 配置、CI/CD、跨平台编译、依赖管理 | Yellow |
| `review-agent` | Sonnet | 代码审查、正确性/性能/架构合规检查 | Red |

## Skills

| Skill | 触发场景 |
|-------|----------|
| `game-engine-dev` | 主编排入口，分析任务并分发到对应 Agent |
| `engine-architecture` | 设计引擎系统时自动激活（ECS、渲染管线、资源管理等） |
| `engine-performance` | 性能优化、内存分析、SIMD、多线程等场景自动激活 |

## 支持的技术栈

- **语言**: C++17、Lua/LuaJIT、HLSL/GLSL
- **构建**: CMake
- **依赖管理**: vcpkg、Conan、FetchContent

## 安装

### 全局安装（所有项目生效）

编辑 `~/.claude/settings.json`：

```json
{
  "extraKnownMarketplaces": {
    "local-engine": {
      "source": {
        "source": "directory",
        "path": "C:/Users/heguoling/Desktop/claude-code-flow/game-engine-dev"
      }
    }
  },
  "enabledPlugins": {
    "game-engine-dev@local-engine": true
  }
}
```

### 项目级安装（仅当前项目生效）

在项目根目录创建 `.claude/settings.json`，内容同上。路径可使用相对路径以便团队共享：

```json
{
  "extraKnownMarketplaces": {
    "local-engine": {
      "source": {
        "source": "directory",
        "path": "../claude-code-flow/game-engine-dev"
      }
    }
  },
  "enabledPlugins": {
    "game-engine-dev@local-engine": true
  }
}
```

> 项目级配置可提交到 git，团队成员 clone 后即可使用。建议使用相对路径以兼容不同开发环境。

### 通过命令安装

在 Claude Code 中运行 `/plugin`，选择添加本地目录并输入插件路径。

安装后运行 `/reload-plugins` 使配置生效。

### 验证安装

```bash
# 确认插件加载
/reload-plugins

# 测试触发
"Design an ECS architecture for my engine"
"Write unit tests for the math library"
"Set up CMake with vcpkg for SDL2"
```

## 工作流

```
用户需求 → Plan Agent (Opus, HTML可视化)
         ↓ 用户浏览器审阅确认
      Architect (Opus) 架构设计
         ↓
      Core Developer (Sonnet) 实现
         ↓
      Review Agent (Sonnet) 代码审查 ←── 发现问题则返回修改
         ↓ 审查通过
      Test Engineer (Sonnet) 测试
         ↓
      Build Engineer (Haiku) 构建配置
         ↓
      完成
```

## 使用示例

```
# 完整功能开发 — Plan → 浏览器审阅 → 实现 → Review → 测试
"Build a complete rendering pipeline with shadow mapping"

# 仅规划 — 触发 Plan Agent，生成 HTML 可视化方案
"Plan the audio system architecture with spatial audio and streaming"

# 仅架构设计 — 触发 Architect (Opus)
"Design the resource management system with async loading"

# 仅代码实现 — 触发 Core Developer (Sonnet)
"Implement a spatial hash grid for broad-phase collision"

# 仅审查 — 触发 Review Agent (Sonnet)
"Review the ECS implementation for thread safety issues"

# 仅测试 — 触发 Test Engineer (Sonnet)
"Write performance benchmarks for the ECS with 100k entities"

# 仅构建配置 — 触发 Build Engineer (Haiku)
"Add SDL2 and ImGui as dependencies and configure the editor target"
```

## 插件结构

```
game-engine-dev/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── plan-agent.md         # Opus — 实现规划 + HTML可视化（只读）
│   ├── architect.md          # Opus — 架构设计（只读）
│   ├── core-developer.md     # Sonnet — 代码实现
│   ├── test-engineer.md      # Sonnet — 测试
│   ├── build-engineer.md     # Haiku — 构建
│   └── review-agent.md       # Sonnet — 代码审查（只读）
└── skills/
    ├── game-engine-dev/      # 主编排 Skill
    │   ├── SKILL.md
    │   └── references/
    │       ├── architecture-patterns.md
    │       └── performance-guide.md
    ├── engine-architecture/  # 架构知识 Skill
    │   └── SKILL.md
    └── engine-performance/   # 性能知识 Skill
        └── SKILL.md
```
