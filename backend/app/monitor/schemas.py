from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any

class MonitorDataBase(BaseModel):
    metric_name: str
    value: int

class MonitorDataCreate(MonitorDataBase):
    pass

class MonitorData(MonitorDataBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

# CPU信息模型
class CPUInfo(BaseModel):
    cores: int
    load_avg: List[float]
    percent: float
    threads: int

# 磁盘信息模型
class DiskInfo(BaseModel):
    percent: float
    total: float
    used: float

# 内存信息模型
class MemoryInfo(BaseModel):
    percent: float
    total: float
    used: float

# 磁盘I/O信息模型
class DiskIOInfoDetail(BaseModel):
    busy_time: int
    read_bytes_per_sec: float
    read_count_per_sec: float
    write_bytes_per_sec: float
    write_count_per_sec: float

# 网络接口信息模型
class NetworkInterfaceInfo(BaseModel):
    bytes_recv_per_sec: float
    bytes_sent_per_sec: float
    packets_recv: int
    packets_sent: int

# 网络流量响应模型
class NetworkTrafficResponse(BaseModel):
    code: int
    data: Dict[str, Any]
    message: str

# 磁盘I/O响应模型
class DiskIOResponse(BaseModel):
    code: int
    data: Dict[str, Any]
    message: str

# 系统信息响应模型
class SystemInfoResponse(BaseModel):
    code: int
    data: dict
    message: str

class SystemInfo(BaseModel):
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    load_avg_1min: float
    load_avg_5min: float
    load_avg_15min: float
    timestamp: datetime

# 新增主机详细信息模型
class HostInfo(BaseModel):
    hostname: str
    platform: str
    platform_version: str
    architecture: str
    kernel_version: str
    ip_address: str
    boot_time: datetime
    uptime: int
    timestamp: datetime

# 新增网络流量监控模型
class NetworkTraffic(BaseModel):
    interface: str
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    timestamp: datetime

class NetworkTrafficInfo(BaseModel):
    interfaces: list[NetworkTraffic]
    timestamp: datetime

# 新增磁盘I/O监控模型
class DiskIO(BaseModel):
    device: str
    read_count: int
    write_count: int
    read_bytes: int
    write_bytes: int
    read_time: int
    write_time: int
    timestamp: datetime

class DiskIOInfo(BaseModel):
    disks: list[DiskIO]
    timestamp: datetime

# 新增磁盘I/O趋势数据模型
class DiskIOTrendData(BaseModel):
    device: str
    read_bytes: int
    write_bytes: int
    timestamp: datetime

class DiskIOTrendInfo(BaseModel):
    data: list[DiskIOTrendData]
    timestamp: datetime


class PanelResourceResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Dict[str, Any]