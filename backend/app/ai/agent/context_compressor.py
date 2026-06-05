"""
上下文压缩 - 当对话历史超过 token 阈值时自动压缩旧消息

策略：
  1. 估算每条消息的 token 数（≈ 字符数 / 3.5，中英文混合）
  2. 如果总 token 数超过阈值（默认 4096），触发压缩
  3. 保留最新的 N 条消息（默认 10 条），将之前的消息压缩成一段摘要
  4. 将摘要作为 system 消息插入上下文
"""
import logging
from typing import List, Dict

from app.ai.provider.base import BaseLLMModel, ChatMessage

logger = logging.getLogger(__name__)

# 默认压缩阈值（token 数）
DEFAULT_MAX_TOKENS = 4096
# 保留的最新消息数
DEFAULT_KEEP_LATEST = 10
# 每个字符约等于的 token 数（中英文混合）
CHARS_PER_TOKEN = 3.5


def estimate_tokens(text: str) -> int:
    """估算文本的 token 数"""
    return int(len(text) / CHARS_PER_TOKEN) + 1


def estimate_messages_tokens(messages: List[ChatMessage]) -> int:
    """估算消息列表的总 token 数"""
    total = 0
    for m in messages:
        total += estimate_tokens(m.content or '')
        if m.role == 'system':
            total += 20  # system 标记开销
        elif m.role == 'user':
            total += 10
        elif m.role == 'assistant':
            total += 10
        elif m.role == 'tool':
            total += 15  # tool 消息有额外的 name 和 tool_call_id
    return total


async def compress_messages(
    messages: List[ChatMessage],
    llm: BaseLLMModel,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    keep_latest: int = DEFAULT_KEEP_LATEST,
) -> List[ChatMessage]:
    """
    压缩超过 token 阈值的消息列表。

    返回:
        压缩后的消息列表（如果无需压缩，返回原始列表）
    """
    if not messages:
        return messages

    total_tokens = estimate_messages_tokens(messages)
    if total_tokens <= max_tokens:
        logger.debug(f'[Context] 无需压缩: {total_tokens} tokens <= {max_tokens}')
        return messages

    logger.info(f'[Context] 触发压缩: {total_tokens} tokens > {max_tokens}')

    # 分离 system 消息和其他消息
    system_messages = [m for m in messages if m.role == 'system']
    non_system_messages = [m for m in messages if m.role != 'system']

    if len(non_system_messages) <= keep_latest:
        logger.debug(f'[Context] 非 system 消息不足 {keep_latest} 条，不压缩')
        return messages

    # 要压缩的部分（最早的）
    compress_part = non_system_messages[:-keep_latest]
    # 保留的最新部分
    keep_part = non_system_messages[-keep_latest:]

    # 生成摘要
    summary = await _summarize_messages(compress_part, llm)

    # 构建压缩后的消息列表：system(s) + 摘要(system) + 保留的部分
    compressed = list(system_messages)
    if summary:
        compressed.append(ChatMessage(
            role='system',
            content=f'[对话历史摘要]\n{summary}',
        ))
    compressed.extend(keep_part)

    compressed_tokens = estimate_messages_tokens(compressed)
    logger.info(f'[Context] 压缩完成: {total_tokens} → {compressed_tokens} tokens (减少 {(total_tokens - compressed_tokens) / total_tokens * 100:.0f}%)')

    return compressed


async def _summarize_messages(
    messages: List[ChatMessage],
    llm: BaseLLMModel,
) -> str:
    """用 LLM 将一批消息压缩成摘要"""
    if not messages:
        return ''

    # 组装摘要输入
    conversation_text = []
    for m in messages:
        if m.role == 'user':
            conversation_text.append(f'用户: {m.content[:200]}')
        elif m.role == 'assistant':
            conversation_text.append(f'助手: {m.content[:300]}')
        elif m.role == 'tool':
            # tool 结果太长，只取关键信息
            snippet = m.content[:100].replace('\n', ' ')
            conversation_text.append(f'工具[{m.name}]: {snippet}')
        elif m.role == 'system':
            conversation_text.append(f'系统: {m.content[:200]}')

    # 如果太长了就截断
    input_text = '\n'.join(conversation_text)
    if len(input_text) > 4000:
        input_text = input_text[:4000] + '\n...（后续内容省略）'

    prompt = (
        '你是一个对话摘要助手。请用中文总结以下对话中已经讨论过的核心内容。\n'
        '要求：\n'
        '1. 只提取关键信息，忽略客套话\n'
        '2. 如果涉及系统操作（命令执行、文件读写等），记录下执行了什么操作和结果\n'
        '3. 保持简洁，不超过 200 字\n'
        '4. 只输出摘要本身\n\n'
        f'{input_text}'
    )

    try:
        response = await llm.achat(
            messages=[ChatMessage(role='user', content=prompt)],
            temperature=0.3,
            max_tokens=300,
        )
        summary = response.content.strip()
        if summary:
            logger.debug(f'[Context] 摘要生成成功 ({len(summary)} 字符)')
            return summary
    except Exception as e:
        logger.warning(f'[Context] 摘要生成失败: {e}')

    # fallback: 简单拼接
    logger.debug('[Context] 使用 fallback 摘要')
    return _simple_summary(messages)


def _simple_summary(messages: List[ChatMessage]) -> str:
    """简单的 fallback 摘要"""
    user_count = sum(1 for m in messages if m.role == 'user')
    tool_count = sum(1 for m in messages if m.role == 'tool')
    tool_names = set()
    for m in messages:
        if m.role == 'tool' and m.name:
            tool_names.add(m.name)

    parts = [f'历史对话共 {user_count} 轮问答']
    if tool_names:
        parts.append(f'使用过工具: {", ".join(sorted(tool_names))}')
    return '；'.join(parts)
