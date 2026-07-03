# Deep Agents Skills 完整指南

> **来源**: 官方 `deepagents-skills.md` (1012行) + [Agent Skills 规范](https://agentskills.io/specification)
> **定位**: Skills 的完整语法、权限、运行时加载、调试。快速示例见 `SKILL.md` §2.5。

---

## 1. Skill 文件结构

```
skills/
├── langgraph-docs/
│   └── SKILL.md                # 必需 — YAML frontmatter + Markdown 指令
├── arxiv-search/
│   ├── SKILL.md
│   ├── scripts/
│   │   └── search.py           # Python 可执行脚本
│   └── references/
│       └── api-guide.md        # 参考文档
└── order-helpers/
    ├── SKILL.md
    └── assets/
        └── template.json       # 模板等静态资源
```

### SKILL.md 模板

```markdown
---
name: langgraph-docs
description: Use this skill for requests related to LangGraph.
---

# langgraph-docs

## Overview
This skill explains how to access LangGraph documentation...

## Instructions
### 1. Fetch the documentation index
Use `fetch_url` to read: https://docs.langchain.com/llms.txt

### 2. Select relevant documentation
Based on the question, identify 2-4 most relevant URLs...

### 3. Fetch and synthesize
Read the selected URLs and synthesize an answer...
```

### Frontmatter 字段

| 字段 | 必填 | 说明 |
|------|:--:|------|
| `name` | ✅ | 唯一标识名（kebab-case） |
| `description` | ✅ | **触发依据** — Agent 靠这个决定是否激活 skill |
| `module` | 可选 | 指向可执行脚本（`scripts/xxx.py`），声明为 interpreter skill |

---

## 2. 渐进披露机制

```
阶段 1: Agent 读所有 SKILL.md 的 frontmatter（name + description）
阶段 2: 用户输入匹配到 skill → Agent 读完整 SKILL.md 指令
阶段 3: 指令中引用的 scripts/ references/ assets/ → Agent 按需加载
```

> **设计原则**: 不要让 frontmatter 太长。Agent 每次启动都读所有 frontmatter，太长浪费 token。

---

## 3. Interpreter Skills（可执行代码）

```python
# skills/arxiv-search/SKILL.md frontmatter:
# ---
# name: arxiv-search
# description: Search arxiv for research papers
# module: scripts/search.py     ← 关键：声明为 interpreter skill
# ---

# skills/arxiv-search/scripts/search.py
def search_arxiv(query: str, max_results: int = 10) -> dict:
    """Search the arxiv API and return structured results."""
    import requests
    resp = requests.get(
        "https://export.arxiv.org/api/query",
        params={"search_query": query, "max_results": max_results},
    )
    return {"results": resp.text}
```

> Interpreter skill 的 `module` 字段让 Agent 可以将 skill 加载为可调用 Python 模块，通过代码解释器执行。

### Sandbox 执行

```python
from deepagents.middleware import SkillsMiddleware

SkillsMiddleware(
    backend=StateBackend(),
    sources=["./skills/"],
    sandbox=True,  # 技能代码在隔离沙箱中执行
)
```

---

## 4. 运行时动态加载

### 固定列表

```python
agent = create_deep_agent(model=model, skills=["./skills/basic/"])
```

### 动态回调（按环境/用户切换）

```python
def get_skills(runtime) -> list[str]:
    """运行时决定加载哪些技能"""
    if runtime.context.get("tier") == "pro":
        return ["./skills/basic/", "./skills/pro/"]
    return ["./skills/basic/"]

agent = create_deep_agent(model=model, skills=get_skills)
```

### 命名空间技能（多用户隔离）

```python
agent = create_deep_agent(model=model, skills=[
    "./skills/shared/",                              # 所有人可见
    {"namespace": "user-123", "source": "./skills/personal/"},  # 用户专属
])
```

---

## 5. 技能权限（Skill Permissions）

```python
from deepagents.middleware import SkillsMiddleware

SkillsMiddleware(
    backend=StateBackend(),
    sources=["./skills/"],
    permissions={
        # 所有用户共享
        "langgraph-docs": {"type": "shared", "users": "*"},

        # 限定用户
        "admin-tools": {"type": "limited", "users": ["admin", "operator"]},

        # 只读 — Agent 不能写入修改
        "compliance-rules": {"type": "read_only"},

        # Agent 可编辑的个人技能
        "my-notes": {"type": "editable", "scope": "user"},
    },
)
```

| 权限类型 | Agent 可读 | Agent 可写 | 适用 |
|---------|:--:|:--:|------|
| `shared` | ✅ | ❌ | 公共知识 |
| `limited` | ✅ (限定用户) | ❌ | 敏感技能 |
| `read_only` | ✅ | ❌ | 合规规则 |
| `editable` | ✅ | ✅ | 个人笔记/记忆 |

---

## 6. 子 Agent 专属技能

```python
subagents = [{
    "name": "researcher",
    "description": "深度调研。使用研究专用工具和论文检索技能。",
    "system_prompt": "你是研究员...",
    "skills": ["./skills/research/"],  # 只给 researcher 的技能
    # 主 Agent 的 skills 不会传给 researcher
}]
agent = create_deep_agent(model=model, subagents=subagents)
```

---

## 7. Skills vs Tools vs Memory — 区别

| | Skills | Tools | Memory |
|------|------|------|------|
| **触发** | LLM 读 description 后主动激活 | LLM 根据 function schema 调用 | 按需读写 |
| **内容** | Markdown 指令 + 可选脚本 | Python 函数 | JSON 数据 |
| **加载** | 按需（渐进披露） | 每次 model call 都注入 schema | 调用时读写 |
| **持久化** | 文件系统 | 代码 | Store |
| **适合** | 领域知识、工作流指南 | 外部 API 调用、计算 | 用户偏好、跨会话状态 |

---

## 8. 排障

| 症状 | 可能原因 | 修复 |
|------|---------|------|
| Skill 不激活 | `description` 太模糊或不匹配用户输入 | 重写 description：具体说明触发场景 |
| Skills 启动时缺失 | `sources` 路径错误或权限不足 | 检查路径 + 确认目录存在 |
| 引用文件找不到 | `SKILL.md` 中引用路径错误 | 相对路径相对于 skill 目录 |
| Script 执行失败 | Python 环境缺依赖或语法错误 | 在 script 中做好 try/except |
| 子Agent 无法访问 skill | 未在子Agent 的 `skills=` 中声明 | 子Agent skills 不继承主Agent |

---

> **返回**: [`SKILL.md`](../SKILL.md) §2.5 技能 | §2.6 中间件装配架构
