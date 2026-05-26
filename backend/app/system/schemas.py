from pydantic import BaseModel
from typing import Dict, Optional

class EnvConfigBase(BaseModel):
    """环境配置基础模型"""
    DATABASE_URL: Optional[str] = None
    APP_NAME: Optional[str] = None
    DEBUG: Optional[bool] = None
    VERSION: Optional[str] = None
    SECRET_KEY: Optional[str] = None
    ALGORITHM: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: Optional[int] = None
    TIMEZONE: Optional[str] = None
    ENABLE_DOCS: Optional[bool] = None
    LANGUAGE: Optional[str] = None
    THEME: Optional[str] = None
    LOGIN_NOTIFY: Optional[bool] = None
    HOST: Optional[str] = None
    PORT: Optional[int] = None
    SSL_ENABLED: Optional[bool] = None

class EnvConfigCreate(EnvConfigBase):
    """创建环境配置模型"""
    pass

class EnvConfigUpdate(EnvConfigBase):
    """更新环境配置模型"""
    pass

class EnvConfigInDB(EnvConfigBase):
    """数据库中的环境配置模型"""
    class Config:
        from_attributes = True

class EnvConfigResponse(BaseModel):
    """环境配置响应模型"""
    configs: Dict[str, str]
    message: str

class ServiceRestartResponse(BaseModel):
    """服务重启响应模型"""
    message: str
    status: str

class CommonSettingsUpdate(BaseModel):
    """通用设置更新模型"""
    LANGUAGE: Optional[str] = None
    THEME: Optional[str] = None
    LOGIN_NOTIFY: Optional[bool] = None
    RECYCLE: Optional[bool] = None

class CommonSettingsResponse(BaseModel):
    """通用设置响应模型"""
    LANGUAGE: str
    THEME: str
    LOGIN_NOTIFY: str
    RECYCLE: str

class RecycleConfigUpdate(BaseModel):
    """回收站配置更新模型"""
    RECYCLE: bool

class SSLCertUpdate(BaseModel):
    """SSL证书更新模型"""
    cert_content: Optional[str] = None
    key_content: Optional[str] = None

class SSLCertResponse(BaseModel):
    """SSL证书响应模型"""
    cert_content: Optional[str] = None
    key_content: Optional[str] = None
    message: str