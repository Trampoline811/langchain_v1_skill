# LangChain v1.0 中间件深度剖析

> 从钩子机制到实战模式：Skills/Handoffs 背后的共同引擎
> 基于 LangChain 官方 middleware-overview + built-in + custom 三文档，2026-07-03 整理

---

## 一、一句话定位

**中间件 = Agent 生命周期的钩子系统**。在 Agent 循环的每个关键节点（启动前、调模型前、调模型后、调工具前后），中间件可以拦截、修改、跳转或注入额外行为。

| 对比维度 | Middleware (v1.0) | Memory (v0.x) | Callbacks (v0.x) |
|----------|-------------------|---------------|-------------------|
| **定位** | Agent 生命周期的通用钩子 | 对话历史管理 | 事件监听 |
| **粒度** | 每次模型调用 / 每次工具调用 / 每次 Agent 启动 | 每轮对话 | 每个事件 |
| **状态读写** | 原生支持 `state_schema` | 独立于 Agent 状态 | 只读，不能改 Agent 行为 |
| **可组合** | 栈式堆叠，before 顺序 + after 逆序 | 单 Memory 实例 | 多 Callback 并行 |
| **典型场景** | 动态提示词、状态驱动路由、工具过滤、HITL | 存储对话历史 | 日志、监控 |

---

## 二、核心机制

### 2.1 Agent 循环中的钩子点

```
Agent 启动
  │
  ├── before_agent       ← 每次 invoke 跑一次（session 级初始化）
  │
  ▼
┌─────────── Agent Loop ───────────┐
│                                   │
│  ├── before_model       ← 每轮模型调用前
│  │                          改 system prompt / 过滤工具 / jump_to
│  │
│  ├── wrap_model_call    ← 包裹模型调用
│  │    │                     可改 request → 调 handler → 改 response
│  │    │                     "洋葱皮"包在最外层
│  │    ▼
│  │  模型调用
│  │    │
│  │    ▼
│  │  wrap_model_call 返回
│  │
│  ├── after_model        ← 每轮模型调用后
│  │                          读模型输出 / 决定 jump_to
│  │
│  ├── wrap_tool_call     ← 包裹每个工具调用
│  │                          改工具参数 / 改返回值 / 中断
│  │
│  ▼
│  (循环回到 before_model 或 END)
│                                   │
└───────────────────────────────────┘
  │
  ├── after_agent        ← Agent 结束前跑一次
  ▼
返回用户
```

### 2.2 两类钩子

| 类型 | 钩子 | 触发频率 | 典型用途 |
|------|------|:--:|------|
| **Node-style** | `before_agent` | 1次/调用 | 初始化 state、加载配置 |
| | `before_model` | N次/调用 | 日志、限流、jump_to |
| | `after_model` | N次/调用 | 检查输出、触发 HITL |
| | `after_agent` | 1次/调用 | 清理、持久化 |
| **Wrap-style** | `wrap_model_call` | N次/调用 | **动态提示词注入**、工具过滤、重试 |
| | `wrap_tool_call` | N次/调用 | 工具参数校验、结果后处理 |

**关键区别**：
- Node-style：返回 `dict | None` 更新 state，可 `jump_to`
- Wrap-style：接收 `request` + `handler`，调用 `handler(modified_request)` 然后返回 `response`，**嵌套执行**

### 2.3 执行顺序（多中间件栈）

```python
agent = create_agent(
    model="gpt-5.4",
    middleware=[A, B, C],  # ← 顺序很重要
)
```

```
before_model:  A → B → C          (正序)
wrap_model_call: A.wrap() → B.wrap() → C.wrap() → 模型  (嵌套，A 在最外层)
after_model:   C → B → A          (逆序)
```

> **记忆**：`before` 正序执行，`after` 逆序执行，`wrap` 洋葱皮嵌套。

### 2.4 `AgentMiddleware` 的三个类属性

```python
class MyMiddleware(AgentMiddleware):
    state_schema = CustomState     # ① 扩展 Agent state，加自定义字段
    tools = [my_tool]              # ② 中间件自带的工具（逻辑一体打包）
    transformers = (MyTransformer,) # ③ 流式事件转换器（高级）
```

### 2.5 `wrap_model_call` 的 `request.override()` 可修改项

| 可修改字段 | 用途 |
|-----------|------|
| `system_prompt` / `system_message` | **动态提示词注入** ← Skills 核心机制 |
| `tools` | 动态工具过滤/选择 |
| `model` | 动态模型切换 |
| `response_format` | 动态输出格式 |

---

## 三、内置中间件全景

> 以下按功能分类列出 LangChain v1.0 14 个内置中间件。

### 3.1 上下文管理

