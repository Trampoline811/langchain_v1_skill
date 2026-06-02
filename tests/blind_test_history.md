# 盲测四组来历回顾

## 原始需求

> "对比 skill 加载前后的代码质量" → 核心是 **C vs D**

## 四组的形成过程

| 组 | 文件 | 怎么来的 |
|----|------|---------|
| **C** (10/10) | `with_skill_langchain_v1.py` | skill ON，模型用训练数据 + skill 纠正 → 正确 v1.0 |
| **D** (0/10) | `pure_langchain.py` | skill OFF，纯训练数据，只用 LangChain → 全部 v0.x |
| **B** (2/10) | `without_skill_langchain.py` | skill OFF，提示"LangChain + LangGraph" → 部分新部分旧 |
| **A** (9/10) | `only_langchain.py` | skill OFF，但模型**自行联网搜索**了官方文档 → 自愈 |

## 简化后的标准盲测（推荐）

以后只跑两组就够了：

```
C 组 (skill ON):  "用 Python + LangChain 写天气查询 Agent"
D 组 (skill OFF): "用 Python + LangChain 写天气查询 Agent"
                  (不要联网，不要提示用 LangGraph)
```

**C vs D = skill 的真实价值**。A 组和 B 组是意外产物，不必每次跑。
