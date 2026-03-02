"""
项目管理服务

使用 SQLite 数据库存储项目数据
"""
from typing import Dict, List, Optional

from loguru import logger

from app.core.state import ScriptState, create_initial_state
from app.models.project import ProjectModel


class ProjectService:
    """项目服务"""

    # 内存缓存（可选，用于提高性能）
    _cache: Dict[str, ScriptState] = {}

    @classmethod
    def create_project(cls, name: str) -> ScriptState:
        """
        创建新项目

        Args:
            name: 项目名称

        Returns:
            ScriptState: 初始状态
        """
        import uuid

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        state = create_initial_state(project_id, name)

        # 保存到数据库
        if ProjectModel.create(state):
            logger.info(f"创建项目: {project_id} - {name}")
            # 更新缓存
            cls._cache[project_id] = state
        else:
            raise Exception("创建项目失败")

        return state

    @classmethod
    def get_project(cls, project_id: str) -> Optional[ScriptState]:
        """
        获取项目

        Args:
            project_id: 项目ID

        Returns:
            Optional[ScriptState]: 项目状态，不存在则返回 None
        """
        # 先查缓存
        if project_id in cls._cache:
            return cls._cache[project_id]

        # 查询数据库
        state = ProjectModel.get_by_id(project_id)
        if state:
            cls._cache[project_id] = state

        return state

    @classmethod
    def update_project(cls, project_id: str, state: ScriptState) -> ScriptState:
        """
        更新项目

        Args:
            project_id: 项目ID
            state: 新状态

        Returns:
            ScriptState: 更新后的状态
        """
        from datetime import datetime

        state["updated_at"] = datetime.now().isoformat()

        # 更新数据库
        if ProjectModel.update(project_id, state):
            logger.debug(f"更新项目: {project_id}")
            # 更新缓存
            cls._cache[project_id] = state
        else:
            raise Exception(f"更新项目失败: {project_id}")

        return state

    @classmethod
    def delete_project(cls, project_id: str) -> bool:
        """
        删除项目

        Args:
            project_id: 项目ID

        Returns:
            bool: 是否删除成功
        """
        if ProjectModel.delete(project_id):
            logger.info(f"删除项目: {project_id}")
            # 清除缓存
            cls._cache.pop(project_id, None)
            return True
        return False

    @classmethod
    def list_projects(
        cls,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 10
    ) -> List[ScriptState]:
        """
        获取项目列表

        Args:
            status: 状态筛选
            page: 页码
            size: 每页数量

        Returns:
            List[ScriptState]: 项目列表
        """
        return ProjectModel.list_all(status=status, page=page, size=size)

    @classmethod
    def get_project_count(cls, status: Optional[str] = None) -> int:
        """
        获取项目数量

        Args:
            status: 状态筛选

        Returns:
            int: 项目数量
        """
        return ProjectModel.count(status=status)

    @classmethod
    def clear_cache(cls) -> None:
        """清除缓存"""
        cls._cache.clear()