| 中间件 | 作用 | 典型参数 |
|--------|------|---------|
| **SummarizationMiddleware** | 历史压缩 | `model`, `trigger=(tokens, 4000)`, `keep=(messages, 20)` |
| **ContextEditingMiddleware** | 上下文编辑 | `edits=[ClearToolUsesEdit(trigger=2000, keep=3)]` |
| **FilesystemMiddleware** | 文件读写能力 | `backend=StateBackend()` |
| **FilesystemFileSearchMiddleware** | Glob + Grep 搜索 | `root_path="/workspace"` |

### 3.2 可靠性与容错

| 中间件 | 作用 | 典型参数 |
|--------|------|---------|
| **ModelFallbackMiddleware** | 模型故障切换 | 备选模型列表 |
| **ToolRetryMiddleware** | 工具调用重试 | `max_retries=3`, `backoff_factor=2.0` |
| **ModelRetryMiddleware** | 模型调用重试 | `max_retries=3` |

### 3.3 安全与护栏

| 中间件 | 作用 | 典型参数 |
|--------|------|---------|
| **HumanInTheLoopMiddleware** | 人工审批中断 | `interrupt_on={"send_email": True}` |
| **PIIMiddleware** | 敏感信息检测 | 内置 + 自定义 PII 类型 |
| **ModelCallLimitMiddleware** | 模型调用上限 | `max_calls=100`, `exit_behavior="error"` |
| **ToolCallLimitMiddleware** | 工具调用上限 | `max_tool_calls=50` |

### 3.4 工具增强

| 中间件 | 作用 | 典型参数 |
|--------|------|---------|
| **LLMToolSelectorMiddleware** | LLM 自动选相关工具 | 从 N 个工具中挑 K 个 |
| **LLMToolEmulatorMiddleware** | 模拟工具调用 | 为特定工具做 LLM 仿真 |
| **ShellToolMiddleware** | Shell 执行能力 | `workspace_root`, `execution_policy` |
| **TodoListMiddleware** | 内置 TODO 管理 | `write_todos` 工具 |

### 3.5 DeepAgents 专属

| 中间件 | 作用 |
|--------|------|
| **SkillsMiddleware** | Skills 渐进披露 |
| **MemoryMiddleware** | 长期记忆加载 |
| **SubAgentMiddleware** | 子 Agent 调度 |
| **CodeInterpreterMiddleware** | QuickJS/Python 解释器 |

### 3.6 DeepAgents 三层中间件堆栈

> `create_deep_agent()` 的本质 = `create_agent()` + 三层自动装配的中间件堆栈。

**常驻层（5 个，始终启用，不可排除）：**

| 中间件 | 注入能力 |
|--------|---------|
| `TodoListMiddleware` | `write_todos` 工具 + 规划提示词 |
| `FilesystemMiddleware` | 6 个文件工具 + 权限控制 |
| `SummarizationMiddleware` | 对话历史自动压缩 |
| `PatchToolCallsMiddleware` | 工具调用内部修补（框架内部） |
| `AnthropicPromptCachingMiddleware` | 提示词缓存（非 Anthropic 模型自动跳过） |

**条件层（5 个，按参数自动激活）：**

| 触发条件 | 中间件 | 注入能力 |
|---------|--------|---------|
| 有子 Agent | `SubAgentMiddleware` | `task` 工具 + Context Quarantine |
| 传 `skills=` | `SkillsMiddleware` | 从 `skills/` 加载领域知识 |
| 有异步子 Agent | `AsyncSubAgentMiddleware` | 5 把遥控器工具 |
| 传 `memory=` | `MemoryMiddleware` | 从 `AGENTS.md` 加载持久记忆 |
| 传 `interrupt_on=` | `HumanInTheLoopMiddleware` | 拦截指定工具等待审批 |

**用户自定义层（`middleware=[]` 按需叠加）：** §3.1-3.4 中全部通用中间件均可用于此层。

**三层执行顺序：** `before_model`: 常驻→条件→自定义（正序）；`wrap_model_call`: 自定义.wrap() 包 条件.wrap() 包 常驻.wrap()（嵌套洋葱）；`after_model`: 自定义→条件→常驻（逆序）。

> **不可排除规则**：`TodoListMiddleware` + `FilesystemMiddleware` 是 DeepAgents 硬依赖。不需要它们 → 直接用 `create_agent()`。

---

## 四、自定义中间件（MDA 三层）

### 4.1 核心思想

自定义中间件就是**写一个拦截器**：告诉 Agent "在 XX 时机，帮我做 XX 事"。最小中间件只需要一个钩子函数。

### 4.2 理论说明（静动分离）

