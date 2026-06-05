"""
意图路由 - 自动匹配用户输入与 Toolset

功能：
  1. 关键词模糊匹配：用户输入命中 Toolset 的 trigger_keywords 则加载对应工具
  2. 精确指定：用户或配置指定 enabled_tools 列表
  3. 智能模式：结合以上两者，自动补充工具集
  4. 全量模式：所有工具可用
"""
import re
import logging
from typing import List, Optional

from app.ai.agent.toolsets import (
    TOOLSETS,
    WEB_SEARCH_KEYWORDS,
    get_all_tools_from_toolsets,
)

logger = logging.getLogger(__name__)


def resolve_tools(
    user_input: str,
    enabled_tools: Optional[List[str]] = None,
    smart_mode: bool = False,
) -> List[str]:
    """
    根据用户输入和配置，决定启用哪些工具。

    参数:
        user_input: 用户输入文本
        enabled_tools: 手动指定的工具 ID 列表（精确模式）
        smart_mode: 是否启用智能模式（关键词匹配补充工具）

    返回:
        工具 ID 列表（用于 AIToolRegistry.get_openai_tools）
    """
    # 1. 精确模式：直接使用指定工具
    if enabled_tools is not None and not smart_mode:
        logger.debug(f'[IntentRouter] 精确模式，启用 {len(enabled_tools)} 个工具')
        return enabled_tools

    # 2. 智能模式：关键词匹配 + 基础工具
    matched_tools = set()

    if smart_mode:
        matched_tools = _match_toolsets(user_input)
        # 智能模式下始终包含基础系统工具
        matched_tools.update(TOOLSETS.get('system', {}).get('tools', []))
        # 智能模式下自动判断是否需要联网搜索
        input_lower = user_input.lower()
        for kw in WEB_SEARCH_KEYWORDS:
            if kw.lower() in input_lower:
                matched_tools.add('web_search')
                logger.debug(f'[IntentRouter] 命中搜索关键词 "{kw}" → 启用 web_search')
                break
        logger.debug(f'[IntentRouter] 智能模式，关键词匹配到 {len(matched_tools)} 个工具')
    else:
        # 3. 默认模式：全量工具
        matched_tools = set(get_all_tools_from_toolsets())
        logger.debug(f'[IntentRouter] 默认模式，启用全部 {len(matched_tools)} 个工具')

    # 处理 enabled_tools
    if enabled_tools is not None:
        if smart_mode:
            # 智能模式：enabled_tools 作为补充（如联网搜索开关），不进行过滤
            matched_tools.update(set(enabled_tools))
            logger.debug(f'[IntentRouter] 智能模式，补充 enabled_tools，共 {len(matched_tools)} 个工具')
        else:
            # 默认模式：取交集（限制可用的工具范围）
            matched_tools &= set(enabled_tools)
            logger.debug(f'[IntentRouter] 与 enabled_tools 取交集，剩余 {len(matched_tools)} 个工具')

    return list(matched_tools)


def _match_toolsets(user_input: str) -> set:
    """关键词模糊匹配，返回匹配的工具集 ID"""
    matched = set()
    input_lower = user_input.lower()

    for ts_id, ts_info in TOOLSETS.items():
        keywords = ts_info.get('trigger_keywords', [])
        for kw in keywords:
            # 模糊匹配：关键词在用户输入中出现即可
            if kw.lower() in input_lower:
                matched.add(ts_id)
                logger.debug(f'[IntentRouter] 命中 "{kw}" → toolset "{ts_id}"')
                break  # 一个工具集只要命中一个关键词即可

    # 如果没有命中任何工具集，默认只启用系统工具
    if not matched:
        matched.add('system')

    # 根据匹配的工具集 ID，收集工具
    result = set()
    for ts_id in matched:
        ts_info = TOOLSETS.get(ts_id, {})
        result.update(ts_info.get('tools', []))

    return result
