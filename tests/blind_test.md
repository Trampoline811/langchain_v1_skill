# LangChain v1.0 Skill 盲测方案

## 测试原理

```
同一 LLM (DeepSeek-V3)，同一 prompt，
唯一变量 = skill 是否激活。
对比两组产出的 v1.0 API 使用正确率。
```

## 测试对象

| 条件 | skill 状态 | 预期 |
|------|-----------|------|
| A 组（对照） | langchain-v1 **未加载** | 混用旧版 API（ChatOpenAI, AgentExecutor, LLMChain） |
| B 组（实验） | langchain-v1 **已加载** | 纯 v1.0 API（create_agent, init_chat_model, @tool） |

## 五个测试用例

### 用例 1: 基础 Agent（最简单）
```
请用 Python + LangChain 写一个天气查询 Agent，
用户输入城市名，Agent 调用 get_weather 工具返回天气。
```

**评分项：**
- [ ] 用 `create_agent()` 而非 `AgentExecutor` / `initialize_agent`
- [ ] 用 `init_chat_model("openai:gpt-4")` 而非 `ChatOpenAI(model="gpt-4")`
- [ ] 用 `@tool` 装饰器而非 `Tool.from_function()`
- [ ] 用 `agent.invoke({"messages": [...]})` 而非 `agent.run()`

### 用例 2: 带记忆的多轮对话
```
请用 LangChain 实现一个客服 Bot，能记住用户的姓名和偏好，
在后续对话中使用这些信息。
```

**评分项：**
- [ ] 用 `checkpointer=InMemorySaver()` + `thread_id` 而非 `ConversationBufferMemory()`
- [ ] 用 `state_schema` 扩展自定义字段（user_name）而非自定义 StateGraph
- [ ] 正确使用 `config={"configurable": {"thread_id": "..."}}`

### 用例 3: 结构化输出
```
请用 LangChain 写一个简历解析 Agent，
输入简历文本，输出结构化的 CandidateInfo（含 name, skills, score）。
```

**评分项：**
- [ ] 用 `response_format=MySchema` 而非在 prompt 里要求输出 JSON
- [ ] 用 Pydantic BaseModel 定义 schema
- [ ] 用 `result["structured_response"]` 获取结果
- [ ] 不会用 `model.with_structured_output()` + 手动拼接 chain

### 用例 4: 中间件定制
```
LangChain Agent 需要对 send_email 工具调用进行人工审批，
同时对工具失败进行自动重试（最多3次）。请实现。
```

**评分项：**
- [ ] 用 `HumanInTheLoopMiddleware(interrupt_on={"send_email": True})`
- [ ] 用 `ToolRetryMiddleware(max_retries=3)`
- [ ] 不会用 callback 或手动 try/catch 实现
- [ ] 正确配合 `checkpointer`（HITL 必须）

### 用例 5: 多智能体协作
```
请用 LangChain 实现一个研发团队 Agent 系统：
一个 Manager Agent 根据任务类型分发给 Coder 或 Reviewer 子 Agent。
```

**评分项：**
- [ ] 用 `SubAgentMiddleware` 或 `agent.as_tool()` 嵌套
- [ ] 不会用旧版 `MultiAgentChain` 或手动编排
- [ ] 每个子 Agent 独立创建，有各自的 name 和 tools
- [ ] Manager 用路由逻辑分发，而非 if-else

## 评分规则

每用例满分 4 分，总分 20 分：

| 分数 | 含义 |
|------|------|
| 4 | 全部使用 v1.0 正确 API |
| 3 | 用了 v1.0 API 但有 1 处版本不匹配 |
| 2 | 混用了 v0 和 v1 API |
| 1 | 大部分用 v0 API |
| 0 | 全是旧版 API |

## 预期结果

| 组 | 预期均分 | 理由 |
|----|---------|------|
| A（无 skill） | 6-10 分 | LLM 训练数据主要是 v0.x，会混用 ChatOpenAI/AgentExecutor |
| B（有 skill） | 16-20 分 | Skill 强制黑名单 + API 速查表 → 正确率显著提升 |

## 执行方式

### 方式 1: Claude Code 新会话

```bash
# A 组: 临时禁用 skill
claude --no-skills
# 然后输入 5 个 prompt，记录代码

# B 组: skill 正常激活
claude
# skill 激活后输入同样的 5 个 prompt
```

### 方式 2: API 直接调用

```python
import openai

system_a = "You are a Python developer."  # 对照组
system_b = open("E:/AI_skill/langchain-v1/SKILL.md").read()  # 实验组

prompts = [...]  # 上面的 5 个 prompt

for i, prompt in enumerate(prompts):
    for label, system in [("A", system_a), ("B", system_b)]:
        response = openai.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        print(f"Case {i+1} Group {label}: {response.choices[0].message.content}")
```

## 成功标准

- B 组均分 > 15/20 → skill 有效
- B 组 - A 组 >= 5 分 → skill 有明显提升
- 0 处旧版 API 调用（黑名单全部规避）

## 持续改进

如果某用例 B 组得分低于 3 分 → 对应章节不够清晰 → 回看 SKILL.md 补充示例
