from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, update, delete
from app.host import models, schemas
from typing import List, Optional, Tuple, Dict
import logging
import asyncio
import platform
import subprocess
# 导入加密工具
from utils.encryption import encrypt_password, decrypt_password
# 导入生成令牌所需的模块
import time
import hmac
import hashlib

logger = logging.getLogger(__name__)
from config.settings import settings

async def create_host(db: AsyncSession, host: schemas.HostCreate) -> models.Host:
    """创建主机"""
    # 加密密码（如果提供了密码且使用密码认证）
    host_data = host.dict()
    if host_data.get("password") and host_data.get("auth_method", "password") == "password":
        host_data["password"] = encrypt_password(host_data["password"])
    elif host_data.get("auth_method") == "key":
        # 如果是密钥认证，不存储密码
        host_data["password"] = None
        # 加密私钥密码（如果提供了私钥密码）
        if host_data.get("private_key_password"):
            host_data["private_key_password"] = encrypt_password(host_data["private_key_password"])
        # 注意：在实际应用中，私钥通常不应该直接存储在数据库中
        # 这里仅作演示，实际应用中应该使用更安全的方式处理
        # 例如：将私钥存储在安全的密钥管理系统中，或加密后存储
    else:
        # 确保没有设置私钥字段
        host_data["private_key"] = None
        host_data["private_key_password"] = None
    
    db_host = models.Host(**host_data)
    db.add(db_host)
    await db.commit()
    await db.refresh(db_host)
    return db_host

async def get_hosts(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[models.Host]:
    """获取主机列表"""
    result = await db.execute(select(models.Host).offset(skip).limit(limit))
    hosts = result.scalars().all()
    return list(hosts)

async def get_host(db: AsyncSession, host_id: int) -> Optional[models.Host]:
    """根据ID获取主机"""
    result = await db.execute(select(models.Host).where(models.Host.id == host_id))
    return result.scalar_one_or_none()

async def update_host(db: AsyncSession, host_id: int, host_update: schemas.HostUpdate) -> Optional[models.Host]:
    """更新主机信息"""
    # 先获取主机
    db_host = await get_host(db, host_id)
    if not db_host:
        return None
    
    # 更新主机信息
    update_data = host_update.dict(exclude_unset=True)
    
    # 处理密码加密和私钥
    if "auth_method" in update_data:
        if update_data["auth_method"] == "password":
            # 如果切换到密码认证，清除私钥和私钥密码
            update_data["private_key"] = None
            update_data["private_key_password"] = None
            # 如果提供了密码，则加密
            if update_data.get("password"):
                update_data["password"] = encrypt_password(update_data["password"])
        elif update_data["auth_method"] == "key":
            # 如果切换到密钥认证，清除密码
            update_data["password"] = None
            # 加密私钥密码（如果提供了私钥密码）
            if update_data.get("private_key_password"):
                update_data["private_key_password"] = encrypt_password(update_data["private_key_password"])
            # 注意：在实际应用中，私钥通常不应该直接存储在数据库中
            # 这里仅作演示，实际应用中应该使用更安全的方式处理
    else:
        # 如果没有更改认证方式，根据当前认证方式处理
        if getattr(db_host, 'auth_method', 'password') == "password":
            # 密码认证模式
            if "password" in update_data and update_data["password"]:
                update_data["password"] = encrypt_password(update_data["password"])
            # 确保私钥字段为空
            if "private_key" in update_data:
                update_data["private_key"] = None
            if "private_key_password" in update_data:
                update_data["private_key_password"] = None
        elif getattr(db_host, 'auth_method', 'password') == "key":
            # 密钥认证模式
            if "password" in update_data:
                # 密钥认证模式下不应该有密码
                update_data["password"] = None
            # 加密私钥密码（如果提供了私钥密码）
            if "private_key_password" in update_data and update_data["private_key_password"]:
                update_data["private_key_password"] = encrypt_password(update_data["private_key_password"])
    
    for key, value in update_data.items():
        setattr(db_host, key, value)
    
    await db.commit()
    await db.refresh(db_host)
    return db_host

async def delete_host(db: AsyncSession, host_id: int) -> bool:
    """删除主机"""
    # 检查是否为系统创建的本机配置（127.0.0.1且is_system_created为True），如果是则不允许删除
    host = await get_host(db, host_id)
    if host and getattr(host, 'address', '') == "127.0.0.1" and getattr(host, 'is_system_created', False):
        raise ValueError("不允许删除系统创建的本机配置")
    
    result = await db.execute(delete(models.Host).where(models.Host.id == host_id))
    await db.commit()
    return result.rowcount > 0

async def check_host_status(host_address: str, port: int = 22, timeout: int = 5) -> dict:
    """检测主机状态（通过TCP连接测试）
    
    Args:
        host_address: 主机地址
        port: 端口号，默认为22（SSH端口）
        timeout: 超时时间（秒）
        
    Returns:
        dict: 包含状态信息的字典
    """
    try:
        # 使用TCP连接测试主机状态
        async def _tcp_connect():
            try:
                # 创建socket连接
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host_address, port),
                    timeout=timeout
                )
                # 关闭连接
                writer.close()
                await writer.wait_closed()
                return True, "TCP连接成功"
            except asyncio.TimeoutError:
                return False, f"连接超时（超过{timeout}秒）"
            except Exception as e:
                return False, f"连接失败: {str(e)}"
        
        # 执行连接测试
        is_alive, message = await _tcp_connect()
        
        return {
            "host": host_address,
            "port": port,
            "status": "online" if is_alive else "offline",
            "is_alive": is_alive,
            "response": message if is_alive else "",
            "error": "" if is_alive else message
        }
    except Exception as e:
        return {
            "host": host_address,
            "port": port,
            "status": "offline",
            "is_alive": False,
            "response": "",
            "error": f"检测主机状态时发生错误: {str(e)}"
        }


