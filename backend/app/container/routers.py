from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status, Body
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from config.database import get_container_db
from app.container.models import DockerNode
from app.container.schemas import (
    DockerNodeCreate, DockerNodeUpdate, DockerNodeResponse, DockerNodeList, 
    DockerNodeStatus, ContainerListResponse, ContainerInspectResponse, ContainerLogsResponse,
    ContainerOperationResponse, ContainerStatsResponse, ImageListResponse, ImageDetailResponse,
    NetworkListResponse, NetworkDetailResponse, NetworkOperationResponse, NetworkCreate,
    VolumeListResponse, VolumeDetailResponse, VolumeOperationResponse, VolumeCreate,
    ContainerSummary, SimplifiedContainerListResponse, ComposeProjectLogsResponse,
    ImageImportRequest, ImageImportResponse, LogContentResponse, ImageDeleteRequest,
    ImageExportRequest, ImageExportResponse, ImagePruneRequest, ImagePullRequest, ImagePullResponse,
    ImagePullCancelRequest, ImageBuildRequest, ImageBuildResponse, ImageCachePruneRequest, ImageCachePruneResponse,
    ContainerCreateRequest,
    DockerInfo,
    ResourceLimit,
    LocalDockerStatusResponse,
    ImageOptionListResponse,
    NetworkOptionListResponse,
    VolumeOptionListResponse,
    ContainerTerminalRequest,
    ContainerTerminalResponse,
    ContainerCommitRequest,
    ContainerCommitResponse,
    ImageTagRequest,
    ImageTagResponse
)
from middleware.auth import get_current_active_user
from app.container.service import DockerNodeService
from app.container.images_service import DockerImageService
from app.container.networks_service import DockerNetworkService
from app.container.volumes_service import DockerVolumeService
from app.container.compose_service import DockerComposeService
from app.container.schemas import ComposeProjectList

router = APIRouter(prefix="/container", tags=["container"])

##################################节点管理api###########################################

