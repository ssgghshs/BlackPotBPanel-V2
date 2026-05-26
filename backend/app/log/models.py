from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from config.database import Base
from datetime import datetime
from config.settings import settings
import pytz

class LoginLog(Base):
    __tablename__ = "login_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    username = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    login_time = Column(DateTime, default=lambda: get_localized_datetime())
    status = Column(String, nullable=False)  # success, failed
    location = Column(String, nullable=True)  # 添加地理位置字段
    
    def __repr__(self):
        return f"<LoginLog(id={self.id}, username='{self.username}', login_time='{self.login_time}')>"


def get_localized_datetime():
    """根据配置的时区获取本地化的时间"""
    try:
        # 获取配置的时区
        timezone_str = settings.TIMEZONE if hasattr(settings, 'TIMEZONE') else 'UTC'
        
        # 创建时区对象
        if timezone_str == 'UTC':
            tz = pytz.UTC
        else:
            tz = pytz.timezone(timezone_str)
        
        # 获取当前时间并本地化
        now = datetime.now(tz)
        return now
    except Exception as e:
        # 如果时区配置有问题，回退到UTC
        print(f"时区配置错误，使用UTC: {e}")
        return datetime.now(pytz.UTC)