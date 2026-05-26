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