# 仓库结构

```
langchain_v1/
├── README.md                     # 公开入口 — 面向最终用户的简明说明
├── CLAUDE.md                     # 本文件 — 维护者专用，不推送（.gitignore）
├── skills/                       # 核心产物 — 1 父技能 + 4 子技能（层级结构）
│   └── langchain-v1-suite/       # 父技能入口（路由决策 + 三层架构）
│       ├── SKILL.md              #   渐进披露入口（~800 tokens）
│       ├── CHANGELOG.md
│       ├── langchain-v1/         #   子技能：Agent Framework + 5 references
│       │   ├── SKILL.md
│       │   ├── CHANGELOG.md
│       │   └── references/
│       │       ├── api-reference.md
│       │       ├── decision-guide.md
│       │       ├── mcp-integration.md
│       │       ├── migration-comparison.md
│       │       └── patterns.md
│       ├── langgraph-v1/         #   子技能：Agent Runtime + 3 references
│       │   ├── SKILL.md
│       │   ├── CHANGELOG.md
│       │   └── references/
│       │       ├── graph-api-reference.md
│       │       ├── checkpointer-store-guide.md
│       │       └── fault-tolerance-guide.md
│       ├── deepagents-v1/        #   子技能：Agent Harness + 3 references
│       │   ├── SKILL.md
│       │   ├── CHANGELOG.md
│       │   └── references/
│       │       ├── backends-guide.md
│       │       ├── subagents-guide.md
│       │       └── skills-guide.md
│       └── langsmith-trace/      #   子技能：Observability + reference
│           ├── SKILL.md
│           ├── CHANGELOG.md
│           └── reference/
│               └── cli-commands.md
├── docs/                         # 文档素材 — skill 的源头（.gitignore 排除）
│   ├── official/                  # 官方文档下载副本（165 文件）
│   │   ├── concepts/              #   跨产品概念 (4)
│   │   ├── deepagents/            #   Deep Agents Harness (41)
│   │   ├── langchain/             #   LangChain Framework (66)
│   │   ├── langgraph/             #   LangGraph Runtime (35)
│   │   ├── contributing/          #   社区贡献指南 (7)
│   │   └── reference/             #   SDK 参考索引 (5)
│   └── community/                 # 社区/实战案例（.gitignore 排除）
│       ├── 赋范/                   #   赋范大模型技术社区
│       │   ├── cases/             #     完整项目示例
│       │   └── patterns/          #     代码模式、最佳实践
│       └── 沧海九粟/               #   沧海九粟《Deep Agents 实战》课程
│           └── ch01-* ~ ch09-*    #     11 章 + 2 准备篇
├── topics/                       # 专题研究报告（基于 docs/ 加工的学习产出）
│   ├── INDEX.md                   #   专题索引
│   └── langchain-skills-deep-dive.md  # Skills 机制深度剖析
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
