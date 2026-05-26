from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
import docker
import asyncio
import time
import os
import logging
import subprocess
import tempfile
from datetime import datetime, timedelta
from dateutil import parser  # 添加dateutil.parser导入

# 获取logger实例
logger = logging.getLogger(__name__)

from app.container.models import DockerNode
from app.container.schemas import (
    DockerNodeCreate, DockerNodeUpdate, DockerNodeStatus,
    ContainerListResponse, ContainerSummary, ContainerInspectResponse, ContainerLogsResponse,
    ContainerOperationResponse, ContainerExecRequest, ContainerExecResponse,
    ContainerStatsResponse, DockerInfo, ContainerCreateRequest, ExposedPort, VolumeMount,
    ResourceLimit, ContainerCommitResponse
)



def create_docker_client_with_tls(config: Dict[str, Any]):
    """创建带有TLS配置的Docker客户端
    
    使用证书文件路径直接创建Docker客户端
    """
    tls_kwargs = {}
    
    try:
        # 处理CA证书
        if config['tls'].get('ca_cert_path'):
            tls_kwargs['ca_cert'] = config['tls']['ca_cert_path']
            
        # 处理客户端证书和密钥
        if config['tls'].get('client_cert_path') and config['tls'].get('client_key_path'):
            tls_kwargs['client_cert'] = (config['tls']['client_cert_path'], config['tls']['client_key_path'])
        
        tls_config = docker.tls.TLSConfig(**tls_kwargs, verify=True)
        client = docker.DockerClient(
            base_url=config['base_url'],
            tls=tls_config
        )
        
        # 不需要临时文件，返回客户端和空列表
        return client, []
    except Exception as e:
        raise e




def read_certificate_content(cert_path: Optional[str]) -> Optional[str]:
    """读取证书文件内容
    
    Args:
        cert_path: 证书文件路径
        
    Returns:
        证书文件内容，如果文件不存在或读取失败则返回None
    """
    if not cert_path or not os.path.exists(cert_path):
        return None
    
    try:
        with open(cert_path, 'r') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取证书文件失败 {cert_path}: {str(e)}")
        return None


def save_certificate_files(identifier: str, ca_cert_content: Optional[str], client_cert_content: Optional[str], client_key_content: Optional[str]) -> tuple[str, str, str]:
    """保存证书文件到指定路径
    
    Args:
        identifier: 节点标识
        ca_cert_content: CA证书内容
        client_cert_content: 客户端证书内容
        client_key_content: 客户端密钥内容
        
    Returns:
        (ca_cert_path, client_cert_path, client_key_path): 证书文件路径元组
    """
    # 证书根目录
    tls_root_dir = '/opt/blackpotbpanel-v2/server/tlscert'
    # 节点证书目录
    node_cert_dir = os.path.join(tls_root_dir, identifier)
    
    # 创建目录（如果不存在）
    os.makedirs(node_cert_dir, exist_ok=True)
    # 设置目录权限为700
    os.chmod(node_cert_dir, 0o700)
    
    # 证书文件路径
    ca_cert_path = os.path.join(node_cert_dir, 'ca.pem')
    client_cert_path = os.path.join(node_cert_dir, 'cert.pem')
    client_key_path = os.path.join(node_cert_dir, 'key.pem')
    
    # 保存证书文件
    if ca_cert_content:
        with open(ca_cert_path, 'w') as f:
            f.write(ca_cert_content)
        # 设置文件权限为600
        os.chmod(ca_cert_path, 0o600)
    
    if client_cert_content:
        with open(client_cert_path, 'w') as f:
            f.write(client_cert_content)
        # 设置文件权限为600
        os.chmod(client_cert_path, 0o600)
    
    if client_key_content:
        with open(client_key_path, 'w') as f:
            f.write(client_key_content)
        # 设置文件权限为600
        os.chmod(client_key_path, 0o600)
    
    return ca_cert_path, client_cert_path, client_key_path

