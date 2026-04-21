# Game Engine Dev Plugin

Claude Code 工作流插件，通过模型分层 Agent 编排游戏引擎开发流程。

## 特性

- 模型分层 -- Opus(规划/架构), Sonnet(实现/测试/审查), Haiku(构建)
- Plan Gate -- 复杂任务生成 HTML 可视化方案，浏览器审阅确认
- Review Gate -- 实现后自动代码审查，拦截问题再提交
- 混合编排 -- 简单任务直接分发，复杂项目 Team + TaskList 协调
- 引擎知识库 -- ECS、渲染管线、内存管理、性能优化

## Agent

| Agent | 模型 | 职责 |
|-------|------|------|
| `oracle` | Opus | 实现规划, 分阶段路线图, HTML 可视化 |
| `atlas` | Opus | 架构设计, ECS, 模块拆分 |
| `forge` | Sonnet | C++/Lua/HLSL 实现 |
| `prism` | Sonnet | 测试框架, 单元/集成/性能测试 |
| `anvil` | Haiku | CMake, CI/CD, 跨平台编译 |
| `sentinel` | Sonnet | 代码审查, 正确性/性能/架构合规 |

## Skills

| Skill | 触发场景 |
|-------|----------|
| `game-engine-dev` | 主编排, 分析任务并分发 Agent |
| `engine-architecture` | 引擎系统设计 (ECS, 渲染管线, 资源管理) |
| `engine-performance` | 性能优化, 内存, SIMD, 多线程 |

## 技术栈

C++17, Lua/LuaJIT, HLSL/GLSL, CMake, vcpkg/Conan

## 安装

### 全局

`~/.claude/settings.json`，在已有的配置中合并以下内容:

```json
{
  "extraKnownMarketplaces": {
    "game-engine-dev": {
      "source": {
        "source": "directory",
        "path": "C:/Users/heguoling/Desktop/claude-code-flow"
      }
    }
  },
  "enabledPlugins": {
    "game-engine-dev@game-engine-dev": true
  }
}
```

### 项目级

在**你的游戏引擎项目**根目录创建 `.claude/settings.json`（不是本仓库），路径用相对路径以便团队共享:

```json
{
  "extraKnownMarketplaces": {
    "game-engine-dev": {
      "source": {
        "source": "directory",
        "path": "../claude-code-flow"
      }
    }
  },
  "enabledPlugins": {
    "game-engine-dev@game-engine-dev": true
  }
}
```

也可用 `/plugin` 命令交互安装，装完 `/reload-plugins` 生效。

> 注意: 不要在插件仓库内部创建 `.claude/settings.json`，会导致循环引用。配置应放在使用插件的项目中。

## 工作流

所有任务经过 Plan -> Implement -> Review 流水线，复杂任务增加 Design 阶段和 HTML 可视化。

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
  [等待审查通过]
      |
      v
报告 & 完成
```

## 使用示例

```
# 完整功能开发
"Build a complete rendering pipeline with shadow mapping"

# 仅规划 (HTML 可视化)
"Plan the audio system architecture with spatial audio and streaming"

# 仅架构设计
"Design the resource management system with async loading"

# 仅代码实现
"Implement a spatial hash grid for broad-phase collision"

# 仅审查
"Review the ECS implementation for thread safety issues"

# 仅测试
"Write performance benchmarks for the ECS with 100k entities"

# 仅构建配置
"Add SDL2 and ImGui as dependencies and configure the editor target"
```

## 结构

```
claude-code-flow/
├── .claude-plugin/
│   └── plugin.json
├── agents/
│   ├── oracle.md             # Opus -- 规划 + HTML (只读)
│   ├── atlas.md              # Opus -- 架构设计 (只读)
│   ├── forge.md              # Sonnet -- 代码实现
│   ├── prism.md              # Sonnet -- 测试
│   ├── anvil.md              # Haiku -- 构建
│   └── sentinel.md           # Sonnet -- 审查 (只读)
└── skills/
    ├── game-engine-dev/      # 主编排
    │   ├── SKILL.md
    │   └── references/
    │       ├── architecture-patterns.md
    │       └── performance-guide.md
    ├── engine-architecture/  # 架构知识
    │   └── SKILL.md
    └── engine-performance/   # 性能知识
        └── SKILL.md
```
