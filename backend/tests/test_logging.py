import logging
import logging.config
import asyncio
from config.logging_config import LOGGING_CONFIG

# 初始化日志配置
logging.config.dictConfig(LOGGING_CONFIG)

# 获取不同模块的日志记录器
root_logger = logging.getLogger()
app_logger = logging.getLogger("app")
uvicorn_logger = logging.getLogger("uvicorn.access")

# 测试日志输出
root_logger.info("Root logger test message")
app_logger.info("App logger test message")
uvicorn_logger.info("Uvicorn logger test message")

# 测试不同级别的日志
app_logger.debug("Debug message")
app_logger.info("Info message")
app_logger.warning("Warning message")
app_logger.error("Error message")

print("日志测试完成，检查日志文件是否生成")