import os
import asyncio
import logging
import yaml
import subprocess
import docker
import shutil
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

# 从service.py导入create_docker_client_with_tls辅助函数
from app.container.service import create_docker_client_with_tls

# 查找docker命令的完整路径
def get_docker_command() -> str:
    """获取docker命令的完整路径
    
    首先尝试通过shutil.which查找系统PATH中的docker命令，
    如果找不到，则尝试常见的docker安装路径。
    
    Returns:
        str: docker命令的完整路径或'docker'
    """
    # 常见的docker可执行文件路径
    common_paths = [
        '/usr/bin/docker',
        '/usr/local/bin/docker',
        '/bin/docker',
        '/snap/bin/docker'
    ]
    
    # 首先尝试通过shutil.which查找
    docker_path = shutil.which('docker')
    if docker_path:
        return docker_path
    
    # 如果找不到，尝试常见路径
    for path in common_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    
    # 如果都找不到，返回'docker'作为后备
    return 'docker'

from app.container.models import DockerNode
from app.container.schemas import ComposeProjectSummary, ComposeProjectList, ContainerSummary, ContainerListResponse, SimplifiedContainerItem, SimplifiedContainerListResponse, ComposeContainerLog, ComposeProjectLogsResponse

logger = logging.getLogger(__name__)

# 简单的内存缓存实现
_cache = {}
_CACHE_TTL = 10  # 缓存有效期10秒


