from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List, Dict, Any
import docker
import asyncio
from app.container.models import DockerNode
from app.container.schemas import VolumeSummary, VolumeListResponse, VolumeDetailResponse, VolumeOperationResponse, VolumeCreate, VolumeOptionListResponse, VolumeOption


class DockerVolumeService:
    """Docker存储卷服务类"""
    
    @staticmethod
    async def get_docker_client(node: DockerNode):
        """
        获取Docker客户端连接
        
        Args:
            node: Docker节点对象
            
        Returns:
            docker.DockerClient: Docker客户端实例
            
        Raises:
            HTTPException: 当连接失败时抛出
        """
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来创建Docker客户端
            def create_client_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        from app.container.service import create_docker_client_with_tls
                        client, _ = create_docker_client_with_tls(config)
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    
                    # 测试连接是否成功
                    client.ping()
                    return client
                except Exception as e:
                    raise e
            
            # 异步执行创建客户端
            client = await loop.run_in_executor(None, create_client_sync)
            return client
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"连接到Docker节点失败: {str(e)}"
            )
    
    @staticmethod
    async def create_volume(db: AsyncSession, node_id: int, volume_data: VolumeCreate) -> VolumeDetailResponse:
        """
        在指定Docker节点上创建存储卷
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            volume_data: 存储卷创建数据
            
        Returns:
            VolumeDetailResponse: 创建的存储卷详细信息
            
        Raises:
            HTTPException: 当节点不存在、创建失败或连接失败时抛出
        """
        # 验证节点是否存在
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Docker节点 {node_id} 不存在"
            )
        
        try:
            # 获取Docker客户端
            docker_client = await DockerVolumeService.get_docker_client(node)
            
            # 构建创建存储卷的参数
            volume_kwargs = {
                'driver': volume_data.driver
            }
            
            # 如果提供了名称，添加到参数中
            if volume_data.name:
                volume_kwargs['name'] = volume_data.name
            
            # 如果提供了驱动选项，添加到参数中
            if volume_data.driver_opts:
                volume_kwargs['driver_opts'] = volume_data.driver_opts
            
            # 如果提供了标签，添加到参数中
            if volume_data.labels:
                volume_kwargs['labels'] = volume_data.labels
            
            # 定义同步函数来创建存储卷
            def create_volume_sync():
                try:
                    # 创建存储卷
                    volume = docker_client.volumes.create(**volume_kwargs)
                    return volume
                except docker.errors.APIError as e:
                    # 处理Docker API错误
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"创建存储卷失败: {str(e)}"
                    )
                except Exception as e:
                    # 处理其他错误
                    raise e
            
            # 异步执行创建存储卷
            loop = asyncio.get_running_loop()
            volume = await loop.run_in_executor(None, create_volume_sync)
            
            # 获取创建的存储卷信息
            volume_info = volume.attrs
            
            # 构建响应对象
            return VolumeDetailResponse(
                name=volume.name,
                driver=volume_info.get('Driver', ''),
                mountpoint=volume_info.get('Mountpoint', ''),
                labels=volume_info.get('Labels') or {},
                scope=volume_info.get('Scope', ''),
                created_at=volume_info.get('CreatedAt', ''),
                usage_count=0,  # 新创建的存储卷使用计数为0
                options=volume_info.get('Options') or {},
                cluster_volume=volume_info.get('ClusterVolume', False),
                containers={}
            )
            
        except HTTPException:
            # 重新抛出已处理的HTTP异常
            raise
        except Exception as e:
            # 处理连接错误或其他异常
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建存储卷失败: {str(e)}"
            )
    
    @staticmethod
    async def get_volumes(db: AsyncSession, node_id: int) -> VolumeListResponse:
        """
        获取指定Docker节点上的存储卷列表
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            
        Returns:
            VolumeListResponse: 存储卷列表响应对象
            
        Raises:
            HTTPException: 当节点不存在或连接失败时抛出
        """
        # 验证节点是否存在
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Docker节点 {node_id} 不存在"
            )
        
        try:
            # 获取Docker客户端
            docker_client = await DockerVolumeService.get_docker_client(node)
            
            # 获取存储卷列表
            volumes = docker_client.volumes.list()
            
            # 转换为响应模型
            volume_summaries = []
            for volume in volumes:
                # 获取存储卷详情
                volume_info = volume.attrs
                
                volume_summaries.append(VolumeSummary(
                name=volume.name,
                driver=volume_info.get('Driver', ''),
                mountpoint=volume_info.get('Mountpoint', ''),
                labels=volume_info.get('Labels') or {},  # 确保labels始终是字典类型
                scope=volume_info.get('Scope', ''),
                created_at=volume_info.get('CreatedAt', '')
            ))
            
            return VolumeListResponse(
                items=volume_summaries,
                total=len(volume_summaries)
            )
            
        except Exception as e:
            # 处理连接错误或其他异常
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取存储卷列表失败: {str(e)}"
            )
    
    @staticmethod
    async def get_volume_detail(db: AsyncSession, node_id: int, volume_id: str) -> VolumeDetailResponse:
        """
        获取指定Docker节点上的指定存储卷详细信息
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            volume_id: 存储卷ID或名称
            
        Returns:
            VolumeDetailResponse: 存储卷详细信息响应对象
            
        Raises:
            HTTPException: 当节点不存在、存储卷不存在或连接失败时抛出
        """
        # 验证节点是否存在
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Docker节点 {node_id} 不存在"
            )
        
        try:
            # 获取Docker客户端
            docker_client = await DockerVolumeService.get_docker_client(node)
            
            # 获取存储卷详情
            try:
                volume = docker_client.volumes.get(volume_id)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"存储卷 {volume_id} 不存在: {str(e)}"
                )
            
            # 获取存储卷信息
            volume_info = volume.attrs
            
            # 计算使用计数（连接的容器数量）
            containers = volume_info.get('Containers', {})
            usage_count = len(containers) if isinstance(containers, dict) else 0
            
            # 构建容器引用信息
            container_references = {}
            if isinstance(containers, dict):
                for container_id, container_data in containers.items():
                    if isinstance(container_data, dict) and 'Name' in container_data:
                        container_references[container_id] = container_data['Name']
            
            # 构建响应对象
            return VolumeDetailResponse(
                name=volume.name,
                driver=volume_info.get('Driver', ''),
                mountpoint=volume_info.get('Mountpoint', ''),
                labels=volume_info.get('Labels') or {},  # 确保labels始终是字典类型
                scope=volume_info.get('Scope', ''),
                created_at=volume_info.get('CreatedAt', ''),
                usage_count=usage_count,
                options=volume_info.get('Options') or {},  # 确保options始终是字典类型
                cluster_volume=volume_info.get('ClusterVolume', False),
                containers=container_references
            )
            
        except HTTPException:
            # 重新抛出已处理的HTTP异常
            raise
        except Exception as e:
            # 处理连接错误或其他异常
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取存储卷详情失败: {str(e)}"
            )
    
    @staticmethod
    async def delete_volume(db: AsyncSession, node_id: int, volume_id: str, force: bool = False) -> VolumeOperationResponse:
        """
        删除指定Docker节点上的指定存储卷
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            volume_id: 存储卷ID或名称
            force: 是否强制删除，默认为False
            
        Returns:
            VolumeOperationResponse: 存储卷操作响应对象
            
        Raises:
            HTTPException: 当节点不存在、存储卷不存在、存储卷正在使用或连接失败时抛出
        """
        # 验证节点是否存在
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Docker节点 {node_id} 不存在"
            )
        
        try:
            # 获取Docker客户端
            docker_client = await DockerVolumeService.get_docker_client(node)
            
            # 尝试获取存储卷
            try:
                volume = docker_client.volumes.get(volume_id)
                volume_name = volume.name
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"存储卷 {volume_id} 不存在: {str(e)}"
                )
            
            # 检查存储卷是否正在被使用
            volume_info = volume.attrs
            containers = volume_info.get('Containers', {})
            usage_count = len(containers) if isinstance(containers, dict) else 0
            
            if usage_count > 0 and not force:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"存储卷 {volume_name} 正在被 {usage_count} 个容器使用，请先停止相关容器或使用force参数强制删除"
                )
            
            # 执行删除操作
            try:
                volume.remove(force=force)
                return VolumeOperationResponse(
                    volume_id=volume_id,
                    volume_name=volume_name,
                    operation="delete",
                    success=True,
                    message=f"存储卷 {volume_name} 删除成功"
                )
            except Exception as e:
                # 处理删除失败的情况
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"删除存储卷 {volume_name} 失败: {str(e)}"
                )
                
        except HTTPException:
            # 重新抛出已处理的HTTP异常
            raise
        except Exception as e:
            # 处理连接错误或其他异常
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除存储卷失败: {str(e)}"
            )
    
    @staticmethod
    async def prune_volumes(db: AsyncSession, node_id: int) -> Dict[str, Any]:
        """
        清理指定Docker节点上所有未使用的存储卷
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            
        Returns:
            Dict[str, Any]: 清理结果，包含删除的存储卷列表和释放的空间
            
        Raises:
            HTTPException: 当节点不存在或连接失败时抛出
        """
        # 验证节点是否存在
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Docker节点 {node_id} 不存在"
            )
        
        try:
            # 获取Docker客户端
            docker_client = await DockerVolumeService.get_docker_client(node)
            
            # 定义同步函数来清理未使用的存储卷
            def prune_volumes_sync():
                try:
                    # 使用Docker API的prune方法清理未使用的存储卷
                    result = docker_client.volumes.prune()
                    return result
                except docker.errors.APIError as e:
                    # 处理Docker API错误
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"清理未使用存储卷失败: {str(e)}"
                    )
                except Exception as e:
                    # 处理其他错误
                    raise e
            
            # 异步执行清理操作
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, prune_volumes_sync)
            
            # 返回清理结果
            return {
                "deleted": result.get('VolumesDeleted', []),
                "space_reclaimed": result.get('SpaceReclaimed', 0),
                "message": f"成功清理 {len(result.get('VolumesDeleted', []))} 个未使用的存储卷"
            }
            
        except HTTPException:
            # 重新抛出已处理的HTTP异常
            raise
        except Exception as e:
            # 处理连接错误或其他异常
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"清理未使用存储卷失败: {str(e)}"
            )
    
    @staticmethod
    async def get_volume_options(db: AsyncSession, node_id: int) -> VolumeOptionListResponse:
        """
        获取指定Docker节点上的存储卷选项列表
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            
        Returns:
            VolumeOptionListResponse: 存储卷选项列表响应对象
            
        Raises:
            HTTPException: 当节点不存在或连接失败时抛出
        """
        # 验证节点是否存在
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Docker节点 {node_id} 不存在"
            )
        
        try:
            # 获取Docker客户端
            docker_client = await DockerVolumeService.get_docker_client(node)
            
            # 获取存储卷列表
            volumes = docker_client.volumes.list()
            
            # 转换为选项列表
            volume_options = []
            for volume in volumes:
                volume_options.append(VolumeOption(option=volume.name))
            
            return VolumeOptionListResponse(data=volume_options)
            
        except Exception as e:
            # 处理连接错误或其他异常
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取存储卷选项列表失败: {str(e)}"
            )