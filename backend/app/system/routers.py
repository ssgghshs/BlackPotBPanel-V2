from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict
import logging
import asyncio  # 添加 asyncio 导入
from middleware.auth import get_current_active_user
from config.database import get_db  # 添加数据库依赖导入
from sqlalchemy.ext.asyncio import AsyncSession  # 添加异步会话导入
from app.user.schemas import RoleEnum  # 添加RoleEnum导入

# 导入系统服务模块和schemas
from app.system import schemas, service

router = APIRouter(prefix="/system", tags=["system"])

# 获取日志记录器
logger = logging.getLogger(__name__)

@router.get("/config/common", response_model=schemas.CommonSettingsResponse)
async def get_common_settings():
    """获取通用设置（LANGUAGE、THEME和LOGIN_NOTIFY）"""
    try:
        # 调用service层的函数获取通用设置
        common_settings = await service.get_common_settings()
        
        return schemas.CommonSettingsResponse(**common_settings)
    except Exception as e:
        logging.error(f"读取通用设置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="读取通用设置失败"
        )

@router.post("/config/common/update", response_model=schemas.CommonSettingsResponse)
async def update_common_settings(
    settings: schemas.CommonSettingsUpdate,
    current_user = Depends(get_current_active_user)
):
    """更新通用设置（LANGUAGE、THEME和LOGIN_NOTIFY）"""
    try:
        # 调用service层的函数更新通用设置
        updated_settings = await service.update_common_settings(settings)
        
        return schemas.CommonSettingsResponse(**updated_settings)
    except Exception as e:
        logging.error(f"更新通用设置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新通用设置失败"
        )

@router.get("/config", response_model=schemas.EnvConfigResponse)
async def get_env_config(current_user = Depends(get_current_active_user)):
    """获取环境配置"""
    try:
        # 检查用户角色，权限控制保留在路由层
        user_role = "ADMIN" if hasattr(current_user, 'role') and current_user.role == RoleEnum.ADMIN.value else "USER"
        
        # 调用service层的函数获取配置
        allowed_configs = await service.get_env_config(user_role)
        
        return schemas.EnvConfigResponse(
            configs=allowed_configs,
            message="success"
        )
    except Exception as e:
        logging.error(f"读取环境配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="读取环境配置失败"
        )

@router.post("/config/update", response_model=schemas.EnvConfigResponse)
async def update_env_config(
    config: schemas.EnvConfigUpdate,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)  # 添加数据库会话依赖
):
    """更新环境配置"""
    try:
        # 检查用户角色，权限控制保留在路由层
        user_role = "ADMIN" if hasattr(current_user, 'role') and current_user.role == RoleEnum.ADMIN.value else "USER"
        
        # 调用service层的函数更新配置
        allowed_configs = await service.update_env_config(config, user_role)
        
        # 检查是否修改了需要重启的配置项，如果是则重启服务
        config_dict = config.model_dump(exclude_unset=True)
        if (
            ("TIMEZONE" in config_dict and config_dict["TIMEZONE"] is not None) or
            ("DEBUG" in config_dict) or
            ("ENABLE_DOCS" in config_dict) or
            ("ACCESS_TOKEN_EXPIRE_MINUTES" in config_dict) or
            ("HOST" in config_dict) or
            ("PORT" in config_dict) or
            ("SSL_ENABLED" in config_dict) or
            ("LOGIN_LIMIT" in config_dict) or
            ("SECURITY_ENTRANCE" in config_dict) or
            ("API_OPEN" in config_dict)
        ):
            # 异步执行服务重启
            asyncio.create_task(service.restart_service())

        return schemas.EnvConfigResponse(
            configs=allowed_configs,
            message="环境配置更新成功，部分配置需要重启服务才能完全生效"
        )
    except Exception as e:
        logging.error(f"更新环境配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新环境配置失败"
        )




@router.get("/config/recycle", response_model=Dict[str, str])
async def get_recycle_config(
    current_user = Depends(get_current_active_user),    
):
    """获取回收站配置"""
    try:
        # 调用service层的函数获取配置
        configs = await service.get_common_settings()
        
        # 只返回回收站配置
        return {"RECYCLE": configs.get("RECYCLE", "True")}
    except Exception as e:
        logging.error(f"读取回收站配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="读取回收站配置失败"
        )

