from sqlalchemy import Column, Integer, String, DateTime, CheckConstraint
from config.database import Base
from config.settings import settings
from datetime import datetime, timezone
import os
import time
import pytz


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: get_localized_datetime())
    is_active = Column(Integer, default=1)
    role = Column(String, default="operator")
    __table_args__ = (
        CheckConstraint(role.in_(["admin", "auditor", "operator"]), name="role_check"),
    )
    
    def set_password(self, password: str):
        """设置用户密码"""
        from middleware.auth import get_password_hash
        self.hashed_password = get_password_hash(password)
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


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