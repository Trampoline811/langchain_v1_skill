---
name: deepagents-v1
description: Deep Agents 开箱即用 agent harness 代码生成规范。内置文件系统、子agent、规划、上下文管理、代码执行。当用户需要复杂多步任务、代码生成/执行、深度研究、内容构建等完整 agent 堆栈时使用。触发词：deepagents、create_deep_agent、sandbox、代码执行、filesystem、文件系统、长任务、subagent 集群、深度研究、内容构建、FilesystemMiddleware、SubAgentMiddleware、SkillsMiddleware、MemoryMiddleware、RubricMiddleware、评分量规、CodeInterpreter、eval、PTC、动态子Agent、task()、streaming、事件流、TodoListMiddleware。
---

# Deep Agents v1 编码规范

> Deep Agents = `create_agent()` + **预组装中间件堆栈**。内置文件系统、摘要、子 agent、记忆、技能。
> `create_deep_agent()` 开箱即用；需要精细控制时用 `create_agent()` + 手选中间件。

## 定位：Agent Harness

> LangChain 官方定义：DeepAgents 是 **Agent Harness**（代理即用电池包）——比 Framework 更高层，"a general purpose version of Claude Code"。
> LangChain 是 Agent Framework（抽象层），LangGraph 是 Agent Runtime（基础设施层），DeepAgents 是 Agent Harness（预组装层）。
> — Harrison Chase, "[Agent Frameworks, Runtimes, and Harnesses- oh my!](https://www.langchain.com/blog/agent-frameworks-runtimes-and-harnesses-oh-my)" (2025.10)
> 💡 不确定用哪个？→ 回到父技能 `skills/langchain-v1-suite/SKILL.md` 查路由决策表

## ⚠️ 版本基线：deepagents 0.6 → 0.7（2026-07 breaking，本文档以 ≥0.7.x 为准）

> v0.7 把"框架默认替你做决定"的范围大幅收窄：**默认层更薄，策略由应用显式选择**（输入 Token 降 ~65%）。旧教程/旧代码基于 v0.6 默认值写的部分必须按下面清单核对，**不能照抄 v0.5/0.6 代码**。已核对基线：`deepagents==0.7.1`~`0.7.8`、`langchain>=1.4`。

| v0.7 变化 | 旧行为（v0.6） | 新行为（v0.7+） | 迁移动作 |
|---|---|---|---|
| `TodoListMiddleware` 改为 **opt-in** | 默认装配，`write_todos`/`todos`/规划提示词随 Agent 自带 | 默认**不再装配**（官方评测无显著增益） | 需要时显式加 `middleware=[TodoListMiddleware()]`（从 `langchain.agents.middleware` 导入，**不是** deepagents） |
| 默认基础提示词变空 + 工具说明精简 | 框架附带长通用提示词/教程式工具说明 | 默认基础层为空，接口优于示例 | 业务约束写进自己的 `system_prompt`，别把旧基础提示词复制回来 |
| Backend Factory 移除 | `backend=lambda rt: StoreBackend()` 兼容写法 | 只收**具体实例**；`StoreBackend` 必须显式 `namespace=`（跨用户隔离关键） | 删 `BackendFactory`/`BACKEND_TYPES`/`FileFormat`/`Unset`；用 `StoreBackend(namespace=lambda rt: (rt.server_info.user.identity,))` |
| 文件工具增强 | `write_file` 已存在即报错；无 `delete`；空 `ls/glob` 返回 `[]` | `write_file` 直接覆盖；新增 `delete`（递归删目录=全有或全无）；空目录返回文本 `No files found`；`read_file` 行号后两个空格（不再固定宽度+Tab） | 需要删除就用 `delete`；解析原始工具文本的代码全部重查（`"[]"`/`split("\t")`/固定宽度假设） |
| 大目录搜索有界 | `grep/glob` 可能挂起或丢结果 | 超时返回已得结果并标记 `truncated=True`；`grep` 默认上限 1000 匹配（模型可 `max_count` 调）；`read_file` 分页返回总行数/剩余/下一 offset | "无异常"≠搜索完整；看到 `truncated` 要收窄路径或继续分片 |
| Middleware **按 `.name` 原位替换** | 传入同名内置中间件实例报重复错误 | `.name` 与内置同名 → 原位替换（保留栈顺序）；无同名 → 插到核心层之后 | 覆盖 `SummarizationMiddleware` 阈值/模型/提示词直接传新实例；**整实例替换，不是字段 merge**（backend/权限等要自备） |
| Prompt caching / Profile | — | `deepagents[aws]` Bedrock 缓存；Fireworks 自动 session affinity；Nemotron 3 Ultra 内置 HarnessProfile | 按需关注，与通用 API 无关 |

**v0.6→v0.7 静态扫描清单**（迁移时执行）：
```bash
rg -n 'BackendFactory|BACKEND_TYPES|FileFormat|Unset|history_path_prefix|ls_info|glob_info|grep_raw' .
rg -n 'backend\s*=\s*(lambda|.*_factory)' .
rg -n 'split\("\\t"|"\[\]"|cat -n|No files found' .
```

## ⚠️ 选型边界：什么时候**不该**用 Deep Agents

> 菜刀功能齐全，但修指甲该用指甲刀。Deep Agents 不是万能答案。

### ✅ 该用 Deep Agents 的信号

- 任务涉及**多文件读写**、多步骤规划、子任务委派
- 需要**自动上下文管理**（大结果卸载、对话压缩）
- 需要**跨会话持久化记忆**（用户偏好、累积知识）
- 需要**子 Agent 并行或异步执行**
- 任务复杂到"Agent 一次 invoke 不够用"

### ❌ 不该用 Deep Agents 的信号 — 用 `create_agent()` 就够了

- **单轮问答**、简单 tool-calling（查天气、算数学、翻译）
- **不需要文件系统**、不涉及多步骤规划
- 上下文短、一次调用就能完成
- 用户明确说"简单"、"快速"、"轻量"
- 只需要 1-2 个工具，且工具返回很短

### 🔀 该直接用 LangGraph 的信号 — 跳过 Deep Agents

- 需要**精细控制图编排**（分支、循环、条件边）
- 需要自行管理 checkpoint 和 state schema
- Deep Agents 的预设中间件反而碍事
- 已有成熟的 LangGraph 图，只想加 Agent 能力 → 用 `create_agent()` + 自定义中间件

### 竞品对比速查

| 维度 | Deep Agents | Claude Agent SDK | Codex SDK |
|------|-------------|------------------|-----------|
| 模型绑定 | **模型无关** 100+ | 绑定 Claude | 绑定 OpenAI |
| 长期记忆 | ✅ StoreBackend | ❌ | ❌ |
| 虚拟文件系统 | ✅ 可插拔后端 | 本地 | 本地 |
| 沙箱执行 | ✅ Sandbox-as-Tool | ❌ | ✅ OS 级 |
| 生产部署 | LangSmith 全链路 | 自定义 HTTP | 云端 |

> **一句话**：需要模型灵活性 + 跨会话记忆 → Deep Agents。全员 Claude → Claude Agent SDK。全员 OpenAI → Codex SDK。

## 定位

```
DeepAgents  ← 预组装 harness ← 你现在在这
    │         内置: FilesystemMiddleware + SummarizationMiddleware
    │         + SubAgentMiddleware + MemoryMiddleware + SkillsMiddleware
    │         适用: 长任务、代码生成、深度研究、内容构建
    │
LangChain   ← Agent框架 (create_agent, @tool, middleware)
    │
LangGraph   ← 编排运行时 (StateGraph, persistence, streaming)
```

---

## 1. 快速开始

```python
# pip install deepagents langchain-openai
from deepagents import create_deep_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    tools=[get_weather],
    system_prompt="You are a helpful assistant.",
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in SF?"}]}
)
```

### 国内模型配置（硅基流动直连）

无需代理，兼容 OpenAI 接口，永久免费模型可用：

```python
from langchain_openai import ChatOpenAI
import os

# 免费模型（学习实验）
model = ChatOpenAI(
    model="THUDM/glm-4-9b-chat",  # 128K 上下文，支持 Tools，永久免费
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
)

# 推荐模型（实际项目）
# "Pro/zai-org/GLM-5"        — 智谱旗舰，Agent 任务最佳
# "Pro/moonshotai/Kimi-K2.5" — Kimi 旗舰，256K 上下文
# "Qwen/Qwen3.5-27B"         — Qwen 最新，支持思考模式
# "deepseek-ai/DeepSeek-V3.2"— 推理 + Agent 顶级
```

> `ChatOpenAI` + `base_url` 是接入国内平台的通用模式——换 URL 和 Key 就能切 DeepSeek、智谱、阿里云等。

