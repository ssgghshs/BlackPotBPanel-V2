"""
黑锅面板系统工具

包含面板运维常用的工具：
  1. get_system_info      系统概况（CPU/内存/磁盘/系统版本）
  2. get_process_list     进程列表与搜索
  3. get_disk_usage       磁盘分区详情
  4. manage_service       系统服务管理（启动/停止/重启/状态）
  5. execute_command      执行 Shell 命令（高风险）
  6. read_file            读取文件内容
  7. request_user_input   请求用户输入
"""
import json
import logging
import os
import subprocess

import psutil

from app.ai.agent.tool_registry import register_tool

logger = logging.getLogger(__name__)


# ==================== 系统监控工具 ====================


@register_tool(id='get_system_info', category='system_monitor', name_cn='系统概况', risk_level='low')
def get_system_info() -> str:
    """
    获取服务器系统概况信息，包括CPU使用率、内存使用率、磁盘使用率、系统版本、运行时间等。
    参数: 无
    """
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_cores = psutil.cpu_count(logical=False) or 1
        cpu_threads = psutil.cpu_count(logical=True) or 1
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)

        # 内存
        mem = psutil.virtual_memory()
        mem_total_gb = round(mem.total / (1024 ** 3), 2)
        mem_used_gb = round(mem.used / (1024 ** 3), 2)
        mem_percent = mem.percent

        # Swap
        try:
            swap = psutil.swap_memory()
            swap_total_gb = round(swap.total / (1024 ** 3), 2)
            swap_used_gb = round(swap.used / (1024 ** 3), 2)
        except Exception:
            swap_total_gb = 0
            swap_used_gb = 0

        # 磁盘
        disk_usage = psutil.disk_usage('/')
        disk_total_gb = round(disk_usage.total / (1024 ** 3), 2)
        disk_used_gb = round(disk_usage.used / (1024 ** 3), 2)
        disk_percent = disk_usage.percent

        # 系统信息
        import platform
        import socket
        boot_time_ts = psutil.boot_time()
        import datetime
        uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(boot_time_ts)
        uptime_days = uptime.days
        uptime_hours = uptime.seconds // 3600

        hostname = socket.gethostname()
        kernel = platform.release()

        lines = [
            f'📊 系统概况 ({hostname})',
            f'',
            f'系统版本: {platform.system()} {platform.release()} ({platform.machine()})',
            f'运行时间: {uptime_days} 天 {uptime_hours} 小时',
            f'',
            f'CPU: {cpu_cores}核/{cpu_threads}线程  使用率 {cpu_percent}%',
            f'负载: {load_avg[0]:.2f} / {load_avg[1]:.2f} / {load_avg[2]:.2f}',
            f'',
            f'内存: {mem_used_gb}GB / {mem_total_gb}GB ({mem_percent}%)',
            f'Swap: {swap_used_gb}GB / {swap_total_gb}GB',
            f'',
            f'磁盘(/): {disk_used_gb}GB / {disk_total_gb}GB ({disk_percent}%)',
        ]
        return '\n'.join(lines)

    except Exception as e:
        logger.error(f'get_system_info 失败: {e}')
        return f'[错误] 获取系统信息失败: {str(e)}'