```
════════════ 静态准备（程序启动） ════════════

两种写法选一种：

写法A — 装饰器（快速，单钩子）：
  @before_model
  def my_hook(state, runtime) -> dict | None:
      ...拦截逻辑...
      return None  # 或 {"jump_to": "end"}

写法B — 类（强大，多钩子/配置）：
  class MyMiddleware(AgentMiddleware):
      state_schema = CustomState    # 可选：扩展 state
      tools = [my_tool]              # 可选：带工具

      def __init__(self, max_calls=50):
          self.max_calls = max_calls

      def before_model(self, state, runtime) -> dict | None:
          ...拦截逻辑...

      def wrap_model_call(self, request, handler):
          return handler(request.override(system_prompt=...))

════════════ 动态执行（每次 Agent invoke） ═══════════

Agent 启动
  │
  ├── before_agent 触发（1次）
  │
  ├── [循环开始]
  │   before_model 触发                   ← 改 prompt / 过滤工具 / jump_to
  │   wrap_model_call 触发                ← 嵌套包裹模型调用
  │   模型响应
  │   after_model 触发                    ← 读输出 / 更新 state / jump_to
  │   [如有工具调用] wrap_tool_call 触发
  │   [回到循环]
  │
  ├── after_agent 触发（1次）
```

**本质**：`before_model` = 在模型**看到**之前改上下文；`wrap_model_call` = 在模型**调用**之外包一层洋葱皮。

### 4.3 关键代码骨架

**最小可跑示例 — 消息计数限制**：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain.messages import AIMessage

class MessageLimitMiddleware(AgentMiddleware):
    """超过 50 条消息后强制终止。"""

    def __init__(self, max_messages: int = 50):
        super().__init__()
        self.max_messages = max_messages

    def before_model(self, state: AgentState, runtime) -> dict | None:
        if len(state["messages"]) >= self.max_messages:
            return {
                "messages": [AIMessage("对话已达上限。")],
                "jump_to": "end",           # ← 跳过模型调用，直接结束
            }
        return None  # ← 不拦截，正常继续

agent = create_agent(
    model="gpt-5.4",
    middleware=[MessageLimitMiddleware(max_messages=50)],
)
```

**动态提示词注入 — 最常用模式**：

```python
class PromptInjectMiddleware(AgentMiddleware):
    """每次模型调用前，拼一段动态内容到 system prompt。"""

    def wrap_model_call(self, request, handler):
        extra = f"\n当前时间: {datetime.now()}\n用户等级: VIP"
        new_system = request.system_message.content_blocks + [
            {"type": "text", "text": extra}
        ]
        return handler(request.override(
            system_message=SystemMessage(content=new_system)
        ))
```

> **常见疑问：两种写法怎么选？**
>
> | 场景 | 用 |
> |------|-----|
> | 一个钩子，无配置 | 装饰器 `@before_model` |
> | 多个钩子放一起 | 类 `class XxxMiddleware(AgentMiddleware)` |
> | 需要 `__init__` 传配置 | 类 |
> | 需要带配套工具 (`tools = [...]`) | 类 |
> | 需要扩展 state (`state_schema`) | 类 |

---

## 五、三大实战模式

### 5.1 动态提示词注入 — Skills 的核心

**对应机制**：`wrap_model_call` + `request.override(system_message=...)`

**核心思想**：每轮模型调用前，将运行时信息注入 system prompt。Agent 看不到注入逻辑——它只看到"这个 prompt 本来就有这些内容"。

**与 Skills 的关系**：Skills 模式的 `SkillMiddleware` 就是用这个机制——把技能摘要拼到 system prompt 末尾，让 Agent 知道有哪些技能可用。

> 完整 Skills 机制见 [`langchain-skills-deep-dive.md` §五](langchain-skills-deep-dive.md#五langchain-multi-agent-skillsdiy-模式)。

**通用代码骨架**：

```python
class DynamicContextMiddleware(AgentMiddleware):
    """按用户身份/时间/业务状态动态注入上下文。"""

    def __init__(self, get_context: Callable):
        self.get_context = get_context

    def wrap_model_call(self, request, handler):
        context = self.get_context(request.state, request.runtime)
        return handler(request.override(
            system_message=append_to_system_message(
                request.system_message, context
            )
        ))
```

### 5.2 状态驱动配置切换 — Handoffs 的核心

**对应机制**：`wrap_model_call` + State 读取 + 动态切换 prompt + tools

**核心思想**：中间件读 `state.current_step`，查配置表，切换 system_prompt 和 tools。工具通过 `Command(update={"current_step": "next"})` 驱动步骤流转。单 Agent 模拟多角色。

> 完整 Handoffs 机制见 [`multi-agent-routing-comparison.md` §4.3](multi-agent-routing-comparison.md#43-handoffs--状态驱动工作流流转)。

**通用代码骨架**：

```python
STEP_CONFIGS = {
    "triage": {"prompt": "...", "tools": [tool_a]},
    "specialist": {"prompt": "...", "tools": [tool_b, tool_c]},
}

