# 专题报告写作规范

> 生成 `topics/` 下任意专题报告时，必须遵守以下规范。
> 由 CLAUDE.md 的 topics/ 扩展规则引用，每次会话自动加载。

---

## 一、目录语义

| 目录 | 语义 | 性质 |
|------|------|------|
| `docs/official/` | 官方文档下载副本 | 原材料 |
| `docs/community/` | 社区案例/代码模式 | 参考素材 |
| `topics/` | 基于 `docs/` 加工的分析报告 | **加工品** |

> `topics/` 不存原材料，只存分析产出。源文件引用指向 `docs/`。

---

## 二、报告总体结构

```markdown
# 标题（中文，点明主题）

> 一句话副标题 + 基于哪些源文件 + 日期

---

## 一、概述/定位
## 二、核心概念
## 三~N、主体内容（按需分章）
## N+1、快速速查/选型指南（可选）
## N+2、本地相关文件索引（可选）

---

## 参考资料  ← 强制
```

---

## 三、MDA 三层结构（模式详解专用）

当报告包含"模式/架构详解"类章节时，每个子模式按 MDA 框架展开：

```
M — Mechanics（关键代码骨架）
     ↑ 用哪些 API/类/函数、怎么写
D — Dynamics（理论说明）  ← 承上启下
     ↑ LangChain 的哪些机制如何组合、运行时怎么运转
A — Aesthetics（核心思想）
     ↑ 设计意图、用户体验目标、解决什么问题
```

**写作顺序为 A→D→M**（读者先理解思想，再看机制，最后看代码）：

```markdown
### x.x Pattern 名称

**核心思想**:（Aesthetics）
  - 一句话概括设计意图
  - 用户视角的感受（"用户感觉在和谁对话？"）
  - 和其他模式的本质区别

**理论说明**:（Dynamics）  ← 最容易遗漏
  - 机制对照表：用到什么机制 | 作用 | LangChain 实现
  - 运行时串联流程：分步描述 Agent-Tools-Middleware-State 如何协作
  - 本质：一行公式总结

**关键代码骨架**:（Mechanics）
  - 可运行的伪代码，关键 API 标注注释
```

### 理论说明的"机制对照表"模板

```markdown
| 机制 | 作用 | LangChain 实现 |
|------|------|----------------|
| 机制名 | 解决什么问题 | `具体 API/类/函数` |
```

### 理论说明的"运行时流程"模板

```markdown
1. 启动/触发 → 哪个组件做了什么 → 状态变化
2. 中间步骤 → Agent 决策/工具调用/中间件拦截 → 状态变化
3. 结果 → 如何响应用户
```

---

## 四、引用规范（强制）

每个报告末尾必须包含 `## 参考资料` 章节。

### 4.1 模板

```markdown
## 参考资料

> 专题报告引用规范见 [`topics/INDEX.md`](INDEX.md#扩展规则)。

### 本地源文件

| 本地路径 | 官方 URL |
|----------|----------|
| `docs/official/{product}/{slug}.md` | [页面标题](https://docs.langchain.com/oss/python/{product}/{slug}) |

### 外部参考（如有）

| URL | 说明 |
|-----|------|
| https://example.com | 简要说明 |

> **整理日期**: YYYY-MM-DD
```

### 4.2 URL 映射规则

`docs/official/{product}/{slug}.md` → `https://docs.langchain.com/oss/python/{product}/{slug}`

示例：
- `docs/official/langchain/langchain-multi-agent-skills.md` → `https://docs.langchain.com/oss/python/langchain/multi-agent/skills`
- `docs/official/deepagents/deepagents-skills.md` → `https://docs.langchain.com/oss/python/deepagents/skills`

### 4.3 引用要求

- **本地源文件**：必须列出所有引用的 `docs/official/` 或 `docs/community/` 文件，附带官方 URL
- **外部参考**：列出规范、仓库、博客等外部链接（如有）
- **Skill 参考**：如引用了项目自身的 skill 文件（`skills/xxx/references/yyy.md`），也需列出

---

## 五、深度分析框架（deep-research 启发，本地适配版）

> 提取 deep-research 的分析管道，适配到本地 `docs/official/` 源文件。**零 token 成本，同等分析深度。**

### 5.1 核心原则

deep-research 的价值不在 WebSearch，在 **分析结构**。将以下 7 个步骤融入手动报告：

