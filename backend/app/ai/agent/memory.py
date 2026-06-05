"""
记忆系统 - 会话级 KV 记忆存储

功能：
  1. 自动记忆：对话中自动提取关键信息注入 system prompt
  2. 手动记忆：Agent 通过工具 save_memory / recall_memory 读写记忆
  3. 持久化：使用线程安全的 dict 存储（后续可扩展为 DB 持久化）

使用方式：
  memory_engine = ConversationMemory()
  memory_engine.save(session_id, 'server_os', 'CentOS 7.9')
  mem = memory_engine.recall(session_id, 'server_os')
  all_mem = memory_engine.get_all(session_id)
"""
import json
import logging
import threading
from typing import Dict, List, Optional, Any

from app.ai.agent.tool_registry import register_tool

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    会话记忆引擎。
    每个 session_id 对应一个 dict，存储 key-value 记忆。
    线程安全。
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, str]] = {}
        self._lock = threading.Lock()

    def save(self, session_id: str, key: str, value: str) -> None:
        """保存一条记忆"""
        if not session_id or not key:
            return
        with self._lock:
            if session_id not in self._store:
                self._store[session_id] = {}
            self._store[session_id][key] = value
            logger.debug(f'[Memory] 保存: session={session_id}, key="{key}"')

    def recall(self, session_id: str, key: str) -> Optional[str]:
        """读取一条记忆"""
        if not session_id or not key:
            return None
        with self._lock:
            return self._store.get(session_id, {}).get(key)

    def get_all(self, session_id: str) -> Dict[str, str]:
        """获取该会话所有记忆"""
        if not session_id:
            return {}
        with self._lock:
            return dict(self._store.get(session_id, {}))

    def delete(self, session_id: str, key: str) -> bool:
        """删除一条记忆"""
        if not session_id or not key:
            return False
        with self._lock:
            if session_id in self._store and key in self._store[session_id]:
                del self._store[session_id][key]
                return True
            return False

    def clear(self, session_id: str) -> None:
        """清除该会话所有记忆"""
        if not session_id:
            return
        with self._lock:
            self._store.pop(session_id, None)

    def format_for_prompt(self, session_id: str, max_items: int = 20) -> str:
        """
        将记忆格式化为 system prompt 使用的文本。
        格式：
          [记忆]
          • key1: value1
          • key2: value2
        """
        memories = self.get_all(session_id)
        if not memories:
            return ''

        items = list(memories.items())[:max_items]
        lines = ['[记忆]']
        for k, v in items:
            # 值太长时截断
            display_v = v[:200].replace('\n', ' ') if v else ''
            lines.append(f'  • {k}: {display_v}')

        return '\n'.join(lines)

    def inject_into_system_prompt(self, session_id: str, system_prompt: str) -> str:
        """
        将记忆注入到 system prompt 中。
        如果没有记忆，返回原始 prompt。
        """
        memory_text = self.format_for_prompt(session_id)
        if not memory_text:
            return system_prompt
        return f'{system_prompt}\n\n{memory_text}'


# ==================== 全局单例 ====================

_global_memory = ConversationMemory()


def get_memory() -> ConversationMemory:
    """获取全局记忆引擎实例"""
    return _global_memory


# ==================== 注册工具 ====================


@register_tool(id='save_memory', category='system', name_cn='保存记忆', risk_level='low')
def save_memory(key: str, value: str, session_id: str = '') -> str:
    """
    保存一条持久化记忆。可用于记住用户的信息、偏好设置、关键配置等。
    参数: key(记忆的键名，如 "用户偏好语言"), value(记忆的值，如 "中文"), session_id(会话ID，由系统自动传入)
    """
    if not key or not value:
        return '参数错误：key 和 value 不能为空'

    # session_id 由调用方传入（Agent 的 session_id）
    actual_session_id = session_id or 'default'
    _global_memory.save(actual_session_id, key, value)

    count = len(_global_memory.get_all(actual_session_id))
    return f'已保存记忆: "{key}" = "{value}" (共 {count} 条记忆)'


@register_tool(id='recall_memory', category='system', name_cn='读取记忆', risk_level='low')
def recall_memory(key: str, session_id: str = '') -> str:
    """
    读取之前保存的持久化记忆。可以用于查询用户的信息、之前的配置等。
    参数: key(要查询的记忆键名，如 "用户偏好语言"), session_id(会话ID，由系统自动传入)
    """
    if not key:
        return '参数错误：key 不能为空'

    actual_session_id = session_id or 'default'
    value = _global_memory.recall(actual_session_id, key)

    if value is None:
        all_memories = _global_memory.get_all(actual_session_id)
        if all_memories:
            return f'未找到键 "{key}"。当前已有的记忆: {", ".join(all_memories.keys())}'
        return f'未找到键 "{key}"，暂无已保存的记忆。'

    return f'"{key}" = {value}'


@register_tool(id='list_memories', category='system', name_cn='列出所有记忆', risk_level='low')
def list_memories(session_id: str = '') -> str:
    """
    列出当前会话中所有已保存的记忆。
    参数: session_id(会话ID，由系统自动传入)
    """
    actual_session_id = session_id or 'default'
    all_mem = _global_memory.get_all(actual_session_id)

    if not all_mem:
        return '暂无已保存的记忆。'

    lines = [f'当前共 {len(all_mem)} 条记忆:']
    for k, v in all_mem.items():
        display_v = v[:100].replace('\n', ' ') if v else ''
        lines.append(f'  • {k}: {display_v}')
    return '\n'.join(lines)


@register_tool(id='delete_memory', category='system', name_cn='删除记忆', risk_level='low')
def delete_memory(key: str, session_id: str = '') -> str:
    """
    删除一条已保存的记忆。
    参数: key(要删除的记忆键名), session_id(会话ID，由系统自动传入)
    """
    if not key:
        return '参数错误：key 不能为空'

    actual_session_id = session_id or 'default'
    if _global_memory.delete(actual_session_id, key):
        return f'已删除记忆: "{key}"'
    return f'未找到键 "{key}"，删除失败。'
