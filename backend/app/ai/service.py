import json
import logging
from typing import Optional, List, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.ai import models, schemas

logger = logging.getLogger(__name__)


# ==================== AI 模型配置 ====================

async def get_model_configs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    provider: Optional[str] = None,
    model_type: Optional[str] = None,
    is_enabled: Optional[int] = None,
) -> Tuple[List[models.AiModelConfig], int]:
    query = select(models.AiModelConfig)
    if provider is not None:
        query = query.where(models.AiModelConfig.provider == provider)
    if model_type is not None:
        query = query.where(models.AiModelConfig.model_type == model_type)
    if is_enabled is not None:
        query = query.where(models.AiModelConfig.is_enabled == is_enabled)
    query = query.order_by(models.AiModelConfig.sort_order, models.AiModelConfig.id.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    count_query = select(func.count()).select_from(models.AiModelConfig)
    if provider is not None:
        count_query = count_query.where(models.AiModelConfig.provider == provider)
    if model_type is not None:
        count_query = count_query.where(models.AiModelConfig.model_type == model_type)
    if is_enabled is not None:
        count_query = count_query.where(models.AiModelConfig.is_enabled == is_enabled)
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    return items, total or 0


async def get_model_config(db: AsyncSession, model_id: int) -> Optional[models.AiModelConfig]:
    result = await db.execute(select(models.AiModelConfig).where(models.AiModelConfig.id == model_id))
    return result.scalar_one_or_none()


async def create_model_config(
    db: AsyncSession,
    config_in: schemas.AiModelConfigCreate,
) -> models.AiModelConfig:
    data = config_in.model_dump()
    # 处理 extra_params
    if isinstance(data.get('extra_params'), dict):
        data['extra_params'] = json.dumps(data['extra_params'], ensure_ascii=False)
    # 处理 bool → int
    data['is_enabled'] = 1 if data.get('is_enabled') else 0
    data['is_default'] = 1 if data.get('is_default') else 0

    model_config = models.AiModelConfig(**data)
    db.add(model_config)
    await db.flush()
    await db.refresh(model_config)
    return model_config


async def update_model_config(
    db: AsyncSession,
    model_id: int,
    config_in: schemas.AiModelConfigUpdate,
) -> Optional[models.AiModelConfig]:
    model_config = await get_model_config(db, model_id)
    if not model_config:
        return None
    update_data = config_in.model_dump(exclude_unset=True)
    # 处理 extra_params
    if 'extra_params' in update_data and isinstance(update_data['extra_params'], dict):
        update_data['extra_params'] = json.dumps(update_data['extra_params'], ensure_ascii=False)
    # 处理 bool → int
    if 'is_enabled' in update_data:
        update_data['is_enabled'] = 1 if update_data['is_enabled'] else 0
    if 'is_default' in update_data:
        update_data['is_default'] = 1 if update_data['is_default'] else 0
    if 'sort_order' in update_data:
        update_data['sort_order'] = update_data['sort_order'] or 0
    for field, value in update_data.items():
        setattr(model_config, field, value)
    await db.flush()
    await db.refresh(model_config)
    return model_config


async def delete_model_config(db: AsyncSession, model_id: int) -> bool:
    model_config = await get_model_config(db, model_id)
    if not model_config:
        return False
    await db.delete(model_config)
    return True


async def discover_models_from_api(base_url: str, api_key: str) -> List[str]:
    """通过 OpenAI 兼容 API 发现可用模型列表"""
    import openai
    urls_to_try = [base_url.rstrip('/')]
    if not base_url.rstrip('/').endswith('/v1'):
        urls_to_try.append(base_url.rstrip('/') + '/v1')

    last_error = None
    for url in urls_to_try:
        try:
            client = openai.OpenAI(api_key=api_key, base_url=url)
            response = client.models.list()
            return [model.id for model in response.data]
        except openai.NotFoundError:
            last_error = f'接口路径不存在: {url}/models'
            continue
        except openai.APIConnectionError:
            last_error = f'无法连接到服务器: {url}'
            continue
        except Exception:
            raise

    raise ValueError(last_error or '发现模型失败，请检查地址和密钥')


# ==================== AI 对话 ====================

async def get_conversations(
    db: AsyncSession,
    model_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[List[models.AiConversation], int]:
    query = select(models.AiConversation)
    if model_id is not None:
        query = query.where(models.AiConversation.model_id == model_id)
    query = query.order_by(models.AiConversation.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    count_query = select(func.count()).select_from(models.AiConversation)
    if model_id is not None:
        count_query = count_query.where(models.AiConversation.model_id == model_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    return items, total or 0


async def get_conversation(db: AsyncSession, conversation_id: int) -> Optional[models.AiConversation]:
    result = await db.execute(select(models.AiConversation).where(models.AiConversation.id == conversation_id))
    return result.scalar_one_or_none()


async def create_conversation(
    db: AsyncSession,
    conversation_in: schemas.AiConversationCreate,
) -> models.AiConversation:
    conversation = models.AiConversation(**conversation_in.model_dump())
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)
    return conversation


async def update_conversation(
    db: AsyncSession,
    conversation_id: int,
    conversation_in: schemas.AiConversationUpdate,
) -> Optional[models.AiConversation]:
    conversation = await get_conversation(db, conversation_id)
    if not conversation:
        return None
    update_data = conversation_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(conversation, field, value)
    await db.flush()
    await db.refresh(conversation)
    return conversation


async def update_conversation_model(
    db: AsyncSession,
    conversation_id: int,
    model_id: int,
    model_name: str,
) -> Optional[models.AiConversation]:
    conversation = await get_conversation(db, conversation_id)
    if not conversation:
        return None

    # 模型变化时，清除旧模型的回复消息
    if conversation.model_id != model_id:
        await db.execute(
            delete(models.AiMessage).where(
                models.AiMessage.conversation_id == conversation_id,
                models.AiMessage.role == 'assistant',
            )
        )
        conversation.token_usage_prompt = 0
        conversation.token_usage_completion = 0

    conversation.model_id = model_id
    conversation.model_name = model_name
    await db.flush()
    return conversation


async def delete_conversation(db: AsyncSession, conversation_id: int) -> bool:
    conversation = await get_conversation(db, conversation_id)
    if not conversation:
        return False
    await db.execute(
        delete(models.AiMessage).where(models.AiMessage.conversation_id == conversation_id)
    )
    await db.delete(conversation)
    return True


# ==================== AI 消息 ====================

async def get_messages(
    db: AsyncSession,
    conversation_id: int,
    skip: int = 0,
    limit: int = 500,
) -> Tuple[List[models.AiMessage], int]:
    query = (
        select(models.AiMessage)
        .where(models.AiMessage.conversation_id == conversation_id)
        .order_by(models.AiMessage.id.asc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    count_query = (
        select(func.count())
        .select_from(models.AiMessage)
        .where(models.AiMessage.conversation_id == conversation_id)
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    return items, total or 0


async def delete_message(db: AsyncSession, conversation_id: int, message_id: int) -> bool:
    message = await db.execute(
        select(models.AiMessage).where(
            models.AiMessage.id == message_id,
            models.AiMessage.conversation_id == conversation_id,
        )
    )
    msg = message.scalar_one_or_none()
    if not msg:
        return False
    await db.delete(msg)
    return True


async def add_message(
    db: AsyncSession,
    message_in: schemas.AiMessageCreate,
    token_usage: int = 0,
) -> models.AiMessage:
    message = models.AiMessage(
        conversation_id=message_in.conversation_id,
        role=message_in.role,
        content=message_in.content,
        token_usage=token_usage,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


# ==================== AI 聊天 ====================

async def build_conversation_messages(
    db: AsyncSession,
    conversation_id: int,
    system_prompt: Optional[str] = None,
    max_messages: int = 100,
) -> Tuple[List[dict], models.AiConversation]:
    """构建对话消息历史"""
    conversation = await get_conversation(db, conversation_id)
    if not conversation:
        raise ValueError('对话不存在')

    messages = []

    # 系统提示词
    system = system_prompt or conversation.system_prompt
    if system:
        messages.append({'role': 'system', 'content': system})

    # 历史消息
    history, _ = await get_messages(db, conversation_id, limit=max_messages)
    for msg in history:
        messages.append({
            'role': msg.role,
            'content': msg.content,
        })

    return messages, conversation


async def stream_chat_with_model(
    db: AsyncSession,
    request: schemas.AiStreamChatRequest,
):
    """流式 AI 聊天 - 返回异步生成器"""
    from app.ai.provider import ChatMessage as ProviderChatMessage
    from app.ai.provider.factory import get_model_from_db

    # 获取模型配置
    model_config = await get_model_config(db, request.model_id)
    if not model_config:
        raise ValueError('模型不存在')
    if not model_config.is_enabled:
        raise ValueError('模型未启用')

    # 智能模式：自动使用默认模型
    if request.smart_mode:
        default_models, _ = await get_model_configs(db, is_enabled=1, limit=1)
        default_model = None
        # 优先找 is_default 的模型
        for m in default_models:
            if m.is_default:
                default_model = m
                break
        if default_model and default_model.id != request.model_id:
            model_config = default_model

    # 创建或获取对话
    conversation_id = request.conversation_id
    if conversation_id:
        conversation = await get_conversation(db, conversation_id)
        if not conversation:
            raise ValueError('对话不存在')
    else:
        conversation_create = schemas.AiConversationCreate(
            model_id=request.model_id,
            title=request.message[:100],
            model_name=model_config.model_name,
            system_prompt=request.system_prompt,
        )
        conversation = await create_conversation(db, conversation_create)
        conversation_id = conversation.id

    # 先 yield 会话 ID，让前端知道新会话
    yield {
        'type': 'session',
        'conversation_id': conversation_id,
    }

    # 保存用户消息
    user_msg = schemas.AiMessageCreate(
        conversation_id=conversation_id,
        role='user',
        content=request.message,
    )
    await add_message(db, user_msg)

    # 构建消息历史
    messages, _ = await build_conversation_messages(
        db, conversation_id,
        system_prompt=request.system_prompt,
    )

    # 创建 Provider 模型
    model = await get_model_from_db(model_config)
    provider_messages = [
        ProviderChatMessage(role=m['role'], content=m.get('content', ''))
        for m in messages
    ]

    temperature = request.temperature if request.temperature is not None else model_config.temperature / 100
    max_tokens = request.max_tokens or model_config.max_tokens

    # 流式调用
    full_content = ''
    usage_info = {}

    try:
        async for chunk in model.achat_stream(
            messages=provider_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            if chunk.usage:
                usage_info = chunk.usage
                continue

            if chunk.content:
                full_content += chunk.content
                yield {
                    'type': 'content',
                    'content': chunk.content,
                }

            if chunk.finish_reason:
                yield {
                    'type': 'done',
                    'finish_reason': chunk.finish_reason,
                }

        # 流结束，保存助手消息
        if full_content:
            assistant_msg = schemas.AiMessageCreate(
                conversation_id=conversation_id,
                role='assistant',
                content=full_content,
            )
            await add_message(
                db, assistant_msg,
                token_usage=usage_info.get('total_tokens', 0),
            )

            # 更新对话 Token 统计
            conversation.token_usage_prompt += usage_info.get('prompt_tokens', 0)
            conversation.token_usage_completion += usage_info.get('completion_tokens', 0)
            if not conversation.title or len(conversation.title) <= 5:
                conversation.title = request.message[:100]
            await db.flush()

        yield {
            'type': 'usage',
            **usage_info,
        }

    except Exception as e:
        logger.error(f'AI 流式聊天失败: {e}')
        yield {
            'type': 'error',
            'message': str(e),
        }
        # 出错时也保存已有内容
        if full_content:
            assistant_msg = schemas.AiMessageCreate(
                conversation_id=conversation_id,
                role='assistant',
                content=full_content,
            )
            await add_message(db, assistant_msg)

