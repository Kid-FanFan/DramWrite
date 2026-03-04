"""
需求澄清子图 (ClarifyGraph)

工作流（V1.2更新）：
1. 用户输入 -> 意图分析节点
2. 根据意图类型路由：
   - QUESTION/ANSWER/CHAT -> 统一响应生成节点
   - REQUEST_SUGGESTION -> 选项生成节点
   - AUTO_FILL -> 自动填充处理
   - CONFIRM_START -> 检查完整度，生成确认书或继续
   - MODIFY -> 更新需求 -> 响应生成节点
3. 循环直到需求确认
"""
from typing import Literal

from langgraph.graph import StateGraph, END

from app.core.state import ScriptState, check_requirement_completeness
from app.agents.clarify.nodes import (
    intent_analyzer_node,
    response_generator_node,
    guidance_generator_node,
    options_generator_node,
    summary_generator_node
)


def should_continue_clarify(state: ScriptState) -> Literal["response", "options", "generate_summary", "complete", "llm_not_configured"]:
    """
    判断是否继续需求澄清

    Returns:
        response: 使用统一响应生成节点
        options: 生成建议选项
        generate_summary: 生成需求确认书
        complete: 需求已锁定，结束澄清
        llm_not_configured: LLM未配置，终止流程
    """
    from loguru import logger

    # LLM 未配置
    if state.get("llm_not_configured"):
        logger.info("🔀 [路由] -> llm_not_configured (LLM未配置)")
        return "llm_not_configured"

    # 需求已锁定
    if state.get("requirements_locked"):
        logger.info("🔀 [路由] -> complete (需求已锁定)")
        return "complete"

    # 检查是否需要生成确认书
    completeness = state.get("completeness", 0)
    showed_summary = state.get("showed_summary", False)

    if completeness >= 80 and not showed_summary:
        logger.info(f"🔀 [路由] -> generate_summary (完整度{completeness}%>=80%)")
        return "generate_summary"

    # 根据意图类型路由
    intent = state.get("last_intent", "ANSWER")

    # 请求建议 -> 选项生成
    if intent == "REQUEST_SUGGESTION":
        logger.info(f"🔀 [路由] -> options (意图={intent})")
        return "options"

    # 其他意图 -> 统一响应生成
    logger.info(f"🔀 [路由] -> response (意图={intent})")
    return "response"


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
    workflow.add_node("response_generator", response_generator_node)
    workflow.add_node("options_generator", options_generator_node)
    workflow.add_node("summary_generator", summary_generator_node)

    # 设置入口点
    workflow.set_entry_point("intent_analyzer")

    # 意图分析后的条件分支
    workflow.add_conditional_edges(
        "intent_analyzer",
        should_continue_clarify,
        {
            "response": "response_generator",
            "options": "options_generator",
            "generate_summary": "summary_generator",
            "complete": END,
            "llm_not_configured": END  # LLM未配置，直接结束
        }
    )

    # 响应生成器结束（等待用户输入）
    workflow.add_edge("response_generator", END)

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
