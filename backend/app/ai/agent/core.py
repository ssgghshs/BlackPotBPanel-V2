"""
AI Agent 核心类

管理一次对话的函数调用循环：
  1. 组装 messages → 调用 LLM
  2. 若 LLM 返回 tool_calls → 执行工具 → 结果插回 messages → 继续
  3. 若 LLM 返回纯文本 → 结束

卡死检测（Orchestrator）：
  - 重复工具调用检测：同一工具连续调用 >= 3 次 → 打断
  - 无进展检测：连续多轮只有 tool_calls 没有生成 content → 打断
  - 全局超时：整个对话循环超过 timeout 秒 → 打断

yield 事件流（供 SSE 流式响应使用）：
  - reasoning       思考内容
  - content         文本内容（逐块）
  - tool_calls      工具调用声明
  - tool_confirm    危险操作确认（需用户确认后才执行）
  - tool_executing  工具执行中
  - tool_result     工具执行结果
  - stop            对话结束（含 usage）
  - error           错误
"""
import asyncio
import json
import logging
import time
from typing import Any, Dict, Generator, List, Optional

from app.ai.provider.base import (
    BaseLLMModel, ChatMessage, ChatResponse,
)
from app.ai.agent.tool_registry import AIToolRegistry

logger = logging.getLogger(__name__)

# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """你是一个 AI 黑锅面板运维助手，可以帮助用户回答问题、执行命令、读取文件等。

## 工具使用规则
1. 当需要执行命令、读取文件等操作时，使用提供的 function calling 工具
2. 工具执行后，基于工具返回结果给用户做总结
3. 如果工具返回错误，请尝试其他方式或告知用户
4. 日常对话直接回复，无需调用工具

