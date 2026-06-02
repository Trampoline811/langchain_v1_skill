# LangChain v1.0 Skill Suite

为没有 LangChain v1.0 训练数据的 LLM 提供编码规范的 Claude Code Skill。

## 盲测验证

| 条件 | 得分 | 关键错误 |
|------|:--:|------|
| Skill ON | **10/10** | 无 |
| Skill OFF | **0/10** | AgentExecutor + ChatOpenAI + create_react_agent |

无 skill 的离线 LLM 会用 2023 年的 v0.x API。加载 skill 后全部纠正。

## 架构

```
skills/
├── langchain-v1/     核心 (always-on, 406行) — create_agent / @tool / middleware
├── langgraph-v1/     扩展 (按需, 261行) — StateGraph / persistence / interrupts
└── deepagents-v1/    扩展 (按需, 275行) — sandboxes / subagents / context engineering
```

## 安装

复制 `skills/` 下需要的目录到你的 skill 目录，在 settings.json 启用：

```json
{
  "skillOverrides": {
    "langchain-v1": "on"
  }
}
```

## 测试结果

见 `results/20250602/` — 四组盲测代码，结果见 `tests/blind_test_analysis.md`

## 维护

```bash
# 同步官方文档
python tools/update_skill.py

# 只拉文档
python tools/update_skill.py --docs-only

# 功能验证
python tools/update_skill.py --test-only

# 打包结果
python tools/update_skill.py --package
```
