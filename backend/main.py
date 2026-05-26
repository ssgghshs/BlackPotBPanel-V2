from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import config.settings
import os
import logging
import logging.config
from config.logging_config import LOGGING_CONFIG
import uvicorn
from app import create_app
# 导入初始化模块
from init.appinit import run_initialization


# 只在主进程中执行初始化操作
if __name__ == "__main__" and not os.environ.get("UVICORN_RELOAD_WORKER"):
    # 先初始化日志配置
    logging.config.dictConfig(LOGGING_CONFIG)
    # 再执行所有初始化操作
    run_initialization()


# 创建FastAPI应用实例
app = create_app()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许的源
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # 允许的方法
    allow_headers=["Authorization", "Content-Type"],  # 允许的头部
)


if __name__ == "__main__":
    # 初始化日志配置
    logging.config.dictConfig(LOGGING_CONFIG)
    
    # 构建Uvicorn配置
    uvicorn_config = {
        "app": "main:app",
        "host": config.settings.settings.HOST,
        "port": config.settings.settings.PORT,
        "reload": config.settings.settings.DEBUG,
        "reload_dirs": ["."],
        "reload_includes": ["*.py", "../setting.conf"],
        "log_config": LOGGING_CONFIG,
        "log_level": "info"
    }
    
    # 添加SSL配置（如果启用）
    if config.settings.settings.SSL_ENABLED:
        uvicorn_config.update({
            "ssl_certfile": config.settings.settings.SSL_CERT_PATH,
            "ssl_keyfile": config.settings.settings.SSL_KEY_PATH
        })
    
    # 为Uvicorn配置日志
    uvicorn.run(**uvicorn_config)