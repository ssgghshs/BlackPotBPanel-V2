from pydantic import BaseModel
from datetime import datetime

class FileBase(BaseModel):
    filename: str
    size: int

class FileCreate(FileBase):
    pass

class File(FileBase):
    id: int
    filepath: str
    upload_time: datetime

    class Config:
        from_attributes = True

class FileInfo(BaseModel):
    """文件信息模型"""
    filename: str
    size: int
    is_directory: bool
    modified_time: datetime