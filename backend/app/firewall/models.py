from sqlalchemy import Column, Integer, String, Text, DateTime
from config.database import FirewallBase
from config.settings import settings
from datetime import datetime
import pytz

def get_localized_datetime():
    try:
        timezone_str = settings.TIMEZONE if hasattr(settings, 'TIMEZONE') else 'UTC'
        if timezone_str == 'UTC':
            tz = pytz.UTC
        else:
            tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        return now
    except Exception as e:
        print(f"时区配置错误，使用UTC: {e}")
        return datetime.now(pytz.UTC)


class FirewallRule(FirewallBase):
    __tablename__ = "firewall_rules"

    id = Column(Integer, primary_key=True, index=True)
    port = Column(String(50), nullable=False, index=True, comment="端口或端口范围，如 80 或 39000-40000")
    protocol = Column(String(10), nullable=False, default="tcp", comment="协议: tcp, udp, tcp/udp")
    strategy = Column(String(10), nullable=False, default="accept", comment="策略: accept, drop, reject")
    address = Column(String(50), nullable=False, default="all", comment="源地址, all表示所有")
    chain = Column(String(10), nullable=False, default="INPUT", comment="链: INPUT, OUTPUT")
    brief = Column(String(255), nullable=True, comment="备注说明")
    addtime = Column(DateTime, nullable=False, default=get_localized_datetime, comment="添加时间")

    def __repr__(self):
        return f"<FirewallRule(id={self.id}, port='{self.port}', protocol='{self.protocol}', strategy='{self.strategy}')>"


class FirewallIpRule(FirewallBase):
    __tablename__ = "firewall_ip_rules"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String(50), nullable=False, index=True, comment="IP地址或CIDR")
    strategy = Column(String(10), nullable=False, default="drop", comment="策略: accept, drop, reject")
    chain = Column(String(10), nullable=False, default="INPUT", comment="链: INPUT, OUTPUT")
    brief = Column(String(255), nullable=True, comment="备注说明")
    addtime = Column(DateTime, nullable=False, default=get_localized_datetime, comment="添加时间")

    def __repr__(self):
        return f"<FirewallIpRule(id={self.id}, address='{self.address}', strategy='{self.strategy}')>"


class FirewallForward(FirewallBase):
    __tablename__ = "firewall_forwards"

    id = Column(Integer, primary_key=True, index=True)
    S_Address = Column(String(50), nullable=False, default="0.0.0.0", comment="源地址")
    S_Port = Column(String(10), nullable=False, comment="源端口")
    T_Address = Column(String(50), nullable=False, comment="目标地址")
    T_Port = Column(String(10), nullable=False, comment="目标端口")
    Protocol = Column(String(10), nullable=False, default="tcp", comment="协议: tcp, udp")
    brief = Column(String(255), nullable=True, comment="备注说明")
    addtime = Column(DateTime, nullable=False, default=get_localized_datetime, comment="添加时间")

    def __repr__(self):
        return f"<FirewallForward(id={self.id}, {self.S_Port}->{self.T_Address}:{self.T_Port})>"


class FirewallCountryRule(FirewallBase):
    __tablename__ = "firewall_country_rules"

    id = Column(Integer, primary_key=True, index=True)
    country_code = Column(String(10), nullable=False, index=True, comment="国家代码，如 US、CN")
    country_name = Column(String(100), nullable=False, comment="国家名称")
    strategy = Column(String(10), nullable=False, default="drop", comment="策略: accept, drop")
    ports = Column(String(255), nullable=True, default="", comment="端口，空表示所有端口")
    brief = Column(String(255), nullable=True, comment="备注说明")
    addtime = Column(DateTime, nullable=False, default=get_localized_datetime, comment="添加时间")

    def __repr__(self):
        return f"<FirewallCountryRule(id={self.id}, country='{self.country_code}', strategy='{self.strategy}')>"
