"""
WebSocket SSH 终端服务模块
"""
import asyncio
import json
import time
import hmac
import hashlib
import select
import paramiko
import threading
from typing import Optional
from fastapi import WebSocket, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.host import service, models, ssh_service
from app.user import models as user_models
from utils.encryption import decrypt_password
import logging

logger = logging.getLogger(__name__)

class TerminalManager:
    """终端管理器"""
    
    def __init__(self):
        self.active_connections = {}
    
    async def connect(self, websocket: WebSocket, host_id: int, token: str, db: AsyncSession, current_user: Optional[user_models.User] = None):
        """处理 WebSocket 连接"""
        user_id = current_user.id if current_user else 'unknown'
        logger.info(f"用户 {user_id} 尝试连接主机 {host_id}")
        
        # 验证令牌
        # logger.debug(f"验证主机 {host_id} 的连接令牌")
        if not await self._validate_token(token, host_id):
            logger.warning(f"用户 {user_id} 的令牌验证失败")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
            return
        
        # 获取主机信息
        # logger.debug(f"获取主机 {host_id} 的信息")
        db_host = await service.get_host(db, host_id)
        if not db_host:
            logger.warning(f"主机 {host_id} 不存在")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Host not found")
            return
        
        # 建立 SSH 连接
        try:
            logger.info(f"尝试建立到主机 {db_host.address}:{db_host.port} 的SSH连接")
            ssh_client = await self._create_ssh_connection(db_host)
            channel = ssh_client.invoke_shell(term='xterm-256color', width=100, height=30)
            logger.info(f"SSH连接成功，主机 {db_host.address}:{db_host.port}")
            
            # 存储连接信息
            connection_key = f"{host_id}_{user_id}"
            self.active_connections[connection_key] = {
                'websocket': websocket,
                'ssh_client': ssh_client,
                'channel': channel,
                'user': current_user
            }
            # logger.debug(f"已存储连接信息，连接键: {connection_key}")
            
            # 启动数据转发
            await self._start_data_forwarding(websocket, channel, connection_key)
            
        except Exception as e:
            logger.error(f"SSH连接失败: {str(e)}", exc_info=True)
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason=f"SSH connection failed: {str(e)}")
    
    async def _validate_token(self, token: str, host_id: int) -> bool:
        """验证令牌有效性"""
        try:
            # 令牌格式：host_id:timestamp:signature
            parts = token.split(':')
            if len(parts) != 3 or parts[0] != str(host_id):
                return False
                
            # 检查时间戳是否在有效期内（5分钟）
            token_timestamp = int(parts[1])
            current_time = int(time.time())
            if current_time - token_timestamp > 300:  # 5分钟有效期
                return False
                
            # 从配置中获取密钥
            from config.settings import settings
            message = f"{host_id}:{token_timestamp}"
            expected_signature = hmac.new(
                settings.SECRET_KEY.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return parts[2] == expected_signature
        except Exception as e:
            logger.error(f"令牌验证失败: {e}")
            return False
    
    async def _create_ssh_connection(self, db_host: models.Host) -> paramiko.SSHClient:
        """创建 SSH 连接"""
        def _connect():
            logger.info(f"开始创建SSH连接，主机: {db_host.address}:{db_host.port}")
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 获取属性值
            auth_method = getattr(db_host, 'auth_method', '')
            password_field = getattr(db_host, 'password', None)
            private_key_field = getattr(db_host, 'private_key', None)
            private_key_password_field = getattr(db_host, 'private_key_password', None)
            address = getattr(db_host, 'address', '')
            port = getattr(db_host, 'port', 22)
            username = getattr(db_host, 'username', '')
            
            # logger.debug(f"连接参数: 主机={address}, 端口={port}, 用户名={username}, 认证方式={auth_method}")
            
            try:
                if auth_method == "password" and password_field:
                    # 密码认证
                    # logger.debug("使用密码认证方式")
                    try:
                        password = decrypt_password(str(password_field))
                        # logger.debug("成功解密密码")
                    except Exception as decrypt_error:
                        logger.error(f"密码解密失败: {decrypt_error}", exc_info=True)
                        raise Exception(f"密码解密失败: {str(decrypt_error)}")
                        
                    ssh_client.connect(
                        hostname=str(address),
                        port=int(port),
                        username=str(username),
                        password=password,
                        timeout=10
                    )
                    logger.info("密码认证成功")
                    
                elif auth_method == "key" and private_key_field:
                    # 密钥认证
                    # logger.debug("使用密钥认证方式")
                    private_key = str(private_key_field)
                    private_key_password = None
                    
                    # 检查私钥内容
                    if len(private_key.strip()) < 50:
                        logger.warning("私钥内容异常简短，可能是无效的私钥")
                    
                    if private_key_password_field:
                        try:
                            private_key_password = decrypt_password(str(private_key_password_field))
                            # logger.debug("成功解密私钥密码")
                        except Exception as decrypt_error:
                            logger.error(f"私钥密码解密失败: {decrypt_error}", exc_info=True)
                            # 解密失败时，将私钥密码字段设为None
                            private_key_password = None
                            # logger.debug("继续尝试不带密码加载私钥")
                    
                    # 使用通用的密钥加载方法
                    try:
                        # logger.debug("尝试加载SSH私钥")
                        pkey = ssh_service.SSHService._load_private_key(private_key, private_key_password)
                        if not pkey:
                            raise Exception("无法加载私钥，不支持的密钥格式或密码错误")
                        logger.info("成功加载SSH私钥")
                    except Exception as key_error:
                        logger.error(f"私钥加载失败: {key_error}", exc_info=True)
                        raise Exception(f"私钥加载失败: {str(key_error)}")
                    
                    ssh_client.connect(
                        hostname=str(address),
                        port=int(port),
                        username=str(username),
                        pkey=pkey,
                        timeout=10
                    )
                    logger.info("密钥认证成功")
                    
                else:
                    error_msg = "未提供有效的认证信息"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                logger.info(f"SSH连接成功建立: {address}:{port}")
                return ssh_client
            except paramiko.AuthenticationException:
                logger.error(f"SSH认证失败，请检查用户名和密码/密钥")
                raise Exception("SSH认证失败，请检查用户名和密码/密钥")
            except paramiko.SSHException as e:
                logger.error(f"SSH连接错误: {str(e)}")
                raise Exception(f"SSH连接错误: {str(e)}")
            except Exception as e:
                logger.error(f"SSH连接创建失败: {str(e)}", exc_info=True)
                raise
            
        # 在线程池中执行阻塞的SSH连接操作
        return await asyncio.get_event_loop().run_in_executor(None, _connect)
    
    async def _start_data_forwarding(self, websocket: WebSocket, channel, connection_key: str):
        """启动数据转发"""
        try:
            # 首先接受WebSocket连接
            await websocket.accept()
            
            # 发送初始欢迎信息
            welcome_msg = f"\r\n\x1b[1;34m*** Connected to host {connection_key.split('_')[0]} ***\x1b[0m\r\n"
            await websocket.send_text(welcome_msg)
            
            # 获取当前事件循环
            loop = asyncio.get_event_loop()
            
            # 启动后台线程转发SSH输出到WebSocket
            def forward_ssh_output():
                while True:
                    try:
                        # 使用 select 等待数据，避免忙等待
                        readable, _, _ = select.select([channel], [], [], 0.1)
                        if readable:
                            data = channel.recv(4096).decode('utf-8', errors='ignore')
                            if data:
                                # 在事件循环中发送数据
                                asyncio.run_coroutine_threadsafe(
                                    websocket.send_text(data), 
                                    loop
                                )
                    except Exception as e:
                        logger.error(f"SSH输出转发错误: {e}")
                        break
            
            thread = threading.Thread(target=forward_ssh_output)
            thread.daemon = True
            thread.start()
            
            # 监听WebSocket输入并转发到SSH
            while True:
                try:
                    message = await websocket.receive_text()
                    data = json.loads(message)
                    
                    if data['type'] == 'input':
                        channel.send(data['data'])
                    elif data['type'] == 'resize':
                        # 处理终端大小调整
                        new_size = data['data']
                        channel.resize_pty(
                            width=new_size['cols'],
                            height=new_size['rows']
                        )
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析错误: {e}")
                    continue
                except Exception as e:
                    logger.error(f"WebSocket接收错误: {e}")
                    break
        except Exception as e:
            logger.error(f"数据转发错误: {e}")
        finally:
            # 清理连接
            await self._cleanup_connection(connection_key)
    
    async def _cleanup_connection(self, connection_key: str):
        """清理连接资源"""
        if connection_key in self.active_connections:
            conn_info = self.active_connections[connection_key]
            
            # 关闭SSH连接
            if 'channel' in conn_info:
                try:
                    conn_info['channel'].close()
                except Exception as e:
                    logger.error(f"关闭SSH通道失败: {e}")
            
            if 'ssh_client' in conn_info:
                try:
                    conn_info['ssh_client'].close()
                except Exception as e:
                    logger.error(f"关闭SSH客户端失败: {e}")
            
            # 从活动连接中移除
            del self.active_connections[connection_key]
            logger.info(f"连接 {connection_key} 已清理")