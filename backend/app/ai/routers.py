from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession
from middleware.auth import get_current_active_user
from config.database import get_ai_db
from app.ai import service, schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


def _format_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f'{size_bytes:.1f}{unit}' if unit != 'B' else f'{size_bytes}B'
        size_bytes /= 1024
    return f'{size_bytes:.1f}TB'


# ==================== AI 模型配置管理 ====================

@router.get("/models/list", response_model=schemas.AiModelConfigListResponse)
async def get_ai_models(
    provider: Optional[str] = Query(None, description='按厂商筛选'),
    model_type: Optional[str] = Query(None, description='按模型类型筛选'),
    is_enabled: Optional[int] = Query(None, ge=0, le=1, description='按启用状态筛选'),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_ai_db),
):
    """获取 AI 模型列表（支持按厂商、类型、状态筛选）"""
    items, total = await service.get_model_configs(
        db, skip=skip, limit=limit,
        provider=provider, model_type=model_type, is_enabled=is_enabled,
    )
    return {"total": total, "items": items}


@router.get("/models/{model_id}", response_model=schemas.AiModelConfig)
async def get_ai_model(
    model_id: int,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_ai_db),
):
    """获取单个 AI 模型详情"""
    model_config = await service.get_model_config(db, model_id)
    if not model_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    return model_config


@router.post("/models/create", response_model=schemas.AiModelConfig, status_code=status.HTTP_201_CREATED)
async def create_ai_model(
    config_in: schemas.AiModelConfigCreate,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_ai_db),
):
    """创建 AI 模型配置"""
    try:
        model_config = await service.create_model_config(db, config_in)
        return model_config
    except Exception as e:
        logger.error(f"创建 AI 模型失败: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/models/{model_id}/update", response_model=schemas.AiModelConfig)
async def update_ai_model(
    model_id: int,
    config_in: schemas.AiModelConfigUpdate,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_ai_db),
):
    """更新 AI 模型配置（部分更新）"""
    model_config = await service.update_model_config(db, model_id, config_in)
    if not model_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    return model_config


@router.post("/models/{model_id}/delete")
async def delete_ai_model(
    model_id: int,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_ai_db),
):
    """删除 AI 模型配置"""
    success = await service.delete_model_config(db, model_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模型不存在")
    return {"message": "模型已删除", "model_id": model_id}


@router.post("/models/discover", response_model=schemas.AiModelDiscoverResponse)
async def discover_ai_models(
    req: schemas.AiModelDiscoverRequest,
    current_user=Depends(get_current_active_user),
):
    """通过 OpenAI 兼容 API 发现可用模型列表"""
    try:
        model_ids = await service.discover_models_from_api(
            base_url=req.base_url,
            api_key=req.api_key,
        )
        return {"models": model_ids}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"发现模型失败: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"发现模型失败: {str(e)}")


# ==================== AI 对话管理 ====================

@router.get("/conversations/list", response_model=schemas.AiConversationListResponse)
async def get_ai_conversations(
    model_id: Optional[int] = Query(None, ge=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_ai_db),
):
    """获取对话列表（可按模型筛选）"""
    items, total = await service.get_conversations(db, model_id=model_id, skip=skip, limit=limit)
    return {"total": total, "items": items}


@router.get("/conversations/{conversation_id}", response_model=schemas.AiConversation)
async def get_ai_conversation(
    conversation_id: int,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_ai_db),
):
    """获取单个对话详情"""
    conversation = await service.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    return conversation


@router.post("/conversations/create", response_model=schemas.AiConversation, status_code=status.HTTP_201_CREATED)
async def create_ai_conversation(
    conversation_in: schemas.AiConversationCreate,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_ai_db),
):
    """创建新对话"""
    try:
        conversation = await service.create_conversation(db, conversation_in)
        return conversation
    except Exception as e:
        logger.error(f"创建对话失败: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/conversations/{conversation_id}/update", response_model=schemas.AiConversation)
async def update_ai_conversation(
    conversation_id: int,
    conversation_in: schemas.AiConversationUpdate,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_ai_db),
):
    """更新对话信息"""
    conversation = await service.update_conversation(db, conversation_id, conversation_in)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    return conversation


