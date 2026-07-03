# 国产模型集成指南

> **来源**: AgentSeek `model-integration.md` + `cn-models/README.md`（ob-labs/agentseek），社区实战验证
> **定位**: 国产模型（DeepSeek/Qwen/GLM/Moonshot 等）OpenAI 兼容接口的集成方案、踩坑、修复。
> **文中标记**: `[社区]` = AgentSeek 社区踩坑经验

---

## 1. 直接用 ChatOpenAI 的三个坑 `[社区]`

以 Qwen 为例，最简单的接入方式：

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="qwen-max",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
)
```

**快速验证可以，但上生产有三个坑：**

| 问题 | 原因 | 影响 |
|------|------|------|
| `reasoning_content`（思考过程）被静默丢弃 | `_create_chat_result` / `_convert_chunk_to_generation_chunk` 不认识该字段 | 流式和非流式都不会输出思考过程 |
| 多轮推理链断裂 | `_get_request_payload` 不处理 `additional_kwargs["reasoning_content"]`，AIMessage 中的思考内容无法回传给模型 | 下一轮丢失上一轮的推理上下文 |
| 空 `tools: []` 触发 provider 报错 | 部分国产 provider 严格校验空数组，`ChatOpenAI` 即便没绑工具也发空 `tools` | 请求直接被拒绝 |

**结论**：`ChatOpenAI` 直连仅适合**快速验证**和**不需要推理链的简单对话**。

---

## 2. 两种解决方案

### 方案 A：代码生成 — 自定义集成类（推荐）

通过 AI Coding 生成继承 `BaseChatOpenAI` 的集成类，一键修复所有关键方法：

```python
# 生成的 Qwen 集成类（示例）
from models.qwen import ChatQwen

llm = ChatQwen(model="qwen-max")
# reasoning_content 自动保留、空 tools 自动去除、JSONDecodeError 友好提示
```

生成的集成类覆盖：

| 修复点 | 方法 |
|--------|------|
| `reasoning_content` 保留 | `_create_chat_result` / `_convert_chunk_to_generation_chunk` |
| 多轮推理链 | `_get_request_payload` 处理推理内容回传 |
| 空 `tools: []` 报错 | 未绑工具时从 payload 中移除 `tools` 字段 |
| 弱模型 `with_structured_output` 不稳定 | 升级为 `json_schema` / `json_mode` / `structured_output` 工具三级降级 |
| 流式响应非 JSON | friendly error message 替代原始 `JSONDecodeError` |
| token 统计缺失 | 解析 X-GT 等 response header |

**生成集成类的 3 个参数**（确认后即可生成）：
1. **Model Name** — 小写，如 `qwen`、`glm`、`deepseek`、`moonshot`
2. **API Base URL** — OpenAI 兼容端点
3. **API Key 环境变量名** — 如 `QWEN_API_KEY`

### 方案 B：第三方库 — 直接安装

```bash
pip install langchain-dev-utils
```

提供多个国产模型的预构建适配（`ChatQwen`、`ChatGLM`、`ChatDeepSeek` 等），开箱即用但更新依赖社区节奏。

---

## 3. 主流国产模型速查

| 模型 | 关键能力 | 推荐场景 |
|------|---------|---------|
| **DeepSeek** | 长推理链、强代码能力、低成本 | 代码审查、复杂推理、RAG |
| **Qwen** | 推理+工具调用均衡、中英双语 | 通用 Agent、企业应用 |
| **GLM** | DeepAgents 评测最高分（89%） | 深度 Agent、多步规划 |
| **Moonshot** | 超长上下文（128K+） | 文档分析、长文处理 |

### 接入语法

```python
# 方式1: init_chat_model — 直接传（仅限于 provider 原生支持的模型）
from langchain.chat_models import init_chat_model
model = init_chat_model("deepseek:deepseek-chat")

# 方式2: ChatOpenAI + 自定义集成类 — 国产模型推荐
from models.deepseek import ChatDeepSeek
model = ChatDeepSeek(model="deepseek-chat")

# 方式3: init_chat_model + base_url — 任意 OpenAI 兼容端点
model = init_chat_model(
    "openai:qwen-max",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
)
```

---

## 4. 推理模型接入注意事项 `[社区]`

### 4.1 reasoning_content 保留

确保自定义集成类正确处理 `reasoning_content`：

```python
# AIMessage 中保留推理内容
msg = AIMessage(
    content="回答正文",
    additional_kwargs={"reasoning_content": "思考过程..."},
)
# ❌ 默认 ChatOpenAI 不会把 reasoning_content 传回下一轮
# ✅ 自定义集成类在 _get_request_payload 中处理
```

### 4.2 推理模型 vs 对话模型

| 维度 | 推理模型（deepseek-reasoner） | 对话模型（deepseek-chat） |
|------|------|------|
| 思考过程 | 有 `reasoning_content` | 无 |
| 响应时间 | 慢（>10s） | 快（<3s） |
| 适用场景 | 复杂推理、代码审查、数学 | 日常对话、简单问答 |
| 成本 | 高 | 低 |

**最佳实践**：用 `@wrap_model_call` 做动态路由：

```python
@wrap_model_call
def route_model(request, handler):
    """复杂问题用推理模型，简单问题用对话模型"""
    msg_count = len(request.state.get("messages", []))
    if msg_count > 10 or "review" in str(request.state).lower():
        request.model = init_chat_model("deepseek:deepseek-reasoner")
    else:
        request.model = init_chat_model("deepseek:deepseek-chat")
    return handler(request)
```

---

## 5. 生产环境配置推荐 `[社区]`

```python
import os
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

# ✅ 生产推荐：国产模型 + 自定义集成类
model = init_chat_model(
    "openai:deepseek-reasoner",
    base_url="https://api.deepseek.com/v1",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0.6,
    max_tokens=16384,
)

agent = create_agent(
    model=model,
    tools=[...],
    system_prompt="你是一个中文技术助手。",
    checkpointer=InMemorySaver(),
)
```

### 生产 Checklist

- [ ] 使用自定义集成类而不是裸 `ChatOpenAI`
- [ ] API key 通过环境变量管理，不硬编码
- [ ] 配置合理的 `max_tokens`（国产模型默认通常太小）
- [ ] 推理模型和对话模型分场景路由
- [ ] 验证 `reasoning_content` 是否在多轮对话中正确保留
- [ ] 国内 API 服务偶发延迟高，建议配置 `timeout=60.0`

---

> **返回**: [`SKILL.md`](../SKILL.md) §3 模型初始化 | §5 中间件 | `references/api-reference.md`
