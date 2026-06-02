# 盲测结果 — 2025-06-02

## 四组对照

| 组 | 文件 | 联网 | Skill | 得分 | 关键错误 |
|----|------|:--:|:--:|:--:|------|
| A | only_langchain.py | YES | NO | 9/10 | 缺中间件 |
| B | without_skill_langchain.py | NO | NO | 2/10 | ChatOpenAI + 过度工程 |
| C | with_skill_langchain_v1.py | NO | YES | 10/10 | 无 |
| D | pure_langchain.py | NO | NO | 0/10 | 全部v0.x API |

## 结论

Skill ON vs OFF (C vs D): 0分 → 10分, Δ = +10
LLM训练数据 = 大量v0.x残留。Skill是唯一保障。

## 测试prompt

"请用 Python + LangChain 写一个天气查询 Agent，用户输入城市名，Agent 调用 get_weather 工具返回天气。"
