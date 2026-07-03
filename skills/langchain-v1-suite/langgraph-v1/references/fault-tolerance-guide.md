# LangGraph 容错与弹性模式

> **来源**: 官方 `langgraph-fault-tolerance.md` (1234行)
> **定位**: 重试、超时、错误处理、优雅关闭的完整 API 参考。快速示例见 `SKILL.md` §8。

---

## 1. RetryPolicy（重试策略）

### 完整参数

```python
from langgraph.types import RetryPolicy

RetryPolicy(
    max_attempts: int = 3,               # 最大尝试次数（含首次）
    backoff_factor: float = 2.0,          # 指数退避倍数
    initial_interval: float = 1.0,        # 首次重试等待（秒）
    max_interval: float = 60.0,           # 重试间隔上限（秒）
    retry_on: tuple[type[Exception]] = (Exception,),  # 触发重试的异常类型
    jitter: bool = False,                 # 是否加随机抖动（避免惊群）
)
```

### 使用方式

```python
# 方式1: 节点级（优先级最高）
builder.add_node(
    "api_call", api_node,
    retry=RetryPolicy(
        max_attempts=3,
        retry_on=(ConnectionError, TimeoutError),
    ),
)

# 注意: compile() 当前版本不接受 retry= 参数
# RetryPolicy 仅在节点级 add_node(retry=...) 设置

# 方式3: 条件重试（节点内动态决定）
from langgraph.types import get_retry_state

def api_node(state):
    retry_state = get_retry_state()
    if retry_state and retry_state.attempt >= 2:
        return Command(goto="fallback")  # 不再重试，直接降级
    result = call_api()
    return {"data": result}
```

### 优先级

```
节点级 retry > 图级 retry > 默认（不重试）
```

---

## 2. 超时控制

### 两种超时

| 超时类型 | 参数 | 触发条件 |
|---------|------|---------|
| `timeout` | 秒 | 节点总执行时间超限 |
| `idle_timeout` | 秒 | 节点无任何 stream 输出超限 |

```python
builder.add_node(
    "slow_task", slow_node,
    timeout=30.0,       # 最多跑 30 秒
    idle_timeout=10.0,  # 10 秒没输出 → 超时
)
```

### NodeTimeoutError 处理

```python
def slow_node(state):
    try:
        result = long_running_task(state["input"])
        return {"result": result}
    except NodeTimeoutError:
        # 超时不是致命错误 → 返回部分结果
        return {"result": "timeout", "partial": True}
```

### Heartbeat 模式（防止误超时）

```python
# LangGraph 自动在节点执行期间发送心跳
# 如果心跳也停了 → idle_timeout 触发

# 手动发信号（长时间无输出的阻塞调用前）
from langgraph.types import heartbeat

def batch_processing_node(state):
    for i, item in enumerate(state["items"]):
        if i % 100 == 0:
            heartbeat()  # 告诉 runtime "我还活着"
        process(item)
    return {"done": True}
```

---

## 3. 错误处理模式

### 节点内捕获 + Command 路由（推荐）

```python
def resilient_node(state) -> Command:
    try:
        data = call_external_api(state["query"])
        return Command(update={"api_result": data}, goto="success_handler")
    except TimeoutError:
        return Command(update={"error": "timeout"}, goto="retry_later")
    except AuthError:
        return Command(update={"error": "auth"}, goto="reauth")
    except Exception:
        return Command(update={"error": "unknown"}, goto="fallback")
```

> **社区验证**: 节点内 try/except + Command 路由 比 RetryPolicy + 默认 crash 更可靠。原因：能根据异常类型走不同恢复路径。

### 图级默认错误处理

```python
def default_error_handler(state, error):
    """所有节点未捕获异常的统一处理"""
    return {"errors": state.get("errors", []) + [str(error)]}

graph = builder.compile(
    checkpointer=checkpointer,
    default_error_handler=default_error_handler,
)
```

### Subgraph 错误传播

```python
# 子图内异常默认传播到父图
# 父图可以通过 try/except 捕获

def parent_node(state):
    try:
        sub_result = subgraph.invoke({"input": state["data"]})
        return {"sub_result": sub_result}
    except Exception:
        return {"sub_result": None, "sub_failed": True}
```

---

## 4. 优雅关闭

### SIGTERM 处理

```python
import signal

graph = builder.compile(checkpointer=checkpointer)

def handle_sigterm(signum, frame):
    """收到关闭信号 → 保存 checkpoint 后退出"""
    print("收到 SIGTERM，保存状态后退出...")
    # 图会自动保存当前 checkpoint
    # 下次用同一 thread_id 调 invoke — 从断点恢复
    raise SystemExit(0)

signal.signal(signal.SIGTERM, handle_sigterm)

# 恢复运行
# graph.invoke(None, config) → 从上次保存的 checkpoint 继续
```

---

## 5. 重试/超时/错误的适用矩阵

| 场景 | RetryPolicy | timeout | try/except + Command |
|------|:--:|:--:|:--:|
| 瞬时网络错误 | ✅ | — | — |
| API 速率限制 | ✅ (backoff) | — | — |
| 长时间阻塞 | — | ✅ | — |
| 无响应的节点 | — | ✅ idle | ✅ (fallback) |
| 多错误类型分流 | — | — | ✅ (最佳) |
| 资源清理 | — | — | ✅ (finally) |

---

## 6. Functional API 容错

```python
from langgraph.func import entrypoint, task
from langgraph.types import RetryPolicy

@task(retry=RetryPolicy(max_attempts=3))
def flaky_api_call(query: str) -> str:
    return requests.get(f"https://api.example.com/search?q={query}").text

@entrypoint(checkpointer=InMemorySaver())
def robust_workflow(query: str) -> str:
    try:
        result = flaky_api_call(query).result()
        return result
    except Exception:
        return "API 暂时不可用"
```

---

## 7. `[社区]` 社区实践

### 渐进式重试退避（生产推荐）

```python
# 社区验证的生产级重试配置
RetryPolicy(
    max_attempts=5,
    initial_interval=1.0,    # 1s → 2s → 4s → 8s → 16s
    backoff_factor=2.0,
    max_interval=30.0,        # 上限 30 秒
    jitter=True,              # 加抖动，避免惊群
    retry_on=(
        ConnectionError,
        TimeoutError,
        httpx.HTTPStatusError,  # HTTP 5xx
    ),
)
```

### 国内网络适配

```python
# 国内 API 服务超时配置建议
builder.add_node(
    "call_siliconflow", sf_node,
    timeout=60.0,           # 国内服务偶发延迟高
    idle_timeout=30.0,
    retry=RetryPolicy(
        max_attempts=3,
        initial_interval=2.0,  # 先等 2 秒再重试
        backoff_factor=1.5,    # 平缓退避
    ),
)
```

---

> **返回**: [`SKILL.md`](../SKILL.md) §8 容错与超时
