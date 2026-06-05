"""
面板日志查询与分析工具

日志来源：
  1. login_logs     登录日志（主数据库）
  2. system_logs    系统日志（/opt/blackpotbpanel-v2/backend/logs/）
  3. waf_access     网站访问日志（WAF_ACCESS_LOG_PATH）
  4. waf_error      WAF 错误日志（WAF_ERROR_LOG_PATH）
  5. waf_attack     WAF 拦截攻击日志（WAF_LOG_PATH）
"""
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Optional

from app.ai.agent.tool_registry import register_tool
from config.settings import settings

logger = logging.getLogger(__name__)

# WAF 日志路径（从 settings 读取）
WAF_LOG_PATH = settings.WAF_LOG_PATH
WAF_ACCESS_LOG_PATH = settings.WAF_ACCESS_LOG_PATH
WAF_ERROR_LOG_PATH = settings.WAF_ERROR_LOG_PATH

# 系统日志目录
SYSTEM_LOG_DIR = "/opt/blackpotbpanel-v2/backend/logs"

# 数据库路径（从 settings.DATABASE_URL 提取）
_DB_PATH = settings.DATABASE_URL.replace("sqlite:///", "")


# ==================== 数据库日志查询 ====================


def _query_login_logs(
    limit: int = 20,
    username: str = '',
    status: str = '',
    hours: int = 0,
) -> str:
    """查询登录日志（同步 SQLite 查询）"""
    import sqlite3
    try:
        db_path = _DB_PATH
        if not os.path.isfile(db_path):
            return f'[错误] 数据库文件不存在: {db_path}'

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        where_clauses = []
        params = []

        if username:
            where_clauses.append('username LIKE ?')
            params.append(f'%{username}%')
        if status:
            where_clauses.append('status = ?')
            params.append(status)
        if hours > 0:
            time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()
            where_clauses.append('login_time >= ?')
            params.append(time_threshold)

        where_sql = ''
        if where_clauses:
            where_sql = ' WHERE ' + ' AND '.join(where_clauses)

        sql = f'SELECT id, user_id, username, ip_address, status, login_time, location FROM login_logs{where_sql} ORDER BY login_time DESC LIMIT ?'
        params.append(limit)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            msg = '暂无登录日志'
            if username:
                msg += f' (用户: {username})'
            if status:
                msg += f' (状态: {status})'
            return msg

        lines = [f'📋 登录日志 (共 {len(rows)} 条):', '']
        lines.append(f'{"ID":<6} {"用户":<14} {"IP":<18} {"状态":<8} {"时间":<22} 位置')
        lines.append('-' * 100)

        for r in rows:
            loc = r['location'] or '-'
            lines.append(
                f'{r["id"]:<6} {r["username"]:<14} {r["ip_address"]:<18} '
                f'{r["status"]:<8} {r["login_time"]:<22} {loc}'
            )

        # 统计
        total = len(rows)
        success = sum(1 for r in rows if r['status'] == 'success')
        failed = total - success
        if total > 0:
            lines.append(f'\n📊 统计: 共 {total} 次  |  成功 {success} 次  |  失败 {failed} 次')

        return '\n'.join(lines)

    except Exception as e:
        logger.error(f'查询登录日志失败: {e}')
        return f'[错误] 查询登录日志失败: {str(e)}'


# ==================== 系统日志工具 ====================


def _read_latest_logs(
    log_dir: str,
    pattern: str = '*.log',
    limit: int = 50,
    keyword: str = '',
) -> str:
    """读取指定目录下最新的日志文件内容"""
    if not os.path.isdir(log_dir):
        return f'[错误] 日志目录不存在: {log_dir}'

    try:
        # 查找日志文件
        import glob
        log_files = glob.glob(os.path.join(log_dir, pattern))
        log_files = [f for f in log_files if os.path.isfile(f)]
        log_files.sort(key=os.path.getmtime, reverse=True)

        if not log_files:
            return f'未找到匹配的日志文件 ({log_dir}/{pattern})'

        lines = []
        total_read = 0

        for file_path in log_files:
            if total_read >= limit:
                break

            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))

            # 只读最后 200KB
            read_size = min(file_size, 200 * 1024)
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                if file_size > read_size:
                    f.seek(file_size - read_size)
                    # 跳到下一行开头
                    f.readline()

                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if keyword and keyword.lower() not in line.lower():
                        continue

                    if total_read >= limit:
                        break
                    lines.append(line)
                    total_read += 1

            if total_read > 0:
                break

        if not lines:
            return f'未找到匹配的日志' + (f' (关键词: {keyword})' if keyword else '')

        result = [f'📋 日志文件: {log_files[0] if len(log_files) == 1 else log_files[0] + " (最新)"}']
        if len(log_files) > 1:
            result[0] += f'\n   共 {len(log_files)} 个文件，显示最新 {len(lines)} 行'
        result.append('')
        result.extend(lines)

        return '\n'.join(result)

    except Exception as e:
        logger.error(f'读取日志失败: {e}')
        return f'[错误] 读取日志失败: {str(e)}'


