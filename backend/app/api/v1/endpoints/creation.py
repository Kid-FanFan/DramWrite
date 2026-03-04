"""
剧本创作 API
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from loguru import logger

from app.services.project import ProjectService
from app.agents.create.graph import run_creation_workflow, run_creation_step
from app.agents.create.nodes import (
    synopsis_creator_node,
    character_creator_node,
    outline_creator_node
)

router = APIRouter()

# 存储正在运行的创作任务
_creation_tasks: dict[str, asyncio.Task] = {}

# V1.2新增：存储创作调试日志（内存存储，每个项目最多保留100条）
_creation_logs: dict[str, list] = {}


def add_creation_log(project_id: str, message: str):
    """添加创作日志"""
    import time
    if project_id not in _creation_logs:
        _creation_logs[project_id] = []

    timestamp = time.strftime("%H:%M:%S")
    _creation_logs[project_id].append(f"[{timestamp}] {message}")

    # 只保留最近100条
    if len(_creation_logs[project_id]) > 100:
        _creation_logs[project_id] = _creation_logs[project_id][-100:]


def get_creation_logs(project_id: str) -> list:
    """获取创作日志"""
    return _creation_logs.get(project_id, [])


class CreationProgressResponse(BaseModel):
    """创作进度响应"""
    status: str
    current_step: str
    percentage: int
    completed_episodes: int
    total_episodes: int
    estimated_remaining_time: int


class RegenerateRequest(BaseModel):
    """重新生成请求"""
    content_type: str = Field(..., description="内容类型: synopsis/characters/outline/script")
    episode_number: Optional[int] = Field(None, description="集数（仅对 script 有效）")


async def _run_creation_background(project_id: str, project: dict):
    """
    后台执行创作流程

    异步执行创作流水线，定期更新项目状态，使前端可以通过轮询获取进度
    """
    try:
        logger.info(f"开始后台创作流程: {project_id}")

        # 初始化进度
        total_episodes = project.get("total_episodes", 80)
        project["creation_progress"] = {
            "step": "synopsis",
            "status": "in_progress",
            "percentage": 0,
            "completed_episodes": 0,
            "total_episodes": total_episodes
        }
        project["status"] = "creating"
        ProjectService.update_project(project_id, project)

        # V1.2新增：初始化调试日志
        _creation_logs[project_id] = []
        add_creation_log(project_id, f"🎬 创作流程启动 - 总集数: {total_episodes}")

        # 获取需求确认书信息用于日志
        confirmation = project.get("requirement_confirmation", {})
        add_creation_log(project_id, f"📋 需求确认书: {confirmation.get('title', '未命名')}")
        add_creation_log(project_id, f"🎭 题材: {confirmation.get('genre', '未设定')}")
        add_creation_log(project_id, f"💖 感情线: {'有' if confirmation.get('romance_line_summary') else '无'}")
        add_creation_log(project_id, f"🌍 世界观: {'有' if confirmation.get('world_building_summary') else '无'}")

        # 第1步：生成故事梗概
        logger.info(f"[{project_id}] 开始生成故事梗概")
        add_creation_log(project_id, "▶️ 步骤1: 故事梗概生成...")
        project["creation_progress"]["step"] = "synopsis"
        project["creation_progress"]["percentage"] = 5
        ProjectService.update_project(project_id, project)

        result = await synopsis_creator_node(project)
        project.update(result)
        project["creation_progress"]["step"] = "synopsis"
        project["creation_progress"]["percentage"] = 10
        ProjectService.update_project(project_id, project)
        logger.info(f"[{project_id}] 故事梗概生成完成")
        add_creation_log(project_id, f"✅ 故事梗概完成 - 剧名: {project.get('story_title', '未命名')[:30]}...")
        add_creation_log(project_id, f"   一句话: {project.get('one_liner', '')[:40]}...")

        # 检查是否使用了需求确认书的信息
        confirmation = project.get("requirement_confirmation", {})
        if confirmation.get("title"):
            add_creation_log(project_id, f"   使用需求确认书剧名: {confirmation['title']}")
        else:
            add_creation_log(project_id, "   未找到需求确认书剧名，使用AI生成")

        # 第2步：生成人物小传
        logger.info(f"[{project_id}] 开始生成人物小传")
        project["creation_progress"]["step"] = "characters"
        project["creation_progress"]["percentage"] = 15
        ProjectService.update_project(project_id, project)

        result = await character_creator_node(project)
        project.update(result)
        project["creation_progress"]["step"] = "characters"
        project["creation_progress"]["percentage"] = 20
        ProjectService.update_project(project_id, project)
        logger.info(f"[{project_id}] 人物小传生成完成")
        chars = project.get("character_profiles", [])
        add_creation_log(project_id, f"✅ 人物小传完成 - 共{len(chars)}个人物")
        for char in chars[:3]:  # 显示前3个人物
            add_creation_log(project_id, f"   • {char.get('name', '未知')} ({char.get('role', '角色')}) - {char.get('personality', '无性格')[:20]}...")


        # 第3步：生成分集大纲
        logger.info(f"[{project_id}] 开始生成分集大纲")
        project["creation_progress"]["step"] = "outline"
        project["creation_progress"]["percentage"] = 25
        ProjectService.update_project(project_id, project)

        result = await outline_creator_node(project)
        project.update(result)
        project["creation_progress"]["step"] = "outline"
        project["creation_progress"]["percentage"] = 30
        ProjectService.update_project(project_id, project)
        logger.info(f"[{project_id}] 分集大纲生成完成")
        outlines = project.get("episode_outlines", [])
        add_creation_log(project_id, f"✅ 分集大纲完成 - 共{len(outlines)}集")
        # 统计付费卡点
        checkpoints = [o for o in outlines if o.get("is_checkpoint")]
        add_creation_log(project_id, f"   付费卡点: 第{', '.join([str(o.get('episode_number')) for o in checkpoints[:5]])}...等{len(checkpoints)}个")

        # 第4步：生成剧本正文（增强上下文管理版）
        logger.info(f"[{project_id}] 开始生成剧本正文（带上下文管理）")
        add_creation_log(project_id, "▶️ 步骤4: 剧本正文生成...")

        # 初始化剧本上下文
        from app.agents.create.nodes import initialize_script_context
        if not project.get("script_context"):
            project = initialize_script_context(project)
            logger.info(f"[{project_id}] 剧本上下文已初始化")
            add_creation_log(project_id, "📝 剧本上下文已初始化")

        # 安全地获取数据（防止None值）
        outlines = project.get("episode_outlines") or []
        scripts = project.get("scripts") or []
        total_episodes = len(outlines)

        if not outlines:
            logger.error(f"[{project_id}] 分集大纲为空，无法生成剧本")
            raise ValueError("分集大纲为空，无法生成剧本")

        logger.info(f"[{project_id}] 大纲集数: {total_episodes}, 已有剧本: {len(scripts)}集")
        add_creation_log(project_id, f"🎯 开始生成剧本 - 共{total_episodes}集，批次大小: 5集")

        # 批量生成剧本，但每5集保存一次状态
        batch_size = 5
        start_episode = len(scripts)  # 使用安全处理后的 scripts 变量

        for batch_start in range(start_episode, total_episodes, batch_size):
            batch_end = min(batch_start + batch_size, total_episodes)

            # 检查是否已暂停
            current_project = ProjectService.get_project(project_id)
            if current_project and current_project.get("status") == "paused":
                logger.info(f"[{project_id}] 创作已暂停（在第{batch_start}集后）")
                add_creation_log(project_id, f"⏸️ 创作已暂停（在第{batch_start}集后）")
                return

            # 生成本批次剧本
            from app.agents.create.nodes import script_writer_node
            result = await script_writer_node(project, batch_end=batch_end)

            # 更新项目状态
            project.update(result)

            # 获取实际完成的集数
            completed_count = len(project.get("scripts", []))
            progress_percent = 30 + int(completed_count / total_episodes * 60)

            project["creation_progress"]["step"] = "script"
            project["creation_progress"]["percentage"] = progress_percent
            project["creation_progress"]["completed_episodes"] = completed_count

            # 保存状态到数据库
            ProjectService.update_project(project_id, project)

            logger.info(f"[{project_id}] 进度：{completed_count}/{total_episodes}集 ({progress_percent}%)")
            script_ctx = project.get('script_context') or {}
            pending_hooks = script_ctx.get('pending_hooks', [])
            logger.info(f"[{project_id}] 当前上下文 - 待回收悬念：{len(pending_hooks)}个")

            # V1.2新增：添加详细日志
            add_creation_log(project_id, f"📝 剧本进度: {completed_count}/{total_episodes}集 ({progress_percent}%)")
            if pending_hooks:
                add_creation_log(project_id, f"   待回收悬念: {len(pending_hooks)}个")
            # 记录本批次生成的剧集
            batch_scripts = project.get("scripts", [])[batch_start:batch_end]
            for script in batch_scripts:
                ep_num = script.get("episode_number", 0)
                word_count = script.get("word_count", 0)
                is_checkpoint = "【付费卡点" in script.get("content", "")
                cp_mark = " 💰" if is_checkpoint else ""
                add_creation_log(project_id, f"   第{ep_num}集: {word_count}字{cp_mark}")

        # 第5步：质量检查
        logger.info(f"[{project_id}] 开始质量检查")
        add_creation_log(project_id, "▶️ 步骤5: 质量检查...")
        project["creation_progress"]["step"] = "quality_check"
        project["creation_progress"]["percentage"] = 95
        ProjectService.update_project(project_id, project)

        from app.agents.create.nodes import quality_checker_node
        result = quality_checker_node(project)
        project.update(result)

        # 统计质量检查结果
        scripts = project.get("scripts", [])
        passed_count = sum(1 for s in scripts if s.get("quality_report", {}).get("pass", False))
        add_creation_log(project_id, f"✅ 质量检查完成 - {passed_count}/{len(scripts)}集通过")

        # 完成
        project["status"] = "completed"
        project["creation_progress"]["step"] = "completed"
        project["creation_progress"]["status"] = "completed"
        project["creation_progress"]["percentage"] = 100
        ProjectService.update_project(project_id, project)

        logger.info(f"[{project_id}] 创作流程完成")
        add_creation_log(project_id, "🎉 创作流程全部完成!")
        add_creation_log(project_id, f"📊 总计: {len(scripts)}集剧本, {sum(s.get('word_count', 0) for s in scripts)}字")

    except Exception as e:
        logger.error(f"[{project_id}] 创作流程失败: {e}")
        add_creation_log(project_id, f"❌ 创作流程失败: {str(e)[:100]}")
        project["status"] = "failed"
        project["creation_progress"]["status"] = "failed"
        project["creation_progress"]["error"] = str(e)
        ProjectService.update_project(project_id, project)
    finally:
        # 清理任务引用
        if project_id in _creation_tasks:
            del _creation_tasks[project_id]


@router.post("/{project_id}/create/start", response_model=dict)
async def start_creation(project_id: str):
    """
    开始剧本创作

    异步启动创作流程，立即返回，前端通过轮询获取进度

    Args:
        project_id: 项目ID
    """
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if project.get("status") not in ["creating", "locked"]:
        raise HTTPException(status_code=400, detail="项目不在创作阶段")

    # 如果已经有正在运行的任务，先取消
    if project_id in _creation_tasks:
        _creation_tasks[project_id].cancel()
        try:
            await _creation_tasks[project_id]
        except asyncio.CancelledError:
            pass
        del _creation_tasks[project_id]

    try:
        # 确保 total_episodes 已设置（从需求中读取）
        if "total_episodes" not in project or not project.get("total_episodes"):
            requirements = project.get("requirements", {})
            episodes = requirements.get("episodes", 80)
            try:
                project["total_episodes"] = int(episodes) if episodes else 80
            except (ValueError, TypeError):
                project["total_episodes"] = 80

        # 设置初始状态
        project["status"] = "creating"
        project["creation_progress"] = {
            "step": "synopsis",
            "status": "pending",
            "percentage": 0,
            "completed_episodes": 0,
            "total_episodes": project["total_episodes"]
        }
        ProjectService.update_project(project_id, project)

        # 在后台启动创作流程
        task = asyncio.create_task(_run_creation_background(project_id, project))
        _creation_tasks[project_id] = task

        logger.info(f"创作任务已启动: {project_id}")

        return {
            "code": 200,
            "message": "success",
            "data": {
                "status": "creating",
                "estimated_time": 1800
            }
        }
    except Exception as e:
        logger.error(f"启动创作失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动创作失败: {str(e)}")


@router.post("/{project_id}/create/pause", response_model=dict)
async def pause_creation(project_id: str):
    """
    暂停创作

    Args:
        project_id: 项目ID
    """
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    project["status"] = "paused"
    ProjectService.update_project(project_id, project)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "status": "paused"
        }
    }


@router.post("/{project_id}/create/resume", response_model=dict)
async def resume_creation(project_id: str):
    """
    继续创作

    Args:
        project_id: 项目ID
    """
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    project["status"] = "creating"
    ProjectService.update_project(project_id, project)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "status": "creating"
        }
    }


@router.get("/{project_id}/progress", response_model=dict)
async def get_progress(project_id: str):
    """
    获取创作进度

    Args:
        project_id: 项目ID
    """
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    progress = project.get("creation_progress") or {}

    return {
        "code": 200,
        "message": "success",
        "data": {
            "status": project.get("status"),
            "current_step": progress.get("step", "start"),
            "percentage": progress.get("percentage", 0),
            "steps": [
                {"name": "synopsis", "status": _get_step_status(progress, "synopsis"), "percentage": 10},
                {"name": "characters", "status": _get_step_status(progress, "characters"), "percentage": 20},
                {"name": "outline", "status": _get_step_status(progress, "outline"), "percentage": 30},
                {"name": "script", "status": _get_step_status(progress, "script"), "percentage": 60},
                {"name": "quality_check", "status": _get_step_status(progress, "quality_check"), "percentage": 10}
            ],
            "completed_episodes": progress.get("completed_episodes", 0),
            "total_episodes": progress.get("total_episodes", 80),
            "estimated_remaining_time": _estimate_remaining_time(progress)
        }
    }


def _get_step_status(progress: dict, step_name: str) -> str:
    """获取步骤状态"""
    current_step = progress.get("step", "")
    if current_step == step_name:
        return "in_progress"
    elif _step_completed(current_step, step_name):
        return "completed"
    return "pending"


def _step_completed(current: str, target: str) -> bool:
    """判断步骤是否已完成"""
    order = ["synopsis", "characters", "outline", "script", "quality_check"]
    if current not in order or target not in order:
        return False
    return order.index(current) > order.index(target)


def _estimate_remaining_time(progress: dict) -> int:
    """估算剩余时间（秒）"""
    percentage = progress.get("percentage", 0)
    if percentage >= 100:
        return 0
    # 假设总共需要30分钟
    total_seconds = 30 * 60
    return int((100 - percentage) / 100 * total_seconds)


@router.post("/{project_id}/create/regenerate", response_model=dict)
async def regenerate_content(
    project_id: str,
    request: RegenerateRequest
):
    """
    重新生成内容

    Args:
        project_id: 项目ID
        content_type: 内容类型
        episode_number: 集数（仅对 script 有效）
    """
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    try:
        # 确保 total_episodes 已设置（从需求中读取）
        if "total_episodes" not in project or not project.get("total_episodes"):
            requirements = project.get("requirements", {})
            episodes = requirements.get("episodes", 80)
            try:
                project["total_episodes"] = int(episodes) if episodes else 80
            except (ValueError, TypeError):
                project["total_episodes"] = 80

        content_type = request.content_type
        if content_type == "synopsis":
            result = await synopsis_creator_node(project)
        elif content_type == "characters":
            result = await character_creator_node(project)
        elif content_type == "outline":
            result = await outline_creator_node(project)
        else:
            raise HTTPException(status_code=400, detail="不支持的内容类型")

        ProjectService.update_project(project_id, result)

        return {
            "code": 200,
            "message": "success",
            "data": {
                "status": "completed",
                "content_type": content_type
            }
        }
    except Exception as e:
        logger.error(f"重新生成失败: {e}")
        raise HTTPException(status_code=500, detail="重新生成失败")


# 内容获取接口
@router.get("/{project_id}/synopsis", response_model=dict)
async def get_synopsis(project_id: str):
    """获取故事梗概"""
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    return {
        "code": 200,
        "message": "success",
        "data": {
            "title": project.get("story_title", ""),
            "one_liner": project.get("one_liner", ""),
            "synopsis": project.get("story_synopsis", ""),
            "selling_points": project.get("selling_points", [])
        }
    }


@router.get("/{project_id}/characters", response_model=dict)
async def get_characters(project_id: str):
    """获取人物小传"""
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    return {
        "code": 200,
        "message": "success",
        "data": {
            "characters": project.get("character_profiles", []),
            "relationship_map": project.get("relationship_map", "")
        }
    }


@router.get("/{project_id}/outlines", response_model=dict)
async def get_outlines(
    project_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    """获取分集大纲"""
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    outlines = project.get("episode_outlines", [])
    total = len(outlines)

    # 分页
    start = (page - 1) * size
    end = start + size
    items = outlines[start:end]

    return {
        "code": 200,
        "message": "success",
        "data": {
            "total": total,
            "page": page,
            "size": size,
            "items": items
        }
    }


@router.get("/{project_id}/episodes/{episode_number}", response_model=dict)
async def get_episode(project_id: str, episode_number: int):
    """获取单集剧本"""
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    scripts = project.get("scripts", [])
    episode = None
    for script in scripts:
        if script.get("episode_number") == episode_number:
            episode = script
            break

    if not episode:
        raise HTTPException(status_code=404, detail="剧集不存在")

    return {
        "code": 200,
        "message": "success",
        "data": episode
    }


@router.get("/{project_id}/create/logs", response_model=dict)
async def api_get_creation_logs(project_id: str):
    """
    获取创作调试日志

    Args:
        project_id: 项目ID
    """
    project = ProjectService.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    logs = get_creation_logs(project_id)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "logs": logs,
            "count": len(logs)
        }
    }
