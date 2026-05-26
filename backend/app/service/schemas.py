from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import datetime


from enum import Enum


class ProcessInfo(BaseModel):
    """进程信息模型"""
    pid: int  # 进程ID
    name: str  # 进程名称
    ppid: int  # 父进程PID
    threads: int  # 线程数
    user: str  # 用户
    status: str  # 状态
    cpu_percent: float  # CPU使用率
    memory_percent: float  # 内存使用率
    create_time: str  # 启动时间（格式：YYYY-MM-DD HH:MM:SS）


class ProcessListResponse(BaseModel):
    """进程列表响应模型"""
    processes: List[ProcessInfo]  # 进程列表
    total: int  # 进程总数


class ConnectionInfo(BaseModel):
    """连接信息模型（与1panel兼容）"""
    type: str
    status: str
    localaddr: Dict[str, Any]  # 对应1panel的Laddr
    remoteaddr: Dict[str, Any]  # 对应1panel的Raddr
    PID: int
    name: str


class NetworkConnectionInfo(BaseModel):
    """网络连接信息模型（简化格式）"""
    type: str  # 连接类型：tcp 或 udp
    pid: int  # 进程ID
    name: str  # 进程名称
    local_address: str  # 本地地址/端口
    remote_address: str  # 远程地址/端口
    status: str  # 连接状态


class NetworkConnectionListResponse(BaseModel):
    """网络连接列表响应模型"""
    connections: List[NetworkConnectionInfo]  # 网络连接列表
    total: int  # 连接总数


class ProcessDetailResponse(BaseModel):
    """进程详情响应模型（与1panel兼容）"""
    PID: int
    name: str
    PPID: int
    username: str
    status: str
    startTime: str
    numThreads: int
    numConnections: int
    cpuPercent: str
    diskRead: str
    diskWrite: str
    cmdLine: str
    rss: str
    vms: str
    hwm: str
    data: str
    stack: str
    locked: str
    swap: str
    cpuValue: float
    rssValue: int  # 从float改为int，与1panel一致
    envs: List[str]
    openFiles: List[Dict[str, Any]]
    connects: List[ConnectionInfo]



