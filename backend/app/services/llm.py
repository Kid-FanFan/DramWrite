"""
LLM 服务 - 多模型统一接口
"""
import json
import time
from enum import Enum
from typing import Any, AsyncGenerator, Dict, Optional

import httpx
from loguru import logger

from app.core.config import settings


class LLMProvider(str, Enum):
    """支持的 LLM 提供商"""
    TONGYI = "tongyi"           # 通义千问
    WENXIN = "wenxin"           # 文心一言
    ZHIPU = "zhipu"             # 智谱AI
    DOUBAO = "doubao"           # 豆包
    KIMI = "kimi"               # Kimi
    GEMINI = "gemini"           # Gemini
    DEEPSEEK = "deepseek"       # DeepSeek
    OPENAI = "openai"           # OpenAI
    CLAUDE = "claude"           # Claude
    CUSTOM = "custom"           # 自定义 OpenAI-compatible API


# 默认模型配置
DEFAULT_MODELS = {
    LLMProvider.TONGYI: "qwen-max",
    LLMProvider.WENXIN: "ERNIE-Bot-4",
    LLMProvider.ZHIPU: "glm-4",
    LLMProvider.DOUBAO: "doubao-pro-128k",
    LLMProvider.KIMI: "moonshot-v1-128k",
    LLMProvider.GEMINI: "gemini-pro",
    LLMProvider.DEEPSEEK: "deepseek-chat",
    LLMProvider.OPENAI: "gpt-4",
    LLMProvider.CLAUDE: "claude-3-sonnet-20240229",
    LLMProvider.CUSTOM: "",
}

# 默认 API Base URL
DEFAULT_API_BASES = {
    LLMProvider.TONGYI: "https://dashscope.aliyuncs.com/api/v1",
    LLMProvider.WENXIN: "https://aip.baidubce.com/rpc/2.0",
    LLMProvider.ZHIPU: "https://open.bigmodel.cn/api/paas/v4",
    LLMProvider.DOUBAO: "https://ark.cn-beijing.volces.com/api/v3",
    LLMProvider.KIMI: "https://api.moonshot.cn/v1",
    LLMProvider.GEMINI: "https://generativelanguage.googleapis.com/v1",
    LLMProvider.DEEPSEEK: "https://api.deepseek.com/v1",
    LLMProvider.OPENAI: "https://api.openai.com/v1",
    LLMProvider.CLAUDE: "https://api.anthropic.com/v1",
    LLMProvider.CUSTOM: "",
}


