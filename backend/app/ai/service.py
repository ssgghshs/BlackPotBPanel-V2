import json
import logging
import os
import uuid
from datetime import timedelta, datetime
from typing import Optional, List, Tuple, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.ai import models, schemas
from config.settings import settings as app_settings
import pytz

logger = logging.getLogger(__name__)


def _get_localized_now() -> datetime:
    """获取当前时间的本地化（时区感知）datetime"""
    try:
        tz_str = app_settings.TIMEZONE or 'UTC'
        if tz_str == 'UTC':
            tz = pytz.UTC
        else:
            tz = pytz.timezone(tz_str)
        return datetime.now(tz)
    except Exception:
        return datetime.now(pytz.UTC)


def _format_size(size_bytes: int) -> str:
    """人性化文件大小显示"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f'{size_bytes:.1f}{unit}' if unit != 'B' else f'{size_bytes}B'
        size_bytes /= 1024
    return f'{size_bytes:.1f}TB'


# ==================== 文件上传 ====================

async def save_uploaded_file(file_content: bytes, filename: str) -> schemas.AiUploadResponse:
    """保存上传的文件到临时目录，返回路径信息"""
    from config.settings import settings

    upload_dir = os.path.join(settings.TEMP_PATH, 'ai_uploads')
    os.makedirs(upload_dir, exist_ok=True)

    # 生成唯一文件名防止重名
    ext = os.path.splitext(filename)[1]
    safe_name = f'{uuid.uuid4().hex}{ext}'
    save_path = os.path.join(upload_dir, safe_name)

    with open(save_path, 'wb') as f:
        f.write(file_content)

    return schemas.AiUploadResponse(
        path=save_path,
        name=filename,
        size=len(file_content),
    )


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
    reasoning_content: str = None,
) -> models.AiMessage:
    message = models.AiMessage(
        conversation_id=message_in.conversation_id,
        role=message_in.role,
        content=message_in.content,
        reasoning_content=reasoning_content,
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
        entry = {
            'role': msg.role,
            'content': msg.content,
        }
        if msg.reasoning_content:
            entry['reasoning_content'] = msg.reasoning_content
        messages.append(entry)

    return messages, conversation


# ---- Agent 会话级缓存 ----
import threading
import time as time_module

_agents: Dict[str, Any] = {}
_agents_lock = threading.Lock()
_agents_last_access: Dict[str, float] = {}
_AGENT_IDLE_TIMEOUT = 1800  # 30 分钟

def _cleanup_idle_agents():
    """清理超时的 Agent 实例"""
    now = time_module.time()
    with _agents_lock:
        expired = [sid for sid, ts in _agents_last_access.items() if now - ts > _AGENT_IDLE_TIMEOUT]
        for sid in expired:
            agent = _agents.pop(sid, None)
            if agent:
                try:
                    agent.stop()
                except Exception:
                    pass
            _agents_last_access.pop(sid, None)
        if expired:
            logger.info(f'[Agent] 自动清理 {len(expired)} 个空闲 Agent')


async def _get_or_create_agent(
    session_id: str,
    model_instance,
    user_message: str = '',
    enabled_tools: List[str] = None,
    system_prompt: str = None,
) -> Any:
    """获取或创建会话级 Agent"""
    from app.ai.agent import Agent, AIToolRegistry
    from app.ai.provider.factory import get_model_from_db

    if len(_agents) > 50:
        _cleanup_idle_agents()

    llm_model = await get_model_from_db(model_instance)

    with _agents_lock:
        if session_id in _agents:
            agent = _agents[session_id]
            agent.reset_stop()
            _agents_last_access[session_id] = time_module.time()
            # 更新配置
            if enabled_tools is not None:
                agent.enabled_tools = enabled_tools
            if system_prompt:
                agent.system_prompt = system_prompt
            return agent

    # 新建
    config = {}
    if enabled_tools:
        config['enabled_tools'] = enabled_tools
    if system_prompt:
        config['system_prompt'] = system_prompt

    agent = Agent(
        session_id=session_id,
        model=llm_model,
        tool_registry=AIToolRegistry(),
        config=config,
    )

    with _agents_lock:
        _agents[session_id] = agent
        _agents_last_access[session_id] = time_module.time()

    return agent


def _stop_agent(session_id: str):
    """停止指定会话的 Agent"""
    with _agents_lock:
        agent = _agents.get(session_id)
        if agent:
            agent.stop()


def _confirm_agent_tool(conversation_id: int, call_id: str, confirmed: bool) -> bool:
    """
    确认 Agent 的高风险工具执行。
    返回 True 表示确认成功，False 表示没有找到对应的 Agent 或确认不匹配。
    """
    session_id = str(conversation_id)
    with _agents_lock:
        agent = _agents.get(session_id)
        if not agent:
            logger.warning(f'[Service] 确认失败: 未找到 Agent (conversation_id={conversation_id})')
            return False
    return agent.confirm_tool(call_id, confirmed)


async def _auto_generate_title(
    db: AsyncSession,
    conversation: models.AiConversation,
    user_message: str,
    ai_response: str,
):
    """根据首轮对话内容自动生成对话标题"""
    if conversation.title and len(conversation.title) > 5:
        return  # 已有有效标题，不覆盖

    try:
        from app.ai.provider.factory import get_model_from_db
        from app.ai.provider.base import ChatMessage

        # 获取模型配置并创建 LLM 实例
        model_config = await get_model_config(db, conversation.model_id)
        if not model_config or not model_config.is_enabled:
            return

        llm = await get_model_from_db(model_config)

        prompt = (
            "你是一个标题生成助手。请根据以下用户消息和 AI 回复，生成一个简短（不超过 20 字）的对话标题。\n"
            "只返回标题本身，不要加引号或多余文字。\n\n"
            f"用户消息: {user_message[:200]}\n"
            f"AI 回复: {ai_response[:200]}"
        )

        messages = [ChatMessage(role='user', content=prompt)]
        response = await llm.achat(messages=messages, temperature=0.3, max_tokens=50)

        title = response.content.strip().strip('"\'「」')
        if title and len(title) <= 50:
            conversation.title = title
            await db.flush()
            logger.info(f'[Service] 自动生成标题: "{title}" (conversation_id={conversation.id})')
    except Exception as e:
        logger.warning(f'[Service] 自动生成标题失败: {e}')
        # 标题生成失败不影响主流程，使用默认标题
        if not conversation.title or len(conversation.title) <= 5:
            conversation.title = user_message[:100]


async def stream_chat_with_model(
    db: AsyncSession,
    request: schemas.AiStreamChatRequest,
    user_id: int = 0,
):
    """流式 AI 聊天（集成 Agent + 意图路由 + 标题自动生成）"""
    from app.ai.agent.intent_router import resolve_tools

    # 获取模型配置
    model_config = await get_model_config(db, request.model_id)
    if not model_config:
        raise ValueError('模型不存在')
    if not model_config.is_enabled:
        raise ValueError('模型未启用')

    # 创建或获取对话
    conversation_id = request.conversation_id
    is_new_conversation = False
    if conversation_id:
        conversation = await get_conversation(db, conversation_id)
        if not conversation:
            raise ValueError('对话不存在')
    else:
        is_new_conversation = True
        conversation_create = schemas.AiConversationCreate(
            model_id=request.model_id,
            title=request.message[:100],
            model_name=model_config.model_name,
            system_prompt=request.system_prompt,
        )
        conversation = await create_conversation(db, conversation_create)
        conversation_id = conversation.id

    # yield 会话 ID
    yield {
        'type': 'session',
        'conversation_id': conversation_id,
    }

    # 处理附加文件：将文件路径信息注入用户消息，AI 通过 read_file 工具按需读取
    files_context = []
    if request.files:
        for file_path in request.files:
            if not file_path or not os.path.isfile(file_path):
                files_context.append(f'  - [文件不存在] {file_path}')
                continue
            try:
                fsize = _format_size(os.path.getsize(file_path))
                fname = os.path.basename(file_path)
                files_context.append(f'  - {fname} ({fsize}) — 路径: {file_path}')
            except Exception as e:
                files_context.append(f'  - {file_path} — [{str(e)}]')

    if files_context:
        file_ref = (
            '\n\n[用户上传了以下文件，你可以使用 read_file 工具读取它们的内容]\n'
            + '\n'.join(files_context)
        )
        user_msg_content = request.message + file_ref
    else:
        user_msg_content = request.message

    # 先构建历史消息（不含当前用户消息），避免 history 与 message 重复
    history_messages, _ = await build_conversation_messages(
        db, conversation_id,
        system_prompt=request.system_prompt,
    )
    # 去掉 system 消息，Agent 自己会加
    history = [m for m in history_messages if m['role'] != 'system']

    # 上下文压缩：如果历史消息过多，自动压缩旧消息节省 token
    try:
        from app.ai.provider.base import ChatMessage as ChatMsg
        from app.ai.agent.context_compressor import compress_messages
        from app.ai.provider.factory import get_model_from_db

        chat_msgs = [
            ChatMsg(role=h['role'], content=h.get('content', ''))
            for h in history
        ]
        if len(chat_msgs) > 20:  # 超过 20 条才触发压缩（节省 token）
            llm_for_compress = await get_model_from_db(model_config)
            compressed = await compress_messages(chat_msgs, llm=llm_for_compress)
            history = [
                {'role': m.role, 'content': m.content}
                for m in compressed
            ]
            logger.info(f'[Service] 上下文压缩: {len(chat_msgs)} 条 → {len(compressed)} 条')
    except Exception as e:
        logger.warning(f'[Service] 上下文压缩失败（不影响主流程）: {e}')

    # 再保存用户消息到 DB（含文件内容）
    user_msg = schemas.AiMessageCreate(
        conversation_id=conversation_id,
        role='user',
        content=user_msg_content,
    )
    await add_message(db, user_msg)

    # 意图路由：决定启用哪些工具
    enabled_tools = resolve_tools(
        user_input=request.message,
        enabled_tools=request.enabled_tools,
        smart_mode=request.smart_mode,
    )

    # 如果上传了文件，确保 read_file 工具始终可用
    if request.files and 'read_file' not in enabled_tools:
        enabled_tools.append('read_file')
        logger.debug(f'[Service] 有附件文件，强制启用 read_file 工具')

    # 获取/创建 Agent
    agent = await _get_or_create_agent(
        session_id=str(conversation_id),
        model_instance=model_config,
        user_message=request.message,
        enabled_tools=enabled_tools,
        system_prompt=request.system_prompt,
    )

    full_content = ''
    reasoning_content = ''
    usage_info = {}

    try:
        # 通过 Agent 异步循环处理
        async for event in agent.achat(
            message=user_msg_content,
            history=history,
        ):
            event_type = event.get('type', '')

            if event_type == 'content':
                full_content += event.get('content', '')
                yield event

            elif event_type == 'reasoning':
                reasoning_content += event.get('content', '')
                yield event

            elif event_type == 'tool_calls':
                yield event

            elif event_type == 'tool_confirm':
                # 透传给前端，等待用户确认
                yield event

            elif event_type == 'tool_executing':
                yield event

            elif event_type == 'tool_result':
                yield event

            elif event_type == 'error':
                yield event
                if full_content:
                    assistant_msg_create = schemas.AiMessageCreate(
                        conversation_id=conversation_id,
                        role='assistant',
                        content=full_content,
                    )
                    await add_message(db, assistant_msg_create, reasoning_content=reasoning_content)
                return

            elif event_type == 'stop':
                usage_info = event.get('usage', {})

        # Agent 循环结束，保存结果
        if full_content:
            prompt_tokens = usage_info.get('prompt_tokens', 0)
            completion_tokens = usage_info.get('completion_tokens', 0)
            total_tokens = usage_info.get('total_tokens', 0)

            # 如果 Provider 没返回 usage，简单估算
            if total_tokens <= 0:
                prompt_tokens = len(request.message)
                completion_tokens = len(full_content)
                total_tokens = prompt_tokens + completion_tokens

            assistant_msg_create = schemas.AiMessageCreate(
                conversation_id=conversation_id,
                role='assistant',
                content=full_content,
            )
            await add_message(db, assistant_msg_create, token_usage=total_tokens, reasoning_content=reasoning_content)

            # 更新对话统计
            conversation.token_usage_prompt += prompt_tokens
            conversation.token_usage_completion += completion_tokens
            await db.flush()

            # 自动生成标题（首条对话才生成）
            if is_new_conversation:
                await _auto_generate_title(db, conversation, request.message, full_content)

            # 记录用量日志
            usage_log = models.AiUsageLog(
                user_id=user_id,
                model_id=model_config.id,
                conversation_id=conversation_id,
                conversation_title=conversation.title or '',
                model_name=model_config.model_name,
                provider=model_config.provider,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )
            db.add(usage_log)
            logger.info(f'[Agent] 已记录用量: user={user_id}, total_tokens={total_tokens}')

        # yield 最终 usage
        if usage_info:
            yield {'type': 'usage', **usage_info}

    except Exception as e:
        logger.error(f'Agent 流式聊天异常: {e}')
        yield {'type': 'error', 'message': str(e)}
        if full_content:
            assistant_msg_create = schemas.AiMessageCreate(
                conversation_id=conversation_id,
                role='assistant',
                content=full_content,
            )
            await add_message(db, assistant_msg_create, reasoning_content=reasoning_content)


# ==================== AI 工具集 ====================

def get_toolsets() -> list:
    """获取可用工具集列表（供前端动态展示）"""
    from app.ai.agent.toolsets import TOOLSETS as _TOOLSETS
    return [
        {'id': ts_id, 'name': ts_info['name'], 'tools': ts_info.get('tools', [])}
        for ts_id, ts_info in _TOOLSETS.items()
    ]


# ==================== AI 用量统计 ====================

async def get_usage_stats(
    db: AsyncSession,
    user_id: int,
    time_range: str = 'week',
) -> dict:
    """获取用量统计（汇总 + 按模型 + 按日趋势 + 最近明细）"""
    now = _get_localized_now()
    if time_range == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == 'week':
        start_date = now - timedelta(days=7)
    elif time_range == 'month':
        start_date = now - timedelta(days=30)
    else:
        start_date = None

    query = select(models.AiUsageLog).where(models.AiUsageLog.user_id == user_id)
    if start_date:
        query = query.where(models.AiUsageLog.created_at >= start_date)

    # 1. 汇总
    count_query = select(func.count()).where(models.AiUsageLog.user_id == user_id)
    sum_prompt = select(func.coalesce(func.sum(models.AiUsageLog.prompt_tokens), 0)).where(models.AiUsageLog.user_id == user_id)
    sum_completion = select(func.coalesce(func.sum(models.AiUsageLog.completion_tokens), 0)).where(models.AiUsageLog.user_id == user_id)
    sum_total = select(func.coalesce(func.sum(models.AiUsageLog.total_tokens), 0)).where(models.AiUsageLog.user_id == user_id)
    if start_date:
        count_query = count_query.where(models.AiUsageLog.created_at >= start_date)
        sum_prompt = sum_prompt.where(models.AiUsageLog.created_at >= start_date)
        sum_completion = sum_completion.where(models.AiUsageLog.created_at >= start_date)
        sum_total = sum_total.where(models.AiUsageLog.created_at >= start_date)

    total_requests = (await db.execute(count_query)).scalar() or 0
    total_input = (await db.execute(sum_prompt)).scalar() or 0
    total_output = (await db.execute(sum_completion)).scalar() or 0
    total_tokens = (await db.execute(sum_total)).scalar() or 0

    # 2. 按模型分组
    by_model_query = (
        select(
            models.AiUsageLog.model_name,
            models.AiUsageLog.provider,
            func.count().label('request_count'),
            func.coalesce(func.sum(models.AiUsageLog.prompt_tokens), 0).label('input_tokens'),
            func.coalesce(func.sum(models.AiUsageLog.completion_tokens), 0).label('output_tokens'),
            func.coalesce(func.sum(models.AiUsageLog.total_tokens), 0).label('total_tokens'),
        )
        .where(models.AiUsageLog.user_id == user_id)
        .group_by(models.AiUsageLog.model_name, models.AiUsageLog.provider)
        .order_by(func.sum(models.AiUsageLog.total_tokens).desc())
    )
    if start_date:
        by_model_query = by_model_query.where(models.AiUsageLog.created_at >= start_date)
    by_model_result = await db.execute(by_model_query)
    by_model_list = [
        {
            'model_name': row.model_name,
            'provider': row.provider,
            'request_count': row.request_count,
            'input_tokens': row.input_tokens,
            'output_tokens': row.output_tokens,
            'total_tokens': row.total_tokens,
        }
        for row in by_model_result.all()
    ]

    # 3. 按日趋势
    daily_query = (
        select(
            func.date(models.AiUsageLog.created_at).label('date'),
            func.count().label('request_count'),
            func.coalesce(func.sum(models.AiUsageLog.prompt_tokens), 0).label('input_tokens'),
            func.coalesce(func.sum(models.AiUsageLog.completion_tokens), 0).label('output_tokens'),
            func.coalesce(func.sum(models.AiUsageLog.total_tokens), 0).label('total_tokens'),
        )
        .where(models.AiUsageLog.user_id == user_id)
        .group_by(func.date(models.AiUsageLog.created_at))
        .order_by('date')
    )
    if start_date:
        daily_query = daily_query.where(models.AiUsageLog.created_at >= start_date)
    daily_result = await db.execute(daily_query)
    daily_stats = [
        {
            'date': str(row.date) if row.date else '',
            'request_count': row.request_count,
            'input_tokens': row.input_tokens,
            'output_tokens': row.output_tokens,
            'total_tokens': row.total_tokens,
        }
        for row in daily_result.all()
    ]

    # 4. 最近 50 条明细
    recent_query = (
        select(models.AiUsageLog)
        .where(models.AiUsageLog.user_id == user_id)
        .order_by(models.AiUsageLog.created_at.desc())
        .limit(50)
    )
    if start_date:
        recent_query = recent_query.where(models.AiUsageLog.created_at >= start_date)
    recent_result = await db.execute(recent_query)
    recent_logs = recent_result.scalars().all()

    return {
        'summary': {
            'total_requests': total_requests,
            'total_input_tokens': total_input,
            'total_output_tokens': total_output,
            'total_tokens': total_tokens,
        },
        'by_model': by_model_list,
        'daily_stats': daily_stats,
        'recent_logs': [
            {
                'id': log.id,
                'conversation_id': log.conversation_id,
                'conversation_title': log.conversation_title or '',
                'model_name': log.model_name,
                'provider': log.provider,
                'prompt_tokens': log.prompt_tokens,
                'completion_tokens': log.completion_tokens,
                'total_tokens': log.total_tokens,
                'cost': log.cost or 0,
                'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else '',
            }
            for log in recent_logs
        ],
    }


async def get_usage_export(
    db: AsyncSession,
    user_id: int,
    time_range: str = 'week',
) -> list:
    """获取用量导出数据"""
    now = _get_localized_now()
    if time_range == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == 'week':
        start_date = now - timedelta(days=7)
    elif time_range == 'month':
        start_date = now - timedelta(days=30)
    else:
        start_date = None

    query = (
        select(models.AiUsageLog)
        .where(models.AiUsageLog.user_id == user_id)
        .order_by(models.AiUsageLog.created_at.desc())
    )
    if start_date:
        query = query.where(models.AiUsageLog.created_at >= start_date)

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            'date': log.created_at.strftime('%Y-%m-%d %H:%M:%S') if log.created_at else '',
            'model': log.model_name,
            'provider': log.provider,
            'input_tokens': log.prompt_tokens,
            'output_tokens': log.completion_tokens,
            'total_tokens': log.total_tokens,
            'cost': log.cost or 0,
        }
        for log in logs
    ]


async def reset_usage(db: AsyncSession, user_id: int) -> int:
    """清空当前用户的用量记录"""
    result = await db.execute(
        delete(models.AiUsageLog).where(models.AiUsageLog.user_id == user_id)
    )
    return result.rowcount

