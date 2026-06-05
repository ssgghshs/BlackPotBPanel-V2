"""
联网搜索工具

支持 5 家搜索服务商（按优先级尝试）：
  1. DuckDuckGo - 无需 API Key（免费）
  2. Bing Web Search API - 需要 API Key
  3. Serper API - 需要 API Key
  4. Tavily Search API - 需要 API Key
  5. SearXNG - 需要自建服务地址

依赖: httpx

配置方式（环境变量）：
  - AI_WEB_SEARCH_PROVIDER: 首选服务商（ddg/bing/serper/tavily/searxng）
  - AI_WEB_SEARCH_API_KEY: API Key
  - AI_WEB_SEARCH_API_BASE: 自定义搜索 API 地址（SearXNG 等）
"""
import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor

import httpx

from app.ai.agent.tool_registry import register_tool

logger = logging.getLogger(__name__)

# 全局线程池（复用，避免每次新建线程）
_SEARCH_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix='websearch')

# 搜索超时（秒）
HTTP_TIMEOUT = 5.0
GLOBAL_TIMEOUT = 8.0


# ==================== 搜索服务商实现 ====================


async def _search_duckduckgo(query: str, max_results: int = 5) -> str:
    """DuckDuckGo 搜索（无需 API Key，仅 API 接口，无 HTML 回退）"""
    try:
        url = 'https://api.duckduckgo.com/'
        params = {
            'q': query,
            'format': 'json',
            'no_html': 1,
            'skip_disambig': 1,
            't': 'blackpotbpanel-ai',
        }
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []

        abstract = data.get('AbstractText', '')
        if abstract:
            source = data.get('AbstractSource', '')
            results.append(f'📄 {abstract}\n  来源: {source}\n')

        related = data.get('RelatedTopics', [])
        for item in related[:max_results]:
            if 'Text' in item:
                results.append(f'• {item["Text"]}')
                if 'FirstURL' in item:
                    results[-1] += f'\n  {item["FirstURL"]}'
            elif 'Topics' in item:
                for sub in item['Topics'][:3]:
                    if 'Text' in sub:
                        results.append(f'• {sub["Text"]}')

        if not results:
            return '(DuckDuckGo 暂无相关结果)'

        return '\n\n'.join(results[:max_results])

    except httpx.TimeoutException:
        return '(DuckDuckGo 超时)'
    except Exception as e:
        logger.debug(f'DuckDuckGo 搜索失败: {e}')
        return '(DuckDuckGo 暂无结果)'


async def _search_bing(query: str, api_key: str, max_results: int = 5) -> str:
    """Bing Web Search API"""
    if not api_key:
        return '(Bing API Key 未配置)'
    try:
        url = 'https://api.bing.microsoft.com/v7.0/search'
        headers = {'Ocp-Apim-Subscription-Key': api_key}
        params = {'q': query, 'count': max_results, 'mkt': 'zh-CN'}
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get('webPages', {}).get('value', [])[:max_results]:
            results.append(f'• {item.get("name", "")}\n  {item.get("snippet", "")}\n  {item.get("url", "")}')
        return '\n\n'.join(results) if results else '(Bing 无结果)'
    except Exception as e:
        logger.debug(f'Bing 搜索失败: {e}')
        return '(Bing 搜索失败)'


async def _search_serper(query: str, api_key: str, max_results: int = 5) -> str:
    """Serper API（Google 搜索结果）"""
    if not api_key:
        return '(Serper API Key 未配置)'
    try:
        url = 'https://google.serper.dev/search'
        headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
        payload = {'q': query, 'num': max_results, 'gl': 'cn', 'hl': 'zh-cn'}
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get('organic', [])[:max_results]:
            results.append(f'• {item.get("title", "")}\n  {item.get("snippet", "")}\n  {item.get("link", "")}')
        return '\n\n'.join(results) if results else '(Serper 无结果)'
    except Exception as e:
        logger.debug(f'Serper 搜索失败: {e}')
        return '(Serper 搜索失败)'