@register_tool(id='get_process_list', category='system_monitor', name_cn='进程列表', risk_level='low')
def get_process_list(search: str = '', sort_by: str = 'cpu', limit: int = 20) -> str:
    """
    获取系统进程列表，可按关键词搜索和按 CPU/内存排序。
    参数: search(搜索关键词，按进程名模糊匹配，可选), sort_by(排序方式: cpu/memory/pid，默认cpu), limit(返回条数，默认20)
    """
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username', 'status']):
            try:
                pinfo = proc.info
                name = pinfo.get('name', '') or ''
                if search and search.lower() not in name.lower():
                    continue
                processes.append({
                    'pid': pinfo['pid'],
                    'name': name,
                    'cpu': pinfo.get('cpu_percent') or 0,
                    'mem': round(pinfo.get('memory_percent') or 0, 1),
                    'user': pinfo.get('username') or '?',
                    'status': pinfo.get('status') or '?',
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not processes:
            return f'未找到匹配的进程' + (f' (关键词: {search})' if search else '')

        # 排序
        if sort_by == 'memory' or sort_by == 'mem':
            processes.sort(key=lambda p: p['mem'], reverse=True)
        elif sort_by == 'pid':
            processes.sort(key=lambda p: p['pid'])
        else:  # cpu
            processes.sort(key=lambda p: p['cpu'], reverse=True)

        processes = processes[:limit]

        lines = [f'进程列表 (共 {len(processes)} 条):', '']
        lines.append(f'{"PID":<8} {"CPU%":<7} {"MEM%":<7} {"USER":<12} {"STATUS":<8} NAME')
        lines.append('-' * 80)
        for p in processes:
            lines.append(f'{p["pid"]:<8} {p["cpu"]:<7.1f} {p["mem"]:<7} {p["user"]:<12} {p["status"]:<8} {p["name"]}')

        return '\n'.join(lines)

    except Exception as e:
        logger.error(f'get_process_list 失败: {e}')
        return f'[错误] 获取进程列表失败: {str(e)}'


@register_tool(id='get_disk_usage', category='system_monitor', name_cn='磁盘使用情况', risk_level='low')
def get_disk_usage() -> str:
    """
    获取所有磁盘分区的使用情况，包括设备、挂载点、总大小、已用、可用、使用率。
    参数: 无
    """
    try:
        lines = ['磁盘分区使用情况:', '']

        # 排除的挂载点
        exclude_mounts = {'/proc', '/sys', '/dev', '/run', '/snap', '/boot'}
        # 识别的文件系统类型
        include_fstypes = {'ext2', 'ext3', 'ext4', 'xfs', 'btrfs', 'zfs', 'ntfs', 'fat32', 'vfat', 'exfat', 'nfs', 'nfs4', 'cifs'}

        partitions = []
        for part in psutil.disk_partitions(True):
            try:
                if part.mountpoint in exclude_mounts:
                    continue
                if part.mountpoint.startswith('/proc') or part.mountpoint.startswith('/sys'):
                    continue
                if part.fstype and part.fstype not in include_fstypes and part.mountpoint != '/':
                    if 'fuse' not in part.fstype:
                        continue

                usage = psutil.disk_usage(part.mountpoint)
                total_gb = round(usage.total / (1024 ** 3), 2)
                used_gb = round(usage.used / (1024 ** 3), 2)
                free_gb = round(usage.free / (1024 ** 3), 2)
                percent = usage.percent
                partitions.append({
                    'device': part.device,
                    'mount': part.mountpoint,
                    'fstype': part.fstype or '?',
                    'total': total_gb,
                    'used': used_gb,
                    'free': free_gb,
                    'percent': percent,
                })
            except (PermissionError, OSError):
                continue

        if partitions:
            lines.append(f'{"设备":<20} {"挂载点":<20} {"总大小":<8} {"已用":<8} {"可用":<8} {"使用率":<7} 类型')
            lines.append('-' * 90)
            for p in partitions:
                lines.append(
                    f'{p["device"]:<20} {p["mount"]:<20} '
                    f'{p["total"]:<8} {p["used"]:<8} {p["free"]:<8} '
                    f'{p["percent"]:<6.1f}% {p["fstype"]}'
                )

        # 汇总
        total_all = sum(p['total'] for p in partitions)
        used_all = sum(p['used'] for p in partitions)
        lines.append(f'\n总计: {round(total_all, 2)} GB  已用: {round(used_all, 2)} GB  使用率: {round(used_all / total_all * 100, 1) if total_all > 0 else 0}%')

        return '\n'.join(lines)

    except Exception as e:
        logger.error(f'get_disk_usage 失败: {e}')
        return f'[错误] 获取磁盘使用情况失败: {str(e)}'


# ==================== 服务管理工具 ====================


@register_tool(id='manage_service', category='system_service', name_cn='服务管理', risk_level='high')
def manage_service(action: str, service_name: str) -> str:
    """
    管理系统服务的运行状态。
    参数: action(操作类型: status/start/stop/restart/enable/disable), service_name(服务名称，如 nginx mysql sshd)
    """
    valid_actions = {'status', 'start', 'stop', 'restart', 'enable', 'disable'}
    if action not in valid_actions:
        return f'[错误] 不支持的操作: {action}，可用: {", ".join(sorted(valid_actions))}'

    try:
        # 构建 systemctl 命令
        cmd = ['systemctl', action, service_name]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if proc.returncode == 0:
            output = proc.stdout.strip() or proc.stderr.strip() or f'{action} {service_name} 成功'
            lines = [f'✅ {action} {service_name} 成功']
            if output:
                lines.append(output)
            return '\n'.join(lines)
        else:
            error = proc.stderr.strip() or '未知错误'
            return f'[失败] {action} {service_name}: {error}'

    except subprocess.TimeoutExpired:
        return f'[超时] {action} {service_name} 操作超时（30秒）'
    except FileNotFoundError:
        return '[错误] systemctl 命令不存在，可能不是 systemd 系统'
    except Exception as e:
        logger.error(f'manage_service 失败: {e}')
        return f'[错误] 服务管理失败: {str(e)}'


@register_tool(id='list_services', category='system_service', name_cn='列出系统服务', risk_level='low')
def list_services(search: str = '', state: str = '') -> str:
    """
    列出系统所有 systemd 服务及其运行状态。可按关键词搜索服务名，或按状态筛选。
    参数: search(搜索关键词，按服务名模糊匹配，可选), state(按状态筛选: running/exited/failed/active/inactive，可选)
    """
    try:
        cmd = ['systemctl', 'list-units', '--type=service', '--all', '--no-pager', '--plain']
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        if proc.returncode != 0:
            return f'[错误] 获取服务列表失败: {proc.stderr.strip() or "未知错误"}'

        lines = proc.stdout.split('\n')
        services = []
        started = False
        for line in lines:
            line = line.strip()
            if line.startswith('● ') or line.startswith('  '):
                continue
            # systemctl 输出格式: UNIT LOAD ACTIVE SUB DESCRIPTION
            parts = line.split(None, 4)
            if len(parts) >= 4 and parts[0].endswith('.service'):
                name = parts[0].replace('.service', '')
                active = parts[2]  # active / inactive
                sub = parts[3]     # running / exited / failed
                desc = parts[4] if len(parts) > 4 else ''
                services.append({
                    'name': name,
                    'active': active,
                    'sub': sub,
                    'desc': desc,
                })

        # 筛选
        if search:
            services = [s for s in services if search.lower() in s['name'].lower()]
        if state:
            state_lower = state.lower()
            services = [s for s in services if state_lower in s['sub'].lower() or state_lower in s['active'].lower()]

        if not services:
            msg = '未找到匹配的服务'
            if search:
                msg += f' (关键词: {search})'
            return msg

        # 排序：running 在前，其他的在后
        services.sort(key=lambda s: (0 if s['sub'] == 'running' else 1, s['name']))

        lines = [f'系统服务列表 (共 {len(services)} 个)', '']
        lines.append(f'{"状态":<8} {"服务名":<32} {"说明"}')
        lines.append('-' * 90)
        for s in services:
            status_icon = '🟢' if s['sub'] == 'running' else ('🔴' if s['sub'] == 'failed' else '⚪')
            status_text = s['sub'].ljust(6)
            name = s['name'][:30]
            desc = (s['desc'] or '')[:50]
            lines.append(f'{status_icon} {status_text:<6} {name:<32} {desc}')

        # 统计
        running_count = sum(1 for s in services if s['sub'] == 'running')
        failed_count = sum(1 for s in services if s['sub'] == 'failed')
        if running_count or failed_count:
            lines.append(f'\n📊 运行中: {running_count}  异常: {failed_count}  总计: {len(services)}')

        return '\n'.join(lines)

    except subprocess.TimeoutExpired:
        return '[超时] 获取服务列表超时（15秒）'
    except FileNotFoundError:
        return '[错误] systemctl 命令不存在，不是 systemd 系统'
    except Exception as e:
        logger.error(f'list_services 失败: {e}')
        return f'[错误] 获取服务列表失败: {str(e)}'


# ==================== 基础工具 ====================


@register_tool(id='execute_command', category='system', name_cn='执行命令', risk_level='high')
def execute_command(command: str, work_dir: str = '') -> str:
    """
    执行系统 Shell 命令。
    参数: command(要执行的命令), work_dir(工作目录，可选)
    """
    try:
        cwd = work_dir if work_dir and os.path.isdir(work_dir) else None

        proc = subprocess.run(
            ['sh', '-c', command],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        output = proc.stdout
        if proc.stderr:
            output += f'\n[STDERR]\n{proc.stderr}'
        if proc.returncode != 0:
            output = f'[exit code: {proc.returncode}]\n{output}'

        max_len = 10000
        if len(output) > max_len:
            output = output[:max_len] + f'\n\n...(输出过长，已截断，共 {len(output)} 字符)'

        return output.strip() or '(命令无输出)'

    except subprocess.TimeoutExpired:
        return '[错误] 命令执行超时（60秒）'
    except FileNotFoundError:
        return f'[错误] 命令不存在: {command}'
    except Exception as e:
        logger.error(f'execute_command 执行失败: {e}')
        return f'[错误] 执行失败: {str(e)}'


@register_tool(id='read_file', category='file', name_cn='读取文件', risk_level='low')
def read_file(path: str, max_length: int = 50000) -> str:
    """
    读取指定路径的文件内容。
    当用户上传了文件或提到了文件路径时，使用此工具读取文件内容进行分析。
    参数: path(文件完整路径), max_length(最大读取字符数，默认50000)
    """
    try:
        if not os.path.isfile(path):
            return f'[错误] 文件不存在: {path}'

        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(max_length)

        file_size = os.path.getsize(path)

        info = f'文件: {path} ({_format_size(file_size)})\n\n'
        if file_size > max_length:
            info += f'(仅显示前 {max_length} 字符，实际 {file_size} 字节)\n\n'

        return info + content

    except PermissionError:
        return f'[错误] 权限不足，无法读取: {path}'
    except Exception as e:
        logger.error(f'read_file 失败: {e}')
        return f'[错误] 读取失败: {str(e)}'


@register_tool(id='request_user_input', category='system', name_cn='请求用户输入', risk_level='low')
def request_user_input(prompt: str = '', fields: str = '') -> str:
    """
    向用户请求输入信息（如密码、确认等需要用户手动输入的场景）。
    参数: prompt(提示文本), fields(字段列表JSON，如 [{"name":"password","label":"密码","type":"password"}])
    """
    return f'[需要用户输入] {prompt}'


def _format_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f'{size_bytes:.1f} {unit}'
        size_bytes /= 1024
    return f'{size_bytes:.1f} TB'
