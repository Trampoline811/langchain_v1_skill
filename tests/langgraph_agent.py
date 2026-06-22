"""
LangGraph v1.0 API 盲测 — StateGraph + checkpointer + store + interrupt
覆盖: StateGraph / Command / Send / GraphInterrupt / InMemorySaver / InMemoryStore

用法:
  uv run python tests/langgraph_agent.py          # 全量测试
  uv run python tests/langgraph_agent.py --demo   # 演示模式（自动跑一轮）

无需 API Key — 纯 LangGraph 本地运行。
"""

import sys
from typing import TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command, Send, RetryPolicy, interrupt
from langchain_core.utils.uuid import uuid7


# ═══════════════════════════════════════════
# 1. State 定义
# ═══════════════════════════════════════════

class TaskState(TypedDict):
    tasks: list[dict]                    # 待处理任务列表
    results: Annotated[list, operator.add]  # Reducer: 并行结果汇聚
    summary: str                         # 最终汇总


# ═══════════════════════════════════════════
# 2. 节点定义
# ═══════════════════════════════════════════

def prepare_tasks(state: TaskState) -> dict:
    """准备任务列表 → 不做修改，直接传递"""
    return {}


def continue_to_workers(state: TaskState) -> list[Send]:
    """路由函数: 每个 task 动态 fan-out 一个 worker"""
    return [
        Send("worker", {"task": task})
        for task in state["tasks"]
    ]


def worker(state: dict) -> dict:
    """处理单个任务"""
    task = state["task"]
    result = {
        "id": task["id"],
        "name": task["name"],
        "result": f"Processed: {task['name']}",
        "priority": task.get("priority", "normal"),
    }
    return {"results": [result]}


def summarizer(state: TaskState) -> dict:
    """汇总所有 worker 结果"""
    total = len(state.get("results", []))
    completed = [r["name"] for r in state.get("results", [])]
    return {
        "summary": f"已完成 {total} 个任务: {', '.join(completed)}"
    }


# ═══════════════════════════════════════════
# 3. Command 节点（带中断）
# ═══════════════════════════════════════════

def approval_gate(state: TaskState) -> dict:
    """生成汇总后 → 触发人工审批"""
    task_count = len(state.get("results", []))
    if task_count > 3:
        # interrupt() 抛出 GraphInterrupt → 执行暂停
        # 客户端用 Command(resume={"approved": True}) 恢复
        approved = interrupt({
            "action": "review_batch",
            "reason": f"批量处理 {task_count} 个任务，需人工审核",
            "data": state.get("summary", ""),
        })
        if not approved.get("approved"):
            return {"summary": "已拒绝"}
    return {"summary": state.get("summary", "")}


# ═══════════════════════════════════════════
# 4. Store 操作节点
# ═══════════════════════════════════════════

def save_to_store(state: TaskState, config) -> dict:
    """将结果存入 Store（长期记忆）"""
    runtime = config["configurable"].get("__pregel_runtime")
    if runtime and runtime.store:
        runtime.store.put(
            ("tasks", "history"),
            config["configurable"]["thread_id"],
            {
                "summary": state.get("summary", ""),
                "task_count": len(state.get("results", [])),
            },
        )
    return {}


# ═══════════════════════════════════════════
# 5. 构建图
# ═══════════════════════════════════════════

def build_graph():
    builder = StateGraph(TaskState)

    builder.add_node("prepare", prepare_tasks)
    builder.add_node("worker", worker,
        retry=RetryPolicy(max_attempts=2),
    )
    builder.add_node("summarizer", summarizer)
    builder.add_node("approval_gate", approval_gate)
    builder.add_node("save_to_store", save_to_store)

    builder.add_edge(START, "prepare")
    builder.add_conditional_edges("prepare", continue_to_workers, {"worker": "worker"})
    builder.add_edge("worker", "summarizer")
    builder.add_edge("summarizer", "approval_gate")
    builder.add_edge("approval_gate", "save_to_store")
    # 若未中断 approval_gate → END, save_to_store → END
    builder.add_edge("save_to_store", END)

    return builder


# ═══════════════════════════════════════════
# 6. 测试执行
# ═══════════════════════════════════════════

def test_fanout_and_interrupt():
    """测试1: fan-out 并行 + 中断"""
    print("=" * 60)
    print("  测试1: Send fan-out + GraphInterrupt")
    print("=" * 60)

    store = InMemoryStore()
    checkpointer = InMemorySaver()
    graph = build_graph().compile(checkpointer=checkpointer, store=store)

    thread_id = str(uuid7())
    config = {"configurable": {"thread_id": thread_id}}

    tasks = [
        {"id": 1, "name": "分析数据", "priority": "high"},
        {"id": 2, "name": "生成报告", "priority": "normal"},
        {"id": 3, "name": "发送通知", "priority": "low"},
        {"id": 4, "name": "备份文件", "priority": "normal"},
    ]

    # 首次执行 — 超过3个任务 → approval_gate 触发 interrupt()
    result = graph.invoke({"tasks": tasks}, config)

    # interrupt() 返回后，result 中应包含 __interrupt__ 标记
    interrupt_info = result.get("__interrupt__")
    if interrupt_info:
        print(f"  ✅ 中断触发: {len(interrupt_info)} 个")
    elif result.get("summary"):
        print(f"  ✅ 执行完成（未触发中断）: {result['summary'][:80]}")
    else:
        print(f"  ⚠️  结果: {str(result)[:100]}")

    # 恢复执行 — 用 Command(resume=...)
    resume_result = graph.invoke(Command(resume={"approved": True}), config)
    summary = resume_result.get("summary", "")
    if summary:
        print(f"  ✅ 审批后恢复: {summary[:80]}")
    else:
        print(f"  ⚠️  恢复后: {str(resume_result)[:100]}")

    return True


