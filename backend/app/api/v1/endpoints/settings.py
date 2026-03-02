"""
设置 API - LLM配置管理
"""
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

from app.services.llm import LLMConfig, LLMProvider, LLMService, get_llm_service, reset_llm_service
from app.models.config import ConfigModel

router = APIRouter()

# 配置键名
CONFIG_KEY_LLM = "llm_config"

# 默认配置
DEFAULT_LLM_CONFIG = {
    "provider": "tongyi",
    "apiKey": "",
    "apiBase": "",
    "model": "qwen-max",
    "temperature": 0.7,
    "maxTokens": 4000,
}


class LLMSettingsRequest(BaseModel):
    """LLM设置请求"""
    provider: str = Field(default="tongyi", description="模型提供商")
    apiKey: Optional[str] = Field(None, description="API Key")
    apiBase: Optional[str] = Field(None, description="API Base URL")
    model: Optional[str] = Field(None, description="模型名称")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度参数")
    maxTokens: int = Field(default=4000, ge=100, le=8000, description="最大Token数")


class LLMTestResponse(BaseModel):
    """LLM测试结果"""
    success: bool
    responseTime: float
    message: str
    responsePreview: Optional[str] = None


def _get_current_config() -> Dict[str, Any]:
    """获取当前配置（从数据库）"""
    config = ConfigModel.get(CONFIG_KEY_LLM)
    if not config:
        return DEFAULT_LLM_CONFIG.copy()

    # 合并默认配置（处理新增字段）
    merged = DEFAULT_LLM_CONFIG.copy()
    merged.update(config)
    return merged


@router.get("/llm", response_model=dict)
async def get_llm_settings():
    """
    获取LLM配置
    """
    config = _get_current_config()

    return {
        "code": 200,
        "message": "success",
        "data": {
            "provider": config["provider"],
            "apiKey": _mask_api_key(config.get("apiKey", "")),
            "apiBase": config.get("apiBase", ""),
            "model": config.get("model", ""),
            "temperature": config.get("temperature", 0.7),
            "maxTokens": config.get("maxTokens", 4000),
        }
    }


@router.post("/llm", response_model=dict)
async def update_llm_settings(request: LLMSettingsRequest):
    """
    更新LLM配置
    """
    # 验证提供商
    try:
        provider = LLMProvider(request.provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"不支持的模型提供商: {request.provider}")

    # 获取当前配置
    current = _get_current_config()

    # 更新配置
    new_config = {
        "provider": request.provider,
        "apiKey": request.apiKey if request.apiKey is not None else current.get("apiKey", ""),
        "apiBase": request.apiBase if request.apiBase is not None else current.get("apiBase", ""),
        "model": request.model if request.model is not None else current.get("model", ""),
        "temperature": request.temperature,
        "maxTokens": request.maxTokens,
    }

    # 保存到数据库
    if ConfigModel.set(CONFIG_KEY_LLM, new_config):
        logger.info(f"LLM配置已更新: provider={request.provider}, model={request.model}")

        # 重置LLM服务实例
        reset_llm_service()

        return {
            "code": 200,
            "message": "success",
            "data": {
                "provider": request.provider,
                "model": request.model,
            }
        }
    else:
        raise HTTPException(status_code=500, detail="保存配置失败")


@router.post("/llm/test", response_model=dict)
async def test_llm_connection(request: LLMSettingsRequest):
    """
    测试LLM连接
    """
    try:
        config = LLMConfig(
            provider=request.provider,
            api_key=request.apiKey,
            api_base=request.apiBase,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.maxTokens,
        )

        service = LLMService(config)
        result = await service.test_connection()
        await service.close()

        return {
            "code": 200,
            "message": "success",
            "data": {
                "success": result["success"],
                "responseTime": result["response_time"],
                "message": result["message"],
                "responsePreview": result.get("response_preview", "")
            }
        }
    except Exception as e:
        logger.error(f"LLM连接测试失败: {e}")
        return {
            "code": 200,
            "message": "success",
            "data": {
                "success": False,
                "responseTime": 0,
                "message": str(e),
                "responsePreview": ""
            }
        }


@router.get("/llm/providers", response_model=dict)
async def get_llm_providers():
    """
    获取支持的LLM提供商列表
    """
    providers = [
        {"id": provider.value, "name": _get_provider_name(provider)}
        for provider in LLMProvider
    ]

    return {
        "code": 200,
        "message": "success",
        "data": providers
    }


def _mask_api_key(api_key: str) -> str:
    """脱敏API Key"""
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "****"
    return api_key[:4] + "****" + api_key[-4:]


def _get_provider_name(provider: LLMProvider) -> str:
    """获取提供商中文名"""
    names = {
        LLMProvider.TONGYI: "通义千问",
        LLMProvider.WENXIN: "文心一言",
        LLMProvider.ZHIPU: "智谱AI",
        LLMProvider.DOUBAO: "豆包",
        LLMProvider.KIMI: "Kimi",
        LLMProvider.GEMINI: "Gemini",
        LLMProvider.DEEPSEEK: "DeepSeek",
        LLMProvider.OPENAI: "OpenAI",
        LLMProvider.CLAUDE: "Claude",
        LLMProvider.CUSTOM: "自定义",
    }
    return names.get(provider, provider.value)


# 兼容旧代码的接口
# 让其他模块可以通过导入 _current_llm_config 获取配置
class ConfigProxy:
    """配置代理，兼容旧代码访问 _current_llm_config"""

    def get(self, key: str, default: Any = None) -> Any:
        config = _get_current_config()
        return config.get(key, default)

    def __getitem__(self, key: str) -> Any:
        config = _get_current_config()
        return config[key]

    def __setitem__(self, key: str, value: Any) -> None:
        config = _get_current_config()
        config[key] = value
        ConfigModel.set(CONFIG_KEY_LLM, config)


# 导出兼容接口
_current_llm_config = ConfigProxy()
