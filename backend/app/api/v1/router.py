"""
API 路由聚合
"""
from fastapi import APIRouter

from app.api.v1.endpoints import projects, chat, creation, export, settings

api_router = APIRouter()

# 项目路由
api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["项目管理"]
)

# 对话路由
api_router.include_router(
    chat.router,
    prefix="/projects",
    tags=["需求澄清"]
)

# 创作路由
api_router.include_router(
    creation.router,
    prefix="/projects",
    tags=["剧本创作"]
)

# 导出路由
api_router.include_router(
    export.router,
    prefix="/projects",
    tags=["导出功能"]
)

# 设置路由
api_router.include_router(
    settings.router,
    prefix="/settings",
    tags=["设置"]
)
