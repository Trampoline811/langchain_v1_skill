import json
from typing import List, Dict, Any
from dataclasses import dataclass, field
from deepagents import Agent, Tool

# ---------- 自定义工具 ----------
@dataclass
class CalculatorTool(Tool):
    """计算器工具：支持加法和乘法"""
    name: str = "calculator"
    description: str = "执行基本算术运算（加法和乘法）。输入格式：{'operation': 'add'|'multiply', 'numbers': [num1, num2, ...]}"
    
    def run(self, **kwargs) -> str:
        operation = kwargs.get("operation")
        numbers = kwargs.get("numbers", [])
        
        if not numbers or len(numbers) < 2:
            return json.dumps({"error": "至少需要两个数字"})
        
        if operation == "add":
            result = sum(numbers)
        elif operation == "multiply":
            result = 1
            for num in numbers:
                result *= num
        else:
            return json.dumps({"error": f"不支持的操作: {operation}"})
        
        return json.dumps({"result": result, "operation": operation, "numbers": numbers})

# ---------- 数据模型 ----------
@dataclass
class ResearchPlan:
    """研究计划结构"""
    title: str
    budget: float
    steps: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "budget": self.budget,
            "steps": self.steps
        }

# ---------- Agent 构建 ----------
def build_research_agent() -> Agent:
    """构建深度研究规划 Agent"""
    calculator = CalculatorTool()
    
    system_prompt = """你是一个深度研究规划专家。你的任务是：
1. 使用计算器工具计算研究预算（例如：基础费用 + 额外费用，或基础费用 × 倍数）
2. 根据计算结果生成结构化的研究计划
3. 输出格式必须为 JSON，包含 title, budget, steps 字段

示例输出：
{
    "title": "AI 伦理研究计划",
    "budget": 15000,
    "steps": ["文献综述", "数据收集", "模型分析", "报告撰写"]
}

请确保：
- 预算必须是数字类型
- 步骤至少包含 3 个具体步骤
- 使用计算器工具进行预算计算"""
    
    return Agent(
        name="research_planner",
        system_prompt=system_prompt,
        tools=[calculator],
        output_format="json"
    )

# ---------- 模型初始化 ----------
def init_model():
    """初始化 LLM 模型（示例使用 mock，实际可替换为真实模型）"""
    # 实际使用时替换为真实模型，例如：
    # from langchain_openai import ChatOpenAI
    # return ChatOpenAI(model="gpt-4", temperature=0)
    
    # 这里使用一个简单的 mock 模型用于演示
    class MockModel:
        def __call__(self, messages):
            # 模拟模型响应
            return {
                "content": json.dumps({
                    "title": "量子计算研究计划",
                    "budget": 25000,
                    "steps": ["文献调研", "算法设计", "仿真实验", "结果分析", "论文撰写"]
                })
            }
    
    return MockModel()

# ---------- 主程序 ----------
def main():
    """单轮示例调用"""
    # 初始化模型
    model = init_model()
    
    # 构建 Agent
    agent = build_research_agent()
    
    # 用户请求
    user_request = "请规划一个关于量子计算的研究计划，预算计算方式：基础费用 20000 加上额外费用 5000"
    
    # 执行 Agent
    try:
        response = agent.run(user_request, model=model)
        
        # 解析输出
        if isinstance(response, str):
            try:
                plan_data = json.loads(response)
            except:
                plan_data = {"raw": response}
        else:
            plan_data = response
        
        # 转换为结构化对象
        plan = ResearchPlan(
            title=plan_data.get("title", "未命名计划"),
            budget=float(plan_data.get("budget", 0)),
            steps=plan_data.get("steps", [])
        )
        
        # 打印结构化输出
        print("=== 研究计划输出 ===")
        print(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False))
        
        # 验证计算器工具是否被调用
        print("\n=== 工具调用记录 ===")
        for call in agent.tool_calls:
            print(f"工具: {call['tool']}, 输入: {call['input']}, 输出: {call['output']}")
            
    except Exception as e:
        print(f"执行出错: {e}")

if __name__ == "__main__":
    main()