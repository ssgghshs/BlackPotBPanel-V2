from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
import os


class ResourceLimit(BaseModel):
    """资源限制响应模型"""
    cpus: int = Field(..., description="CPU核心数")
    total_memory: int = Field(..., description="总内存大小(MB)")



# 移除循环导入
class DockerNodeBase(BaseModel):
    """Docker节点基础模型"""
    name: str = Field(..., min_length=1, max_length=255, description="节点名称")
    identifier: Optional[str] = Field(None, max_length=100, description="节点标识")
    description: Optional[str] = Field(None, description="节点描述")
    endpoint_type: str = Field(..., pattern="^(unix_socket|tcp)$", description="端点类型: unix_socket, tcp")
    endpoint_url: str = Field(..., min_length=1, max_length=500, description="Docker API端点URL")
    use_tls: bool = Field(False, description="是否启用TLS")
    ca_cert: Optional[str] = Field(None, description="TLS CA证书内容")
    client_cert: Optional[str] = Field(None, description="TLS客户端证书内容")
    client_key: Optional[str] = Field(None, description="TLS客户端密钥内容")
    compose_path: Optional[str] = Field(None, max_length=500, description="Docker Compose文件路径")


class DockerNodeCreate(DockerNodeBase):
    """创建Docker节点的请求模型"""
    pass


class DockerNodeUpdate(BaseModel):
    """更新Docker节点的请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="节点名称")
    identifier: Optional[str] = Field(None, max_length=100, description="节点标识")
    description: Optional[str] = Field(None, description="节点描述")
    endpoint_type: Optional[str] = Field(None, pattern="^(unix_socket|tcp)$", description="端点类型: unix_socket, tcp")
    endpoint_url: Optional[str] = Field(None, min_length=1, max_length=500, description="Docker API端点URL")
    use_tls: Optional[bool] = Field(None, description="是否启用TLS")
    ca_cert: Optional[str] = Field(None, description="TLS CA证书内容")
    client_cert: Optional[str] = Field(None, description="TLS客户端证书内容")
    client_key: Optional[str] = Field(None, description="TLS客户端密钥内容")
    compose_path: Optional[str] = Field(None, max_length=500, description="Docker Compose文件路径")


class DockerNodeResponse(DockerNodeBase):
    """Docker节点响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    # 添加连接配置信息（不包含敏感信息）
    connection_config: Dict[str, Any]
    
    class Config:
        from_attributes = True


class DockerNodeList(BaseModel):
    """Docker节点列表响应模型"""
    items: List[DockerNodeResponse]
    total: int
    skip: int
    limit: int


class DockerNodeStatus(BaseModel):
    """Docker节点状态响应模型"""
    node_id: int
    is_online: bool = Field(..., description="节点是否在线")
    status: str = Field(..., description="节点状态: online, offline, error")
    error_message: Optional[str] = Field(None, description="错误信息，仅当状态为error时有效")
    check_time: datetime = Field(default_factory=datetime.now, description="状态检查时间")



class ContainerSummary(BaseModel):
    """容器摘要信息"""
    containerID: str = Field(..., description="容器ID")
    name: str = Field(..., description="容器名称")
    imageID: str = Field(..., description="镜像ID")
    imageName: str = Field(..., description="镜像名称")
    createTime: str = Field(..., description="创建时间")
    state: str = Field(..., description="容器状态")
    network: List[str] = Field(default_factory=list, description="网络IP列表")
    ports: List[str] = Field(default_factory=list, description="端口映射列表")
    isFromApp: bool = Field(False, description="是否来自应用")
    isFromCompose: bool = Field(False, description="是否来自Compose")
    appName: str = Field("", description="应用名称")
    appInstallName: str = Field("", description="应用安装名称")
    websites: Optional[Any] = Field(None, description="网站信息")


class SimplifiedContainerItem(BaseModel):
    """简化版容器信息项"""
    name: str = Field(..., description="容器名称")
    imageName: str = Field(..., description="镜像名称")
    createTime: str = Field(..., description="创建时间")
    state: str = Field(..., description="容器状态")
    network: List[str] = Field(default_factory=list, description="网络IP列表")
    ports: List[str] = Field(default_factory=list, description="端口映射列表")


class SimplifiedContainerListResponse(BaseModel):
    """简化版容器列表响应模型"""
    items: List[SimplifiedContainerItem]
    total: int


class ContainerListResponse(BaseModel):
    """容器列表响应模型"""
    items: List[ContainerSummary]
    total: int


