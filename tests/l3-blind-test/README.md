# L3 盲测 — 生成→执行→判定 闭环验证

> 补齐「LLM 读 skill 现写代码 → 自动执行 → 判跑通」的自动化验证层。
> 与 L1（确定性回归：langgraph_agent.py / deep_agent.py）、L2（真实 LLM 冒烟：resume_agent.py）互补。

## 验证目标

回答两个此前未被自动验证覆盖的问题：

1. **生成正确性**：一个不知道 LangChain v1 的 LLM，读 skill（ON 组）后写出的代码是否
   使用 v1.0 API（黑名单 0 命中）？对照不读 skill 的 OFF 组差距多大？
2. **可运行性**：写出的代码在真实 .venv 环境里能否 import + 构造 + 跑通（不只人工看代码）？

## 三级判定标准（从静态到动态）

| 级别 | 检查内容 | 判定 | 成本 |
|------|---------|------|------|
| **L3a 语法编译** | `python -m py_compile` | 语法错误 → FAIL | 无 LLM |
| **L3b 导入+构造** | import 生成模块，调 `build_agent()`/`build_graph()` 工厂 | import/构造异常 → FAIL | 无 LLM |
| **L3c 真实执行** | 对构造出的 agent 跑一轮（fake model 或真实 LLM） | 执行异常/无结构化结果 → FAIL | 有 key |

> 判定组合：`L3a 通过 → 可运行候选`；`L3a+L3b → 结构正确`；`L3a+L3b+L3c → 真跑通`。
> 生成代码的**静态评分**沿用 blind_test.md 规则（每例 0-4 分，看 API 使用正误）。

> **L3c 判定语义**：真实凭据可用时才真跑；模型工厂凭据失败（如 provider 无 key）→ 降级
> `FakeMessagesListChatModel` 只验 API 结构（此时 L3b 构造成功即判 PASS，不追 L3c）；
> fake model 能力不足以驱动真跑（如对 agent 图抛 `NotImplementedError`）→ 判 **SKIP 不判 FAIL**
> （属判定 harness 限制，非生成代码错误）。外部模型/网络不可达同样 SKIP。

## 七个用例（由简到繁，跨 3 个子技能）

与 `tests/blind_test.md` 同源（prompt 见 `cases.py`）。每个用例的 `skill` 字段决定
**ON 组注入哪个子技能**作为系统提示（langchain-v1 / deepagents-v1 / langgraph-v1），
OFF 组一律裸写对照——扩展后不只验证 langchain-v1，还覆盖 deepagents / langgraph 两个子技能：

| 用例 | 主题 | 注入技能 | 覆盖 API |
|------|------|---------|---------|
| 1 | 天气查询 Agent | langchain-v1 | `create_agent` / `init_chat_model` / `@tool` / `agent.invoke` |
| 2 | 客服 Bot 多轮记忆 | langchain-v1 | `checkpointer=InMemorySaver` + `thread_id` / `state_schema` 扩展 |
| 3 | 简历解析结构化输出 | langchain-v1 | `response_format=Pydantic` / `result["structured_response"]` |
| 4 | send_email 审批 + 失败重试 | langchain-v1 | `HumanInTheLoopMiddleware` / `ToolRetryMiddleware` + checkpointer |
| 5 | Manager 分发多智能体 | langchain-v1 | `SubAgentMiddleware` / `agent.as_tool()` 嵌套 |
| 6 | 深度研究规划 Agent | deepagents-v1 | `create_deep_agent` / `@tool` / `response_format`（Pydantic 结构化计划） |
| 7 | 持久化记忆问答图 | langgraph-v1 | `StateGraph` / `Annotated` reducer / `compile(checkpointer=InMemorySaver())` |

## 执行方式

```bash
# 前置：.venv 已建 + DEEPSEEK_API_KEY 已设（生成代码需要一次 API 调用；
#       判定本身可用 fake model 无 key 跑）
# 注意：判定环境额外依赖 python-dotenv（个别生成代码会 import 它）
python -m pip install python-dotenv   # 或用 uv

# 生成 + 全三级判定（默认 ON 组 = 读 langchain-v1 SKILL.md）
python tests/l3-blind-test/run.py --group on

# 对照组：不读 skill 裸写
python tests/l3-blind-test/run.py --group off

# 只跑到指定级（省 key）：--max-level b
python tests/l3-blind-test/run.py --group on --max-level b
```

输出：
- `generated/on/case1_weather.py` … 生成代码落盘（可人工复查）
- `report_<组>_<时间戳>.md` 评分 + 三级判定表
- 评分规则：静态分 0-4/例（见 blind_test.md），汇总 `4×N` 分动态计算（7 例满分 28）

## 成功标准（沿用 blind_test.md，N=用例数动态）

- ON 组每例均分 ≥ 3/4（满 `4×N`）→ skill 有效
- ON − OFF 每例均值 ≥ 1.0 分 → skill 有明显提升
- 0 处黑名单 API（ON 组）
- PASS/SKIP 率 ON ≥ OFF（真跑通是最终裁判；SKIP 不计 FAIL）

## 与 docs/ 镜像的关系

生成的代码若抛错，优先回 `docs/official/` 镜像查官方 API 现状 → 若 skill 与官方文档不一致，
按 diff 驱动流程更新 skill（见 AGENTS.md Step 3）。
