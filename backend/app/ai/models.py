from sqlalchemy import Column, Integer, String, DateTime, Text, SmallInteger
from config.database import AiBase
from datetime import datetime
from config.settings import settings
import pytz


def get_localized_datetime():
    try:
        timezone_str = settings.TIMEZONE if hasattr(settings, 'TIMEZONE') else 'UTC'
        if timezone_str == 'UTC':
            tz = pytz.UTC
        else:
            tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        return now
    except Exception as e:
        print(f"时区配置错误，使用UTC: {e}")
        return datetime.now(pytz.UTC)


class AiModelConfig(AiBase):
    """AI 模型配置"""
    __tablename__ = "ai_model_configs"

    PROVIDER_CHOICES = [
        'openai', 'deepseek', 'ollama', 'longcat', 'vllm',
        'openrouter', 'azure', 'anthropic', 'google', 'zhipu',
        'baidu', 'alibaba', 'xiaomi', 'custom',
    ]
    MODEL_TYPE_CHOICES = ['LLM', 'EMBEDDING', 'TTS', 'STT', 'IMAGE']

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="显示名称，如 GPT-4o")
    model_name = Column(String(200), nullable=False, comment="模型标识，如 gpt-4o")
    provider = Column(String(50), nullable=False, index=True, comment="厂商标识")
    model_type = Column(String(50), default='LLM', comment="模型类型")
    api_base = Column(String(500), default='', comment="API 地址")
    api_key = Column(String(500), default='', comment="API 密钥")
    api_secret = Column(String(500), default='', comment="API Secret")
    api_version = Column(String(50), default='', comment="API 版本")
    max_tokens = Column(Integer, default=4096, comment="最大输出 Token 数")
    context_length = Column(Integer, default=8192, comment="上下文窗口大小")
    temperature = Column(Integer, default=70, comment="温度参数，存储为整数 0-200，使用时除以 100")
    top_p = Column(Integer, default=100, comment="Top P，存储为整数 0-100，使用时除以 100")
    extra_params = Column(Text, default='{}', comment="额外参数 JSON")
    is_enabled = Column(SmallInteger, default=1, comment="1启用 0停用")
    is_default = Column(SmallInteger, default=0, comment="1默认 0非默认")
    sort_order = Column(Integer, default=0, comment="排序")
    created_at = Column(DateTime, default=get_localized_datetime)
    updated_at = Column(DateTime, default=get_localized_datetime, onupdate=get_localized_datetime)

    def __repr__(self):
        return f"<AiModelConfig(id={self.id}, name='{self.name}', provider='{self.provider}')>"


class AiConversation(AiBase):
    """AI 对话记录"""
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, nullable=False, index=True, comment="关联的模型配置ID")
    title = Column(String(256), nullable=True, comment="对话标题")
    model_name = Column(String(200), nullable=False, comment="使用的模型标识")
    system_prompt = Column(Text, nullable=True, comment="系统提示词")
    status = Column(SmallInteger, default=1, comment="1进行中 2已完成 3已归档")
    token_usage_prompt = Column(Integer, default=0, comment="提示 Token 消耗")
    token_usage_completion = Column(Integer, default=0, comment="生成 Token 消耗")
    created_at = Column(DateTime, default=get_localized_datetime)
    updated_at = Column(DateTime, default=get_localized_datetime, onupdate=get_localized_datetime)

    def __repr__(self):
        return f"<AiConversation(id={self.id}, title='{self.title}')>"


class AiMessage(AiBase):
    """AI 对话消息"""
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, nullable=False, index=True, comment="关联的对话ID")
    role = Column(String(16), nullable=False, comment="角色: user / assistant / system")
    content = Column(Text, nullable=False, comment="消息内容")
    reasoning_content = Column(Text, nullable=True, comment="思考内容（DeepSeek thinking 模式）")
    token_usage = Column(Integer, default=0, comment="本条 Token 消耗")
    created_at = Column(DateTime, default=get_localized_datetime)

    def __repr__(self):
        return f"<AiMessage(id={self.id}, role='{self.role}', conversation_id={self.conversation_id})>"


class AiUsageLog(AiBase):
    """AI 用量日志 - 记录每次 AI 请求的 Token 消耗"""
    __tablename__ = "ai_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True, comment="用户ID")
    model_id = Column(Integer, nullable=True, comment="模型配置ID")
    conversation_id = Column(Integer, nullable=True, index=True, comment="关联的对话ID")
    conversation_title = Column(String(256), default='', comment="对话标题")
    model_name = Column(String(200), nullable=False, comment="模型标识")
    provider = Column(String(50), nullable=False, comment="厂商")
    prompt_tokens = Column(Integer, default=0, comment="输入 Token 数")
    completion_tokens = Column(Integer, default=0, comment="输出 Token 数")
    total_tokens = Column(Integer, default=0, comment="总 Token 数")
    cost = Column(Integer, default=0, comment="费用（单位：分，暂未启用）")
    created_at = Column(DateTime, default=get_localized_datetime, index=True, comment="记录时间")

    def __repr__(self):
        return f"<AiUsageLog(id={self.id}, user_id={self.user_id}, total_tokens={self.total_tokens})>"
