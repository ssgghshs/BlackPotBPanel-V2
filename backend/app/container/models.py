from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from config.database import ContainerBase
from config.settings import settings
from datetime import datetime
from typing import Optional, Dict, Any
import json
import pytz

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


class DockerNode(ContainerBase):
    """Docker节点模型
    支持管理本地Docker套接字和远程Docker节点（TCP或TCP+TLS）
    """
    __tablename__ = "docker_nodes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True, comment="节点名称")
    identifier = Column(String(100), nullable=True, index=True, comment="节点标识")
    description = Column(Text, nullable=True, comment="节点描述")
    
    # 连接信息
    endpoint_type = Column(String(20), nullable=False, comment="端点类型: unix_socket, tcp")
    endpoint_url = Column(String(500), nullable=False, comment="Docker API端点URL")
    use_tls = Column(Boolean, default=False, comment="是否启用TLS")
    
    # TLS认证信息（如果需要）
    ca_cert = Column(Text, nullable=True, comment="TLS CA证书路径")
    client_cert = Column(Text, nullable=True, comment="TLS客户端证书路径")
    client_key = Column(Text, nullable=True, comment="TLS客户端密钥路径")
    

    # Compose路径配置
    compose_path = Column(String(500), nullable=True, comment="Docker Compose文件路径")
    
    # 元数据
    created_at = Column(DateTime, nullable=False, default=get_localized_datetime, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=get_localized_datetime, onupdate=get_localized_datetime, comment="更新时间")
    
    def __repr__(self):
        return f"<DockerNode(id={self.id}, name='{self.name}', endpoint='{self.endpoint_url}')>"
    
    @property
    def connection_config(self) -> Dict[str, Any]:
        """获取Docker连接配置，用于Docker SDK初始化"""
        config = {
            'base_url': self.endpoint_url
        }
        
        # 如果启用了TLS，添加TLS配置
        if self.endpoint_type == 'tcp' and self.use_tls:
            tls_config = {}
            import os
            # 优先使用原始路径属性（如果存在），否则使用当前的ca_cert值（可能是路径或内容）
            ca_cert_path = getattr(self, '_original_ca_cert', self.ca_cert)
            client_cert_path = getattr(self, '_original_client_cert', self.client_cert)
            client_key_path = getattr(self, '_original_client_key', self.client_key)
            
            # 确保使用路径而不是内容
            if ca_cert_path and isinstance(ca_cert_path, str) and os.path.exists(ca_cert_path):
                tls_config['ca_cert_path'] = ca_cert_path
            if client_cert_path and isinstance(client_cert_path, str) and os.path.exists(client_cert_path):
                tls_config['client_cert_path'] = client_cert_path
            if client_key_path and isinstance(client_key_path, str) and os.path.exists(client_key_path):
                tls_config['client_key_path'] = client_key_path
            
            # 只有当有TLS配置时才添加tls参数
            if tls_config:
                config['tls'] = tls_config
        
        return config

