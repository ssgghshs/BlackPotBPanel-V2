from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.container.models import DockerNode
from app.container.schemas import NetworkSummary, NetworkListResponse, NetworkDetailResponse, NetworkOperationResponse, NetworkCreate, NetworkOption, NetworkOptionListResponse
import docker
import docker.errors
import asyncio
from fastapi import HTTPException


class DockerNetworkService:
    """Docker网络服务类，处理Docker网络相关的业务逻辑"""
    
    @staticmethod
    async def get_docker_client(node: DockerNode):
        """获取Docker客户端连接
        
        Args:
            node: Docker节点对象
            
        Returns:
            docker.DockerClient: Docker客户端实例
        """
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 导入create_docker_client_with_tls函数
            from app.container.service import create_docker_client_with_tls
            
            # 定义同步函数来创建Docker客户端
            def create_client_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
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
            raise HTTPException(status_code=500, detail=f"连接到Docker节点失败: {str(e)}")
    
    @staticmethod
    async def get_network_detail(db: AsyncSession, node_id: int, network_id: str) -> NetworkDetailResponse:
        """
获取指定Docker节点上的指定网络的详细信息
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            network_id: 网络ID
            
        Returns:
            NetworkDetailResponse: 网络详细信息响应
        """
        # 获取节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        
        try:
            # 获取Docker客户端
            client = await DockerNetworkService.get_docker_client(node)
            
            # 获取网络详情
            network = client.networks.get(network_id)
            network_info = network.attrs
            
            # 构建响应对象
            network_detail = NetworkDetailResponse(
                id=network.id,
                name=network.name,
                driver=network_info.get('Driver', ''),
                scope=network_info.get('Scope', ''),
                internal=network_info.get('Internal', False),
                enableIPv6=network_info.get('EnableIPv6', False),
                ipamDriver=network_info.get('IPAM', {}).get('Driver', ''),
                ipamConfig=network_info.get('IPAM', {}).get('Config', [])[0] if network_info.get('IPAM', {}).get('Config', []) else {},

                containers=network_info.get('Containers', {}),
                options=network_info.get('Options', {}),
                labels=network_info.get('Labels', {}),
                created=network_info.get('Created', '')
            )
            
            return network_detail
            
        except docker.errors.APIError as e:
            # 处理特定的Docker API错误
            error_message = str(e)
            if "No such network" in error_message:
                raise HTTPException(status_code=404, detail="网络不存在")
            else:
                raise HTTPException(status_code=500, detail=f"Docker API错误: {error_message}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取网络详情失败: {str(e)}")
        finally:
            # 关闭Docker客户端连接
            if 'client' in locals():
                client.close()
    
    @staticmethod
    async def get_networks(db: AsyncSession, node_id: int) -> NetworkListResponse:
        """获取指定Docker节点上的网络列表
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            
        Returns:
            NetworkListResponse: 网络列表响应
        """
        # 获取节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        
        try:
            # 获取Docker客户端
            client = await DockerNetworkService.get_docker_client(node)
            
            # 获取网络列表
            networks = client.networks.list()
            
            # 转换为响应模型
            network_summaries = []
            for network in networks:
                # 获取网络详情
                network_info = network.attrs
                
                # 计算已使用的容器数量
                containers_count = len(network_info.get('Containers', {}))
                
                # 提取子网和网关信息
                subnet = ""
                gateway = ""
                ipam_config = network_info.get('IPAM', {}).get('Config', [])
                if ipam_config:
                    subnet = ipam_config[0].get('Subnet', '')
                    gateway = ipam_config[0].get('Gateway', '')
                
                # 将字典格式的labels转换为列表格式
                labels_dict = network_info.get('Labels', {})
                labels_list = [f"{key}={value}" for key, value in labels_dict.items()]
                
                network_summary = NetworkSummary(
                    id=network.id,
                    name=network.name,
                    labels=labels_list,
                    driver=network_info.get('Driver', 'null'),
                    ipamDriver=network_info.get('IPAM', {}).get('Driver', 'default'),
                    subnet=subnet,
                    gateway=gateway,
                    createdAt=network_info.get('Created', ''),
                    attachable=network_info.get('Attachable', False)
                )
                network_summaries.append(network_summary)
            
            return NetworkListResponse(
                items=network_summaries,
                total=len(network_summaries)
            )
            
        except docker.errors.APIError as e:
            raise HTTPException(status_code=500, detail=f"Docker API错误: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取网络列表失败: {str(e)}")
        finally:
            # 关闭Docker客户端连接
            if 'client' in locals():
                client.close()
    
    @staticmethod
    async def create_network(db: AsyncSession, node_id: int, network_data: NetworkCreate) -> NetworkDetailResponse:
        """
在指定Docker节点上创建新的网络
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            network_data: 网络创建数据
            
        Returns:
            NetworkDetailResponse: 创建的网络详细信息
        """
        # 获取节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        
        try:
            # 获取Docker客户端
            client = await DockerNetworkService.get_docker_client(node)
            
            # 准备创建网络的参数
            network_kwargs = {
                'name': network_data.name,
                'driver': network_data.driver,
                'options': network_data.options or {},
                'internal': network_data.internal,
                'enable_ipv6': network_data.enableIPv6,
                'labels': network_data.labels or {},
                'check_duplicate': network_data.check_duplicate,
                'attachable': network_data.attachable
            }
            
            # 处理IPAM配置
            if network_data.ipam:
                network_kwargs['ipam'] = network_data.ipam
            
            # 创建网络
            network = client.networks.create(**network_kwargs)
            
            # 获取创建的网络详情
            network_info = network.attrs
            
            # 构建响应对象
            network_detail = NetworkDetailResponse(
                id=network.id,
                name=network.name,
                driver=network_info.get('Driver', ''),
                scope=network_info.get('Scope', ''),
                internal=network_info.get('Internal', False),
                enableIPv6=network_info.get('EnableIPv6', False),
                ipamDriver=network_info.get('IPAM', {}).get('Driver', ''),
                ipamConfig=network_info.get('IPAM', {}).get('Config', [])[0] if network_info.get('IPAM', {}).get('Config', []) else {},
                containers=network_info.get('Containers', {}),
                options=network_info.get('Options', {}),
                labels=network_info.get('Labels', {}),
                created=network_info.get('Created', '')
            )
            
            return network_detail
            
        except docker.errors.APIError as e:
            # 处理特定的Docker API错误
            error_message = str(e)
            if "network with name" in error_message and "already exists" in error_message:
                raise HTTPException(status_code=409, detail=f"网络名称已存在: {network_data.name}")
            elif "invalid name" in error_message.lower():
                raise HTTPException(status_code=400, detail=f"无效的网络名称: {error_message}")
            else:
                raise HTTPException(status_code=500, detail=f"创建网络失败: {error_message}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"创建网络失败: {str(e)}")
        finally:
            # 关闭Docker客户端连接
            if 'client' in locals():
                client.close()
    
    @staticmethod
    async def delete_network(db: AsyncSession, node_id: int, network_id: str, force: bool = False) -> NetworkOperationResponse:
        """
删除指定Docker节点上的指定网络
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            network_id: 网络ID
            force: 是否强制删除
            
        Returns:
            NetworkOperationResponse: 网络操作响应
        """
        # 获取节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        
        try:
            # 获取Docker客户端
            client = await DockerNetworkService.get_docker_client(node)
            
            # 获取网络对象
            network = client.networks.get(network_id)
            network_info = network.attrs
            network_name = network.name
            
            # 禁止删除Docker自带的网络
            protected_networks = ['none', 'host', 'bridge']
            if network_name in protected_networks:
                raise HTTPException(status_code=403, detail=f"禁止删除Docker自带网络: {network_name}")
            
            # 检查网络是否被使用
            containers_count = len(network_info.get('Containers', {}))
            if containers_count > 0 and not force:
                raise HTTPException(
                    status_code=400, 
                    detail=f"网络正在被{containers_count}个容器使用，请先停止或移除使用该网络的容器，或使用force参数强制删除"
                )
            
            # 删除网络
            network.remove()
            
            return NetworkOperationResponse(
                network_id=network_id,
                network_name=network_name,
                operation="delete",
                success=True,
                message="网络删除成功"
            )
            
        except docker.errors.APIError as e:
            # 处理特定的Docker API错误
            error_message = str(e)
            if "No such network" in error_message:
                raise HTTPException(status_code=404, detail="网络不存在")
            elif "network is in use" in error_message.lower():
                raise HTTPException(status_code=400, detail=f"网络正在使用中: {error_message}. 使用force参数强制删除")
            else:
                raise HTTPException(status_code=500, detail=f"Docker API错误: {error_message}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"删除网络失败: {str(e)}")
        finally:
            # 关闭Docker客户端连接
            if 'client' in locals():
                client.close()
    
    @staticmethod
    async def prune_networks(db: AsyncSession, node_id: int) -> Dict[str, Any]:
        """
        清理指定Docker节点上所有未使用的网络
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            
        Returns:
            Dict[str, Any]: 清理结果，包含删除的网络列表和相关信息
        """
        # 获取节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        
        try:
            # 获取Docker客户端
            client = await DockerNetworkService.get_docker_client(node)
            
            # 定义同步函数来清理未使用的网络
            def prune_networks_sync():
                # 使用Docker API的networks.prune()方法清理未使用的网络
                # 注意：Docker的networks.prune()不会删除默认的bridge、host和none网络
                result = client.networks.prune()
                return result
            
            # 异步执行清理操作
            loop = asyncio.get_running_loop()
            prune_result = await loop.run_in_executor(None, prune_networks_sync)
            
            # 构建返回结果
            # 确保prune_result不为None
            if prune_result is None:
                deleted_networks = []
            else:
                deleted_networks = prune_result.get('NetworksDeleted', [])
            
            # 再次确保deleted_networks是列表类型
            if deleted_networks is None:
                deleted_networks = []
            
            return {
                "deleted_networks": deleted_networks,
                "total_deleted": len(deleted_networks),
                "message": f"成功清理了{len(deleted_networks)}个未使用的网络"
            }
            
        except docker.errors.APIError as e:
            # 处理特定的Docker API错误
            error_message = str(e)
            raise HTTPException(status_code=500, detail=f"清理未使用网络失败: {error_message}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"清理未使用网络失败: {str(e)}")
        finally:
            # 关闭Docker客户端连接
            if 'client' in locals():
                client.close()
    
    @staticmethod
    async def get_network_options(db: AsyncSession, node_id: int) -> NetworkOptionListResponse:
        """
        获取指定Docker节点上的网络选项列表
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            
        Returns:
            NetworkOptionListResponse: 网络选项列表响应
        """
        # 获取节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        
        try:
            # 获取Docker客户端
            client = await DockerNetworkService.get_docker_client(node)
            
            # 获取网络列表
            networks = client.networks.list()
            
            # 提取网络名称并创建NetworkOption列表
            network_options = []
            for network in networks:
                network_option = NetworkOption(option=network.name)
                network_options.append(network_option)
            
            # 创建并返回响应对象
            return NetworkOptionListResponse(data=network_options)
            
        except docker.errors.APIError as e:
            # 处理特定的Docker API错误
            error_message = str(e)
            raise HTTPException(status_code=500, detail=f"获取网络选项列表失败: {error_message}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取网络选项列表失败: {str(e)}")
        finally:
            # 关闭Docker客户端连接
            if 'client' in locals():
                client.close()