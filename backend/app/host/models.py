from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from config.database import Base
from config.settings import settings
from datetime import datetime, timezone
import pytz

def get_localized_datetime():
    """根据配置的时区获取本地化的时间"""
    try:
        # 获取配置的时区
        timezone_str = settings.TIMEZONE if hasattr(settings, 'TIMEZONE') else 'UTC'
        
        # 创建时区对象
        if timezone_str == 'UTC':
            tz = timezone.utc
        else:
            tz = pytz.timezone(timezone_str)
        
        # 获取当前时间并本地化
        now = datetime.now(tz)
        return now
    except Exception as e:
        # 如果时区配置有问题，回退到UTC
        print(f"时区配置错误，使用UTC: {e}")
        return datetime.now(timezone.utc)

class Host(Base):
    __tablename__ = "hosts"
    
    id = Column(Integer, primary_key=True, index=True)
    comment = Column(String(255), nullable=True, comment="主机备注")
    address = Column(String(255), nullable=False, comment="主机地址")
    username = Column(String(100), nullable=False, comment="用户名")
    port = Column(Integer, nullable=False, default=22, comment="端口")
    password = Column(String(500), nullable=True, comment="加密后的密码")  # 增加长度以适应加密后的密码
    private_key = Column(Text, nullable=True, comment="私钥内容")  # 添加私钥字段
    private_key_password = Column(String(500), nullable=True, comment="私钥密码")  # 添加私钥密码字段
    created_at = Column(DateTime, default=get_localized_datetime, comment="创建时间")
    auth_method = Column(String(50), nullable=False, default="password", comment="认证方式")
    is_system_created = Column(Boolean, nullable=False, default=False, comment="是否为系统创建的记录")
    
    def __repr__(self):
        return f"<Host(id={self.id}, comment='{self.comment}', address='{self.address}')>"
 

class HostCommand(Base):
    __tablename__ = "host_commands"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="命令名称")
    command = Column(Text, nullable=False, comment="命令内容")
    created_at = Column(DateTime, default=get_localized_datetime, comment="创建时间")
    updated_at = Column(DateTime, default=get_localized_datetime, onupdate=get_localized_datetime, comment="更新时间")
    
    def __repr__(self):
        return f"<HostCommand(id={self.id}, name='{self.name}')>"