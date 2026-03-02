"""
项目管理 API
"""
from typing import List, Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from app.services.project import ProjectService

router = APIRouter()


class ProjectCreateRequest(BaseModel):
    """创建项目请求"""
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")


class ProjectResponse(BaseModel):
    """项目响应"""
    id: str
    name: str
    status: str
    genre: Optional[str] = None
    completeness: int = 0
    created_at: str
    updated_at: str


class ProjectListResponse(BaseModel):
    """项目列表响应"""
    total: int
    page: int
    size: int
    items: List[ProjectResponse]


@router.get("", response_model=dict)
async def list_projects(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选")
):
    """
    获取项目列表

    Args:
        page: 页码，默认1
        size: 每页数量，默认10
        status: 状态筛选 (clarifying/creating/completed)
    """
    projects = ProjectService.list_projects(status=status, page=page, size=size)
    total = ProjectService.get_project_count(status=status)

    # 转换响应格式
    items = []
    for p in projects:
        items.append({
            "id": p["project_id"],
            "name": p["project_name"],
            "status": p["status"],
            "genre": p.get("requirements", {}).get("genre"),
            "completeness": p.get("completeness", 0),
            "created_at": p["created_at"],
            "updated_at": p["updated_at"]
        })

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


@router.post("", response_model=dict)
async def create_project(request: ProjectCreateRequest):
    """
    创建新项目

    Args:
        request: 创建项目请求
    """
    from loguru import logger
    logger.info(f"Creating project with name: {request.name}")

    state = ProjectService.create_project(request.name)
    logger.info(f"Created project: {state['project_id']}")

    return {
        "code": 200,
        "message": "success",
        "data": {
            "id": state["project_id"],
            "name": state["project_name"],
            "status": state["status"],
            "created_at": state["created_at"]
        }
    }


@router.get("/{project_id}", response_model=dict)
async def get_project(project_id: str):
    """
    获取项目详情

    Args:
        project_id: 项目ID
    """
    state = ProjectService.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="项目不存在")

    return {
        "code": 200,
        "message": "success",
        "data": {
            "project_id": state["project_id"],
            "project_name": state["project_name"],
            "status": state["status"],
            "requirements": state.get("requirements", {}),
            "completeness": state.get("completeness", 0),
            "messages": state.get("messages", []),
            "total_episodes": state.get("total_episodes", 80),
            "created_at": state["created_at"],
            "updated_at": state["updated_at"],
            # 创作内容（确保已生成的内容都能被前端获取）
            "story_synopsis": state.get("story_synopsis"),
            "story_title": state.get("story_title"),
            "one_liner": state.get("one_liner"),
            "selling_points": state.get("selling_points", []),
            "character_profiles": state.get("character_profiles", []),
            "relationship_map": state.get("relationship_map"),
            "episode_outlines": state.get("episode_outlines", []),
            "scripts": state.get("scripts", []),
            "creation_progress": state.get("creation_progress"),
            "script_context": state.get("script_context"),
        }
    }


@router.delete("/{project_id}", response_model=dict)
async def delete_project(project_id: str):
    """
    删除项目

    Args:
        project_id: 项目ID
    """
    success = ProjectService.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="项目不存在")

    return {
        "code": 200,
        "message": "success",
        "data": None
    }
