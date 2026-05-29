from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class SSHServiceAction(str, Enum):
    """SSH服务操作类型枚举"""
    START = "start"
    STOP = "stop"
    RESTART = "restart"

class HostBase(BaseModel):
    comment: Optional[str] = None
    address: str
    username: str
    port: int = 22
    # 不在API响应中直接暴露密码
    password: Optional[str] = None
    private_key: Optional[str] = None  # 添加私钥字段
    private_key_password: Optional[str] = None  # 添加私钥密码字段
    auth_method: str = "password"
    is_system_created: bool = False

class HostCreate(HostBase):
    pass

class HostUpdate(BaseModel):
    comment: Optional[str] = None
    address: Optional[str] = None
    username: Optional[str] = None
    port: Optional[int] = None
    password: Optional[str] = None
    private_key: Optional[str] = None  # 添加私钥字段
    private_key_password: Optional[str] = None  # 添加私钥密码字段
    auth_method: Optional[str] = None
    is_system_created: Optional[bool] = None

class HostInDB(HostBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class HostSimple(BaseModel):
    """主机简化模型，仅包含文件传输所需的字段"""
    id: int
    comment: Optional[str] = None
    address: str
    username: str
    port: int = 22

    class Config:
        from_attributes = True


# SSH配置信息相关的 Pydantic 模型
class SSHConfigInfo(BaseModel):
    install: bool  # 是否安装或存在
    status: bool  # 服务运行状态
    port: str  # 端口
    passwordAuthentication: str  # 密码认证
    pubkeyAuthentication: str  # 公钥认证
    permitRootLogin: str  # 允许root登录
    useDNS: str  # 控制SSH服务器是否启用DNS解析功能
    currentUser: str  # 当前用户


# SSH服务操作请求模型
class SSHServiceOperation(BaseModel):
    """SSH服务操作请求模型"""
    action: SSHServiceAction = Field(..., description="操作类型: start(启动), stop(停止), restart(重启)")


# SSH服务操作响应模型
class SSHServiceOperationResponse(BaseModel):
    """SSH服务操作响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作结果消息")
    status: bool = Field(..., description="操作后的服务状态")


# SSH配置更新请求模型
class SSHConfigUpdate(BaseModel):
    """SSH配置更新请求模型"""
    port: Optional[str] = Field(None, description="SSH服务端口")
    passwordAuthentication: Optional[str] = Field(None, description="密码认证状态")
    pubkeyAuthentication: Optional[str] = Field(None, description="公钥认证状态")
    permitRootLogin: Optional[str] = Field(None, description="允许root登录状态")
    useDNS: Optional[str] = Field(None, description="DNS解析功能状态")

# SSH配置文件响应模型
class SSHConfigFile(BaseModel):
    """SSH配置文件响应模型"""
    path: str = Field(..., description="SSH配置文件路径")
    content: str = Field(..., description="SSH配置文件内容")

# SSH authorized_keys文件响应模型
class SSHAuthKeysFile(BaseModel):
    """SSH authorized_keys文件响应模型"""
    path: str = Field(..., description="authorized_keys文件路径")
    content: str = Field(..., description="authorized_keys文件内容")

# HostCommand 相关的 Pydantic 模型
class HostCommandBase(BaseModel):
    name: str
    command: str

class HostCommandCreate(HostCommandBase):
    pass

class HostCommandUpdate(BaseModel):
    name: Optional[str] = None
    command: Optional[str] = None

class HostCommandInDB(HostCommandBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# SSH登录日志相关的 Pydantic 模型
class SSHLogQuery(BaseModel):
    """SSH登录日志查询参数模型"""
    skip: int = Field(default=0, description="跳过的记录数")
    limit: int = Field(default=100, description="返回的记录数")
    info: Optional[str] = Field(default=None, description="搜索关键字")
    status: Optional[str] = Field(default=None, description="登录状态筛选，可选值: success, failed")

class SSHLogEntry(BaseModel):
    """SSH登录日志条目模型"""
    timestamp: str = Field(..., description="登录时间")
    user: str = Field(..., description="登录用户")
    ip: str = Field(..., description="登录IP地址")
    port: str = Field(..., description="登录端口")
    status: str = Field(..., description="登录状态: success 或 failed")
    method: Optional[str] = Field(default=None, description="认证方式")
    area: Optional[str] = Field(default=None, description="IP归属地区")

class SSHLogResponse(BaseModel):
    """SSH登录日志列表响应模型"""
    total: int = Field(..., description="总记录数")
    items: List[SSHLogEntry] = Field(..., description="日志条目列表")

class SSHLogExportRequest(BaseModel):
    """SSH登录日志导出请求模型"""
    status: Optional[str] = Field(default=None, description="登录状态筛选，可选值: success, failed")
    export_format: str = Field(default="csv", description="导出格式: csv, excel")


class SSHLogCleanupRequest(BaseModel):
    """SSH登录日志清理请求模型"""
    before_date: Optional[datetime] = Field(default=None, description="清理此日期之前的日志")
    status: Optional[str] = Field(default=None, description="清理指定状态的日志，可选值: success, failed")
    keep_days: Optional[int] = Field(default=None, description="保留最近多少天的日志")


class SSHLogCleanupResponse(BaseModel):
    """SSH登录日志清理响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作结果消息")
    cleaned_count: Optional[int] = Field(default=None, description="已清理的日志数量")


# 远程文件相关 Pydantic 模型
class RemoteFileInfo(BaseModel):
    """远程主机文件信息模型"""
    filename: str = Field(..., description="文件名（符号链接格式为 name -> target）")
    size: str = Field(..., description="格式化后的文件大小，如 1.5 MB")
    is_directory: bool = Field(..., description="是否为目录")
    modified_time: str = Field(..., description="修改时间（ISO 格式）")
    permissions: str = Field(..., description="权限模式，如 755")
    user: str = Field(..., description="所有者用户名")
    group: str = Field(..., description="所属组名")
    is_symlink: bool = Field(..., description="是否为符号链接")
    target_path: str = Field(..., description="符号链接目标路径")
    path: str = Field(..., description="完整文件路径")

class RemoteFileListRequest(BaseModel):
    """远程文件列表请求模型"""
    path: str = Field(default="/", description="远程主机上的目录路径")

class RemoteFileListResponse(BaseModel):
    """远程文件列表响应模型"""
    data: List[RemoteFileInfo] = Field(..., description="文件列表")
    total: int = Field(..., description="文件总数")
    skip: int = Field(default=0, description="跳过的记录数")
    limit: int = Field(default=100, description="返回的记录数")


class RemoteFileCreateRequest(BaseModel):
    """远程主机创建文件/文件夹请求模型"""
    path: str = Field(..., description="父目录路径，如 /home/user")
    name: str = Field(..., description="文件或文件夹名称")
    type: str = Field(default="file", description="创建类型: file(文件) 或 directory(文件夹)")
    content: Optional[str] = Field(default="", description="文件内容（创建文件时可选）")


class RemoteFileCreateResponse(BaseModel):
    """远程主机创建文件/文件夹响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")


class RemoteFileDeleteRequest(BaseModel):
    """远程主机删除文件/文件夹请求模型"""
    path: str = Field(..., description="文件或文件夹的完整路径，如 /home/user/test.txt")
    type: str = Field(default="file", description="删除类型: file(文件) 或 directory(文件夹)")


class ScpTransferRequest(BaseModel):
    """SCP 文件传输请求模型"""
    direction: str = Field(default="upload", description="传输方向: upload(本地→远程) 或 download(远程→本地)")
    source_paths: List[str] = Field(..., description="源文件路径列表；upload 时为本地路径，download 时为远程路径")
    remote_dir: str = Field(..., description="目标目录路径；upload 时为远程目录，download 时为本地目录")


class ScpTransferTask(BaseModel):
    """SCP 传输任务状态模型"""
    task_id: str = Field(..., description="传输任务ID")
    status: str = Field(..., description="状态: pending/running/completed/failed/cancelled")
    progress: float = Field(0, description="总体进度 0-100")
    current_file: str = Field("", description="当前正在传输的文件名")
    total_files: int = Field(0, description="文件总数")
    completed_files: int = Field(0, description="已完成文件数")
    total_bytes: int = Field(0, description="总字节数")
    transferred_bytes: int = Field(0, description="已传输字节数")
    message: str = Field("", description="状态消息")


class HostResource(BaseModel):
    """主机资源占用信息"""
    id: int = Field(..., description="主机ID")
    cpu: float = Field(0, description="CPU使用率 (%)")
    cpu_usage: int = Field(0, description="CPU使用量 (核数)")
    memory: float = Field(0, description="内存使用率 (%)")
    mem_usage: int = Field(0, description="内存使用量 (MB)")
    disk: float = Field(0, description="磁盘使用率 (%)")
    disk_usage: int = Field(0, description="磁盘使用量 (GB)")