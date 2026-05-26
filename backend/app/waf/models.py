from sqlalchemy import Column, Integer, String, DateTime, Boolean
from config.database import WafBase
from datetime import datetime, timezone
import pytz
from config.settings import settings


def get_localized_datetime():
    """根据配置的时区获取本地化的时间"""
    try:
        timezone_str = settings.TIMEZONE if hasattr(settings, 'TIMEZONE') else 'UTC'
        
        if timezone_str == 'UTC':
            tz = timezone.utc
        else:
            tz = pytz.timezone(timezone_str)
        
        now = datetime.now(tz)
        return now
    except Exception as e:
        print(f"时区配置错误，使用UTC: {e}")
        return datetime.now(timezone.utc)


class SSLCert(WafBase):
    """SSL证书模型"""
    __tablename__ = "ssl_certs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    domain = Column(String, nullable=True)
    issuer = Column(String, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: get_localized_datetime())
    updated_at = Column(DateTime, default=lambda: get_localized_datetime(), onupdate=lambda: get_localized_datetime())
    
    def __repr__(self):
        return f"<SSLCert(id={self.id}, name='{self.name}')>"


class ThreatIntelConfig(WafBase):
    """AbuseIPDB威胁情报平台API配置（全局单条记录）"""
    __tablename__ = "threat_intel_config"

    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String(255), nullable=False, default="", comment="API密钥")
    enabled = Column(Boolean, default=True, comment="是否启用")
    last_sync_time = Column(DateTime, nullable=True, default=None, comment="最后一次同步时间")
    synced_ip_count = Column(Integer, default=0, comment="已同步的恶意IP数量")
    created_at = Column(DateTime, default=lambda: get_localized_datetime())
    updated_at = Column(DateTime, default=lambda: get_localized_datetime(), onupdate=lambda: get_localized_datetime())

    def __repr__(self):
        return f"<ThreatIntelConfig(id={self.id}, enabled={self.enabled})>"
