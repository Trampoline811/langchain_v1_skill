# L3 盲测首轮结果 — 2026-09-07

## 结论速览

| 组 | 静态分 | 运行判定 | skill 效果 |
|----|--------|---------|-----------|
| **ON**（读 langchain-v1 SKILL.md）| **20/20** | **5/5 PASS** | 全部 v1.0 API + 全部可构造 |
| **OFF**（裸写对照）| 8/20 | 5/5 FAIL | 混用 v0 API，import 即炸 |

> 静态分差 **12 分**；运行通过率 **5/5 vs 0/5**。skill 显著有效。

## 逐用例明细

### ON 组（system = langchain-v1 SKILL.md 全文）

| 用例 | 主题 | 静态 | 黑名单 | 运行 |
|------|------|:----:|--------|:----:|
| 1 | 天气查询 Agent | 4/4 | 无 | ✅ 构造成功 |
| 2 | 客服 Bot 记忆 | 4/4 | 无 | ✅ 构造成功 |
| 3 | 简历结构化输出 | 4/4 | 无 | ✅ 构造成功 |
| 4 | HITL 审批 + 重试 | 4/4 | 无 | ✅ 构造成功 |
| 5 | Manager 多智能体 | 4/4 | 无 | ✅ 构造成功 |

生成代码: `tests/l3-blind-test/generated/on/case*.py`（可人工复查）

### OFF 组（system = "You are an expert Python developer."）

| 用例 | 主题 | 静态 | 黑名单命中 | 运行 |
|------|------|:----:|-----------|:----:|
| 1 | 天气查询 Agent | 2/4 | AgentExecutor, ChatOpenAI | ❌ import 失败 |
| 2 | 客服 Bot 记忆 | 0/4 | +create_react_agent, ConversationBufferMemory | ❌ import 失败 |
| 3 | 简历结构化输出 | 2/4 | AgentExecutor, ChatOpenAI | ❌ import 失败 |
| 4 | HITL 审批 + 重试 | 2/4 | AgentExecutor, ChatOpenAI | ❌ import 失败 |
| 5 | Manager 多智能体 | 2/4 | AgentExecutor, ChatOpenAI | ❌ import 失败 |

生成代码: `tests/l3-blind-test/generated/off/case*.py`

## 判定设计说明（重要）

- **L3a** 语法编译 → **L3b** import + 调 build 工厂构造（参数自适应：按签名注入本地模型工厂，
  失败降级 `FakeMessagesListChatModel`，只验 API 结构）→ **L3c** invoke 真跑（fake 或真实 LLM）
- 模型工厂返回字符串（`"openai:gpt-4o"`，create_agent 支持但需真实凭据）→ 判定目标为 API
  结构正确性 → fake 降级，外部凭据/网络错误判 SKIP 不判 FAIL
- OFF 组失败模式高度一致（AgentExecutor 已从 langchain.agents 移除 → ImportError），
  说明盲测跑在**真实 v1.0 环境**而非只看代码风格——正是「真跑通」判定的意义

## 复现命令

```bash
# ON 组：生成 + 判定（需 DEEPSEEK_API_KEY 生成；判定本身可用 fake 无 key）
python tests/l3-blind-test/run.py --group on

# OFF 组对照
python tests/l3-blind-test/run.py --group off

# 只判定已有文件（不再调 LLM）
python tests/l3-blind-test/run.py --group on --no-llm
```

## 发现的问题与后续

- ON 组代码均正确使用了 v1.0 API（黑名单 0 命中）→ **skill 内容与官方 v1.0 一致** ✅
- OFF 组的系统性 v0 API 误用 → 印证「无 skill 时 LLM 训练数据默认写 v0.x」的项目前提
- 后续：deepagents/langgraph 场景可各加一档用例；每组多轮取均分降方差（本次各 1 轮）
