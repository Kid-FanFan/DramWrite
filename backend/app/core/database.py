"""
SQLite 数据库连接管理模块

使用 Python 标准库 sqlite3，无需额外依赖
"""
import os
import sqlite3
from typing import Optional
from contextlib import contextmanager

# 数据库文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE_PATH = os.path.join(DATA_DIR, "scriptmaster.db")


class Database:
    """数据库管理类"""

    _instance: Optional["Database"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.db_path = DATABASE_PATH
            self._init_db()
            Database._initialized = True

    def _init_db(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 创建项目表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    project_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_projects_status
                ON projects(status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_projects_created
                ON projects(created_at DESC)
            """)

            # 创建配置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            conn.commit()

    @contextmanager
    def get_connection(self):
        """
        获取数据库连接

        使用示例:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM projects")
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 让查询结果可以通过列名访问
        try:
            yield conn
        finally:
            conn.close()

    def execute(self, sql: str, parameters: tuple = ()) -> sqlite3.Cursor:
        """
        执行 SQL 语句

        Args:
            sql: SQL 语句
            parameters: 参数

        Returns:
            Cursor: 游标对象
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, parameters)
            conn.commit()
            return cursor

    def fetchone(self, sql: str, parameters: tuple = ()) -> Optional[sqlite3.Row]:
        """
        查询单条记录

        Args:
            sql: SQL 语句
            parameters: 参数

        Returns:
            Optional[Row]: 查询结果
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, parameters)
            return cursor.fetchone()

    def fetchall(self, sql: str, parameters: tuple = ()) -> list:
        """
        查询多条记录

        Args:
            sql: SQL 语句
            parameters: 参数

        Returns:
            list: 查询结果列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, parameters)
            return cursor.fetchall()


# 全局数据库实例
db = Database()