**`create_deep_agent()` 自动装配（v0.7+ 实际默认）：**
- `FilesystemMiddleware` — 虚拟文件系统（v0.7 起内置 `delete`，`write_file` 已存在直接覆盖，空 `ls/glob` 返回 `No files found`）
- `SummarizationMiddleware` — 上下文超限自动压缩（默认约 85% 触发，可用同名实例覆盖阈值）
- 内置 `general-purpose` 子 agent（默认可用，继承主 Agent 工具/权限/中间件覆盖）
- `MemoryMiddleware` — 仅当传 `memory=` 时激活
- `SkillsMiddleware` — 仅当传 `skills=` 时激活
- ⚠️ **v0.7 起 `TodoListMiddleware` 不再默认装配**——需要规划/进度 UI 时显式加：
  ```python
  from langchain.agents.middleware import TodoListMiddleware
  agent = create_deep_agent(model=model, middleware=[TodoListMiddleware()])
  ```

---

## 2. 内置能力

### 2.1 文件系统（FilesystemMiddleware）

```python
from deepagents import create_deep_agent
from deepagents.backends import StateBackend

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    backend=StateBackend(),  # 或 FilesystemBackend(root_dir="...")
)

# Agent 自动获得文件系统工具：read_file, write_file, edit_file, delete, ls, glob, grep
# 文件跨轮次持久化在 state 中
# v0.7：write_file 已存在时直接覆盖；delete 递归删目录=全有或全无（权限层整体检查后代路径）
#      read_file 分页返回 {总行数, 剩余行数, 下一 offset}；grep/glob 超时返回 truncated=True 的部分结果
#      需要最小工具面时用 FilesystemMiddleware(backend=..., tools=["read_file","ls","glob","grep"]) allowlist（read_file 不可排除）
```

**六种 Backend 完整参考：**

| Backend | 存储位置 | 持久化 | 适用场景 | 安全风险 |
|---------|---------|:--:|------|------|
| `StateBackend()` | Agent state（内存） | 同线程内 | 默认选择、临时草稿纸 | 低 |
| `FilesystemBackend(root_dir)` | 本地磁盘 | ✅ 永久 | 本地 CLI、编程助手 | ⚠️ 可读 `.env` 等敏感文件 |
| `LocalShellBackend(root_dir)` | 本地磁盘 + Shell | ✅ 永久 | 个人开发机 | 🔴 可执行任意命令 |
| `StoreBackend(namespace=...)` | LangGraph Store | ✅ 跨会话 | 长期记忆、知识库 | 低 |
| `CompositeBackend(routes={...})` | 混合路由 | 混合 | 多后端组合 | 取决于子后端 |
| 沙箱后端 | 隔离容器 | ✅ 永久 | 安全代码执行 | 低 |

**CompositeBackend 混合路由：**不同路径自动走不同后端：

```python
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

agent = create_deep_agent(
    model=model,
    backend=CompositeBackend(
        default=StateBackend(),           # 默认临时
        routes={
            "/memories/": StoreBackend(    # /memories/ 下持久化
                namespace=lambda rt: (rt.server_info.user.identity,),
            ),
        },
    ),
)
# Agent 写入 /workspace/plan.md → StateBackend（临时）
# Agent 写入 /memories/prefs.txt → StoreBackend（跨会话持久化）
# ls/glob/grep 自动聚合所有后端结果
```

**声明式权限：**

```python
from deepagents import FilesystemPermission

# 禁止写入 /policies/ 下任何文件
FilesystemPermission(operations=["write"], paths=["/policies/**"], mode="deny")
```

**自定义后端：**实现 `BackendProtocol` 6 个方法（`ls`、`read`、`write`、`edit`、`grep`、`glob`），可接入 S3/Postgres 等任意存储。

```python
from deepagents.backends.protocol import (
    BackendProtocol, WriteResult, EditResult, LsResult,
    ReadResult, GrepResult, GlobResult,
)

class S3Backend(BackendProtocol):
    def __init__(self, bucket: str, prefix: str = ""):
        self.bucket = bucket
        self.prefix = prefix.rstrip("/")

    def ls(self, path: str) -> LsResult:
        ...  # 列出对象，返回 FileInfo 列表

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult:
        ...  # 返回 ReadResult(file_data=...) 或 ReadResult(error=...)

    def write(self, file_path: str, content: str) -> WriteResult:
        ...  # 外部存储后端 files_update=None

    def edit(self, file_path: str, old: str, new: str, replace_all: bool = False) -> EditResult:
        ...  # 读取 → 替换 → 写回

    def grep(self, pattern: str, path: str = None, glob: str = None) -> GrepResult:
        ...  # 正则搜索

    def glob(self, pattern: str, path: str = "/") -> GlobResult:
        ...  # 通配符匹配
```

**安全策略（PolicyWrapper / GuardedBackend）：**

对需要拦截策略（速率限制、审计日志、内容检查）的场景，继承现有后端覆写方法：

```python
class GuardedBackend(FilesystemBackend):
    def __init__(self, *, deny_prefixes: list[str], **kwargs):
        super().__init__(**kwargs)
        self.deny_prefixes = [p.rstrip("/") + "/" for p in deny_prefixes]

    def write(self, file_path: str, content: str) -> WriteResult:
        if any(file_path.startswith(p) for p in self.deny_prefixes):
            return WriteResult(error=f"写入被拒绝：{file_path}")
        return super().write(file_path, content)

    def edit(self, file_path: str, old: str, new: str, replace_all: bool = False) -> EditResult:
        if any(file_path.startswith(p) for p in self.deny_prefixes):
            return EditResult(error=f"编辑被拒绝：{file_path}")
        return super().edit(file_path, old, new, replace_all)
```

**后端选择指南：**

| 场景 | 推荐后端 | 理由 |
|------|---------|------|
| 学习和实验 | `StateBackend()`（默认） | 零配置，自动清理 |
| 本地编程助手 | `FilesystemBackend(root_dir=".")` | 直接操作项目文件 |
| 需要跨会话记忆 | `CompositeBackend` | 混合临时 + 持久化 |
| 需要执行代码 | 沙箱后端 | 安全隔离 |
| 生产部署 | `StoreBackend` 或 `CompositeBackend` | 持久化 + 可伸缩 |

**自动上下文管理（无感知）：**
- 工具结果 >20K tokens → 自动卸载到文件系统，对话中替换为文件引用 + 前 10 行预览
- 上下文达窗口 85% → 自动生成结构化摘要，完整记录保存到文件系统
- Agent 随时 `read_file`/`grep` 回溯完整内容

### 2.2 代码执行（QuickJS Interpreters + PTC + Sandboxes）

> **Interpreter ≠ Sandbox**。Interpreter（`CodeInterpreterMiddleware`，Beta）是 **Agent 循环内的内存 JS 运行时**（QuickJS），让模型用代码编排循环/筛选/批量工具调用，中间结果不进模型上下文；Sandbox 是独立容器/VM 里执行 Shell/依赖/测试（见 §2.7）。需要 Python 3.11+ 与 `langchain-quickjs>=0.2.0`（安装 `uv add "deepagents[quickjs]"`）。

**选型：普通 Tool Calling vs Interpreter vs Sandbox vs Dynamic Subagents**

| 任务形状 | 优先选择 |
|---|---|
| 一两个简单外部调用 | 普通 Tool Calling |
| 纯内存排序/分组/解析/校验 | `CodeInterpreterMiddleware`（纯 JS） |
| 大量外部调用需循环/并行 | `CodeInterpreterMiddleware` + **PTC**（`Promise.all` 批量） |
| Shell/装依赖/跑测试/完整文件系统 | Sandbox（§2.7） |
| 大量独立任务需不同 Agent 角色 | Dynamic Subagents（§2.8，代码调度 `task()`） |

**基础用法（`eval` 工具）：**

```python
from deepagents import create_deep_agent
from langchain_quickjs import CodeInterpreterMiddleware

agent = create_deep_agent(
    model=model,
    system_prompt="Use eval for deterministic filtering and aggregation.",
    middleware=[CodeInterpreterMiddleware(mode="call")],  # call|turn|thread
)
# Agent 获得 eval 工具 → 把自写 JS 交给 QuickJS 执行，返回最后一个表达式值
```

**PTC（Programmatic Tool Calling）— 白名单工具以 `tools.*` 暴露给 JS：**

```python
from langchain.tools import tool
from langchain_quickjs import CodeInterpreterMiddleware

@tool
def lookup_order(order_id: str) -> dict: ...   # 窄工具：按 ID 读一条

agent = create_deep_agent(
    model=model,
    tools=[lookup_order],                        # 或 tools=[]，仅 PTC 用
    middleware=[
        CodeInterpreterMiddleware(
            ptc=[lookup_order],   # 传 BaseTool 对象=只给解释器；传 "lookup_order" 名称=从 Agent 工具集匹配
            mode="turn",
            max_ptc_calls=16,
        )
    ],
)
```

```typescript
// Python snake_case 工具名 → JS camelCase：lookup_order → tools.lookupOrder
// 参数名保持原 Tool Schema（仍是 order_id，不是 orderId）
const rows = await Promise.all(ids.map(id => tools.lookupOrder({ order_id: id })));
```

**配置参数（默认值）：**