class DockerNodeService:
    """Docker节点服务类"""
    
    @staticmethod
    async def create_container(db: AsyncSession, node_id: int, req: ContainerCreateRequest) -> ContainerOperationResponse:
        node = await DockerNodeService.get_docker_node(db, node_id)
        try:
            config = node.connection_config
            loop = asyncio.get_running_loop()
            def create_sync():
                try:
                    if 'tls' in config:
                        client, _ = create_docker_client_with_tls(config)
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    try:
                        existing = client.containers.get(req.name)
                        if existing:
                            raise HTTPException(status_code=400, detail="容器名称已存在")
                    except docker.errors.NotFound:
                        pass
                    labels = {}
                    for item in req.labels or []:
                        if '=' in item:
                            k, v = item.split('=', 1)
                            labels[k] = v
                    mounts = []
                    from docker.types import Mount
                    for m in req.volumes or []:
                        ro = (m.mode or 'rw') == 'ro'
                        mounts.append(Mount(target=m.containerDir, source=m.sourceDir, type=m.type, read_only=ro, propagation=m.shared))
                    ports = {}
                    def add_port_mapping(host_ip, host_port, container_port, proto):
                        key = f"{container_port}/{proto}"
                        if host_ip:
                            ports[key] = (host_ip, int(host_port))
                        else:
                            ports[key] = int(host_port)
                    for p in req.exposedPorts or []:
                        hp = p.hostPort
                        cp = p.containerPort
                        proto = (p.protocol or 'tcp').lower()
                        host_ip = p.hostIP or ''
                        if '-' in hp and '-' in cp:
                            hs, he = hp.split('-', 1)
                            cs, ce = cp.split('-', 1)
                            hs_i = int(hs); he_i = int(he)
                            cs_i = int(cs); ce_i = int(ce)
                            span_h = he_i - hs_i
                            span_c = ce_i - cs_i
                            count = min(span_h, span_c) + 1
                            for i in range(count):
                                add_port_mapping(host_ip, hs_i + i, cs_i + i, proto)
                        else:
                            add_port_mapping(host_ip, int(hp.split('-')[0]), int(cp.split('-')[0]), proto)
                    nano_cpus = int((req.nanoCPUs or 0) * 1000000000)
                    mem_limit = int((req.memory or 0) * 1024 * 1024) if (req.memory or 0) > 0 else None
                    dns_list = req.dns or None
                    restart_policy = {'Name': req.restartPolicy or 'no'}
                    if (req.restartPolicy or 'no') == 'on-failure':
                        restart_policy['MaximumRetryCount'] = 5
                    network_mode = None
                    if req.network in ['host', 'none', 'bridge']:
                        network_mode = req.network
                    host_config = client.api.create_host_config(
                        privileged=req.privileged,
                        auto_remove=req.autoRemove,
                        publish_all_ports=req.publishAllPorts,
                        restart_policy=restart_policy,
                        cpu_shares=req.cpuShares or 0,
                        nano_cpus=nano_cpus,
                        mem_limit=mem_limit,
                        dns=dns_list,
                        mounts=mounts,
                        network_mode=network_mode,
                        port_bindings=ports or None
                    )
                    environment = req.env or None
                    entrypoint = req.entrypoint or None
                    command = req.cmd or None
                    exposed_ports = list(ports.keys()) if ports else None
                    created = client.api.create_container(
                        image=req.image,
                        name=req.name,
                        command=command,
                        entrypoint=entrypoint,
                        tty=req.tty,
                        stdin_open=req.openStdin,
                        hostname=req.hostname,
                        domainname=req.domainName,
                        user=req.user,
                        working_dir=req.workingDir,
                        environment=environment,
                        labels=labels or None,
                        host_config=host_config,
                        ports=exposed_ports
                    )
                    container_id = created.get('Id')
                    client.api.start(container_id)
                    container = client.containers.get(container_id)
                    if req.network and req.network not in ['host', 'none', 'bridge']:
                        try:
                            client.api.connect_container_to_network(container.id, req.network, ipv4_address=req.ipv4 or None, ipv6_address=req.ipv6 or None)
                        except Exception:
                            pass
                    container.start()
                    return ContainerOperationResponse(
                        container_id=container.id,
                        container_name=req.name,
                        operation="create",
                        success=True,
                        message="容器创建并启动成功"
                    )
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"创建容器失败: {str(e)}")
                finally:
                    if 'client' in locals():
                        client.close()
            response = await loop.run_in_executor(None, create_sync)
            return response
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"创建容器时发生错误: {str(e)}")
    async def create_docker_node(db: AsyncSession, node_data: DockerNodeCreate) -> DockerNode:
        """创建Docker节点"""
        # 检查节点名称是否已存在
        existing_node = await db.execute(
            select(DockerNode).where(DockerNode.name == node_data.name)
        )
        if existing_node.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="节点名称已存在")
        
        # 创建节点对象
        db_node = DockerNode(**node_data.model_dump())
        
        # 如果启用TLS并提供了证书内容
        if node_data.use_tls and node_data.ca_cert and node_data.client_cert and node_data.client_key:
            try:
                # 确保identifier存在
                if not db_node.identifier:
                    # 如果没有提供identifier，使用名称的小写形式并替换特殊字符
                    db_node.identifier = db_node.name.lower().replace(' ', '_').replace('-', '_')
                
                # 使用线程池异步保存证书文件
                loop = asyncio.get_running_loop()
                ca_cert_path, client_cert_path, client_key_path = await loop.run_in_executor(
                    None,
                    save_certificate_files,
                    db_node.identifier,
                    node_data.ca_cert,
                    node_data.client_cert,
                    node_data.client_key
                )
                
                # 更新数据库中的证书路径字段
                db_node.ca_cert = ca_cert_path
                db_node.client_cert = client_cert_path
                db_node.client_key = client_key_path
                logger.info(f"成功保存节点 {db_node.name} 的TLS证书文件")
            except Exception as e:
                logger.error(f"保存TLS证书文件失败: {str(e)}")
                raise HTTPException(status_code=500, detail=f"保存TLS证书失败: {str(e)}")
        
        # 添加到数据库
        db.add(db_node)
        await db.commit()
        await db.refresh(db_node)
        
        # 如果提供了compose_path，则创建对应的本地目录
        if db_node.compose_path:
            try:
                # 使用线程池异步创建目录
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, lambda: os.makedirs(db_node.compose_path, exist_ok=True))
                logger.info(f"成功创建Compose目录: {db_node.compose_path}")
            except Exception as e:
                logger.error(f"创建Compose目录失败 {db_node.compose_path}: {str(e)}")
                # 目录创建失败不影响节点创建，只记录错误
        
        return db_node
    
    @staticmethod
    async def get_docker_nodes(db: AsyncSession, skip: int = 0, limit: int = 100) -> tuple[List[DockerNode], int]:
        """获取Docker节点列表"""
        # 获取总数
        total_result = await db.execute(
            select(func.count(DockerNode.id))
        )
        total = total_result.scalar()
        
        # 获取分页数据
        result = await db.execute(
            select(DockerNode)
            .offset(skip)
            .limit(limit)
            .order_by(DockerNode.id)
        )
        nodes = result.scalars().all()
        
        # 创建节点副本并读取证书内容
        nodes_with_cert_content = []
        for node in nodes:
            # 创建节点副本
            node_copy = node.__class__()
            # 复制所有属性
            for key, value in vars(node).items():
                setattr(node_copy, key, value)
            
            # 如果启用TLS，读取证书内容
            if node.use_tls:
                # 保存原始路径到临时属性，用于内部操作
                node_copy._original_ca_cert = node.ca_cert
                node_copy._original_client_cert = node.client_cert
                node_copy._original_client_key = node.client_key
                
                # 读取证书内容
                loop = asyncio.get_running_loop()
                node_copy.ca_cert = await loop.run_in_executor(None, read_certificate_content, node.ca_cert)
                node_copy.client_cert = await loop.run_in_executor(None, read_certificate_content, node.client_cert)
                node_copy.client_key = await loop.run_in_executor(None, read_certificate_content, node.client_key)
            
            nodes_with_cert_content.append(node_copy)
        
        return nodes_with_cert_content, total
    
    @staticmethod
    async def get_docker_node(db: AsyncSession, node_id: int) -> Optional[DockerNode]:
        """根据ID获取Docker节点"""
        result = await db.execute(
            select(DockerNode).where(DockerNode.id == node_id)
        )
        node = result.scalar_one_or_none()
        if not node:
            raise HTTPException(status_code=404, detail="节点不存在")
        
        # 创建节点副本
        node_copy = node.__class__()
        # 复制所有属性
        for key, value in vars(node).items():
            setattr(node_copy, key, value)
        
        # 如果启用TLS，读取证书内容
        if node.use_tls:
            # 保存原始路径到临时属性，用于内部操作
            node_copy._original_ca_cert = node.ca_cert
            node_copy._original_client_cert = node.client_cert
            node_copy._original_client_key = node.client_key
            
            # 读取证书内容
            loop = asyncio.get_running_loop()
            node_copy.ca_cert = await loop.run_in_executor(None, read_certificate_content, node.ca_cert)
            node_copy.client_cert = await loop.run_in_executor(None, read_certificate_content, node.client_cert)
            node_copy.client_key = await loop.run_in_executor(None, read_certificate_content, node.client_key)
        
        return node_copy
    
    @staticmethod
    async def update_docker_node(db: AsyncSession, node_id: int, node_update: DockerNodeUpdate) -> DockerNode:
        """更新Docker节点信息"""
        try:
            # 直接从数据库查询原始节点对象
            result = await db.execute(select(DockerNode).where(DockerNode.id == node_id))
            db_node = result.scalar_one_or_none()
            if not db_node:
                raise HTTPException(status_code=404, detail="节点不存在")
            
            # 保存原始compose_path，用于后续判断是否需要创建新目录
            old_compose_path = db_node.compose_path
            
            # 检查是否需要更新TLS证书
            need_update_cert = False
            cert_update_data = {}
            if node_update.use_tls is not None or node_update.ca_cert is not None or node_update.client_cert is not None or node_update.client_key is not None:
                # 准备更新的证书内容
                if node_update.ca_cert is not None:
                    cert_update_data['ca_cert'] = node_update.ca_cert
                if node_update.client_cert is not None:
                    cert_update_data['client_cert'] = node_update.client_cert
                if node_update.client_key is not None:
                    cert_update_data['client_key'] = node_update.client_key
                
                # 如果启用TLS并提供了至少一个证书内容，需要更新
                if (node_update.use_tls or db_node.use_tls) and any(cert_update_data.values()):
                    need_update_cert = True
            
            # 更新节点信息（排除证书字段，稍后单独处理）
            update_data = node_update.model_dump(exclude_unset=True)
            # 临时保存证书字段的值，稍后处理
            cert_fields = ['ca_cert', 'client_cert', 'client_key']
            temp_cert_data = {}
            for field in cert_fields:
                if field in update_data:
                    temp_cert_data[field] = update_data.pop(field)
            
            for field, value in update_data.items():
                setattr(db_node, field, value)
            
            # 处理TLS证书更新
            if need_update_cert:
                try:
                    # 确保identifier存在
                    if not db_node.identifier:
                        db_node.identifier = db_node.name.lower().replace(' ', '_').replace('-', '_')
                    
                    # 准备证书内容（使用新值或读取现有证书文件内容）
                    ca_cert_content = temp_cert_data.get('ca_cert')
                    client_cert_content = temp_cert_data.get('client_cert')
                    client_key_content = temp_cert_data.get('client_key')
                    
                    # 如果没有提供新的证书内容且存在证书文件，则读取现有文件内容
                    loop = asyncio.get_running_loop()
                    if ca_cert_content is None and db_node.ca_cert:
                        ca_cert_content = await loop.run_in_executor(None, read_certificate_content, db_node.ca_cert)
                    if client_cert_content is None and db_node.client_cert:
                        client_cert_content = await loop.run_in_executor(None, read_certificate_content, db_node.client_cert)
                    if client_key_content is None and db_node.client_key:
                        client_key_content = await loop.run_in_executor(None, read_certificate_content, db_node.client_key)
                    
                    # 使用线程池异步保存证书文件
                    loop = asyncio.get_running_loop()
                    ca_cert_path, client_cert_path, client_key_path = await loop.run_in_executor(
                        None,
                        save_certificate_files,
                        db_node.identifier,
                        ca_cert_content,
                        client_cert_content,
                        client_key_content
                    )
                    
                    # 更新数据库中的证书路径字段
                    db_node.ca_cert = ca_cert_path
                    db_node.client_cert = client_cert_path
                    db_node.client_key = client_key_path
                    logger.info(f"成功更新节点 {db_node.name} 的TLS证书文件")
                except Exception as e:
                    logger.error(f"更新TLS证书文件失败: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"更新TLS证书失败: {str(e)}")
            
            # 使用显式的事务管理，确保事务正确提交
            try:
                await db.commit()
                logger.info(f"Docker节点 {node_id} 更新成功，准备刷新对象")
                
                # 刷新节点信息
                try:
                    # 先检查对象是否仍然在会话中
                    if db_node in db:
                        await db.refresh(db_node)
                        logger.info(f"成功刷新Docker节点 {node_id} 对象")
                    else:
                        # 如果对象已从会话中分离，重新查询获取最新对象
                        logger.warning(f"节点对象已从会话中分离，重新查询节点 {node_id}")
                        result = await db.execute(select(DockerNode).where(DockerNode.id == node_id))
                        db_node = result.scalar_one_or_none()
                        if not db_node:
                            raise HTTPException(status_code=404, detail="更新后的节点不存在")
                except Exception as refresh_error:
                    logger.error(f"刷新Docker节点 {node_id} 时发生错误: {str(refresh_error)}")
                    # 如果刷新失败，尝试重新获取节点
                    result = await db.execute(select(DockerNode).where(DockerNode.id == node_id))
                    db_node = result.scalar_one_or_none()
                    if not db_node:
                        raise HTTPException(status_code=404, detail="更新后的节点不存在")
                        
            except Exception as commit_error:
                # 如果提交失败，回滚事务
                await db.rollback()
                logger.error(f"Docker节点 {node_id} 更新时事务提交失败: {str(commit_error)}")
                raise HTTPException(status_code=500, detail=f"更新节点时数据库提交失败: {str(commit_error)}")
            
            # 如果compose_path发生变化，则创建新的目录
            if db_node.compose_path and db_node.compose_path != old_compose_path:
                try:
                    # 使用线程池异步创建目录
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, lambda: os.makedirs(db_node.compose_path, exist_ok=True))
                    logger.info(f"成功创建更新后的Compose目录: {db_node.compose_path}")
                except Exception as e:
                    logger.error(f"创建更新后的Compose目录失败 {db_node.compose_path}: {str(e)}")
                    # 目录创建失败不影响节点更新，只记录错误
            
            return db_node
            
        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            # 捕获其他异常，确保事务回滚
            try:
                await db.rollback()
            except:
                pass
            logger.error(f"更新Docker节点 {node_id} 时发生错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"更新节点失败: {str(e)}")

    @staticmethod
    async def delete_docker_node(db: AsyncSession, node_id: int) -> bool:
        """删除Docker节点"""
        try:
            # 先检查节点是否存在
            result = await db.execute(
                select(func.count(DockerNode.id)).where(DockerNode.id == node_id)
            )
            count = result.scalar()
            if count == 0:
                raise HTTPException(status_code=404, detail="节点不存在")
            
            # 使用直接的delete语句删除节点，避免先查询对象可能导致的状态问题
            delete_stmt = delete(DockerNode).where(DockerNode.id == node_id)
            await db.execute(delete_stmt)
            
            # 使用显式的事务管理，确保事务正确提交
            try:
                await db.commit()
                logger.info(f"Docker节点 {node_id} 删除成功")
                return True
            except Exception as commit_error:
                # 如果提交失败，回滚事务
                await db.rollback()
                logger.error(f"Docker节点 {node_id} 删除时事务提交失败: {str(commit_error)}")
                raise HTTPException(status_code=500, detail=f"删除节点时数据库提交失败: {str(commit_error)}")
                
        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            # 捕获其他异常，确保事务回滚
            try:
                await db.rollback()
            except:
                pass
            logger.error(f"删除Docker节点 {node_id} 时发生错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"删除节点失败: {str(e)}")
    
    @staticmethod
    async def check_docker_node_status(node: DockerNode) -> DockerNodeStatus:
        """检查Docker节点状态
        
        连接Docker节点并检查是否在线，返回节点状态信息
        """
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来检查节点状态
            def check_status_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        client, _ = create_docker_client_with_tls(config)
                        # 尝试ping Docker守护进程
                        client.ping()
                        return True, None
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                        # 尝试ping Docker守护进程
                        client.ping()
                        return True, None
                except Exception as e:
                    return False, str(e)
            
            # 异步执行状态检查
            is_online, error_msg = await loop.run_in_executor(None, check_status_sync)
            
            # 构建状态响应
            if is_online:
                return DockerNodeStatus(
                    node_id=node.id,
                    is_online=True,
                    status="online",
                    error_message=None,
                    check_time=datetime.now()
                )
            else:
                return DockerNodeStatus(
                    node_id=node.id,
                    is_online=False,
                    status="error" if error_msg else "offline",
                    error_message=error_msg,
                    check_time=datetime.now()
                )
                
        except Exception as e:
            # 处理其他可能的错误
            return DockerNodeStatus(
                node_id=node.id,
                is_online=False,
                status="error",
                error_message=f"状态检查失败: {str(e)}",
                check_time=datetime.now()
            )
    
    @staticmethod
    async def get_docker_node_status(db: AsyncSession, node_id: int) -> DockerNodeStatus:
        """获取指定Docker节点的状态"""
        # 获取节点
        node = await DockerNodeService.get_docker_node(db, node_id)
        
        # 检查节点状态
        return await DockerNodeService.check_docker_node_status(node)
    
    @staticmethod
    async def get_containers(db: AsyncSession, node_id: int) -> ContainerListResponse:
        """获取指定Docker节点的容器列表"""
        # 获取节点
        node = await DockerNodeService.get_docker_node(db, node_id)
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来获取容器列表
            def get_containers_sync():
                try:
                    # 创建Docker客户端并获取容器
                    containers = []
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        client, _ = create_docker_client_with_tls(config)
                        # 获取所有容器（包括已停止的）
                        containers = client.containers.list(all=True)
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                        # 获取所有容器（包括已停止的）
                        containers = client.containers.list(all=True)
                    
                    # 转换为响应格式
                    container_list = []
                    for container in containers:
                        # 构建端口映射字符串列表，显示所有暴露的端口（含无宿主机映射的端口）
                        ports = []
                        if container.attrs.get('NetworkSettings', {}).get('Ports'):
                            for private_port, mappings in container.attrs['NetworkSettings']['Ports'].items():
                                # 提取端口号和协议
                                port_parts = private_port.split('/')
                                private_port_num = port_parts[0]
                                protocol = port_parts[1] if len(port_parts) > 1 else 'tcp'
                                
                                # 如果有宿主机映射，显示映射信息
                                if mappings:
                                    for mapping in mappings:
                                        host_ip = mapping.get('HostIp', '')
                                        host_port = mapping.get('HostPort')
                                        if host_port:
                                            # 确保IP地址格式正确，避免空IP
                                            display_ip = host_ip if host_ip else '0.0.0.0'
                                            # 格式化为: IP:host_port->private_port/protocol
                                            port_str = f"{display_ip}:{host_port}->{private_port_num}/{protocol}"
                                            ports.append(port_str)
                                # 如果没有宿主机映射，仅显示容器端口
                                else:
                                    port_str = f"{private_port_num}/{protocol}"
                                    ports.append(port_str)
                        
                        # 提取网络IP地址列表
                        network_ips = []
                        networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
                        for net_name, net_config in networks.items():
                            if 'IPAddress' in net_config and net_config['IPAddress']:
                                network_ips.append(net_config['IPAddress'])
                        
                        # 处理创建时间，格式化为YYYY-MM-DD HH:MM:SS
                        created_str = container.attrs.get('Created')
                        if created_str:
                            # 使用dateutil.parser处理各种ISO格式的时间字符串，包括9位纳秒精度
                            created_dt = parser.isoparse(created_str)
                            create_time_str = created_dt.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            create_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        # 提取容器名称（增强版，支持多种数据结构）
                        container_name = ""
                        try:
                            # 尝试多种可能的名称字段路径
                            # 1. 检查attrs中的Names字段（列表形式）
                            if container.attrs.get('Names') and isinstance(container.attrs['Names'], list) and container.attrs['Names']:
                                container_name = container.attrs['Names'][0].lstrip('/')
                            # 2. 检查attrs中的Names字段（字符串形式）
                            elif container.attrs.get('Names') and isinstance(container.attrs['Names'], str):
                                container_name = container.attrs['Names'].lstrip('/')
                            # 3. 检查attrs中的Name字段（某些版本可能使用这个字段）
                            elif container.attrs.get('Name'):
                                container_name = container.attrs['Name'].lstrip('/')
                        except Exception:
                            pass  # 忽略所有提取名称过程中的错误
                        
                        # 如果还是没有名称，使用容器ID的前12个字符作为默认名称
                        if not container_name:
                            container_name = container.id[:12]
                        
                        container_summary = ContainerSummary(
                            containerID=container.id,
                            name=container_name,
                            imageID=container.attrs.get('Image', ''),
                            imageName=container.image.tags[0] if container.image.tags else container.image.id[:12],
                            createTime=create_time_str,
                            state=container.attrs.get('State', {}).get('Status', ''),
                            network=network_ips,
                            ports=ports,
                            isFromApp=False,  # 默认值
                            isFromCompose=False,  # 默认值
                            appName="",  # 默认值
                            appInstallName="",  # 默认值
                            websites=None  # 默认值
                        )
                        container_list.append(container_summary)
                    
                    return container_list
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"获取容器列表失败: {str(e)}")
            
            # 异步执行获取容器列表
            container_list = await loop.run_in_executor(None, get_containers_sync)
            
            # 返回容器列表响应
            return ContainerListResponse(
                items=container_list,
                total=len(container_list)
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取容器列表时发生错误: {str(e)}")
    
    @staticmethod
    async def inspect_container(db: AsyncSession, node_id: int, container_id: str) -> ContainerInspectResponse:
        """获取指定节点上指定容器的详细信息"""
        # 获取节点
        node = await DockerNodeService.get_docker_node(db, node_id)
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来获取容器inspect信息
            def inspect_container_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        client, _ = create_docker_client_with_tls(config)
                        # 获取容器inspect信息
                        container = client.containers.get(container_id)
                        container_info = container.attrs
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                        # 获取容器inspect信息
                        container = client.containers.get(container_id)
                        container_info = container.attrs
                    
                    # 提取容器名称（增强版，支持多种数据结构）
                    container_name = ""
                    try:
                        # 尝试多种可能的名称字段路径
                        # 1. 检查attrs中的Names字段（列表形式）
                        if container_info.get('Names') and isinstance(container_info['Names'], list) and container_info['Names']:
                            container_name = container_info['Names'][0].lstrip('/')
                        # 2. 检查attrs中的Names字段（字符串形式）
                        elif container_info.get('Names') and isinstance(container_info['Names'], str):
                            container_name = container_info['Names'].lstrip('/')
                        # 3. 检查attrs中的Name字段（某些版本可能使用这个字段）
                        elif container_info.get('Name'):
                            container_name = container_info['Name'].lstrip('/')
                    except Exception:
                        pass  # 忽略所有提取名称过程中的错误
                    
                    # 如果还是没有名称，使用容器ID的前12个字符作为默认名称
                    if not container_name:
                        container_name = container_info.get('Id', '')[:12]
                    
                    # 构建响应对象
                    container_inspect = ContainerInspectResponse(
                        id=container_info.get('Id', ''),
                        name=container_name,
                        image=container_info.get('Config', {}).get('Image', ''),
                        image_id=container_info.get('Image', ''),
                        created=container_info.get('Created', ''),
                        state=container_info.get('State', {}),
                        network_settings=container_info.get('NetworkSettings', {}),
                        config=container_info.get('Config', {}),
                        host_config=container_info.get('HostConfig', {}),
                        mount_points=container_info.get('Mounts', [])
                    )
                    
                    return container_inspect
                except docker.errors.NotFound:
                    raise HTTPException(status_code=404, detail="容器不存在")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"获取容器详细信息失败: {str(e)}")
            
            # 异步执行获取容器inspect信息
            container_inspect = await loop.run_in_executor(None, inspect_container_sync)
            
            return container_inspect
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取容器详细信息时发生错误: {str(e)}")

    @staticmethod
    async def check_local_docker(db: AsyncSession):
        """检测本地Docker状态（面板部署所在的Linux服务器）
        
        通过检查 /var/run/docker.sock 是否存在并尝试连接来判断Docker是否启用
        """
        from app.container.schemas import LocalDockerStatusResponse

        socket_path = "/var/run/docker.sock"
        installed = False
        running = False
        socket_exists = os.path.exists(socket_path)
        version = None
        node_id = None
        message = ""

        loop = asyncio.get_running_loop()

        def _check_docker():
            nonlocal installed, running, version, message
            try:
                result = subprocess.run(
                    ["which", "docker"],
                    capture_output=True, text=True, timeout=5
                )
                installed = result.returncode == 0
                if not installed:
                    message = "Docker未安装"
                    return

                result = subprocess.run(
                    ["docker", "version", "--format", "{{.Server.Version}}"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    version = result.stdout.strip()
                    running = True
                    message = f"Docker服务运行中 (v{version})"
                elif socket_exists:
                    message = "Docker socket存在但服务未响应"
                else:
                    message = "Docker已安装但服务未运行"

            except FileNotFoundError:
                installed = False
                message = "Docker未安装"
            except subprocess.TimeoutExpired:
                installed = True
                message = "Docker命令执行超时"
            except Exception as e:
                message = f"Docker状态检测异常: {str(e)}"

        await loop.run_in_executor(None, _check_docker)

        if socket_exists:
            result = await db.execute(
                select(DockerNode).filter(DockerNode.identifier == "localhost")
            )
            local_node = result.scalar_one_or_none()
            if not local_node:
                result = await db.execute(
                    select(DockerNode).filter(
                        DockerNode.endpoint_type == "unix_socket",
                        DockerNode.endpoint_url == "unix:///var/run/docker.sock"
                    )
                )
                local_node = result.scalar_one_or_none()
            if local_node:
                node_id = local_node.id

        return LocalDockerStatusResponse(
            installed=installed,
            running=running,
            socket_exists=socket_exists,
            version=version,
            node_id=node_id,
            message=message
        )

    @staticmethod
    async def get_container_logs(db: AsyncSession, node_id: int, container_id: str, lines: int = 100, 
                                since: Optional[int] = None, until: Optional[int] = None, 
                                timestamps: bool = False) -> ContainerLogsResponse:
        """获取指定节点上指定容器的日志"""
        # 获取节点
        node = await DockerNodeService.get_docker_node(db, node_id)
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来获取容器日志
            def get_container_logs_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        client, _ = create_docker_client_with_tls(config)
                        # 获取容器
                        container = client.containers.get(container_id)
                        # 获取容器日志
                        logs = container.logs(
                            stdout=True,
                            stderr=True,
                            stream=False,
                            timestamps=timestamps,
                            tail=lines,
                            since=since,
                            until=until
                        )
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                        # 获取容器
                        container = client.containers.get(container_id)
                        # 获取容器日志
                        logs = container.logs(
                            stdout=True,
                            stderr=True,
                            stream=False,
                            timestamps=timestamps,
                            tail=lines,
                            since=since,
                            until=until
                        )
                    

                    
                    # 将字节转换为字符串
                    log_str = logs.decode('utf-8', errors='replace')
                    
                    # 提取容器名称（增强版，支持多种数据结构）
                    container_name = ""
                    try:
                        # 尝试多种可能的名称字段路径
                        # 1. 检查attrs中的Names字段（列表形式）
                        if container.attrs.get('Names') and isinstance(container.attrs['Names'], list) and container.attrs['Names']:
                            container_name = container.attrs['Names'][0].lstrip('/')
                        # 2. 检查attrs中的Names字段（字符串形式）
                        elif container.attrs.get('Names') and isinstance(container.attrs['Names'], str):
                            container_name = container.attrs['Names'].lstrip('/')
                        # 3. 检查attrs中的Name字段（某些版本可能使用这个字段）
                        elif container.attrs.get('Name'):
                            container_name = container.attrs['Name'].lstrip('/')
                    except Exception:
                        pass  # 忽略所有提取名称过程中的错误
                    
                    # 如果还是没有名称，使用容器ID的前12个字符作为默认名称
                    if not container_name:
                        container_name = container.id[:12]
                    
                    # 构建响应对象
                    logs_response = ContainerLogsResponse(
                        container_id=container.id,
                        container_name=container_name,
                        logs=log_str,
                        lines=lines,
                        since=since,
                        until=until,
                        timestamps=timestamps,
                        follow=False
                    )
                    
                    return logs_response
                except docker.errors.NotFound:
                    raise HTTPException(status_code=404, detail="容器不存在")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"获取容器日志失败: {str(e)}")
            
            # 异步执行获取容器日志
            logs_response = await loop.run_in_executor(None, get_container_logs_sync)
            
            return logs_response
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取容器日志时发生错误: {str(e)}")
    
    @staticmethod
    async def start_container(db: AsyncSession, node_id: int, container_id: str) -> ContainerOperationResponse:
        """启动指定节点上的指定容器"""
        # 获取节点
        node = await DockerNodeService.get_docker_node(db, node_id)
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来启动容器
            def start_container_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        client, _ = create_docker_client_with_tls(config)
                        # 获取容器
                        container = client.containers.get(container_id)
                        
                        # 创建执行实例
                        exec_instance = container.exec_run(
                            cmd=exec_request.command,
                            shell=exec_request.shell,
                            stdout=True,
                            stderr=True,
                            stdin=exec_request.stdin,
                            tty=exec_request.tty
                        )
                        
                        return ContainerExecResponse(
                            exec_id=exec_instance.id,
                            exit_code=exec_instance.exit_code,
                            stdout=exec_instance.output.decode('utf-8') if isinstance(exec_instance.output, bytes) else exec_instance.output,
                            stderr="",  # docker-py的exec_run返回的是combined output
                            success=exec_instance.exit_code == 0
                        )
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    
                    # 获取容器
                    container = client.containers.get(container_id)
                    
                    # 创建执行实例
                    exec_instance = container.exec_run(
                        cmd=exec_request.command,
                        stdout=True,
                        stderr=True,
                        stdin=exec_request.stdin,
                        tty=exec_request.tty,
                        detach=True
                    )
                    
                    # 构建响应对象
                    return ContainerExecResponse(
                        exec_id=exec_instance.id,
                        container_id=container.id,
                        command=exec_request.command,
                        success=True,
                        message="执行实例创建成功"
                    )
                except docker.errors.NotFound:
                    raise HTTPException(status_code=404, detail="容器不存在")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"创建执行实例失败: {str(e)}")
            
            # 异步执行创建执行实例
            response = await loop.run_in_executor(None, create_exec_sync)
            
            return response
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"创建容器执行实例时发生错误: {str(e)}")
    
    @staticmethod
    # get_container_terminal方法已移除（WebSocket终端功能不再需要）
    
    
    @staticmethod
    async def start_container(db: AsyncSession, node_id: int, container_id: str) -> ContainerOperationResponse:
        """启动指定节点上的指定容器"""
        # 获取节点
        node = await DockerNodeService.get_docker_node(db, node_id)
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来启动容器
            def start_container_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        client, _ = create_docker_client_with_tls(config)
                        # 获取容器
                        container = client.containers.get(container_id)
                        # 启动容器
                        container.start()
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                        # 获取容器
                        container = client.containers.get(container_id)
                        # 启动容器
                        container.start()
                    
                    # 提取容器名称（增强版，支持多种数据结构）
                    container_name = ""
                    try:
                        # 尝试多种可能的名称字段路径
                        # 1. 检查attrs中的Names字段（列表形式）
                        if container.attrs.get('Names') and isinstance(container.attrs['Names'], list) and container.attrs['Names']:
                            container_name = container.attrs['Names'][0].lstrip('/')
                        # 2. 检查attrs中的Names字段（字符串形式）
                        elif container.attrs.get('Names') and isinstance(container.attrs['Names'], str):
                            container_name = container.attrs['Names'].lstrip('/')
                        # 3. 检查attrs中的Name字段（某些版本可能使用这个字段）
                        elif container.attrs.get('Name'):
                            container_name = container.attrs['Name'].lstrip('/')
                    except Exception:
                        pass  # 忽略所有提取名称过程中的错误
                    
                    # 如果还是没有名称，使用容器ID的前12个字符作为默认名称
                    if not container_name:
                        container_name = container.id[:12]
                    
                    # 构建响应对象
                    return ContainerOperationResponse(
                        container_id=container.id,
                        container_name=container_name,
                        operation="start",
                        success=True,
                        message="容器启动成功"
                    )
                except docker.errors.NotFound:
                    raise HTTPException(status_code=404, detail="容器不存在")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"启动容器失败: {str(e)}")
            
            # 异步执行启动容器
            response = await loop.run_in_executor(None, start_container_sync)
            
            return response
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"启动容器时发生错误: {str(e)}")

    @staticmethod
    async def stop_container(db: AsyncSession, node_id: int, container_id: str, timeout: int = 10) -> ContainerOperationResponse:
        """停止指定节点上的指定容器"""
        # 获取节点
        node = await DockerNodeService.get_docker_node(db, node_id)
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来停止容器
            def stop_container_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        client, _ = create_docker_client_with_tls(config)
                        # 获取容器
                        container = client.containers.get(container_id)
                        # 停止容器
                        container.stop(timeout=timeout)
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                        # 获取容器
                        container = client.containers.get(container_id)
                        # 停止容器
                        container.stop(timeout=timeout)
                    
                    # 提取容器名称（增强版，支持多种数据结构）
                    container_name = ""
                    try:
                        # 尝试多种可能的名称字段路径
                        # 1. 检查attrs中的Names字段（列表形式）
                        if container.attrs.get('Names') and isinstance(container.attrs['Names'], list) and container.attrs['Names']:
                            container_name = container.attrs['Names'][0].lstrip('/')
                        # 2. 检查attrs中的Names字段（字符串形式）
                        elif container.attrs.get('Names') and isinstance(container.attrs['Names'], str):
                            container_name = container.attrs['Names'].lstrip('/')
                        # 3. 检查attrs中的Name字段（某些版本可能使用这个字段）
                        elif container.attrs.get('Name'):
                            container_name = container.attrs['Name'].lstrip('/')
                    except Exception:
                        pass  # 忽略所有提取名称过程中的错误
                    
                    # 如果还是没有名称，使用容器ID的前12个字符作为默认名称
                    if not container_name:
                        container_name = container.id[:12]
                    
                    # 构建响应对象
                    return ContainerOperationResponse(
                        container_id=container.id,
                        container_name=container_name,
                        operation="stop",
                        success=True,
                        message="容器停止成功"
                    )
                except docker.errors.NotFound:
                    raise HTTPException(status_code=404, detail="容器不存在")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"停止容器失败: {str(e)}")
            
            # 异步执行停止容器
            response = await loop.run_in_executor(None, stop_container_sync)
            
            return response
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"停止容器时发生错误: {str(e)}")

    @staticmethod
    async def pause_container(db: AsyncSession, node_id: int, container_id: str) -> ContainerOperationResponse:
        """暂停指定节点上的指定容器"""
        # 获取节点
        node = await DockerNodeService.get_docker_node(db, node_id)
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来暂停容器
            def pause_container_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        client, _ = create_docker_client_with_tls(config)
                        # 获取容器
                        container = client.containers.get(container_id)
                        # 暂停容器
                        container.pause()
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                        # 获取容器
                        container = client.containers.get(container_id)
                        # 暂停容器
                        container.pause()
                    
                    # 提取容器名称（增强版，支持多种数据结构）
                    container_name = ""
                    try:
                        # 尝试多种可能的名称字段路径
                        # 1. 检查attrs中的Names字段（列表形式）
                        if container.attrs.get('Names') and isinstance(container.attrs['Names'], list) and container.attrs['Names']:
                            container_name = container.attrs['Names'][0].lstrip('/')
                        # 2. 检查attrs中的Names字段（字符串形式）
                        elif container.attrs.get('Names') and isinstance(container.attrs['Names'], str):
                            container_name = container.attrs['Names'].lstrip('/')
                        # 3. 检查attrs中的Name字段（某些版本可能使用这个字段）
                        elif container.attrs.get('Name'):
                            container_name = container.attrs['Name'].lstrip('/')
                    except Exception:
                        pass  # 忽略所有提取名称过程中的错误
                    
                    # 如果还是没有名称，使用容器ID的前12个字符作为默认名称
                    if not container_name:
                        container_name = container.id[:12]
                    
                    # 构建响应对象
                    return ContainerOperationResponse(
                        container_id=container.id,
                        container_name=container_name,
                        operation="pause",
                        success=True,
                        message="容器暂停成功"
                    )
                except docker.errors.NotFound:
                    raise HTTPException(status_code=404, detail="容器不存在")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"暂停容器失败: {str(e)}")
            
            # 异步执行暂停容器
            response = await loop.run_in_executor(None, pause_container_sync)
            
            return response
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"暂停容器时发生错误: {str(e)}")

    @staticmethod
    async def unpause_container(db: AsyncSession, node_id: int, container_id: str) -> ContainerOperationResponse:
        """恢复指定节点上的指定容器"""
        # 获取节点
        node = await DockerNodeService.get_docker_node(db, node_id)
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来恢复容器
            def unpause_container_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        client, _ = create_docker_client_with_tls(config)
                        # 获取容器
                        container = client.containers.get(container_id)
                        # 恢复容器
                        container.unpause()
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                        # 获取容器
                        container = client.containers.get(container_id)
                        # 恢复容器
                        container.unpause()
                    
                    # 提取容器名称（增强版，支持多种数据结构）
                    container_name = ""
                    try:
                        # 尝试多种可能的名称字段路径
                        # 1. 检查attrs中的Names字段（列表形式）
                        if container.attrs.get('Names') and isinstance(container.attrs['Names'], list) and container.attrs['Names']:
                            container_name = container.attrs['Names'][0].lstrip('/')
                        # 2. 检查attrs中的Names字段（字符串形式）
                        elif container.attrs.get('Names') and isinstance(container.attrs['Names'], str):
                            container_name = container.attrs['Names'].lstrip('/')
                        # 3. 检查attrs中的Name字段（某些版本可能使用这个字段）
                        elif container.attrs.get('Name'):
                            container_name = container.attrs['Name'].lstrip('/')
                    except Exception:
                        pass  # 忽略所有提取名称过程中的错误
                    
                    # 如果还是没有名称，使用容器ID的前12个字符作为默认名称
                    if not container_name:
                        container_name = container.id[:12]
                    
                    # 构建响应对象
                    return ContainerOperationResponse(
                        container_id=container.id,
                        container_name=container_name,
                        operation="unpause",
                        success=True,
                        message="容器恢复成功"
                    )
                except docker.errors.NotFound:
                    raise HTTPException(status_code=404, detail="容器不存在")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"恢复容器失败: {str(e)}")
            
            # 异步执行恢复容器
            response = await loop.run_in_executor(None, unpause_container_sync)
            
            return response
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"恢复容器时发生错误: {str(e)}")

    @staticmethod
    async def restart_container(db: AsyncSession, node_id: int, container_id: str, timeout: int = 10) -> ContainerOperationResponse:
        """重启指定节点上的指定容器"""
        # 获取节点
        node = await DockerNodeService.get_docker_node(db, node_id)
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来重启容器
            def restart_container_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        client, _ = create_docker_client_with_tls(config)
                        # 获取容器
                        container = client.containers.get(container_id)
                        # 重启容器
                        container.restart(timeout=timeout)
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                        # 获取容器
                        container = client.containers.get(container_id)
                        # 重启容器
                        container.restart(timeout=timeout)
                    
                    # 提取容器名称（增强版，支持多种数据结构）
                    container_name = ""
                    try:
                        # 尝试多种可能的名称字段路径
                        # 1. 检查attrs中的Names字段（列表形式）
                        if container.attrs.get('Names') and isinstance(container.attrs['Names'], list) and container.attrs['Names']:
                            container_name = container.attrs['Names'][0].lstrip('/')
                        # 2. 检查attrs中的Names字段（字符串形式）
                        elif container.attrs.get('Names') and isinstance(container.attrs['Names'], str):
                            container_name = container.attrs['Names'].lstrip('/')
                        # 3. 检查attrs中的Name字段（某些版本可能使用这个字段）
                        elif container.attrs.get('Name'):
                            container_name = container.attrs['Name'].lstrip('/')
                    except Exception:
                        pass  # 忽略所有提取名称过程中的错误
                    
                    # 如果还是没有名称，使用容器ID的前12个字符作为默认名称
                    if not container_name:
                        container_name = container.id[:12]
                    
                    # 构建响应对象
                    return ContainerOperationResponse(
                        container_id=container.id,
                        container_name=container_name,
                        operation="restart",
                        success=True,
                        message="容器重启成功"
                    )
                except docker.errors.NotFound:
                    raise HTTPException(status_code=404, detail="容器不存在")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"重启容器失败: {str(e)}")
            
            # 异步执行重启容器
            response = await loop.run_in_executor(None, restart_container_sync)
            
            return response
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"重启容器时发生错误: {str(e)}")

    @staticmethod
    async def commit_container(db: AsyncSession, node_id: int, container_id: str, image_name: str = None) -> ContainerCommitResponse:
        """将指定节点上的指定容器提交为镜像"""
        # 从image_name中提取repository和tag
        repository = None
        tag = None
        if image_name:
            parts = image_name.split(':', 1)
            repository = parts[0]
            if len(parts) > 1:
                tag = parts[1]
        
        # 获取节点
        node = await DockerNodeService.get_docker_node(db, node_id)
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来提交容器
            def commit_container_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        client, _ = create_docker_client_with_tls(config)
                        # 获取容器
                        container = client.containers.get(container_id)
                        # 提交容器为镜像
                        image = container.commit(repository=repository, tag=tag)
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                        # 获取容器
                        container = client.containers.get(container_id)
                        # 提交容器为镜像
                        image = container.commit(repository=repository, tag=tag)
                    
                    # 构建完整镜像名称
                    full_image_name = image.tags[0] if image.tags else image.id[:12]
                    
                    # 构建响应对象
                    response_data = ContainerCommitResponse(
                        container_id=container.id,
                        image_id=image.id,
                        repository=repository,
                        tag=tag,
                        image_name=full_image_name,
                        success=True,
                        message="容器提交为镜像成功"
                    )
                    return response_data
                except docker.errors.NotFound:
                    raise HTTPException(status_code=404, detail="容器不存在")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"提交容器为镜像失败: {str(e)}")
            
            # 异步执行提交容器
            response = await loop.run_in_executor(None, commit_container_sync)
            
            return response
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"提交容器为镜像时发生错误: {str(e)}")
            
    @staticmethod
    async def delete_container(db: AsyncSession, node_id: int, container_id: str, force: bool = False) -> ContainerOperationResponse:
        """删除指定节点上的指定容器"""
        # 获取节点
        node = await DockerNodeService.get_docker_node(db, node_id)
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来删除容器
            def delete_container_sync():
                try:
                    container_name = ""
                    
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        client, _ = create_docker_client_with_tls(config)
                        # 获取容器
                        container = client.containers.get(container_id)
                        # 提取容器名称（增强版，支持多种数据结构）
                        try:
                            # 尝试多种可能的名称字段路径
                            # 1. 检查attrs中的Names字段（列表形式）
                            if container.attrs.get('Names') and isinstance(container.attrs['Names'], list) and container.attrs['Names']:
                                container_name = container.attrs['Names'][0].lstrip('/')
                            # 2. 检查attrs中的Names字段（字符串形式）
                            elif container.attrs.get('Names') and isinstance(container.attrs['Names'], str):
                                container_name = container.attrs['Names'].lstrip('/')
                            # 3. 检查attrs中的Name字段（某些版本可能使用这个字段）
                            elif container.attrs.get('Name'):
                                container_name = container.attrs['Name'].lstrip('/')
                        except Exception:
                            pass  # 忽略所有提取名称过程中的错误
                        
                        # 删除容器
                        container.remove(force=force)
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                        # 获取容器
                        container = client.containers.get(container_id)
                        
                        # 提取容器名称（增强版，支持多种数据结构）
                        try:
                            # 尝试多种可能的名称字段路径
                            # 1. 检查attrs中的Names字段（列表形式）
                            if container.attrs.get('Names') and isinstance(container.attrs['Names'], list) and container.attrs['Names']:
                                container_name = container.attrs['Names'][0].lstrip('/')
                            # 2. 检查attrs中的Names字段（字符串形式）
                            elif container.attrs.get('Names') and isinstance(container.attrs['Names'], str):
                                container_name = container.attrs['Names'].lstrip('/')
                            # 3. 检查attrs中的Name字段（某些版本可能使用这个字段）
                            elif container.attrs.get('Name'):
                                container_name = container.attrs['Name'].lstrip('/')
                        except Exception:
                            pass  # 忽略所有提取名称过程中的错误
                        
                        # 删除容器
                        container.remove(force=force)
                    
                    # 如果还是没有名称，使用容器ID的前12个字符作为默认名称
                    if not container_name:
                        container_name = container_id[:12]
                    
                    # 构建响应
                    return ContainerOperationResponse(
                        container_id=container_id,
                        container_name=container_name,
                        operation="delete",
                        success=True,
                        message="容器删除成功"
                    )
                except docker.errors.NotFound:
                    raise HTTPException(status_code=404, detail="容器不存在")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"删除容器失败: {str(e)}")
            
            # 异步执行删除容器
            response = await loop.run_in_executor(None, delete_container_sync)
            
            return response
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"删除容器时发生错误: {str(e)}")
    
    @staticmethod
    async def get_docker_info(db: AsyncSession, node_id: int) -> 'DockerInfo':
        """获取指定节点的Docker信息，包括版本、容器数量、镜像数量等"""
        # 获取节点
        node = await DockerNodeService.get_docker_node(db, node_id)
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            docker_host = config['base_url']
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来获取Docker版本和系统信息
            def get_docker_info_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        client, _ = create_docker_client_with_tls(config)
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    
                    # 获取Docker版本信息
                    version_info = client.version()
                    
                    # 获取Docker系统信息
                    system_info = client.info()
                    
                    # 关闭客户端连接
                    client.close()
                    
                    return version_info, system_info
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"获取Docker信息失败: {str(e)}")
            
            # 异步执行获取Docker版本和系统信息
            version_info, system_info = await loop.run_in_executor(None, get_docker_info_sync)
            
            # 分别获取容器、镜像、网络、存储卷和编排项目数量
            # 1. 获取容器数量，并计算运行中和已停止的容器数量
            containers = await DockerNodeService.get_containers(db, node_id)
            container_count = len(containers.items)
            
            # 计算运行中和已停止的容器数量
            running_containers = 0
            stopped_containers = 0
            for container in containers.items:
                if hasattr(container, 'state') and container.state:
                    if container.state.lower() == 'running':
                        running_containers += 1
                    else:
                        stopped_containers += 1
            
            # 2. 获取镜像数量
            from app.container.images_service import DockerImageService
            images = await DockerImageService.get_images(db, node_id)
            # 检查images对象是否有items属性，否则使用默认值0
            if hasattr(images, 'items'):
                image_count = len(images.items)
            else:
                image_count = 0
            
            # 3. 获取网络数量
            from app.container.networks_service import DockerNetworkService
            networks = await DockerNetworkService.get_networks(db, node_id)
            # 检查networks对象是否有items属性，否则使用默认值0
            if hasattr(networks, 'items'):
                network_count = len(networks.items)
            else:
                network_count = 0
            
            # 4. 获取存储卷数量
            from app.container.volumes_service import DockerVolumeService
            volumes = await DockerVolumeService.get_volumes(db, node_id)
            # 检查volumes对象是否有items属性，否则使用默认值0
            if hasattr(volumes, 'items'):
                volume_count = len(volumes.items)
            else:
                volume_count = 0
            
            # 5. 获取编排项目数量
            from app.container.compose_service import DockerComposeService
            compose_projects = await DockerComposeService.get_compose_projects(db, node_id)
            # 检查compose_projects对象是否有items属性，否则使用默认值0
            if hasattr(compose_projects, 'items'):
                compose_count = len(compose_projects.items)
            else:
                compose_count = 0
            
            # 获取存储插件列表
            storage_plugins = []
            if 'Plugins' in system_info and 'Volume' in system_info['Plugins']:
                storage_plugins = system_info['Plugins']['Volume']
            
            # 获取网络插件列表
            network_plugins = []
            if 'Plugins' in system_info and 'Network' in system_info['Plugins']:
                network_plugins = system_info['Plugins']['Network']
            
            # 获取默认日志驱动
            log_driver = system_info.get('LoggingDriver', None)
            
            # 获取文件存储驱动
            storage_driver = system_info.get('Driver', None)
            
            # 获取Docker根目录
            root_dir = system_info.get('DockerRootDir', None)
            
            # 获取CPU核心数
            cpus = system_info.get('NCPU', None)
            
            # 获取总内存大小（字节）
            total_memory_bytes = system_info.get('MemTotal', None)
            
            # 将内存字节数转换为带Gi单位的字符串
            total_memory = None
            if total_memory_bytes is not None:
                # 1 GiB = 1024^3 字节
                gibibyte = 1024 * 1024 * 1024
                total_memory_gib = total_memory_bytes / gibibyte
                # 格式化为带Gi单位的字符串，保留两位小数
                total_memory = f"{total_memory_gib:.2f} Gi"
            
            # 构建响应对象
            return DockerInfo(
                docker_host=docker_host,
                server_version=version_info.get('Version', 'Unknown'),
                container_count=container_count,
                image_count=image_count,
                network_count=network_count,
                volume_count=volume_count,
                compose_count=compose_count,
                stopped_containers=stopped_containers,
                running_containers=running_containers,
                storage_plugins=storage_plugins,
                network_plugins=network_plugins,
                log_driver=log_driver,
                storage_driver=storage_driver,
                root_dir=root_dir,
                cpus=cpus,
                total_memory=total_memory
            )
        except HTTPException:
            raise
    
    @staticmethod
    async def get_resource_limit(db: AsyncSession, node_id: int) -> 'ResourceLimit':
        """获取指定节点的资源限制信息，包括CPU核心数和内存总量(MB)"""
        # 获取节点
        node = await DockerNodeService.get_docker_node(db, node_id)
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来获取Docker系统信息
            def get_resource_info_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        client, _ = create_docker_client_with_tls(config)
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    
                    # 获取Docker系统信息
                    system_info = client.info()
                    
                    # 关闭客户端连接
                    client.close()
                    
                    return system_info
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"获取资源信息失败: {str(e)}")
            
            # 异步执行获取Docker系统信息
            system_info = await loop.run_in_executor(None, get_resource_info_sync)
            
            # 获取CPU核心数
            cpus = system_info.get('NCPU', 0)
            
            # 获取总内存大小（字节）并转换为MB
            total_memory_bytes = system_info.get('MemTotal', 0)
            # 1 MB = 1024 * 1024 字节
            total_memory_mb = int(total_memory_bytes / (1024 * 1024))
            
            # 构建响应对象
            return ResourceLimit(
                cpus=cpus,
                total_memory=total_memory_mb
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取资源限制信息时发生错误: {str(e)}")

    @staticmethod
    async def get_container_stats(db: AsyncSession, node_id: int, container_id: str) -> ContainerStatsResponse:
        """获取指定节点上指定容器的资源占用信息"""
        # 获取节点
        node = await DockerNodeService.get_docker_node(db, node_id)
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来获取容器资源占用
            def get_stats_sync():
                client = None
                stats_gen = None
                try:
                    container_name = ""
                    
                    # 创建Docker客户端
                    if 'tls' in config:
                        client, _ = create_docker_client_with_tls(config)
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    
                    container = client.containers.get(container_id)
                    
                    # 提取容器名称（增强版，支持多种数据结构）
                    try:
                        if container.attrs.get('Names') and isinstance(container.attrs['Names'], list) and container.attrs['Names']:
                            container_name = container.attrs['Names'][0].lstrip('/')
                        elif container.attrs.get('Names') and isinstance(container.attrs['Names'], str):
                            container_name = container.attrs['Names'].lstrip('/')
                        elif container.attrs.get('Name'):
                            container_name = container.attrs['Name'].lstrip('/')
                    except Exception:
                        pass
                    
                    if not container_name:
                        container_name = container_id[:12]
                    
                    # 使用流式stats，采样两次以获取准确的CPU使用率
                    # 第一次采样丢弃（初始化precpu_stats基准值），第二次采样用于计算
                    # 这与docker stats CLI的行为一致：两次采样间隔约1秒
                    stats_gen = container.stats(stream=True, decode=True)
                    _ = next(stats_gen)
                    time.sleep(1.0)
                    stats = next(stats_gen)
                    
                    # 计算CPU使用率
                    cpu_percentage = 0.0
                    try:
                        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
                        system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
                        online_cpus = stats['cpu_stats'].get('online_cpus', len(stats['cpu_stats']['cpu_usage'].get('percpu_usage', [1])))
                        if system_delta > 0 and online_cpus > 0:
                            cpu_percentage = (cpu_delta / system_delta) * online_cpus * 100
                    except (KeyError, ZeroDivisionError):
                        cpu_percentage = 0.0
                    
                    # 获取内存使用情况
                    memory_stats = stats.get('memory_stats', {})
                    
                    def calculate_actual_memory_usage(memory_stats):
                        """计算容器实际内存使用量，与docker stats CLI保持一致

                        docker stats CLI的MEM USAGE = usage - cache
                        cgroup v1使用cache字段，cgroup v2使用inactive_file字段
                        """
                        usage = memory_stats.get('usage', 0)
                        stats_data = memory_stats.get('stats', {})

                        cache = stats_data.get('cache', 0)
                        if cache > 0:
                            return max(0, usage - cache)

                        inactive_file = stats_data.get('inactive_file', 0)
                        if inactive_file > 0:
                            return max(0, usage - inactive_file)

                        return usage
                    
                    actual_memory_usage = calculate_actual_memory_usage(memory_stats)
                    
                    memory_limit = memory_stats.get('limit', 1)
                    memory_percentage = (actual_memory_usage / memory_limit) * 100 if memory_limit > 0 else 0.0
                    
                    # 获取网络IO信息
                    networks = stats.get('networks', {}) or {}
                    network_rx_bytes = 0
                    network_tx_bytes = 0
                    if networks and hasattr(networks, 'values'):
                        for network_stats in networks.values():
                            if network_stats:
                                network_rx_bytes += network_stats.get('rx_bytes', 0)
                                network_tx_bytes += network_stats.get('tx_bytes', 0)
                    
                    # 获取块设备IO信息
                    block_io = stats.get('blkio_stats', {}).get('io_service_bytes_recursive', []) or []
                    block_read_bytes = 0
                    block_write_bytes = 0
                    
                    if not block_io:
                        block_io_service_bytes = stats.get('blkio_stats', {}).get('io_service_bytes', []) or []
                        if block_io_service_bytes:
                            block_io = block_io_service_bytes
                    
                    if block_io and isinstance(block_io, list):
                        for io in block_io:
                            if io:
                                op = io.get('op', '').lower()
                                value = io.get('value', 0)
                                if op == 'read':
                                    block_read_bytes += value
                                elif op == 'write':
                                    block_write_bytes += value
                    
                    # 获取进程数量
                    pids = stats.get('pids_stats', {}).get('current', 0)
                    
                    return ContainerStatsResponse(
                        container_id=container_id,
                        container_name=container_name,
                        cpu_percentage=round(cpu_percentage, 2),
                        memory_usage=actual_memory_usage,
                        memory_limit=memory_limit,
                        memory_percentage=round(memory_percentage, 2),
                        network_rx_bytes=network_rx_bytes,
                        network_tx_bytes=network_tx_bytes,
                        block_read_bytes=block_read_bytes,
                        block_write_bytes=block_write_bytes,
                        pids=pids
                    )
                except docker.errors.NotFound:
                    raise HTTPException(status_code=404, detail="容器不存在")
                except StopIteration:
                    raise HTTPException(status_code=500, detail="容器stats流异常终止，容器可能已停止")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"获取容器资源占用失败: {str(e)}")
                finally:
                    if stats_gen is not None:
                        try:
                            stats_gen.close()
                        except Exception:
                            pass
                    if client is not None:
                        try:
                            client.close()
                        except Exception:
                            pass
            
            # 异步执行获取容器资源占用
            response = await loop.run_in_executor(None, get_stats_sync)
            
            return response
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取容器资源占用时发生错误: {str(e)}")



