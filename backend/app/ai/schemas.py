from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List, Any
import json


# ==================== AI 模型配置管理 ====================

PROVIDER_CHOICES = [
    'openai', 'deepseek', 'ollama', 'longcat', 'vllm',
    'openrouter', 'azure', 'anthropic', 'google', 'zhipu',
    'baidu', 'alibaba', 'xiaomi', 'custom',
]
MODEL_TYPE_CHOICES = ['LLM', 'EMBEDDING', 'TTS', 'STT', 'IMAGE']


class AiModelConfigBase(BaseModel):
    model_config = {'protected_namespaces': ()}

    name: str
    model_name: str
    provider: str
    model_type: str = 'LLM'
    api_base: str = ''
    api_key: str = ''
    api_secret: str = ''
    api_version: str = ''
    max_tokens: int = 4096
    context_length: int = 8192
    temperature: int = 70
    top_p: int = 100
    extra_params: Any = {}
    is_enabled: bool = True
    is_default: bool = False
    sort_order: int = 0

    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        if v not in PROVIDER_CHOICES:
            raise ValueError(f'不支持的厂商: {v}，可选: {PROVIDER_CHOICES}')
        return v

    @field_validator('model_type')
    @classmethod
    def validate_model_type(cls, v):
        if v not in MODEL_TYPE_CHOICES:
            raise ValueError(f'不支持的模型类型: {v}，可选: {MODEL_TYPE_CHOICES}')
        return v

    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        if v < 0 or v > 200:
            raise ValueError('temperature 必须在 0-200 之间')
        return v

    @field_validator('top_p')
    @classmethod
    def validate_top_p(cls, v):
        if v < 0 or v > 100:
            raise ValueError('top_p 必须在 0-100 之间')
        return v


class AiModelConfigCreate(AiModelConfigBase):
    pass


class AiModelConfigUpdate(BaseModel):
    model_config = {'protected_namespaces': ()}

    name: Optional[str] = None
    model_name: Optional[str] = None
    provider: Optional[str] = None
    model_type: Optional[str] = None
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    api_version: Optional[str] = None
    max_tokens: Optional[int] = None
    context_length: Optional[int] = None
    temperature: Optional[int] = None
    top_p: Optional[int] = None
    extra_params: Optional[Any] = None
    is_enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    sort_order: Optional[int] = None


class AiModelConfig(AiModelConfigBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AiModelConfigListResponse(BaseModel):
    total: int
    items: List[AiModelConfig]


class AiModelDiscoverRequest(BaseModel):
    base_url: str
    api_key: str


class AiModelDiscoverResponse(BaseModel):
    models: List[str]


# ==================== AI 对话 ====================

class AiConversationBase(BaseModel):
    model_config = {'protected_namespaces': ()}

    model_id: int
    title: Optional[str] = None
    model_name: str
    system_prompt: Optional[str] = None


class AiConversationCreate(AiConversationBase):
    pass


class AiConversationUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[int] = None


class AiConversation(AiConversationBase):
    id: int
    status: int
    token_usage_prompt: int
    token_usage_completion: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AiConversationListResponse(BaseModel):
    total: int
    items: List[AiConversation]


# ==================== AI 消息 ====================

class AiMessageBase(BaseModel):
    role: str
    content: str


class AiMessageCreate(AiMessageBase):
    conversation_id: int


class AiMessage(AiMessageBase):
    id: int
    conversation_id: int
    token_usage: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AiMessageListResponse(BaseModel):
    total: int
    items: List[AiMessage]


# ==================== AI 对话/聊天 ====================

class AiStreamChatRequest(BaseModel):
    model_config = {'protected_namespaces': ()}

    model_id: int
    conversation_id: Optional[int] = None
    message: str
    system_prompt: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