class StepConfigMiddleware(AgentMiddleware):
    state_schema = SupportState  # current_step: str

    def wrap_model_call(self, request, handler):
        step = request.state.get("current_step", "triage")
        config = STEP_CONFIGS[step]
        return handler(request.override(
            system_prompt=config["prompt"],
            tools=config["tools"],
        ))
```

### 5.3 工具动态选择 — 上下文感知路由

**对应机制**：`wrap_model_call` + `request.override(tools=...)`

**核心思想**：不是所有工具每轮都该出现。根据用户权限、对话阶段、认证状态动态过滤工具列表。

```python
class PermissionToolFilter(AgentMiddleware):
    """未认证用户只能调 public_ 前缀的工具。"""

    def wrap_model_call(self, request, handler):
        is_auth = request.state.get("authenticated", False)
        if not is_auth:
            tools = [t for t in request.tools if t.name.startswith("public_")]
            request = request.override(tools=tools)
        return handler(request)
```

---

## 六、与 v0.x 的对比

### 6.1 Memory → Middleware

| v0.x Memory | v1.0 Middleware 替代 |
|-------------|---------------------|
| `ConversationBufferMemory` | 不需要——Agent 自动保留消息历史 |
| `ConversationSummaryMemory` | `SummarizationMiddleware` |
| `ConversationTokenBufferMemory` | `SummarizationMiddleware(trigger=("tokens", N))` |
| 自定义 Memory 逻辑 | 自定义 Middleware `before_model` / `wrap_model_call` |

### 6.2 Callbacks → Middleware

| v0.x Callback | v1.0 Middleware Hook |
|---------------|---------------------|
| `on_llm_start` | `before_model` |
| `on_llm_end` | `after_model` |
| `on_tool_start` | `wrap_tool_call`（入参前） |
| `on_tool_end` | `wrap_tool_call`（返回值后） |
| `on_agent_action` | `before_model` + state 读取 |

**核心差异**：Callbacks 只能"旁观"，Middleware 可以**改 prompt**、**换工具**、**跳过模型调用**（`jump_to: "end"`）。

---

## 七、常见坑点与避坑指南

| # | 坑点 | 严重度 | 避坑建议 |
|---|------|:---:|------|
| ① | **触发时机误解**：以为 `wrap_model_call` 只在"最后一轮"触发 | 🔴 高 | **每次**模型调用前都触发。Agent 循环中 5 轮对话 = 5 次 `wrap_model_call` |
| ② | **`tools` 注册位置混淆**：类变量 vs `create_agent(tools=...)` | 🟡 中 | 效果相同。`tools` 和 middleware 逻辑一体时写类变量，通用工具直接传 `create_agent` |
| ③ | **中间件顺序影响行为** | 🟡 中 | `before` 正序、`after` 逆序、`wrap` 洋葱嵌套。排前面的 middleware 包在最外层 |
| ④ | **忘记 `return handler(request)`** | 🔴 高 | `wrap_model_call` 必须调用 `handler()` 并返回——否则模型永远不会被调用 |
| ⑤ | **`jump_to` 需提前声明** | 🟡 中 | 类写法用 `@hook_config(can_jump_to=["end", "tools"])`，装饰器用参数 `can_jump_to=["end"]` |
| ⑥ | **`state_schema` 的字段用 `NotRequired`** | 🟢 低 | 否则每次 `invoke` 都必须传这个字段，类型检查不通过 |

---

## 参考资料

> 专题报告引用规范见 [`topics/INDEX.md`](INDEX.md#扩展规则)。

### 本地源文件

| 本地路径 | 官方 URL |
|----------|----------|
| `docs/official/langchain/langchain-middleware-overview.md` | [Middleware overview](https://docs.langchain.com/oss/python/langchain/middleware) |
| `docs/official/langchain/langchain-middleware-built-in.md` | [Built-in middleware](https://docs.langchain.com/oss/python/langchain/middleware/built-in) |
| `docs/official/langchain/langchain-middleware-custom.md` | [Custom middleware](https://docs.langchain.com/oss/python/langchain/middleware/custom) |
| `docs/official/langchain/langchain-agents.md` | [LangChain Agents](https://docs.langchain.com/oss/python/langchain/agents) |

### 交叉引用

| 本地专题 | 关联内容 |
|----------|---------|
| `topics/langchain-skills-deep-dive.md` §五 | Skills DIY 模式 = 中间件动态提示词注入实战 |
| `topics/multi-agent-routing-comparison.md` §4.3 | Handoffs 模式 = 中间件状态驱动配置切换实战 |
| `topics/langchain-hitl-deep-dive.md` §四/§五 | HumanInTheLoopMiddleware 详解 + DeepAgents 三层堆栈条件激活 |

> **整理日期**: 2026-07-09
