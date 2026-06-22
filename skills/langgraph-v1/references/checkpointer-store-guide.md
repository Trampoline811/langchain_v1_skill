# LangGraph 持久化完整指南：Checkpointer + Store

> **来源**: 官方 `langgraph-checkpointers.md` (1128行) + `langgraph-stores.md` (631行) + `langgraph-persistence.md`
> **定位**: 所有持久化后端的完整对比、配置、进阶用法。快速开始见 `SKILL.md` §4。

---

## 一、Checkpointer（短期记忆 — 单线程状态）

### 可用后端

| 后端 | 导入路径 | 持久化 | 适用 |
|------|---------|:--:|------|
| `InMemorySaver` | `langgraph.checkpoint.memory` | ❌ 进程内 | 开发/测试 |
| `SqliteSaver` | `langgraph.checkpoint.sqlite` | ✅ 本地文件 | 本地开发/小项目 |
| `AsyncSqliteSaver` | `langgraph.checkpoint.sqlite` | ✅ 本地文件 | 异步 + SQLite |
| `PostgresSaver` | `langgraph.checkpoint.postgres` | ✅ PostgreSQL | 生产环境 |
| `AsyncPostgresSaver` | `langgraph.checkpoint.postgres` | ✅ PostgreSQL | 异步 + 生产 |
| `RedisSaver` | `langgraph.checkpoint.redis` | ✅ Redis | 高吞吐/缓存式 |

### 基础用法

```python
# 开发
from langgraph.checkpoint.memory import InMemorySaver
graph = builder.compile(checkpointer=InMemorySaver())

# 本地持久化
from langgraph.checkpoint.sqlite import SqliteSaver
graph = builder.compile(
    checkpointer=SqliteSaver.from_conn_string("checkpoints.db")
)

# 生产（PostgreSQL）
from langgraph.checkpoint.postgres import PostgresSaver
graph = builder.compile(
    checkpointer=PostgresSaver.from_conn_string(
        "postgresql://user:pass@localhost:5432/langgraph"
    )
)
```

### 序列化配置

```python
# 默认：JSON + pickle fallback（兼容性最好）
checkpointer = InMemorySaver(
    serde=JsonPlusSerializer(pickle_fallback=True)
)

# 加密序列化（敏感数据）
from langgraph.checkpoint.serde import EncryptedSerializer
checkpointer = PostgresSaver.from_conn_string(
    DB_URL,
    serde=EncryptedSerializer(encryption_key=os.environ["ENCRYPTION_KEY"])
)
```

### 状态操作 API

```python
config = {"configurable": {"thread_id": "user-123"}}

# 获取当前状态快照
snapshot = graph.get_state(config)
# snapshot.values     → dict: State 内容
# snapshot.next       → tuple[str]: 待执行节点
# snapshot.metadata   → {"step": N, "source": "loop", ...}
# snapshot.config     → 下一个 checkpoint 的 config

# 获取状态历史（支持时间旅行）
history = list(graph.get_state_history(config))
# history[0]  → 最新
# history[-1] → 最早
# history[N].config → 可用于重播

# 从历史某点重播
past_config = history[-3].config
graph.invoke(None, past_config)  # 从该点重新执行

# 直接修改状态
graph.update_state(config, {"field": new_value})
graph.invoke(None, config)  # 继续执行
```

### 持久化模式

| 模式 | 行为 | 场景 |
|------|------|------|
| **全量**（默认） | 每个 super-step 后完整保存 state | 通用 |
| **增量 (Delta)** | 仅存储变更字段 | 大 state 优化 |

```python
# 开启增量模式（自定义 checkpointer 时）
class MyDeltaCheckpointer(BaseCheckpointer):
    def put_writes(self, config, writes, task_id, task_path):
        # 只序例化 writes 中的增量
        ...
```

---

## 二、Store（长期记忆 — 跨线程共享）

> Checkpointer = 单线程内的对话历史。Store = 跨线程的持久知识。

### 后端对比

