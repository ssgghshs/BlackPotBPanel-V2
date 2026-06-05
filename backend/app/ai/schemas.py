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


class AiConversationSwitchModel(BaseModel):
    model_config = {'protected_namespaces': ()}

    model_id: int
    model_name: str


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
    reasoning_content: Optional[str] = None
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
    files: Optional[List[str]] = None  # 附加文件路径列表（上传后的服务端路径）
    system_prompt: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    smart_mode: Optional[bool] = True
    enabled_tools: Optional[List[str]] = None


class AiUploadResponse(BaseModel):
    """文件上传响应"""
    path: str
    name: str
    size: int


class AiToolConfirmRequest(BaseModel):
    """危险操作确认请求"""
    model_config = {'protected_namespaces': ()}

    conversation_id: int
    call_id: str
    confirmed: bool


# ==================== AI 工具集 ====================

class AiToolsetInfo(BaseModel):
    """工具集信息"""
    id: str
    name: str
    tools: List[str]


class AiToolsetsResponse(BaseModel):
    """工具集列表响应"""
    toolsets: List[AiToolsetInfo]


# ==================== AI 用量统计 ====================

class AiUsageLogItem(BaseModel):
    """用量日志单条记录"""
    model_config = {'protected_namespaces': (), 'from_attributes': True}

    id: int
    conversation_id: Optional[int] = None
    conversation_title: str = ''
    model_name: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: int = 0
    created_at: Optional[str] = None


class AiUsageSummary(BaseModel):
    """用量汇总"""
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0


class AiUsageByModel(BaseModel):
    """按模型分组统计"""
    model_config = {'protected_namespaces': ()}

    model_name: str
    provider: str
    request_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int


class AiUsageDailyStat(BaseModel):
    """按日趋势"""
    date: str
    request_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int


class AiUsageResponse(BaseModel):
    """用量统计响应"""
    summary: AiUsageSummary
    by_model: List[AiUsageByModel]
    daily_stats: List[AiUsageDailyStat]
    recent_logs: List[AiUsageLogItem]


class AiUsageExportItem(BaseModel):
    """用量导出单条记录"""
    date: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: int = 0


class AiUsageResetResponse(BaseModel):
    """用量重置响应"""
    deleted_count: int
    message: str
