"""
AI 工具注册系统 (AIToolRegistry)

功能：
- @register_tool 装饰器，根据函数签名+docstring 自动生成 ToolDefinition
- execute(name, arguments) 执行已注册的工具
- get_openai_tools(enabled_ids) 生成 OpenAI function calling 格式列表
"""
import inspect
import json
import logging
from typing import Dict, Any, Callable, List, Optional, Union

from app.ai.provider.base import ToolDefinition

logger = logging.getLogger(__name__)


class AIToolRegistry:
    """工具注册中心（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, Callable] = {}
            cls._instance._definitions: Dict[str, ToolDefinition] = {}
            cls._instance._metadata: Dict[str, Dict[str, Any]] = {}
        return cls._instance

    # ---- 注册 ----

    def register_tool(self, tool_id: Union[str, Callable] = None, **kwargs):
        """
        装饰器：注册一个工具函数。
        用法:
            @register_tool(id='execute_command', category='system', name_cn='执行命令', risk_level='high')
            def execute_command(command: str) -> str:
                '''执行Shell命令。参数: command(要执行的命令)'''
                ...
        """
        if callable(tool_id):
            return self._register_func(tool_id, tool_id.__name__, kwargs)

        def decorator(func: Callable):
            final_id = tool_id if tool_id else func.__name__
            return self._register_func(func, final_id, kwargs)

        return decorator

    def _register_func(self, func: Callable, final_id: str, meta: Dict[str, Any]) -> Callable:
        name = func.__name__
        self._tools[name] = func

        schema = self._generate_schema(func)
        self._definitions[name] = ToolDefinition(
            name=name,
            description=schema['function']['description'],
            parameters=schema['function']['parameters'],
        )
        self._metadata[name] = {
            'id': final_id,
            'name': name,
            'name_cn': meta.get('name_cn', ''),
            'category': meta.get('category', 'default'),
            'risk_level': meta.get('risk_level', 'low'),
            'description': schema['function']['description'],
        }
        logger.debug(f'[ToolRegistry] 已注册工具: {name} (id={final_id})')
        return func

    # ---- 查询 ----

    def get_tool(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    def get_definition(self, name: str) -> Optional[ToolDefinition]:
        return self._definitions.get(name)

    def get_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        return self._metadata.get(name)

    def all_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def get_openai_tools(self, enabled_ids: List[str] = None) -> List[Dict[str, Any]]:
        """生成 OpenAI function calling 格式的工具列表"""
        result = []
        for name, defn in self._definitions.items():
            meta = self._metadata.get(name, {})
            if enabled_ids is not None:
                if meta.get('id', name) not in enabled_ids:
                    continue
            result.append({
                'type': 'function',
                'function': {
                    'name': defn.name,
                    'description': defn.description,
                    'parameters': defn.parameters,
                }
            })
        return result

    def get_all_tools_info(self) -> List[Dict[str, Any]]:
        """获取所有工具的元信息"""
        return [dict(m) for m in self._metadata.values()]

    # ---- 执行 ----

    def execute(self, name: str, arguments: Dict[str, Any]) -> str:
        """执行已注册的工具"""
        func = self.get_tool(name)
        if not func:
            return self._xml_error(f'工具 {name} 不存在')

        try:
            sig = inspect.signature(func)
            valid_kwargs = {}
            for pname, param in sig.parameters.items():
                if pname in ('self', 'cls'):
                    continue
                if param.kind in (inspect.Parameter.VAR_POSITIONAL,
                                  inspect.Parameter.VAR_KEYWORD):
                    continue
                if pname in arguments:
                    valid_kwargs[pname] = arguments[pname]
                elif param.default == inspect.Parameter.empty:
                    return self._xml_error(f'缺少必填参数: {pname}')

            result = func(**valid_kwargs)
            return self._xml_result(name, 'success', str(result))

        except Exception as e:
            logger.error(f'[ToolRegistry] 工具执行失败: {name}, args={arguments}, err={e}')
            return self._xml_error(f'执行失败: {str(e)}')

    # ---- Schema 生成 ----

    def _generate_schema(self, func: Callable) -> Dict[str, Any]:
        """从函数签名和 docstring 生成 OpenAI function schema"""
        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or ''
        description, param_descriptions = self._parse_docstring(doc)

        properties = {}
        required = []

        for pname, param in sig.parameters.items():
            if pname in ('self', 'cls'):
                continue
            if param.kind in (inspect.Parameter.VAR_POSITIONAL,
                              inspect.Parameter.VAR_KEYWORD):
                continue
            # 隐藏 session_id 参数（由系统自动注入）
            if pname == 'session_id':
                continue

            prop = {'type': 'string'}
            # 从类型提示推类型
            if param.annotation != inspect.Parameter.empty:
                type_map = {
                    str: 'string', int: 'integer', float: 'number',
                    bool: 'boolean', list: 'array', dict: 'object',
                }
                origin = getattr(param.annotation, '__origin__', None)
                if origin is list:
                    prop['type'] = 'array'
                    args = getattr(param.annotation, '__args__', None)
                    if args:
                        inner = type_map.get(args[0], 'string')
                        prop['items'] = {'type': inner}
                else:
                    prop['type'] = type_map.get(param.annotation, 'string')

            # 从 docstring 拿参数描述
            if pname in param_descriptions:
                prop['description'] = param_descriptions[pname]

            if param.default != inspect.Parameter.empty:
                prop['default'] = param.default
            else:
                required.append(pname)

            properties[pname] = prop

        schema = {
            'type': 'object',
            'properties': properties,
        }
        if required:
            schema['required'] = required

        return {
            'function': {
                'name': func.__name__,
                'description': description,
                'parameters': schema,
            }
        }

    @staticmethod
    def _parse_docstring(doc: str) -> (str, Dict[str, str]):
        """从 docstring 提取描述和参数说明"""
        if not doc:
            return '', {}

        parts = doc.split('参数:', 1)
        description = parts[0].strip()

        param_descriptions = {}
        if len(parts) > 1:
            param_text = parts[1].strip()
            for line in param_text.split(','):
                line = line.strip()
                if '(' in line and ')' in line:
                    name = line.split('(')[0].strip()
                    desc_start = line.find(')')
                    desc = line[desc_start + 1:].strip()
                    if name:
                        param_descriptions[name] = desc

        return description, param_descriptions

    # ---- XML 结果格式 ----

    @staticmethod
    def _xml_result(name: str, status: str, content: str) -> str:
        return (
            f'\n<tool>'
            f'\n<tool_name>{name}</tool_name>'
            f'\n<toolcall_status>{status}</toolcall_status>'
            f'\n<toolcall_result>'
            f'\n{content}'
            f'\n</toolcall_result>'
            f'\n</tool>\n'
        )

    @staticmethod
    def _xml_error(msg: str) -> str:
        return (
            f'\n<tool>'
            f'\n<tool_name>unknown</tool_name>'
            f'\n<toolcall_status>error</toolcall_status>'
            f'\n<toolcall_result>'
            f'\n{msg}'
            f'\n</toolcall_result>'
            f'\n</tool>\n'
        )


# 全局单例
registry = AIToolRegistry()
register_tool = registry.register_tool