@router.post("/nodes", response_model=DockerNodeResponse, summary="创建Docker节点")
async def create_docker_node(
    node_data: DockerNodeCreate,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """创建新的Docker节点
    
    - **name**: 节点名称，必须唯一
    - **description**: 节点描述（可选）
    - **endpoint_type**: 端点类型，支持 unix_socket、tcp
    - **endpoint_url**: Docker API 端点 URL
    - **use_tls**: 是否启用TLS（对于tcp类型）
    - **ca_cert**: TLS CA证书（当 use_tls 为 true 时可选）
    - **client_cert**: TLS客户端证书（当 use_tls 为 true 时可选）
    - **client_key**: TLS客户端密钥（当 use_tls 为 true 时可选）
    """
    node = await DockerNodeService.create_docker_node(db, node_data)
    # 转换为响应模型
    return DockerNodeResponse(
            id=node.id,
            name=node.name,
            identifier=node.identifier,
            description=node.description,
            endpoint_type=node.endpoint_type,
            endpoint_url=node.endpoint_url,
            use_tls=node.use_tls,
            ca_cert=node.ca_cert,
            client_cert=node.client_cert,
            client_key=node.client_key,
            compose_path=node.compose_path,
            created_at=node.created_at,
            updated_at=node.updated_at,
            connection_config=node.connection_config
        )


@router.get("/nodes", response_model=DockerNodeList, summary="获取Docker节点列表")
async def get_docker_nodes(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """获取Docker节点列表，支持分页
    
    - **skip**: 跳过的记录数，默认为0
    - **limit**: 返回的最大记录数，默认为100
    """
    nodes, total = await DockerNodeService.get_docker_nodes(db, skip=skip, limit=limit)
    # 转换为响应模型列表
    node_responses = []
    for node in nodes:
        node_responses.append(DockerNodeResponse(
                id=node.id,
            name=node.name,
            identifier=node.identifier,
            description=node.description,
            endpoint_type=node.endpoint_type,
            endpoint_url=node.endpoint_url,
            use_tls=node.use_tls,
            ca_cert=node.ca_cert,
            client_cert=node.client_cert,
            client_key=node.client_key,
            compose_path=node.compose_path,
            created_at=node.created_at,
            updated_at=node.updated_at,
            connection_config=node.connection_config
            ))
    
    return DockerNodeList(
        items=node_responses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/nodes/{node_id}", response_model=DockerNodeResponse, summary="获取Docker节点详情")
async def get_docker_node(
    node_id: int,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """根据ID获取Docker节点的详细信息"""
    node = await DockerNodeService.get_docker_node(db, node_id)
    # 转换为响应模型
    return DockerNodeResponse(
            id=node.id,
            name=node.name,
            identifier=node.identifier,
            description=node.description,
            endpoint_type=node.endpoint_type,
            endpoint_url=node.endpoint_url,
            use_tls=node.use_tls,
            ca_cert=node.ca_cert,
            client_cert=node.client_cert,
            client_key=node.client_key,
            compose_path=node.compose_path,
            created_at=node.created_at,
            updated_at=node.updated_at,
            connection_config=node.connection_config
        )


@router.post("/nodes/{node_id}/update", response_model=DockerNodeResponse, summary="更新Docker节点")
async def update_docker_node(
    node_id: int,
    node_update: DockerNodeUpdate,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """更新Docker节点信息
    
    注意：本地节点的名称、端点类型和端点URL不能修改
    """
    node = await DockerNodeService.update_docker_node(db, node_id, node_update)
    # 转换为响应模型
    return DockerNodeResponse(
            id=node.id,
            name=node.name,
            identifier=node.identifier,
            description=node.description,
            endpoint_type=node.endpoint_type,
            endpoint_url=node.endpoint_url,
            use_tls=node.use_tls,
            ca_cert=node.ca_cert,
            client_cert=node.client_cert,
            client_key=node.client_key,
            compose_path=node.compose_path,
            created_at=node.created_at,
            updated_at=node.updated_at,
            connection_config=node.connection_config
        )


@router.post("/nodes/{node_id}/delete", summary="删除Docker节点")
async def delete_docker_node(
    node_id: int,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """删除Docker节点
    
    注意：本地节点不能删除，identifier为localhost的节点也不能删除
    """
    # 先获取节点信息，检查identifier
    node = await DockerNodeService.get_docker_node(db, node_id)
    if node.identifier == "localhost":
        raise HTTPException(status_code=403, detail="identifier为localhost的节点不允许删除")
    await DockerNodeService.delete_docker_node(db, node_id)
    return {"message": "节点删除成功"}


@router.get("/nodes/{node_id}/status", response_model=DockerNodeStatus, summary="获取Docker节点状态")
async def get_docker_node_status(
    node_id: int,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """获取指定Docker节点的状态
    
    检测节点是否在线，返回节点状态信息
    - **node_id**: Docker节点ID
    - 返回节点在线状态、错误信息（如有）和检查时间
    """
    return await DockerNodeService.get_docker_node_status(db, node_id)


@router.get("/nodes/{node_id}/info", response_model=DockerInfo, summary="获取Docker节点详细信息")
async def get_docker_node_info(
    node_id: int,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerNodeService.get_docker_info(db, node_id)


@router.get("/nodes/{node_id}/info/limit", response_model=ResourceLimit, summary="获取Docker节点资源限制信息")
async def get_docker_node_resource_limit(
    node_id: int,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取指定Docker节点的资源限制信息
    
    返回节点的CPU核心数和总内存大小(MB)
    - **node_id**: Docker节点ID
    - 返回CPU核心数和总内存大小(MB)
    """
    return await DockerNodeService.get_resource_limit(db, node_id)


@router.get("/local-docker/status", response_model=LocalDockerStatusResponse, summary="检测本地Docker状态")
async def check_local_docker_status(
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """检测面板部署所在Linux服务器的Docker状态
    
    检测内容包括：
    - Docker 是否已安装
    - Docker 守护进程是否运行中
    - /var/run/docker.sock 是否存在
    - Docker 版本号
    - 对应的本地Docker节点ID（如果已注册）
    """
    return await DockerNodeService.check_local_docker(db)


##################################容器管理api###########################################

@router.get("/nodes/{node_id}/containers", response_model=ContainerListResponse, summary="获取容器列表")
async def get_containers(
    node_id: int,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """ 获取指定Docker节点上的容器列表 """
    return await DockerNodeService.get_containers(db, node_id)

@router.post("/nodes/{node_id}/containers/create", response_model=ContainerOperationResponse, summary="创建容器")
async def create_container(
    node_id: int,
    container_data: ContainerCreateRequest,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerNodeService.create_container(db, node_id, container_data)    


@router.get("/nodes/{node_id}/containers/{container_id}/inspect", response_model=ContainerInspectResponse, summary="获取容器详细信息")
async def inspect_container(
    node_id: int,
    container_id: str,
    db: AsyncSession = Depends(get_container_db),
     current_user = Depends(get_current_active_user)
):
    """ 获取指定节点上指定容器的详细信息 """
    return await DockerNodeService.inspect_container(db, node_id, container_id)


@router.get("/nodes/{node_id}/containers/{container_id}/logs", response_model=ContainerLogsResponse, summary="获取指定容器日志")
async def get_container_logs(
    node_id: int,
    container_id: str,
    lines: int = Query(100, ge=1, le=10000, description="返回的日志行数"),
    since: Optional[int] = Query(None, description="返回指定时间戳之后的日志"),
    until: Optional[int] = Query(None, description="返回指定时间戳之前的日志"),
    timestamps: bool = Query(False, description="是否包含时间戳"),
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """ 获取指定节点上指定容器的日志 """
    logs_response = await DockerNodeService.get_container_logs(
        db, node_id, container_id, lines=lines, since=since, until=until, timestamps=timestamps
    )
    return logs_response


@router.get("/nodes/{node_id}/containers/{container_id}/stats", response_model=ContainerStatsResponse, summary="获取容器资源占用")
async def get_container_stats(
    node_id: int,
    container_id: str,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """ 获取指定节点上指定容器的资源占用信息
    
    返回容器的CPU使用率、内存使用情况、网络IO、磁盘IO等资源占用信息
    """
    return await DockerNodeService.get_container_stats(db, node_id, container_id)


@router.post("/nodes/{node_id}/containers/{container_id}/start", response_model=ContainerOperationResponse, summary="启动容器")
async def start_container(
    node_id: int,
    container_id: str,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """ 启动指定节点上的指定容器 """
    return await DockerNodeService.start_container(
        db,
        node_id,
        container_id
    )

@router.post("/nodes/{node_id}/containers/{container_id}/stop", response_model=ContainerOperationResponse, summary="停止容器")
async def stop_container(
    node_id: int,
    container_id: str,
    timeout: int = Query(10, description="停止超时时间（秒）"),
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerNodeService.stop_container(
        db,
        node_id,
        container_id,
        timeout=timeout
    )


@router.post("/nodes/{node_id}/containers/{container_id}/pause", response_model=ContainerOperationResponse, summary="暂停容器")
async def pause_container(
    node_id: int,
    container_id: str,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerNodeService.pause_container(
        db,
        node_id,
        container_id
    )


@router.post("/nodes/{node_id}/containers/{container_id}/unpause", response_model=ContainerOperationResponse, summary="恢复容器")
async def unpause_container(
    node_id: int,
    container_id: str,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerNodeService.unpause_container(
        db,
        node_id,
        container_id
    )

@router.post("/nodes/{node_id}/containers/{container_id}/restart", response_model=ContainerOperationResponse, summary="重启容器")
async def restart_container(
    node_id: int,
    container_id: str,
    timeout: int = Query(10, description="重启超时时间（秒）"),
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerNodeService.restart_container(
        db,
        node_id,
        container_id,
        timeout=timeout
    )

@router.post("/nodes/{node_id}/containers/{container_id}/delete", response_model=ContainerOperationResponse, summary="删除容器")
async def delete_container(
    node_id: int,
    container_id: str,
    force: bool = Query(False, description="是否强制删除正在运行的容器"),
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerNodeService.delete_container(
        db,
        node_id,
        container_id,
        force=force
    )

@router.post("/nodes/{node_id}/containers/{container_id}/commit", response_model=ContainerCommitResponse, summary="提交容器为镜像")
async def commit_container(
    node_id: int,
    container_id: str,
    commit_data: ContainerCommitRequest,
    db: AsyncSession = Depends(get_container_db),
    # current_user = Depends(get_current_active_user)
):
    """将指定节点上的指定容器提交为镜像
    
    - **image_name**: 完整镜像名称，格式: repository[:tag]，例如: myapp:v1.0（可选）
    """
    return await DockerNodeService.commit_container(
        db,
        node_id,
        container_id,
        image_name=commit_data.image_name
    )


# 容器终端相关路由

@router.post("/nodes/{node_id}/containers/{container_id}/terminal", response_model=ContainerTerminalResponse, summary="创建容器终端连接")
async def create_container_terminal(
    node_id: int,
    container_id: str,
    terminal_data: ContainerTerminalRequest,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """
    创建容器终端连接
    
    - **node_id**: Docker节点ID
    - **container_id**: 容器ID
    - **shell**: 容器终端连接类型，如sh、bash、ash等
    - **user**: 用户，如root等
    
    返回构建好的Docker exec命令和连接信息
    """
    # 获取节点信息以构建正确的docker命令
    node = await DockerNodeService.get_docker_node(db, node_id)
    config = node.connection_config
    
    # 构建基础docker命令
    docker_cmd = ['docker']
    
    # 添加连接参数（支持远程节点和TLS）
    if 'base_url' in config:
        # 解析base_url以提取主机和端口信息
        base_url = config['base_url']
        if base_url.startswith('tcp://'):
            # 对于TCP连接，添加-H参数
            docker_cmd.extend(['-H', base_url.replace('tcp://', '')])
        elif base_url.startswith('unix://'):
            # 对于Unix socket连接，添加-H参数
            docker_cmd.extend(['-H', base_url])
    
    # 添加TLS参数（如果配置了TLS）
    if 'tls' in config:
        docker_cmd.append('--tlsverify')
        if config['tls'].get('ca_cert_path'):
            docker_cmd.extend(['--tlscacert', config['tls']['ca_cert_path']])
        if config['tls'].get('client_cert_path'):
            docker_cmd.extend(['--tlscert', config['tls']['client_cert_path']])
        if config['tls'].get('client_key_path'):
            docker_cmd.extend(['--tlskey', config['tls']['client_key_path']])
    
    # 添加exec命令部分
    docker_cmd.extend(['container', 'exec', '-it'])
    # 当user字段不为空时才添加-u参数
    if terminal_data.user and terminal_data.user.strip():
        docker_cmd.extend(['-u', terminal_data.user.strip()])
    docker_cmd.extend([container_id, terminal_data.shell])
    
    # 构建完整的exec命令字符串
    exec_command = ' '.join(docker_cmd)
    
    # 从数据库中获取本机主机配置ID，与host模块中的/connect_localhost接口保持一致
    from sqlalchemy import select
    from app.host import models as host_models
    try:
        # 查询本机主机配置（address为127.0.0.1）
        result = await db.execute(
            select(host_models.Host).filter(host_models.Host.address == "127.0.0.1")
        )
        localhost_hosts = result.scalars().all()
        
        # 确保使用本机配置ID作为host_id
        localhost_host_id = 1  # 默认值
        if localhost_hosts:
            for host in localhost_hosts:
                if getattr(host, 'address', '') == "127.0.0.1":
                    localhost_host_id = int(getattr(host, 'id', 1))
                    break
    except Exception:
        # 发生异常时使用默认值1
        localhost_host_id = 1
    
    # 生成终端连接令牌，与主机模块保持一致的格式和生成方式
    import time, hmac, hashlib
    from config.settings import settings
    timestamp = int(time.time())
    message = f"{localhost_host_id}:{timestamp}"
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # 生成与主机模块一致格式的token
    token = f"{localhost_host_id}:{timestamp}:{signature}"
    
    return ContainerTerminalResponse(
        success=True,
        message="200",
        host_id=localhost_host_id,
        token=token,
        exec=exec_command
    )


##################################镜像管理api###########################################

@router.get("/nodes/{node_id}/images", response_model=ImageListResponse, summary="获取镜像列表")
async def get_images(
    node_id: int,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """获取指定Docker节点上的镜像列表"""
    return await DockerImageService.get_images(db, node_id)

@router.get("/nodes/{node_id}/images/list", response_model=ImageOptionListResponse, summary="获取Docker节点镜像选项列表")
async def get_image_options(
    node_id: int,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取指定Docker节点上的镜像选项列表
    
    返回节点上所有镜像的标签列表，用于前端选择器
    - **node_id**: Docker节点ID
    - 返回格式: {"data": [{"option": "镜像标签"}]}
    """
    return await DockerImageService.get_image_options(db, node_id)    


@router.get("/nodes/{node_id}/images/{image_id}/inspect", response_model=ImageDetailResponse, summary="获取镜像详细信息")
async def get_image_detail(
    node_id: int,
    image_id: str,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """获取指定Docker节点上指定镜像的详细信息"""
    return await DockerImageService.get_image_detail(db, node_id, image_id)


@router.post("/nodes/{node_id}/images/{image_id}/delete", response_model=ContainerOperationResponse, summary="删除镜像")
async def delete_image(
    node_id: int,
    image_id: str,
    delete_request: ImageDeleteRequest,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerImageService.delete_image(db, node_id, image_id, force=delete_request.force)


@router.post("/nodes/{node_id}/images/import", response_model=ImageImportResponse, summary="导入镜像")
async def import_image(
    node_id: int,
    import_data: ImageImportRequest,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerImageService.import_image(db, node_id, import_data)


@router.post("/nodes/{node_id}/images/pull", response_model=ImagePullResponse, summary="拉取镜像")
async def pull_image(
    node_id: int,
    pull_data: ImagePullRequest,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerImageService.pull_image(db, node_id, pull_data)


@router.post("/nodes/{node_id}/images/pull/cancel", summary="取消拉取镜像")
async def cancel_pull_image(
    node_id: int,
    cancel_data: ImagePullCancelRequest,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerImageService.cancel_pull_image(db, node_id, cancel_data)


@router.post("/nodes/{node_id}/images/build", response_model=ImageBuildResponse, summary="构建镜像")
async def build_image(
    node_id: int,
    build_data: ImageBuildRequest,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerImageService.build_image(db, node_id, build_data)


@router.post("/nodes/{node_id}/images/cache/prune", response_model=ImageCachePruneResponse, summary="清除镜像缓存")
async def prune_image_cache(
    node_id: int,
    prune_data: ImageCachePruneRequest,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerImageService.prune_image_cache(db, node_id, prune_data)


@router.get("/operations/{operation_id}/log/read", response_model=LogContentResponse, summary="获取导入镜像操作日志")
async def get_operation_log(
    operation_id: str,
    current_user = Depends(get_current_active_user)
):
    return await DockerImageService.get_operation_log(operation_id)


@router.post("/nodes/{node_id}/images/prune", summary="清理未使用的镜像")
async def prune_images(
    node_id: int,
    prune_request: ImagePruneRequest = Body(ImagePruneRequest(), description="镜像清理请求参数"),
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerImageService.prune_images(db, node_id, prune_request=prune_request)

@router.post("/nodes/{node_id}/images/export", response_model=ImageExportResponse, summary="导出镜像")
async def export_image(
    node_id: int,
    export_data: ImageExportRequest,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerImageService.export_image(db, node_id, export_data)


@router.post("/nodes/{node_id}/images/{image_id}/tag", response_model=ImageTagResponse, summary="管理镜像标签")
async def manage_image_tags(
    node_id: int,
    image_id: str,
    tag_request: ImageTagRequest = Body(..., description="镜像标签管理请求参数"),
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerImageService.manage_image_tags(db, node_id, image_id, tag_request)



##################################网络管理api###########################################

@router.get("/nodes/{node_id}/networks", response_model=NetworkListResponse, summary="获取网络列表")
async def get_networks(
    node_id: int,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerNetworkService.get_networks(db, node_id)


@router.get("/nodes/{node_id}/networks/list", response_model=NetworkOptionListResponse, summary="获取Docker节点网络选项列表")
async def get_network_options(
    node_id: int,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取指定Docker节点上的网络选项列表
    
    返回节点上所有网络的名称列表，用于前端选择器
    - **node_id**: Docker节点ID
    - 返回格式: {"data": [{"option": "网络名称"}]}
    """
    return await DockerNetworkService.get_network_options(db, node_id)


@router.post("/nodes/{node_id}/networks/create", response_model=NetworkDetailResponse, summary="创建网络")
async def create_network(
    node_id: int,
    network_data: NetworkCreate,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerNetworkService.create_network(db, node_id, network_data)


@router.get("/nodes/{node_id}/networks/{network_id}/inspect", response_model=NetworkDetailResponse, summary="获取网络详情")
async def get_network_detail(
    node_id: int,
    network_id: str,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerNetworkService.get_network_detail(db, node_id, network_id)


@router.post("/nodes/{node_id}/networks/{network_id}/delete", response_model=NetworkOperationResponse, summary="删除网络")
async def delete_network(
    node_id: int,
    network_id: str,
    force: bool = Query(False, description="是否强制删除正在使用的网络"),
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerNetworkService.delete_network(db, node_id, network_id, force=force)


@router.post("/nodes/{node_id}/networks/prune", summary="清理未使用的网络")
async def prune_networks(
    node_id: int,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerNetworkService.prune_networks(db, node_id)





##################################存储卷管理api###########################################

@router.get("/nodes/{node_id}/volumes", response_model=VolumeListResponse, summary="获取存储卷列表")
async def get_volumes(
    node_id: int,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerVolumeService.get_volumes(db, node_id)

@router.get("/nodes/{node_id}/volumes/list", response_model=VolumeOptionListResponse, summary="获取Docker节点存储卷选项列表")
async def get_volume_options(
    node_id: int,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    """
    获取指定Docker节点上的存储卷选项列表
    
    返回节点上所有存储卷的名称列表，用于前端选择器
    - **node_id**: Docker节点ID
    - 返回格式: {"data": [{"option": "存储卷名称"}]}
    """
    return await DockerVolumeService.get_volume_options(db, node_id)


@router.post("/nodes/{node_id}/volumes/create", response_model=VolumeDetailResponse, summary="创建存储卷")
async def create_volume(
    node_id: int,
    volume_data: VolumeCreate,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerVolumeService.create_volume(db, node_id, volume_data)


@router.get("/nodes/{node_id}/volumes/{volume_id}/inspect", response_model=VolumeDetailResponse, summary="获取存储卷详情")
async def get_volume_detail(
    node_id: int,
    volume_id: str,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerVolumeService.get_volume_detail(db, node_id, volume_id)


@router.post("/nodes/{node_id}/volumes/{volume_id}/delete", response_model=VolumeOperationResponse, summary="删除存储卷")
async def delete_volume(
    node_id: int,
    volume_id: str,
    force: bool = Query(False, description="是否强制删除正在使用的存储卷"),
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerVolumeService.delete_volume(db, node_id, volume_id, force=force)


@router.post("/nodes/{node_id}/volumes/prune", summary="清理未使用的存储卷")
async def prune_volumes(
    node_id: int,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    return await DockerVolumeService.prune_volumes(db, node_id)




##################################Compose项目管理api###########################################

@router.get("/nodes/{node_id}/composelist", response_model=ComposeProjectList, summary="获取Compose项目列表")
async def get_compose_projects(
    node_id: int,
    refresh: bool = Query(False, description="是否强制刷新数据，绕过缓存"),
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    try:
        return await DockerComposeService.get_compose_projects(db, node_id, refresh=refresh)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Compose项目列表失败: {str(e)}")

@router.post("/nodes/{node_id}/compose/{project_name}/start", response_model=Dict[str, Any], summary="启动Compose项目")
async def start_compose_project(
    node_id: int,
    project_name: str,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    try:
        result = await DockerComposeService.start_compose_project(db, node_id, project_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动Compose项目失败: {str(e)}")

@router.post("/nodes/{node_id}/compose/{project_name}/restart", response_model=Dict[str, Any], summary="重启Compose项目")
async def restart_compose_project(
    node_id: int,
    project_name: str,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    try:
        result = await DockerComposeService.restart_compose_project(db, node_id, project_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重启Compose项目失败: {str(e)}")

@router.post("/nodes/{node_id}/compose/{project_name}/stop", response_model=Dict[str, Any], summary="停止Compose项目")
async def stop_compose_project(
    node_id: int,
    project_name: str,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    try:
        result = await DockerComposeService.stop_compose_project(db, node_id, project_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止Compose项目失败: {str(e)}")

@router.post("/nodes/{node_id}/compose/create", response_model=Dict[str, Any], summary="创建Compose项目")
async def create_compose_project(
    node_id: int,
    request: dict,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    try:
        # 验证必需参数
        if "project_name" not in request or "compose_content" not in request:
            raise ValueError("project_name和compose_content是必需参数")
        
        project_name = request["project_name"]
        compose_content = request["compose_content"]
        start_on_create = request.get("start_on_create", False)
        env_content = request.get("env_content", None)
        
        # 调用服务层方法创建项目
        result = await DockerComposeService.create_compose_project(
            db, node_id, project_name, compose_content, start_on_create, None, env_content
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建Compose项目失败: {str(e)}")

@router.get("/nodes/{node_id}/compose/{project_name}/containers", response_model=SimplifiedContainerListResponse, summary="获取Compose项目容器列表")
async def get_compose_project_containers(
    node_id: int,
    project_name: str,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    try:
        # 从Compose服务获取项目容器列表
        container_list = await DockerComposeService.get_compose_project_containers(db, node_id, project_name)
        
        # 返回容器列表响应
        return SimplifiedContainerListResponse(
            items=container_list,
            total=len(container_list)
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Compose项目容器列表失败: {str(e)}")


@router.get("/nodes/{node_id}/compose/{project_name}/logs", response_model=ComposeProjectLogsResponse, summary="获取Compose项目日志")
async def get_compose_project_logs(
    node_id: int,
    project_name: str,
    lines: int = Query(100, ge=1, le=10000, description="每个容器返回的日志行数"),
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    try:
        # 从Compose服务获取项目日志
        logs_response = await DockerComposeService.get_compose_project_logs(db, node_id, project_name, lines)
        
        return logs_response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Compose项目日志失败: {str(e)}")

@router.post("/nodes/{node_id}/compose/{project_name}/delete", response_model=Dict[str, Any], summary="删除Compose项目")
async def delete_compose_project(
    node_id: int,
    project_name: str,
    db: AsyncSession = Depends(get_container_db),
    current_user = Depends(get_current_active_user)
):
    try:
        result = await DockerComposeService.delete_compose_project(db, node_id, project_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除Compose项目失败: {str(e)}")