@router.post("/config/recycle/update", response_model=Dict[str, str])
async def update_recycle_config(
    recycle_config: schemas.RecycleConfigUpdate,
    current_user = Depends(get_current_active_user),    
):
    """修改回收站配置"""
    try:
        # 调用service层的函数更新配置
        # 创建CommonSettingsUpdate对象，只设置RECYCLE字段
        update_data = schemas.CommonSettingsUpdate(
            RECYCLE=recycle_config.RECYCLE
        )
        
        # 更新配置
        updated_settings = await service.update_common_settings(update_data)
        
        # 只返回更新后的回收站配置
        return {"RECYCLE": updated_settings.get("RECYCLE", "True")}
    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"更新回收站配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新回收站配置失败"
        )

@router.post("/restart", response_model=schemas.ServiceRestartResponse)
async def restart_service(
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """重启服务"""
    try:
        # 检查是否为管理员
        if current_user.role != RoleEnum.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以重启服务"
            )

        # 执行服务重启逻辑
        result = await service.restart_service()

        logger.info(f"服务已成功重启，结果: {result}")
        # 使用返回的 result 数据构建响应
        return schemas.ServiceRestartResponse(
            message=result.get("message", "服务已成功重启"),
            status=result.get("status", "success")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重启服务失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重启服务失败: {str(e)}"
        )


@router.get("/config/ssl", response_model=schemas.SSLCertResponse)
async def get_ssl_cert(
    current_user = Depends(get_current_active_user)
):
    """获取SSL证书和私钥内容"""
    try:
        # 检查是否为管理员
        if current_user.role != RoleEnum.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以获取SSL证书内容"
            )

        # 获取SSL证书内容
        cert_content = service.get_ssl_cert_content()

        return schemas.SSLCertResponse(
            cert_content=cert_content.get("cert_content"),
            key_content=cert_content.get("key_content"),
            message="成功获取SSL证书内容"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取SSL证书内容失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取SSL证书内容失败: {str(e)}"
        )

@router.post("/config/ssl/update", response_model=schemas.SSLCertResponse)
async def update_ssl_cert(
    ssl_data: schemas.SSLCertUpdate,
    current_user = Depends(get_current_active_user)
):
    """更新SSL证书和私钥内容"""
    try:
        # 检查是否为管理员
        if current_user.role != RoleEnum.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以更新SSL证书内容"
            )

        # 更新SSL证书内容
        await service.update_ssl_cert_content(
            cert_content=ssl_data.cert_content,
            key_content=ssl_data.key_content
        )

        # 获取更新后的证书内容
        updated_cert = service.get_ssl_cert_content()

        return schemas.SSLCertResponse(
            cert_content=updated_cert.get("cert_content"),
            key_content=updated_cert.get("key_content"),
            message="SSL证书和私钥更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新SSL证书内容失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新SSL证书内容失败: {str(e)}"
        )


# ==================== 系统设置（服务器设置）====================

@router.get("/settings", response_model=schemas.SystemSettingsResponse, summary="获取所有系统设置（合并接口）")
async def get_system_settings(
    current_user = Depends(get_current_active_user)
):
    """获取所有系统设置（DNS、Swap、时区、Hosts、内存盘、镜像源等）"""
    try:
        settings = await service.get_all_settings()
        return schemas.SystemSettingsResponse(**settings)
    except Exception as e:
        logger.error(f"获取系统设置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统设置失败: {str(e)}"
        )


@router.post("/dns/set", summary="设置DNS")
async def set_dns(
    dns_data: schemas.DNSConfig,
    current_user = Depends(get_current_active_user)
):
    """设置DNS服务器地址"""
    try:
        result = service.set_dns_config(dns1=dns_data.dns1, dns2=dns_data.dns2)
        return result
    except Exception as e:
        logger.error(f"设置DNS失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/dns/test", summary="测试DNS可用性")