| # | 步骤 | deep-research 方式 | 本地适配方式 | 成本 |
|---|------|--------------------|-------------|:--:|
| ① | **多角度分解** | 5路并行 WebSearch | 手动将 topic 拆为 3-5 个子问题，覆盖不同维度 | 0 |
| ② | **源分级** | primary/secondary/blog/forum | 标注本地源类型：`official-doc` / `community-case` / `skill-ref` / `external-url` | 0 |
| ③ | **关键声明提取** | 从 23 个网页提取 111 条 claim | 从 `docs/official/` 中提取核心论断（每源 3-5 条） | ~10K tokens |
| ④ | **交叉验证** | 3-vote 对抗验证 | 同一声明在 2+ 独立源文件中核对，标记一致/矛盾/无覆盖 | ~20K tokens |
| ⑤ | **信心标注** | high / medium / low | 同左，基于交叉验证结果 | 0 |
| ⑥ | **坑点/反模式搜集** | 从 forum/issue/blog 提取 | 优先从本地 `docs/official/` 查找；缺口处标记 "待外部补充"，可选启动 deep-research 补 | 0~340万 |
| ⑦ | **限定声明 + 开放问题** | 末尾 cav eats + openQuestions | 同左，强制写入每个报告末尾 | ~2K tokens |

### 5.2 报告中新增的标准章节

基于以上框架，每个专题报告应在原有结构基础上新增：

```markdown
## §N. 已知坑点与避坑指南  ← 来自步骤⑥
## §N+1. 跨框架/竞品对比（如适用）  ← 来自步骤①多角度
## §N+2. 可靠性数据（如有）  ← 来自步骤⑤

---

## 限定声明 ← 来自步骤⑦
## 待解决问题 ← 来自步骤⑦
```

### 5.3 什么时候启动 deep-research（不替代手动）

| 条件 | 启动 deep-research？ |
|------|:--:|
| 本地 `docs/official/` 已覆盖 topic 核心内容 | ❌ 不启动 |
| 需要找社区踩坑/反模式/GitHub Issues | ✅ 启动（本地无此信息） |
| 需要跨框架对比（vs MCP / CrewAI / OpenAI SDK） | ✅ 启动 |
| 需要最新生产数据（通过率/token统计/版本更新） | ✅ 启动 |
| 小型专题，本地源充足 | ❌ 不启动（手动框架足够） |
| 你明确告诉我 "这个 topic 很重要，值得花钱" | ✅ 启动 |

> **预算参考**：deep-research 单次 ~300 万 tokens。建议每月 ≤ 3 次，仅用于高价值专题的**坑点发现**和**跨框架对比**两个维度。

### 5.4 坑点搜集的本地优先策略

```
1. 先扫 docs/official/ → 是否有 "troubleshooting" / "common issues" / "limitations" 章节
2. 扫 docs/community/cases/ → 是否有实战踩坑记录
3. 扫 skills/*/references/ → 是否有 "lessons-learned" 类内容
4. 以上都无 → 标记 {PITFALLS_TODO} → 可选启动 deep-research 补充
5. deep-research 返回 → 提取 pitfall claims → 交叉验证 → 写入报告
```

---

## 六、扩展流程（新增专题时）

每次生成新专题报告，按以下步骤执行：

1. 在 `topics/` 下新建 `xxx.md`（kebab-case 命名）
2. 更新 `topics/INDEX.md` 表格加一行（文件名 + 专题 + 描述 + 日期）
3. 报告末尾必须包含 `## 参考资料` 章节（按 §四 规范）

> CLAUDE.md 已强制此流程，无需手动记忆。

---

## 七、常见问题

### Q: 理论说明 vs 架构要素 有什么区别？

架构要素是流水账（"1. 定义Skill 2. 创建工具 3. 构建中间件"），只列步骤不解释为什么。理论说明要回答：
- 为什么选这些机制（不是其他机制）？
- 它们如何串联运转（运行时顺序）？
- 核心思想怎么通过这套机制实现？

### Q: 什么时候用 MDA 三层，什么时候不用？

- **模式/架构详解**（如多智能体路由对比 §4）→ 必须用 MDA
- **概念总览/对比表**（如 Skills 深度剖析 §一~§三）→ 不需要，用传统章节即可
- **速查/选型表** → 不需要

### Q: 引用可以省略官方 URL 吗？

不可以。本地文件可能过时，官方 URL 是验证来源可信度的唯一途径。