async def _search_tavily(query: str, api_key: str, max_results: int = 5) -> str:
    """Tavily Search API"""
    if not api_key:
        return '(Tavily API Key 未配置)'
    try:
        url = 'https://api.tavily.com/search'
        payload = {
            'api_key': api_key, 'query': query, 'max_results': max_results,
            'search_depth': 'basic', 'include_answer': True,
        }
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        parts = []
        answer = data.get('answer', '')
        if answer:
            parts.append(f'📝 摘要: {answer}')
        for item in data.get('results', [])[:max_results]:
            parts.append(f'• {item.get("title", "")}\n  {item.get("content", "")}\n  {item.get("url", "")}')
        return '\n\n'.join(parts) if parts else '(Tavily 无结果)'
    except Exception as e:
        logger.debug(f'Tavily 搜索失败: {e}')
        return '(Tavily 搜索失败)'


async def _search_searxng(query: str, base_url: str, max_results: int = 5) -> str:
    """SearXNG 自建搜索引擎"""
    if not base_url:
        return '(SearXNG 地址未配置)'
    try:
        url = base_url.rstrip('/') + '/search'
        params = {'q': query, 'format': 'json', 'language': 'zh-CN', 'categories': 'general', 'pageno': 1}
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get('results', [])[:max_results]:
            results.append(f'• {item.get("title", "")}\n  {item.get("content", "")}\n  {item.get("url", "")}')
        return '\n\n'.join(results) if results else '(SearXNG 无结果)'
    except Exception as e:
        logger.debug(f'SearXNG 搜索失败: {e}')
        return '(SearXNG 搜索失败)'


# ==================== 配置读取 ====================


def _get_config() -> dict:
    return {
        'provider': os.environ.get('AI_WEB_SEARCH_PROVIDER', 'ddg'),
        'api_key': os.environ.get('AI_WEB_SEARCH_API_KEY', ''),
        'api_base': os.environ.get('AI_WEB_SEARCH_API_BASE', ''),
    }


# ==================== 异步执行器 ====================


async def _run_search(query: str, max_results: int) -> str:
    """执行搜索（纯异步，无线程切换开销）"""
    config = _get_config()
    provider = config.get('provider', 'ddg').lower()
    api_key = config.get('api_key', '')
    api_base = config.get('api_base', '')

    providers = {
        'ddg': _search_duckduckgo,
        'bing': lambda q, m: _search_bing(q, api_key, m),
        'serper': lambda q, m: _search_serper(q, api_key, m),
        'tavily': lambda q, m: _search_tavily(q, api_key, m),
        'searxng': lambda q, m: _search_searxng(q, api_base, m),
    }

    search_fn = providers.get(provider, _search_duckduckgo)

    try:
        result = await asyncio.wait_for(search_fn(query, max_results), timeout=GLOBAL_TIMEOUT)
        return result
    except asyncio.TimeoutError:
        logger.warning(f'[WebSearch] 搜索超时 ({GLOBAL_TIMEOUT}s): {query}')
        return f'(搜索超时，请稍后重试)'
    except Exception as e:
        logger.error(f'[WebSearch] 搜索异常: {e}')
        return f'(搜索失败: {str(e)})'


def _sync_run_search(query: str, max_results: int) -> str:
    """同步入口（在线程池中运行事件循环）"""
    try:
        return asyncio.run(_run_search(query, max_results))
    except Exception as e:
        logger.error(f'[WebSearch] 同步执行异常: {e}')
        return f'(搜索异常: {str(e)})'


# ==================== 注册工具 ====================


@register_tool(id='web_search', category='web_search', name_cn='联网搜索', risk_level='low')
def web_search(query: str, max_results: int = 5) -> str:
    """
    进行联网搜索，获取最新的网络信息。
    参数: query(搜索关键词), max_results(返回结果数，默认5)
    """
    logger.info(f'[WebSearch] 搜索: "{query[:50]}...", max_results={max_results}')

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # 没有运行中的事件循环，直接同步运行
        return _sync_run_search(query, max_results)

    # 有运行中的事件循环，用线程池执行（复用线程，避免新建开销）
    future = _SEARCH_EXECUTOR.submit(_sync_run_search, query, max_results)
    try:
        return future.result(timeout=GLOBAL_TIMEOUT + 2)
    except Exception as e:
        logger.error(f'[WebSearch] 线程池执行异常: {e}')
        return f'(搜索异常: {str(e)})'