class DockerComposeService:
    """Docker Compose服务类"""
    
    @staticmethod
    async def get_compose_projects(db: AsyncSession, node_id: int, refresh: bool = False) -> ComposeProjectList:
        """
        获取指定Docker节点上的Compose项目列表
        结合dpanel的实现方式：通过容器标签识别和文件系统扫描相结合
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            refresh: 是否强制刷新数据，绕过缓存
            
        Returns:
            ComposeProjectList: Compose项目列表响应
        """
        # 尝试从缓存获取（如果没有强制刷新）
        cache_key = f"compose_projects_{node_id}"
        if not refresh and cache_key in _cache:
            cached_data, timestamp = _cache[cache_key]
            # 检查缓存是否过期
            if datetime.now() - timestamp < timedelta(seconds=_CACHE_TTL):
                logger.info(f"Return the list of Compose projects from the cache, node ID: {node_id}")
                return cached_data
            else:
                # 删除过期缓存
                del _cache[cache_key]
        
        # 获取节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise ValueError(f"节点ID {node_id} 不存在")
        
        try:
            # 1. 通过Docker API获取所有带有compose标签的容器，识别所有项目
            # 2. 扫描compose_path路径下的文件
            # 3. 合并两种方式的结果，避免重复
            
            # 创建一个空集合用于存储已处理的项目名称，避免重复
            processed_projects = set()
            all_projects = []
            
            # 方法1: 通过Docker API获取所有带有compose标签的容器，识别项目
            label_projects = await DockerComposeService._get_projects_from_container_labels(node)
            for project in label_projects:
                if project['name'] not in processed_projects:
                    processed_projects.add(project['name'])
                    all_projects.append(project)
            
            # 方法2: 扫描compose_path路径获取项目（如果设置了路径）
            compose_path = getattr(node, 'compose_path', None)
            if compose_path:
                path_projects = await DockerComposeService._scan_compose_projects(compose_path, node)
                for project in path_projects:
                    # 检查是否已经通过标签识别到该项目
                    if project['name'] not in processed_projects:
                        processed_projects.add(project['name'])
                        all_projects.append(project)
            
            # 转换为响应模型
            project_items = []
            for project in all_projects:
                project_items.append(ComposeProjectSummary(
                    name=project['name'],
                    path=project['path'],
                    compose_file=project['compose_file'],
                    services=project['services'],
                    status=project['status'],
                    created_at=project['created_at'],
                    updated_at=project['updated_at'],
                    containerCount=project.get('containerCount', 0),
                    runningCount=project.get('runningCount', 0)
                ))
            
            result = ComposeProjectList(
                items=project_items,
                total=len(project_items)
            )
            
            # 缓存结果
            _cache[cache_key] = (result, datetime.now())
            return result
            
        except Exception as e:
            logger.error(f"获取Compose项目列表失败: {str(e)}")
            raise
    
    @staticmethod
    async def _get_projects_from_container_labels(node: DockerNode) -> List[Dict[str, Any]]:
        """
        通过Docker API获取所有带有compose标签的容器，识别Compose项目
        类似dpanel的实现方式，基于com.docker.compose.project标签
        
        Args:
            node: Docker节点对象
            
        Returns:
            List[Dict]: 识别到的项目列表
        """
        projects = []
        project_containers = {}
        
        try:
            # 获取Docker客户端连接配置
            config = node.connection_config
            loop = asyncio.get_event_loop()
            
            # 定义同步函数来获取所有容器
            def get_all_containers_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        client, _ = create_docker_client_with_tls(config)
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    
                    # 获取所有容器（包括已停止的）
                    return client.containers.list(all=True)
                except Exception as e:
                    logger.error(f"获取容器列表失败: {str(e)}")
                    return []
            
            # 异步执行获取所有容器
            containers = await loop.run_in_executor(None, get_all_containers_sync)
            
            # 按项目名称分组容器
            for container in containers:
                # 检查是否有compose项目标签
                if 'com.docker.compose.project' in container.labels:
                    project_name = container.labels['com.docker.compose.project']
                    if project_name not in project_containers:
                        project_containers[project_name] = []
                    project_containers[project_name].append(container)
            
            # 为每个项目构建项目信息
            for project_name, containers in project_containers.items():
                # 收集项目信息
                services = set()
                running_count = 0
                compose_files = set()
                
                for container in containers:
                    # 收集服务名称
                    service_name = container.labels.get('com.docker.compose.service', '')
                    if service_name:
                        services.add(service_name)
                    
                    # 检查容器状态
                    if container.status == 'running':
                        running_count += 1
                    
                    # 尝试获取compose文件路径
                    compose_file = container.labels.get('com.docker.compose.project.working_dir', '')
                    if compose_file:
                        # 尝试找到docker-compose文件
                        potential_files = [
                            os.path.join(compose_file, 'docker-compose.yml'),
                            os.path.join(compose_file, 'docker-compose.yaml')
                        ]
                        for file_path in potential_files:
                            compose_files.add(file_path)
                
                # 确定项目路径和compose文件
                project_path = ''
                compose_file = ''
                
                # 首先尝试从容器标签中获取的compose文件
                found_valid_compose = False
                if compose_files:
                    for file_path in compose_files:
                        if os.path.exists(file_path):
                            compose_file = file_path
                            project_path = os.path.dirname(compose_file)
                            found_valid_compose = True
                            break
                
                # 如果从容器标签中没有找到有效的compose文件，尝试从节点配置的compose_path中查找
                if not found_valid_compose and hasattr(node, 'compose_path') and node.compose_path:
                    # 尝试在compose_path下查找与项目名称匹配的目录
                    potential_project_path = os.path.join(node.compose_path, project_name)
                    if os.path.exists(potential_project_path) and os.path.isdir(potential_project_path):
                        # 尝试查找docker-compose文件
                        potential_compose_files = [
                            os.path.join(potential_project_path, 'docker-compose.yml'),
                            os.path.join(potential_project_path, 'docker-compose.yaml')
                        ]
                        for file_path in potential_compose_files:
                            if os.path.exists(file_path):
                                compose_file = file_path
                                project_path = potential_project_path
                                found_valid_compose = True
                                break
                
                # 如果仍然没有找到有效的compose文件
                if not found_valid_compose:
                    if compose_files:
                        # 至少有一个潜在的compose文件路径，但不存在
                        first_compose_file = list(compose_files)[0]
                        compose_file = "notfound"
                        project_path = os.path.dirname(first_compose_file)
                    else:
                        # 根本没有找到compose文件路径
                        project_path = f"/external-compose/{project_name}"
                        compose_file = "notfound"
                
                # 确定项目状态
                container_count = len(containers)
                if running_count > 0:
                    if running_count == container_count:
                        status = 'running'
                    else:
                        status = 'partial'
                else:
                    status = 'stopped'
                
                # 创建项目信息
                project = {
                    'name': project_name,
                    'path': project_path,
                    'compose_file': compose_file,
                    'services': list(services),
                    'status': status,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    'containerCount': container_count,
                    'runningCount': running_count
                }
                
                projects.append(project)
            
            return projects
            
        except Exception as e:
            logger.error(f"通过容器标签识别Compose项目失败: {str(e)}")
            return []
    
    @staticmethod
    async def _scan_compose_projects(compose_path: str, node: DockerNode) -> List[Dict[str, Any]]:
        """
        扫描指定路径下的Docker Compose项目
        
        Args:
            compose_path: compose文件的根路径
            node: Docker节点对象，用于获取远程连接信息
            
        Returns:
            List[Dict]: Compose项目信息列表
        """
        projects = []
        project_tasks = []
        
        # 使用线程池执行同步的文件系统操作
        loop = asyncio.get_event_loop()
        
        try:
            # 检查路径是否存在
            exists = await loop.run_in_executor(None, os.path.exists, compose_path)
            if not exists:
                logger.warning(f"Compose路径 {compose_path} 不存在")
                return []
            
            # 检查是否是目录
            is_dir = await loop.run_in_executor(None, os.path.isdir, compose_path)
            if not is_dir:
                logger.warning(f"Compose路径 {compose_path} 不是一个目录")
                return []
            
            # 列出目录下的所有子目录
            subdirs = await loop.run_in_executor(None, os.listdir, compose_path)
            
            for subdir in subdirs:
                project_path = os.path.join(compose_path, subdir)
                
                # 检查是否是目录
                is_project_dir = await loop.run_in_executor(None, os.path.isdir, project_path)
                if not is_project_dir:
                    continue
                
                # 查找docker-compose文件
                compose_files = []
                try:
                    files = await loop.run_in_executor(None, os.listdir, project_path)
                    for file in files:
                        if file.startswith('docker-compose') and (file.endswith('.yml') or file.endswith('.yaml')):
                            compose_files.append(os.path.join(project_path, file))
                except Exception as e:
                    logger.error(f"扫描项目目录 {project_path} 失败: {str(e)}")
                    continue
                
                # 如果没有compose文件，跳过
                if not compose_files:
                    continue
                
                # 对于每个compose文件，创建一个项目
                for compose_file in compose_files:
                    # 获取文件的创建和修改时间
                    stat_info = await loop.run_in_executor(None, os.stat, compose_file)
                    created_at = datetime.fromtimestamp(stat_info.st_ctime).isoformat()
                    updated_at = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                    
                    # 从文件名提取项目名称（去掉docker-compose前缀和扩展名）
                    file_name = os.path.basename(compose_file)
                    if file_name == 'docker-compose.yml' or file_name == 'docker-compose.yaml':
                        project_name = subdir
                    else:
                        # 处理docker-compose.override.yml或其他自定义名称
                        project_name = f"{subdir}-{file_name.replace('docker-compose.', '').replace('.yml', '').replace('.yaml', '')}"
                    
                    # 解析docker-compose文件获取服务列表和容器数量
                    services = []
                    container_count = 0
                    
                    try:
                        # 异步读取并解析compose文件
                        compose_content = await loop.run_in_executor(None, DockerComposeService._read_compose_file, compose_file)
                        if compose_content and 'services' in compose_content:
                            services = list(compose_content['services'].keys())
                            container_count = len(services)
                            # 检查是否有服务配置了多个容器实例
                            for service_name, service_config in compose_content['services'].items():
                                if isinstance(service_config, dict) and 'deploy' in service_config:
                                    replicas = service_config['deploy'].get('replicas', 1)
                                    if isinstance(replicas, int) and replicas > 1:
                                        # 对于多副本服务，更新容器总数
                                        container_count += (replicas - 1)
                    except Exception as e:
                        logger.error(f"解析compose文件 {compose_file} 失败: {str(e)}")
                        # 如果解析失败，保持默认值
                    
                    # 创建项目基础信息
                    project = {
                        'name': project_name,
                        'path': project_path,
                        'compose_file': compose_file,
                        'services': services,
                        'status': 'stopped',
                        'created_at': created_at,
                        'updated_at': updated_at,
                        'containerCount': container_count,
                        'runningCount': 0
                    }
                    projects.append(project)
                    
                    # 创建检查容器状态的任务
                    project_tasks.append(DockerComposeService._check_project_status(project, node))
            
            # 并行执行所有项目的状态检查
            if project_tasks:
                await asyncio.gather(*project_tasks, return_exceptions=True)
            
            return projects
            
        except Exception as e:
            logger.error(f"扫描Compose项目失败: {str(e)}")
            raise
    
    @staticmethod
    def _read_compose_file(compose_file_path: str) -> Dict[str, Any]:
        """
        读取并解析docker-compose文件
        
        Args:
            compose_file_path: compose文件路径
            
        Returns:
            Dict: 解析后的compose文件内容
        """
        if not os.path.exists(compose_file_path):
            return {}
            
        with open(compose_file_path, 'r', encoding='utf-8') as f:
            try:
                return yaml.safe_load(f)
            except yaml.YAMLError:
                # 如果YAML解析失败，尝试使用docker-compose config验证
                try:
                    result = subprocess.run(
                        ['docker-compose', '-f', compose_file_path, 'config'],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if result.returncode == 0:
                        return yaml.safe_load(result.stdout)
                except Exception:
                    pass
                return {}
    
    @staticmethod
    async def _check_project_status(project: Dict[str, Any], node: DockerNode):
        """
        异步检查单个项目的容器状态
        
        Args:
            project: 项目字典（将被修改以包含状态信息）
            node: Docker节点对象
        """
        loop = asyncio.get_event_loop()
        status_checked = False
        
        try:
            # 使用超时执行容器状态检查
            running_containers = await asyncio.wait_for(
                loop.run_in_executor(
                    None, 
                    DockerComposeService._check_running_containers,
                    project['path'], 
                    project['compose_file'], 
                    node
                ),
                timeout=2  # 减少超时时间到2秒
            )
            
            running_count = len(running_containers)
            container_count = project['containerCount']
            
            # 更新项目状态
            if running_count > 0:
                if running_count == container_count:
                    project['status'] = 'running'
                else:
                    project['status'] = 'partial'
            else:
                project['status'] = 'stopped'
            
            project['runningCount'] = running_count
            status_checked = True
            
        except asyncio.TimeoutError:
            logger.warning(f"检查项目 {project['name']} 状态超时，尝试快速状态检查")
            # 超时情况下尝试更快速的状态检查方法
            try:
                # 使用Docker API直接检查容器状态（更快）
                fast_running_count = await DockerComposeService._fast_check_running_containers(project, node)
                if fast_running_count is not None:
                    container_count = project['containerCount']
                    if fast_running_count > 0:
                        if fast_running_count == container_count:
                            project['status'] = 'running'
                        else:
                            project['status'] = 'partial'
                    else:
                        project['status'] = 'stopped'
                    project['runningCount'] = fast_running_count
                    status_checked = True
            except Exception as inner_e:
                logger.error(f"快速检查项目 {project['name']} 状态失败: {str(inner_e)}")
        
        except Exception as e:
            logger.error(f"检查项目 {project['name']} 状态失败: {str(e)}")
            # 出错情况下尝试快速状态检查作为备选
            try:
                fast_running_count = await DockerComposeService._fast_check_running_containers(project, node)
                if fast_running_count is not None:
                    container_count = project['containerCount']
                    if fast_running_count > 0:
                        if fast_running_count == container_count:
                            project['status'] = 'running'
                        else:
                            project['status'] = 'partial'
                    else:
                        project['status'] = 'stopped'
                    project['runningCount'] = fast_running_count
                    status_checked = True
            except Exception:
                pass
        
        # 如果所有状态检查都失败，尝试降低状态可信度
        if not status_checked and 'status' in project and project['status'] == 'running':
            # 如果之前状态是running但无法验证，将其降级为unknown
            project['status'] = 'unknown'
            logger.warning(f"项目 {project['name']} 状态未知，降级为unknown状态")
    
    @staticmethod
    async def _fast_check_running_containers(project: Dict[str, Any], node: DockerNode) -> int:
        """
        快速检查项目中运行的容器数量
        使用Docker API直接查询，比执行shell命令更快
        
        Args:
            project: 项目字典
            node: Docker节点对象
            
        Returns:
            int: 运行中的容器数量，如果检查失败返回None
        """
        try:
            config = node.connection_config
            loop = asyncio.get_event_loop()
            
            def check_containers():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        client, _ = create_docker_client_with_tls(config)
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    
                    # 只查询运行中的容器，使用标签过滤
                    running_containers = client.containers.list(
                        filters={
                            'label': f'com.docker.compose.project={project["name"]}',
                            'status': 'running'
                        }
                    )
                    return len(running_containers)
                except Exception:
                    return None
            
            return await loop.run_in_executor(None, check_containers)
        except Exception:
            return None
    
    @staticmethod
    def _check_running_containers(project_path: str, compose_file: str, node: DockerNode) -> List[str]:
        """
        检查正在运行的容器（支持远程连接）
        
        Args:
            project_path: 项目路径
            compose_file: compose文件路径
            node: Docker节点对象，用于获取远程连接信息
            
        Returns:
            List[str]: 运行中的容器名称列表
        """
        # 构建远程连接参数
        # 使用docker命令的完整路径
        docker_cmd = [get_docker_command()]
        
        # 如果节点配置了远程连接信息，添加-H参数
        # 获取节点属性值
        endpoint_type = getattr(node, 'endpoint_type', '')
        endpoint_url = getattr(node, 'endpoint_url', '')
        
        if endpoint_type == 'tcp' and endpoint_url:
            # 构建远程连接URL
            if endpoint_url.startswith('http://') or endpoint_url.startswith('https://'):
                remote_url = endpoint_url
            else:
                # 假设endpoint_url格式为 host:port
                remote_url = f"tcp://{endpoint_url}"
            docker_cmd.extend(['-H', remote_url])
        
        # 尝试多种方法获取运行中的容器，但优化方法顺序和执行
        methods = [
            "docker_compose_ps_direct",  # 优先使用直接查询运行中服务的命令
            "docker_ps_with_label",      # 其次使用docker ps过滤标签（通常更快）
            "docker_compose_ps_all"      # 最后使用完整的ps命令（更兼容但较慢）
        ]
        
        for method in methods:
            try:
                # 添加超时控制，避免单个命令阻塞过长时间
                if method == "docker_compose_ps_direct":
                    # 直接使用docker compose ps --status running命令（最快）
                    cmd = docker_cmd + ['compose', '-f', compose_file, 'ps', '--services', '--status', 'running']
                    result = subprocess.run(
                        cmd,
                        cwd=project_path,
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=2  # 单个命令超时控制
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        running_services = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                        return running_services
                
                elif method == "docker_ps_with_label":
                    # 使用docker ps过滤compose项目标签
                    project_name = os.path.basename(project_path)
                    docker_ps_cmd = docker_cmd + ['ps', '--filter', f'label=com.docker.compose.project={project_name}', '--format', '{{.Names}}']
                    result = subprocess.run(
                        docker_ps_cmd,
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=2  # 单个命令超时控制
                    )
                    
                    if result.returncode == 0:
                        container_names = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                        # 从容器名称中提取服务名（通常格式为project_service_1）
                        running_services = []
                        for name in container_names:
                            parts = name.split('_')
                            if len(parts) > 1:
                                # 假设服务名是第二个部分
                                service_name = parts[1]
                                if service_name not in running_services:
                                    running_services.append(service_name)
                        
                        if running_services:
                            return running_services
                
                elif method == "docker_compose_ps_all":
                    # 方法3: 使用docker compose ps，然后解析输出判断状态
                    cmd = docker_cmd + ['compose', '-f', compose_file, 'ps']
                    result = subprocess.run(
                        cmd,
                        cwd=project_path,
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=2  # 单个命令超时控制
                    )
                    
                    if result.returncode == 0:
                        running_services = []
                        lines = result.stdout.split('\n')
                        # 跳过标题行
                        for line in lines[2:]:
                            parts = line.strip().split()
                            if len(parts) >= 5:
                                # 状态通常在倒数第二个字段
                                status = parts[-2]
                                # 服务名通常在倒数第四个字段
                                service = parts[-4]
                                # 检查状态是否包含Up
                                if 'Up' in status:
                                    running_services.append(service)
                        
                        if running_services:
                            return running_services
            
            except subprocess.TimeoutExpired:
                logger.warning(f"Using method {method} check container status timeout")
                # 继续尝试下一个方法
            except Exception as e:
                logger.error(f"Using method {method} check container status error: {str(e)}")
                # 继续尝试下一个方法
        
        return []

    @staticmethod
    async def get_compose_project_containers(db: AsyncSession, node_id: int, project_name: str) -> List[SimplifiedContainerItem]:
        """
        获取指定Compose项目的容器列表
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            project_name: Compose项目名称
            
        Returns:
            List[SimplifiedContainerItem]: 简化版容器信息列表
        """
        # 获取节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise ValueError(f"节点ID {node_id} 不存在")
        
        try:
            # 获取Docker客户端连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_event_loop()
            
            # 定义同步函数来获取容器列表
            def get_project_containers_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        client, _ = create_docker_client_with_tls(config)
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    
                    # 使用标签过滤获取指定Compose项目的容器
                    # 根据docker-compose的标签规范，项目容器会有com.docker.compose.project标签
                    containers = client.containers.list(all=True, filters={
                        'label': f'com.docker.compose.project={project_name}'
                    })
                    
                    # 转换为响应格式
                    container_list = []
                    for container in containers:
                        # 构建端口映射字符串列表
                        ports = []
                        if container.attrs.get('NetworkSettings', {}).get('Ports'):
                            for private_port, mappings in container.attrs['NetworkSettings']['Ports'].items():
                                if mappings:
                                    for mapping in mappings:
                                        host_ip = mapping.get('HostIp', '')
                                        host_port = mapping.get('HostPort')
                                        if host_port:
                                            # 确保IP地址格式正确，避免空IP
                                            display_ip = host_ip if host_ip else '0.0.0.0'
                                            # 提取端口号和协议
                                            port_parts = private_port.split('/')
                                            private_port_num = port_parts[0]
                                            protocol = port_parts[1] if len(port_parts) > 1 else 'tcp'
                                            # 格式化为: IP:host_port->private_port/protocol
                                            port_str = f"{display_ip}:{host_port}->{private_port_num}/{protocol}"
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
                            created_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
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
                        
                        # 提取镜像名称
                        image_name = ""
                        if container.image.tags:
                            image_name = container.image.tags[0]
                        else:
                            image_name = container.image.id[:12]
                        
                        # 获取服务名称（从标签中提取）
                        service_name = container.labels.get('com.docker.compose.service', '')
                        
                        container_summary = SimplifiedContainerItem(
                            name=container_name,
                            imageName=image_name,
                            createTime=create_time_str,
                            state=container.attrs.get('State', {}).get('Status', ''),
                            network=network_ips,
                            ports=ports
                        )
                        container_list.append(container_summary)
                    
                    return container_list
                except Exception as e:
                    raise Exception(f"获取Compose项目容器列表失败: {str(e)}")
            
            # 异步执行获取容器列表
            container_list = await loop.run_in_executor(None, get_project_containers_sync)
            return container_list
            
        except ValueError:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取Compose项目容器列表时发生错误: {str(e)}")

    @staticmethod
    async def get_compose_project_logs(db: AsyncSession, node_id: int, project_name: str, lines: int = 100) -> ComposeProjectLogsResponse:
        """
        获取指定Compose项目的日志
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            project_name: Compose项目名称
            lines: 每个容器返回的日志行数
            
        Returns:
            ComposeProjectLogsResponse: Compose项目日志响应
        """
        # 获取节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise ValueError(f"节点ID {node_id} 不存在")
        
        try:
            # 获取Docker客户端连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_event_loop()
            
            # 定义同步函数来获取项目日志
            def get_project_logs_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 使用辅助函数创建带TLS的Docker客户端
                        client, _ = create_docker_client_with_tls(config)
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    
                    # 使用标签过滤获取指定Compose项目的容器
                    containers = client.containers.list(all=True, filters={
                        'label': f'com.docker.compose.project={project_name}'
                    })
                    
                    # 收集每个容器的日志
                    container_logs = []
                    for container in containers:
                        # 提取容器名称
                        container_name = ""
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
                            container_name = container.id[:12]
                        
                        # 获取服务名称
                        service_name = container.labels.get('com.docker.compose.service', '')
                        
                        # 获取容器日志 - 使用docker compose logs命令获取原始格式
                        try:
                            # 构建docker compose logs命令
                            compose_file_path = os.path.join(self.docker_compose_path, project_name, 'docker-compose.yml')
                            # 使用subprocess直接执行docker compose logs命令获取原始格式输出
                            import subprocess
                            # 移除--timestamps参数，让docker compose logs使用默认的容器名称前缀格式
                            cmd = [
                                'docker', 'compose', '-f', compose_file_path,
                                'logs', '--tail', str(lines), container_name
                            ]
                            # 执行命令并捕获输出
                            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                            log_str = result.stdout
                            # 如果没有输出，设置为空字符串
                            if not log_str:
                                log_str = ''
                        except Exception as e:
                            # 出错时使用SDK作为备选方案，并手动添加容器名称前缀
                            try:
                                logs = container.logs(
                                    stdout=True,
                                    stderr=True,
                                    tail=lines,
                                    timestamps=False  # 不使用SDK的时间戳，保持与docker compose logs一致
                                )
                                log_str = logs.decode('utf-8', errors='replace')
                                # 手动添加容器名称前缀，格式为：容器名称 | 日志内容
                                formatted_logs = []
                                for line in log_str.splitlines():
                                    formatted_logs.append(f"{container_name}  | {line}")
                                log_str = '\n'.join(formatted_logs)
                            except Exception as inner_e:
                                log_str = f"无法获取日志: {str(inner_e)}"
                        
                        # 创建日志条目
                        log_entry = ComposeContainerLog(
                            container_name=container_name,
                            service_name=service_name,
                            logs=log_str,
                            timestamp=datetime.now()
                        )
                        container_logs.append(log_entry)
                    
                    # 创建响应对象
                    return ComposeProjectLogsResponse(
                        project_name=project_name,
                        logs=container_logs,
                        total=len(container_logs)
                    )
                    
                except Exception as e:
                    raise Exception(f"获取Compose项目日志失败: {str(e)}")
            
            # 异步执行获取日志
            logs_response = await loop.run_in_executor(None, get_project_logs_sync)
            return logs_response
            
        except ValueError:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取Compose项目日志时发生错误: {str(e)}")
    
    @staticmethod
    async def start_compose_project(db: AsyncSession, node_id: int, project_name: str) -> Dict[str, Any]:
        """
        启动指定的Docker Compose项目
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            project_name: Compose项目名称
            
        Returns:
            Dict[str, Any]: 启动结果信息
        """
        # 获取节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise ValueError(f"节点ID {node_id} 不存在")
        
        # 首先获取项目信息，以验证项目是否存在并获取compose文件路径
        projects_list = await DockerComposeService.get_compose_projects(db, node_id, refresh=True)
        
        # 查找指定的项目
        project = None
        for p in projects_list.items:
            if p.name == project_name:
                project = p
                break
        
        if not project:
            raise ValueError(f"Compose项目 {project_name} 不存在")
        
        if project.compose_file == "notfound":
            raise ValueError(f"Compose项目 {project_name} 的compose文件不存在")
        
        # 检查compose文件是否存在
        if not os.path.exists(project.compose_file):
            raise ValueError(f"Compose文件 {project.compose_file} 不存在")
        
        # 准备启动项目
        loop = asyncio.get_event_loop()
        
        # 定义同步函数来启动项目
        def start_project_sync():
            try:
                # 构建docker compose up命令
                # 先创建基础命令，不包含compose子命令
                # 使用docker命令的完整路径
                cmd = [get_docker_command()]
                
                # 如果是远程节点，添加-H参数和TLS配置
                endpoint_type = getattr(node, 'endpoint_type', '')
                endpoint_url = getattr(node, 'endpoint_url', '')
                use_tls = getattr(node, 'use_tls', False)
                ca_cert = getattr(node, 'ca_cert', '')
                client_cert = getattr(node, 'client_cert', '')
                client_key = getattr(node, 'client_key', '')
                
                if endpoint_type == 'tcp' and endpoint_url:
                    # 构建远程连接URL，确保格式正确
                    if endpoint_url.startswith('tcp://'):
                        remote_url = endpoint_url
                    elif endpoint_url.startswith('http://') or endpoint_url.startswith('https://'):
                        # 如果已经有协议前缀，只使用tcp://
                        remote_url = f"tcp://{endpoint_url.split('://')[1]}"
                    else:
                        remote_url = f"tcp://{endpoint_url}"
                    
                    # 添加-H参数
                    cmd.extend(['-H', remote_url])
                    
                    # 如果启用了TLS，添加TLS配置参数（在compose子命令之前）
                    if use_tls:
                        if ca_cert:
                            cmd.extend(['--tlsverify', '--tlscacert', ca_cert])
                        if client_cert:
                            cmd.extend(['--tlscert', client_cert])
                        if client_key:
                            cmd.extend(['--tlskey', client_key])
                
                # 添加compose子命令和参数
                cmd.extend(['compose', '-f', project.compose_file, 'up', '-d'])
                
                # 记录执行的命令
                # logger.info(f"执行Docker Compose启动命令: {' '.join(cmd)}, 工作目录: {project.path}")
                
                # 执行启动命令
                result = subprocess.run(
                    cmd,
                    cwd=project.path,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=300  # 延长超时时间至120秒，以适应大型Compose项目
                )
                
                logger.info(f"Compose Project {project_name} started successfully")
                
                # 返回成功信息
                return {
                    "status": "success",
                    "message": f"Compose Project {project_name} started successfully",
                    "project_name": project_name,
                    "output": result.stdout
                }
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Compose Project {project_name} start failed: {e.stderr}")
                raise Exception(f"启动失败: {e.stderr}")
            except subprocess.TimeoutExpired:
                logger.error(f"Compose Project {project_name} start timeout")
                raise Exception("启动超时，请检查项目配置")
            except Exception as e:
                logger.error(f"Compose Project {project_name} start error: {str(e)}")
                raise
        
        try:
            # 异步执行启动命令
            result = await loop.run_in_executor(None, start_project_sync)
            
            # 清除缓存，确保下次获取时能看到最新状态
            cache_key = f"compose_projects_{node_id}"
            if cache_key in _cache:
                del _cache[cache_key]
            
            return result
            
        except ValueError:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"启动Compose项目时发生错误: {str(e)}")
    
    @staticmethod
    async def create_compose_project(db: AsyncSession, node_id: int, project_name: str, compose_content: str, 
                                  start_on_create: bool = False, base_path: str = None, env_content: str = None) -> Dict[str, Any]:
        """
        创建Docker Compose项目
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            project_name: Compose项目名称
            compose_content: Compose文件内容
            start_on_create: 创建后是否自动启动
            base_path: 项目基础路径，默认为None（使用默认路径）
            env_content: .env文件内容，默认为None（不创建.env文件）
            
        Returns:
            Dict[str, Any]: 创建结果信息
        """
        # 获取节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise ValueError(f"节点ID {node_id} 不存在")
        
        # 确定项目路径
        if base_path is None:
            # 优先使用节点配置的compose_path
            if hasattr(node, 'compose_path') and node.compose_path:
                base_path = node.compose_path
            else:
                # 使用系统默认路径
                base_path = os.path.join('/opt', 'docker', 'compose')
        
        # 创建项目完整路径
        project_path = os.path.join(base_path, project_name)
        compose_file_path = os.path.join(project_path, 'docker-compose.yml')
        
        # 检查项目是否已存在
        if os.path.exists(project_path):
            if os.path.exists(compose_file_path):
                raise ValueError(f"Compose项目 {project_name} 已存在")
        
        # 准备创建项目
        loop = asyncio.get_event_loop()
        
        # 定义同步函数来创建项目
        def create_project_sync():
            try:
                # 创建项目目录
                os.makedirs(project_path, exist_ok=True)
                logger.info(f"Create Compose project directory: {project_path}")
                
                # 写入compose文件
                with open(compose_file_path, 'w', encoding='utf-8') as f:
                    f.write(compose_content)
                logger.info(f"Create Compose file: {compose_file_path}")
                
                # 如果提供了.env文件内容，创建.env文件
                env_file_path = None
                if env_content:
                    env_file_path = os.path.join(project_path, '.env')
                    with open(env_file_path, 'w', encoding='utf-8') as f:
                        f.write(env_content)
                    logger.info(f"Create .env file: {env_file_path}")
                
                # 如果需要自动启动
                start_result = None
                if start_on_create:
                    try:
                        # 构建docker compose up命令
                        cmd = [get_docker_command()]
                        cmd.extend(['compose', '-f', compose_file_path, 'up', '-d'])
                        
                        # 执行启动命令
                        result = subprocess.run(
                            cmd,
                            cwd=project_path,
                            capture_output=True,
                            text=True,
                            check=True,
                            timeout=60  # 启动可能需要更长时间
                        )
                        start_result = {
                            "status": "success",
                            "output": result.stdout
                        }
                        logger.info(f"Compose项目 {project_name} 自动启动成功")
                    except Exception as start_e:
                        logger.error(f"Compose项目 {project_name} 自动启动失败: {str(start_e)}")
                        start_result = {
                            "status": "error",
                            "error": str(start_e)
                        }
                
                # 返回成功信息
                result = {
                    "status": "success",
                    "message": f"Compose项目 {project_name} 创建成功",
                    "project_name": project_name,
                    "project_path": project_path,
                    "compose_file": compose_file_path
                }
                
                # 如果创建了.env文件，添加到结果中
                if env_file_path:
                    result["env_file"] = env_file_path
                
                if start_result:
                    result["start_result"] = start_result
                
                return result
                
            except Exception as e:
                # 如果出错，尝试清理已创建的文件和目录
                if os.path.exists(compose_file_path):
                    try:
                        os.remove(compose_file_path)
                        if not os.listdir(project_path):
                            os.rmdir(project_path)
                    except:
                        pass
                
                logger.error(f"创建Compose项目 {project_name} 失败: {str(e)}")
                raise Exception(f"创建失败: {str(e)}")
        
        try:
            # 异步执行创建命令
            result = await loop.run_in_executor(None, create_project_sync)
            
            # 清除缓存，确保下次获取时能看到最新状态
            cache_key = f"compose_projects_{node_id}"
            if cache_key in _cache:
                del _cache[cache_key]
            
            return result
            
        except ValueError:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"创建Compose项目时发生错误: {str(e)}")
    
    @staticmethod
    async def delete_compose_project(db: AsyncSession, node_id: int, project_name: str) -> Dict[str, Any]:
        """
        删除指定的Docker Compose项目
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            project_name: Compose项目名称
            
        Returns:
            Dict[str, Any]: 删除结果信息
        """
        # 获取节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise ValueError(f"节点ID {node_id} 不存在")
        
        # 首先获取项目信息，以验证项目是否存在并获取compose文件路径和项目路径
        projects_list = await DockerComposeService.get_compose_projects(db, node_id, refresh=True)
        
        # 查找指定的项目
        project = None
        for p in projects_list.items:
            if p.name == project_name:
                project = p
                break
        
        if not project:
            raise ValueError(f"Compose项目 {project_name} 不存在")
        
        if project.compose_file == "notfound":
            raise ValueError(f"Compose项目 {project_name} 的compose文件不存在，无法删除")
        
        # 检查是否为远程节点且compose文件不在本地
        endpoint_type = getattr(node, 'endpoint_type', '')
        if endpoint_type == 'tcp' and not os.path.exists(project.compose_file):
            raise ValueError("不支持在远程节点上删除Compose项目，除非compose文件在本地存在")
        
        # 检查compose文件是否存在
        if not os.path.exists(project.compose_file):
            raise ValueError(f"Compose文件 {project.compose_file} 不存在，无法删除")
        
        # 准备删除项目
        loop = asyncio.get_event_loop()
        
        # 定义同步函数来删除项目
        def delete_project_sync():
            try:
                # 先停止项目
                try:
                    # 构建docker compose down命令
                    cmd = [get_docker_command()]
                    cmd.extend(['compose', '-f', project.compose_file, 'down', '-v'])
                    
                    # 执行停止命令
                    subprocess.run(
                        cmd,
                        cwd=project.path,
                        capture_output=True,
                        text=True,
                        check=False,  # 即使失败也继续，因为可能项目已经停止
                        timeout=30
                    )
                    logger.info(f"删除前已停止Compose项目 {project_name}")
                except Exception as stop_e:
                    logger.warning(f"删除前停止Compose项目 {project_name} 时出错: {str(stop_e)}")
                
                # 删除项目目录及其所有内容
                if os.path.exists(project.path):
                    shutil.rmtree(project.path)
                    logger.info(f"已删除Compose项目目录: {project.path}")
                
                logger.info(f"Compose项目 {project_name} 删除成功")
                
                # 返回成功信息
                return {
                    "status": "success",
                    "message": f"Compose项目 {project_name} 删除成功",
                    "project_name": project_name,
                    "project_path": project.path
                }
                
            except Exception as e:
                logger.error(f"删除Compose项目 {project_name} 失败: {str(e)}")
                raise Exception(f"删除失败: {str(e)}")
        
        try:
            # 异步执行删除命令
            result = await loop.run_in_executor(None, delete_project_sync)
            
            # 清除缓存，确保下次获取时能看到最新状态
            cache_key = f"compose_projects_{node_id}"
            if cache_key in _cache:
                del _cache[cache_key]
            
            return result
            
        except ValueError:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"删除Compose项目时发生错误: {str(e)}")
    
    @staticmethod
    async def restart_compose_project(db: AsyncSession, node_id: int, project_name: str) -> Dict[str, Any]:
        """
        重启指定的Docker Compose项目
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            project_name: Compose项目名称
            
        Returns:
            Dict[str, Any]: 重启结果信息
        """
        # 获取节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise ValueError(f"节点ID {node_id} 不存在")
        
        # 首先获取项目信息，以验证项目是否存在并获取compose文件路径
        projects_list = await DockerComposeService.get_compose_projects(db, node_id, refresh=True)
        
        # 查找指定的项目
        project = None
        for p in projects_list.items:
            if p.name == project_name:
                project = p
                break
        
        if not project:
            raise ValueError(f"Compose项目 {project_name} 不存在")
        
        if project.compose_file == "notfound":
            raise ValueError(f"Compose项目 {project_name} 的compose文件不存在")
        
        # 检查compose文件是否存在（只对非远程节点检查）
        endpoint_type = getattr(node, 'endpoint_type', '')
        if endpoint_type != 'tcp' and not os.path.exists(project.compose_file):
            raise ValueError(f"Compose文件 {project.compose_file} 不存在")
        
        # 准备重启项目
        loop = asyncio.get_event_loop()
        
        # 定义同步函数来重启项目
        def restart_project_sync():
            try:
                # 构建docker compose restart命令
                # 先创建基础命令，不包含compose子命令
                # 使用docker命令的完整路径
                cmd = [get_docker_command()]
                
                # 如果是远程节点，添加-H参数和TLS配置
                endpoint_type = getattr(node, 'endpoint_type', '')
                endpoint_url = getattr(node, 'endpoint_url', '')
                use_tls = getattr(node, 'use_tls', False)
                ca_cert = getattr(node, 'ca_cert', '')
                client_cert = getattr(node, 'client_cert', '')
                client_key = getattr(node, 'client_key', '')
                
                if endpoint_type == 'tcp' and endpoint_url:
                    # 构建远程连接URL，确保格式正确
                    if endpoint_url.startswith('tcp://'):
                        remote_url = endpoint_url
                    elif endpoint_url.startswith('http://') or endpoint_url.startswith('https://'):
                        # 如果已经有协议前缀，只使用tcp://
                        remote_url = f"tcp://{endpoint_url.split('://')[1]}"
                    else:
                        remote_url = f"tcp://{endpoint_url}"
                    
                    # 添加-H参数
                    cmd.extend(['-H', remote_url])
                    
                    # 如果启用了TLS，添加TLS配置参数（在compose子命令之前）
                    if use_tls:
                        if ca_cert:
                            cmd.extend(['--tlsverify', '--tlscacert', ca_cert])
                        if client_cert:
                            cmd.extend(['--tlscert', client_cert])
                        if client_key:
                            cmd.extend(['--tlskey', client_key])
                
                # 添加compose子命令和参数
                cmd.extend(['compose', '-f', project.compose_file, 'restart'])
                
                # 执行重启命令
                result = subprocess.run(
                    cmd,
                    cwd=project.path,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30  # 设置合理的超时时间
                )
                
                logger.info(f"Compose Project {project_name} restart success")
                
                # 返回成功信息
                return {
                    "status": "success",
                    "message": f"Compose Project {project_name} restart success",
                    "project_name": project_name,
                    "output": result.stdout
                }
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Restart Compose Project {project_name} fail: {e.stderr}")
                raise Exception(f"重启失败: {e.stderr}")
            except subprocess.TimeoutExpired:
                logger.error(f"Restart Compose Project {project_name} timeout")
                raise Exception("重启超时，请检查项目配置")
            except Exception as e:
                logger.error(f"Restart Compose Project {project_name} error: {str(e)}")
                raise
        
        try:
            # 异步执行重启命令
            result = await loop.run_in_executor(None, restart_project_sync)
            
            # 清除缓存，确保下次获取时能看到最新状态
            cache_key = f"compose_projects_{node_id}"
            if cache_key in _cache:
                del _cache[cache_key]
            
            return result
            
        except ValueError:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"重启Compose项目时发生错误: {str(e)}")
    
    @staticmethod
    async def stop_compose_project(db: AsyncSession, node_id: int, project_name: str) -> Dict[str, Any]:
        """
        停止指定的Docker Compose项目
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            project_name: Compose项目名称
            
        Returns:
            Dict[str, Any]: 停止结果信息
        """
        # 获取节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise ValueError(f"节点ID {node_id} 不存在")
        
        # 首先获取项目信息，以验证项目是否存在并获取compose文件路径
        projects_list = await DockerComposeService.get_compose_projects(db, node_id, refresh=True)
        
        # 查找指定的项目
        project = None
        for p in projects_list.items:
            if p.name == project_name:
                project = p
                break
        
        if not project:
            raise ValueError(f"Compose项目 {project_name} 不存在")
        
        if project.compose_file == "notfound":
            raise ValueError(f"Compose项目 {project_name} 的compose文件不存在")
        
        # 检查compose文件是否存在（只对非远程节点检查）
        endpoint_type = getattr(node, 'endpoint_type', '')
        if endpoint_type != 'tcp' and not os.path.exists(project.compose_file):
            raise ValueError(f"Compose文件 {project.compose_file} 不存在")
        
        # 准备停止项目
        loop = asyncio.get_event_loop()
        
        # 定义同步函数来停止项目
        def stop_project_sync():
            try:
                # 构建docker compose down命令
                # 先创建基础命令，不包含compose子命令
                # 使用docker命令的完整路径
                cmd = [get_docker_command()]
                
                # 如果是远程节点，添加-H参数和TLS配置
                endpoint_type = getattr(node, 'endpoint_type', '')
                endpoint_url = getattr(node, 'endpoint_url', '')
                use_tls = getattr(node, 'use_tls', False)
                ca_cert = getattr(node, 'ca_cert', '')
                client_cert = getattr(node, 'client_cert', '')
                client_key = getattr(node, 'client_key', '')
                
                if endpoint_type == 'tcp' and endpoint_url:
                    # 构建远程连接URL，确保格式正确
                    if endpoint_url.startswith('tcp://'):
                        remote_url = endpoint_url
                    elif endpoint_url.startswith('http://') or endpoint_url.startswith('https://'):
                        # 如果已经有协议前缀，只使用tcp://
                        remote_url = f"tcp://{endpoint_url.split('://')[1]}"
                    else:
                        remote_url = f"tcp://{endpoint_url}"
                    
                    # 添加-H参数
                    cmd.extend(['-H', remote_url])
                    
                    # 如果启用了TLS，添加TLS配置参数（在compose子命令之前）
                    if use_tls:
                        if ca_cert:
                            cmd.extend(['--tlsverify', '--tlscacert', ca_cert])
                        if client_cert:
                            cmd.extend(['--tlscert', client_cert])
                        if client_key:
                            cmd.extend(['--tlskey', client_key])
                
                # 添加compose子命令和参数
                cmd.extend(['compose', '-f', project.compose_file, 'down'])
                
                # 记录执行的命令
                # logger.info(f"执行Docker Compose停止命令: {' '.join(cmd)}, 工作目录: {project.path}")
                
                # 执行停止命令
                result = subprocess.run(
                    cmd,
                    cwd=project.path,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30  # 设置合理的超时时间
                )
                
                logger.info(f"Compose Project {project_name} stopped successfully")
                
                # 返回成功信息
                return {
                    "status": "success",
                    "message": f"Compose Project {project_name} stopped successfully",
                    "project_name": project_name,
                    "output": result.stdout
                }
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Compose Project {project_name} stop failed: {e.stderr}")
                raise Exception(f"停止失败: {e.stderr}")
            except subprocess.TimeoutExpired:
                logger.error(f"Compose Project {project_name} stop timeout")
                raise Exception("停止超时，请检查项目配置")
            except Exception as e:
                logger.error(f"Compose Project {project_name} stop error: {str(e)}")
                raise
        
        try:
            # 异步执行停止命令
            result = await loop.run_in_executor(None, stop_project_sync)
            
            # 清除缓存，确保下次获取时能看到最新状态
            cache_key = f"compose_projects_{node_id}"
            if cache_key in _cache:
                del _cache[cache_key]
            
            return result
            
        except ValueError:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"停止Compose项目时发生错误: {str(e)}")