| 参数 | 默认 | 说明 |
|---|---:|---|
| `mode` | `"thread"` | 状态保留：`call`(单次 eval 重置)/`turn`(本轮多次 eval 共享)/`thread`(跨轮，Snapshot+Checkpointer) |
| `memory_limit` | 64 MB | 每线程 QuickJS 堆上限 |
| `timeout` | 5 s | 每次 `eval` 执行时限 |
| `max_ptc_calls` | 256 | 单次 `eval` 内 PTC 调用上限（**不限制 `task()` 调度数**） |
| `max_result_chars` | 4000 | 截断返回模型的结果/错误/console |
| `capture_console` | True | 是否返回 console 输出 |
| `subagents` | True | 配子 Agent 时是否暴露 `task()`（§2.8 用） |
| `max_snapshot_bytes` | None | Snapshot 上限（默认跟随内存上限） |

**安全边界（不可绕过）：**
- QuickJS 默认**无**文件/网络/Shell/系统时间；PTC 白名单里放什么工具，JS 就能做什么 → 优先窄工具，宽 SQL/任意 URL 不进白名单
- ⚠️ PTC 调用**不逐次走父 Agent 的 `interrupt_on` 审批**——转账/删库/发信等高副作用工具必须走普通工具路径或保留 HITL
- QuickJS 是进程内受限运行时，**不是宿主内存隔离**；不可信代码仍要进 Sandbox/容器
- Snapshot 恢复不撤销 PTC 已造成的外部副作用（不是事务）

### 2.3 子 Agent（SubAgentMiddleware）

> 核心动机：**Context Quarantine（上下文隔离）**— 子 Agent 在独立上下文中工作，只返回精炼结果给主 Agent。

**字段完整参考（10 个字段 + 继承规则）：**

| 字段 | 必填 | 继承主Agent？ | 说明 |
|------|:--:|:--:|------|
| `name` | ✅ | — | 唯一标识，主 Agent 靠它指定委派给谁 |
| `description` | ✅ | — | 能力描述，主 Agent **据此决策路由**（越具体越准） |
| `system_prompt` | ✅ | ❌ 不继承 | 子 Agent 专属指令，需独立定义 |
| `tools` | 可选 | ✅ 默认继承 | 指定后**完全替换**（不合并） |
| `model` | 可选 | ✅ 默认继承 | 可指定不同模型或 `"provider:model"` 字符串 |
| `middleware` | 可选 | ❌ 不继承 | 子 Agent 自己的中间件 |
| `interrupt_on` | 可选 | ✅ 默认继承 | 可覆盖主 Agent 的 HITL 配置 |
| `skills` | 可选 | ❌ 不继承 | 指定后独立运行 SkillsMiddleware |
| `response_format` | 可选 | ❌ 不继承 | Pydantic schema 结构化输出（需 >=0.5.3） |
| `permissions` | 可选 | ✅ 默认继承 | 指定后**完全替换**（不合并） |

> 关键：`system_prompt` 和 `tools` 的继承行为不同 — tools 默认继承主 Agent，system_prompt 需要独立写。

**三种定义形态：**

| 形态 | 用法 | 适用 |
|------|------|------|
| Dict 定义 | `{"name": "...", "tools": [...], ...}` | **大多数情况**，简单直观 |
| `CompiledSubAgent` | `CompiledSubAgent(name="...", runnable=graph)` | 复用现成 LangGraph 图 |
| 转子 Agent | `create_deep_agent(name="...", ...).as_subagent()` | 快速原型 |

**General-purpose 子 Agent**（默认可用，继承主 Agent 全部能力）：

```python
# 禁用（不想让 Agent 有 task 工具时）
from deepagents.profiles import GeneralPurposeSubagentProfile, HarnessProfile
agent = create_deep_agent(
    model=model, subagents=[],
    profile=HarnessProfile(general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False)),
)

# 覆盖（给默认子 Agent 配更强模型）
agent = create_deep_agent(model=model, subagents=[
    {"name": "general-purpose", "description": "通用助手", "system_prompt": "...",
     "model": ChatOpenAI(model="Pro/zai-org/GLM-5", ...)},
])
```

**结构化输出**（子 Agent → 主 Agent 返回 JSON）：`"response_format": ResearchFindings` → ToolMessage 收到 `'{"summary": "...", "confidence": 0.87}'`

**最佳实践 5 条：**
1. **描述要具体** — ✅ `"需要多次搜索、交叉验证和综合分析时使用"` vs ❌ `"做研究"`
2. **提示词要详细** — 必须含输出格式 + 字数限制，否则子 Agent 返回大量原始数据 → 上下文隔离失效
3. **工具集要精简** — 最小权限原则，只给需要的工具
4. **模型分级** — 轻量任务用免费模型，深度分析用旗舰模型
5. **输出要精练** — 强制 `"返回结果控制在 500 字以内"`

**排障 3 问：**
- 子 Agent 没被调用 → `description` 太模糊，或主 Agent system_prompt 没指示委派
- 上下文依然膨胀 → 子 Agent 返回了原始数据，未做字数限制
- 调错子 Agent → 多个 `description` 过于相似，需明确区分使用场景

### 2.4 记忆（MemoryMiddleware）

> Deep Agents 将记忆作为一等公民——Agent 以文件形式读写记忆，Backend 控制存储位置。核心机制：**文件路径路由** → `/memories/` 前缀走 StoreBackend 持久化，其他路径走 StateBackend（临时）。

**两种记忆对比：**

| 维度 | 短期记忆（Checkpointer） | 长期记忆（Store） |
|------|----------------------|------------------|
| **作用域** | 同一 `thread_id` 内 | **跨 thread、跨会话** |
| **存储层** | LangGraph Checkpointer | LangGraph Store |
| **开发用** | `MemorySaver`（内存，重启丢失） | `InMemoryStore`（内存，重启丢失） |
| **生产用** | `PostgresSaver`（DB 持久化） | `PostgresStore`（DB 持久化） |
| **典型内容** | 消息历史、文件系统状态、任务清单 | 用户偏好、项目背景、累积知识 |

**基础用法：**

```python
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

agent = create_deep_agent(
    model=model,
    memory=["/memories/AGENTS.md"],       # 启动时加载到 system prompt
    backend=CompositeBackend(
        default=StateBackend(),            # 临时文件
        routes={
            "/memories/": StoreBackend(    # 持久化文件（跨会话）
                namespace=lambda rt: (rt.server_info.user.identity,),
            ),
        },
    ),
)
```

Agent 的读写完全透明——`write_file("/workspace/draft.txt")` → StateBackend（临时），`write_file("/memories/prefs.md", "简洁代码")` → StoreBackend（下次对话仍可读）。

**三种作用域：**

| 作用域 | namespace 函数 | 可见性 | 典型用途 |
|--------|---------------|--------|---------|
| **Agent 级** | `(rt.server_info.assistant_id,)` | 所有用户共享 | 项目背景、技术规范 |
| **用户级** | `(rt.server_info.user.identity,)` | 仅该用户 | 偏好设置、个人笔记 |
| **组织级** | `(org_id,)` | 全体成员（通常只读） | 合规策略、公司规范 |

```python
def agent_namespace(rt):
    return (rt.server_info.assistant_id,)

def user_namespace(rt):
    return (rt.server_info.user.identity,)

def org_namespace(rt):
    return (getattr(rt.context, "org_id", "default-org"),)
```

**四种实用场景：**

| 场景 | 做法 |
|------|------|
| 用户偏好记忆 | `memory=["/memories/preferences.md"]` → Agent 首次对话记住，后续自动加载 |
| 自我改进 Agent | Agent 记录"上次这个任务踩了什么坑"到 `/memories/lessons.md`，下次避开 |
| 知识库累积 | 多次研究对话逐渐积累到 `/memories/knowledge/`，形成个人知识库 |
| 研究项目持续推进 | 同一项目跨多次对话推进，所有中间产物持久化 |

**记忆的六个维度（设计参考）：**

| 维度 | 选项 |
|------|------|
| **内容类型** | 情景记忆（过去经历）/ 程序性记忆（Skills）/ 语义记忆（事实） |
| **作用域** | 用户级 / Agent 级 / 组织级 |
| **更新策略** | 对话中实时 / 对话间后台整合 |
| **检索方式** | 启动加载（`memory=`）/ 按需读取（文件系统工具） |
| **权限控制** | 读写 / 只读（组织策略防注入） |
| **并发写入** | 多 Agent 同时写同一文件 → last-write-wins |

**生产升级路径：**

```python
# 开发阶段
from langgraph.store.memory import InMemoryStore
store = InMemoryStore()

# 生产阶段
from langgraph.store.postgres import PostgresStore
import os

with PostgresStore.from_conn_string(os.environ["DATABASE_URL"]) as store:
    store.setup()  # 首次自动建表
    agent = create_deep_agent(
        model=model,
        memory=["/memories/AGENTS.md"],
        store=store,  # ← 传入生产 Store
        backend=CompositeBackend(
            default=StateBackend(),
            routes={"/memories/": StoreBackend(namespace=user_namespace)},
        ),
    )
```

