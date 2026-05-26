from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class LoginLogBase(BaseModel):
    user_id: int
    username: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str
    location: Optional[str] = None  # 添加地理位置字段

class LoginLogCreate(LoginLogBase):
    pass

class LoginLog(LoginLogBase):
    id: int
    login_time: datetime
    
    class Config:
        from_attributes = True


# 访问日志相关的Schema
class AccessLogBase(BaseModel):
    access_log_path: str
    error_log_path: str

class AccessLogCreate(AccessLogBase):
    pass

class AccessLog(AccessLogBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True