## 文件上传处理
当用户上传文件或附件时，用户消息末尾会注明文件路径。
请使用 read_file 工具读取文件内容，然后根据内容回答用户的问题。
不要要求用户提供文件路径，路径已包含在消息中。"""

# 需要用户确认的高风险工具风险级别
HIGH_RISK_LEVELS = {'high'}

# 需要自动注入 session_id 的工具
_MEMORY_TOOL_NAMES = {'save_memory', 'recall_memory', 'list_memories', 'delete_memory'}

# 卡死检测配置
MAX_CONSECUTIVE_SAME_TOOL = 5    # 同一工具连续调用 N 次 → 打断
MAX_STALL_ITERATIONS = 4         # 连续 N 轮无内容产出 → 打断
GLOBAL_TIMEOUT_SECONDS = 180     # 全程超时秒数


class Agent:
    """AI Agent - 管理函数调用循环"""

    def __init__(
        self,
        session_id: str,
        model: BaseLLMModel,
        tool_registry: AIToolRegistry = None,
        config: Dict[str, Any] = None,
    ):
        self.session_id = session_id
        self.model = model
        self.tool_registry = tool_registry or AIToolRegistry()
        self.config = config or {}

        self.system_prompt = self.config.get('system_prompt', DEFAULT_SYSTEM_PROMPT)
        self.enabled_tools = self.config.get('enabled_tools', [])
        if not self.enabled_tools:
            self.enabled_tools = self.tool_registry.all_tool_names()

        self.max_tool_iterations = self.config.get('max_tool_iterations', 10)
        self.temperature = self.config.get('temperature', 0.7)
        self.max_tokens = self.config.get('max_tokens', 4096)

        self._stop_flag = False
        self._stall_count = 0
        self._last_tool_names: List[str] = []
        self._start_time: float = 0.0

        self._confirm_event = asyncio.Event()
        self._pending_confirm: Optional[dict] = None
        self._confirm_result: Optional[bool] = None

    # ---- 外部控制 ----

    def stop(self):
        """停止 Agent"""
        self._stop_flag = True
        # 如果有等待确认的操作，立即释放
        if self._pending_confirm:
            self._confirm_event.set()

    def is_stopped(self) -> bool:
        return self._stop_flag

    def reset_stop(self):
        self._stop_flag = False
        self._reset_confirm()

    def _reset_confirm(self):
        """重置确认状态"""
        self._pending_confirm = None
        self._confirm_result = None
        self._confirm_event.clear()

    def confirm_tool(self, call_id: str, confirmed: bool) -> bool:
        """
        用户对危险操作的确认结果。
        返回 True 表示确认已应用，False 表示没有等待该确认。
        """
        if not self._pending_confirm:
            logger.warning(f'[Agent] 没有等待确认的操作 (call_id={call_id})')
            return False

        if self._pending_confirm.get('call_id') != call_id:
            logger.warning(f'[Agent] call_id 不匹配: 期望 "{self._pending_confirm["call_id"]}", 收到 "{call_id}"')
            return False

        self._confirm_result = confirmed
        self._confirm_event.set()
        logger.info(f'[Agent] 用户确认工具执行: {call_id}, confirmed={confirmed}')
        return True

    async def _wait_for_confirm(self, timeout: float = 300.0) -> Optional[bool]:
        """等待用户确认，超时返回 False"""
        try:
            await asyncio.wait_for(self._confirm_event.wait(), timeout=timeout)
            return self._confirm_result
        except asyncio.TimeoutError:
            logger.warning(f'[Agent] 确认超时 (call_id={self._pending_confirm.get("call_id", "?")})')
            return False

    def _get_tool_risk_level(self, tool_name: str) -> str:
        meta = self.tool_registry.get_metadata(tool_name)
        if meta:
            return meta.get('risk_level', 'low')
        return 'low'

    def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """执行工具，自动注入 session_id 到记忆工具"""
        if tool_name in _MEMORY_TOOL_NAMES:
            arguments = {**arguments, 'session_id': self.session_id}
        return self.tool_registry.execute(tool_name, arguments)

    def _build_system_prompt(self) -> str:
        """构建 system prompt，注入记忆"""
        try:
            from app.ai.agent.memory import get_memory
            memory = get_memory()
            return memory.inject_into_system_prompt(self.session_id, self.system_prompt)
        except ImportError:
            return self.system_prompt
        except Exception as e:
            logger.debug(f'[Agent] 记忆注入失败: {e}')
            return self.system_prompt

    # ---- 卡死检测 ----

    def _check_stall(self, tool_name: str, iteration_content: str) -> Optional[str]:
        """
        卡死检测。
        返回打断原因（str）或 None（正常继续）。
        """
        # 1. 全局超时检测
        elapsed = time.time() - self._start_time
        if elapsed > GLOBAL_TIMEOUT_SECONDS:
            logger.warning(f'[Agent] 全局超时 {GLOBAL_TIMEOUT_SECONDS}s (session={self.session_id})')
            return f'对话超时（超过 {GLOBAL_TIMEOUT_SECONDS} 秒），已自动结束。如有需要，请重试。'

        # 2. 重复工具调用检测
        self._last_tool_names.append(tool_name)
        if len(self._last_tool_names) >= MAX_CONSECUTIVE_SAME_TOOL:
            recent = self._last_tool_names[-MAX_CONSECUTIVE_SAME_TOOL:]
            if len(set(recent)) == 1:
                logger.warning(f'[Agent] 重复工具调用检测: 连续 {MAX_CONSECUTIVE_SAME_TOOL} 次调用 "{tool_name}"')
                return f'检测到重复工具调用，已自动中断循环。请重新描述需求。'

        # 3. 无进展检测
        if not iteration_content:
            self._stall_count += 1
            if self._stall_count >= MAX_STALL_ITERATIONS:
                logger.warning(f'[Agent] 无进展检测: 连续 {MAX_STALL_ITERATIONS} 轮无内容生成')
                return f'AI 长时间未生成回答，已自动中断。请重新描述需求。'
        else:
            self._stall_count = 0

        return None

    # ---- 主循环 ----

    def chat(
        self,
        message: str,
        history: List[Dict[str, Any]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Agent 主循环（同步生成器）
        同步版本不支持 tool_confirm（高风险工具直接执行）
        """
        self.reset_stop()

        messages = [ChatMessage(role='system', content=self._build_system_prompt())]
        if history:
            for h in history:
                msg = ChatMessage(
                    role=h.get('role', 'user'),
                    content=h.get('content', ''),
                )
                if h.get('tool_calls'):
                    msg.tool_calls = h['tool_calls']
                if h.get('tool_call_id'):
                    msg.tool_call_id = h['tool_call_id']
                if h.get('name'):
                    msg.name = h['name']
                if h.get('reasoning_content'):
                    msg.reasoning_content = h['reasoning_content']
                messages.append(msg)

        messages.append(ChatMessage(role='user', content=message))

        tools = self.tool_registry.get_openai_tools(self.enabled_tools)
        has_tools = bool(tools)

        full_content = ''
        usage_info = {}

        for iteration in range(self.max_tool_iterations):
            if self._stop_flag:
                yield {'type': 'stop', 'usage': usage_info, 'reason': 'user_stopped'}
                return

            try:
                if has_tools:
                    response = self.model.chat(
                        messages=messages,
                        tools=tools,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                    )
                else:
                    response = self.model.chat(
                        messages=messages,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                    )
            except Exception as e:
                logger.error(f'Agent chat 调用 LLM 失败: {e}')
                yield {'type': 'error', 'content': f'AI 模型调用失败: {str(e)}'}
                return

            if response.usage:
                usage_info = response.usage

            if response.reasoning_content:
                yield {'type': 'reasoning', 'content': response.reasoning_content}

            if response.content:
                full_content += response.content
                yield {'type': 'content', 'content': response.content}

            if response.tool_calls:
                last_reasoning = response.reasoning_content or ''
                for tc in response.tool_calls[:10]:
                    tc_id = tc.get('id', '')
                    func_info = tc.get('function', {})
                    tool_name = func_info.get('name', '')
                    try:
                        arguments = json.loads(func_info.get('arguments', '{}'))
                    except json.JSONDecodeError:
                        arguments = {}

                    yield {'type': 'tool_calls', 'tool_calls': response.tool_calls}

                    # 同步版本：高风险工具直接执行（不等待确认）
                    yield {
                        'type': 'tool_executing',
                        'tool_name': tool_name,
                        'call_id': tc_id,
                        'arguments': arguments,
                    }

                    result = self._execute_tool(tool_name, arguments)

                    yield {
                        'type': 'tool_result',
                        'tool_name': tool_name,
                        'call_id': tc_id,
                        'result': result,
                    }

                    messages.append(ChatMessage(
                        role='assistant', content='', tool_calls=[tc],
                        reasoning_content=last_reasoning,
                    ))
                    messages.append(ChatMessage(
                        role='tool', content=result, tool_call_id=tc_id, name=tool_name,
                    ))

                continue

            break

        yield {
            'type': 'stop',
            'usage': usage_info,
            'finish_reason': response.finish_reason if hasattr(response, 'finish_reason') else '',
        }

    async def achat(
        self,
        message: str,
        history: List[Dict[str, Any]] = None,
    ):
        """
        异步版 Agent 主循环（async generator）
        支持 tool_confirm 事件（高风险工具需用户确认）
        """
        self.reset_stop()
        self._start_time = time.time()
        self._stall_count = 0
        self._last_tool_names = []

        messages = [ChatMessage(role='system', content=self.system_prompt)]
        if history:
            for h in history:
                msg = ChatMessage(
                    role=h.get('role', 'user'),
                    content=h.get('content', ''),
                )
                if h.get('tool_calls'):
                    msg.tool_calls = h['tool_calls']
                if h.get('tool_call_id'):
                    msg.tool_call_id = h['tool_call_id']
                if h.get('name'):
                    msg.name = h['name']
                messages.append(msg)

        messages.append(ChatMessage(role='user', content=message))

        tools = self.tool_registry.get_openai_tools(self.enabled_tools)
        has_tools = bool(tools)

        full_content = ''
        usage_info = {}

        for iteration in range(self.max_tool_iterations):
            if self._stop_flag:
                yield {'type': 'stop', 'usage': usage_info, 'reason': 'user_stopped'}
                return

            try:
                if has_tools:
                    logger.debug(f'[Agent] 发送 tools 给 LLM: {len(tools)}个工具')
                    response = await self.model.achat(
                        messages=messages,
                        tools=tools,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                    )
                else:
                    response = await self.model.achat(
                        messages=messages,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                    )
            except Exception as e:
                logger.error(f'Agent achat 调用 LLM 失败: {e}')
                yield {'type': 'error', 'content': f'AI 模型调用失败: {str(e)}'}
                return

            if response.usage:
                usage_info = response.usage

            if response.reasoning_content:
                yield {'type': 'reasoning', 'content': response.reasoning_content}

            if response.content:
                full_content += response.content
                yield {'type': 'content', 'content': response.content}

            if response.tool_calls:
                logger.debug(f'[Agent] LLM 返回 tool_calls: {len(response.tool_calls)}个')
                last_reasoning = response.reasoning_content or ''
                for tc in response.tool_calls[:10]:
                    tc_id = tc.get('id', '')
                    func_info = tc.get('function', {})
                    tool_name = func_info.get('name', '')
                    try:
                        arguments = json.loads(func_info.get('arguments', '{}'))
                    except json.JSONDecodeError:
                        arguments = {}

                    yield {'type': 'tool_calls', 'tool_calls': response.tool_calls}

                    # 卡死检测
                    iteration_content = response.content or ''
                    if iteration_content or len(response.tool_calls) > 0:
                        stall_reason = self._check_stall(tool_name, iteration_content)
                        if stall_reason:
                            logger.warning(f'[Agent] 卡死打断: {stall_reason}')
                            full_content += f'\n\n[{stall_reason}]'
                            yield {'type': 'content', 'content': f'\n\n[{stall_reason}]'}
                            yield {'type': 'stop', 'usage': usage_info, 'reason': 'stall_detected'}
                            return

                    # 检查是否需要用户确认
                    risk_level = self._get_tool_risk_level(tool_name)
                    if risk_level in HIGH_RISK_LEVELS:
                        # 需要用户确认
                        confirm_data = {
                            'tool_name': tool_name,
                            'call_id': tc_id,
                            'arguments': arguments,
                            'risk_level': risk_level,
                        }
                        self._pending_confirm = confirm_data
                        self._confirm_event.clear()
                        self._confirm_result = None

                        yield {
                            'type': 'tool_confirm',
                            **confirm_data,
                        }

                        # 等待用户确认
                        confirmed = await self._wait_for_confirm()

                        if not confirmed:
                            logger.info(f'[Agent] 用户拒绝执行高风险工具: {tool_name}')
                            message_text = f'[高风险操作已取消] {tool_name} 已被用户拒绝。'
                            full_content += message_text
                            yield {
                                'type': 'tool_result',
                                'tool_name': tool_name,
                                'call_id': tc_id,
                                'result': message_text,
                            }
                            # 将拒绝结果加入消息，告知 LLM
                            messages.append(ChatMessage(
                                role='assistant',
                                content='',
                                tool_calls=[tc],
                                reasoning_content=last_reasoning,
                            ))
                            messages.append(ChatMessage(
                                role='tool',
                                content=message_text,
                                tool_call_id=tc_id,
                                name=tool_name,
                            ))
                            continue

                    # 执行工具
                    yield {
                        'type': 'tool_executing',
                        'tool_name': tool_name,
                        'call_id': tc_id,
                        'arguments': arguments,
                    }

                    result = self._execute_tool(tool_name, arguments)

                    yield {
                        'type': 'tool_result',
                        'tool_name': tool_name,
                        'call_id': tc_id,
                        'result': result,
                    }

                    messages.append(ChatMessage(
                        role='assistant', content='', tool_calls=[tc],
                        reasoning_content=last_reasoning,
                    ))
                    messages.append(ChatMessage(
                        role='tool', content=result, tool_call_id=tc_id, name=tool_name,
                    ))

                continue

            break

        yield {
            'type': 'stop',
            'usage': usage_info,
            'finish_reason': response.finish_reason if hasattr(response, 'finish_reason') else '',
        }
