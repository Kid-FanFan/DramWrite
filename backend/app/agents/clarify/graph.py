"""
需求澄清子图 (ClarifyGraph)

工作流：
1. 用户输入 -> 意图分析节点
2. 判断是否继续澄清：
   - 需求完整度 >= 80% -> 生成需求确认书
   - 用户请求帮助 -> 生成建议选项
   - 否则 -> 生成引导问题
3. 循环直到需求确认
"""
from typing import Literal

from langgraph.graph import StateGraph, END

from app.core.state import ScriptState, check_requirement_completeness
from app.agents.clarify.nodes import (
    intent_analyzer_node,
    guidance_generator_node,
    options_generator_node,
    summary_generator_node
)


def should_continue_clarify(state: ScriptState) -> Literal["continue", "generate_summary", "complete", "llm_not_configured"]:
    """
    判断是否继续需求澄清

    Returns:
        continue: 继续收集需求
        generate_summary: 生成需求确认书
        complete: 需求已锁定，结束澄清
        llm_not_configured: LLM未配置，终止流程
    """
    # LLM 未配置
    if state.get("llm_not_configured"):
        return "llm_not_configured"

    # 需求已锁定
    if state.get("requirements_locked"):
        return "complete"

    # 检查是否需要生成确认书
    completeness = state.get("completeness", 0)
    showed_summary = state.get("showed_summary", False)

    if completeness >= 80 and not showed_summary:
        return "generate_summary"

    return "continue"


def should_generate_options(state: ScriptState) -> Literal["options", "guidance"]:
    """
    判断是否生成选项或引导问题
    """
    if state.get("need_options"):
        return "options"
    return "guidance"


def create_clarify_graph() -> StateGraph:
    """
    创建需求澄清子图

    Returns:
        StateGraph: 配置好的状态图
    """
    # 创建图
    workflow = StateGraph(ScriptState)

    # 添加节点
    workflow.add_node("intent_analyzer", intent_analyzer_node)
    workflow.add_node("guidance_generator", guidance_generator_node)
    workflow.add_node("options_generator", options_generator_node)
    workflow.add_node("summary_generator", summary_generator_node)

    # 设置入口点
    workflow.set_entry_point("intent_analyzer")

    # 意图分析后的条件分支
    workflow.add_conditional_edges(
        "intent_analyzer",
        should_continue_clarify,
        {
            "continue": "guidance_generator",
            "generate_summary": "summary_generator",
            "complete": END,
            "llm_not_configured": END  # LLM未配置，直接结束
        }
    )

    # 引导生成器的条件分支
    workflow.add_conditional_edges(
        "guidance_generator",
        should_generate_options,
        {
            "options": "options_generator",
            "guidance": END  # 等待用户输入
        }
    )

    # 选项生成器结束
    workflow.add_edge("options_generator", END)

    # 确认书生成器结束（等待用户确认）
    workflow.add_edge("summary_generator", END)

    return workflow


# 编译图
clarify_graph = create_clarify_graph()
clarify_workflow = clarify_graph.compile()


async def run_clarify_step(state: ScriptState) -> ScriptState:
    """
    运行需求澄清单步

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    # 执行一步工作流
    result = await clarify_workflow.ainvoke(state)
    return result
