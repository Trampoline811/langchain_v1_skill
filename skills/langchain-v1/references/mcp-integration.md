# MCP 工具集成详解

> 从 SKILL.md 分离出来的 MCP 深度内容。

## MCP 解决什么问题

MCP 不是"另一种写工具的方式"——它解决的是**工具接口的标准化和跨组织复用**。

**问题：** Agent 需要调 GitHub API、Slack API、Jira API、数据库。以前每个服务写 wrapper（鉴权、错误处理、分页、重试），每个不同。

**MCP 方案：** 这些服务的官方/社区提供标准化 MCP Server。Agent 只需知道"连哪个 server"，工具自动发现。

```
以前                             MCP 方案
Agent                            Agent
├─ github_tool (手写300行)       └─ MultiServerMCPClient
├─ slack_tool (手写200行)            ├─ github MCP server
├─ jira_tool (手写250行)             ├─ slack MCP server
└─ db_tool (手写150行)               └─ jira MCP server
你维护所有工具代码                你只维护连接配置
```

## 基本用法

```bash
pip install langchain-mcp-adapters
```

```python
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

async def main():
    client = MultiServerMCPClient({
        "math": {
            "transport": "stdio",
            "command": "python",
            "args": ["/path/to/math_server.py"],
        },
        "weather": {
            "transport": "http",
            "url": "http://localhost:8000/mcp",
            "headers": {"Authorization": "Bearer TOKEN"},
        },
    })
    tools = await client.get_tools()
    agent = create_agent("openai:gpt-5.4", tools)
    result = await agent.ainvoke({"messages": "what is the weather?"})
```

## 三种传输方式

| Transport | 适用 | 说明 |
|-----------|------|------|
| `stdio` | 本地工具 | 启动子进程通信，进程生命期内有状态 |
| `http` / `streamable_http` | 远程 HTTP | 推荐 |
| `sse` | ⚠️ MCP spec 已废弃 | 不推荐新项目 |

## MCP 三大原语

| 原语 | 用途 | LangChain 转换 |
|------|------|---------------|
| **Tools** | 可执行函数 | → LangChain Tool，喂给 create_agent() |
| **Resources** | 暴露数据（文件、数据库） | → Blob 对象 |
| **Prompts** | 预定义提示词模板 | ⚠️ v1 尚未完全集成 |

## 有状态 vs 无状态

默认无状态：每次 tool 调用 → 新 session → 执行 → 销毁。适用于独立 API 调用。

有状态（显式 session，适用于数据库连接池等）：

```python
from langchain_mcp_adapters.tools import load_mcp_tools

async with client.session("server_name") as session:
    tools = await load_mcp_tools(session)
    agent = create_agent("openai:gpt-5.4", tools)
```

## Interceptor（MCP 层的中间件）

MCP server 是独立进程，无法访问 LangGraph state/store/context。Interceptor 桥接：

```python
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from langchain.messages import ToolMessage

async def auth_interceptor(request: MCPToolCallRequest, handler):
    """在 MCP 工具调用前后注入 LangGraph 上下文"""
    runtime = request.runtime  # ← LangGraph runtime
    
    # 前置拦截：鉴权
    if request.name in ("delete_file", "export_data"):
        if not runtime.state.get("authenticated"):
            return ToolMessage(
                content="Authentication required.",
                tool_call_id=runtime.tool_call_id,
            )
    
    # 修改参数
    modified = request.override(
        args={**request.args, "user_id": runtime.context.user_id}
    )
    return await handler(modified)

client = MultiServerMCPClient({...}, tool_interceptors=[auth_interceptor])
```

## 能力边界

**✅ 擅长：** 连接已有标准化 MCP server、混合 MCP + @tool、多模态响应、跨语言 server

**❌ 不擅长：** 简单一次性工具（写 @tool 更快）、需要直接读写 LangGraph state 的逻辑（用 Interceptor 弥补）、动态服务发现（配置固定在初始化时）、高频低延迟（IPC/HTTP 有通信开销）

## 选择指南

| 场景 | 方案 |
|------|------|
| 自定义业务逻辑 | `@tool` |
| 外部服务有 MCP server | `MultiServerMCPClient` |
| MCP server 需要注入应用状态 | MCP + Interceptor |
| Agent 层面统一控制行为 | Middleware（作用于所有工具） |
| MCP 层单独控制某个 server | Interceptor（只作用于 MCP 工具） |
