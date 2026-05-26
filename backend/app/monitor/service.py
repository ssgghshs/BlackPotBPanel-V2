from sqlalchemy.ext.asyncio import AsyncSession
from . import models, schemas
import psutil
import os
from datetime import datetime


def get_panel_resource() -> dict:
    """获取面板进程自身的资源占用情况"""
    process = psutil.Process(os.getpid())

    cpu_percent = process.cpu_percent(interval=0.5)

    memory_info = process.memory_info()
    memory_rss_mb = round(memory_info.rss / (1024 * 1024), 2)
    memory_vms_mb = round(memory_info.vms / (1024 * 1024), 2)
    memory_percent = process.memory_percent()

    total_memory = psutil.virtual_memory().total
    total_memory_mb = round(total_memory / (1024 * 1024), 2)

    num_threads = process.num_threads()

    try:
        num_fds = process.num_fds()
    except Exception:
        num_fds = 0

    return {
        "code": 200,
        "message": "success",
        "data": {
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(memory_percent, 2),
            "memory_rss_mb": memory_rss_mb,
            "memory_vms_mb": memory_vms_mb,
            "total_memory_mb": total_memory_mb,
            "num_threads": num_threads,
            "num_fds": num_fds
        }
    }
