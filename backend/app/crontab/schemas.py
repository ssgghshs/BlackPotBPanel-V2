from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class CrontabTaskBase(BaseModel):
    name: str
    task_type: str
    command: str
    where1: Optional[int] = 0
    where_hour: Optional[int] = 0
    where_minute: Optional[int] = 0
    where_week: Optional[int] = 0
    status: Optional[int] = 1
    save: Optional[int] = 3
    description: Optional[str] = None


class CrontabTaskCreate(CrontabTaskBase):
    pass


class CrontabTaskUpdate(BaseModel):
    name: Optional[str] = None
    task_type: Optional[str] = None
    command: Optional[str] = None
    where1: Optional[int] = None
    where_hour: Optional[int] = None
    where_minute: Optional[int] = None
    where_week: Optional[int] = None
    status: Optional[int] = None
    save: Optional[int] = None
    description: Optional[str] = None


class CrontabTask(CrontabTaskBase):
    id: int
    echo: str
    last_run_time: Optional[datetime] = None
    last_result: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CrontabTaskRunResult(BaseModel):
    task_id: int
    name: str
    started_at: datetime
    output: str
    success: bool


class CrontabTaskLog(BaseModel):
    id: int
    task_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    output: Optional[str] = None
    success: bool
    duration: Optional[float] = None


class CrontabTaskListResponse(BaseModel):
    total: int
    items: List[CrontabTask]
    skip: int
    limit: int


class CrontabTypeInfo(BaseModel):
    type: str
    label: str
    description: str


CRONTAB_TYPES: List[CrontabTypeInfo] = [
    CrontabTypeInfo(type="day", label="每天", description="每天的指定小时分钟执行"),
    CrontabTypeInfo(type="day-n", label="每N天", description="每隔N天的指定小时分钟执行"),
    CrontabTypeInfo(type="hour", label="每小时", description="每小时的第N分钟执行"),
    CrontabTypeInfo(type="hour-n", label="每N小时", description="每隔N小时的第N分钟执行"),
    CrontabTypeInfo(type="minute-n", label="每N分钟", description="每隔N分钟执行一次"),
    CrontabTypeInfo(type="week", label="每周", description="每周指定天的指定时间执行"),
    CrontabTypeInfo(type="month", label="每月", description="每月指定天的指定时间执行"),
]
