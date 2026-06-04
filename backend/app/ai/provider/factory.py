from typing import Any, Dict
from app.ai.provider.base import BaseAIProvider, BaseLLMModel, ModelConfig

# Provider 注册表
_PROVIDER_REGISTRY: Dict[str, type[BaseAIProvider]] = {}


def register_provider(key: str, provider_cls: type[BaseAIProvider]):
    """注册 Provider"""
    _PROVIDER_REGISTRY[key.lower()] = provider_cls


def get_provider(provider_key: str, **kwargs) -> BaseAIProvider:
    """获取 Provider 实例"""
    provider_key = provider_key.lower()
    if provider_key not in _PROVIDER_REGISTRY:
        raise ValueError(f'不支持的 Provider: {provider_key}，已注册: {list(_PROVIDER_REGISTRY.keys())}')
    provider_cls = _PROVIDER_REGISTRY[provider_key]
    return provider_cls(provider_key=provider_key, **kwargs)


def create_model(model_config: ModelConfig) -> BaseLLMModel:
    """根据配置创建模型"""
    provider = get_provider(model_config.provider_key)
    return provider.create_model(model_config)


def get_model_from_config(
    provider_key: str,
    model_name: str,
    api_base: str = '',
    api_key: str = '',
    api_secret: str = '',
    api_version: str = '',
    max_tokens: int = 4096,
    temperature: float = 0.7,
    top_p: float = 1.0,
    **kwargs
) -> BaseLLMModel:
    """通过配置参数创建模型"""
    model_config = ModelConfig(
        model_name=model_name,
        provider_key=provider_key,
        api_base=api_base,
        api_key=api_key,
        api_secret=api_secret,
        api_version=api_version,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        extra_params=kwargs,
    )
    return create_model(model_config)


async def get_model_from_db(model_instance) -> BaseLLMModel:
    """从数据库模型实例创建模型"""
    from app.ai.models import AiModelConfig

    return get_model_from_config(
        provider_key=model_instance.provider,
        model_name=model_instance.model_name,
        api_base=model_instance.api_base or '',
        api_key=model_instance.api_key or '',
        api_secret=model_instance.api_secret or '',
        api_version=model_instance.api_version or '',
        max_tokens=model_instance.max_tokens or 4096,
        temperature=(model_instance.temperature or 70) / 100,
        top_p=(model_instance.top_p or 100) / 100,
    )


# ========== 注册默认 Provider ==========
from app.ai.provider.openai_provider import OpenAIProvider

# OpenAI 及其兼容服务都使用 OpenAIProvider
register_provider('openai', OpenAIProvider)
register_provider('deepseek', OpenAIProvider)
register_provider('ollama', OpenAIProvider)
register_provider('longcat', OpenAIProvider)
register_provider('vllm', OpenAIProvider)
register_provider('openrouter', OpenAIProvider)
register_provider('azure', OpenAIProvider)
register_provider('xiaomi', OpenAIProvider)
register_provider('anthropic', OpenAIProvider)
register_provider('google', OpenAIProvider)
register_provider('zhipu', OpenAIProvider)
register_provider('baidu', OpenAIProvider)
register_provider('alibaba', OpenAIProvider)
register_provider('custom', OpenAIProvider)