def generate_terminal_token(host_id: int, secret_key: str) -> str:
    """生成终端连接令牌
    
    Args:
        host_id: 主机ID
        secret_key: 用于签名的密钥
        
    Returns:
        str: 生成的令牌，格式为 host_id:timestamp:signature
    """
    timestamp = int(time.time())
    message = f"{host_id}:{timestamp}"
    signature = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"{host_id}:{timestamp}:{signature}"


# HostCommand 相关的服务函数
async def create_host_command(db: AsyncSession, command: schemas.HostCommandCreate) -> models.HostCommand:
    """创建主机命令"""
    db_command = models.HostCommand(**command.dict())
    db.add(db_command)
    await db.commit()
    await db.refresh(db_command)
    return db_command

async def get_host_commands(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[models.HostCommand]:
    """获取主机命令列表"""
    result = await db.execute(select(models.HostCommand).offset(skip).limit(limit))
    commands = result.scalars().all()
    return list(commands)

async def get_host_command(db: AsyncSession, command_id: int) -> Optional[models.HostCommand]:
    """根据ID获取主机命令"""
    result = await db.execute(select(models.HostCommand).where(models.HostCommand.id == command_id))
    return result.scalar_one_or_none()

async def update_host_command(db: AsyncSession, command_id: int, command_update: schemas.HostCommandUpdate) -> Optional[models.HostCommand]:
    """更新主机命令"""
    db_command = await get_host_command(db, command_id)
    if not db_command:
        return None
    
    update_data = command_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_command, key, value)
    
    await db.commit()
    await db.refresh(db_command)
    return db_command

async def delete_host_command(db: AsyncSession, command_id: int) -> bool:
    """删除主机命令"""
    result = await db.execute(delete(models.HostCommand).where(models.HostCommand.id == command_id))
    await db.commit()
    return result.rowcount > 0


# 本机ssh服务相关的服务函数
from app.host.schemas import SSHServiceAction, SSHServiceOperationResponse
from utils.ssh_utils import SSHServiceChecker

