# 易犯错误（血泪教训）

> 以下来自 2026-06-22 AgentSeek 对标更新中实际犯过的错，写下来防止再犯。

## 错误 1：Skill vs Reference 边界判断失误

**症状**：把 langsmith-trace 先做成了 langchain-v1 的 reference（`references/langsmith-trace.md`），用户纠正后才发现应该独立为 skill。

**判断标准（自检 3 问）**：
| 问题 | 答"是"→ reference | 答"否"→ 考虑独立 skill |
|------|:--:|:--:|
| 内容只服务于当前这一个 skill？ | reference | skill |
| 没有独立的触发词/场景？ | reference | skill |
| 不是独立产品/工具？ | reference | skill |

**教训**：LangSmith 是独立可观测平台，跨 Framework/Runtime/Harness 三层，有独立 CLI 和触发词（"debug trace"、"LangSmith"）。满足 3 个"否" → 独立 skill。

## 错误 2：新增 skill 后忘记联动更新

**症状**：新增 `langsmith-trace` skill 后，忘记同步更新：
- `agent-sdk-router/SKILL.md` — 路由决策表缺新 skill
- `README.md` — Skill 目录表、架构图、选型速查
- `CLAUDE.md` — 仓库结构、决策逻辑

**教训**：新增/删除 skill 时，必须联动更新以下 **4 个文件**：

| 文件 | 更新内容 |
|------|---------|
| `skills/agent-sdk-router/SKILL.md` | 决策表 + 场景对照 + 执行协议 |
| `README.md` | Skill 目录表 + 架构图 + 选型速查 + 更新日志 |
| `CLAUDE.md` | 仓库结构 + 架构三层图 + 决策逻辑 + 核心原则条数 |
| `tools/update_skill.py` | 如有自动化同步脚本，也要更新 skill 列表 |

## 错误 3：cp -r 嵌套陷阱

**症状**：`cp -r skills/langchain-v1 "E:/AI_skill/langchain-v1/"` 在目标已存在时，会在目标下面创建 `langchain-v1/langchain-v1/` 嵌套目录。

**教训**：同步命令必须先删后拷：

```bash
# ❌ 错误 — 目标存在会嵌套
cp -r skills/langchain-v1 "E:/AI_skill/langchain-v1/"

# ✅ 正确 — 先删再拷
rm -rf "E:/AI_skill/langchain-v1"
cp -r skills/langchain-v1 "E:/AI_skill/langchain-v1/"
```

## 错误 4：同步不完整

**症状**：更新了 langchain-v1 后只同步了那一个 skill，忘了其他 skill 也需要同步（别的 skill 也可能有交叉引用更新）。

**教训**：每次任何 skill 更新后，**全量同步所有 skill** 到 `E:\AI_skill\`，不要只同步改动的那个。特别是路由 skill 和 README 的更新涉及多个文件时。
