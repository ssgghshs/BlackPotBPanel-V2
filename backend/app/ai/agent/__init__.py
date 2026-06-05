from app.ai.agent.tool_registry import AIToolRegistry, register_tool
from app.ai.agent.core import Agent

# 导入工具模块（触发生效 @register_tool 装饰器）
from app.ai.agent.tools import system_tools  # noqa: F401
from app.ai.agent.tools import log_tools  # noqa: F401
from app.ai.agent.memory import save_memory, recall_memory, list_memories, delete_memory  # noqa: F401

__all__ = ['AIToolRegistry', 'register_tool', 'Agent']
