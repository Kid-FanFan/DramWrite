"""
剧本创作子图 (CreateGraph)

工作流（线性流水线）：
需求锁定 → 故事梗概 → 人物小传 → 分集大纲 → 剧本正文 → 质量检查 → 完成

支持单步执行和批量执行两种模式
"""
from typing import Literal

from langgraph.graph import StateGraph, END

from app.core.state import ScriptState
from app.agents.create.nodes import (
    synopsis_creator_node,
    character_creator_node,
    outline_creator_node,
    script_writer_node,
    quality_checker_node
)


def should_continue_creation(state: ScriptState) -> Literal[
    "synopsis", "characters", "outline", "script", "quality_check", "complete"
]:
    """
    判断当前创作阶段

    根据 creation_progress.step 决定下一步
    """
    progress = state.get("creation_progress", {})
    current_step = progress.get("step", "start")

    # 定义流程
    flow = {
        "start": "synopsis",
        "synopsis": "characters",
        "characters": "outline",
        "outline": "script",
        "script": "quality_check",
        "quality_check": "complete"
    }

    return flow.get(current_step, "complete")


def create_create_graph() -> StateGraph:
    """
    创建剧本创作子图

    Returns:
        StateGraph: 配置好的状态图
    """
    # 创建图
    workflow = StateGraph(ScriptState)

    # 添加节点
    workflow.add_node("synopsis_creator", synopsis_creator_node)
    workflow.add_node("character_creator", character_creator_node)
    workflow.add_node("outline_creator", outline_creator_node)
    workflow.add_node("script_writer", script_writer_node)
    workflow.add_node("quality_checker", quality_checker_node)

    # 设置入口点
    workflow.set_entry_point("synopsis_creator")

    # 线性流水线边
    workflow.add_edge("synopsis_creator", "character_creator")
    workflow.add_edge("character_creator", "outline_creator")
    workflow.add_edge("outline_creator", "script_writer")
    workflow.add_edge("script_writer", "quality_checker")
    workflow.add_edge("quality_checker", END)

    return workflow


# 编译图
create_graph = create_create_graph()
create_workflow = create_graph.compile()


async def run_creation_workflow(state: ScriptState) -> ScriptState:
    """
    运行完整的剧本创作流水线

    Args:
        state: 当前状态（需求已锁定）

    Returns:
        完成后的状态
    """
    result = await create_workflow.ainvoke(state)
    return result


async def run_creation_step(state: ScriptState, step: str) -> ScriptState:
    """
    运行单步创作

    Args:
        state: 当前状态
        step: 步骤名称 (synopsis/characters/outline/script/quality_check)

    Returns:
        执行步骤后的状态
    """
    nodes = {
        "synopsis": synopsis_creator_node,
        "characters": character_creator_node,
        "outline": outline_creator_node,
        "script": script_writer_node,
        "quality_check": quality_checker_node
    }

    node = nodes.get(step)
    if not node:
        raise ValueError(f"未知的创作步骤: {step}")

    # 调用异步节点
    return await node(state)
