from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from config.database import get_script_db, get_db
from app.script import service, schemas
from app.script.models import Script
from pydantic import BaseModel
from middleware.auth import get_current_active_user
from app.user import models as user_models
import asyncio
import json
import uuid
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/script", tags=["script"])

# 存储WebSocket连接的字典
active_connections = {}

# 定义执行脚本的请求模型
class ExecuteScriptRequest(BaseModel):
    script_id: int
    host_ids: List[int]
    # 支持传入脚本参数
    script_parameters: Optional[str] = None

# 注意：ExecuteScriptRequest类用于异步执行脚本接口，支持参数传递

# 获取脚本列表
@router.get("/list", response_model=schemas.ScriptsResponse)
async def read_scripts(
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_script_db),
    current_user: user_models.User = Depends(get_current_active_user)
):
    """获取脚本列表"""
    return await service.get_scripts(db, skip=skip, limit=limit)


# 创建脚本
@router.post("/create", response_model=schemas.ScriptResponse)
async def create_script(script: schemas.ScriptCreate, db: AsyncSession = Depends(get_script_db), current_user: user_models.User = Depends(get_current_active_user)):
    """创建脚本"""
    db_script = await service.create_script(db, script)
    # 调用to_dict方法并使用返回的字典创建ScriptResponse对象
    script_dict = db_script.to_dict()
    return schemas.ScriptResponse(**script_dict)

# 更新脚本
@router.post("/scripts/{script_id}/update", response_model=schemas.ScriptResponse)
async def update_script(script_id: int, script: schemas.ScriptUpdate, db: AsyncSession = Depends(get_script_db), current_user: user_models.User = Depends(get_current_active_user)):
    """更新脚本"""
    db_script = await service.get_script_by_id(db, script_id)
    if db_script is None:
        raise HTTPException(status_code=404, detail="脚本未找到")
    updated_script = await service.update_script(db, script_id, script)
    if updated_script is None:
        raise HTTPException(status_code=404, detail="脚本未找到")
    # 调用to_dict方法并使用返回的字典创建ScriptResponse对象
    script_dict = updated_script.to_dict()
    return schemas.ScriptResponse(**script_dict)

# 删除脚本
@router.post("/scripts/{script_id}/delete")
async def delete_script(script_id: int, db: AsyncSession = Depends(get_script_db), current_user: user_models.User = Depends(get_current_active_user)):
    """删除脚本"""
    db_script = await service.get_script_by_id(db, script_id)
    if db_script is None:
        raise HTTPException(status_code=404, detail="脚本未找到")
    result = await service.delete_script(db, script_id)
    return {"success": result}

# 获取脚本类型列表
@router.get("/script-types/list", response_model=List[schemas.ScriptTypeResponse])
async def read_script_types(db: AsyncSession = Depends(get_script_db), current_user: user_models.User = Depends(get_current_active_user)):
    """获取脚本类型列表"""
    script_types = await service.get_script_types(db)
    # 转换为ScriptTypeResponse对象列表
    return [schemas.ScriptTypeResponse(**script_type.__dict__) for script_type in script_types]


# 创建脚本类型
@router.post("/script-types/create", response_model=schemas.ScriptTypeResponse)
async def create_script_type(script_type: schemas.ScriptTypeCreate, db: AsyncSession = Depends(get_script_db), current_user: user_models.User = Depends(get_current_active_user)):
    """创建脚本类型"""
    db_script_type = await service.create_script_type(db, script_type)
    return schemas.ScriptTypeResponse(**db_script_type.__dict__)

# 更新脚本类型
@router.post("/script-types/{script_type_id}/update", response_model=schemas.ScriptTypeResponse)
async def update_script_type(script_type_id: int, script_type: schemas.ScriptTypeUpdate, db: AsyncSession = Depends(get_script_db), current_user: user_models.User = Depends(get_current_active_user)):
    """更新脚本类型"""
    db_script_type = await service.get_script_type_by_id(db, script_type_id)
    if db_script_type is None:
        raise HTTPException(status_code=404, detail="脚本类型未找到")
    updated_script_type = await service.update_script_type(db, script_type_id, script_type)
    if updated_script_type is None:
        raise HTTPException(status_code=404, detail="脚本类型未找到")
    return schemas.ScriptTypeResponse(**updated_script_type.__dict__)

