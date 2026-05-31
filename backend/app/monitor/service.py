import psutil
import platform
import socket
import os
import time
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from . import models, schemas


def safe_format_error(error):
    try:
        if error is None:
            return "未知错误"
        error_str = str(error)
        safe_str = error_str.replace('%', '%%')
        return safe_str
    except:
        return "未知错误"


def get_cpu_model_name():
    try:
        if platform.system() == "Linux":
            if os.path.exists('/proc/cpuinfo'):
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('model name'):
                            cpu_model = line.split(':', 1)[1].strip()
                            return cpu_model
        elif platform.system() == "Windows":
            try:
                import subprocess
                result = subprocess.run(
                    ['wmic', 'cpu', 'get', 'name'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    return lines[1].strip()
            except:
                pass

        processor_info = platform.processor()
        if processor_info and processor_info.strip():
            return processor_info

        return "Unknown CPU"
    except Exception:
        return "Unknown CPU"


def get_detailed_platform_version():
    try:
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                lines = f.readlines()
                info = {}
                for line in lines:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        info[key] = value.strip('"').strip("'")

                if 'ID' in info and 'VERSION_ID' in info:
                    return f"{info['ID']}-{info['VERSION_ID']}".lower()
                elif 'ID' in info:
                    return info['ID'].lower()

        if os.path.exists('/etc/redhat-release'):
            with open('/etc/redhat-release', 'r') as f:
                content = f.read().strip()
                if 'CentOS' in content:
                    import re
                    match = re.search(r'release\s+(\d+)', content)
                    if match:
                        return f"centos-{match.group(1)}".lower()
                elif 'Red Hat' in content:
                    import re
                    match = re.search(r'release\s+(\d+)', content)
                    if match:
                        return f"redhat-{match.group(1)}".lower()

        platform_name = platform.system()
        platform_version = platform.version()
        return f"{platform_name.lower()}-{platform_version}".lower()
    except Exception:
        platform_name = platform.system()
        platform_version = platform.version()
        return f"{platform_name.lower()}-{platform_version}".lower()


async def get_host_info():
    hostname = socket.gethostname()
    platform_name = platform.system()
    architecture = platform.machine()
    kernel_version = platform.release()
    platform_version = get_detailed_platform_version()

    try:
        ip_address = socket.gethostbyname(hostname)
    except:
        ip_address = "127.0.0.1"

    boot_time_timestamp = psutil.boot_time()
    boot_time = datetime.fromtimestamp(boot_time_timestamp)

    current_time = datetime.now()
    uptime_seconds = int((current_time - boot_time).total_seconds())

    days = uptime_seconds // (24 * 3600)
    uptime_seconds = uptime_seconds % (24 * 3600)
    hours = uptime_seconds // 3600
    uptime_seconds %= 3600
    minutes = uptime_seconds // 60
    seconds = uptime_seconds % 60

    return {
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


async def get_system_info():
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_cores = psutil.cpu_count(logical=False) or 1
    cpu_threads = psutil.cpu_count(logical=True) or 1
    cpu_model_name = get_cpu_model_name()

    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    memory_total_gb = round(memory.total / (1024**3), 2)
    memory_used_gb = round(memory.used / (1024**3), 2)

    try:
        swap = psutil.swap_memory()
        swap_percent = swap.percent
        swap_total_gb = round(swap.total / (1024**3), 2)
        swap_used_gb = round(swap.used / (1024**3), 2)
    except Exception:
        swap_percent = 0.0
        swap_total_gb = 0.0
        swap_used_gb = 0.0

    try:
        disk_percent = 0
        disk_total_gb = 0
        disk_used_gb = 0
        all_disks_info = []

        disk_partitions = psutil.disk_partitions(True)
        coutine_types = ['ext2', 'ext3', 'ext4', 'xfs', 'btrfs', 'fat32', 'nfs', 'cifs', 'smb', 'iscsi']
        coutine_keys = ['docker', 'volume', 'overlay', '/snap', '/run/user', '/dev/']
        cuts = ['/mnt/cdrom', '/boot', '/boot/efi', '/dev', '/dev/shm', '/run/lock', '/run', '/run/shm', '/run/user', '/dev/zram']

        for partition in disk_partitions:
            try:
                if partition.mountpoint in cuts:
                    continue
                if partition.mountpoint.startswith('/proc'):
                    continue
                if partition.device.startswith('/dev/loop'):
                    continue
                if partition.fstype.lower() not in coutine_types and partition.mountpoint != "/":
                    if (partition.fstype.lower() not in coutine_types and 'fuse' not in partition.fstype.lower()) or partition.fstype.lower() == 'fusectl':
                        continue

                is_continue = False
                for key in coutine_keys:
                    if key == "overlay" and partition.mountpoint == "/":
                        continue
                    if key in partition.mountpoint:
                        is_continue = True
                        break
                if is_continue:
                    continue

                statvfs = os.statvfs(partition.mountpoint)

                disk_total = statvfs.f_frsize * statvfs.f_blocks
                disk_used_raw = disk_total - (statvfs.f_frsize * statvfs.f_bfree)
                root_reserved = statvfs.f_frsize * statvfs.f_bfree - statvfs.f_frsize * statvfs.f_bavail

                adjusted_total = disk_total - root_reserved
                if adjusted_total > 0:
                    disk_used_percent = round((disk_used_raw / adjusted_total) * 100, 2)
                else:
                    disk_used_percent = 0.0

                disk_total_gb_single = round(disk_total / (1024**3), 2)
                disk_used_gb_single = round(disk_used_raw / (1024**3), 2)

                inodes_total = statvfs.f_files
                inodes_free = statvfs.f_ffree
                inodes_used = inodes_total - inodes_free
                if inodes_total > 0:
                    inodes_used_percent = round((inodes_used / inodes_total) * 100, 2)
                else:
                    inodes_used_percent = 0.0

                disk_info = {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "percent": disk_used_percent,
                    "total": disk_total_gb_single,
                    "used": disk_used_gb_single,
                    "inodesTotal": inodes_total,
                    "inodesUsed": inodes_used,
                    "inodesUsedPercent": inodes_used_percent,
                }
                all_disks_info.append(disk_info)

                if partition.mountpoint == "/":
                    disk_percent = disk_used_percent
                    disk_total_gb = disk_total_gb_single
                    disk_used_gb = disk_used_gb_single

            except Exception:
                continue

        if not all_disks_info:
            for partition in disk_partitions:
                try:
                    if partition.mountpoint == "/":
                        statvfs = os.statvfs("/")
                        disk_total = statvfs.f_frsize * statvfs.f_blocks
                        disk_used_raw = disk_total - (statvfs.f_frsize * statvfs.f_bfree)
                        disk_total_gb = round(disk_total / (1024**3), 2)
                        disk_used_gb = round(disk_used_raw / (1024**3), 2)
                        root_reserved = statvfs.f_frsize * statvfs.f_bfree - statvfs.f_frsize * statvfs.f_bavail
                        adjusted = disk_total - root_reserved
                        disk_percent = round((disk_used_raw / adjusted) * 100, 2) if adjusted > 0 else 0
                        break
                except Exception:
                    continue
    except Exception as disk_error:
        disk_percent = 0
        disk_total_gb = 0
        disk_used_gb = 0
        all_disks_info = []
        try:
            safe_disk_error = safe_format_error(disk_error)
            print("获取磁盘使用率失败: {}".format(safe_disk_error))
        except:
            print("获取磁盘使用率失败: 未知错误")

    if platform.system() != "Windows":
        load_avg = psutil.getloadavg()
        load_avg_1min, load_avg_5min, load_avg_15min = load_avg
    else:
        load_avg_1min = load_avg_5min = load_avg_15min = cpu_percent

    return {
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
                "all_disks": all_disks_info
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


previous_net_io = {}
previous_net_timestamp = None


async def get_network_traffic():
    global previous_net_io, previous_net_timestamp

    current_net_io = psutil.net_io_counters(pernic=True)
    current_timestamp = time.time()

    interfaces_data = {}

    if previous_net_io and previous_net_timestamp:
        time_delta = current_timestamp - previous_net_timestamp

        if time_delta > 0:
            for interface, current_stats in current_net_io.items():
                if interface in previous_net_io:
                    previous_stats = previous_net_io[interface]

                    bytes_recv_per_sec = round((current_stats.bytes_recv - previous_stats.bytes_recv) / time_delta, 2)
                    bytes_sent_per_sec = round((current_stats.bytes_sent - previous_stats.bytes_sent) / time_delta, 2)
                    packets_recv_per_sec = round((current_stats.packets_recv - previous_stats.packets_recv) / time_delta, 2)
                    packets_sent_per_sec = round((current_stats.packets_sent - previous_stats.packets_sent) / time_delta, 2)

                    interfaces_data[interface] = {
                        "bytes_recv_per_sec": max(0, bytes_recv_per_sec),
                        "bytes_sent_per_sec": max(0, bytes_sent_per_sec),
                        "packets_recv_per_sec": max(0, packets_recv_per_sec),
                        "packets_sent_per_sec": max(0, packets_sent_per_sec),
                        "packets_recv": current_stats.packets_recv,
                        "packets_sent": current_stats.packets_sent
                    }
                else:
                    interfaces_data[interface] = {
                        "bytes_recv_per_sec": 0.0,
                        "bytes_sent_per_sec": 0.0,
                        "packets_recv_per_sec": 0.0,
                        "packets_sent_per_sec": 0.0,
                        "packets_recv": current_stats.packets_recv,
                        "packets_sent": current_stats.packets_sent
                    }
        else:
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
        for interface, stats in current_net_io.items():
            interfaces_data[interface] = {
                "bytes_recv_per_sec": 0.0,
                "bytes_sent_per_sec": 0.0,
                "packets_recv_per_sec": 0.0,
                "packets_sent_per_sec": 0.0,
                "packets_recv": stats.packets_recv,
                "packets_sent": stats.packets_sent
            }

    previous_net_io = current_net_io
    previous_net_timestamp = current_timestamp

    return {
        "code": 200,
        "data": {
            "interfaces": interfaces_data,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "message": "success"
    }


previous_disk_io = {}
previous_disk_timestamp = None


async def get_disk_io():
    global previous_disk_io, previous_disk_timestamp

    current_disk_io = psutil.disk_io_counters(perdisk=True)
    current_timestamp = time.time()

    disks_data = {}

    if previous_disk_io and previous_disk_timestamp:
        time_delta = current_timestamp - previous_disk_timestamp

        if time_delta > 0:
            for device, current_stats in current_disk_io.items():
                if device in previous_disk_io:
                    previous_stats = previous_disk_io[device]

                    read_bytes_per_sec = round((current_stats.read_bytes - previous_stats.read_bytes) / time_delta, 2)
                    write_bytes_per_sec = round((current_stats.write_bytes - previous_stats.write_bytes) / time_delta, 2)
                    read_count_per_sec = round((current_stats.read_count - previous_stats.read_count) / time_delta, 2)
                    write_count_per_sec = round((current_stats.write_count - previous_stats.write_count) / time_delta, 2)

                    disks_data[device] = {
                        "busy_time": current_stats.read_time + current_stats.write_time,
                        "read_bytes_per_sec": max(0, read_bytes_per_sec),
                        "read_count_per_sec": max(0, read_count_per_sec),
                        "write_bytes_per_sec": max(0, write_bytes_per_sec),
                        "write_count_per_sec": max(0, write_count_per_sec),
                    }
                else:
                    disks_data[device] = {
                        "busy_time": current_stats.read_time + current_stats.write_time,
                        "read_bytes_per_sec": 0.0,
                        "read_count_per_sec": 0.0,
                        "write_bytes_per_sec": 0.0,
                        "write_count_per_sec": 0.0,
                    }
        else:
            for device, stats in current_disk_io.items():
                disks_data[device] = {
                    "busy_time": stats.read_time + stats.write_time,
                    "read_bytes_per_sec": 0.0,
                    "read_count_per_sec": 0.0,
                    "write_bytes_per_sec": 0.0,
                    "write_count_per_sec": 0.0,
                }
    else:
        for device, stats in current_disk_io.items():
            disks_data[device] = {
                "busy_time": stats.read_time + stats.write_time,
                "read_bytes_per_sec": 0.0,
                "read_count_per_sec": 0.0,
                "write_bytes_per_sec": 0.0,
                "write_count_per_sec": 0.0,
            }

    previous_disk_io = current_disk_io
    previous_disk_timestamp = current_timestamp

    return {
        "code": 200,
        "data": {
            "disks": disks_data,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "message": "success"
    }


def get_panel_resource() -> dict:
    process = psutil.Process(os.getpid())

    cpu_percent = process.cpu_percent(interval=0.5)

    memory_info = process.memory_info()
    memory_rss_mb = round(memory_info.rss / (1024 * 1024), 2)
    memory_vms_mb = round(memory_info.vms / (1024 * 1024), 2)
    memory_percent = process.memory_percent()

    total_memory = psutil.virtual_memory().total
    total_memory_mb = round(total_memory / (1024 * 1024), 2)

    num_threads = process.num_threads()

    try:
        num_fds = process.num_fds()
    except Exception:
        num_fds = 0

    return {
        "code": 200,
        "message": "success",
        "data": {
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(memory_percent, 2),
            "memory_rss_mb": memory_rss_mb,
            "memory_vms_mb": memory_vms_mb,
            "total_memory_mb": total_memory_mb,
            "num_threads": num_threads,
            "num_fds": num_fds
        }
    }