async def operate_local_ssh_service(action: SSHServiceAction) -> SSHServiceOperationResponse:
    """操作本机SSH服务（启动/停止/重启）
    
    Args:
        action: SSH服务操作类型，来自SSHServiceAction枚举
        
    Returns:
        SSHServiceOperationResponse: 操作结果响应对象
    """
    import asyncio
    import functools
    try:
        # 将枚举值转换为字符串
        action_str = action.value
        
        # 调用工具类执行服务操作（异步方式）
        loop = asyncio.get_event_loop()
        success, message = await loop.run_in_executor(None, functools.partial(SSHServiceChecker.operate_ssh_service, action_str))
        
        # 获取操作后的服务状态（转换为布尔值，异步方式）
        new_status = await loop.run_in_executor(None, SSHServiceChecker.is_ssh_running)
        
        # 返回响应对象
        return SSHServiceOperationResponse(
            success=success,
            message=message,
            status=new_status
        )
        
    except Exception as e:
        # 捕获所有异常并记录日志
        logger.error(f"操作SSH服务时发生错误: {str(e)}")
        return SSHServiceOperationResponse(
            success=False,
            message=f"操作失败: {str(e)}",
            status=False  # 错误情况下返回False表示服务未运行
        )

async def get_local_ssh_config() -> schemas.SSHConfigInfo:
    """获取本机SSH配置信息
    
    Returns:
        schemas.SSHConfigInfo: 包含本机SSH配置信息的对象
    """
    import getpass
    import asyncio
    import functools
    # 导入我们新创建的SSH工具类
    from utils.ssh_utils import SSHServiceChecker, SSHConfigParser, get_default_ssh_config
    
    # 获取默认配置
    config = get_default_ssh_config()
    
    # 异步检查SSH安装状态和运行状态
    loop = asyncio.get_event_loop()
    config["install"] = await loop.run_in_executor(None, SSHServiceChecker.is_ssh_installed)
    config["status"] = await loop.run_in_executor(None, SSHServiceChecker.is_ssh_running)
    
    # 获取当前用户名
    config["currentUser"] = getpass.getuser()
    
    # 如果SSH已安装，尝试解析配置文件
    if config["install"]:
        # 异步查找配置文件
        config_path = await loop.run_in_executor(None, SSHServiceChecker.find_ssh_config)
        if config_path:
            # 异步解析配置文件
            parsed_config = await loop.run_in_executor(None, functools.partial(SSHConfigParser.parse_config_file, config_path))
            # 更新配置（只更新解析到的值，保留默认值）
            config.update(parsed_config)
    
    # 创建并返回SSHConfigInfo对象
    return schemas.SSHConfigInfo(**config)

async def update_local_ssh_config(config_update: schemas.SSHConfigUpdate) -> tuple[bool, str]:
    """更新本地SSH配置参数
    
    Args:
        config_update: 要更新的SSH配置项
        
    Returns:
        tuple[bool, str]: (是否更新成功, 消息)
    """
    import asyncio
    import functools
    try:
        # 检查SSH是否安装（异步方式）
        loop = asyncio.get_event_loop()
        ssh_installed = await loop.run_in_executor(None, SSHServiceChecker.is_ssh_installed)
        if not ssh_installed:
            return False, "SSH服务未安装，无法更新配置"
        
        # 构建更新字典
        updates = {}
        
        # 将非None的配置项添加到更新字典中
        if config_update.port is not None:
            # 验证端口号是否为有效的数字字符串
            try:
                port_num = int(config_update.port)
                if not (1 <= port_num <= 65535):
                    return False, "端口号必须在1-65535之间"
                updates["port"] = config_update.port
            except ValueError:
                return False, "端口号必须是有效的数字"
        
        if config_update.passwordAuthentication is not None:
            # 验证是否为yes或no
            if config_update.passwordAuthentication.lower() not in ["yes", "no"]:
                return False, "密码认证状态必须是'yes'或'no'"
            updates["passwordAuthentication"] = config_update.passwordAuthentication.lower()
        
        if config_update.pubkeyAuthentication is not None:
            # 验证是否为yes或no
            if config_update.pubkeyAuthentication.lower() not in ["yes", "no"]:
                return False, "公钥认证状态必须是'yes'或'no'"
            updates["pubkeyAuthentication"] = config_update.pubkeyAuthentication.lower()
        
        if config_update.permitRootLogin is not None:
            # 验证是否为有效的值
            valid_values = ["yes", "no", "without-password", "forced-commands-only"]
            if config_update.permitRootLogin.lower() not in valid_values:
                return False, f"允许root登录状态必须是以下值之一: {', '.join(valid_values)}"
            updates["permitRootLogin"] = config_update.permitRootLogin.lower()
        
        if config_update.useDNS is not None:
            # 验证是否为yes或no
            if config_update.useDNS.lower() not in ["yes", "no"]:
                return False, "DNS解析功能状态必须是'yes'或'no'"
            updates["useDNS"] = config_update.useDNS.lower()
        
        # 如果没有需要更新的配置项
        if not updates:
            return True, "没有需要更新的配置项"
        
        # 调用SSHServiceChecker更新配置（异步方式）
        success, message = await loop.run_in_executor(None, functools.partial(SSHServiceChecker.update_ssh_config, updates))
        
        logger.info(f"SSH configuration update result: {success}, message: {message}")
        
        return success, message
        
    except Exception as e:
        logger.error(f"更新本地SSH配置失败: {e}")
        return False, f"更新配置时发生异常: {str(e)}"