class NewContainerItem(BaseModel):
    """新容器信息项"""
    containerID: str = Field(..., description="容器ID")
    name: str = Field(..., description="容器名称")
    imageID: str = Field(..., description="镜像ID")
    imageName: str = Field(..., description="镜像名称")
    createTime: str = Field(..., description="创建时间")
    state: str = Field(..., description="容器状态")
    network: List[str] = Field(default_factory=list, description="网络IP列表")
    ports: List[str] = Field(default_factory=list, description="端口映射列表")
    isFromApp: bool = Field(False, description="是否来自应用")
    isFromCompose: bool = Field(False, description="是否来自Compose")
    appName: str = Field("", description="应用名称")
    appInstallName: str = Field("", description="应用安装名称")
    websites: Optional[Any] = Field(None, description="网站信息")


class NewContainerListResponse(BaseModel):
    """新容器列表响应模型"""
    items: List[NewContainerItem]
    total: int


class ContainerInspectResponse(BaseModel):
    """容器详细信息响应模型"""
    id: str = Field(..., description="容器ID")
    name: str = Field(..., description="容器名称")
    image: str = Field(..., description="镜像ID")
    image_name: Optional[str] = Field(None, description="镜像名称")
    state: Dict[str, Any] = Field(default_factory=dict, description="容器状态信息")
    config: Dict[str, Any] = Field(default_factory=dict, description="容器配置信息")
    network_settings: Dict[str, Any] = Field(default_factory=dict, description="网络配置信息")
    mounts: List[Dict[str, Any]] = Field(default_factory=list, description="挂载信息")
    created: str = Field(..., description="创建时间")
    host_config: Dict[str, Any] = Field(default_factory=dict, description="主机配置信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="容器元数据")


class ContainerLogsResponse(BaseModel):
    """容器日志响应模型"""
    container_id: str = Field(..., description="容器ID")
    container_name: str = Field(..., description="容器名称")
    logs: str = Field(..., description="容器日志内容")
    lines: int = Field(default=100, description="返回的日志行数")
    since: Optional[int] = Field(None, description="返回指定时间戳之后的日志")
    until: Optional[int] = Field(None, description="返回指定时间戳之前的日志")
    timestamps: bool = Field(default=False, description="是否包含时间戳")
    follow: bool = Field(default=False, description="是否持续获取日志")


class ContainerOperationResponse(BaseModel):
    """容器操作响应模型"""
    container_id: str = Field(..., description="容器ID")
    container_name: str = Field(..., description="容器名称")
    operation: str = Field(..., description="操作类型: start, stop, pause, unpause, restart, delete")
    success: bool = Field(..., description="操作是否成功")
    message: Optional[str] = Field(None, description="操作消息")


class ContainerExecRequest(BaseModel):
    """容器执行请求模型"""
    command: str = Field(..., description="要执行的命令")
    tty: bool = Field(True, description="是否分配TTY终端")
    stdin: bool = Field(True, description="是否打开标准输入")


class ContainerExecResponse(BaseModel):
    """容器执行响应模型"""
    exec_id: str = Field(..., description="执行ID")
    container_id: str = Field(..., description="容器ID")
    command: str = Field(..., description="执行的命令")
    success: bool = Field(..., description="是否成功创建执行实例")
    message: Optional[str] = Field(None, description="响应消息")


# ContainerTerminalInfo模型已移除（WebSocket终端功能不再需要）


class ExposedPort(BaseModel):
    hostIP: Optional[str] = Field('', description="宿主机IP")
    hostPort: str = Field(..., description="宿主机端口或范围")
    containerPort: str = Field(..., description="容器端口或范围")
    protocol: str = Field('tcp', description="协议: tcp/udp")


class VolumeMount(BaseModel):
    type: str = Field(..., description="挂载类型: bind/volume")
    sourceDir: str = Field(..., description="源路径或卷名")
    containerDir: str = Field(..., description="容器内路径")
    mode: str = Field('rw', description="读写模式: rw/ro")
    shared: Optional[str] = Field(None, description="绑定传播模式")


class ContainerCreateRequest(BaseModel):
    name: str = Field(..., description="容器名称")
    image: str = Field(..., description="镜像标签")
    network: Optional[str] = Field(None, description="网络模式或网络名称")
    hostname: Optional[str] = Field(None, description="主机名")
    domainName: Optional[str] = Field(None, description="域名")
    macAddr: Optional[str] = Field(None, description="MAC地址")
    dns: List[str] = Field(default_factory=list, description="DNS服务器")
    ipv4: Optional[str] = Field(None, description="IPv4地址")
    ipv6: Optional[str] = Field(None, description="IPv6地址")
    publishAllPorts: bool = Field(False, description="是否发布所有端口")
    exposedPorts: List[ExposedPort] = Field(default_factory=list, description="端口映射")
    tty: bool = Field(False, description="是否分配TTY")
    openStdin: bool = Field(False, description="是否打开stdin")
    workingDir: Optional[str] = Field(None, description="工作目录")
    user: Optional[str] = Field(None, description="运行用户")
    cmd: List[str] = Field(default_factory=list, description="命令")
    entrypoint: List[str] = Field(default_factory=list, description="入口点")
    cpuShares: Optional[int] = Field(0, description="CPU份额")
    nanoCPUs: Optional[float] = Field(0, description="CPU核数(小数)")
    memory: Optional[float] = Field(0, description="内存大小(MiB)")
    privileged: bool = Field(False, description="特权模式")
    autoRemove: bool = Field(False, description="自动删除")
    volumes: List[VolumeMount] = Field(default_factory=list, description="卷挂载")
    labels: List[str] = Field(default_factory=list, description="标签列表 key=value")
    env: List[str] = Field(default_factory=list, description="环境变量列表 key=value")
    restartPolicy: Optional[str] = Field('no', description="重启策略: no/always/on-failure")


class ContainerStatsResponse(BaseModel):
    """容器资源占用响应模型"""
    container_id: str = Field(..., description="容器ID")
    container_name: str = Field(..., description="容器名称")
    cpu_percentage: float = Field(..., description="CPU使用率百分比")
    memory_usage: int = Field(..., description="内存使用量(字节)")
    memory_limit: int = Field(..., description="内存限制(字节)")
    memory_percentage: float = Field(..., description="内存使用率百分比")
    network_rx_bytes: int = Field(..., description="网络接收字节数")
    network_tx_bytes: int = Field(..., description="网络发送字节数")
    block_read_bytes: int = Field(..., description="磁盘读取字节数")
    block_write_bytes: int = Field(..., description="磁盘写入字节数")
    pids: int = Field(..., description="进程ID数量")
    timestamp: datetime = Field(default_factory=datetime.now, description="统计时间戳")


class ImageSummary(BaseModel):
    """镜像摘要信息"""
    id: str = Field(..., description="镜像ID")
    id_short: str = Field(..., description="短镜像ID")
    createdAt: str = Field(..., description="创建时间")
    isUsed: bool = Field(default=False, description="镜像是否被使用")
    tags: List[str] = Field(default_factory=list, description="镜像标签列表")
    size: int = Field(..., description="镜像大小（字节）")


class ImageListResponse(BaseModel):
    """镜像列表响应模型"""
    items: List[ImageSummary]
    total: int


class ImageDetailResponse(BaseModel):
    """镜像详细信息响应模型"""
    id: str = Field(..., description="镜像ID")
    id_short: str = Field(..., description="短镜像ID")
    createdAt: str = Field(..., description="创建时间")
    isUsed: bool = Field(default=False, description="镜像是否被使用")
    tags: List[str] = Field(default_factory=list, description="镜像标签列表")
    size: int = Field(..., description="镜像大小（字节）")
    digest: Optional[str] = Field(None, description="镜像摘要")
    repo_digests: List[str] = Field(default_factory=list, description="镜像摘要列表")
    parent_id: str = Field(..., description="父镜像ID")
    os: str = Field(..., description="操作系统")
    architecture: str = Field(..., description="架构")
    container_config: Dict[str, Any] = Field(default_factory=dict, description="容器配置")
    config: Dict[str, Any] = Field(default_factory=dict, description="镜像配置")
    graph_driver: Dict[str, Any] = Field(default_factory=dict, description="图形驱动信息")


class NetworkSummary(BaseModel):
    """网络摘要信息"""
    id: str = Field(..., description="网络ID")
    name: str = Field(..., description="网络名称")
    labels: List[str] = Field(default_factory=list, description="网络标签列表")
    driver: str = Field(..., description="网络驱动")
    ipamDriver: str = Field(..., description="IPAM驱动")
    subnet: str = Field(default="", description="子网")
    gateway: str = Field(default="", description="网关")
    createdAt: str = Field(default="", description="创建时间")
    attachable: bool = Field(default=False, description="是否可附加")


class NetworkListResponse(BaseModel):
    """网络列表响应模型"""
    items: List[NetworkSummary]
    total: int


class NetworkDetailResponse(BaseModel):
    """网络详细信息响应模型"""
    id: str = Field(..., description="网络ID")
    name: str = Field(..., description="网络名称")
    driver: str = Field(..., description="网络驱动")
    scope: str = Field(..., description="网络作用域")
    internal: bool = Field(default=False, description="是否内部网络")
    enableIPv6: bool = Field(default=False, description="是否启用IPv6")
    ipamDriver: str = Field(..., description="IPAM驱动")
    ipamConfig: Dict[str, Any] = Field(default_factory=dict, description="IPAM配置")
    containers: Dict[str, Any] = Field(default_factory=dict, description="连接的容器")
    options: Dict[str, str] = Field(default_factory=dict, description="网络选项")
    labels: Dict[str, str] = Field(default_factory=dict, description="网络标签")
    created: str = Field(..., description="创建时间")


class NetworkOperationResponse(BaseModel):
    """网络操作响应模型"""
    network_id: str = Field(..., description="网络ID")
    network_name: str = Field(..., description="网络名称")
    operation: str = Field(..., description="操作类型: delete")
    success: bool = Field(..., description="操作是否成功")
    message: Optional[str] = Field(None, description="操作消息")


class NetworkCreate(BaseModel):
    """创建网络的请求模型"""
    name: str = Field(..., min_length=1, max_length=255, description="网络名称")
    driver: str = Field("bridge", description="网络驱动，默认为bridge")
    options: Optional[Dict[str, str]] = Field(None, description="网络选项")
    ipam: Optional[Dict[str, Any]] = Field(None, description="IPAM配置")
    internal: bool = Field(False, description="是否为内部网络")
    enableIPv6: bool = Field(False, description="是否启用IPv6")
    labels: Optional[Dict[str, str]] = Field(None, description="网络标签")
    check_duplicate: bool = Field(True, description="是否检查重复网络名称")
    attachable: bool = Field(False, description="网络是否可附加")


class VolumeCreate(BaseModel):
    """创建存储卷的请求模型"""
    name: Optional[str] = Field(None, description="存储卷名称，不指定时Docker会自动生成")
    driver: str = Field("local", description="存储卷驱动，默认为local")
    driver_opts: Optional[Dict[str, str]] = Field(None, description="驱动选项")
    labels: Optional[Dict[str, str]] = Field(None, description="存储卷标签")


class VolumeSummary(BaseModel):
    """存储卷摘要信息"""
    name: str = Field(..., description="存储卷名称")
    driver: str = Field(..., description="存储卷驱动")
    mountpoint: str = Field(..., description="存储卷挂载点")
    labels: Dict[str, str] = Field(default_factory=dict, description="存储卷标签")
    scope: str = Field(..., description="存储卷作用域")
    created_at: str = Field(..., description="创建时间")


class VolumeListResponse(BaseModel):
    """存储卷列表响应模型"""
    items: List[VolumeSummary]
    total: int


class VolumeDetailResponse(BaseModel):
    """存储卷详细信息响应模型"""
    name: str = Field(..., description="存储卷名称")
    driver: str = Field(..., description="存储卷驱动")
    mountpoint: str = Field(..., description="存储卷挂载点")
    labels: Dict[str, str] = Field(default_factory=dict, description="存储卷标签")
    scope: str = Field(..., description="存储卷作用域")
    created_at: str = Field(..., description="创建时间")
    usage_count: int = Field(default=0, description="使用计数")
    # 可选的存储卷选项
    options: Dict[str, str] = Field(default_factory=dict, description="存储卷选项")
    cluster_volume: bool = Field(default=False, description="是否为集群卷")
    # 引用该存储卷的容器
    containers: Dict[str, str] = Field(default_factory=dict, description="引用该存储卷的容器")


class VolumeOperationResponse(BaseModel):
    """存储卷操作响应模型"""
    volume_id: str = Field(..., description="存储卷ID")
    volume_name: str = Field(..., description="存储卷名称")
    operation: str = Field(..., description="操作类型: delete")
    success: bool = Field(..., description="操作是否成功")
    message: Optional[str] = Field(None, description="操作消息")


class ComposeProjectSummary(BaseModel):
    """Compose项目摘要信息"""
    name: str = Field(..., description="项目名称")
    path: str = Field(..., description="项目路径")
    compose_file: str = Field(..., description="docker-compose文件路径")
    services: List[str] = Field(default_factory=list, description="服务列表")
    status: str = Field(..., description="项目状态: running, stopped, partial")
    created_at: str = Field(..., description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")
    containerCount: int = Field(0, description="总容器数")
    runningCount: int = Field(0, description="运行中的容器数")


class ComposeProjectList(BaseModel):
    """Compose项目列表响应模型"""
    items: List[ComposeProjectSummary]
    total: int


class NetworkOption(BaseModel):
    """网络选项模型"""
    option: str = Field(..., description="网络名称选项")


class NetworkOptionListResponse(BaseModel):
    """网络选项列表响应模型"""
    data: List[NetworkOption] = Field(default_factory=list, description="网络选项列表")


class ComposeContainerLog(BaseModel):
    """Compose容器日志模型"""
    container_name: str = Field(..., description="容器名称")
    service_name: str = Field(..., description="服务名称")
    logs: str = Field(..., description="容器日志内容")
    timestamp: datetime = Field(default_factory=datetime.now, description="日志时间戳")


class ComposeProjectLogsResponse(BaseModel):
    """Compose项目日志响应模型"""
    project_name: str = Field(..., description="项目名称")
    logs: List[ComposeContainerLog] = Field(default_factory=list, description="项目中各容器的日志列表")
    total: int = Field(..., description="日志条目总数")


class ImageImportRequest(BaseModel):
    """镜像导入请求模型"""
    image_path: str = Field(..., description="镜像tar包路径")
    tag: Optional[str] = Field(None, description="导入后镜像的标签")
    quiet: bool = Field(False, description="是否静默导入")


class ImageImportResponse(BaseModel):
    """镜像导入响应模型"""
    operation_id: str = Field(..., description="操作ID")
    message: str = Field(..., description="操作消息")
    log_file_path: str = Field(..., description="日志文件路径")
    success: bool = Field(..., description="操作是否成功启动")


class ImageDeleteRequest(BaseModel):
    """镜像删除请求模型"""
    force: bool = Field(False, description="是否强制删除被使用的镜像")


class ImagePruneRequest(BaseModel):
    """镜像清理请求模型"""
    dangling: Optional[bool] = Field(None, description="是否仅清理悬空镜像：true(只清理悬空镜像)，false(清理所有未使用镜像)")


class ImageExportRequest(BaseModel):
    """镜像导出请求模型"""
    output_path: str = Field(..., description="导出文件保存路径")
    tag: Optional[str] = Field(None, description="要导出的镜像标签")
    compress: bool = Field(True, description="是否压缩导出文件")


class ImageExportResponse(BaseModel):
    """镜像导出响应模型"""
    message: str = Field(..., description="操作消息")
    log_file_path: str = Field(..., description="日志文件路径")
    output_file_path: str = Field(..., description="导出文件保存路径")
    success: bool = Field(..., description="操作是否成功启动")


class LogContentResponse(BaseModel):
    """日志内容响应模型"""
    operation_id: str = Field(..., description="操作ID")
    log_content: str = Field(..., description="日志内容")
    log_file_exists: bool = Field(..., description="日志文件是否存在")
    is_complete: bool = Field(False, description="操作是否完成")


class ImagePullRequest(BaseModel):
    name: str = Field(..., description="镜像名称，例如 nginx 或 registry/repo")
    tag: Optional[str] = Field(None, description="镜像标签，未提供则默认为latest或从name解析")


class ImagePullResponse(BaseModel):
    operation_id: str = Field(..., description="操作ID")
    message: str = Field(..., description="操作消息")
    log_file_path: str = Field(..., description="日志文件路径")
    success: bool = Field(..., description="操作是否成功启动")


class ImagePullCancelRequest(BaseModel):
    operation_id: str = Field(..., description="要取消的拉取操作ID")


class ImageBuildRequest(BaseModel):
    path: str = Field(..., description="Dockerfile路径")
    tag: str = Field(..., description="镜像标签")


class ImageBuildResponse(BaseModel):
    operation_id: str = Field(..., description="操作ID")
    message: str = Field(..., description="操作消息")
    log_file_path: str = Field(..., description="日志文件路径")
    success: bool = Field(..., description="操作是否成功启动")


class ImageOption(BaseModel):
    option: str = Field(..., description="镜像名称选项")


class ImageOptionListResponse(BaseModel):
    data: List[ImageOption] = Field(default_factory=list, description="镜像选项列表")


class VolumeOption(BaseModel):
    option: str = Field(..., description="卷名称选项")


class VolumeOptionListResponse(BaseModel):
    data: List[VolumeOption] = Field(default_factory=list, description="卷选项列表")


class ImageCachePruneRequest(BaseModel):
    """清除镜像缓存请求模型"""
    all: bool = Field(False, description="是否清除所有缓存镜像，默认只清除悬空缓存")


class ImageCachePruneResponse(BaseModel):
    """清除镜像缓存响应模型"""
    operation_id: str = Field(..., description="操作ID")
    message: str = Field(..., description="操作消息")
    log_file_path: str = Field(..., description="日志文件路径")
    success: bool = Field(..., description="操作是否成功启动")


class DockerInfo(BaseModel):
    """Docker主机信息"""
    docker_host: str = Field(..., description="Docker Host（节点连接地址）")
    server_version: str = Field(..., description="Docker服务端版本")
    container_count: int = Field(..., description="容器数量")
    stopped_containers: int = Field(..., description="已停止的容器数量")
    running_containers: int = Field(..., description="运行中的容器数量")
    image_count: int = Field(..., description="镜像数量")
    network_count: int = Field(..., description="网络数量")
    volume_count: int = Field(..., description="存储卷数量")
    compose_count: int = Field(..., description="编排数量")
    cpus: Optional[int] = Field(None, description="CPU核心数")
    total_memory: Optional[str] = Field(None, description="总内存大小（带Gi单位）")
    storage_plugins: Optional[List[str]] = Field(default_factory=list, description="存储插件列表")
    network_plugins: Optional[List[str]] = Field(default_factory=list, description="网络插件列表")
    log_driver: Optional[str] = Field(None, description="默认日志驱动")
    storage_driver: Optional[str] = Field(None, description="文件存储驱动")
    root_dir: Optional[str] = Field(None, description="Docker根目录")
    
    class Config:
        from_attributes = True


class ContainerTerminalRequest(BaseModel):
    """容器终端连接请求模型"""
    shell: str = Field(..., description="容器终端连接类型，如sh、bash、ash等")
    user: str = Field(..., description="用户，如root等")


class ContainerTerminalResponse(BaseModel):
    """容器终端连接响应模型"""
    success: bool = Field(..., description="连接是否成功")
    message: str = Field(..., description="响应消息")
    host_id: int = Field(..., description="主机ID")
    token: str = Field(..., description="连接令牌")
    exec: str = Field(..., description="执行的Docker命令")


class ContainerCommitRequest(BaseModel):
    """容器提交镜像请求模型"""
    image_name: Optional[str] = Field(None, description="完整镜像名称，格式: repository[:tag]，例如: myapp:v1.0")
    message: Optional[str] = Field(None, description="提交信息")
    author: Optional[str] = Field(None, description="作者信息")
    pause: bool = Field(True, description="提交前是否暂停容器")
    changes: Optional[List[str]] = Field(None, description="Dockerfile指令列表，如['CMD [\'/bin/bash\']', 'EXPOSE 80']")


class ContainerCommitResponse(BaseModel):
    """容器提交镜像响应模型"""
    container_id: str = Field(..., description="容器ID")
    image_id: str = Field(..., description="新创建的镜像ID")
    repository: Optional[str] = Field(None, description="镜像仓库名")
    tag: Optional[str] = Field(None, description="镜像标签")
    image_name: str = Field(..., description="完整镜像名称（包含标签）")
    success: bool = Field(..., description="操作是否成功")
    message: Optional[str] = Field(None, description="操作消息")


class ImageTagRequest(BaseModel):
    """镜像标签管理请求模型"""
    tags: List[str] = Field(..., description="镜像标签列表")


class ImageTagResponse(BaseModel):
    """镜像标签管理响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作消息")
    image_id: str = Field(..., description="镜像ID")
    updated_tags: List[str] = Field(default_factory=list, description="更新后的标签列表")


class LocalDockerStatusResponse(BaseModel):
    """本地Docker状态检测响应模型"""
    installed: bool = Field(..., description="Docker是否已安装")
    running: bool = Field(..., description="Docker守护进程是否运行中")
    socket_exists: bool = Field(..., description="/var/run/docker.sock 是否存在")
    version: Optional[str] = Field(None, description="Docker版本号")
    node_id: Optional[int] = Field(None, description="对应的本地Docker节点ID（如果已注册）")
    message: str = Field("", description="状态描述信息")