# ==================== WAF 日志工具 ====================


def _parse_waf_log_line(line: str) -> Optional[dict]:
    """解析 WAF JSON 日志行"""
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def _read_waf_json_log(
    log_path: str,
    limit: int = 30,
    keyword: str = '',
    attack_type: str = '',
    hours: int = 0,
) -> str:
    """读取 WAF JSON 格式的日志文件"""
    if not os.path.isfile(log_path):
        return f'[错误] 日志文件不存在: {log_path}'

    try:
        entries = []
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = _parse_waf_log_line(line)
                if not entry:
                    continue

                # 过滤
                if keyword:
                    kw = keyword.lower()
                    if (kw not in (entry.get('client_ip', '') or '').lower()
                            and kw not in (entry.get('request_uri', '') or '').lower()
                            and kw not in (entry.get('attack_type', '') or '').lower()):
                        continue

                if attack_type:
                    if (entry.get('attack_type', '') or '').lower() != attack_type.lower():
                        continue

                if hours > 0:
                    ts = entry.get('timestamp', 0)
                    if ts < (datetime.now() - timedelta(hours=hours)).timestamp():
                        continue

                entries.append(entry)

        if not entries:
            return '未找到匹配的 WAF 日志条目' + (f' (类型: {attack_type})' if attack_type else '')

        # 按时间倒序
        entries.sort(key=lambda e: e.get('timestamp', 0), reverse=True)
        entries = entries[:limit]

        lines = [f'🛡️ WAF 日志 (显示最新 {len(entries)} 条):', '']
        for e in entries:
            ts = e.get('datetime', '') or datetime.fromtimestamp(e.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')
            client_ip = e.get('client_ip', '?')
            at = e.get('attack_type', '?')
            action = e.get('action', '?')
            uri = (e.get('request_uri', '') or '')[:60]
            method = e.get('request_method', '?')
            app = (e.get('application', '') or '')[:30]

            lines.append(f'[{ts}] {method} {uri}')
            lines.append(f'  IP: {client_ip}  攻击类型: {at}  动作: {action}')
            lines.append(f'  应用: {app}')
            lines.append('')

        # 统计
        if len(entries) > 1:
            types = {}
            for e in entries:
                t = e.get('attack_type', 'unknown')
                types[t] = types.get(t, 0) + 1
            stats = '  '.join(f'{k}: {v}次' for k, v in sorted(types.items(), key=lambda x: -x[1]))
            lines.append(f'📊 攻击类型分布: {stats}')

        return '\n'.join(lines)

    except Exception as e:
        logger.error(f'读取 WAF 日志失败: {e}')
        return f'[错误] 读取 WAF 日志失败: {str(e)}'


# ==================== 读取 Nginx/OpenResty 访问日志 ====================


def _parse_nginx_access_log(log_path: str, limit: int = 30, keyword: str = '') -> str:
    """解析 Nginx/OpenResty 标准访问日志"""
    if not os.path.isfile(log_path):
        return f'[错误] 日志文件不存在: {log_path}'

    try:
        file_size = os.path.getsize(log_path)
        read_size = min(file_size, 500 * 1024)  # 最多读 500KB

        lines = []
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            if file_size > read_size:
                f.seek(file_size - read_size)
                f.readline()  # 跳到下一行开头

            for line in f:
                line = line.strip()
                if not line:
                    continue
                if keyword and keyword.lower() not in line.lower():
                    continue
                lines.append(line)
                if len(lines) >= limit:
                    break

        if not lines:
            return '未找到匹配的访问日志' + (f' (关键词: {keyword})' if keyword else '')

        # 解析日志行
        result = [f'📋 访问日志 (最新 {len(lines)} 条):', '']
        # Nginx combined 格式: IP - - [date] "METHOD URI PROTO" STATUS SIZE "REFERER" "UA"
        log_pattern = re.compile(
            r'(\S+)\s+\S+\s+\S+\s+\[([^\]]+)\]\s+"([A-Z]+)\s+(\S+)\s+(\S+)"\s+(\d+)\s+(\d+)\s+"([^"]*)"\s+"([^"]*)"'
        )

        parsed_count = 0
        for line in lines:
            match = log_pattern.match(line)
            if match:
                ip, dt, method, uri, proto, status, size, referer, ua = match.groups()
                result.append(f'[{dt}] {method} {uri[:50]} → {status}  IP: {ip}')
                parsed_count += 1
            else:
                # 无法解析，显示原始行截断
                result.append(f'{line[:120]}')

        result.append(f'\n📊 共 {len(lines)} 条 | 成功解析 {parsed_count} 条')
        if keyword:
            result.append(f'筛选关键词: {keyword}')

        return '\n'.join(result)

    except Exception as e:
        logger.error(f'读取访问日志失败: {e}')
        return f'[错误] 读取访问日志失败: {str(e)}'


# ==================== 注册工具 ====================


@register_tool(id='query_login_logs', category='log', name_cn='登录日志查询', risk_level='low')
def query_login_logs(
    limit: int = 20,
    username: str = '',
    status: str = '',
    hours: int = 0,
) -> str:
    """
    查询面板登录日志，可按用户、状态、时间范围筛选。
    参数: limit(返回条数，默认20), username(按用户名筛选，可选), status(按状态筛选: success/failed), hours(仅查询最近N小时的日志，0表示不限)
    """
    return _query_login_logs(limit=limit, username=username, status=status, hours=hours)


@register_tool(id='query_system_logs', category='log', name_cn='系统日志查询', risk_level='low')
def query_system_logs(
    limit: int = 50,
    keyword: str = '',
    log_file: str = '',
) -> str:
    """
    查询后端系统运行日志，用于排查面板自身问题。
    参数: limit(返回行数，默认50), keyword(搜索关键词，可选), log_file(指定日志文件名，如 app.log error.log，默认自动选择最新)
    """
    pattern = f'*{log_file}' if log_file else '*.log'
    return _read_latest_logs(SYSTEM_LOG_DIR, pattern=pattern, limit=limit, keyword=keyword)


@register_tool(id='query_waf_attack_logs', category='log', name_cn='WAF攻击日志查询', risk_level='low')
def query_waf_attack_logs(
    limit: int = 30,
    attack_type: str = '',
    keyword: str = '',
    hours: int = 0,
) -> str:
    """
    查询 WAF 拦截的攻击日志，包括 SQL注入、XSS、CC攻击、爬虫等。
    参数: limit(返回条数，默认30), attack_type(按攻击类型筛选，如 sql/cc/bot/xss), keyword(搜索关键词，按IP或URI筛选), hours(仅查询最近N小时，0表示不限)
    """
    return _read_waf_json_log(WAF_LOG_PATH, limit=limit, keyword=keyword, attack_type=attack_type, hours=hours)


@register_tool(id='query_waf_access_logs', category='log', name_cn='WAF访问日志查询', risk_level='low')
def query_waf_access_logs(
    limit: int = 30,
    keyword: str = '',
) -> str:
    """
    查询 WAF 网站访问日志（Nginx/OpenResty 标准访问日志格式）。
    参数: limit(返回条数，默认30), keyword(搜索关键词，按IP或路径筛选)
    """
    return _parse_nginx_access_log(WAF_ACCESS_LOG_PATH, limit=limit, keyword=keyword)


@register_tool(id='query_waf_error_logs', category='log', name_cn='WAF错误日志查询', risk_level='low')
def query_waf_error_logs(
    limit: int = 30,
    keyword: str = '',
) -> str:
    """
    查询 WAF 错误日志（Nginx/OpenResty 错误日志）。
    参数: limit(返回条数，默认30), keyword(搜索关键词，可选)
    """
    return _read_latest_logs(
        os.path.dirname(WAF_ERROR_LOG_PATH) if WAF_ERROR_LOG_PATH else '',
        pattern=os.path.basename(WAF_ERROR_LOG_PATH) if WAF_ERROR_LOG_PATH else 'error.log',
        limit=limit,
        keyword=keyword,
    )
