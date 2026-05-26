from sqlalchemy import Column, Integer, String, DateTime, Text, SmallInteger
from config.database import CrontabTaskBase
from datetime import datetime
from config.settings import settings
import pytz


def get_localized_datetime():
    try:
        timezone_str = settings.TIMEZONE if hasattr(settings, 'TIMEZONE') else 'UTC'
        if timezone_str == 'UTC':
            tz = pytz.UTC
        else:
            tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        return now
    except Exception as e:
        print(f"时区配置错误，使用UTC: {e}")
        return datetime.now(pytz.UTC)


class CrontabTask(CrontabTaskBase):
    __tablename__ = "crontab_tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, comment="任务名称")
    task_type = Column(String(16), nullable=False, comment="周期类型: day/day-n/hour/hour-n/minute-n/week/month")
    where1 = Column(Integer, default=0, comment="N值(每N天/小时/分钟)")
    where_hour = Column(Integer, default=0, comment="小时")
    where_minute = Column(Integer, default=0, comment="分钟")
    where_week = Column(Integer, default=0, comment="星期(0=周日,1-6)")
    command = Column(Text, nullable=False, comment="要执行的命令或脚本路径")
    status = Column(SmallInteger, default=1, comment="1启用 0停用")
    echo = Column(String(64), unique=True, index=True, comment="唯一标识，用作脚本文件名")
    save = Column(Integer, default=3, comment="日志保留条数")
    last_run_time = Column(DateTime, nullable=True, comment="上次执行时间")
    last_result = Column(String(256), nullable=True, comment="上次执行结果")
    description = Column(String(256), nullable=True, comment="备注描述")
    created_at = Column(DateTime, default=get_localized_datetime)
    updated_at = Column(DateTime, default=get_localized_datetime, onupdate=get_localized_datetime)

    def __repr__(self):
        return f"<CrontabTask(id={self.id}, name='{self.name}', type='{self.task_type}')>"
