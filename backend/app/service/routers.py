from fastapi import APIRouter, WebSocket, Query, HTTPException, Depends
import logging
from datetime import datetime
from typing import Optional
from app.service import service
from app.service import schemas
from app.service.schemas import ProcessListResponse, ProcessDetailResponse, NetworkConnectionListResponse
from app.service.service import get_process_list, get_process_detail, terminate_process, get_network_connections
from middleware.auth import get_current_active_user
from app.user import models as user_models

router = APIRouter(prefix="/service", tags=["service"])

logger = logging.getLogger(__name__)


@router.get("/processes", summary="获取系统进程列表")
async def processes(
    skip: int = 0,
    limit: int = 100,
    current_user: user_models.User = Depends(get_current_active_user)
):
    """
    获取系统中所有进程的详细信息列表
    
    - **参数**: skip: 跳过的进程数, limit: 返回的最大进程数
    - **返回数据**: 包含PID、名称、父进程PID、线程数、用户、状态、CPU使用率、内存使用率和启动时间的进程列表
    - **认证**: 需要用户登录
    """
    try:
        processes_list = get_process_list()
        total = len(processes_list)
        start = max(0, skip)
        end = start + max(0, limit)
        paged_processes = processes_list[start:end]
        return {
            "data": paged_processes,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取进程列表失败: {str(e)}")
        


@router.get("/process/{pid}", response_model=ProcessDetailResponse, summary="获取进程详情")
async def get_process(
    pid: int, 
    current_user: user_models.User = Depends(get_current_active_user)
    ):
    """
    根据PID获取进程的详细信息
    
    - **pid**: 进程ID
    - **返回数据**: 进程的详细信息，包括基本信息、连接信息、资源使用情况等
    - **认证**: 需要用户登录
    """
    try:
        process_detail = get_process_detail(pid)
        return process_detail
    except ValueError as e:
        if "不存在" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        elif "无权限" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取进程详情失败: {str(e)}")


@router.post("/process/{pid}/terminate", summary="终止指定进程")
async def terminate_process_endpoint(
    pid: int,
    current_user: user_models.User = Depends(get_current_active_user)
):
    """
    终止指定PID的进程
    
    - **pid**: 要终止的进程ID
    - **返回数据**: 操作结果，包含是否成功、进程信息和消息
    - **认证**: 需要用户登录
    - **错误处理**:
      - 404: 进程不存在
      - 403: 无权限终止进程
      - 400: 终止操作失败
      - 500: 服务器内部错误
    """
    try:
        result = terminate_process(pid)
        return result
    except ValueError as e:
        if "不存在" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        elif "无权限" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"终止进程失败: {str(e)}")


@router.get("/network/connections", summary="获取网络连接列表")
async def network_connections(
    skip: int = 0,
    limit: int = 100,
    current_user: user_models.User = Depends(get_current_active_user)
    ):
    """
    获取系统中所有网络连接的详细信息列表

    - **参数**: skip: 跳过的连接数, limit: 返回的最大连接数
    - **返回数据**: 包含类型、PID、名称、本地地址、远程地址和状态的网络连接列表
    - **认证**: 需要用户登录
    """
    try:
        connections_list = get_network_connections()
        total = len(connections_list)
        start = max(0, skip)
        end = start + max(0, limit)
        paged_connections = connections_list[start:end]
        return {
            "data": paged_connections,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取网络连接列表失败: {str(e)}")




