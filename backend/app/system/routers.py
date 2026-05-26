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
            message="成功获取环境配置"
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
            ("SSL_ENABLED" in config_dict)
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


       