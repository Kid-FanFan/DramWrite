"""
配置数据模型

存储应用配置，如 LLM 设置
"""
import json
from typing import Optional, Dict, Any

from app.core.database import db


class ConfigModel:
    """
    配置模型

    键值对存储配置数据
    """

    @staticmethod
    def init_table() -> None:
        """初始化配置表"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        row = db.fetchone(
            "SELECT value FROM config WHERE key = ?",
            (key,)
        )

        if row:
            try:
                return json.loads(row["value"])
            except json.JSONDecodeError:
                return row["value"]
        return default

    @staticmethod
    def set(key: str, value: Any) -> bool:
        """
        设置配置值

        Args:
            key: 配置键
            value: 配置值

        Returns:
            bool: 是否设置成功
        """
        try:
            json_value = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            db.execute(
                """
                INSERT OR REPLACE INTO config (key, value)
                VALUES (?, ?)
                """,
                (key, json_value)
            )
            return True
        except Exception as e:
            print(f"设置配置失败: {e}")
            return False

    @staticmethod
    def delete(key: str) -> bool:
        """
        删除配置

        Args:
            key: 配置键

        Returns:
            bool: 是否删除成功
        """
        try:
            cursor = db.execute(
                "DELETE FROM config WHERE key = ?",
                (key,)
            )
            return cursor.rowcount > 0
        except Exception as e:
            print(f"删除配置失败: {e}")
            return False
