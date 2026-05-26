from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from config.database import ScriptBase  # 使用脚本数据库的基类
from config.settings import settings
from datetime import datetime
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


class ScriptType(ScriptBase):
    """
    脚本类型模型
    存储脚本类型和对应的解释器路径
    """
    __tablename__ = "script_types"
    
    id = Column(Integer, primary_key=True, index=True)
    type_name = Column(String(100), unique=True, nullable=False, index=True, comment="脚本类型名称")
    interpreter_path = Column(String(255), nullable=False, comment="脚本解释器路径")
    description = Column(Text, nullable=True, comment="类型描述")
    created_at = Column(DateTime(timezone=True), default=get_localized_datetime, comment="创建时间")
    
    # 建立与Script模型的一对多关系
    scripts = relationship("Script", back_populates="script_type", cascade="all, delete-orphan")


class Script(ScriptBase):
    """
    脚本模型
    存储脚本库中的脚本信息
    """
    __tablename__ = "scripts"
    
    script_id = Column(Integer, primary_key=True, index=True, comment="脚本ID")
    name = Column(String(255), nullable=False, index=True, comment="脚本名称")
    script_type_id = Column(Integer, ForeignKey("script_types.id"), nullable=False, comment="脚本类型ID")
    script_context = Column(Text, nullable=False, comment="脚本内容")
    description = Column(Text, nullable=True, comment="脚本描述")
    # 添加参数相关字段
    requires_params = Column(Boolean, default=False, comment="是否需要参数")
    params_description = Column(Text, nullable=True, comment="参数描述")
    created_at = Column(DateTime(timezone=True), default=get_localized_datetime, nullable=False, comment="创建时间")
    updated_at = Column(DateTime(timezone=True), default=get_localized_datetime, onupdate=get_localized_datetime, nullable=False, comment="更新时间")
    
    # 建立与ScriptType模型的多对一关系
    script_type = relationship("ScriptType", back_populates="scripts")
    
    def to_dict(self) -> dict:
        """将模型转换为字典"""
        # 安全地访问关系属性
        script_type_name = None
        interpreter_path = None
        
        # 只有在关系已加载时才访问
        if hasattr(self, 'script_type') and self.script_type is not None:
            try:
                script_type_name = self.script_type.type_name
                interpreter_path = self.script_type.interpreter_path
            except Exception:
                # 如果访问出错，不设置这些字段
                pass
        
        return {
            "script_id": self.script_id,
            "name": self.name,
            "script_type_id": self.script_type_id,
            "script_type": script_type_name,
            "interpreter_path": interpreter_path,
            "script_context": self.script_context,
            "description": self.description,
            "requires_params": self.requires_params,
            "params_description": self.params_description,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at is not None else None
        }