> **最佳实践**：(1) 用描述性路径如 `/memories/project/tech-stack.md` 而非 `/memo.txt`；(2) 用 `memory=` 声明而非在 system_prompt 里手写；(3) 按主题拆分文件；(4) 组织级策略设只读防注入攻击。

### 2.5 技能（SkillsMiddleware）

> Skills = 目录结构 `SKILL.md` + 可选 `scripts/` `references/` `assets/`。
> Deep agent skills 遵循 [Agent Skills 规范](https://agentskills.io/specification)。
> 核心机制：**渐进披露（Progressive Disclosure）**— Agent 只在需要时加载完整技能内容。

**基础结构：**

```python
from deepagents.middleware import SkillsMiddleware

SkillsMiddleware(
    backend=StateBackend(),
    sources=["./skills/"],  # 技能目录，按需加载
)
```

```
skills/
├── langgraph-docs/
│   └── SKILL.md            # 必需：YAML frontmatter + markdown 指令
├── arxiv-search/
│   ├── SKILL.md
│   ├── scripts/
│   │   └── search.py      # 可执行脚本
│   └── references/
│       └── api-guide.md    # 参考文档
└── order-helpers/
    ├── SKILL.md
    └── assets/
        └── template.json   # 模板等资源
```

**Interpreter Skills（可执行代码技能）：**

```python
# skills/arxiv-search/SKILL.md  frontmatter:
# ---
# name: arxiv-search
# description: Search arxiv for research papers
# module: scripts/search.py     ← 关键：声明为 interpreter skill
# ---

# skills/arxiv-search/scripts/search.py
def search_arxiv(query: str, max_results: int = 10) -> dict:
    """Search arxiv API and return structured results."""
    import requests
    resp = requests.get(f"https://api.arxiv.org/...")
    return resp.json()
```

> Interpreter skills 的 `module` frontmatter 让 Agent 可以将 skill 加载为可调用 Python 模块。

**技能权限（Skill Permissions）：**

```python
from deepagents.middleware import SkillsMiddleware

SkillsMiddleware(
    backend=StateBackend(),
    sources=["./skills/"],
    permissions={
        # 所有用户共享技能
        "langgraph-docs": {"type": "shared", "users": "*"},
        # 限定用户才能用
        "admin-tools": {"type": "limited", "users": ["admin", "operator"]},
        # 只读（禁止 Agent 写入修改）
        "compliance-rules": {"type": "read_only"},
        # Agent 可编辑的个人技能
        "my-notes": {"type": "editable", "scope": "user"},
    },
)
```

**运行时动态加载技能：**

```python
# 固定列表
agent = create_deep_agent(model=model, skills=["./skills/basic/"])

# 动态列表（按环境/用户切换）
def get_skills(runtime):
    if runtime.context.get("tier") == "pro":
        return ["./skills/basic/", "./skills/pro/"]
    return ["./skills/basic/"]

agent = create_deep_agent(model=model, skills=get_skills)

# 命名空间技能（不同用户看不同技能）
agent = create_deep_agent(model=model, skills=[
    "./skills/shared/",
    {"namespace": "user-123", "source": "./skills/personal/"},
])
```

**子 Agent 专属技能：**

```python
subagents = [{
    "name": "researcher",
    "description": "深度调研",
    "system_prompt": "你是研究员...",
    "skills": ["./skills/research/"],  # 只给 researcher 的专属技能
}]
agent = create_deep_agent(model=model, subagents=subagents)
```

**Sandbox 脚本技能** — 在隔离环境中执行 skill 代码：

```python
SkillsMiddleware(
    backend=StateBackend(),
    sources=["./skills/"],
    sandbox=True,  # 启用沙箱执行
)
```

> 完整参考: `docs/official/deepagents-skills.md` (1012行) | [Agent Skills 规范](https://agentskills.io/specification)

---

### 2.6 中间件装配架构

> `create_deep_agent()` 的本质 = `create_agent()` + 三层自动装配的中间件堆栈。

**核心层（v0.7 起自动启用；`TodoListMiddleware` 已移出默认层，改为 opt-in）：**

| 中间件 | 注入能力 | 默认状态 |
|--------|---------|:--:|
| `FilesystemMiddleware` | 6+ 个文件工具（含 v0.7 的 `delete`）+ 权限控制 | ✅ 默认 |
| `SummarizationMiddleware` | 对话历史自动压缩（默认 ~85% 触发，可用同名实例覆盖） | ✅ 默认 |
| `PatchToolCallsMiddleware` | 工具调用内部修补（框架内部） | ✅ 默认 |
| `AnthropicPromptCachingMiddleware` | 提示词缓存（非 Anthropic 模型自动跳过） | ✅ 默认 |
| `TodoListMiddleware` | `write_todos` 工具 + 规划提示词 | ⚠️ **v0.7 起 opt-in** |

> **中间件原位覆盖（v0.7）**：`middleware=[你的实例]` 的 `.name` 与内置同名 → **在原位替换**默认实例（保留栈顺序），可调 Summarization 的 `trigger/keep/model/prompt` 而不拆 Harness。是**整实例替换**，不是字段 merge——替换实例要自带 backend 等完整配置。默认 `general-purpose` 子 Agent 继承主 Agent 覆盖；声明式子 Agent 独立配自己的栈。

**条件层（5 个，按参数自动激活）：**

| 触发条件 | 中间件 | 注入能力 |
|---------|--------|---------|
| 有子 Agent | `SubAgentMiddleware` | `task` 工具 + 子 Agent 上下文隔离 |
| 传 `skills=` | `SkillsMiddleware` | 从 `skills/` 目录加载领域知识 |
| 有异步子 Agent | `AsyncSubAgentMiddleware` | 5 把遥控器工具 |
| 传 `memory=` | `MemoryMiddleware` | 从 `AGENTS.md` 加载持久记忆 |
| 传 `interrupt_on=` | `HumanInTheLoopMiddleware` | 拦截指定工具等待人工审批 |

**用户自定义层（`middleware=[]` 按需叠加，LangChain 预构建的全部可用）：**

| 类别 | 中间件 | 用途 |
|------|--------|------|
| 安全 | `PIIMiddleware` | 个人信息检测脱敏 |
| 弹性 | `ToolRetryMiddleware` | 工具失败自动重试 |
| | `ModelRetryMiddleware` | 模型失败自动重试 |
| | `ModelFallbackMiddleware` | 主模型失败切换备用 |
| 限制 | `ToolCallLimitMiddleware` | 限制工具调用次数 |
| | `ModelCallLimitMiddleware` | 限制模型调用次数 |
| 上下文 | `ContextEditingMiddleware` | 清理旧工具调用结果 |

**手动组合对照：**

```python
# create_deep_agent() 帮你做的：
agent = create_deep_agent(model=model, tools=[search])

# 等价于 create_agent() + 手动装配：
from langchain.agents import create_agent
from langchain.agents.middleware import (
    TodoListMiddleware, FilesystemMiddleware, SummarizationMiddleware
)
agent = create_agent(
    model=model, tools=[search],
    middleware=[
        TodoListMiddleware(),
        FilesystemMiddleware(),
        SummarizationMiddleware(model=model, trigger=("tokens", 4000), keep=("messages", 20)),
    ],
)
```

**TodoListMiddleware 自定义配置：**

```python
from langchain.agents.middleware import TodoListMiddleware

TodoListMiddleware(
    system_prompt="将任务拆解为可执行的步骤，先写测试再写代码。",
    tool_description="管理任务列表的工具。每个任务包含 content（内容）和 status（状态）。",
)
```

**write_todos 任务数据结构：**

```python
# 每个任务：{"content": "任务描述", "status": "pending|in_progress|completed"}
# 状态流转：pending → in_progress → completed
```

Agent 典型行为：收到复杂任务 → 调用 `write_todos([{...pending...}, ...])` 制定计划 → 逐个执行 `pending→in_progress→completed` → 执行中发现新步骤动态追加。

**SummarizationMiddleware 触发机制：**
- `trigger=("tokens", 4000)` — 上下文超过 4000 tokens 触发压缩
- `keep=("messages", 20)` — 保留最近 20 条消息不压缩
- 压缩时会用 LLM 生成结构化摘要（意图、产出物、下一步），完整原始对话保存到文件系统
- **与 TodoListMiddleware 协同**：即使对话被压缩，任务清单仍然完整——Agent 知道当前进度

### 2.7 沙箱执行（SandboxBackendProtocol）

> 沙箱 = 一种特殊的 Backend。普通 Backend（State/Filesystem/Store）只管文件读写；沙箱 Backend **额外实现 `execute()`**，让 Agent 能安全运行代码。Deep Agents 在每次模型调用前检查 Backend 是否实现 `SandboxBackendProtocol`，是则暴露 `execute` 工具。

**快速上手（LangSmith Sandbox）：**

```python
from deepagents import create_deep_agent
from deepagents.backends.langsmith import LangSmithSandbox
from langsmith.sandbox import SandboxClient

client = SandboxClient()
sandbox = client.create_sandbox()  # template_name=, name=, idle_ttl_seconds=
backend = LangSmithSandbox(sandbox=sandbox)

agent = create_deep_agent(
    model="claude-sonnet-4-6",
    backend=backend,
    system_prompt="You are a coding assistant with sandbox access.",
)

result = agent.invoke({"messages": [{"role": "user", "content": "..."}]})
client.delete_sandbox(sandbox.name)  # ← 必须清理！
```

**8 个 Python Provider：**

| Provider | 安装包 | Backend 类 | 创建 → 清理 |
|----------|--------|-----------|------------|
| LangSmith | `langsmith[sandbox]` | `LangSmithSandbox` | `create_sandbox()` → `delete_sandbox()` |
| AgentCore | `langchain-agentcore-codeinterpreter` | `AgentCoreSandbox` | `CodeInterpreter().start()` → `interpreter.stop()` |
| Daytona | `langchain-daytona` | `DaytonaSandbox` | `Daytona().create()` → `sandbox.stop()` |
| E2B | `langchain-e2b` | `E2BSandbox` | `Sandbox.create()` → `sandbox.kill()` |
| Modal | `langchain-modal` | `ModalSandbox` | `modal.Sandbox.create()` → `sandbox.terminate()` |
| Runloop | `langchain-runloop` | `RunloopSandbox` | `devbox.create()` → `devbox.shutdown()` |
| Vercel | `langchain-vercel-sandbox` | `VercelSandbox` | `Sandbox.create()` → `sandbox.stop()` |
| NVIDIA | `langchain-nvidia-openshell` | `OpenShellSandbox` | 构造 → `delete_on_exit=True` |

**文件两个平面：**

```
Agent 平面（沙箱内工具）         宿主平面（Python API）
─────────────────────           ─────────────────────
read_file / write_file          upload_files()    ← 播种依赖/基准数据
edit_file / delete              download_files()  ← 提取产物/审查输出
ls / glob / grep
execute                        　　　　　　　　　　   ← 命令执行，不受文件权限约束
```

**生命周期：**

| 模式 | 复用策略 | 清理 |
|------|---------|------|
| **Thread-scoped**（默认） | `sandbox_name = f"thread-{thread_id}"` + `idle_ttl_seconds` | TTL 到期自动回收 |
| **Assistant-scoped** | `sandbox_name = f"assistant-{assistant_id}"`，跨对话共享 | 需手动清理 |

**安全铁三角（互不替代，必须组合）：**

```
内置文件工具 → FilesystemPermission  ← §4
MCP 工具     → Server ACL + Interceptor + HITL  ← MCP 集成节
沙箱 execute → 凭证不出沙箱 + 网络控制 + 产物审查  ← 本节
```

> **最佳实践**：① 沙箱资源不论成败都在 `finally` 中清理；② 凭证永远优先留在沙箱外（宿主侧工具 > Auth Proxy > 注入沙箱）；③ 沙箱输出默认不可信，审查后再使用。

### 2.8 动态子 Agent（Dynamic Subagents，Beta）

> 普通 `task` 工具 = 主模型**逐次**委派；Dynamic Subagents = 主模型写一段 JS，在**一次 `eval` 内多次调用 `task()`** 完成批量扇出/多阶段/迭代收敛（覆盖完整、无漏项、控制流稳定）。依赖 QuickJS Interpreter（`deepagents==0.7.x` + `langchain-quickjs` 核对）。

```python
agent = create_deep_agent(
    model=model,
    subagents=[
        {"name": "reviewer", "description": "审查代码并给出文件、行号和证据",
         "system_prompt": "只报告有代码证据的候选问题；稳定 ID 用'文件:行号:问题类型'。"},
        {"name": "verifier", "description": "独立复核候选问题并优先识别误报",
         "system_prompt": "重新读取代码，寻找反证后再确认或反驳。"},
    ],
    middleware=[CodeInterpreterMiddleware(mode="turn", subagents=True)],
)
```

**`task()` 调用契约（JS 全局函数，仅三个字段）：**
| 字段 | 必填 | 说明 |
|---|---|---|
| `description` | ✅ | 子 Agent 任务说明，需自包含（含文件路径等定位信息） |
| `subagentType` | ✅ | 必须匹配 `subagents` 里的 `name` |
| `responseSchema` | ❌ | JSON Schema 约束返回值；设置后直接得到 JS 对象（无需 JSON.parse） |

```typescript
const review = await task({ description: "检查 src/auth/login.ts，引用行号",
  subagentType: "reviewer", responseSchema: {...} });
```

**使用要点：**
- 用户请求里用 `workflow` 一词引导主模型走代码编排，并写清：输入范围 / 可用角色 / 先后与并行 / 去重、数量上限、停止条件、最终返回
- 每次 `task()` 都启动**完整子 Agent 推理循环**；`max_ptc_calls` 只管 `tools.*`，**没有 `max_task_calls` 参数**——调度量靠输入批次 + 循环上限 + 提示词约束
- 单次明确委派仍用普通 `task` 工具；异步长程后台任务用 §6 Async Subagents（生命周期目标不同）
- 模型能力不足时 JS 可能语法错误/角色名漂移/循环失控 → 运行前人工检查生成代码
- 支持**递归语言模型（RLM）**工作流：子 Agent 结果可再次作为输入调度下一层 `task()`，形成递归分解

**六种编排模式（官方，interpreter 代码内 `task()` 组合）：**

| 模式 | 形态 | 适用 |
|------|------|------|
| **Classify and act** | 先分类再分发：按输入类型 `if/else` 选不同 `subagentType` | 异构输入需要差异化处理 |
| **Fan-out and synthesize** | 并行扇出（`Promise.all` 多路 `task()`）→ 汇总合成 | 大批量独立子任务，覆盖完整无漏项 |
| **Adversarial verification** | 生成者 vs 验证者互搏：候选 → 独立复核找反证 | 高可信要求（代码审查、事实核验） |
| **Generate and filter** | 批量生成 → 按约束过滤（`filter` 淘汰不合格项） | 候选池 + 质量门槛（内容生成） |
| **Tournament** | 锦标赛逐轮淘汰：多路生成 → 两两对比选优 | 多方案择优（代码改写选最优变体） |
| **Loop until done** | 迭代循环直到满足停止条件（带次数上限防失控） | 渐进收敛型任务（重写直到通过测试） |

> `task()` 从运行中的 `eval` 内部派发，不经过普通 tool-calling 路径 → 隔离默认、审批边界与普通工具调用一致；`max_ptc_calls` 不约束 `task()`，调度上限靠代码结构（循环/批次）自行控制。

### 2.9 运行时验收（RubricMiddleware 评分量规，Beta）

> 解决"Agent 说完成 ≠ 通过验收"：Working Model 生成候选 → Grader Model 按 Rubric + Evidence Tool 证据评审 → `needs_revision` 携差距回炉修订 → 只有 `satisfied` 放行。`RubricMiddleware` 需要 `deepagents>=0.6.5`，本章案例按 0.7.x 核对；Beta API。

```python
from deepagents import RubricMiddleware
from deepagents.middleware.rubric import RubricEvaluation

rubric_middleware = RubricMiddleware(
    model=grader_model,                       # 评分模型（必填，可同/低于工作模型）
    system_prompt="...strict grader...",      # 约束评分方式，不替代 Rubric
    tools=[run_test_suite],                   # 取证工具——只给评分模型，不会成为工作模型工具！
    max_iterations=3,                         # 一次评分尝试最多 N 轮（非"至少修订 3 次"）
    on_evaluation=record_evaluation,          # 每轮 RubricEvaluation 回调（日志/指标，非控制钩子）
)

agent = create_deep_agent(
    model=working_model,
    middleware=[rubric_middleware],
    checkpointer=InMemorySaver(),
)

# Rubric 是调用状态，不是构造参数——每次 invoke 传入：
result = agent.invoke(
    {"messages": [HumanMessage(content=task)], "rubric": rubric},
    config={"configurable": {"thread_id": "..."}},
)
```

**Rubric 编写三原则**：每条标准 = 可判定（一个可检查行为）+ 可取证（要求调用工具拿证据）+ 可修订（失败带 gap/用例/异常）。

**评审结论与验收门（Fail-Closed）：**

| 值 | 层次 | 是否接收结果 |
|---|---|---|
| `satisfied` | 本轮结论 | ✅ 是——唯一放行条件 |
| `needs_revision` | 本轮结论 | ❌（有预算则修订回炉） |
| `failed` / `grader_error` | 本轮结论 | ❌ |
| `max_iterations_reached` | Middleware 运行终态 | ❌（预算耗尽） |

> 最终消息存在 ≠ 通过验收。应用从 `on_evaluation` 累计记录里取最后一轮：`accepted = last_eval and last_eval["result"] == "satisfied"`，否则拒绝/转人工。事件流 `stream.custom` 有 `rubric_evaluation_start/end` 供 UI 显示进度。Rubric 不能替代沙箱/权限/HITL/离线评测。

## 3. 上下文工程（Context Engineering）

Deep Agents 的核心优势：**自动管理上下文窗口**。

```python
from deepagents.backends import StateBackend
from deepagents.middleware import (
    FilesystemMiddleware,
    SummarizationMiddleware,
    MemoryMiddleware,
    SkillsMiddleware,
)

backend = StateBackend()
model = "claude-sonnet-4-6"

agent = create_deep_agent(
    model=model,
    tools=[search],
    backend=backend,
    middleware=[
        FilesystemMiddleware(backend=backend),
        SummarizationMiddleware(
            model=model,                    # 摘要用同一模型
            backend=backend,
            trigger=("tokens", 100000),      # 超 100K tokens 触发压缩
            keep=("messages", 20),           # 保留最近 20 条消息
        ),
        MemoryMiddleware(backend=backend, sources=["./AGENTS.md"]),
        SkillsMiddleware(backend=backend, sources=["./skills/"]),
    ],
)
```

---

## 4. 文件系统权限（FilesystemPermission）

> `FilesystemPermission` 控制内置文件工具（read_file/write_file/edit_file/delete/ls/glob/grep）**能访问哪些路径**。注意：不覆盖 MCP 工具、不覆盖沙箱 `execute`、不覆盖自定义工具——需分别控制。

### 4.1 基本用法

一条规则三字段：`operations`（`"read"` / `"write"`）、`paths`（Glob 列表，支持 `**` 递归和 `{a,b}` 交替）、`mode`（`"allow"` / `"deny"` / `"interrupt"`）。

```python
from deepagents import create_deep_agent, FilesystemPermission

agent = create_deep_agent(
    model=model,
    permissions=[
        FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
    ],
)
```

**操作组映射**：`read` = `ls` + `read_file` + `glob` + `grep`；`write` = `write_file` + `edit_file` + `delete`。

**三种 mode**：`"allow"` 放行 / `"deny"` 拒绝 / `"interrupt"` 暂停等待审批（需 `deepagents>=0.6.8` + checkpointer + 复用 §5 HITL 恢复协议）。

### 4.2 求值模型：首条匹配生效（first-match-wins）

多条规则**按声明顺序**求值，同时匹配 `operations` + `paths` 的第一条立即生效。无匹配时**默认允许**。

```
稳定规则顺序：① 最具体敏感路径 → ② 业务允许路径 → ③ 最宽泛兜底规则
```

### 4.3 四种常见策略

**策略一：整个文件系统只读**
```python
FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")
```

**策略二：只能访问指定工作区（白名单）**
```python
permissions=[
    FilesystemPermission(operations=["read", "write"], paths=["/workspace/**"], mode="allow"),
    FilesystemPermission(operations=["read", "write"], paths=["/**"], mode="deny"),  # ← 末尾兜底！
]
```

**策略三：共享知识只读，用户记忆可写**（配合 CompositeBackend）
```python
backend = CompositeBackend(
    default=StateBackend(),
    routes={"/memories/": StoreBackend(namespace=user_ns),
            "/policies/": StoreBackend(namespace=org_ns)},
)
permissions=[
    FilesystemPermission(operations=["write"], paths=["/policies/**"], mode="deny"),
]
```

**策略四：拒绝所有文件访问**
```python
FilesystemPermission(operations=["read", "write"], paths=["/**"], mode="deny")
# 工具仍在，但每次调用返回权限错误
```

### 4.4 子 Agent 继承规则

| 场景 | 效果 |
|------|------|
| 子 Agent **不配置** `permissions` | 继承父 Agent 的全部权限规则 |
| 子 Agent **配置了** `permissions` | **整体替换**父规则（非追加/交集），规则必须独立闭合 |

### 4.5 PolicyWrapper / GuardedBackend（扩展模式）

当判断条件超出「操作类型 × 路径」两维度（频率/内容/调用身份/租户状态）时，在 Backend 层扩展：

```python
class GuardedBackend(FilesystemBackend):
    def write(self, file_path: str, content: str) -> WriteResult:
        if file_path.startswith("/policies/"):
            return WriteResult(error=f"写入被拒绝：{file_path}")
        return super().write(file_path, content)
```

两层控制顺序：`内置文件工具 → FilesystemPermission（先检查）→ Policy Hook（再执行）→ 实际存储 Backend`

### 4.6 权限验证清单

上线前至少验证 10 项：允许路径读写 ✅ / 敏感路径读取被拒 ✅ / 敏感路径写/编辑/删除被拒 ✅ / 工作区外兜底 ✅ / 规则顺序交换回归 ✅ / 子 Agent 同路径 ✅ / interrupt 三决策恢复 ✅ / Policy Hook 两分支 ✅ / 每个旁路独立控制 ✅ / 目录删除含受保护后代全拒 ✅

> **安全边界重申**：`FilesystemPermission` 不覆盖 MCP 工具（需 Server ACL + Interceptor）· 不覆盖沙箱 `execute`（需沙箱策略）· 不覆盖自定义工具（需工具内校验或 `interrupt_on`）。

---

## 5. Human-in-the-Loop

> Deep Agents 内置 `HumanInTheLoopMiddleware`，通过 `interrupt_on` 参数配置哪些工具需要人工审批。Checkpointer **必须配置**（中断恢复靠它）。

**基础用法：**

```python
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

@tool
def delete_file(path: str) -> str:
    """删除指定文件。"""
    ...

checkpointer = MemorySaver()

agent = create_deep_agent(
    model=model,
    tools=[delete_file, send_email, read_file],
    interrupt_on={
        "delete_file": True,                                        # 完全中断
        "send_email": {"allowed_decisions": ["approve", "reject"]}, # 只能批/拒
        "read_file": False,                                         # 不中断
    },
    checkpointer=checkpointer,  # 必须！
)
```

**三种配置值：**

| 配置值 | 含义 |
|--------|------|
| `True` | 启用中断，允许所有 4 种决策 |
| `False` | 不中断，Agent 直接执行 |
| `{"allowed_decisions": [...]}` | 启用中断，只允许指定决策类型 |

**四种决策类型：**

| 决策 | 含义 | 适用场景 |
|------|------|---------|
| `approve` | 批准，使用 Agent 原始参数执行 | "确认删除这个文件" |
| `edit` | 修改参数后执行 | "收件人改一下再发" |
| `reject` | 跳过调用，把拒绝原因反馈给 Agent | "不要删除，取消" |
| `respond` | 不执行工具，人的回复作为工具结果 | `ask_user` 等"问用户"的工具 |

> ⚠️ `reject` vs `respond`：拒绝副作用工具（删除/发送/部署）用 `reject`，`respond` 只用于"工具本身就是问人"的场景。

**条件中断（`when` 谓词）：**

> 需要 `langchain>=1.3.3`。

```python
from langchain.agents.middleware import ToolCallRequest

def writes_outside_workspace(request: ToolCallRequest) -> bool:
    """仅写入 /workspace/ 外时中断。"""
    path = request.tool_call["args"].get("file_path", "")
    return not path.startswith("/workspace/")

agent = create_deep_agent(
    model=model,
    interrupt_on={
        "write_file": {
            "allowed_decisions": ["approve", "edit", "reject"],
            "when": writes_outside_workspace,  # ← 条件判断
        },
    },
    checkpointer=checkpointer,
)
```

**中断与恢复完整流程：**

```python
# 1. 正常调用 — Agent 遇到中断工具时暂停
config = {"configurable": {"thread_id": "session-001"}}
result = agent.invoke(
    {"messages": [{"role": "user", "content": "删除 /tmp/old.txt"}]},
    config=config,
    version="v2",  # HITL 必须用 v2
)

# 2. 检查是否有待审批项
if "__interrupt__" in result:
    for action in result["__interrupt__"]:
        print(f"Agent 想调用 {action['name']}({action['arguments']})")

    # 3. 人类做决策
    decisions = [
        {"type": "approve"},           # 批准第 1 个
        {"type": "edit", "args": {...}}, # 修改第 2 个
        {"type": "reject", "message": "原因..."},  # 拒绝第 3 个
    ]

    # 4. 恢复执行
    result = agent.invoke(
        None,  # 不追加新消息
        Command(resume={"decisions": decisions}),
        config=config,
        version="v2",
    )
```

**关键要求：**
- ✅ 必须配置 Checkpointer
- ✅ 必须相同 `thread_id`
- ✅ 必须 `version="v2"`
- ✅ `decisions` 数量和顺序与 `action_requests` 一一对应

**批量工具调用：** 一次模型调用可能触发多个工具（4 个 `write_file`），`interrupt_on` 匹配的第一个触发中断，已通过的非中断工具仍会执行。

**子 Agent 独立 HITL：**

```python
agent = create_deep_agent(
    model=model,
    tools=[delete_file, read_file],
    interrupt_on={"delete_file": True, "read_file": False},
    subagents=[{
        "name": "file-manager",
        "description": "管理文件操作",
        "system_prompt": "你是文件管理助手。",
        "tools": [delete_file, read_file],
        "interrupt_on": {
            "delete_file": True,
            "read_file": True,  # 子 Agent 读文件也要审批！
        }
    }],
    checkpointer=checkpointer,
)
```

**按风险等级分层：**

| 级别 | 工具示例 | 策略 |
|------|---------|------|
| 🟢 低风险 | `read_file`, `grep`, `search` | `False` — 不中断 |
| 🟡 中风险 | `write_file`, `edit_file` | 条件中断（`when` 谓词） |
| 🔴 高风险 | `delete_file`, `send_email`, `execute_shell` | `True` — 始终中断 |
| ⚫ 财务/合规 | `transfer_funds`, `deploy` | `{"allowed_decisions": ["approve", "reject"]}` — 不允许 edit |

---

## 6. 异步子 Agent（deepagents>=0.5.0 preview）

> ⚠️ Preview 特性，API 可能变化。同步子 Agent 阻塞主 Agent；异步子 Agent 立即返回任务 ID，主 Agent 全程不阻塞。

**同步 vs 异步：**

| 维度 | 同步 | 异步 |
|------|------|------|
| 执行模型 | 阻塞等完成 | 立即返回 task ID |
| 并发性 | 可并行，但主 Agent 被整批阻塞 | 完全并行，主 Agent 自由 |
| 中途追加指令 | ❌ | ✅ `update_async_task` |
| 取消 | ❌ | ✅ `cancel_async_task` |
| 状态性 | 每次调用独立 | 子 Agent 拥有自己的 thread，历史累积 |
| 典型场景 | 秒级快速委派 | 分钟级以上长程任务 |

**判定方法**：子任务 <5 秒 → 同步；子任务可能跑数分钟且过程需交互 → 异步。

**声明：**

```python
from deepagents import AsyncSubAgent, create_deep_agent

async_subagents = [
    AsyncSubAgent(
        name="researcher",                     # 唯一标识
        description="深度调研，多次搜索+综合分析",  # 路由依据
        graph_id="researcher",                 # Agent Protocol 上的 graph ID
        # url="https://...langsmith.dev",      # 可选：远程 HTTP，不填走 ASGI 进程内
        # headers={...},                       # 可选：自托管鉴权
    ),
]
agent = create_deep_agent(model=model, subagents=async_subagents)
```

**5 把遥控器**（`AsyncSubAgentMiddleware` 自动注入）：

| 工具 | 作用 | 返回 |
|------|------|------|
| `start_async_task` | 启动后台任务 | task ID（立即返回） |
| `check_async_task` | 查询状态与结果 | status + result（若完成） |
| `update_async_task` | 运行中追加新指令 | 确认 + 更新后状态 |
| `cancel_async_task` | 终止运行中任务 | 取消确认 |
| `list_async_tasks` | 列出所有任务及状态 | 任务总览 |

**完整生命周期：**

```
用户：深入调研 LangGraph 多 Agent 架构
主 Agent → start_async_task("researcher", "调研...") → task_id: abc-123
主 Agent ← 「已派 researcher 后台开干，你可以继续问别的」

用户：先帮我把这段代码格式化一下
主 Agent ← （直接处理，researcher 仍在后台跑）

用户：那个调研有进展吗？
主 Agent → check_async_task("abc-123") ← status: running
主 Agent ← 「还在跑，已搜了 4 个关键词，预计还要几分钟」

用户：补一下：重点关注 supervisor/network/hierarchical 三种拓扑
主 Agent → update_async_task("abc-123", "重点关注三种拓扑...") ← 已注入

用户：算了，先停一下
主 Agent → cancel_async_task("abc-123") ← cancelled
```

**设计要点：** 任务元数据存在独立的 `async_tasks` channel 中，与消息历史解耦——即使对话被压缩，主 Agent 永远能通过 `list_async_tasks` 找回所有任务。

**传输模式：**

| 模式 | 默认 | 适用 |
|------|:--:|------|
| ASGI（进程内） | ✅ | 同部署、零延迟、起手式 |
| HTTP（远程） | 传 `url` 后 | 子 Agent 需独立扩缩容/独立团队维护 |

**3 种部署拓扑：** 单部署（全 ASGI，默认）→ 拆分部署（全 HTTP）→ 混合（部分 ASGI + 部分 HTTP）

**最佳实践：**
1. 本地开发 `langgraph dev --n-jobs-per-worker 10`（每子 Agent 占 1 slot）
2. `description` 要行为导向，主 Agent 靠它路由
3. 用 thread ID 串联主 Agent trace ↔ 子 Agent trace（LangSmith 追踪）
4. system_prompt 中加：`"派出异步子Agent后必须立刻交还控制权给用户，不要主动 check"`

**排障 4 问：**
- 刚启动就立刻轮询 → system_prompt 强化"不要主动 check"
- 报告过时状态 → 先 `check_async_task` 再回答
- 任务 ID 被截断 → 换更听话的模型或 system_prompt 强调完整 ID
- 启动后长时间无返回 → worker pool 满了，调大 `--n-jobs-per-worker`

---

## 7. 生产部署

```python
# 1. 用 FilesystemBackend 替代 StateBackend
from deepagents.backends import FilesystemBackend
backend = FilesystemBackend(root_dir="./agent_workspace")

# 2. 用 PostgresSaver + PostgresStore 持久化
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore

# 3. 部署到 LangSmith
# LangSmith 自动配置 checkpointer + store

# 4. 配置 profiles（模型能力精细化控制）
from deepagents.profiles import CodeAgentProfile
agent = create_deep_agent(
    model="claude-sonnet-4-6",
    profile=CodeAgentProfile(),  # 预设代码场景最佳参数
)
```

---

## 8. create_deep_agent() vs create_agent() 速查

> 完整选型决策见文首 [⚠️ 选型边界](#-选型边界什么时候不该用-deep-agents)。

| 场景 | create_agent() | create_deep_agent() |
|------|:--:|:--:|
| 简单 tool-calling | ✅ | ❌ 过重 |
| 需要写文件/跨轮次状态 | ❌ | ✅ |
| 需要自动上下文压缩 | ❌ | ✅ |
| 需要子 agent 并行/异步 | ❌ | ✅ |
| 需要代码执行沙箱 | ❌ | ✅ |
| 需要权限控制 | ❌ | ✅ |
| 需要最小依赖 | ✅ | ❌ |

---

## 9. 执行协议

1. **简单任务用 `create_agent()`** — 不要上来就 deepagents
2. **需要上下文管理 → `create_deep_agent()`** — 自动压缩 + 文件系统
3. **需要子 agent 并行 → 加 `SubAgentMiddleware`** — 每个子 agent 独立上下文
4. **生产环境用 FilesystemBackend** — StateBackend 不持久化
5. **微调中间件 → `create_agent()` + 手选 middleware`** — 精确控制堆栈
6. **Backend 选型 →** `references/backends-guide.md`
7. **子 Agent 详解 →** `references/subagents-guide.md`
8. **Skills 详解 →** `references/skills-guide.md`
9. **MCP 集成 →** `references/mcp-integration.md`（在 langchain-v1 skill 中；langchain>=1.4 用 `MCPAdapter`）
10. **沙箱选型 →** 本节 §2.7
11. **代码编排（Interpreter/PTC/动态子Agent）→** 本节 §2.2 / §2.8
12. **运行时验收 →** 本节 §2.9 RubricMiddleware；**实时展示 →** 本节 §12
13. **v0.6→v0.7 迁移 →** 文首「版本基线」清单 + `rg` 扫描

---

## 10. MCP 集成（Model Context Protocol）

> **两条接入路径，按版本选**：
> - **`langchain>=1.4.0`（新）→ 内置 `langchain.mcp.MCPAdapter`**（基于 FastMCP；Beta，导入触发 `LangChainBetaWarning`）。安装 `uv add "langchain[mcp]"`。MCP 工具是异步工具（`await`）。
> - **`langchain<1.4` 或存量代码 → `langchain-mcp-adapters` 的 `MultiServerMCPClient`**（10.1–10.5 全部适用）。官方已提供 [迁移指南](https://docs.langchain.com/oss/migrate/langchain-mcp-adapters)。

```python
# langchain>=1.4：MCPAdapter — target 自动推断传输（http(s) URL / Path→stdio / 进程内 FastMCP / MCPConfig 多 server / fastmcp.Client）
from langchain.agents import create_agent
from langchain.mcp import MCPAdapter

async def main():
    async with MCPAdapter("https://example.com/mcp") as adapter:   # str 必须是 http(s) URL
        tools = await adapter.list_tools()
        agent = create_deep_agent(model=model, tools=tools)         # create_agent / create_deep_agent 均可
        return await agent.ainvoke({"messages": [...]})

# 多 server：MCPAdapter({"mcpServers": {"a": {...}, "b": {...}}})
# 进程内：MCPAdapter(fastmcp_instance)；脚本：MCPAdapter(Path("server.py"))
```

> 以下 10.1–10.5 以 `langchain-mcp-adapters` 为准（<1.4 / 存量路径），接入思路（Server ACL → Interceptor → HITL → 子 Agent 收缩 → 边界认知）与 v1.4 一致。

### 10.1 快速上手

```bash
pip install "langchain-mcp-adapters>=0.3,<0.4" "mcp>=1.28,<2"
```

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from deepagents import create_deep_agent

# ① 连接 MCP Server
client = MultiServerMCPClient(
    {"course_math": {"transport": "stdio", "command": "python", "args": ["math_server.py"]}},
    tool_name_prefix=True,  # 强烈建议！→ 工具名变为 course_math_add
)
tools = await client.get_tools()

# ② 交给 Agent
agent = create_deep_agent(model=model, tools=tools)
result = await agent.ainvoke({"messages": [{"role": "user", "content": "37 + 58 = ?"}]})
```

> ⚠️ MCP 工具只支持异步——全程用 `await client.get_tools()`、`await tool.ainvoke()`、`await agent.ainvoke()`。同步 `invoke()` 会抛 `NotImplementedError`。

### 10.2 多种传输方式

| 传输 | 配置 | 适用 |
|------|------|------|
| **stdio**（本地） | `{"transport": "stdio", "command": "...", "args": [...]}` | 本地脚本/CLI 工具 |
| **HTTP**（远程） | `{"transport": "http", "url": "https://...", "headers": {...}}` | 远程服务/团队共享 |
| **WebSocket** | 已实装但不推荐主路径 | — |

### 10.3 Session 管理

```python
# 无状态模式（默认）：每次工具调用 = 新 Session → 执行 → 销毁
tools = await client.get_tools()

# 持久 Session：复用连接，适合有状态 Server
async with client.session("course_math") as session:
    tools = await load_mcp_tools(session, ...)  # 需显式传 callbacks/interceptors/前缀
    agent = create_deep_agent(model=model, tools=tools)
    result = await agent.ainvoke(...)  # 所有调用必须在 async with 内
```

**MCP Session vs LangGraph Checkpoint**：

| 维度 | MCP Session | LangGraph Checkpoint |
|------|------------|---------------------|
| **作用域** | 传输层连接（子进程/网络） | 图执行状态（消息历史/工具结果） |
| **生命周期** | Session 打开→关闭 | thread_id 内持久化 |
| **恢复语义** | 不恢复——关闭后连接丢失 | 可恢复——从 Checkpointer 重建 state |
| **负责持久化** | ❌ 不负责（Server 自行管理） | ✅ Checkpointer（MemorySaver/PostgresSaver） |

> **关键**：HITL 中断恢复、进程重启后，MCP Session 不会自动恢复——仅依赖 Agent State 不依赖连接状态。

### 10.4 安全组合模式

```
MCP 工具安全分层：
  ① Server 侧校验（ACL/参数/租户）  ← 必须，MCP 是独立进程
  ② Client Interceptor（≠ Agent Middleware） ← 可做前置过滤
  ③ HITL（interrupt_on 用带前缀最终名）  ← 副作用工具审批
  ④ 子 Agent 工具收缩（显式 tools=）  ← 最小权限
  ⑤ FilesystemPermission 不覆盖 MCP Tool  ← 认识边界
```

### 10.5 排错清单

| 症状 | 原因 | 解决 |
|------|------|------|
| 同步 `invoke()` 报错 | MCP 工具是异步的 | 改 `ainvoke()` |
| 找不到 server 文件 | 相对路径 | `Path(__file__).with_name("...").resolve()` 绝对路径 |
| 协议解析失败 | stdout 混入调试日志 | 日志写 stderr，不用 `print()` |
| HITL 没拦截 | 用了原始 MCP 工具名 | `interrupt_on` 用带前缀的最终名（如 `billing_charge_card`） |
| 文件权限没拦 MCP | 预期行为 | MCP Server 侧独立控制 |
| 状态丢失 | 无状态模式默认临时 Session | 用 `client.session()` 或 Server 端持久化 |

---

## 11. 实战案例速查

> 完整案例源码见 `docs/community/cases/`。deepagents 最擅长**需要文件系统 + 代码执行 + 多步子任务**的复杂场景。

### 11.1 全自动数据分析 Agent

```
场景：上传 CSV/Excel → 自动清洗 → 探索分析 → 生成可视化报告
技术栈：create_deep_agent + FilesystemMiddleware + 代码解释器 + DeepSeek-OCR
```

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model="deepseek:deepseek-chat",
    backend=FilesystemBackend(root_dir="workspace"),
    system_prompt="""You are a data analyst. 
    When the user uploads data, clean it, explore it, and generate a report.
    Use write_file to save plots and analysis results.""",
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "分析 sales.csv 的月度趋势并生成可视化"}]
})
# Agent 自动：读文件 → 清洗 → 统计 → 画图 → write_file 保存 → 输出报告
```

### 11.2 文档审核 Agent

```
场景：上传 PDF 合同 → 结构化提取条款 → 逐条合规检查 → 输出审核报告
技术栈：create_deep_agent + OCR 解析 + RAG 知识库 + HumanInTheLoopMiddleware
```

```python
from deepagents import create_deep_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware

