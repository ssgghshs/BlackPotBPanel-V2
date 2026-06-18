import os
import re
import logging
import logging.handlers
import datetime as dt


class DailyRotatingFileHandler(logging.FileHandler):
    """
    按日期动态切换日志文件的 Handler。

    与 TimedRotatingFileHandler 的区别：
    - TimedRotatingFileHandler 在午夜时会把当前文件重命名加后缀，再重建同名新文件
      导致文件名始终是服务启动当天的日期（如 app_2026-06-12.log 永远不变）
    - DailyRotatingFileHandler 在午夜时直接关闭旧文件、打开新的日期文件
      旧文件保持原名 app_2026-06-12.log，新文件为 app_2026-06-13.log
      文件名与内容日期始终一致，无需重命名
    """

    def __init__(self, log_dir, date_pattern="%Y-%m-%d",
                 file_template="app_{date}.log", backup_count=30, encoding="utf-8"):
        self.log_dir = log_dir
        self.date_pattern = date_pattern
        self.file_template = file_template
        self.backup_count = backup_count
        os.makedirs(log_dir, exist_ok=True)
        initial_filename = self._build_filename(dt.datetime.now())
        super().__init__(initial_filename, mode='a', encoding=encoding, delay=False)

    def _build_filename(self, dt_obj):
        return os.path.join(self.log_dir,
                            self.file_template.format(date=dt_obj.strftime(self.date_pattern)))

    def _get_current_date_str(self):
        return dt.datetime.now().strftime(self.date_pattern)

    def emit(self, record):
        try:
            current_filename = self._build_filename(dt.datetime.now())
            if self.stream and hasattr(self, 'baseFilename'):
                # 比较当前打开的文件名与今天应对应的文件名
                if os.path.abspath(self.baseFilename) != os.path.abspath(current_filename):
                    # 日期已变，执行轮转
                    if self.stream:
                        self.stream.close()
                        self.stream = None
                    self.baseFilename = current_filename
                    self._open()
                    # 轮转后清理过期旧文件
                    if self.backup_count > 0:
                        self._cleanup_old_files()
            super().emit(record)
        except Exception:
            self.handleError(record)

    def _cleanup_old_files(self):
        """删除超过 backup_count 天数的旧日志文件"""
        try:
            date_re = re.compile(
                re.escape(self.file_template).replace(
                    re.escape('{date}'), r'(\d{4}-\d{2}-\d{2})'
                )
            )
            matched_files = []
            for fname in os.listdir(self.log_dir):
                m = date_re.match(fname)
                if m:
                    matched_files.append((m.group(1), fname))
            # 按日期字符串升序（最旧在前）
            matched_files.sort(key=lambda x: x[0])
            # 删除超出保留数量的旧文件
            while len(matched_files) > self.backup_count:
                _, old_name = matched_files.pop(0)
                old_path = os.path.join(self.log_dir, old_name)
                try:
                    os.remove(old_path)
                except OSError:
                    pass
        except Exception:
            pass


# 确保日志目录存在
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 初始日志文件名（仅用于注释参考，实际由 DailyRotatingFileHandler 动态计算）
# app_YYYY-MM-DD.log —— routers.py 和 SystemLogs.vue 均依赖此命名模式

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
            "class": "config.logging_config.DailyRotatingFileHandler",
            "log_dir": LOG_DIR,
            "backup_count": 30,
            "formatter": "detailed",
            "encoding": "utf-8",
        },
        "access_file": {
            "class": "config.logging_config.DailyRotatingFileHandler",
            "log_dir": LOG_DIR,
            "backup_count": 30,
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