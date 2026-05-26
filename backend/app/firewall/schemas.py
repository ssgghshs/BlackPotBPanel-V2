from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re


class FirewallInfoResponse(BaseModel):
    port: int = Field(..., description="端口规则总数(含系统+数据库)")
    ip: int = Field(..., description="IP规则总数(含系统+数据库)")
    trans: int = Field(..., description="端口转发规则总数")
    country: int = Field(..., description="地区限制规则总数")
    ping: bool = Field(..., description="是否允许Ping")
    status: bool = Field(..., description="防火墙运行状态")
    type: str = Field(..., description="防火墙类型: firewalld, ufw, iptables")


class FirewallSetStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(start|stop|restart|reload)$", description="操作: start, stop, restart, reload")


class FirewallSetPingRequest(BaseModel):
    status: str = Field(..., pattern="^(0|1)$", description="是否允许Ping: 0允许, 1禁止")


class PortRuleBase(BaseModel):
    port: str = Field(..., min_length=1, max_length=50, description="端口或端口范围，如 80 或 39000-40000")
    protocol: str = Field("tcp", pattern="^(tcp|udp|tcp/udp)$", description="协议: tcp, udp, tcp/udp")
    strategy: str = Field("accept", pattern="^(accept|drop|reject)$", description="策略: accept, drop, reject")
    address: str = Field("all", max_length=50, description="源地址, all表示所有")
    chain: str = Field("INPUT", pattern="^(INPUT|OUTPUT)$", description="链: INPUT, OUTPUT")
    brief: Optional[str] = Field(None, max_length=255, description="备注说明")

    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        rep = r"^\d{1,5}([:\-]\d{1,5})?$"
        if not re.search(rep, v):
            raise ValueError(f'端口格式不正确: {v}')
        return v


class PortRuleCreate(PortRuleBase):
    pass


class PortRuleUpdate(BaseModel):
    port: Optional[str] = Field(None, min_length=1, max_length=50, description="端口或端口范围")
    protocol: Optional[str] = Field(None, pattern="^(tcp|udp|tcp/udp)$", description="协议")
    strategy: Optional[str] = Field(None, pattern="^(accept|drop|reject)$", description="策略")
    address: Optional[str] = Field(None, max_length=50, description="源地址")
    chain: Optional[str] = Field(None, pattern="^(INPUT|OUTPUT)$", description="链")
    brief: Optional[str] = Field(None, max_length=255, description="备注说明")


class PortRuleResponse(PortRuleBase):
    id: int
    addtime: datetime

    class Config:
        from_attributes = True


class PortRuleList(BaseModel):
    items: List[PortRuleResponse]
    total: int
    skip: int
    limit: int


class MergedPortRuleItem(BaseModel):
    id: int = Field(0, description="数据库ID，0表示仅存在于系统防火墙中")
    port: str = Field(..., description="端口或端口范围")
    protocol: str = Field(..., description="协议")
    strategy: str = Field(..., description="策略")
    address: str = Field(..., description="源地址")
    chain: str = Field(..., description="链")
    brief: str = Field("", description="备注说明")
    addtime: str = Field("--", description="添加时间")
    status: int = Field(-1, description="-1:无法检测,0:未监听,2:监听中")
    stype: str = Field("0", description="0:系统原生规则,1:面板托管规则")


class MergedPortRuleList(BaseModel):
    items: List[MergedPortRuleItem]
    total: int
    skip: int
    limit: int


class IpRuleBase(BaseModel):
    address: str = Field(..., min_length=1, max_length=50, description="IP地址或CIDR")
    strategy: str = Field("drop", pattern="^(accept|drop|reject)$", description="策略: accept, drop, reject")
    chain: str = Field("INPUT", pattern="^(INPUT|OUTPUT)$", description="链: INPUT, OUTPUT")
    brief: Optional[str] = Field(None, max_length=255, description="备注说明")

    @field_validator('address')
    @classmethod
    def validate_address(cls, v):
        if v in ['0.0.0.0', '127.0.0.1', '::1']:
            raise ValueError(f'不允许屏蔽的地址: {v}')
        return v


class IpRuleCreate(IpRuleBase):
    pass


class IpRuleUpdate(BaseModel):
    address: Optional[str] = Field(None, min_length=1, max_length=50, description="IP地址或CIDR")
    strategy: Optional[str] = Field(None, pattern="^(accept|drop|reject)$", description="策略")
    chain: Optional[str] = Field(None, pattern="^(INPUT|OUTPUT)$", description="链")
    brief: Optional[str] = Field(None, max_length=255, description="备注说明")


class IpRuleResponse(IpRuleBase):
    id: int
    addtime: datetime

    class Config:
        from_attributes = True


class IpRuleList(BaseModel):
    items: List[IpRuleResponse]
    total: int
    skip: int
    limit: int


class MergedIpRuleItem(BaseModel):
    id: int = Field(0, description="数据库ID，0表示仅存在于系统防火墙中")
    address: str = Field(..., description="IP地址或CIDR")
    strategy: str = Field(..., description="策略")
    chain: str = Field(..., description="链")
    brief: str = Field("", description="备注说明")
    addtime: str = Field("--", description="添加时间")
    stype: str = Field("0", description="0:系统原生规则,1:面板托管规则")


