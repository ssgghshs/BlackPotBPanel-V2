from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Generator, AsyncGenerator
from dataclasses import dataclass, field


@dataclass
class ToolDefinition:
    """工具定义 - 用于 OpenAI function calling"""
    name: str
    description: str
    parameters: Dict[str, Any]


@dataclass
class ModelConfig:
    """模型配置"""
    model_name: str
    provider_key: str
    api_base: str = ''
    api_key: str = ''
    api_secret: str = ''
    api_version: str = ''
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    reasoning_content: Optional[str] = None


@dataclass
class ChatResponse:
    """聊天响应"""
    content: str = ''
    reasoning_content: str = ''
    tool_calls: List[Dict] = field(default_factory=list)
    finish_reason: str = ''
    usage: Dict[str, int] = field(default_factory=dict)


class BaseAIProvider(ABC):
    """AI Provider 基类"""

    def __init__(self, provider_key: str, **kwargs):
        self.provider_key = provider_key
        self.config = kwargs

    @abstractmethod
    def create_model(self, model_config: ModelConfig) -> Any:
        pass


class BaseLLMModel(ABC):
    """LLM 模型基类"""

    def __init__(self, model_config: ModelConfig):
        self.model_config = model_config

    @abstractmethod
    def chat(
        self,
        messages: List[ChatMessage],
        stream: bool = False,
        **kwargs
    ) -> ChatResponse:
        pass

    @abstractmethod
    def chat_stream(
        self,
        messages: List[ChatMessage],
        **kwargs
    ) -> Generator[ChatResponse, None, None]:
        pass

    @abstractmethod
    async def achat(
        self,
        messages: List[ChatMessage],
        stream: bool = False,
        **kwargs
    ) -> ChatResponse:
        pass

    @abstractmethod
    async def achat_stream(
        self,
        messages: List[ChatMessage],
        **kwargs
    ) -> AsyncGenerator[ChatResponse, None]:
        pass

    def is_valid(self) -> bool:
        return True