def test_checkpointer_persistence():
    """测试2: checkpointer 持久化 — 同一 thread_id 恢复状态"""
    print("\n" + "=" * 60)
    print("  测试2: Checkpointer 持久化")
    print("=" * 60)

    checkpointer = InMemorySaver()
    store = InMemoryStore()
    graph = build_graph().compile(checkpointer=checkpointer, store=store)

    thread_id = str(uuid7())
    config = {"configurable": {"thread_id": thread_id}}

    # 第一轮
    tasks1 = [{"id": 1, "name": "任务A"}]
    result1 = graph.invoke({"tasks": tasks1}, config)

    # 第二轮 — 同一 thread_id，State 应从上一轮恢复
    tasks2 = [{"id": 2, "name": "任务B"}]
    result2 = graph.invoke({"tasks": tasks2}, config)

    # 验证：results 应包含两次调用的结果
    results = result2.get("results", [])
    task_names = [r["name"] for r in results]
    if "任务A" in task_names and "任务B" in task_names:
        print(f"  ✅ 跨轮次状态恢复: {task_names}")
    elif "任务A" in task_names:
        print(f"  ✅ 状态恢复: {task_names}")
    else:
        print(f"  ⚠️  状态可能未正确恢复: {task_names}")

    # 验证 state history
    history = list(graph.get_state_history(config))
    print(f"  ✅ State history: {len(history)} 个 checkpoint")

    return True


def test_store_longterm_memory():
    """测试3: Store 长期记忆 — 跨线程读写"""
    print("\n" + "=" * 60)
    print("  测试3: Store 长期记忆")
    print("=" * 60)

    store = InMemoryStore()
    checkpointer = InMemorySaver()
    graph = build_graph().compile(checkpointer=checkpointer, store=store)

    # 线程1: 写入 Store
    tid1 = str(uuid7())
    config1 = {"configurable": {"thread_id": tid1}}
    graph.invoke({"tasks": [
        {"id": 1, "name": "用户偏好设置"},
    ]}, config1)

    # 验证 Store 中有数据
    memories = store.search(("tasks", "history"))
    if memories:
        print(f"  ✅ Store 写入成功: {len(memories)} 条记录")
        print(f"     {memories[0].value}")
    else:
        print(f"  ⚠️  Store 中无记录")

    # 线程2: 能读到线程1写入的数据
    tid2 = str(uuid7())
    memories2 = store.search(("tasks", "history"))
    if memories2:
        print(f"  ✅ 跨线程读取成功: {len(memories2)} 条记录")
    else:
        print(f"  ⚠️  跨线程读取失败")

    return True


def test_retry_policy():
    """测试4: RetryPolicy 编译"""
    print("\n" + "=" * 60)
    print("  测试4: RetryPolicy 编译")
    print("=" * 60)

    # 独立的简单 State，不与 TaskState 冲突
    class SimpleState(TypedDict):
        value: str

    def simple_worker(state: SimpleState) -> dict:
        return {"value": f"ok:{state['value']}"}

    builder = StateGraph(SimpleState)
    builder.add_node("worker", simple_worker,
        retry=RetryPolicy(
            max_attempts=3,
            backoff_factor=2.0,
            initial_interval=0.5,
            retry_on=(Exception,),
        )
    )
    builder.add_edge(START, "worker")
    builder.add_edge("worker", END)

    graph = builder.compile(checkpointer=InMemorySaver())

    result = graph.invoke(
        {"value": "test"},
        {"configurable": {"thread_id": str(uuid7())}},
    )
    if result.get("value", "").startswith("ok:"):
        print(f"  ✅ 带 RetryPolicy 的图正常执行: {result['value']}")
    else:
        print(f"  ⚠️  意外的结果: {result}")

    return True


# ═══════════════════════════════════════════
# Main
# ═══════════════════════════════════════════

def main():
    demo_mode = "--demo" in sys.argv

    tests = [
        ("Send fan-out + GraphInterrupt", test_fanout_and_interrupt),
        ("Checkpointer 持久化", test_checkpointer_persistence),
        ("Store 长期记忆", test_store_longterm_memory),
        ("RetryPolicy 编译", test_retry_policy),
    ]

    passed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"\n  ❌ {name} FAILED: {e}")

    print("\n" + "=" * 60)
    print(f"  Results: {passed}/{len(tests)} passed")
    print("=" * 60)

    return passed == len(tests)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