class MergedIpRuleList(BaseModel):
    items: List[MergedIpRuleItem]
    total: int
    skip: int
    limit: int


class ForwardBase(BaseModel):
    S_Address: str = Field("0.0.0.0", max_length=50, description="源地址")
    S_Port: str = Field(..., min_length=1, max_length=10, description="源端口")
    T_Address: str = Field(..., min_length=1, max_length=50, description="目标地址")
    T_Port: str = Field(..., min_length=1, max_length=10, description="目标端口")
    Protocol: str = Field("tcp", pattern="^(tcp|udp)$", description="协议: tcp, udp")
    brief: Optional[str] = Field(None, max_length=255, description="备注说明")


class ForwardCreate(ForwardBase):
    pass


class ForwardUpdate(BaseModel):
    S_Address: Optional[str] = Field(None, max_length=50, description="源地址")
    S_Port: Optional[str] = Field(None, min_length=1, max_length=10, description="源端口")
    T_Address: Optional[str] = Field(None, min_length=1, max_length=50, description="目标地址")
    T_Port: Optional[str] = Field(None, min_length=1, max_length=10, description="目标端口")
    Protocol: Optional[str] = Field(None, pattern="^(tcp|udp)$", description="协议")
    brief: Optional[str] = Field(None, max_length=255, description="备注说明")


class ForwardResponse(ForwardBase):
    id: int
    addtime: str = Field("--", description="添加时间")

    class Config:
        from_attributes = True


class ForwardList(BaseModel):
    items: List[ForwardResponse]
    total: int
    skip: int
    limit: int


class FirewallOperationResponse(BaseModel):
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作消息")


class FirewallPortRuleDeleteRequest(BaseModel):
    id: int = Field(..., description="规则ID，0表示系统原生规则")
    port: str = Field(..., description="端口")
    protocol: str = Field("tcp", description="协议")
    chain: str = Field("INPUT", description="链")


class FirewallIpRuleDeleteRequest(BaseModel):
    id: int = Field(..., description="规则ID，0表示系统原生规则")
    address: str = Field(..., description="IP地址")
    strategy: str = Field("drop", description="策略")


class CountryInfo(BaseModel):
    country_code: str = Field(..., description="国家代码，如 US、CN")
    country_name: str = Field(..., description="国家中文名称")


class CountryRuleBase(BaseModel):
    country_codes: List[str] = Field(..., min_length=1, description="国家代码列表，如 ['US', 'GB']")
    strategy: str = Field("drop", pattern="^(accept|drop)$", description="策略: accept, drop")
    ports: str = Field("", description="端口，空表示所有端口，多个用逗号分隔")
    brief: Optional[str] = Field(None, max_length=255, description="备注说明")

    @field_validator('ports')
    @classmethod
    def validate_ports(cls, v):
        if not v:
            return ""
        port_list = v.split(',')
        rep = r"^\d{1,5}$"
        for port in port_list:
            port = port.strip()
            if port and not re.search(rep, port):
                raise ValueError(f'端口格式不正确: {port}')
        return v


class CountryRuleCreate(CountryRuleBase):
    pass


class CountryRuleUpdate(BaseModel):
    strategy: Optional[str] = Field(None, pattern="^(accept|drop)$", description="策略")
    ports: Optional[str] = Field(None, description="端口，空表示所有端口")
    brief: Optional[str] = Field(None, max_length=255, description="备注说明")

    @field_validator('ports')
    @classmethod
    def validate_ports(cls, v):
        if v is None:
            return v
        if v == "":
            return ""
        port_list = v.split(',')
        rep = r"^\d{1,5}$"
        for port in port_list:
            port = port.strip()
            if port and not re.search(rep, port):
                raise ValueError(f'端口格式不正确: {port}')
        return v


class CountryRuleResponse(BaseModel):
    id: int
    country_code: str
    country_name: str
    strategy: str
    ports: str
    brief: Optional[str] = None
    addtime: str = Field("--", description="添加时间")


class CountryRuleList(BaseModel):
    items: List[CountryRuleResponse]
    total: int
    skip: int
    limit: int


class CountryRuleDeleteRequest(BaseModel):
    id: int = Field(..., description="规则ID")
    country_code: str = Field(..., description="国家代码")
    strategy: str = Field("drop", description="策略")
    ports: str = Field("", description="端口")


class CountryRuleCreateResponse(BaseModel):
    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="提示信息")
    data: List[CountryRuleResponse] = Field(..., description="创建的规则列表")


class CountryRuleBatchDeleteItem(BaseModel):
    id: int = Field(..., description="规则ID")
    country_code: str = Field(..., description="国家代码")
    strategy: str = Field("drop", description="策略")
    ports: str = Field("", description="端口")


class CountryRuleBatchDeleteRequest(BaseModel):
    items: List[CountryRuleBatchDeleteItem] = Field(..., min_length=1, description="要删除的规则列表")
