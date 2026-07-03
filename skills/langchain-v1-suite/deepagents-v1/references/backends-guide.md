# Deep Agents Backends 完整指南

> **来源**: 官方 `deepagents-backends.md` (46353字) + 社区案例 `全自动数据分析可视化Agent系统.md`
> **定位**: 6 种 Backend 的完整参数、路由规则、自定义接口。快速示例见 `SKILL.md` §2.1。

---

## 1. Backend 全景对比

| Backend | 存储位置 | 持久化 | 安全 | 适用场景 |
|---------|---------|:--:|:--:|------|
| `StateBackend()` | Agent state（内存） | 同线程 | 🟢 低 | 默认选择、临时草稿纸 |
| `FilesystemBackend(root_dir)` | 本地磁盘 | ✅ 永久 | 🟡 中 | 本地 CLI、编程助手 |
| `LocalShellBackend(root_dir)` | 磁盘 + Shell | ✅ 永久 | 🔴 高 | 个人开发机 |
| `StoreBackend(namespace=...)` | LangGraph Store | ✅ 跨会话 | 🟢 低 | 长期记忆、知识库 |
| `CompositeBackend(routes={...})` | 混合路由 | 混合 | 取决于子后端 | 多后端组合 |
| 沙箱后端 (Custom) | 隔离容器 | ✅ 永久 | 🟢 低 | 安全代码执行 |

---

## 2. 各 Backend 详解

### 2.1 StateBackend（默认）

```python
from deepagents.backends import StateBackend

backend = StateBackend()
```

- 文件存在 Agent state 的 `messages` 中
- 同一次 `invoke` 内持久，进程重启即丢失
- 无需磁盘权限，最快

### 2.2 FilesystemBackend（本地磁盘）

```python
from deepagents.backends import FilesystemBackend

backend = FilesystemBackend(root_dir="./agent_workspace")
```

**安全警告**: Agent 可以通过 `ls` 读取 `.env`、`config.json` 等敏感文件。
**生产建议**: 将 `root_dir` 指向专用目录，不要用项目根目录。

### 2.3 LocalShellBackend（磁盘 + Shell）

```python
from deepagents.backends import LocalShellBackend

backend = LocalShellBackend(root_dir="./workspace")
```

> 🔴 **Agent 可以执行任意系统命令**。仅用于个人开发机。

### 2.4 StoreBackend（跨会话持久化）

```python
from deepagents.backends import StoreBackend

backend = StoreBackend(
    namespace=lambda runtime: (runtime.context.user_id,),
)
```

- 文件写入 LangGraph Store
- **跨 session 持久** — 下次对话自动可用
- 适合：用户偏好、积累知识、项目文档

### 2.5 CompositeBackend（混合路由）

```python
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

backend = CompositeBackend(
    default=StateBackend(),               # 默认临时
    routes={
        "/memories/": StoreBackend(        # /memories/ 下持久化
            namespace=lambda rt: (rt.context.user_id,),
        ),
        "/cache/": StateBackend(),          # /cache/ 下临时
    },
)
```

**路由规则**: 路径前缀匹配 → 走对应 Backend。`ls`/`glob`/`grep` 自动聚合所有子后端结果。

### 2.6 自定义 Backend（BackendProtocol）

```python
from deepagents.backends import BackendProtocol

class S3Backend(BackendProtocol):
    def ls(self, path: str) -> list[dict]:
        """列出 path 下的文件和目录"""
        ...

    def read(self, path: str) -> str:
        """读文件内容"""
        ...

    def write(self, path: str, content: str) -> None:
        """写文件（覆盖）"""
        ...

    def edit(self, path: str, old: str, new: str) -> None:
        """编辑文件（查找替换）"""
        ...

    def grep(self, pattern: str, path: str = "/") -> list[dict]:
        """正则搜索文件内容"""
        ...

    def glob(self, pattern: str, path: str = "/") -> list[str]:
        """文件名匹配"""
        ...
```

> 实现 6 个方法即可接入 S3/MinIO/WebDAV 等任意存储。

---

## 3. FilesystemPermission（声明式权限）

```python
from deepagents import FilesystemPermission

# 黑名单：禁止写入 /policies/ 下任何文件
FilesystemPermission(
    operations=["write", "edit"],
    paths=["/policies/**"],
    mode="deny",
)

# 白名单：只允许读 /workspace/ 下文件
FilesystemPermission(
    operations=["read"],
    paths=["/workspace/**"],
    mode="allow",
)

# 注入到 FilesystemMiddleware
from deepagents.middleware import FilesystemMiddleware

FilesystemMiddleware(
    backend=FilesystemBackend(root_dir="./workspace"),
    permissions=[
        FilesystemPermission(operations=["write"], paths=["/system/**"], mode="deny"),
    ],
)
```

---

## 4. 自动上下文管理

> Deep Agents 自动管理上下文窗口 — **无需手动干预**。

| 机制 | 触发条件 | 行为 |
|------|---------|------|
| 大结果卸载 | tool 结果 > 20K tokens | 完整内容存文件系统，对话中替换为「文件引用 + 前 10 行预览」 |
| 自动摘要 | 上下文达窗口 85% | 生成结构化摘要，完整记录保存到文件系统 |
| 按需回溯 | Agent 主动调用 | `read_file` / `grep` 取回完整内容 |

---

## 5. `[社区]` 社区实践

### 生产推荐配置

```python
from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend

# ✅ 生产环境：本地临时 + Store 持久化混合
backend = CompositeBackend(
    default=FilesystemBackend(root_dir="./agent_workspace"),
    routes={
        "/memories/": StoreBackend(
            namespace=lambda rt: (rt.context.user_id,),
        ),
    },
)
# 临时文件 → 本地磁盘（快）
# 用户记忆 → Store（跨会话）
# .env 保护 → root_dir 指向专用目录
```

### Windows 路径兼容

```python
# ❌ Windows 反斜杠导致 Backend glob 失败
root_dir = "C:\\Users\\admin\\agent_workspace"

# ✅ 统一正斜杠
root_dir = "C:/Users/admin/agent_workspace"
```

### 文件清理

```python
# 社区发现：长时间运行的 agent 会积累大量临时文件
# → FilesystemBackend 不会自动清理，需手动管理
import shutil, os
workspace = "./agent_workspace"
if os.path.exists(workspace):
    shutil.rmtree(workspace)
    os.makedirs(workspace)
```

---

> **返回**: [`SKILL.md`](../SKILL.md) §2.1 文件系统 | §2.4 记忆 | §3 上下文工程