class LLMConfig:
    """LLM 配置"""

    def __init__(
        self,
        provider: str = LLMProvider.TONGYI,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: str = "qwen-max",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        timeout: int = 120
    ):
        self.provider = provider
        self.api_key = api_key
        self.api_base = api_base or DEFAULT_API_BASES.get(provider, "")
        self.model = model or DEFAULT_MODELS.get(provider, "")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（脱敏）"""
        return {
            "provider": self.provider,
            "api_key": self.api_key,
            "api_base": self.api_base,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


class LLMService:
    """LLM 服务"""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            api_base=settings.LLM_API_BASE,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
        self.client = httpx.AsyncClient(timeout=self.config.timeout)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        生成文本

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            **kwargs: 额外参数

        Returns:
            生成的文本
        """
        max_tokens = kwargs.get('max_tokens', self.config.max_tokens)
        logger.info(f"🤖 [LLM调用] provider={self.config.provider}, model={self.config.model}")
        logger.info(f"🤖 [LLM调用] max_tokens参数: 传入={kwargs.get('max_tokens')}, 配置={self.config.max_tokens}, 最终使用={max_tokens}")

        start_time = time.time()
        try:
            if self.config.provider == LLMProvider.TONGYI:
                result = await self._call_tongyi(prompt, system_prompt, **kwargs)
            elif self.config.provider == LLMProvider.OPENAI:
                result = await self._call_openai(prompt, system_prompt, **kwargs)
            else:
                # 其他模型使用 OpenAI 兼容格式
                result = await self._call_openai_compatible(prompt, system_prompt, **kwargs)

            elapsed = time.time() - start_time
            logger.info(f"✅ [LLM响应] 耗时={elapsed:.2f}s, 响应长度={len(result)}字符")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ [LLM失败] 耗时={elapsed:.2f}s, 错误={e}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式生成文本

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            **kwargs: 额外参数

        Yields:
            生成的文本片段
        """
        logger.info(f"流式调用 LLM: {self.config.provider}, model: {self.config.model}")

        try:
            # 目前仅支持 OpenAI 兼容格式的流式输出
            async for chunk in self._call_openai_stream(prompt, system_prompt, **kwargs):
                yield chunk
        except Exception as e:
            logger.error(f"LLM 流式调用失败: {e}")
            raise

    async def generate_with_retry(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_retries: int = 3,
        **kwargs
    ) -> str:
        """
        带重试的生成

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            max_retries: 最大重试次数
            **kwargs: 额外参数

        Returns:
            生成的文本
        """
        import asyncio

        logger.info(f"🔄 [LLM重试] max_retries={max_retries}, kwargs={kwargs}")
        logger.info(f"🔄 [LLM重试] self.config.max_tokens={self.config.max_tokens}")
        for attempt in range(max_retries):
            try:
                return await self.generate(prompt, system_prompt, **kwargs)
            except Exception as e:
                logger.warning(f"⚠️ [LLM重试] 第{attempt + 1}/{max_retries}次失败: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"⏳ [LLM重试] 等待{wait_time}秒后重试...")
                    await asyncio.sleep(wait_time)  # 指数退避
                else:
                    logger.error(f"❌ [LLM重试] 已达最大重试次数，放弃")
                    raise

        raise Exception("LLM 调用失败，已达最大重试次数")

    async def chat_completion(
        self,
        messages: list,
        **kwargs
    ) -> str:
        """
        聊天完成

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            生成的文本
        """
        try:
            return await self._call_openai_compatible_chat(messages, **kwargs)
        except Exception as e:
            logger.error(f"聊天完成调用失败: {e}")
            raise

    async def test_connection(self) -> Dict[str, Any]:
        """
        测试连接

        Returns:
            测试结果
        """
        try:
            start_time = time.time()
            response = await self.generate(
                prompt="你好，这是一个测试。请回复'连接成功'。",
                max_tokens=50
            )
            elapsed = time.time() - start_time

            return {
                "success": True,
                "response_time": round(elapsed, 2),
                "message": "连接成功",
                "response_preview": response[:50]
            }
        except Exception as e:
            return {
                "success": False,
                "response_time": 0,
                "message": str(e)
            }

    async def _call_tongyi(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """调用通义千问"""
        url = f"{self.config.api_base}/services/aigc/text-generation/generation"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.config.model,
            "input": {"messages": messages},
            "parameters": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "result_format": "message"
            }
        }

        response = await self.client.post(url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        if "output" in result and "choices" in result["output"]:
            return result["output"]["choices"][0]["message"]["content"]
        return result.get("output", {}).get("text", "")

    async def _call_openai(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """调用 OpenAI"""
        url = f"{self.config.api_base}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.config.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens)
        }

        response = await self.client.post(url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    async def _call_openai_compatible(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """调用 OpenAI 兼容 API"""
        return await self._call_openai(prompt, system_prompt, **kwargs)

    async def _call_openai_compatible_chat(
        self,
        messages: list,
        **kwargs
    ) -> str:
        """调用 OpenAI 兼容 API (聊天模式)"""
        url = f"{self.config.api_base}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.config.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens)
        }

        response = await self.client.post(url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    async def _call_openai_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """调用 OpenAI 兼容 API 流式输出"""
        url = f"{self.config.api_base}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.config.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True
        }

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            async with client.stream("POST", url, headers=headers, json=data) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        line = line[6:]  # 移除 "data: " 前缀
                        if line == "[DONE]":
                            break
                        try:
                            chunk = json.loads(line)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 全局LLM服务实例
_llm_service: Optional[LLMService] = None


def _get_db_config() -> LLMConfig:
    """从数据库获取LLM配置"""
    try:
        from app.api.v1.endpoints.settings import _get_current_config
        db_config = _get_current_config()
        return LLMConfig(
            provider=db_config.get("provider", "tongyi"),
            api_key=db_config.get("apiKey"),
            api_base=db_config.get("apiBase"),
            model=db_config.get("model", "qwen-max"),
            temperature=db_config.get("temperature", 0.7),
            max_tokens=db_config.get("maxTokens", 4000),
        )
    except Exception:
        # 如果数据库读取失败，使用默认配置
        return LLMConfig(
            provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            api_base=settings.LLM_API_BASE,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )


def get_llm_service(config: Optional[LLMConfig] = None) -> LLMService:
    """获取LLM服务实例"""
    global _llm_service
    if config is not None:
        _llm_service = LLMService(config)
    elif _llm_service is None:
        # 没有传入配置且没有缓存实例时，从数据库读取配置
        db_config = _get_db_config()
        _llm_service = LLMService(db_config)
    return _llm_service


def reset_llm_service():
    """重置LLM服务实例"""
    global _llm_service
    _llm_service = None
