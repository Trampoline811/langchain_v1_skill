# 专题研究报告索引

基于 `docs/` 原始文档加工生成的研究报告、横向对比、速查手册。

> `docs/official/` = 官方文档下载副本（原材料）
> `topics/` = 基于原材料的分析加工（学习产出）

## 专题列表

| 文件 | 专题 | 描述 | 日期 |
|------|------|------|------|
| `multi-agent-routing-comparison.md` | 多智能体路由横向对比 | Skills / Subagents / Handoffs / Router 四种模式的架构、性能、选型速查 | 2026-07-09 |
| `langchain-skills-deep-dive.md` | LangChain Skills 机制深度剖析 | 两层实现路径（LangChain DIY + DeepAgents 内置）、渐进披露原理、文件规范、Interpreter Skills、与 Tools/Memory 边界 | 2026-07-09 |
| `langchain-middleware-deep-dive.md` | LangChain v1.0 中间件深度剖析 | 钩子系统全景（6 hooks + 14 内置中间件）、自定义中间件 MDA 三层、三大实战模式（动态提示词/状态切换/工具过滤）、与 v0.x Memory/Callbacks 对比 | 2026-07-09 |

## 扩展规则

### 新增专题

1. 在 `topics/` 下新增 `.md` 文件（kebab-case 命名）
2. 在上方表格新增一行
3. 更新日期为生成日期

### 引用规范（强制）

每个专题报告末尾必须包含 `## 参考资料` 章节，格式：

```markdown
## 参考资料

> 专题报告引用规范见 [`topics/INDEX.md`](INDEX.md#扩展规则)。

### 本地源文件

| 本地路径 | 官方 URL |
|----------|----------|
| `docs/official/xxx/xxx.md` | [页面标题](https://docs.langchain.com/oss/python/xxx) |

### 外部参考（如有）

| URL | 说明 |
|-----|------|
| https://example.com | 简要说明 |

> **整理日期**: YYYY-MM-DD
```

**规则**：
- **本地源文件** 必须列出所有引用的 `docs/official/` 或 `docs/community/` 文件，并附对应官方 URL
- **外部参考** 列出规范、仓库、博客等外部链接
- 官方 URL 映射规则：`docs/official/{product}/{slug}.md` → `https://docs.langchain.com/oss/python/{product}/{slug}`
