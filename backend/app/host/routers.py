from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.host import schemas, service, models
from app.user import models as user_models
from config.database import get_db
from middleware.auth import get_current_active_user
import asyncio
import logging
# 导入解密工具
from utils.encryption import decrypt_password
# 导入 WebSocket 支持
from app.host.websocket_terminal import TerminalManager
from config.settings import settings

router = APIRouter(prefix="/host", tags=["host"])

# 创建终端管理器实例
terminal_manager = TerminalManager()

logger = logging.getLogger(__name__)

@router.post("/create", response_model=schemas.HostInDB)
async def create_host(
    host: schemas.HostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """创建主机"""
    try:
        db_host = await service.create_host(db, host)
        return db_host
    except Exception as e:
        logger.error(f"创建主机失败: {e}")
        raise HTTPException(status_code=500, detail="创建主机失败")

@router.get("/list", response_model=List[schemas.HostInDB])
async def read_hosts(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """获取主机列表"""
    try:
        hosts = await service.get_hosts(db, skip=skip, limit=limit)
        return hosts
    except Exception as e:
        logger.error(f"获取主机列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取主机列表失败")


@router.get("/transferhosts", response_model=List[schemas.HostSimple])
async def read_file_transfer_hosts(
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """获取文件传输专用主机列表（简化版）

    返回仅包含文件传输所需的字段：id、comment、address、username、port。
    """
    try:
        hosts = await service.get_hosts(db, skip=0, limit=1000)
        return hosts
    except Exception as e:
        logger.error(f"获取文件传输主机列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取文件传输主机列表失败")

@router.get("/{host_id}/detail", response_model=schemas.HostInDB)
async def read_host(
    host_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """根据ID获取主机"""
    try:
        db_host = await service.get_host(db, host_id)
        if db_host is None:
            raise HTTPException(status_code=404, detail="主机不存在")
        return db_host
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取主机失败: {e}")
        raise HTTPException(status_code=500, detail="获取主机失败")

@router.post("/{host_id}/update", response_model=schemas.HostInDB)
async def update_host(
    host_id: int,
    host_update: schemas.HostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """更新主机信息"""
    try:
        db_host = await service.update_host(db, host_id, host_update)
        if db_host is None:
            raise HTTPException(status_code=404, detail="主机不存在")
        return db_host
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新主机失败: {e}")
        raise HTTPException(status_code=500, detail="更新主机失败")

@router.post("/{host_id}/delete", response_model=bool)
async def delete_host(
    host_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """删除主机"""
    try:
        result = await service.delete_host(db, host_id)
        if not result:
            raise HTTPException(status_code=404, detail="主机不存在")
        return result
    except ValueError as e:
        # 处理不允许删除本机配置的异常
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除主机失败: {e}")
        raise HTTPException(status_code=500, detail="删除主机失败")

# 添加主机状态检测端点
@router.get("/{host_id}/status")
async def check_host_status(
    host_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """检测主机状态"""
    try:
        # 获取主机信息
        db_host = await service.get_host(db, host_id)
        if db_host is None:
            raise HTTPException(status_code=404, detail="主机不存在")
        
        # 检测主机状态
        status_result = await service.check_host_status(
            host_address=getattr(db_host, 'address', ''),
            port=getattr(db_host, 'port', 22)
        )
        
        return {
            "success": True,
            "data": status_result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检测主机状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"检测主机状态失败: {str(e)}")

# 添加SSH连接测试端点
@router.post("/{host_id}/ssh_test")
async def test_ssh_connection(
    host_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """测试SSH连接"""
    try:
        # 获取主机信息
        db_host = await service.get_host(db, host_id)
        if db_host is None:
            raise HTTPException(status_code=404, detail="主机不存在")
        
        # 根据认证方式获取相应的认证信息
        decrypted_password = None
        private_key = None
        private_key_password = None
        
        if str(getattr(db_host, 'auth_method', 'password')) == "password" and getattr(db_host, 'password', None):
            decrypted_password = decrypt_password(str(getattr(db_host, 'password', '')))
        elif str(getattr(db_host, 'auth_method', 'password')) == "key" and getattr(db_host, 'private_key', None):
            private_key = getattr(db_host, 'private_key', None)
            # 如果有私钥密码，也解密
            if getattr(db_host, 'private_key_password', None):
                try:
                    private_key_password = decrypt_password(str(getattr(db_host, 'private_key_password', '')))
                except Exception as decrypt_error:
                    logger.error(f"私钥密码解密失败: {decrypt_error}")
                    private_key_password = None
        
        # 延迟导入SSHService以避免循环导入
        from app.host.ssh_service import SSHService
        
        # 执行SSH连接测试
        success, message = await SSHService.test_ssh_connection(
            host=getattr(db_host, 'address', ''),
            port=getattr(db_host, 'port', 22),
            username=getattr(db_host, 'username', ''),
            password=decrypted_password,
            private_key=private_key,
            private_key_password=private_key_password
        )
        
        return {
            "success": success,
            "message": message
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SSH连接测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"SSH连接测试失败: {str(e)}")


# 添加生成终端令牌端点
@router.post("/{host_id}/terminal_token")
async def generate_terminal_token(
    host_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """生成终端连接令牌"""
    try:
        # 获取主机信息
        db_host = await service.get_host(db, host_id)
        if db_host is None:
            raise HTTPException(status_code=404, detail="主机不存在")
        
        # 从配置中获取密钥
        from config.settings import settings
        token = service.generate_terminal_token(host_id, settings.SECRET_KEY)
        
        return {
            "success": True,
            "token": token
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成终端令牌失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成终端令牌失败: {str(e)}")


# 添加 WebSocket 终端端点
@router.websocket("/ws/terminal/{host_id}")
async def websocket_terminal(
    websocket: WebSocket,
    host_id: int,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket 终端连接"""
    # 从查询参数中获取令牌
    token = websocket.query_params.get("token")
    if not token:
        logger.warning(f"WebSocket连接缺少令牌参数，host_id: {host_id}")
        await websocket.close(code=4001, reason="Missing token")
        return
    
    logger.info(f"WebSocket连接请求，host_id: {host_id}, token: {token}")
    
    # 验证令牌有效性
    from app.host.websocket_terminal import TerminalManager
    terminal_manager = TerminalManager()
    if not await terminal_manager._validate_token(token, host_id):
        logger.warning(f"令牌验证失败，host_id: {host_id}")
        await websocket.close(code=4001, reason="Invalid or expired token")
        return
    
    # 获取主机信息
    db_host = await service.get_host(db, host_id)
    if not db_host:
        logger.warning(f"找不到主机: {host_id}")
        await websocket.close(code=4001, reason="Host not found")
        return
    
    # 获取当前用户（通过 WebSocket 连接建立后的认证）
    # 在这种情况下，我们暂时不进行用户认证，直接连接
    # 实际的用户认证应该在终端管理器中进行
    try:
        # 传递 None 作为 current_user，实际的用户验证将在终端管理器中进行
        await terminal_manager.connect(websocket, host_id, token, db, None)
    except HTTPException as e:
        logger.warning(f"用户认证失败，错误: {e.detail}")
        await websocket.close(code=4001, reason=e.detail)
    except Exception as e:
        logger.error(f"WebSocket连接失败: {e}")
        await websocket.close(code=4002, reason="Internal server error")


# 添加连接本机SSH端点
@router.post("/connect_localhost")
async def connect_localhost_ssh(
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """连接本机SSH"""
    try:
        # 查找本机SSH配置（127.0.0.1）
        from sqlalchemy import select
        result = await db.execute(
            select(models.Host).filter(models.Host.address == "127.0.0.1")
        )
        localhost_hosts = result.scalars().all()
        
        # 确保第一条记录是本机配置信息
        localhost_host = None
        if localhost_hosts:
            # 检查第一条记录是否为本机配置
            first_host = localhost_hosts[0]
            if getattr(first_host, 'address', '') == "127.0.0.1":
                localhost_host = first_host
            else:
                # 如果第一条不是本机配置，查找所有记录中是否有本机配置
                for host in localhost_hosts:
                    if getattr(host, 'address', '') == "127.0.0.1":
                        localhost_host = host
                        break
        
        # 如果不存在本机配置，则创建一个默认的系统创建记录
        if not localhost_host:
            localhost_host = models.Host(
                comment="本机",
                address="127.0.0.1",
                username="root",  # 默认用户名，前端会要求用户修改
                port=22,
                auth_method="password",
                password="",  # 初始为空，前端会要求用户填写
                is_system_created=True  # 标记为系统创建的记录
            )
            db.add(localhost_host)
            await db.commit()
            await db.refresh(localhost_host)
        
        # 根据认证方式获取相应的认证信息
        decrypted_password = None
        private_key = None
        private_key_password = None
        
        if str(getattr(localhost_host, 'auth_method', 'password')) == "password" and getattr(localhost_host, 'password', None):
            decrypted_password = decrypt_password(str(getattr(localhost_host, 'password', '')))
        elif str(getattr(localhost_host, 'auth_method', 'password')) == "key" and getattr(localhost_host, 'private_key', None):
            private_key = getattr(localhost_host, 'private_key', None)
            # 如果有私钥密码，也解密
            if getattr(localhost_host, 'private_key_password', None):
                try:
                    private_key_password = decrypt_password(str(getattr(localhost_host, 'private_key_password', '')))
                except Exception as decrypt_error:
                    logger.error(f"私钥密码解密失败: {decrypt_error}")
                    private_key_password = None
        
        # 延迟导入SSHService以避免循环导入
        from app.host.ssh_service import SSHService
        
        # 执行SSH连接测试
        success, message = await SSHService.test_ssh_connection(
            host=getattr(localhost_host, 'address', ''),
            port=getattr(localhost_host, 'port', 22),
            username=getattr(localhost_host, 'username', ''),
            password=decrypted_password,
            private_key=private_key,
            private_key_password=private_key_password
        )
        
        # 获取 host_id 值
        host_id = getattr(localhost_host, 'id', 0)
        
        if success:
            # 连接成功，生成终端令牌
            token = service.generate_terminal_token(int(host_id), settings.SECRET_KEY)
            return {
                "success": True,
                "message": "连接成功",
                "host_id": int(host_id),
                "token": token
            }
        else:
            # 连接失败，返回需要填写的信息
            return {
                "success": False,
                "message": "SSH连接失败，请填写正确的连接信息",
                "host_id": int(host_id),
                "host_info": {
                    "id": int(host_id),
                    "comment": getattr(localhost_host, 'comment', '本机'),
                    "address": getattr(localhost_host, 'address', '127.0.0.1'),
                    "username": getattr(localhost_host, 'username', ''),
                    "port": getattr(localhost_host, 'port', 22),
                    "auth_method": getattr(localhost_host, 'auth_method', 'password')
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"连接本机SSH失败: {e}")
        raise HTTPException(status_code=500, detail=f"连接本机SSH失败: {str(e)}")

# 获取所有主机的资源使用情况
@router.get("/resource/all", response_model=List[schemas.HostResource])
async def get_all_hosts_resource(
    db: AsyncSession = Depends(get_db),
    #current_user: user_models.User = Depends(get_current_active_user)
):
    """获取所有主机的CPU、内存、磁盘资源使用情况"""
    from app.host.remote_service import get_host_resource_usage

    hosts = await service.get_hosts(db, skip=0, limit=1000)

    async def _fetch_resource(host_id):
        try:
            return await get_host_resource_usage(db, host_id)
        except Exception as e:
            logger.warning(f"获取主机 {host_id} 资源信息失败: {e}")
            return schemas.HostResource(
                id=host_id,
                cpu=0, cpu_usage=0,
                memory=0, mem_usage=0,
                disk=0, disk_usage=0,
            )

    results = await asyncio.gather(*[_fetch_resource(h.id) for h in hosts])
    return results


# HostCommand 相关的 API 路由
@router.post("/commands/create", response_model=schemas.HostCommandInDB)
async def create_host_command(
    command: schemas.HostCommandCreate,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """创建主机命令"""
    try:
        db_command = await service.create_host_command(db, command)
        return db_command
    except Exception as e:
        logger.error(f"创建主机命令失败: {e}")
        raise HTTPException(status_code=500, detail="创建主机命令失败")

@router.get("/commands/list", response_model=List[schemas.HostCommandInDB])
async def read_host_commands(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """获取主机命令列表"""
    try:
        commands = await service.get_host_commands(db, skip=skip, limit=limit)
        return commands
    except Exception as e:
        logger.error(f"获取主机命令列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取主机命令列表失败")

@router.get("/commands/{command_id}/detail", response_model=schemas.HostCommandInDB)
async def read_host_command(
    command_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """根据ID获取主机命令"""
    try:
        db_command = await service.get_host_command(db, command_id)
        if db_command is None:
            raise HTTPException(status_code=404, detail="主机命令不存在")
        return db_command
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取主机命令失败: {e}")
        raise HTTPException(status_code=500, detail="获取主机命令失败")

@router.post("/commands/{command_id}/update", response_model=schemas.HostCommandInDB)
async def update_host_command(
    command_id: int,
    command_update: schemas.HostCommandUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """更新主机命令"""
    try:
        db_command = await service.update_host_command(db, command_id, command_update)
        if db_command is None:
            raise HTTPException(status_code=404, detail="主机命令不存在")
        return db_command
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新主机命令失败: {e}")
        raise HTTPException(status_code=500, detail="更新主机命令失败")

@router.post("/commands/{command_id}/delete", response_model=bool)
async def delete_host_command(
    command_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """删除主机命令"""
    try:
        result = await service.delete_host_command(db, command_id)
        if not result:
            raise HTTPException(status_code=404, detail="主机命令不存在")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除主机命令失败: {e}")
        raise HTTPException(status_code=500, detail="删除主机命令失败")


# 本机ssh服务管理相关的 API 路由

@router.get("/ssh/config", response_model=schemas.SSHConfigInfo)
async def get_local_ssh_config_info(
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """获取本机SSH配置信息
    
    该接口用于获取当前服务器上SSH服务的配置信息，包括：
    - 是否安装SSH服务
    - SSH服务是否正在运行
    - SSH服务监听端口
    - 密码认证状态
    - 公钥认证状态
    - 是否允许root登录
    - 是否启用DNS解析
    - 当前用户名
    """
    try:
        ssh_config = await service.get_local_ssh_config()
        return ssh_config
    except Exception as e:
        logger.error(f"获取本机SSH配置信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取本机SSH配置信息失败")

@router.post("/ssh/config/update")
async def update_ssh_config(
    config_update: schemas.SSHConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """更新SSH配置参数
    
    更新SSH服务的配置参数，包括端口、认证方式等。
    更新后会自动重启SSH服务以应用更改（如果服务原本在运行状态）。
    """
    try:
        success, message = await service.update_local_ssh_config(config_update)
        if success:
            # 更新成功后，返回最新的配置信息
            config = await service.get_local_ssh_config()
            return {
                "success": True,
                "message": message,
                "data": config
            }
        else:
            # 更新失败
            return {
                "success": False,
                "message": message
            }, 400
    except Exception as e:
        logger.error(f"更新SSH配置失败: {e}")
        raise HTTPException(status_code=500, detail="更新SSH配置失败")

@router.get("/ssh/config/file", response_model=schemas.SSHConfigFile)
async def get_local_ssh_config_file_content(
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """获取SSH配置文件内容
    
    该接口用于获取当前服务器上SSH服务的完整配置文件内容，包括：
    - 配置文件路径
    - 配置文件的完整文本内容
    """
    try:
        config_file = await service.get_local_ssh_config_file()
        return config_file
    except Exception as e:
        logger.error(f"获取SSH配置文件内容失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ssh/authkeys/file", response_model=schemas.SSHAuthKeysFile)
async def get_local_authorized_keys_file_content(
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """获取SSH authorized_keys文件内容
    
    该接口用于获取当前服务器上SSH服务的authorized_keys文件内容，包括：
    - authorized_keys文件路径
    - authorized_keys文件的完整文本内容
    """
    try:
        keys_file = await service.get_local_authorized_keys_file()
        return keys_file
    except Exception as e:
        logger.error(f"获取authorized_keys文件内容失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ssh/set", response_model=schemas.SSHServiceOperationResponse)
async def operate_ssh_service(
    operation: schemas.SSHServiceOperation,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """操作本机SSH服务（启动/停止/重启）
    
    该接口用于操作当前服务器上的SSH服务
    - action: 操作类型，可选值为 start（启动）、stop（停止）、restart（重启）
    """
    try:
        result = await service.operate_local_ssh_service(operation.action)
        return result
    except Exception as e:
        logger.error(f"操作SSH服务失败: {e}")
        raise HTTPException(status_code=500, detail="操作SSH服务失败")


@router.post("/ssh/log", response_model=schemas.SSHLogResponse)
async def get_ssh_logs(
    query_params: schemas.SSHLogQuery,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """获取SSH登录日志
    
    该接口用于获取当前服务器上的SSH登录日志信息，支持按状态筛选和分页
    - status: 登录状态筛选，可选值为 success（成功）、failed（失败）、all（全部）
    - page: 页码，默认为1
    - page_size: 每页记录数，默认为10
    - limit: 返回记录数限制，默认为100（防止返回过多数据）
    """
    try:
        logs = await service.get_ssh_logs(query_params)
        return logs
    except Exception as e:
        logger.error(f"获取SSH登录日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取SSH登录日志失败: {str(e)}")

@router.post("/ssh/log/cleanup", response_model=schemas.SSHLogCleanupResponse)
async def clean_ssh_logs(
    current_user: user_models.User = Depends(get_current_active_user)
):
    """清理SSH登录日志
    
    该接口用于清理服务器上的SSH登录日志。
    默认清理所有历史日志。
    """
    try:
        # 调用服务函数清理日志
        return await service.clean_ssh_logs()
    except Exception as e:
        logger.error(f"清理SSH登录日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理SSH登录日志失败: {str(e)}")

@router.post("/ssh/log/export")
async def export_ssh_logs(
    export_params: schemas.SSHLogExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """导出SSH登录日志
    
    该接口用于导出当前服务器上的SSH登录日志信息，支持按状态筛选和多种导出格式
    - status: 登录状态筛选，可选值为 success（成功）、failed（失败）、all（全部）
    - export_format: 导出格式，可选值为 csv、excel
    """
    try:
        file_content, file_name, media_type = await service.export_ssh_logs(export_params)
        from fastapi import Response
        return Response(
            content=file_content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={file_name}"
            }
        )
    except Exception as e:
        logger.error(f"导出SSH登录日志失败: {e}")
        raise HTTPException(status_code=500, detail=f"导出SSH登录日志失败: {str(e)}")

# 远程文件相关接口


@router.get("/{host_id}/files/list")
async def get_remote_file_list(
    host_id: int,
    path: str = "/",
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """获取远程主机文件列表（通过SSH）

    该接口用于通过SSH连接远程主机，获取指定路径下的文件列表。
    返回格式与本地文件列表接口一致。

    - **host_id**: 主机ID
    - **path**: 远程路径（Query参数），默认为 /
    - **skip**: 跳过的记录数，默认为0
    - **limit**: 返回的记录数，默认为100
    """
    try:
        from app.host.remote_service import get_remote_file_list as _remote_list

        files = await _remote_list(db, host_id, path)
        total = len(files)
        start = max(0, skip)
        end = start + max(0, limit)
        paged = files[start:end]
        return {
            "data": paged,
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取远程主机文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取远程文件列表失败: {str(e)}")


@router.post("/{host_id}/files/create", response_model=schemas.RemoteFileCreateResponse)
async def create_remote_file(
    host_id: int,
    req: schemas.RemoteFileCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """在远程主机上创建文件或文件夹（通过SSH）

    该接口用于通过SSH连接远程主机，在指定路径下创建文件或文件夹。

    - **host_id**: 主机ID
    - **path**: 父目录路径
    - **name**: 文件或文件夹名称
    - **type**: 创建类型，file（文件）或 directory（文件夹）
    - **content**: 文件内容（创建文件时可选）
    """
    try:
        from app.host.remote_service import create_remote_file_or_folder

        result = await create_remote_file_or_folder(
            db, host_id,
            path=req.path,
            name=req.name,
            type_=req.type,
            content=req.content or ""
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"远程创建文件/文件夹失败: {e}")
        raise HTTPException(status_code=500, detail=f"远程创建文件/文件夹失败: {str(e)}")


@router.post("/{host_id}/files/upload")
async def upload_remote_file(
    host_id: int,
    file: UploadFile = File(...),
    path: str = Form("/"),
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """上传文件到远程主机（通过SFTP）

    该接口用于通过SFTP将文件上传到远程主机的指定目录。

    - **host_id**: 主机ID
    - **file**: 上传的文件（multipart/form-data）
    - **path**: 远程目标目录路径（Form字段）
    """
    if not path or path.strip() == "/":
        raise HTTPException(status_code=400, detail="Cannot upload file to root directory, please specify a subdirectory")

    try:
        from app.host.remote_service import upload_file_to_remote

        result = await upload_file_to_remote(
            db, host_id,
            remote_dir=path,
            filename=file.filename or "unknown",
            file_content=await file.read()
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"上传文件到远程主机失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传文件到远程主机失败: {str(e)}")


@router.post("/{host_id}/files/delete", response_model=schemas.RemoteFileCreateResponse)
async def delete_remote_file(
    host_id: int,
    req: schemas.RemoteFileDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """删除远程主机上的文件或文件夹（通过SSH）

    该接口用于通过SSH连接远程主机，删除指定路径下的文件或文件夹。

    - **host_id**: 主机ID
    - **path**: 文件或文件夹的完整路径
    - **type**: 删除类型，file（文件）或 directory（文件夹）
    """
    try:
        from app.host.remote_service import delete_remote_file as _delete_remote

        result = await _delete_remote(
            db, host_id,
            path=req.path,
            type_=req.type
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"删除远程文件/文件夹失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除远程文件/文件夹失败: {str(e)}")


@router.post("/{host_id}/files/scp-transfer")
async def scp_transfer(
    host_id: int,
    req: schemas.ScpTransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """启动 SCP 文件传输任务，支持双向传输

    支持将本地文件批量传输到远程主机（upload），
    或将远程主机文件批量下载到本地（download），
    类似于 `scp file1.py file2.js root@host:/remote/dir/`。
    立即返回 task_id，实际传输在后台异步执行，
    进度和结果通过 WebSocket `/ws/scp-progress/{task_id}` 实时推送。

    - **host_id**: 目标主机 ID
    - **direction**: 传输方向: upload(本地→远程) 或 download(远程→本地)
    - **source_paths**: 源文件路径列表
    - **remote_dir**: 目标目录路径

    返回:
    - **task_id**: 传输任务 ID，用于 WebSocket 连接监听进度
    """
    import uuid
    from app.host.remote_service import _scp_tasks, ScpTransferTask, start_scp_transfer as _start_transfer
    from config.database import AsyncSessionLocal

    task_id = str(uuid.uuid4())

    pending_task = ScpTransferTask(task_id, host_id, req.source_paths, req.remote_dir)
    pending_task.status = "pending"
    pending_task.message = "任务已创建，等待开始传输..."
    _scp_tasks[task_id] = pending_task

    async def _run_transfer():
        async with AsyncSessionLocal() as bg_db:
            await _start_transfer(
                bg_db, host_id,
                source_paths=req.source_paths,
                remote_dir=req.remote_dir,
                direction=req.direction,
                task_id=task_id,
            )

    asyncio.create_task(_run_transfer())

    return {"task_id": task_id}


@router.post("/scp-transfer/{task_id}/cancel")
async def cancel_scp_transfer(
    task_id: str,
    current_user: user_models.User = Depends(get_current_active_user)
):
    """取消 SCP 传输任务"""
    from app.host.remote_service import cancel_scp_task as _cancel

    if _cancel(task_id):
        return {"success": True, "message": "传输已取消"}
    raise HTTPException(status_code=400, detail="无法取消该任务，任务可能已完成或不存在")


@router.websocket("/ws/scp-progress/{task_id}")
async def websocket_scp_progress(
    websocket: WebSocket,
    task_id: str,
):
    """WebSocket 实时传输进度

    通过 WebSocket 持续推送传输进度信息，每次推送包含完整的任务状态 JSON：
    - task_id: 任务 ID
    - status: 状态（pending/running/completed/failed/cancelled）
    - progress: 进度百分比（0-100）
    - current_file: 当前传输的文件名
    - total_files: 文件总数
    - completed_files: 已完成文件数
    - total_bytes: 总字节数
    - transferred_bytes: 已传输字节数
    - message: 状态消息
    """
    from app.host.remote_service import get_scp_task

    await websocket.accept()
    try:
        last_status = None
        while True:
            task = get_scp_task(task_id)
            if not task:
                await websocket.send_json({
                    "task_id": task_id,
                    "status": "not_found",
                    "message": "传输任务不存在"
                })
                break

            data = task.to_dict()
            if data != last_status:
                await websocket.send_json(data)
                last_status = data

            if task.status in ("completed", "failed", "cancelled"):
                break

            await asyncio.sleep(0.5)
    except Exception:
        logger.warning(f"SCP 进度 WebSocket 连接断开: task_id={task_id}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

