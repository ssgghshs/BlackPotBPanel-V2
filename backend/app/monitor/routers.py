from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from . import schemas, service

from middleware.auth import get_current_active_user

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/host-info")
async def get_host_info(current_user=Depends(get_current_active_user)):
    try:
        return await service.get_host_info()
    except Exception as e:
        safe_error = service.safe_format_error(e)
        raise HTTPException(status_code=500, detail=f"获取主机信息失败: {safe_error}")


@router.get("/system-info")
async def get_system_info(current_user=Depends(get_current_active_user)):
    try:
        return await service.get_system_info()
    except Exception as e:
        safe_error = service.safe_format_error(e)
        raise HTTPException(status_code=500, detail=f"获取系统资源占用失败: {safe_error}")


@router.get("/network-traffic")
async def get_network_traffic(current_user=Depends(get_current_active_user)):
    try:
        return await service.get_network_traffic()
    except Exception as e:
        safe_error = service.safe_format_error(e)
        raise HTTPException(status_code=500, detail=f"获取网络流量信息失败: {safe_error}")


@router.get("/disk-io")
async def get_disk_io(current_user=Depends(get_current_active_user)):
    try:
        return await service.get_disk_io()
    except Exception as e:
        safe_error = service.safe_format_error(e)
        raise HTTPException(status_code=500, detail=f"获取磁盘I/O信息失败: {safe_error}")


@router.get("/panel-resource", response_model=schemas.PanelResourceResponse)
async def get_panel_resource(current_user=Depends(get_current_active_user)):
    try:
        return service.get_panel_resource()
    except Exception as e:
        safe_error = service.safe_format_error(e)
        raise HTTPException(status_code=500, detail=f"获取面板资源占用失败: {safe_error}")
