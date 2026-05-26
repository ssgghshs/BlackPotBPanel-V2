from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from . import schemas, service
import psutil
import platform
import socket
from datetime import datetime
import os
import time

# 添加认证依赖导入
from middleware.auth import get_current_active_user

router = APIRouter(prefix="/monitor", tags=["monitor"])

def safe_format_error(error):
    """安全地格式化错误信息，避免格式化字符问题"""
    try:
        if error is None:
            return "未知错误"
        # 转换为字符串并移除可能引起问题的格式化字符
        error_str = str(error)
        # 移除可能引起问题的格式化字符
        safe_str = error_str.replace('%', '%%')
        return safe_str
    except:
        return "未知错误"

def get_cpu_model_name():
    """获取CPU型号信息，跨平台实现"""
    try:
        # 尝试使用不同方法获取CPU型号
        if platform.system() == "Linux":
            # 在Linux上，读取/proc/cpuinfo文件
            if os.path.exists('/proc/cpuinfo'):
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('model name'):
                            # 提取型号名称并去除多余空格
                            cpu_model = line.split(':', 1)[1].strip()
                            return cpu_model
        elif platform.system() == "Windows":
            # 在Windows上，使用wmic命令
            try:
                import subprocess
                result = subprocess.run(
                    ['wmic', 'cpu', 'get', 'name'], 
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                # 解析输出，获取CPU型号
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    return lines[1].strip()
            except:
                # 如果wmic命令失败，尝试使用platform.processor()
                pass
        
        # 跨平台的备用方法
        processor_info = platform.processor()
        if processor_info and processor_info.strip():
            return processor_info
        
        # 如果以上方法都失败，返回默认值
        return "Unknown CPU"
    except Exception:
        return "Unknown CPU"

def get_detailed_platform_version():
    """获取详细的平台版本信息，如ubuntu-22.04, redhat-8, centos-7等"""
    try:
        # 尝试读取常见的Linux发行版信息文件
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                lines = f.readlines()
                info = {}
                for line in lines:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        # 移除引号
                        info[key] = value.strip('"').strip("'")
                
                # 获取ID和VERSION_ID
                if 'ID' in info and 'VERSION_ID' in info:
                    return f"{info['ID']}-{info['VERSION_ID']}".lower()
                elif 'ID' in info:
                    return info['ID'].lower()
        
        # 如果无法从/etc/os-release获取信息，尝试其他方法
        if os.path.exists('/etc/redhat-release'):
            with open('/etc/redhat-release', 'r') as f:
                content = f.read().strip()
                if 'CentOS' in content:
                    # 简单提取版本号
                    import re
                    match = re.search(r'release\s+(\d+)', content)
                    if match:
                        return f"centos-{match.group(1)}".lower()
                elif 'Red Hat' in content:
                    import re
                    match = re.search(r'release\s+(\d+)', content)
                    if match:
                        return f"redhat-{match.group(1)}".lower()
        
        # 如果以上方法都不行，回退到platform模块
        platform_name = platform.system()
        platform_version = platform.version()
        return f"{platform_name.lower()}-{platform_version}".lower()
    except Exception:
        # 如果出现任何错误，回退到基本的platform信息
        platform_name = platform.system()
        platform_version = platform.version()
        return f"{platform_name.lower()}-{platform_version}".lower()

@router.get("/host-info")
async def get_host_info(current_user = Depends(get_current_active_user)):
    """获取主机详细信息：主机名称、发行版本、内核版本、系统类型、主机地址、启动时间、运行时间"""
    try:
        # 获取主机名称
        hostname = socket.gethostname()
        
        # 获取平台信息
        platform_name = platform.system()
        architecture = platform.machine()
        
        # 获取内核版本
        kernel_version = platform.release()
        
        # 获取详细的平台版本信息
        platform_version = get_detailed_platform_version()
        
        # 获取主机IP地址
        try:
            ip_address = socket.gethostbyname(hostname)
        except:
            ip_address = "127.0.0.1"
        
        # 获取系统启动时间
        boot_time_timestamp = psutil.boot_time()
        boot_time = datetime.fromtimestamp(boot_time_timestamp)
        
        # 计算系统运行时间（秒）
        current_time = datetime.now()
        uptime_seconds = int((current_time - boot_time).total_seconds())
        
        # 将运行时间转换为天、小时、分钟、秒
        days = uptime_seconds // (24 * 3600)
        uptime_seconds = uptime_seconds % (24 * 3600)
        hours = uptime_seconds // 3600
        uptime_seconds %= 3600
        minutes = uptime_seconds // 60
        seconds = uptime_seconds % 60
        
        # 构造返回数据（按用户要求的格式）
        response_data = {
            "code": 200,
            "data": {
                "hostname": hostname,
                "platform_version": platform_version,
                "kernel_version": kernel_version,
                "architecture": architecture.lower(),
                "ip_address": ip_address,
                "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
                "uptime": f"{days}天 {hours}小时 {minutes}分钟 {seconds}秒"
            },
            "message": "success"
        }
        
        return response_data
    except Exception as e:
        # 使用更安全的错误信息处理方式
        safe_error_msg = safe_format_error(e)
        detail_msg = f"获取主机信息失败: {safe_error_msg}"
        raise HTTPException(
            status_code=500,
            detail=detail_msg
        )

@router.get("/system-info")
async def get_system_info(current_user = Depends(get_current_active_user)):
    """获取宿主机的CPU使用率、内存使用率、硬盘使用率、负载信息"""
    try:
        # 获取CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 获取CPU核心数和线程数
        cpu_cores = psutil.cpu_count(logical=False) or 1
        cpu_threads = psutil.cpu_count(logical=True) or 1
        
        # 获取CPU型号
        cpu_model_name = get_cpu_model_name()
        
        # 获取内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_total_gb = round(memory.total / (1024**3), 2)
        memory_used_gb = round(memory.used / (1024**3), 2)
        
        # 获取交换内存信息
        try:
            swap = psutil.swap_memory()
            swap_percent = swap.percent
            swap_total_gb = round(swap.total / (1024**3), 2)
            swap_used_gb = round(swap.used / (1024**3), 2)
        except Exception:
            # 出错时设置默认值
            swap_percent = 0.0
            swap_total_gb = 0.0
            swap_used_gb = 0.0
        
        # 获取硬盘使用率
        try:
            disk_percent = 0
            disk_total_gb = 0
            disk_used_gb = 0
            # 新增：存储所有磁盘信息
            all_disks_info = []
            
            # 获取所有磁盘分区
            disk_partitions = psutil.disk_partitions()
            
            # 定义获取inode信息的函数
            def get_inode_info(mountpoint):
                """获取分区的inode使用情况"""
                try:
                    # Windows系统没有inode概念，返回默认值
                    if platform.system() == "Windows":
                        return {
                            "inodesTotal": 0,
                            "inodesUsed": 0,
                            "inodesUsedPercent": 0.0
                        }
                    
                    # Linux/Unix系统获取inode信息
                    if hasattr(os, 'statvfs'):
                        stat = os.statvfs(mountpoint)
                        inodes_total = stat.f_files
                        inodes_free = stat.f_ffree
                        inodes_used = inodes_total - inodes_free
                        
                        # 计算inode使用百分比
                        if inodes_total > 0:
                            inodes_used_percent = round((inodes_used / inodes_total) * 100, 2)
                        else:
                            inodes_used_percent = 0.0
                        
                        return {
                            "inodesTotal": inodes_total,
                            "inodesUsed": inodes_used,
                            "inodesUsedPercent": inodes_used_percent
                        }
                    
                    # 默认返回值
                    return {
                        "inodesTotal": 0,
                        "inodesUsed": 0,
                        "inodesUsedPercent": 0.0
                    }
                except Exception:
                    # 出错时返回默认值
                    return {
                        "inodesTotal": 0,
                        "inodesUsed": 0,
                        "inodesUsedPercent": 0.0
                    }
            
            # 定义多轮过滤函数
            def filter_disk_partitions(partitions):
                filtered = []
                
                for partition in partitions:
                    try:
                        # 过滤1: 跳过特殊设备和系统保留分区（基于设备名）
                        # Windows系统特殊设备
                        if platform.system() == "Windows":
                            # 跳过系统保留分区、恢复分区、隐藏分区等
                            if any(keyword in partition.device.lower() for keyword in ['\\device\\', '\\harddiskvolume', '\\\\?\\']):
                                continue
                            # 跳过光驱
                            if partition.device.lower().startswith('d:') and 'cdrom' in partition.opts.lower():
                                continue
                        # Linux系统特殊设备
                        else:
                            # 跳过虚拟文件系统和特殊挂载点
                            if any(fs_type in partition.fstype for fs_type in ['tmpfs', 'sysfs', 'proc', 'devtmpfs', 'devpts', 'cgroup', 'cgroup2', 'pstore', 'mqueue', 'debugfs', 'tracefs', 'securityfs', 'fusectl', 'configfs', 'bpf']):
                                continue
                            # 跳过网络文件系统
                            if any(fs_type in partition.fstype for fs_type in ['nfs', 'cifs', 'smbfs', 'sshfs', 'sftp']):
                                continue
                            # 跳过一些特殊挂载点
                            if partition.mountpoint.startswith('/sys') or partition.mountpoint.startswith('/proc') or partition.mountpoint.startswith('/dev'):
                                continue
                            # 跳过容器挂载点
                            if '/docker/' in partition.mountpoint or '/lxc/' in partition.mountpoint or '/var/lib/docker/' in partition.mountpoint:
                                continue
                        
                        # 过滤2: 获取磁盘使用情况，跳过无法访问的分区
                        disk = psutil.disk_usage(partition.mountpoint)
                        
                        # 过滤3: 跳过容量过小的分区（小于100MB）
                        if disk.total < 100 * 1024 * 1024:  # 100MB
                            continue
                        
                        # 过滤4: 跳过只读分区（根据需要可以调整）
                        if platform.system() != "Windows" and 'ro' in partition.opts.split(','):
                            continue
                        
                        # 计算磁盘使用情况
                        disk_percent_single = round((disk.used / disk.total) * 100, 2)
                        disk_total_gb_single = round(disk.total / (1024**3), 2)
                        disk_used_gb_single = round(disk.used / (1024**3), 2)
                        
                        # 获取inode信息
                        inode_info = get_inode_info(partition.mountpoint)
                        
                        # 添加到过滤后的列表
                        filtered.append({
                            "device": partition.device,
                            "mountpoint": partition.mountpoint,
                            "fstype": partition.fstype,  # 添加文件系统类型
                            "percent": disk_percent_single,
                            "total": disk_total_gb_single,
                            "used": disk_used_gb_single,
                            "inodesTotal": inode_info["inodesTotal"],
                            "inodesUsed": inode_info["inodesUsed"],
                            "inodesUsedPercent": inode_info["inodesUsedPercent"]
                        })
                        
                    except Exception:
                        # 跳过无法访问的分区，不添加到结果中
                        continue
                
                return filtered
            
            # 应用过滤函数获取有意义的磁盘分区
            filtered_disks = filter_disk_partitions(disk_partitions)
            all_disks_info = filtered_disks
            
            # 确保系统盘信息被正确设置
            system_disk_found = False
            for disk_info in all_disks_info:
                # 检查是否为系统盘
                if (platform.system() == "Windows" and disk_info["mountpoint"].lower() == "c:") or \
                   (platform.system() != "Windows" and disk_info["mountpoint"] == "/"):
                    disk_percent = disk_info["percent"]
                    disk_total_gb = disk_info["total"]
                    disk_used_gb = disk_info["used"]
                    system_disk_found = True
                    break
            
            # 如果过滤后没有找到系统盘，尝试从原始分区中查找
            if not system_disk_found:
                for partition in disk_partitions:
                    try:
                        if (platform.system() == "Windows" and partition.mountpoint.lower() == "c:") or \
                           (platform.system() != "Windows" and partition.mountpoint == "/"):
                            disk = psutil.disk_usage(partition.mountpoint)
                            disk_percent = round((disk.used / disk.total) * 100, 2)
                            disk_total_gb = round(disk.total / (1024**3), 2)
                            disk_used_gb = round(disk.used / (1024**3), 2)
                            break
                    except Exception:
                        continue
        except Exception as disk_error:
            # 如果无法获取磁盘使用率，设置为0
            disk_percent = 0
            disk_total_gb = 0
            disk_used_gb = 0
            all_disks_info = []
            # 使用安全的方式记录错误日志
            try:
                safe_disk_error = safe_format_error(disk_error)
                print("获取磁盘使用率失败: {}".format(safe_disk_error))  # 使用.format()替代f-string避免格式化错误
            except:
                print("获取磁盘使用率失败: 未知错误")
        
        # 获取系统负载
        if platform.system() != "Windows":
            # Unix/Linux系统
            load_avg = psutil.getloadavg()
            load_avg_1min, load_avg_5min, load_avg_15min = load_avg
        else:
            # Windows系统，使用CPU使用率近似表示负载
            load_avg_1min = load_avg_5min = load_avg_15min = cpu_percent
        
        # 构造返回数据
        response_data = {
            "code": 200,
            "data": {
                "cpu": {
                    "cores": cpu_cores,
                    "load_avg": [
                        round(load_avg_1min, 2),
                        round(load_avg_5min, 2),
                        round(load_avg_15min, 2)
                    ],
                    "percent": round(cpu_percent, 2),
                    "threads": cpu_threads,
                    "cpuModelName": cpu_model_name
                },
                "disk": {
                    "percent": disk_percent,
                    "total": disk_total_gb,
                    "used": disk_used_gb,
                    "all_disks": all_disks_info  # 新增：所有磁盘信息
                },
                "memory": {
                    "percent": round(memory_percent, 2),
                    "total": memory_total_gb,
                    "used": memory_used_gb,
                    "swappercent": round(swap_percent, 2),
                    "swaptotal": swap_total_gb,
                    "swapused": swap_used_gb
                }
            },
            "message": "success"
        }
        
        return response_data
    except Exception as e:
        # 使用更安全的错误信息处理方式
        safe_error_msg = safe_format_error(e)
        detail_msg = f"获取系统资源占用失败: {safe_error_msg}"
        raise HTTPException(
            status_code=500,
            detail=detail_msg
        )

# 添加全局变量存储上一次的网络流量统计信息和时间戳
previous_net_io = {}
previous_net_timestamp = None

@router.get("/network-traffic")
async def get_network_traffic(current_user = Depends(get_current_active_user)):
    """获取网络流量监控信息"""
    try:
        global previous_net_io, previous_net_timestamp
        
        # 获取当前网络接口统计信息和时间戳
        current_net_io = psutil.net_io_counters(pernic=True)
        current_timestamp = time.time()
        
        # 构造接口数据
        interfaces_data = {}
        
        # 如果有上一次的数据，计算每秒速率
        if previous_net_io and previous_net_timestamp:
            time_delta = current_timestamp - previous_net_timestamp
            
            if time_delta > 0:  # 确保时间差大于0
                for interface, current_stats in current_net_io.items():
                    if interface in previous_net_io:
                        previous_stats = previous_net_io[interface]
                        
                        # 计算每秒接收和发送字节数
                        bytes_recv_per_sec = round((current_stats.bytes_recv - previous_stats.bytes_recv) / time_delta, 2)
                        bytes_sent_per_sec = round((current_stats.bytes_sent - previous_stats.bytes_sent) / time_delta, 2)
                        packets_recv_per_sec = round((current_stats.packets_recv - previous_stats.packets_recv) / time_delta, 2)
                        packets_sent_per_sec = round((current_stats.packets_sent - previous_stats.packets_sent) / time_delta, 2)
                        
                        interfaces_data[interface] = {
                            "bytes_recv_per_sec": max(0, bytes_recv_per_sec),  # 确保不为负数
                            "bytes_sent_per_sec": max(0, bytes_sent_per_sec),
                            "packets_recv_per_sec": max(0, packets_recv_per_sec),
                            "packets_sent_per_sec": max(0, packets_sent_per_sec),
                            "packets_recv": current_stats.packets_recv,
                            "packets_sent": current_stats.packets_sent
                        }
                    else:
                        # 新增的网络接口
                        interfaces_data[interface] = {
                            "bytes_recv_per_sec": 0.0,
                            "bytes_sent_per_sec": 0.0,
                            "packets_recv_per_sec": 0.0,
                            "packets_sent_per_sec": 0.0,
                            "packets_recv": current_stats.packets_recv,
                            "packets_sent": current_stats.packets_sent
                        }
            else:
                # 时间差为0，返回0值
                for interface, stats in current_net_io.items():
                    interfaces_data[interface] = {
                        "bytes_recv_per_sec": 0.0,
                        "bytes_sent_per_sec": 0.0,
                        "packets_recv_per_sec": 0.0,
                        "packets_sent_per_sec": 0.0,
                        "packets_recv": stats.packets_recv,
                        "packets_sent": stats.packets_sent
                    }
        else:
            # 第一次获取数据，无法计算速率，返回0
            for interface, stats in current_net_io.items():
                interfaces_data[interface] = {
                    "bytes_recv_per_sec": 0.0,
                    "bytes_sent_per_sec": 0.0,
                    "packets_recv_per_sec": 0.0,
                    "packets_sent_per_sec": 0.0,
                    "packets_recv": stats.packets_recv,
                    "packets_sent": stats.packets_sent
                }
        
        # 更新上一次的数据
        previous_net_io = current_net_io
        previous_net_timestamp = current_timestamp
        
        # 构造返回数据
        response_data = {
            "code": 200,
            "data": {
                "interfaces": interfaces_data,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "message": "success"
        }
        
        return response_data
    except Exception as e:
        # 使用更安全的错误信息处理方式
        safe_error_msg = safe_format_error(e)
        detail_msg = f"获取网络流量信息失败: {safe_error_msg}"
        raise HTTPException(
            status_code=500,
            detail=detail_msg
        )

# 添加全局变量存储上一次的磁盘I/O统计信息和时间戳
previous_disk_io = {}
previous_timestamp = None

@router.get("/disk-io")
async def get_disk_io(current_user = Depends(get_current_active_user)):
    """获取磁盘I/O监控信息"""
    try:
        global previous_disk_io, previous_timestamp
        
        # 获取当前磁盘I/O统计信息和时间戳
        current_disk_io = psutil.disk_io_counters(perdisk=True)
        current_timestamp = time.time()
        
        # 构造磁盘数据
        disks_data = {}
        
        # 如果有上一次的数据，计算每秒速率
        if previous_disk_io and previous_timestamp:
            time_delta = current_timestamp - previous_timestamp
            
            if time_delta > 0:  # 确保时间差大于0
                for device, current_stats in current_disk_io.items():
                    if device in previous_disk_io:
                        previous_stats = previous_disk_io[device]
                        
                        # 计算每秒读写字节数和读写次数
                        read_bytes_per_sec = round((current_stats.read_bytes - previous_stats.read_bytes) / time_delta, 2)
                        write_bytes_per_sec = round((current_stats.write_bytes - previous_stats.write_bytes) / time_delta, 2)
                        read_count_per_sec = round((current_stats.read_count - previous_stats.read_count) / time_delta, 2)
                        write_count_per_sec = round((current_stats.write_count - previous_stats.write_count) / time_delta, 2)
                        
                        disks_data[device] = {
                            "busy_time": current_stats.read_time + current_stats.write_time,  # 总忙碌时间
                            "read_bytes_per_sec": max(0, read_bytes_per_sec),  # 确保不为负数
                            "read_count_per_sec": max(0, read_count_per_sec),
                            "write_bytes_per_sec": max(0, write_bytes_per_sec),
                            "write_count_per_sec": max(0, write_count_per_sec)
                        }
                    else:
                        # 新增的磁盘设备
                        disks_data[device] = {
                            "busy_time": current_stats.read_time + current_stats.write_time,
                            "read_bytes_per_sec": 0.0,
                            "read_count_per_sec": 0.0,
                            "write_bytes_per_sec": 0.0,
                            "write_count_per_sec": 0.0
                        }
            else:
                # 时间差为0，返回0值
                for device, stats in current_disk_io.items():
                    disks_data[device] = {
                        "busy_time": stats.read_time + stats.write_time,
                        "read_bytes_per_sec": 0.0,
                        "read_count_per_sec": 0.0,
                        "write_bytes_per_sec": 0.0,
                        "write_count_per_sec": 0.0
                    }
        else:
            # 第一次获取数据，无法计算速率，返回0
            for device, stats in current_disk_io.items():
                disks_data[device] = {
                    "busy_time": stats.read_time + stats.write_time,
                    "read_bytes_per_sec": 0.0,
                    "read_count_per_sec": 0.0,
                    "write_bytes_per_sec": 0.0,
                    "write_count_per_sec": 0.0
                }
        
        # 更新上一次的数据
        previous_disk_io = current_disk_io
        previous_timestamp = current_timestamp
        
        # 构造返回数据
        response_data = {
            "code": 200,
            "data": {
                "disks": disks_data,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "message": "success"
        }
        
        return response_data
    except Exception as e:
        # 使用更安全的错误信息处理方式
        safe_error_msg = safe_format_error(e)
        detail_msg = f"获取磁盘I/O信息失败: {safe_error_msg}"
        raise HTTPException(
            status_code=500,
            detail=detail_msg
        )


@router.get("/panel-resource", response_model=schemas.PanelResourceResponse)
async def get_panel_resource(current_user=Depends(get_current_active_user)):
    """获取面板进程自身的资源占用（CPU、内存、运行时间等）"""
    try:
        result = service.get_panel_resource()
        return result
    except Exception as e:
        safe_error_msg = safe_format_error(e)
        detail_msg = f"获取面板资源占用失败: {safe_error_msg}"
        raise HTTPException(
            status_code=500,
            detail=detail_msg
        )
