"""
项目数据模型

使用原生 SQLite，不依赖 ORM
"""
import json
from typing import Optional, Dict, Any
from datetime import datetime

from app.core.database import db
from app.core.state import ScriptState, create_initial_state


class ProjectModel:
    """
    项目模型

    提供项目数据的增删改查操作
    """

    @staticmethod
    def create(state: ScriptState) -> bool:
        """
        创建项目

        Args:
            state: 项目状态

        Returns:
            bool: 是否创建成功
        """
        try:
            db.execute(
                """
                INSERT INTO projects (project_id, project_name, status, created_at, updated_at, data)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    state["project_id"],
                    state["project_name"],
                    state["status"],
                    state["created_at"],
                    state["updated_at"],
                    json.dumps(state, ensure_ascii=False, default=str)
                )
            )
            return True
        except Exception as e:
            print(f"创建项目失败: {e}")
            return False

    @staticmethod
    def get_by_id(project_id: str) -> Optional[ScriptState]:
        """
        根据 ID 获取项目

        Args:
            project_id: 项目 ID

        Returns:
            Optional[ScriptState]: 项目状态
        """
        row = db.fetchone(
            "SELECT * FROM projects WHERE project_id = ?",
            (project_id,)
        )

        if row:
            return json.loads(row["data"])
        return None

    @staticmethod
    def update(project_id: str, state: ScriptState) -> bool:
        """
        更新项目

        Args:
            project_id: 项目 ID
            state: 新状态

        Returns:
            bool: 是否更新成功
        """
        try:
            state["updated_at"] = datetime.now().isoformat()
            db.execute(
                """
                UPDATE projects
                SET project_name = ?, status = ?, updated_at = ?, data = ?
                WHERE project_id = ?
                """,
                (
                    state["project_name"],
                    state["status"],
                    state["updated_at"],
                    json.dumps(state, ensure_ascii=False, default=str),
                    project_id
                )
            )
            return True
        except Exception as e:
            print(f"更新项目失败: {e}")
            return False

    @staticmethod
    def delete(project_id: str) -> bool:
        """
        删除项目

        Args:
            project_id: 项目 ID

        Returns:
            bool: 是否删除成功
        """
        try:
            cursor = db.execute(
                "DELETE FROM projects WHERE project_id = ?",
                (project_id,)
            )
            return cursor.rowcount > 0
        except Exception as e:
            print(f"删除项目失败: {e}")
            return False

    @staticmethod
    def list_all(
        status: Optional[str] = None,
        page: int = 1,
        size: int = 10
    ) -> list:
        """
        获取项目列表

        Args:
            status: 状态筛选
            page: 页码
            size: 每页数量

        Returns:
            list: 项目列表
        """
        offset = (page - 1) * size

        if status:
            rows = db.fetchall(
                """
                SELECT data FROM projects
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (status, size, offset)
            )
        else:
            rows = db.fetchall(
                """
                SELECT data FROM projects
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (size, offset)
            )

        return [json.loads(row["data"]) for row in rows]

    @staticmethod
    def count(status: Optional[str] = None) -> int:
        """
        获取项目数量

        Args:
            status: 状态筛选

        Returns:
            int: 项目数量
        """
        if status:
            row = db.fetchone(
                "SELECT COUNT(*) as count FROM projects WHERE status = ?",
                (status,)
            )
        else:
            row = db.fetchone(
                "SELECT COUNT(*) as count FROM projects"
            )

        return row["count"] if row else 0
