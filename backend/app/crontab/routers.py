from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from middleware.auth import get_current_active_user
from config.database import get_crontab_db
from app.crontab import service, schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crontab", tags=["crontab"])


@router.get("/types", response_model=List[schemas.CrontabTypeInfo])
async def get_crontab_types():
    """获取支持的周期类型列表"""
    return schemas.CRONTAB_TYPES


@router.get("/list", response_model=schemas.CrontabTaskListResponse)
async def get_crontab_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[int] = Query(None, ge=0, le=1),
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_crontab_db),
):
    """获取计划任务列表"""
    tasks, total = await service.get_tasks(db, skip=skip, limit=limit, status=status)
    return {"total": total, "items": tasks, "skip": skip, "limit": limit}


@router.get("/{task_id}", response_model=schemas.CrontabTask)
async def get_crontab_task(
    task_id: int,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_crontab_db),
):
    """获取单个计划任务详情"""
    task = await service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return task


@router.post("/create", response_model=schemas.CrontabTask, status_code=status.HTTP_201_CREATED)
async def create_crontab_task(
    task_in: schemas.CrontabTaskCreate,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_crontab_db),
):
    """创建计划任务"""
    try:
        task = await service.create_task(db, task_in)
        return task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"创建计划任务失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{task_id}/update", response_model=schemas.CrontabTask)
async def update_crontab_task(
    task_id: int,
    task_in: schemas.CrontabTaskUpdate,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_crontab_db),
):
    """更新计划任务"""
    try:
        task = await service.update_task(db, task_id, task_in)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
        return task
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"更新计划任务失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{task_id}/delete")
async def delete_crontab_task(
    task_id: int,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_crontab_db),
):
    """删除计划任务"""
    success = await service.delete_task(db, task_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return {"message": "任务已删除", "task_id": task_id}


@router.post("/{task_id}/toggle", response_model=schemas.CrontabTask)
async def toggle_crontab_task(
    task_id: int,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_crontab_db),
):
    """切换计划任务启用/停用状态"""
    task = await service.toggle_task_status(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return task


@router.post("/{task_id}/run", response_model=schemas.CrontabTaskRunResult)
async def run_crontab_task_now(
    task_id: int,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_crontab_db),
):
    """立即执行计划任务"""
    try:
        result = await service.execute_task_now(db, task_id)
        return result
    except ValueError as e:
        detail = str(e)
        if "不存在" in detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    except Exception as e:
        logger.error(f"执行计划任务失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{task_id}/log")
async def get_crontab_task_log(
    task_id: int,
    lines: int = Query(100, ge=1, le=5000),
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_crontab_db),
):
    """获取计划任务执行日志"""
    log_data = await service.get_task_log(db, task_id, lines=lines)
    if not log_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return log_data


@router.post("/{task_id}/log/clear")
async def clear_crontab_task_log(
    task_id: int,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_crontab_db),
):
    """清空计划任务执行日志"""
    success = await service.clear_task_log(db, task_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return {"message": "日志已清空", "task_id": task_id}