| 后端 | 导入 | 语义搜索 | 适用 |
|------|------|:--:|------|
| `InMemoryStore` | `langgraph.store.memory` | ❌ | 开发/测试 |
| `PostgresStore` | `langgraph.store.postgres` | ✅ | 生产 |
| `AsyncPostgresStore` | `langgraph.store.postgres` | ✅ | 异步 + 生产 |

### Store API

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

# 写入（namespace, key, value）
store.put(("users", "prefs"), "user-123", {"theme": "dark", "lang": "zh"})
store.put(("users", "memory"), "user-123", {"name": "Bob", "role": "admin"})

# 搜索（支持语义搜索 + 过滤）
memories = store.search(
    ("users",),                        # namespace 前缀
    query="用户偏好",                    # 语义搜索（PostgresStore）
    filter={"lang": "zh"},             # 精确过滤
    limit=10,
)
# → [Item(namespace=..., key=..., value={...}), ...]

# 列出命名空间
namespaces = store.list_namespaces()
# → [("users", "prefs"), ("users", "memory"), ...]
```

### 与图集成

```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
graph = builder.compile(checkpointer=checkpointer, store=store)

# 节点内通过 config 访问
def memory_node(state, config):
    store = config["configurable"].get("store")
    user_id = config["configurable"].get("user_id")

    # 读
    prefs = store.search(("users", "prefs"), filter={"user": user_id})

    # 写
    store.put(("users", "prefs"), user_id, {"last_query": state["query"]})

    return {"preferences": prefs}
```

### 语义搜索配置

```python
from langgraph.store.postgres import PostgresStore

# 自动嵌入索引
store = PostgresStore.from_conn_string(DB_URL)

# 写入时指定嵌入字段
store.put(
    ("knowledge",), "doc-1",
    {
        "title": "LangGraph 架构",
        "content": "LangGraph 是 Agent Runtime...",
        # content 字段自动生成嵌入用于语义搜索
    },
    index=["content"],  # 指定需要嵌入的字段
)

# 搜索时用自然语言
results = store.search(("knowledge",), query="如何做持久化")
# → 语义匹配，不需要精确关键词
```

### 命名空间设计原则

```
("users", "{user_id}")           — 用户级数据
("projects", "{project_id}")     — 项目级数据
("global", "config")             — 全局配置
("cache", "embeddings")          — 嵌入缓存
```

> **原则**: namespace 的粒度决定搜索范围。`store.search(("users",))` 查所有用户数据，`store.search(("users", "user-123"))` 只看该用户。

---

## 三、自定义后端

### 自定义 Checkpointer

```python
from langgraph.checkpoint.base import BaseCheckpointer

class MyCheckpointer(BaseCheckpointer):
    def get_tuple(self, config): ...          # 读 checkpoint
    def put(self, config, checkpoint, metadata, new_versions): ...  # 写
    def put_writes(self, config, writes, task_id, task_path): ...   # 写增量
    def list(self, config, filter=None, limit=None): ...            # 列历史
    def delete_thread(self, config): ...      # 删线程
```

### 自定义 Store

```python
from langgraph.store.base import BaseStore

class MyStore(BaseStore):
    def put(self, namespace, key, value, index=None): ...
    def search(self, namespace_prefix, query=None, filter=None, limit=10): ...
    def list_namespaces(self): ...
    def get(self, namespace, key): ...
    def delete(self, namespace, key): ...
```

---

## 四、`[社区]` 社区实践

### 检查点清理

```python
# 社区发现：长期运行的图会积累大量 checkpoint
# → 定期清理旧 checkpoint
import sqlite3

conn = sqlite3.connect("checkpoints.db")
conn.execute("DELETE FROM checkpoints WHERE thread_id = ? AND created_at < datetime('now', '-30 days')", (thread_id,))
conn.commit()
```

### Store 性能优化

```python
# ✅ 批量写入（减少 I/O）
for item in batch:
    store.put(namespace, item.key, item.value)
# ⚠️ PostgresStore 支持批量，InMemoryStore 无影响

# ✅ 搜索结果限制
store.search(("users",), limit=10)   # 不要传 limit=999999

# ❌ 高频 search → 生产用 PostgresStore + 连接池
```

---

> **返回**: [`SKILL.md`](../SKILL.md) §4 持久化 | §4.1 Store | §4.2 Time Travel
