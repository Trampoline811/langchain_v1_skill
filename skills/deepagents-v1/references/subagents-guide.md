# Deep Agents 子 Agent 完整指南

> **来源**: 官方 `deepagents-subagents.md` + `deepagents-async-subagents.md`
> **定位**: 同步/异步子 Agent 的完整字段、模式、排障。快速示例见 `SKILL.md` §2.3。
> **文中标记**: 无标记 = 官方文档提炼

---

## 1. 子 Agent 10 字段完整参考

| 字段 | 必填 | 继承主Agent？ | 类型 | 说明 |
|------|:--:|:--:|------|------|
| `name` | ✅ | — | `str` | 唯一标识，主 Agent 路由依据 |
| `description` | ✅ | — | `str` | 能力描述 — **越具体路由越准** |
| `system_prompt` | ✅ | ❌ | `str` | 子 Agent 专属指令 |
| `tools` | 可选 | ✅ 默认继承 | `list` | 指定后**完全替换**（不合并） |
| `model` | 可选 | ✅ 默认继承 | `str \| BaseChatModel` | 可指定不同模型 |
| `middleware` | 可选 | ❌ | `list` | 子 Agent 自己的中间件 |
| `interrupt_on` | 可选 | ✅ 默认继承 | `dict` | HITL 配置 |
| `skills` | 可选 | ❌ | `list[str]` | 专属技能目录 |
| `response_format` | 可选 | ❌ | `type[BaseModel]` | Pydantic 结构化输出 |
| `permissions` | 可选 | ✅ 默认继承 | `dict` | 指定后**完全替换** |

> **关键**: `system_prompt` 和 `tools` 的继承行为不同 — tools 默认继承主 Agent，system_prompt 需要独立写。

---

## 2. 三种定义形态

### Dict 定义（最常用）

```python
from deepagents import create_deep_agent

subagents = [
    {
        "name": "researcher",
        "description": "需要多次搜索、交叉验证和综合分析时使用。输出控制在 500 字以内。",
        "system_prompt": "你是研究员。搜索 → 验证 → 综合 → 精炼输出。",
        "tools": [search, fetch_url],
        "model": "deepseek:deepseek-chat",  # 比主 Agent 用更便宜的模型
    },
]
agent = create_deep_agent(model=main_model, subagents=subagents)
```

### CompiledSubAgent（复用 LangGraph 图）

```python
from deepagents.middleware.subagents import CompiledSubAgent

researcher_graph = create_agent(
    "claude-sonnet-4-6", tools=[search],
    system_prompt="你是研究员..."
)

agent = create_deep_agent(
    model=main_model,
    subagents=[
        CompiledSubAgent(
            name="researcher",
            description="深度调研",
            runnable=researcher_graph,
        ),
    ],
)
```

### 转子 Agent（快速原型）

```python
researcher = create_deep_agent(
    model="deepseek:deepseek-chat",
    tools=[search],
    name="researcher",
    system_prompt="你是研究员...",
)

agent = create_deep_agent(
    model=main_model,
    subagents=[researcher.as_subagent()],
)
```

---

## 3. General-purpose 子 Agent

```python
# 默认启用，无配置即可用
agent = create_deep_agent(model=model)

# 禁用它
from deepagents.profiles import GeneralPurposeSubagentProfile, HarnessProfile

agent = create_deep_agent(
    model=model, subagents=[],
    profile=HarnessProfile(
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False)
    ),
)

# 覆盖它（给更强的模型）
agent = create_deep_agent(model=model, subagents=[
    {
        "name": "general-purpose",
        "description": "通用助手，处理各种日常任务",
        "system_prompt": "你是通用助手...",
        "model": ChatOpenAI(model="Pro/zai-org/GLM-5", base_url="..."),
    },
])
```

---

## 4. 结构化输出（子 Agent → 主 Agent）

```python
from pydantic import BaseModel, Field

class ResearchFindings(BaseModel):
    summary: str = Field(description="调研摘要，不超过 200 字")
    confidence: float = Field(description="结论置信度 0-1")
    sources: list[str] = Field(description="引用来源列表")

subagents = [{
    "name": "researcher",
    "description": "深度调研，返回结构化结果",
    "system_prompt": "调研后以 JSON 格式输出 summary + confidence + sources",
    "tools": [search],
    "response_format": ResearchFindings,  # ← ToolMessage 收到结构化 JSON
}]
```

---

## 5. 异步子 Agent（`deepagents>=0.5.0`）

### 同步 vs 异步

| 维度 | 同步（`task` 工具） | 异步（`start_async_task`） |
|------|------|------|
| 执行模型 | 阻塞等完成 | 立即返回 task ID |
| 并发性 | 可并行，主Agent 被整批阻塞 | 完全并行，主Agent 自由 |
| 中途追加 | ❌ | ✅ `update_async_task` |
| 取消 | ❌ | ✅ `cancel_async_task` |
| 状态性 | 每次独立 | 子Agent 有自己 thread |
| 典型时长 | <5 秒 | 分钟级以上 |

### 声明

```python
from deepagents import AsyncSubAgent, create_deep_agent

async_subagents = [
    AsyncSubAgent(
        name="researcher",                      # 唯一标识
        description="深度调研，多次搜索+综合分析，可能跑数分钟",
        graph_id="researcher",                  # Agent Protocol 上的 graph ID
        # url="https://...langsmith.dev",       # 可选：远程 HTTP
    ),
]
agent = create_deep_agent(model=model, subagents=async_subagents)
```

### 5 把遥控器

| 工具 | 作用 | 返回 |
|------|------|------|
| `start_async_task` | 启动后台任务 | task ID（立即返回） |
| `check_async_task` | 查询状态与结果 | status + result |
| `update_async_task` | 追加新指令 | 确认 |
| `cancel_async_task` | 终止运行中任务 | 取消确认 |
| `list_async_tasks` | 列出所有任务 | 任务总览 |

---

## 6. 最佳实践 5 条

1. **描述要具体** — ✅ `"需要多次搜索、交叉验证和综合分析时使用"` vs ❌ `"做研究"`
2. **提示词要详细** — 必须含输出格式 + 字数限制，否则上下文隔离失效
3. **工具集要精简** — 最小权限原则，只给需要的工具
4. **模型分级** — 轻量任务用免费/便宜模型，深度分析用旗舰模型
5. **输出要精练** — `system_prompt` 中强制 `"返回结果控制在 500 字以内"`

## 7. 排障 3 问

| 症状 | 可能原因 | 修复 |
|------|---------|------|
| 子 Agent 没被调用 | `description` 太模糊 | 写清楚使用场景和触发条件 |
| 上下文依然膨胀 | 子 Agent 返回了原始数据 | `system_prompt` 加字数限制 |
| 调错子 Agent | 多个 `description` 过于相似 | 明确区分使用场景 + 示例 |

---

> **返回**: [`SKILL.md`](../SKILL.md) §2.3 子 Agent | §6 异步子 Agent
