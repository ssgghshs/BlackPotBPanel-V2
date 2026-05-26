from pydantic import BaseModel
from typing import Dict, Optional

class EnvConfig(BaseModel):
    """环境配置模型"""
    DATABASE_URL: Optional[str] = None
    APP_NAME: Optional[str] = None
    VERSION: Optional[str] = None
    DEBUG: Optional[bool] = None
    SECRET_KEY: Optional[str] = None
    ALGORITHM: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: Optional[int] = None
    TIMEZONE: Optional[str] = None
    ENABLE_DOCS: Optional[bool] = None

class EnvConfigResponse(BaseModel):
    """环境配置响应模型"""
    configs: Dict[str, str]
    message: str

class ServiceRestartResponse(BaseModel):
    """服务重启响应模型"""
    message: str
    status: str