from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
import re


class ScriptTypeBase(BaseModel):
    type_name: str
    interpreter_path: str
    description: Optional[str] = None


class ScriptTypeCreate(ScriptTypeBase):
    pass


class ScriptTypeUpdate(BaseModel):
    type_name: Optional[str] = None
    interpreter_path: Optional[str] = None
    description: Optional[str] = None


class ScriptTypeResponse(ScriptTypeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ScriptBase(BaseModel):
    name: str
    script_type_id: int
    script_context: str
    description: Optional[str] = None
    # 添加参数字段
    requires_params: Optional[bool] = False
    params_description: Optional[str] = None


class ScriptCreate(ScriptBase):
    pass


class ScriptUpdate(BaseModel):
    name: Optional[str] = None
    script_type_id: Optional[int] = None
    script_context: Optional[str] = None
    description: Optional[str] = None
    requires_params: Optional[bool] = None
    params_description: Optional[str] = None


class ScriptResponse(ScriptBase):
    script_id: int
    script_type: Optional[str] = None
    interpreter_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 添加脚本列表响应模型
class ScriptsResponse(BaseModel):
    items: List[ScriptResponse]
    total: int
    skip: int
    limit: int





