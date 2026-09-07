# -*- coding: utf-8 -*-
"""L3 盲测用例定义 — prompt + 评分项（与 tests/blind_test.md 同源）"""

CASES = [
    {
        "id": 1,
        "name": "basic_weather_agent",
        "prompt": (
            "请用 Python + LangChain 写一个天气查询 Agent，"
            "用户输入城市名，Agent 调用 get_weather 工具返回天气。\n"
            "注意：这是一个可运行的示例，请把 '模型初始化' 与 'Agent 构建' 拆到独立函数，"
            "并在文件末尾保留 `if __name__ == \"__main__\":` 入口（入口内可只做单轮示例调用）。"
        ),
        "points": [
            "用 create_agent() 而非 AgentExecutor / initialize_agent",
            "用 init_chat_model(\"openai:gpt-4\") 而非 ChatOpenAI(model=\"gpt-4\")",
            "用 @tool 装饰器而非 Tool.from_function()",
            "用 agent.invoke({\"messages\": [...]}) 而非 agent.run()",
        ],
        "build_fn": "build_weather_agent",
        "model_fn": "create_model",
    },
    {
        "id": 2,
        "name": "memory_customer_bot",
        "prompt": (
            "请用 LangChain 实现一个客服 Bot，能记住用户的姓名和偏好，"
            "在后续对话中使用这些信息。\n"
            "注意：这是一个可运行的示例，请把 '模型初始化' 与 'Agent 构建' 拆到独立函数，"
            "并在文件末尾保留 `if __name__ == \"__main__\":` 入口。"
        ),
        "points": [
            "用 checkpointer=InMemorySaver() + thread_id 而非 ConversationBufferMemory()",
            "用 state_schema / 自定义 state 字段（user_name）而非手写 StateGraph",
            "正确使用 config={\"configurable\": {\"thread_id\": \"...\"}}",
        ],
        "build_fn": "build_customer_bot",
        "model_fn": "create_model",
    },
    {
        "id": 3,
        "name": "resume_structured_output",
        "prompt": (
            "请用 LangChain 写一个简历解析 Agent，"
            "输入简历文本，输出结构化的 CandidateInfo（含 name, skills, score）。\n"
            "注意：这是一个可运行的示例，请把 '模型初始化' 与 'Agent 构建' 拆到独立函数，"
            "并在文件末尾保留 `if __name__ == \"__main__\":` 入口。"
        ),
        "points": [
            "用 response_format=Pydantic 模型而非在 prompt 里要求输出 JSON",
            "用 pydantic BaseModel 定义 schema",
            "用 result[\"structured_response\"] 获取结果",
            "不会用 model.with_structured_output() + 手动拼接 chain",
        ],
        "build_fn": "build_resume_agent",
        "model_fn": "create_model",
    },
    {
        "id": 4,
        "name": "hitl_email_approval",
        "prompt": (
            "LangChain Agent 需要对 send_email 工具调用进行人工审批，"
            "同时对工具失败进行自动重试（最多 3 次）。请实现。\n"
            "注意：这是一个可运行的示例，请把 '模型初始化' 与 'Agent 构建' 拆到独立函数，"
            "并在文件末尾保留 `if __name__ == \"__main__\":` 入口。"
        ),
        "points": [
            "用 HumanInTheLoopMiddleware(interrupt_on={\"send_email\": True})",
            "用 ToolRetryMiddleware(max_retries=3)",
            "不会用 callback 或手动 try/catch 实现",
            "正确配合 checkpointer（HITL 必须）",
        ],
        "build_fn": "build_email_agent",
        "model_fn": "create_model",
    },
    {
        "id": 5,
        "name": "multi_agent_manager",
        "prompt": (
            "请用 LangChain 实现一个研发团队 Agent 系统："
            "一个 Manager Agent 根据任务类型分发给 Coder 或 Reviewer 子 Agent。\n"
            "注意：这是一个可运行的示例，请把 '模型初始化' 与 'Agent 构建' 拆到独立函数，"
            "并在文件末尾保留 `if __name__ == \"__main__\":` 入口。"
        ),
        "points": [
            "用 SubAgentMiddleware 或 agent.as_tool() 嵌套",
            "不会用旧版 MultiAgentChain 或手动编排",
            "每个子 Agent 独立创建，有各自的 name 和 tools",
            "Manager 用路由逻辑分发，而非 if-else",
        ],
        "build_fn": "build_manager_agent",
        "model_fn": "create_model",
    },
]

# 黑名单（出现即扣分/标记旧版 API）
BLACKLIST = [
    "AgentExecutor", "initialize_agent", "create_react_agent", "ConversationBufferMemory",
    "ChatOpenAI", "LLMChain", "MultiAgentChain", "Tool.from_function",
    "ConversationSummaryMemory", "memory=ConversationBuffer",
]

# 白名单关键词（用于提示 v1.0 风格，不强制所有用例都出现）
WHITELIST = [
    "create_agent", "init_chat_model", "@tool", "InMemorySaver", "checkpointer",
    "response_format", "structured_response", "HumanInTheLoopMiddleware",
    "ToolRetryMiddleware", "thread_id",
]
