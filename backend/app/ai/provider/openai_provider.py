import logging
from typing import Any, Dict, List, Optional, Generator, AsyncGenerator
import json
import httpx

import openai
from openai import OpenAI, AsyncOpenAI

from app.ai.provider.base import BaseAIProvider, BaseLLMModel, ModelConfig, ChatMessage, ChatResponse, ToolDefinition

logger = logging.getLogger(__name__)


class OpenAIModel(BaseLLMModel):
    """OpenAI 兼容模型实现"""

    def __init__(self, model_config: ModelConfig):
        super().__init__(model_config)
        timeout = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0)
        self.client = OpenAI(
            api_key=model_config.api_key,
            base_url=model_config.api_base or None,
            timeout=timeout,
            max_retries=1,
        )
        self.async_client = AsyncOpenAI(
            api_key=model_config.api_key,
            base_url=model_config.api_base or None,
            timeout=timeout,
            max_retries=1,
        )

    def _build_messages(self, messages: List[ChatMessage]) -> List[Dict]:
        """构建 OpenAI 消息格式"""
        result = []
        # 判断是否为 DeepSeek 模型（deepseek 的 thinking 模式需要 reasoning_content）
        is_deepseek = 'deepseek' in self.model_config.model_name.lower()
        for msg in messages:
            item = {'role': msg.role, 'content': msg.content}
            if msg.tool_calls:
                item['tool_calls'] = msg.tool_calls
            if msg.tool_call_id:
                item['tool_call_id'] = msg.tool_call_id
            if msg.name:
                item['name'] = msg.name
            # DeepSeek 的 thinking 模式严格要求传回 reasoning_content
            # 对于所有 assistant 消息，即使从 DB 加载的老消息没有该字段，也要确保存在
            if is_deepseek and msg.role == 'assistant':
                item['reasoning_content'] = msg.reasoning_content or ''
            elif msg.reasoning_content:
                item['reasoning_content'] = msg.reasoning_content
            result.append(item)
        return result

    def _get_kwargs(self, **kwargs) -> Dict:
        """获取请求参数"""
        params = {
            'model': self.model_config.model_name,
            'max_tokens': kwargs.get('max_tokens', self.model_config.max_tokens),
            'temperature': kwargs.get('temperature', self.model_config.temperature),
            'top_p': kwargs.get('top_p', self.model_config.top_p),
        }
        # 处理 tools（function calling）
        # 支持两种格式：
        #   1. ToolDefinition 对象列表
        #   2. 已经是 OpenAI 格式的 dict 列表（如 [{"type":"function","function":{...}}]）
        raw_tools = kwargs.get('tools')
        if raw_tools:
            if isinstance(raw_tools[0], ToolDefinition):
                params['tools'] = [
                    {
                        'type': 'function',
                        'function': {
                            'name': t.name,
                            'description': t.description,
                            'parameters': t.parameters,
                        }
                    }
                    for t in raw_tools
                ]
            else:
                # 已经是 dict 格式，直接透传
                params['tools'] = raw_tools
            logger.debug(f'_get_kwargs: tools={len(params["tools"])}个')
        # 去掉 None 值
        return {k: v for k, v in params.items() if v is not None}

    def chat(
        self,
        messages: List[ChatMessage],
        stream: bool = False,
        **kwargs
    ) -> ChatResponse:
        """非流式聊天"""
        openai_messages = self._build_messages(messages)
        params = self._get_kwargs(**kwargs)
        params['stream'] = False

        try:
            response = self.client.chat.completions.create(
                messages=openai_messages,
                **params
            )
        except openai.APIError as e:
            logger.error(f'OpenAI API 错误: {e}')
            raise

        choice = response.choices[0] if response.choices else None
        if not choice:
            return ChatResponse()

        delta = choice.message
        return ChatResponse(
            content=delta.content or '',
            tool_calls=[
                {
                    'id': tc.id,
                    'type': tc.type,
                    'function': {'name': tc.function.name, 'arguments': tc.function.arguments}
                }
                for tc in delta.tool_calls or []
            ],
            finish_reason=choice.finish_reason or '',
            usage={
                'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                'completion_tokens': response.usage.completion_tokens if response.usage else 0,
                'total_tokens': response.usage.total_tokens if response.usage else 0,
            }
        )

    def chat_stream(
        self,
        messages: List[ChatMessage],
        **kwargs
    ) -> Generator[ChatResponse, None, None]:
        """流式聊天（同步）"""
        openai_messages = self._build_messages(messages)
        params = self._get_kwargs(**kwargs)
        params['stream'] = True
        params['stream_options'] = {'include_usage': True}

        try:
            stream = self.client.chat.completions.create(
                messages=openai_messages,
                **params
            )
        except openai.APIError as e:
            logger.error(f'OpenAI API 流式错误: {e}')
            raise

        finish_reason = ''
        for chunk in stream:
            if not chunk.choices and chunk.usage:
                yield ChatResponse(
                    content='',
                    finish_reason='stop',
                    usage={
                        'prompt_tokens': chunk.usage.prompt_tokens or 0,
                        'completion_tokens': chunk.usage.completion_tokens or 0,
                        'total_tokens': chunk.usage.total_tokens or 0,
                    }
                )
                return

            choice = chunk.choices[0] if chunk.choices else None
            if not choice:
                continue

            delta = choice.delta
            content = delta.content or ''
            finish_reason = choice.finish_reason or ''

            tool_calls = []
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    tool_calls.append({
                        'id': tc.id,
                        'type': tc.type,
                        'function': {'name': tc.function.name, 'arguments': tc.function.arguments}
                    })

            yield ChatResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
            )

    async def achat(
        self,
        messages: List[ChatMessage],
        stream: bool = False,
        **kwargs
    ) -> ChatResponse:
        """异步非流式聊天"""
        openai_messages = self._build_messages(messages)
        params = self._get_kwargs(**kwargs)
        params['stream'] = False

        try:
            response = await self.async_client.chat.completions.create(
                messages=openai_messages,
                **params
            )
        except openai.APIError as e:
            logger.error(f'OpenAI API 异步错误: {e}')
            raise

        choice = response.choices[0] if response.choices else None
        if not choice:
            return ChatResponse()

        delta = choice.message
        return ChatResponse(
            content=delta.content or '',
            tool_calls=[
                {
                    'id': tc.id,
                    'type': tc.type,
                    'function': {'name': tc.function.name, 'arguments': tc.function.arguments}
                }
                for tc in delta.tool_calls or []
            ],
            finish_reason=choice.finish_reason or '',
            usage={
                'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                'completion_tokens': response.usage.completion_tokens if response.usage else 0,
                'total_tokens': response.usage.total_tokens if response.usage else 0,
            }
        )

    async def achat_stream(
        self,
        messages: List[ChatMessage],
        **kwargs
    ) -> AsyncGenerator[ChatResponse, None]:
        """异步流式聊天"""
        openai_messages = self._build_messages(messages)
        params = self._get_kwargs(**kwargs)
        params['stream'] = True
        params['stream_options'] = {'include_usage': True}

        try:
            stream = await self.async_client.chat.completions.create(
                messages=openai_messages,
                **params
            )
        except openai.APIError as e:
            logger.error(f'OpenAI API 异步流式错误: {e}')
            raise

        async for chunk in stream:
            if not chunk.choices and chunk.usage:
                yield ChatResponse(
                    content='',
                    finish_reason='stop',
                    usage={
                        'prompt_tokens': chunk.usage.prompt_tokens or 0,
                        'completion_tokens': chunk.usage.completion_tokens or 0,
                        'total_tokens': chunk.usage.total_tokens or 0,
                    }
                )
                return

            choice = chunk.choices[0] if chunk.choices else None
            if not choice:
                continue

            delta = choice.delta
            content = delta.content or ''
            finish_reason = choice.finish_reason or ''

            tool_calls = []
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    tool_calls.append({
                        'id': tc.id,
                        'type': tc.type,
                        'function': {'name': tc.function.name, 'arguments': tc.function.arguments}
                    })

            yield ChatResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
            )


class OpenAIProvider(BaseAIProvider):
    """OpenAI Provider"""

    def create_model(self, model_config: ModelConfig) -> OpenAIModel:
        return OpenAIModel(model_config)
