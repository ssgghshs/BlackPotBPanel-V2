import time
import hmac
import hashlib
import logging
import psutil
import datetime
import socket
import platform
import subprocess
from typing import Optional, List, Dict, Any
from app.service.schemas import ProcessInfo, ProcessDetailResponse, ConnectionInfo, NetworkConnectionInfo

logger = logging.getLogger(__name__)

def get_process_list() -> List[ProcessInfo]:
    """获取系统进程信息列表"""
    process_list = []
    try:
        # 先获取所有进程的CPU使用率（需要两次采样）
        psutil.cpu_percent(interval=0.1, percpu=False)
        
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'create_time']):
            try:
                # 获取更详细的进程信息
                proc_info = proc.info
                proc_status = proc.status()
                proc_ppid = proc.ppid()
                proc_threads = len(proc.threads())
                
                # 重新获取进程的CPU使用率（确保有有效的采样）
                proc_cpu_percent = proc.cpu_percent(interval=None)
                
                # 将时间戳转换为指定格式的字符串：YYYY-MM-DD HH:MM:SS
                create_time_str = datetime.datetime.fromtimestamp(proc_info['create_time']).strftime('%Y-%m-%d %H:%M:%S')
                
                process_info = ProcessInfo(
                    pid=proc_info['pid'],
                    name=proc_info['name'],
                    ppid=proc_ppid,
                    threads=proc_threads,
                    user=proc_info.get('username', 'unknown'),
                    status=proc_status,
                    cpu_percent=proc_cpu_percent,
                    memory_percent=proc_info['memory_percent'],
                    create_time=create_time_str
                )
                process_list.append(process_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # 忽略无法访问的进程
                pass
    except Exception as e:
        logger.error(f"获取进程列表时出错: {e}")
    
    return process_list


def get_process_detail(pid: int) -> ProcessDetailResponse:
    """根据PID获取进程详细信息（与1panel兼容）"""
    try:
        # 获取进程对象
        proc = psutil.Process(pid)
        
        # 检查进程是否存在且正在运行
        if not proc.is_running():
            raise ValueError(f"进程 {pid} 未运行")
        
        # 获取进程基本信息
        proc_info = proc.as_dict(attrs=['pid', 'name', 'username', 'create_time'])
        
        # 获取CPU使用率 - 按照1panel的方式，只获取一次
        cpu_value = proc.cpu_percent(interval=0.1)
        cpu_percent = f"{cpu_value:.2f}%"
        
        # 格式化内存值 - 实现与1panel类似的格式化函数
        def format_bytes(bytes_value: int) -> str:
            if bytes_value < 1024:
                return f"{bytes_value} B"
            elif bytes_value < 1024 * 1024:
                return f"{bytes_value / 1024:.2f} KB"
            elif bytes_value < 1024 * 1024 * 1024:
                return f"{bytes_value / (1024 * 1024):.2f} MB"
            else:
                return f"{bytes_value / (1024 * 1024 * 1024):.2f} GB"
        
        # 获取内存信息
        memory_info = proc.memory_info()
        
        # 获取磁盘IO信息
        disk_read = "0 B"
        disk_write = "0 B"
        try:
            io_counters = proc.io_counters()
            disk_read = format_bytes(io_counters.read_bytes)
            disk_write = format_bytes(io_counters.write_bytes)
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
            pass
        
        # 获取连接信息 - 调整为获取所有类型的连接，并改进错误处理
        connections = []
        try:
            # 获取所有类型的连接（包括tcp, udp, unix等）
            for conn_type in ['inet', 'unix']:
                try:
                    proc_conns = proc.connections(kind=conn_type)
                    for conn in proc_conns:
                        # 格式化地址信息
                        localaddr = {}
                        if conn.laddr:
                            if hasattr(conn.laddr, 'ip') and hasattr(conn.laddr, 'port'):
                                # 处理inet类型连接（TCP/UDP）
                                localaddr = {"ip": conn.laddr.ip, "port": conn.laddr.port}
                            else:
                                # 处理其他类型连接（如unix套接字）
                                # 尝试获取地址字符串表示
                                addr_str = str(conn.laddr)
                                localaddr = {"address": addr_str}
                        
                        remoteaddr = {}
                        if conn.raddr:
                            if hasattr(conn.raddr, 'ip') and hasattr(conn.raddr, 'port'):
                                # 处理inet类型连接（TCP/UDP）
                                remoteaddr = {"ip": conn.raddr.ip, "port": conn.raddr.port}
                            else:
                                # 处理其他类型连接（如unix套接字）
                                # 尝试获取地址字符串表示
                                addr_str = str(conn.raddr)
                                remoteaddr = {"address": addr_str}
                        
                        # 确定连接类型字符串
                        type_str = 'tcp' if conn.type == 1 else 'udp' if conn.type == 2 else conn_type
                        
                        # 按照ConnectionInfo模型结构创建连接信息
                        conn_info = ConnectionInfo(
                            type=type_str,
                            status=conn.status if hasattr(conn, 'status') else 'NONE',
                            localaddr=localaddr,
                            remoteaddr=remoteaddr,
                            PID=pid,
                            name=proc_info['name']
                        )
                        connections.append(conn_info)
                except Exception:
                    # 如果某种类型的连接获取失败，继续尝试其他类型
                    continue
        except psutil.NoSuchProcess:
            # 进程不存在的情况
            pass
        except psutil.AccessDenied:
            # 权限被拒绝，但记录日志以便调试
            logger.warning(f"无权限获取进程 {pid} 的连接信息")
        except Exception as e:
            # 捕获其他可能的异常
            logger.error(f"获取进程 {pid} 连接信息时出错: {e}")
        
        # 获取环境变量
        envs = []
        try:
            envs = [f"{k}={v}" for k, v in proc.environ().items()]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        # 获取打开的文件 - 调整为更详细的格式，确保获取完整列表
        open_files = []
        try:
            # 首先尝试使用psutil的open_files()方法
            files = proc.open_files()
            for file in files:
                # 创建更详细的文件信息对象，包含fd（如果可用）
                file_info = {
                    "path": file.path,
                    "fd": getattr(file, 'fd', -1)  # 尝试获取文件描述符
                }
                open_files.append(file_info)
        except psutil.NoSuchProcess:
            # 进程不存在的情况
            pass
        except psutil.AccessDenied:
            # 权限被拒绝，但记录日志以便调试
            logger.warning(f"无权限获取进程 {pid} 的打开文件列表")
        except AttributeError:
            # 某些平台可能不支持此功能
            pass
        except Exception as e:
            # 捕获其他可能的异常
            logger.error(f"获取进程 {pid} 打开文件时出错: {e}")
        
        # 在Linux系统上，尝试直接读取/proc/{pid}/fd目录获取完整的文件描述符列表
        # 这可以获取psutil.open_files()可能遗漏的套接字、管道等
        try:
            import os
            import re
            
            # 构建/proc/{pid}/fd目录路径
            fd_dir = f"/proc/{pid}/fd"
            
            # 检查目录是否存在
            if os.path.isdir(fd_dir):
                # 存储已存在的文件路径，避免重复
                existing_paths = {f["path"] for f in open_files}
                
                # 遍历/proc/{pid}/fd目录中的所有文件描述符
                for fd_name in os.listdir(fd_dir):
                    try:
                        fd_path = os.path.join(fd_dir, fd_name)
                        # 读取符号链接目标
                        if os.path.islink(fd_path):
                            target = os.readlink(fd_path)
                            # 只有当这个文件路径不存在于现有列表中时才添加
                            if target not in existing_paths:
                                # 尝试将fd_name转换为整数
                                fd = int(fd_name)
                                file_info = {
                                    "path": target,
                                    "fd": fd
                                }
                                open_files.append(file_info)
                                existing_paths.add(target)
                    except (OSError, ValueError) as e:
                        # 忽略无法访问的文件描述符
                        continue
        except Exception as e:
            # 捕获所有异常，但不影响主要功能
            logger.debug(f"尝试通过/proc目录获取进程 {pid} 文件描述符时出错: {e}")
        
        # 获取启动时间 - 保持与1panel相同的格式
        start_time_str = datetime.datetime.fromtimestamp(proc_info['create_time']).strftime('%Y-%m-%d %H:%M:%S')
        
        # 获取命令行
        cmd_line = ''
        try:
            cmd_line = ' '.join(proc.cmdline()) if proc.cmdline() else ''
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        # 获取线程数
        num_threads = len(proc.threads())
        
        # 获取进程状态
        status = proc.status()
        
        # 构造响应对象 - 按照1panel的字段顺序和类型
        detail_response = ProcessDetailResponse(
            PID=pid,
            name=proc_info['name'],
            PPID=proc.ppid(),
            username=proc_info.get('username', 'unknown'),
            status=status,
            startTime=start_time_str,
            numThreads=num_threads,
            numConnections=len(connections),
            cpuPercent=cpu_percent,
            diskRead=disk_read,
            diskWrite=disk_write,
            cmdLine=cmd_line,
            rss=format_bytes(memory_info.rss),
            vms=format_bytes(memory_info.vms),
            hwm=format_bytes(getattr(memory_info, 'hwm', memory_info.rss)),  # 使用hwm或rss
            data=format_bytes(getattr(memory_info, 'data', 0)),  # 尝试获取data字段
            stack=format_bytes(getattr(memory_info, 'stack', 0)),  # 尝试获取stack字段
            locked=format_bytes(getattr(memory_info, 'locked', 0)),  # 尝试获取locked字段
            swap=format_bytes(getattr(memory_info, 'swap', 0)),  # 尝试获取swap字段
            cpuValue=cpu_value,
            rssValue=memory_info.rss,  # 使用原始字节数，与1panel一致
            envs=envs,
            openFiles=open_files,
            connects=connections
        )
        
        return detail_response
        
    except psutil.NoSuchProcess:
        logger.error(f"进程 {pid} 不存在")
        raise ValueError(f"进程 {pid} 不存在")
    except psutil.AccessDenied:
        logger.error(f"无权限访问进程 {pid}")
        raise ValueError(f"无权限访问进程 {pid}")
    except Exception as e:
        logger.error(f"获取进程详情时出错: {e}")
        raise ValueError(f"获取进程详情失败: {str(e)}")

def get_network_connections() -> List[NetworkConnectionInfo]:
    """获取系统网络连接列表
    
    Returns:
        List[NetworkConnectionInfo]: 网络连接信息列表
    """
    connections_list = []
    try:
        # 创建PID到进程名称的映射，避免重复获取进程信息
        pid_to_name = {}
        
        # 首先获取所有网络连接
        for conn in psutil.net_connections(kind='inet'):
            # 只处理有PID的连接
            if conn.pid is None:
                continue
            
            # 获取进程名称，如果缓存中没有则查询
            if conn.pid not in pid_to_name:
                try:
                    proc = psutil.Process(conn.pid)
                    pid_to_name[conn.pid] = proc.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pid_to_name[conn.pid] = 'unknown'
            
            # 格式化本地地址
            local_address = '0.0.0.0'
            if conn.laddr:
                local_ip = conn.laddr.ip if hasattr(conn.laddr, 'ip') else '0.0.0.0'
                local_port = conn.laddr.port if hasattr(conn.laddr, 'port') else ''
                local_address = f"{local_ip}:{local_port}"
            
            # 格式化远程地址
            remote_address = '0.0.0.0'
            if conn.raddr:
                remote_ip = conn.raddr.ip if hasattr(conn.raddr, 'ip') else '0.0.0.0'
                remote_port = conn.raddr.port if hasattr(conn.raddr, 'port') else ''
                remote_address = f"{remote_ip}:{remote_port}"
            
            # 确定连接类型和状态（使用整数值而不是常量）
            if conn.type == 1:  # TCP类型通常是1
                conn_type = 'tcp'
            elif conn.type == 2:  # UDP类型通常是2
                conn_type = 'udp'
            else:
                conn_type = 'unknown'
            status = conn.status if hasattr(conn, 'status') else 'NONE'
            
            # 创建网络连接信息对象
            network_conn = NetworkConnectionInfo(
                type=conn_type,
                pid=conn.pid,
                name=pid_to_name[conn.pid],
                local_address=local_address,
                remote_address=remote_address,
                status=status
            )
            
            connections_list.append(network_conn)
            
    except Exception as e:
        logger.error(f"获取网络连接列表时出错: {e}")
    
    return connections_list


def terminate_process(pid: int) -> Dict[str, Any]:
    """终止指定PID的进程
    
    Args:
        pid: 要终止的进程ID
    
    Returns:
        Dict: 包含操作结果的字典
    
    Raises:
        ValueError: 当进程不存在、无权限访问或终止失败时
    """
    try:
        # 获取进程对象
        proc = psutil.Process(pid)
        
        # 保存进程信息以便返回
        process_name = proc.name()
        
        # 尝试正常终止进程（SIGTERM）
        proc.terminate()
        
        # 等待进程终止，最多等待5秒
        try:
            # 等待进程终止，超时时间5秒
            proc.wait(timeout=5)
            logger.info(f"进程 {pid} ({process_name}) 已成功终止")
            return {
                "success": True,
                "pid": pid,
                "name": process_name,
                "message": f"进程 {pid} ({process_name}) 已成功终止"
            }
        except psutil.TimeoutExpired:
            # 如果超时，尝试强制终止（SIGKILL）
            logger.warning(f"进程 {pid} ({process_name}) 终止超时，尝试强制终止")
            proc.kill()
            logger.info(f"进程 {pid} ({process_name}) 已强制终止")
            return {
                "success": True,
                "pid": pid,
                "name": process_name,
                "message": f"进程 {pid} ({process_name}) 已强制终止",
                "force_killed": True
            }
    
    except psutil.NoSuchProcess:
        error_msg = f"进程 {pid} 不存在"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    except psutil.AccessDenied:
        error_msg = f"无权限终止进程 {pid}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    except Exception as e:
        error_msg = f"终止进程 {pid} 失败: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

