"""
Toolset 定义 - 按黑锅面板功能分类的工具集

每个工具集对应面板的一个功能模块：
  - system        系统基础工具（始终可用）
  - system_monitor  系统监控（CPU/内存/磁盘/进程）
  - system_service  服务管理
  - file          文件操作
  - memory        记忆系统

每个工具集包含：
  - name: 显示名称
  - trigger_keywords: 触发关键词（用于意图路由自动匹配）
  - tools: 工具 ID 列表（对应 @register_tool 的 id 参数）
"""
from typing import Dict, List

# ==================== Toolset 定义 ====================

TOOLSETS: Dict[str, dict] = {
    'system': {
        'name': '基础系统',
        'trigger_keywords': [],
        'tools': [
            'request_user_input',
        ],
    },
    'shell': {
        'name': '命令执行',
        'trigger_keywords': [
            '执行', '命令', '运行', 'shell', 'bash', '终端', '命令行',
            '安装', '部署', '配置', '更新', '升级', '下载', '编译',
        ],
        'tools': [
            'execute_command',
        ],
    },
    'system_monitor': {
        'name': '系统监控',
        'trigger_keywords': [
            'cpu', '内存', '磁盘', '进程', '负载', '系统信息', '运行时间',
            '系统状态', '服务器状态', '资源', '性能', '硬件', '主机',
            '查看系统', '系统概况',
            'linux', 'uname', '内核', '发行版', '版本',
        ],
        'tools': [
            'get_system_info',
            'get_process_list',
            'get_disk_usage',
        ],
    },
    'system_service': {
        'name': '服务管理',
        'trigger_keywords': [
            '服务', 'nginx', 'mysql', 'redis', 'php', 'sshd', 'docker',
            '启动', '停止', '重启', '重载', '启用', '禁用',
            'systemctl', 'systemd', '服务状态', '查看服务',
            '列出服务', '所有服务', '服务列表', '服务名',
        ],
        'tools': [
            'manage_service',
            'list_services',
        ],
    },
    'file': {
        'name': '文件操作',
        'trigger_keywords': [
            '文件', '目录', '读取', '查看文件', '打开文件',
            '配置文件', '日志文件', 'nginx配置',
            '上传', '上传文件', '附件', '读文件', '阅读',
            'cat', '看', '读一读', '打开看看',
        ],
        'tools': [
            'read_file',
        ],
    },
    'memory': {
        'name': '记忆系统',
        'trigger_keywords': [
            '记住', '忘记', '记忆', '记得', '保存', '回忆',
            '记录', '存储', '回顾',
        ],
        'tools': [
            'save_memory',
            'recall_memory',
            'list_memories',
            'delete_memory',
        ],
    },
    'log': {
        'name': '日志查询',
        'trigger_keywords': [
            '日志', '登录日志', '系统日志', '访问日志', '错误日志',
            '攻击日志', 'waf日志', '查看日志', '查询日志',
            '登录记录', '失败登录', '登录失败',
            '排查', '故障', '异常',
        ],
        'tools': [
            'query_login_logs',
            'query_system_logs',
            'query_waf_attack_logs',
            'query_waf_access_logs',
            'query_waf_error_logs',
        ],
    },
}


# 联网搜索关键词（供意图路由使用）
WEB_SEARCH_KEYWORDS = [
    '搜索', '查询', '查找', '百度', '谷歌', 'google', 'bing',
    '最新', '新闻', '天气', '百科', '介绍',
    '搜索一下', '网上搜', '查一下',
]


def get_tools_for_toolset(toolset_id: str) -> List[str]:
    """获取指定工具集包含的工具 ID 列表"""
    ts = TOOLSETS.get(toolset_id)
    if ts:
        return ts.get('tools', [])
    return []


def get_toolset_names() -> List[str]:
    """获取所有工具集 ID"""
    return list(TOOLSETS.keys())


def get_all_tools_from_toolsets() -> List[str]:
    """获取所有工具集中定义的工具 ID（去重）"""
    all_tools = set()
    for ts in TOOLSETS.values():
        all_tools.update(ts.get('tools', []))
    return list(all_tools)