@router.post("/conversations/{conversation_id}/switch-model", response_model=schemas.AiConversation)
async def switch_conversation_model(
    conversation_id: int,
    req: schemas.AiConversationSwitchModel,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_ai_db),
):
    """切换对话使用的模型"""
    conversation = await service.update_conversation_model(
        db, conversation_id, req.model_id, req.model_name
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    return conversation


@router.post("/conversations/{conversation_id}/delete")
async def delete_ai_conversation(
    conversation_id: int,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_ai_db),
):
    """删除对话（同时删除关联的消息）"""
    success = await service.delete_conversation(db, conversation_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对话不存在")
    return {"message": "对话已删除", "conversation_id": conversation_id}


# ==================== AI 消息 ====================

@router.get("/conversations/{conversation_id}/messages", response_model=schemas.AiMessageListResponse)
async def get_ai_messages(
    conversation_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=2000),
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_ai_db),
):
    """获取对话中的消息列表"""
    items, total = await service.get_messages(db, conversation_id, skip=skip, limit=limit)
    return {"total": total, "items": items}


@router.post("/conversations/{conversation_id}/messages/{message_id}/delete")
async def delete_ai_message(
    conversation_id: int,
    message_id: int,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_ai_db),
):
    """删除对话中的单条消息"""
    success = await service.delete_message(db, conversation_id, message_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")
    return {"message": "消息已删除", "message_id": message_id}


# ==================== AI 聊天 ====================

@router.post("/chat/stream")
async def stream_chat_with_ai(
    req: schemas.AiStreamChatRequest,
    current_user=Depends(get_current_active_user),
):
    """流式 AI 聊天 (SSE)"""

    async def event_generator():
        from config.database import AiAsyncSessionLocal

        async with AiAsyncSessionLocal() as db:
            try:
                async for event in service.stream_chat_with_model(db, req, user_id=current_user.id):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                await db.commit()
            except ValueError as e:
                await db.rollback()
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
            except Exception as e:
                await db.rollback()
                logger.error(f"AI 流式聊天失败: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
            finally:
                yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/chat/confirm")
async def confirm_tool_execution(
    req: schemas.AiToolConfirmRequest,
    current_user=Depends(get_current_active_user),
):
    """确认/拒绝高风险工具的执行"""
    success = service._confirm_agent_tool(
        conversation_id=req.conversation_id,
        call_id=req.call_id,
        confirmed=req.confirmed,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到对应的 Agent 或确认不匹配",
        )
    return {"message": "确认成功", "confirmed": req.confirmed}


@router.get("/tools/toolsets", response_model=schemas.AiToolsetsResponse)
async def get_ai_toolsets(
    current_user=Depends(get_current_active_user),
):
    """获取可用工具集列表"""
    items = service.get_toolsets()
    return {"toolsets": items}


# ==================== AI 文件上传 ====================

@router.post("/upload", response_model=schemas.AiUploadResponse)
async def upload_ai_file(
    file: UploadFile,
    current_user=Depends(get_current_active_user),
):
    """上传文件供 AI 对话使用（上传后返回服务端路径，可在 chat/stream 的 files 字段引用）"""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件名为空")

    content = await file.read()
    max_size = 50 * 1024 * 1024  # 50MB
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件过大（{_format_size(len(content))}），最大支持 50MB",
        )

    result = await service.save_uploaded_file(content, file.filename)
    logger.info(f'[AI] 上传文件: {file.filename} → {result.path} ({_format_size(result.size)})')
    return result


# ==================== AI 用量统计 ====================

@router.get("/usage", response_model=schemas.AiUsageResponse)
async def get_ai_usage(
    time_range: str = Query('week', description='时间范围: today/week/month/all'),
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_ai_db),
):
    """获取 AI 用量统计（汇总 + 按模型 + 按日趋势 + 最近明细）"""
    data = await service.get_usage_stats(db, user_id=current_user.id, time_range=time_range)
    return data


@router.get("/usage/export")
async def export_ai_usage(
    time_range: str = Query('week', description='时间范围: today/week/month/all'),
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_ai_db),
):
    """导出 AI 用量数据"""
    data = await service.get_usage_export(db, user_id=current_user.id, time_range=time_range)
    return {"data": data}


@router.post("/usage/reset", response_model=schemas.AiUsageResetResponse)
async def reset_ai_usage(
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_ai_db),
):
    """清空当前用户的 AI 用量记录"""
    deleted_count = await service.reset_usage(db, user_id=current_user.id)
    return {
        "deleted_count": deleted_count,
        "message": f"已清空 {deleted_count} 条用量记录",
    }