agent = create_deep_agent(
    model="deepseek:deepseek-chat",
    tools=[ocr_parse, search_regulations],
    middleware=[
        HumanInTheLoopMiddleware(interrupt_on={"final_approval": True}),
    ],
    system_prompt="""You audit documents for compliance.
    1. Parse the document with ocr_parse
    2. Extract key clauses
    3. Check each clause against regulations using search_regulations
    4. Write findings with write_file
    5. Call final_approval for human review before submitting""",
)
```

### 11.3 案例场景对照

| 你要做… | 用 | 参考案例 |
|---------|-----|---------|
| 自动数据分析/EDA/可视化 | `create_deep_agent` + 文件系统 + 代码执行 | [数据分析Agent](docs/community/cases/全自动数据分析可视化Agent系统.md) |
| 多模态 PDF/合同审核 | `create_deep_agent` + OCR + RAG + HITL | [文档审核Agent](docs/community/cases/LangChain%20v1.0%20文档审核类Agent开发实战.md) |
| 全栈 Agent + MCP | `create_agent` + `MultiServerMCPClient` + FastAPI | [mini ChatGPT](docs/community/cases/Ep.01%20从零搭建mini%20ChatGPT（上）.md) |
| OCR 多模态解析 | `create_agent` + MinerU/DeepSeek-OCR + vLLM | [OCR PDF](docs/community/cases/LangChain1.0%20+%20OCR%20多模态PDF解析实战.md) |

---

## 12. 实时事件流（Streaming）

> 新应用用 **`stream_events(..., version="v3")`**（Typed Projections，产品视角）；`stream(..., version="v2")` 是 LangGraph 底层协议（`type/ns/data`），留给调试/迁移。两条流不要混用。

**v3 顶层 projections（coordinator 层）**：`stream.messages` / `stream.tool_calls` / `stream.values`（state 快照，非增量） / `stream.subagents`（委派） / `stream.output`（最终输出）。

**subagent handle 字段**：`name`（= `subagent_type`，仅显示）· `path`（tuple namespace 路径，**UI 卡片唯一键**，区分同名子 Agent）· `status`（started/completed/failed/interrupted）· 按需惰性打开的 `messages` / `tool_calls` / `values` / `subagents` / `output`（失败读取 output 会抛异常 → 渲染为错误）。

```python
# 实时 UI 顺序不失真：异步并发消费 或 同步 interleave
stream = agent.stream_events(request, version="v3")
for name, item in stream.interleave("messages", "subagents"):   # 同步 CLI 用
    ...
# 异步服务：asyncio.gather 同时消费 stream.messages 与 stream.subagents
```

**tool-call handle**：`tool_name` / `input`（可能含敏感数据，脱敏后再记） / `output_deltas`（增量，按序追加） / `completed` / `output` / `error`。状态三分支：`not completed`→running；`error`→failed；否则 completed。

**raw protocol（需审计/重放时）**：`event["seq"]`（严格递增，排序用 seq 不用 timestamp）、`event["method"]`、`params["namespace"]`（`list[str]`，空=根层；子 Agent 事件以 `subagent.path` 为前缀，段格式 `<node>:<id>`）、`params["data"]`（按 method 解析，如 messages 的 content-block-delta → delta.text-delta）。

**自定义进度事件**：工具内 `from langgraph.config import get_stream_writer` → `writer({"status": ..., "progress": ...})`，v2 从 `custom` 分支读，schema 由应用自定并加版本号。

> path/namespace/ns 三处同源：v3 `subagent.path`(tuple) / v3 raw `params.namespace`(list) / v2 `chunk["ns"]`(tuple)。Streaming 不负责持久化/取消/背压——长任务要自己处理超时、断开、重放（写 Trace/DB）。