async def test_dns(
    dns_data: schemas.DNSConfig,
    current_user = Depends(get_current_active_user)
):
    """测试指定的DNS服务器是否可用"""
    try:
        result = service.test_dns(dns1=dns_data.dns1, dns2=dns_data.dns2)
        return result
    except Exception as e:
        logger.error(f"测试DNS失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/swap/set", summary="设置Swap")
async def set_swap(
    swap_data: schemas.SwapSetRequest,
    current_user = Depends(get_current_active_user)
):
    """设置Swap虚拟内存大小（设为0则关闭Swap）"""
    try:
        result = service.set_swap(size=swap_data.size)
        return result
    except Exception as e:
        logger.error(f"设置Swap失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/timezone/set", summary="设置时区")
async def set_timezone(
    tz_data: schemas.TimezoneSetRequest,
    current_user = Depends(get_current_active_user)
):
    """设置系统时区"""
    try:
        result = service.set_timezone(area=tz_data.area, zone=tz_data.zone)
        return result
    except Exception as e:
        logger.error(f"设置时区失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/time/sync", summary="同步系统时间")
async def sync_system_time(
    current_user = Depends(get_current_active_user)
):
    """从网络同步系统时间"""
    try:
        result = service.sync_time()
        return result
    except Exception as e:
        logger.error(f"同步时间失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/password", summary="修改系统密码")
async def set_system_password(
    pwd_data: schemas.PasswordSetRequest,
    current_user = Depends(get_current_active_user)
):
    """修改系统用户密码"""
    try:
        result = service.set_password(
            user=pwd_data.user,
            password=pwd_data.password,
            confirm_password=pwd_data.confirm_password
        )
        return result
    except Exception as e:
        logger.error(f"修改密码失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/memory-disk", summary="创建内存盘")
async def create_memory_disk(
    disk_data: schemas.MemoryDiskCreate,
    current_user = Depends(get_current_active_user)
):
    """创建内存盘（tmpfs挂载）"""
    try:
        result = service.create_memory_disk(path=disk_data.path, size=disk_data.size)
        return result
    except Exception as e:
        logger.error(f"创建内存盘失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/memory-disk/delete", summary="删除内存盘")
async def delete_memory_disk(
    disk_data: schemas.MemoryDiskDelete,
    current_user = Depends(get_current_active_user)
):
    """卸载并删除内存盘"""
    try:
        result = service.delete_memory_disk(path=disk_data.path)
        return result
    except Exception as e:
        logger.error(f"删除内存盘失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/hosts", summary="添加/修改Hosts")
async def add_hosts(
    hosts_data: schemas.HostsCreateRequest,
    current_user = Depends(get_current_active_user)
):
    """添加或修改Hosts记录"""
    try:
        result = service.add_hosts(domain=hosts_data.domain, ip=hosts_data.ip)
        return result
    except Exception as e:
        logger.error(f"添加Hosts失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/hosts/delete", summary="删除Hosts")
async def delete_hosts(
    hosts_data: schemas.HostsDeleteRequest,
    current_user = Depends(get_current_active_user)
):
    """删除Hosts记录"""
    try:
        result = service.delete_hosts(domain=hosts_data.domain)
        return result
    except Exception as e:
        logger.error(f"删除Hosts失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/hosts/toggle", summary="暂停/启用Hosts")
async def toggle_hosts(
    toggle_data: schemas.HostsToggleRequest,
    current_user = Depends(get_current_active_user)
):
    """暂停或启用指定的Hosts记录"""
    try:
        result = service.toggle_hosts(domain=toggle_data.domain, act=toggle_data.act)
        return result
    except Exception as e:
        logger.error(f"操作Hosts失败: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/config/api/generate-key", response_model=dict)
async def generate_api_key(
    current_user = Depends(get_current_active_user)
):
    """生成新的 API 接口密钥"""
    try:
        if current_user.role != RoleEnum.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以生成 API 密钥"
            )
        from middleware.api_auth import generate_api_key, _read_api_config, _write_api_config
        new_key = generate_api_key()
        api_cfg = _read_api_config()
        api_cfg["API_KEY"] = new_key
        _write_api_config(api_cfg)
        return {"code": 200, "message": "API 密钥已生成", "data": {"API_KEY": new_key}}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"生成 API 密钥失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成 API 密钥失败: {str(e)}"
        )