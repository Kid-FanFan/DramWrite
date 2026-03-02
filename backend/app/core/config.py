"""
配置管理模块
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # 应用信息
    APP_NAME: str = "剧作大师 (ScriptMaster)"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, alias="DEBUG")

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # CORS 配置
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # LLM 配置
    LLM_PROVIDER: str = "tongyi"  # tongyi, wenxin, zhipu, openai, claude, etc.
    LLM_API_KEY: Optional[str] = None
    LLM_API_BASE: Optional[str] = None
    LLM_MODEL: str = "qwen-max"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4000

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}"

    # 生成配置
    DEFAULT_EPISODES: int = 80
    DEFAULT_WORDS_PER_EPISODE: int = 700
    MAX_EPISODES: int = 120
    MIN_EPISODES: int = 30


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（缓存）"""
    return Settings()


# 导出配置实例
settings = get_settings()
