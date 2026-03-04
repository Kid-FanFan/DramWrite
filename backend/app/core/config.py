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


# ===== LLM 配置工具函数 =====

def get_current_llm_config() -> dict:
    """
    获取当前 LLM 配置（从本地存储）

    Returns:
        dict: LLM 配置字典
    """
    try:
        from app.services.project import ProjectService
        config = ProjectService.get_settings()
        return config if config else _get_default_llm_config()
    except Exception:
        return _get_default_llm_config()


def check_llm_configured() -> tuple[bool, str]:
    """
    检查 LLM 是否已配置

    Returns:
        tuple: (是否已配置, 错误消息)
    """
    config = get_current_llm_config()

    # 检查 API Key
    api_key = config.get("apiKey") or config.get("api_key")
    if not api_key:
        return False, "请先前往设置页面配置大模型 API Key"

    return True, ""


def _get_default_llm_config() -> dict:
    """获取默认 LLM 配置"""
    return {
        "provider": settings.LLM_PROVIDER,
        "apiKey": settings.LLM_API_KEY,
        "apiBase": settings.LLM_API_BASE,
        "model": settings.LLM_MODEL,
        "temperature": settings.LLM_TEMPERATURE,
        "maxTokens": settings.LLM_MAX_TOKENS
    }
