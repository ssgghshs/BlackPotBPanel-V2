import os
from datetime import datetime

# 确保日志目录存在
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 获取今天的日期用于日志文件名
today = datetime.now().strftime("%Y-%m-%d")
log_filename = os.path.join(LOG_DIR, f"app_{today}.log")

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(asctime)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s %(asctime)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": log_filename,
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "formatter": "detailed",
            "encoding": "utf-8",
        },
        "access_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": log_filename,  # 使用相同的日志文件
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "formatter": "access",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["default", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["default", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["access", "access_file"],
            "level": "INFO",
            "propagate": False,
        },
        "app": {
            "handlers": ["default", "file"],
            "level": "INFO",
            "propagate": False,
        },
        # 添加FastAPI应用日志记录器
        "fastapi": {
            "handlers": ["default", "file"],
            "level": "INFO",
            "propagate": False,
        },
        # 添加应用模块日志记录器
        "app.log": {
            "handlers": ["default", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "app.user": {
            "handlers": ["default", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "app.system": {
            "handlers": ["default", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}