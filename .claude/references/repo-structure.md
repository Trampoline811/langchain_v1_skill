# 仓库结构

```
langchain_v1/
├── README.md                     # 公开入口 — 面向最终用户的简明说明
├── CLAUDE.md                     # 本文件 — 维护者专用，不推送（.gitignore）
├── skills/                       # 核心产物 — 5 个 Claude Code Skill
│   ├── agent-sdk-router/         # 入口路由 skill
│   │   ├── SKILL.md
│   │   └── CHANGELOG.md
│   ├── langchain-v1/             # Framework skill + 5 references
│   │   ├── SKILL.md
│   │   ├── CHANGELOG.md
│   │   └── references/
│   │       ├── api-reference.md
│   │       ├── decision-guide.md
│   │       ├── mcp-integration.md
│   │       ├── migration-comparison.md
│   │       └── patterns.md
│   ├── langgraph-v1/             # Runtime skill + 3 references
│   │   ├── SKILL.md
│   │   ├── CHANGELOG.md
│   │   └── references/
│   │       ├── graph-api-reference.md
│   │       ├── checkpointer-store-guide.md
│   │       └── fault-tolerance-guide.md
│   ├── deepagents-v1/            # Harness skill + 3 references
│   │   ├── SKILL.md
│   │   ├── CHANGELOG.md
│   │   └── references/
│   │       ├── backends-guide.md
│   │       ├── subagents-guide.md
│   │       └── skills-guide.md
│   └── langsmith-trace/          # Observability skill（跨层观测排障）
│       ├── SKILL.md
│       ├── CHANGELOG.md
│       └── reference/
│           └── cli-commands.md
├── docs/                         # 文档素材 — skill 的源头（.gitignore 排除）
│   ├── official/                  # 官方文档下载副本（270 文件）
│   │   ├── langchain/             #   LangChain Framework
│   │   ├── langgraph/             #   LangGraph Runtime
│   │   ├── deepagents/            #   Deep Agents Harness
│   │   ├── concepts/              #   跨产品概念
│   │   └── ...                    #   contributing, reference, changelog 等
│   └── community/                 # 社区/实战案例
│       ├── cases/                 #   完整项目示例
│       └── patterns/              #   代码模式、最佳实践
├── tools/                        # 维护工具
│   ├── update_skill.py           # 自动化同步脚本
│   └── urls.md                   # 官方文档源URL清单（196 条）
├── tests/                        # 盲测验证（3 个脚本，17/17 通过）
│   ├── resume_agent.py           # langchain-v1 盲测
│   ├── langgraph_agent.py        # langgraph-v1 盲测
│   ├── deep_agent.py             # deepagents-v1 盲测
│   ├── blind_test.md             # 盲测方法
│   ├── blind_test_analysis.md    # 盲测分析报告
│   └── maintenance_guide.md      # 维护流程指南
└── results/                      # 盲测结果归档
```