# 删除脚本类型
@router.post("/script-types/{script_type_id}/delete")
async def delete_script_type(script_type_id: int, db: AsyncSession = Depends(get_script_db), current_user: user_models.User = Depends(get_current_active_user)):
    """删除脚本类型"""
    db_script_type = await service.get_script_type_by_id(db, script_type_id)
    if db_script_type is None:
        raise HTTPException(status_code=404, detail="脚本类型未找到")
    result = await service.delete_script_type(db, script_type_id)
    return {"success": result}


# 添加支持交互式终端的WebSocket端点
@router.websocket("/execute/ws/{execution_id}")
async def websocket_execute_script_interactive(
    websocket: WebSocket,
    execution_id: str,
    script_db: AsyncSession = Depends(get_script_db),
    host_db: AsyncSession = Depends(get_db)
):
    """通过WebSocket执行脚本并提供交互式终端，脚本执行完成后保持SSH连接支持继续交互"""
    await websocket.accept()
    
    # 导入必要的模块
    import threading
    import queue
    from app.host import service as host_service
    from app.host.models import Host
    from utils.encryption import decrypt_password
    import paramiko
    import asyncio
    
    # 存储WebSocket连接
    active_connections[execution_id] = websocket
    
    # SSH客户端和通道
    ssh_client = None
    channel = None
    
    # 创建线程安全的队列用于通信
    input_queue = queue.Queue()
    output_queue = queue.Queue()
    
    # 标记是否关闭
    is_closed = False
    
    # 输出转发函数：从output_queue获取数据，应用过滤逻辑后发送到WebSocket
    async def forward_output():
        try:
            while not is_closed:
                if not output_queue.empty():
                    data = output_queue.get_nowait()
                    
                    # 初始化过滤后的数据为原始数据
                    filtered_data = data
                    
                    # 只有当数据包含脚本执行相关的特定模式时才应用过滤逻辑
                    # 这样可以避免影响其他普通终端命令的显示
                    import re
                    
                    # 检查是否包含需要过滤的模式
                    if 'export INIT_SCRIPT=' in data and 'base64 -d' in data:
                        # 应用过滤逻辑，移除不想显示的命令内容
                        # 过滤export INIT_SCRIPT命令本身的显示
                        filtered_data = re.sub(r'export\s+INIT_SCRIPT=\$\(echo\s+\'[^\']*\'\s*\|\s*base64\s*-d\s*2>/dev/null\)\s*2>/dev/null\s*', '', data)
                        
                        # 使用更精确的正则表达式过滤base64相关内容
                        # 只过滤看起来像完整base64编码块的内容
                        filtered_data = re.sub(r'^([A-Za-z0-9+/]{4})*([A-Za-z0-9+/]{3}=|[A-Za-z0-9+/]{2}==)?\s*$', '', filtered_data, flags=re.MULTILINE)
                    
                    # 始终发送数据，无论是否过滤过
                    await websocket.send_text(filtered_data)
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"输出转发错误: {e}")
    
    # 启动输出转发任务
    output_task = asyncio.create_task(forward_output())
    
    try:
        # 等待客户端发送执行参数
        data = await websocket.receive_text()
        params = json.loads(data)
        
        script_id = params.get("script_id")
        host_ids = params.get("host_ids", [])
        script_parameters = params.get("script_parameters")
        
        logger.info(f"WebSocket接收到执行请求: 脚本ID {script_id}, 主机列表 {host_ids}, 参数 {script_parameters}")
        
        # 目前只支持单主机执行（交互式终端只适合单主机）
        if not script_id or len(host_ids) != 1:
            error_msg = "交互式终端模式只支持选择单个主机执行脚本"
            output_queue.put(f"\r\n\x1b[1;31m*** 错误: {error_msg} ***\x1b[0m\r\n")
            await asyncio.sleep(1)  # 给时间发送错误消息
            return
        
        host_id = host_ids[0]
        
        # 获取脚本信息
        result = await script_db.execute(
            select(Script)
            .options(selectinload(Script.script_type))
            .where(Script.script_id == script_id)
        )
        script = result.scalar_one_or_none()
        
        if not script:
            output_queue.put("\r\n\x1b[1;31m*** 错误: 脚本未找到 ***\x1b[0m\r\n")
            await asyncio.sleep(1)
            return
        
        # 只保留参数信息（如果有）
        if script_parameters:
            output_queue.put(f"\r\n\x1b[1;32m*** 执行参数: {script_parameters} ***\x1b[0m\r\n")
        
        # 获取主机信息
        host = await host_service.get_host(host_db, host_id)
        if not host:
            output_queue.put("\r\n\x1b[1;31m*** 错误: 主机未找到 ***\x1b[0m\r\n")
            await asyncio.sleep(1)
            return
        
        # 规范化脚本内容
        script_content = str(script.script_context)
        script_content = script_content.replace('\r\n', '\n').replace('\r', '\n')
        
        # 获取解释器路径
        interpreter_path = script.script_type.interpreter_path if script.script_type else "/bin/bash"
        if not interpreter_path:
            interpreter_path = "/bin/bash"
        
        # 添加shebang行
        if not script_content.startswith("#!"):
            script_content = f"#!{interpreter_path}\n{script_content}"
        
        # 根据认证方式获取认证信息并解密
        decrypted_password = None
        private_key = None
        private_key_password = None
        
        if str(getattr(host, 'auth_method', 'password')) == "password" and getattr(host, 'password', None):
            decrypted_password = decrypt_password(str(getattr(host, 'password', '')))
        elif str(getattr(host, 'auth_method', 'password')) == "key" and getattr(host, 'private_key', None):
            private_key = getattr(host, 'private_key', None)
            if getattr(host, 'private_key_password', None):
                try:
                    private_key_password = decrypt_password(str(getattr(host, 'private_key_password', '')))
                except Exception as decrypt_error:
                    logger.error(f"私钥密码解密失败: {decrypt_error}")
                    private_key_password = None
        
        # 创建SSH客户端连接函数
        def create_ssh_connection():
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                if decrypted_password:
                    client.connect(
                        hostname=str(getattr(host, 'address', '')),
                        port=int(getattr(host, 'port', 22)),
                        username=str(getattr(host, 'username', '')),
                        password=decrypted_password,
                        timeout=10
                    )
                elif private_key:
                    from io import StringIO
                    key_file_obj = StringIO(str(private_key))
                    pkey = None
                    # 尝试多种密钥类型
                    key_types = [
                        paramiko.RSAKey,
                        paramiko.DSSKey,
                        paramiko.ECDSAKey,
                        paramiko.Ed25519Key
                    ]
                    
                    for key_type in key_types:
                        try:
                            key_file_obj.seek(0)  # 重置文件指针
                            if private_key_password:
                                pkey = key_type.from_private_key(key_file_obj, password=private_key_password)
                            else:
                                pkey = key_type.from_private_key(key_file_obj)
                            break  # 成功加载则退出循环
                        except Exception:
                            continue  # 尝试下一种密钥类型
                    
                    if not pkey:
                        raise Exception("无法识别或加载私钥，支持的类型：RSA, DSS, ECDSA, Ed25519")
                    
                    client.connect(
                        hostname=str(getattr(host, 'address', '')),
                        port=int(getattr(host, 'port', 22)),
                        username=str(getattr(host, 'username', '')),
                        pkey=pkey,
                        timeout=10
                    )
                else:
                    raise Exception("未提供有效的认证信息")
                
                return client
            except Exception as e:
                logger.error(f"SSH连接失败: {e}")
                raise
        
        # 创建SSH通道和执行脚本
        def run_ssh_session():
            nonlocal ssh_client, channel
            try:
                # 创建SSH连接
                ssh_client = create_ssh_connection()
                
                # 创建交互式shell通道
                channel = ssh_client.invoke_shell(term='xterm-256color', width=100, height=30)
                # 静默读取并丢弃初始连接时的系统欢迎信息
                time.sleep(0.5)  # 给系统一点时间发送欢迎信息
                while channel.recv_ready():
                    channel.recv(4096)  # 读取并丢弃初始的欢迎信息
                
                # 在SSH环境下，我们通过export设置环境变量，确保特殊字符被正确处理
                # 使用base64编码避免引号和特殊字符问题
                import base64
                # 对脚本内容进行base64编码
                encoded_script = base64.b64encode(script_content.encode('utf-8')).decode('utf-8')
                
                # 先设置环境变量（使用base64解码避免特殊字符问题）
                # 使用静默模式，不显示命令本身的输出
                channel.send(f"export INIT_SCRIPT=$(echo '{encoded_script}' | base64 -d 2>/dev/null) 2>/dev/null\n")
                time.sleep(0.1)
                
                # 执行脚本命令，使用从脚本类型中获取的解释器路径
                if script_parameters:
                    channel.send(f"clear && {interpreter_path} -c \"$INIT_SCRIPT\" {script_parameters}\n")
                else:
                    channel.send(f"clear && {interpreter_path} -c \"$INIT_SCRIPT\"\n")
                time.sleep(0.1)
                
                # 移除提示信息，直接执行脚本
                
                # SSH到WebSocket的数据流转发
                while not is_closed and ssh_client:
                    if channel.recv_ready():
                        data = channel.recv(4096).decode('utf-8', errors='ignore')
                        if data:
                            output_queue.put(data)
                    if channel.exit_status_ready():
                        # 如果shell已退出，添加退出状态信息
                        exit_status = channel.recv_exit_status()
                        output_queue.put(f"\r\n\x1b[1;32m*** Shell已退出，状态码: {exit_status} ***\x1b[0m\r\n")
                        break
                    
                    # 从输入队列读取数据并发送到SSH通道
                    try:
                        input_data = input_queue.get_nowait()
                        channel.send(input_data)
                    except queue.Empty:
                        pass
                    
                    time.sleep(0.01)  # 避免CPU占用过高
                    
            except Exception as e:
                error_msg = f"SSH会话错误: {str(e)}"
                logger.error(error_msg)
                output_queue.put(f"\r\n\x1b[1;31m*** {error_msg} ***\x1b[0m\r\n")
            finally:
                # 关闭通道和连接
                if channel:
                    try:
                        channel.close()
                    except:
                        pass
                if ssh_client:
                    try:
                        ssh_client.close()
                    except:
                        pass
        
        # 启动SSH会话线程
        ssh_thread = threading.Thread(target=run_ssh_session)
        ssh_thread.daemon = True
        ssh_thread.start()
        
        # WebSocket消息处理循环
        while not is_closed:
            try:
                message = await websocket.receive_text()
                try:
                    # 处理终端命令和调整大小
                    data = json.loads(message)
                    if data['type'] == 'input':
                        input_queue.put(data['data'])
                    elif data['type'] == 'resize':
                        # 处理终端大小调整
                        new_size = data['data']
                        if channel:
                            channel.resize_pty(
                                width=new_size['cols'],
                                height=new_size['rows']
                            )
                except json.JSONDecodeError:
                    # 如果不是JSON格式，直接作为输入发送
                    input_queue.put(message)
            except Exception as e:
                logger.error(f"WebSocket接收错误: {e}")
                is_closed = True
                break
                
    except Exception as e:
        logger.error(f"WebSocket执行脚本时发生错误: {e}")
        output_queue.put(f"\r\n\x1b[1;31m*** 执行过程中发生错误: {str(e)} ***\x1b[0m\r\n")
    finally:
        # 设置关闭标志
        is_closed = True
        
        # 取消输出转发任务
        output_task.cancel()
        try:
            await output_task
        except asyncio.CancelledError:
            pass
        
        # 关闭SSH连接
        if channel:
            try:
                channel.close()
            except:
                pass
        if ssh_client:
            try:
                ssh_client.close()
            except:
                pass
        
        # 清理连接
        if execution_id in active_connections:
            del active_connections[execution_id]
        
        # 关闭WebSocket连接
        try:
            await websocket.close()
        except:
            pass



    