async def get_local_ssh_config_file() -> schemas.SSHConfigFile:
    """获取本机SSH配置文件内容
    
    Returns:
        schemas.SSHConfigFile: 包含SSH配置文件路径和内容的对象
    
    Raises:
        HTTPException: 当获取配置文件失败时抛出
    """
    try:
        from utils.ssh_utils import SSHServiceChecker
        
        # 获取配置文件路径和内容（使用异步方法）
        config_path, content, success = await SSHServiceChecker.get_ssh_config_content_async()
        
        if not success:
            raise Exception(content)  # content中包含错误消息
        
        # 返回配置文件对象
        return schemas.SSHConfigFile(path=config_path, content=content)
        
    except Exception as e:
        logger.error(f"获取SSH配置文件内容失败: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))

async def get_local_authorized_keys_file() -> schemas.SSHAuthKeysFile:
    """获取本机SSH authorized_keys文件内容
    
    Returns:
        schemas.SSHAuthKeysFile: 包含authorized_keys文件路径和内容的对象
    
    Raises:
        HTTPException: 当获取authorized_keys文件失败时抛出
    """
    try:
        from utils.ssh_utils import SSHServiceChecker
        
        # 获取authorized_keys文件路径和内容（使用异步方法）
        keys_path, content, success = await SSHServiceChecker.get_authorized_keys_content_async()
        
        if not success:
            raise Exception(content)  # content中包含错误消息
        
        # 返回authorized_keys文件对象
        return schemas.SSHAuthKeysFile(path=keys_path, content=content)
        
    except Exception as e:
        logger.error(f"获取authorized_keys文件内容失败: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


async def get_ssh_logs(query: schemas.SSHLogQuery) -> schemas.SSHLogResponse:
    """获取SSH登录日志
    
    Args:
        query: SSH日志查询参数，包含分页、关键字搜索和状态过滤等信息
        
    Returns:
        schemas.SSHLogResponse: 包含分页的SSH登录日志和总条数的响应对象
    """
    try:
        from utils.ssh_utils import SSHLogReader
        import geoip2.database
        import os
        import ipaddress
        import logging
        import asyncio
        import functools
        
        # 使用skip参数直接作为起始索引
        start_index = query.skip
        
        # 尝试使用直接读取文件的方式获取日志（异步方式）
        loop = asyncio.get_event_loop()
        logs, total = await loop.run_in_executor(
            None, 
            functools.partial(
                SSHLogReader.get_ssh_logs,
                start=start_index,
                limit=query.limit,
                keyword=query.info,
                status=query.status
            )
        )
        
        # 如果直接读取文件失败（返回空列表），尝试使用命令行工具获取
        if not logs:
            logger.info("Try using command-line tools to retrieve SSH login logs")
            logs, total = await loop.run_in_executor(
                None,
                functools.partial(
                    SSHLogReader.get_ssh_logs_by_command,
                    start=start_index,
                    limit=query.limit,
                    keyword=query.info,
                    status=query.status
                )
            )
        
        # 获取地理位置信息的辅助函数
        def get_location_from_ip(ip_address: str) -> str:
            """通过IP地址获取地理位置信息"""
            if not ip_address or ip_address in ["127.0.0.1", "localhost", "::1"]:
                return "Local Address"
            
            # 检查是否为内网地址
            try:
                ip = ipaddress.ip_address(ip_address)
                if ip.is_private:
                    return "Private Address"
            except ValueError:
                return "Invalid IP"
            
            try:
                # 使用 settings 中的 GEOIP_CITY_DB_PATH
                db_path = settings.GEOIP_CITY_DB_PATH
                if not os.path.isabs(db_path):
                    db_path = os.path.abspath(db_path)

                # 检查数据库文件是否存在
                if not os.path.exists(db_path):
                    logger.error(f"GeoLite2数据库文件不存在: {db_path}")
                    return "未知位置"

                # 使用GeoIP2解析IP地址
                with geoip2.database.Reader(db_path) as reader:
                    response = reader.city(ip_address)
                    country = response.country.name or ""
                    city = response.city.name or ""
                    location = f"{country} {city}".strip()
                    return location if location else "未知位置"
            except Exception as e:
                logger.error(f"获取地理位置信息失败: {e}")
                return "未知位置"
        
        # 将日志条目转换为schemas.SSHLogEntry对象
        log_entries = []
        for log in logs:
            ip_address = log.get("ip", "")
            area = get_location_from_ip(ip_address)
            
            entry = schemas.SSHLogEntry(
                    timestamp=log.get("time", ""),
                    user=log.get("username", ""),
                    ip=ip_address,
                    port=log.get("port", ""),
                    status=log.get("status", ""),
                    method=log.get("method", ""),
                    area=area
                )
            log_entries.append(entry)
        
        # 返回响应对象，使用schemas.SSHLogResponse定义的字段
        return schemas.SSHLogResponse(
            total=total,
            items=log_entries
        )
        
    except Exception as e:
        logger.error(f"获取SSH登录日志时发生错误: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"获取SSH登录日志失败: {str(e)}")

async def clean_ssh_logs(cleanup_request: Optional[schemas.SSHLogCleanupRequest] = None) -> schemas.SSHLogCleanupResponse:
    """清理SSH登录日志
    
    Args:
        cleanup_request: SSH日志清理请求参数，可选
        
    Returns:
        schemas.SSHLogCleanupResponse: 清理操作的响应对象
    """
    try:
        from utils.ssh_utils import SSHLogReader
        import asyncio
        import functools
        
        # 调用工具函数清理日志（异步方式）
        # 当没有提供参数时，设置keep_days=0来清理所有历史日志
        loop = asyncio.get_event_loop()
        success, message, cleaned_count = await loop.run_in_executor(
            None,
            functools.partial(
                SSHLogReader.clean_ssh_logs,
                before_date=cleanup_request.before_date if cleanup_request else None,
                keep_days=cleanup_request.keep_days if cleanup_request else 0
            )
        )
        
        # 返回响应对象
        return schemas.SSHLogCleanupResponse(
            success=success,
            message=message,
            cleaned_count=cleaned_count
        )
        
    except Exception as e:
        logger.error(f"清理SSH登录日志时发生错误: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"清理SSH登录日志失败: {str(e)}")

async def export_ssh_logs(export_params: schemas.SSHLogExportRequest) -> tuple[bytes, str, str]:
    """导出SSH登录日志
    
    Args:
        export_params: SSH日志导出参数，包含关键字搜索、状态过滤和导出格式等信息
        
    Returns:
        tuple[bytes, str, str]: 文件内容、文件名和媒体类型
    """
    try:
        from utils.ssh_utils import SSHLogReader
        import geoip2.database
        import os
        import ipaddress
        import csv
        from io import BytesIO, StringIO
        from datetime import datetime
        import asyncio
        import functools
        
        # 获取所有日志（不分页）（异步方式）
        loop = asyncio.get_event_loop()
        logs, _ = await loop.run_in_executor(
            None,
            functools.partial(
                SSHLogReader.get_ssh_logs,
                start=0,
                limit=10000,  # 设置一个较大的限制以获取所有相关日志
                keyword=None,
                status=export_params.status
            )
        )
        
        # 如果直接读取文件失败（返回空列表），尝试使用命令行工具获取
        if not logs:
            logger.info("Try using command-line tools to retrieve SSH login logs for export")
            logs, _ = await loop.run_in_executor(
                None,
                functools.partial(
                    SSHLogReader.get_ssh_logs_by_command,
                    start=0,
                    limit=10000,
                    keyword=None,
                    status=export_params.status
                )
            )
        
        # 获取地理位置信息的辅助函数
        def get_location_from_ip(ip_address: str) -> str:
            """通过IP地址获取地理位置信息"""
            if not ip_address or ip_address in ["127.0.0.1", "localhost", "::1"]:
                return "Local Address"
            
            # 检查是否为内网地址
            try:
                ip = ipaddress.ip_address(ip_address)
                if ip.is_private:
                    return "Private Address"
            except ValueError:
                return "Invalid IP"
            
            try:
                # 使用 settings 中的 GEOIP_CITY_DB_PATH
                db_path = settings.GEOIP_CITY_DB_PATH
                if not os.path.isabs(db_path):
                    db_path = os.path.abspath(db_path)

                # 检查数据库文件是否存在
                if not os.path.exists(db_path):
                    return "Unknown Location"
                
                # 使用GeoIP2解析IP地址
                with geoip2.database.Reader(db_path) as reader:
                    response = reader.city(ip_address)
                    country = response.country.name or ""
                    city = response.city.name or ""
                    location = f"{country} {city}".strip()
                    return location if location else "Unknown Location"
            except Exception as e:
                logger.error(f"获取地理位置信息失败: {e}")
                return "Unknown Location"
        
        # 准备日志数据
        export_data = []
        for log in logs:
            ip_address = log.get("ip", "")
            area = get_location_from_ip(ip_address)
            
            export_data.append({
                "timestamp": log.get("time", ""),
                "user": log.get("username", ""),
                "ip": ip_address,
                "port": log.get("port", ""),
                "status": log.get("status", ""),
                "method": log.get("method", ""),
                "area": area
            })
        
        # 生成导出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_params.export_format.lower() == "excel":
            # 尝试导入pandas和openpyxl用于Excel导出
            try:
                import pandas as pd
                
                # 创建DataFrame
                df = pd.DataFrame(export_data)
                
                # 创建字节流对象
                output = BytesIO()
                
                # 导出为Excel文件
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='SSH登录日志')
                
                # 获取字节数据
                file_content = output.getvalue()
                file_name = f"ssh_logs_{timestamp}.xlsx"
                media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            except ImportError:
                # 如果没有安装pandas和openpyxl，默认导出为CSV
                logger.warning("pandas和openpyxl未安装，默认导出为CSV格式")
                export_params.export_format = "csv"
        
        # 默认导出为CSV格式
        if export_params.export_format.lower() == "csv":
            # 创建字符串IO对象
            output = StringIO()
            
            # 检查是否有数据
            if export_data:
                fieldnames = export_data[0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                
                # 写入表头
                writer.writeheader()
                
                # 写入数据
                writer.writerows(export_data)
            
            # 获取字节数据（使用UTF-8编码，并添加BOM以支持Excel正确识别中文）
            file_content = (output.getvalue()).encode('utf-8-sig')
            file_name = f"ssh_logs_{timestamp}.csv"
            media_type = "text/csv; charset=utf-8-sig"
        
        return file_content, file_name, media_type
        
    except Exception as e:
        logger.error(f"导出SSH登录日志时发生错误: {e}")
        raise Exception(f"导出SSH登录日志失败: {str(e)}")
