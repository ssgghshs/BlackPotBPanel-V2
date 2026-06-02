import os
import sys
import re
import json
import asyncio
import logging
import subprocess
import socket
import shutil
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from app.system import schemas

logger = logging.getLogger(__name__)

# 获取配置文件路径
ENV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "setting.conf")

# 定义不同用户角色可以访问的配置项
ADMIN_CONFIG_FIELDS = [
    'DATABASE_URL', 'APP_NAME', 'VERSION', 'DEBUG', 'SECRET_KEY', 
    'ALGORITHM', 'ACCESS_TOKEN_EXPIRE_MINUTES', 'TIMEZONE', 'ENABLE_DOCS',
    'LANGUAGE', 'THEME', 'LOGIN_NOTIFY', 'RECYCLE', 'HOST', 'PORT', 'SSL_ENABLED',
    'LOGIN_LIMIT', 'SECURITY_ENTRANCE', 'DOMAIN_BINDING',
]
USER_CONFIG_FIELDS = ['APP_NAME', 'VERSION', 'TIMEZONE', 'LANGUAGE', 'THEME', 'LOGIN_NOTIFY', 'RECYCLE']

# 定义不同用户角色可以修改的配置项（VERSION 不允许修改，TIMEZONE、HOST、PORT、SSL_ENABLED 只有管理员可修改）
ADMIN_CONFIG_EDITABLE = [
    'DATABASE_URL', 'APP_NAME', 'DEBUG', 'SECRET_KEY', 
    'ALGORITHM', 'ACCESS_TOKEN_EXPIRE_MINUTES', 'TIMEZONE', 'ENABLE_DOCS',
    'LANGUAGE', 'THEME', 'LOGIN_NOTIFY', 'RECYCLE', 'HOST', 'PORT', 'SSL_ENABLED',
    'LOGIN_LIMIT', 'SECURITY_ENTRANCE', 'DOMAIN_BINDING',
]
USER_CONFIG_EDITABLE = ['APP_NAME', 'LANGUAGE', 'THEME', 'LOGIN_NOTIFY', 'RECYCLE']

def read_env_file() -> Dict[str, str]:
    """读取.env文件内容"""
    configs = {}
    if os.path.exists(ENV_FILE_PATH):
        with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释行
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        configs[key.strip()] = value.strip()
    
    # 过滤掉敏感信息
    sensitive_keys = ['DATABASE_URL', 'SECRET_KEY', 'ALGORITHM']
    filtered_configs = {k: v for k, v in configs.items() if k not in sensitive_keys}
    
    return filtered_configs

def write_env_file(configs: Dict[str, str]) -> None:
    """写入.env文件内容"""
    # 读取原始文件内容，保留注释和格式
    lines = []
    if os.path.exists(ENV_FILE_PATH):
        with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    
    # 更新配置值
    updated_lines = []
    for line in lines:
        stripped_line = line.strip()
        # 保留空行和注释行
        if not stripped_line or stripped_line.startswith('#'):
            updated_lines.append(line)
            continue
            
        # 更新配置行
        if '=' in stripped_line:
            key, _ = stripped_line.split('=', 1)
            key = key.strip()
            if key in configs:
                updated_lines.append(f"{key}={configs[key]}\n")
                # 从待更新列表中移除已处理的键
                del configs[key]
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)
    
    # 添加新的配置项（如果有的话）
    # 过滤掉敏感信息，防止意外添加
    sensitive_keys = ['DATABASE_URL', 'SECRET_KEY', 'ALGORITHM']
    filtered_configs = {k: v for k, v in configs.items() if k not in sensitive_keys}
    
    if filtered_configs:
        updated_lines.append("\n# 动态添加的配置项\n")
        for key, value in filtered_configs.items():
            updated_lines.append(f"{key}={value}\n")
    
    # 写入文件
    with open(ENV_FILE_PATH, 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)

async def get_env_config(user_role: str) -> Dict[str, str]:
    """
    获取环境配置
    
    Args:
        user_role: 用户角色
    
    Returns:
        Dict[str, str]: 环境配置字典
    """
    try:
        configs = read_env_file()
        
        # 根据用户角色过滤配置项
        if user_role == "ADMIN":
            # 管理员可以访问所有非敏感配置
            allowed_configs = {k: v for k, v in configs.items() if k in ADMIN_CONFIG_FIELDS}
        else:
            # 普通用户只能访问部分配置
            allowed_configs = {k: v for k, v in configs.items() if k in USER_CONFIG_FIELDS}
        
        return allowed_configs
    except Exception as e:
        logger.error(f"读取环境配置失败: {e}")
        raise Exception(f"读取环境配置失败: {str(e)}")

async def update_env_config(config_data: schemas.EnvConfigUpdate, user_role: str) -> Dict[str, str]:
    """
    更新环境配置
    
    Args:
        config_data: 配置数据
        user_role: 用户角色
    
    Returns:
        Dict[str, str]: 更新后的配置字典
    """
    try:
        # 读取当前配置
        current_configs = read_env_file()

        # 根据用户角色确定允许更新的配置项
        if user_role == "ADMIN":
            allowed_fields = ADMIN_CONFIG_EDITABLE
        else:
            allowed_fields = USER_CONFIG_EDITABLE

        # 更新配置
        update_data = config_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            # 检查字段是否在允许的范围内
            if key in allowed_fields and value is not None:
                current_configs[key] = str(value)

        # 写入配置文件
        write_env_file(current_configs)

        # 根据用户角色过滤返回的配置项
        if user_role == "ADMIN":
            allowed_configs = {k: v for k, v in current_configs.items() if k in ADMIN_CONFIG_FIELDS}
        else:
            allowed_configs = {k: v for k, v in current_configs.items() if k in USER_CONFIG_FIELDS}

        return allowed_configs
    except Exception as e:
        logger.error(f"更新环境配置失败: {e}")
        raise Exception(f"更新环境配置失败: {str(e)}")

async def get_common_settings() -> Dict[str, str]:
    """
    获取通用设置，返回LANGUAGE、THEME、LOGIN_NOTIFY和RECYCLE字段
    
    Returns:
        Dict[str, str]: 通用设置字典
    """
    try:
        configs = read_env_file()
        
        # 只返回需要的字段
        common_settings = {}
        for field in ['LANGUAGE', 'THEME', 'LOGIN_NOTIFY', 'RECYCLE']:
            if field in configs:
                common_settings[field] = configs[field]
        
        # 如果某些字段不存在，设置默认值
        if 'LANGUAGE' not in common_settings:
            common_settings['LANGUAGE'] = 'zh-CN'
        if 'THEME' not in common_settings:
            common_settings['THEME'] = 'light'
        if 'LOGIN_NOTIFY' not in common_settings:
            common_settings['LOGIN_NOTIFY'] = 'True'
        if 'RECYCLE' not in common_settings:
            common_settings['RECYCLE'] = 'True'
        
        return common_settings
    except Exception as e:
        logger.error(f"读取通用设置失败: {e}")
        # 发生错误时返回默认值
        return {
            'LANGUAGE': 'zh-CN',
            'THEME': 'light',
            'LOGIN_NOTIFY': 'True',
            'RECYCLE': 'True'
        }

async def update_common_settings(settings_data: schemas.CommonSettingsUpdate) -> Dict[str, str]:
    """
    更新通用设置（LANGUAGE、THEME、LOGIN_NOTIFY和RECYCLE）
    
    Args:
        settings_data: 通用设置更新数据
    
    Returns:
        Dict[str, str]: 更新后的通用设置字典
    """
    try:
        # 读取当前配置
        current_configs = read_env_file()
        
        # 转换更新数据为字典
        update_data = settings_data.model_dump(exclude_unset=True)
        
        # 更新配置
        for key, value in update_data.items():
            if key in ['LANGUAGE', 'THEME', 'LOGIN_NOTIFY', 'RECYCLE'] and value is not None:
                # 将布尔值转换为字符串
                if isinstance(value, bool):
                    current_configs[key] = 'True' if value else 'False'
                else:
                    current_configs[key] = str(value)
        
        # 写入配置文件
        write_env_file(current_configs)
        
        # 返回更新后的通用设置
        return await get_common_settings()
    except Exception as e:
        logger.error(f"更新通用设置失败: {e}")
        raise Exception(f"更新通用设置失败: {str(e)}")

async def restart_service() -> Dict[str, str]:
    """
    重启服务的函数
    在systemctl部署环境中，通过systemctl命令重启服务
    """
    try:
        logger.info("开始重启服务...")
        
        # 定义后台重启任务
        async def delayed_restart():
            # 延迟1秒执行，确保当前请求能正常返回
            await asyncio.sleep(1)
            
            # 使用systemctl重启服务
            # 假设服务名称为 blackpotbpanel
            service_name = "Blackpotbpanel"
            
            # 异步执行systemctl命令
            process = await asyncio.create_subprocess_exec(
                "/usr/bin/systemctl", "restart", service_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 等待命令执行完成
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info("服务重启命令执行成功")
            else:
                error_msg = stderr.decode().strip() if stderr else "未知错误"
                logger.error(f"服务重启失败: {error_msg}")
        
        # 创建后台任务执行重启操作，不阻塞当前请求
        asyncio.create_task(delayed_restart())
        
        # 立即返回响应，不等待重启完成
        return {
            "status": "success", 
            "message": "服务重启命令已发送，服务将在1秒后重启"
        }
        
    except Exception as e:
        logger.error(f"重启服务时发生错误: {str(e)}")
        raise Exception(f"重启服务失败: {str(e)}")


def get_ssl_cert_content() -> Dict[str, str]:
    """
    获取SSL证书和私钥文件内容
    
    Returns:
        Dict[str, str]: 包含证书和私钥内容的字典
    """
    try:
        # 证书文件路径
        ssl_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "ssl")
        cert_path = os.path.join(ssl_dir, "ssl.crt")
        key_path = os.path.join(ssl_dir, "ssl.key")
        
        # 读取证书内容
        cert_content = None
        if os.path.exists(cert_path):
            with open(cert_path, "r", encoding="utf-8") as f:
                cert_content = f.read()
        
        # 读取私钥内容
        key_content = None
        if os.path.exists(key_path):
            with open(key_path, "r", encoding="utf-8") as f:
                key_content = f.read()
        
        return {
            "cert_content": cert_content,
            "key_content": key_content
        }
    except Exception as e:
        logger.error(f"读取SSL证书内容失败: {e}")
        raise Exception(f"读取SSL证书内容失败: {str(e)}")

async def update_ssl_cert_content(cert_content: Optional[str] = None, key_content: Optional[str] = None) -> Dict[str, str]:
    """
    更新SSL证书和私钥文件内容
    
    Args:
        cert_content: 证书内容
        key_content: 私钥内容
    
    Returns:
        Dict[str, str]: 操作结果
    """
    try:
        # 证书文件路径
        ssl_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "ssl")
        cert_path = os.path.join(ssl_dir, "ssl.crt")
        key_path = os.path.join(ssl_dir, "ssl.key")
        
        # 确保SSL目录存在
        if not os.path.exists(ssl_dir):
            os.makedirs(ssl_dir, exist_ok=True)
            logger.info(f"创建SSL目录: {ssl_dir}")
        
        # 写入证书内容（如果提供）
        if cert_content is not None:
            with open(cert_path, "w", encoding="utf-8") as f:
                f.write(cert_content)
            logger.info(f"更新SSL证书文件: {cert_path}")
        
        # 写入私钥内容（如果提供）
        if key_content is not None:
            with open(key_path, "w", encoding="utf-8") as f:
                f.write(key_content)
            logger.info(f"更新SSL私钥文件: {key_path}")
        
        return {
            "status": "success",
            "message": "SSL证书和私钥更新成功"
        }
    except Exception as e:
        logger.error(f"更新SSL证书内容失败: {e}")
        raise Exception(f"更新SSL证书内容失败: {str(e)}")


# ==================== 系统设置功能 ====================

async def get_all_settings() -> dict:
    """获取所有系统设置（合并接口）"""
    try:
        dns_config = get_dns_config()
        swap_info = get_swap_info()
        tz_info = get_timezone_info()
        hosts_data = get_hosts_list()
        mem_disk = get_memory_disk_info()

        return {
            "dns": dns_config,
            "swap": swap_info,
            "timezone": tz_info,
            "hosts": hosts_data,
            "memory_disk": mem_disk,
            "message": "success"
        }
    except Exception as e:
        logger.error(f"Failed to get all system settings: {e}")
        raise Exception(f"Failed to get all system settings: {str(e)}")


# ---------- DNS ----------

def get_dns_config() -> dict:
    dns_str = _read_file('/etc/resolv.conf')
    matches = re.findall(r"nameserver\s+(.+)", dns_str)
    return {
        "dns1": matches[0] if len(matches) > 0 else '',
        "dns2": matches[1] if len(matches) > 1 else ''
    }


def set_dns_config(dns1: str, dns2: Optional[str] = None) -> dict:
    if not _check_ip(dns1):
        raise Exception("主要DNS地址无效")
    if dns2 and not _check_ip(dns2):
        raise Exception("备用DNS地址无效")
    content = f"nameserver {dns1}\n"
    if dns2:
        content += f"nameserver {dns2}\n"
    _write_file('/etc/resolv.conf', content)
    return {"status": True, "message": "DNS settings updated successfully"}


def test_dns(dns1: str, dns2: Optional[str] = None) -> dict:
    if not _check_ip(dns1):
        raise Exception("主要DNS地址无效")
    if dns2 and not _check_ip(dns2):
        raise Exception("备用DNS地址无效")

    backup = _read_file('/etc/resolv.conf')
    try:
        content = f"nameserver {dns1}\n"
        if dns2:
            content += f"nameserver {dns2}\n"
        _write_file('/etc/resolv.conf', content)
        socket.gethostbyname('www.qq.com')
        return {"status": True, "message": "Current DNS is available"}
    except socket.error:
        return {"status": False, "message": "Current DNS is not available"}
    finally:
        _write_file('/etc/resolv.conf', backup)


def _check_ip(ip: str) -> bool:
    try:
        socket.inet_pton(socket.AF_INET, ip)
        return True
    except socket.error:
        pass
    try:
        socket.inet_pton(socket.AF_INET6, ip)
        return True
    except socket.error:
        pass
    return False


# ---------- Swap ----------

def get_swap_info() -> dict:
    swap_info = {"total": 0, "used": 0, "free": 0, "size": 0}
    conf = _read_file('/proc/meminfo')
    total_match = re.search(r"SwapTotal:\s*(\d+) kB", conf)
    free_match = re.search(r"SwapFree:\s*(\d+) kB", conf)
    if total_match:
        swap_info["total"] = int(total_match.group(1)) // 1024
    if free_match:
        swap_info["free"] = int(free_match.group(1)) // 1024
    swap_info["used"] = swap_info["total"] - swap_info["free"]
    swap_file = '/www/swap'
    if os.path.exists(swap_file):
        swap_info["size"] = os.path.getsize(swap_file)
    return swap_info


def set_swap(size: int) -> dict:
    swap_file = '/www/swap'
    if os.path.exists(swap_file):
        _run_cmd(f'swapoff {swap_file}')
        os.remove(swap_file)
        escaped = swap_file.replace('/', '\\/')
        _sed_i(f'/{escaped}/d', '/etc/fstab')

    if size > 0:
        _run_cmd(f'dd if=/dev/zero of={swap_file} bs=1M count={size}')
        _run_cmd(f'mkswap -f {swap_file}')
        _run_cmd(f'swapon {swap_file}')
        _write_file('/etc/fstab', f'\n{swap_file} swap swap defaults 0 0\n', append=True)

    info = get_swap_info()
    info["status"] = True
    info["message"] = "Swap settings updated successfully"
    return info


# ---------- 时区 ----------

def get_timezone_info() -> dict:
    zone_list = ['Asia', 'Africa', 'America', 'Antarctica', 'Arctic',
                 'Atlantic', 'Australia', 'Europe', 'Indian', 'Pacific']
    current_area = 'Asia'
    current_zone = 'Shanghai'

    if os.path.islink('/etc/localtime'):
        real = os.readlink('/etc/localtime')
        parts = real.split('/')
        if len(parts) >= 2:
            current_area = parts[-2]
            current_zone = parts[-1]

    res = []
    for area in zone_list:
        area_path = f'/usr/share/zoneinfo/{area}'
        if os.path.exists(area_path):
            zones = [z for z in os.listdir(area_path) if os.path.isfile(f'{area_path}/{z}')]
            zones.sort()
            res.append({"area": area, "zones": zones})

    return {
        "current_area": current_area,
        "current_zone": current_zone,
        "zone_list": res,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def set_timezone(area: str, zone: str) -> dict:
    target = f'/usr/share/zoneinfo/{area}/{zone}'
    if not os.path.exists(target):
        raise Exception("目标时区不存在")
    if os.path.exists('/etc/localtime'):
        os.remove('/etc/localtime')
    os.symlink(target, '/etc/localtime')
    if os.path.exists('/etc/timezone'):
        _write_file('/etc/timezone', f'{area}/{zone}\n')
    return {"status": True, "message": "Timezone updated successfully"}


def sync_time() -> dict:
    # 方法1: ntplib（NTP协议）
    try:
        import ntplib
        c = ntplib.NTPClient()
        response = c.request('pool.ntp.org', version=3, timeout=5)
        date_str = datetime.fromtimestamp(response.tx_time).strftime("%Y-%m-%d %H:%M:%S")
        _run_cmd(f'date -s "{date_str}"')
        return {"status": True, "message": "Time synchronized successfully"}
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"ntplib同步失败: {e}")

    # 方法2: ntpdate 命令
    try:
        _run_cmd('ntpdate -u pool.ntp.org')
        return {"status": True, "message": "Time synchronized successfully"}
    except Exception as e:
        logger.warning(f"ntpdate命令同步失败: {e}")

    # 方法3: timedatectl
    try:
        _run_cmd('timedatectl set-ntp true')
        _run_cmd('sleep 3')
        _run_cmd('timedatectl set-ntp false')
        return {"status": True, "message": "Time synchronized successfully"}
    except Exception as e:
        logger.warning(f"timedatectl同步失败: {e}")

    # 方法4: HTTP API（阿里云）
    try:
        import urllib.request
        resp = urllib.request.urlopen('http://ntp.aliyun.com/time.txt', timeout=5)
        ts = resp.read().decode().strip()
        date_str = datetime.fromtimestamp(int(float(ts))).strftime("%Y-%m-%d %H:%M:%S")
        _run_cmd(f'date -s "{date_str}"')
        return {"status": True, "message": "Time synchronized successfully"}
    except Exception as e:
        logger.error(f"所有时间同步方式均失败: {e}")
        raise Exception(f"时间同步失败，请检查网络连接")


# ---------- 系统密码 ----------

def set_password(user: str, password: str, confirm_password: str) -> dict:
    if not user:
        raise Exception("Username cannot be empty")
    if " " in password:
        raise Exception("Password cannot contain spaces")
    if password != confirm_password:
        raise Exception("Passwords do not match")
    try:
        result = subprocess.run(
            ['passwd', user],
            input=f'{password}\n{password}\n',
            text=True,
            capture_output=True,
            check=True
        )
        return {"status": True, "message": "Password modified successfully"}
    except subprocess.CalledProcessError as e:
        raise Exception(f"Password modified failed: {e.stderr}")


# ---------- 内存盘 ----------

def get_memory_disk_info() -> dict:
    conf = _read_file('/proc/meminfo')
    mem_total_match = re.search(r"MemTotal:\s*(\d+) kB", conf)
    mem_total = mem_total_match.group(1) if mem_total_match else "0"
    mount_file = _get_plugin_path('mount.json')
    mount_info = {}
    if os.path.exists(mount_file):
        try:
            mount_info = json.loads(_read_file(mount_file))
        except:
            mount_info = {}
    for path in mount_info:
        mount_info[path]['used_size'] = _get_dir_size(path)
    _write_file(mount_file, json.dumps(mount_info))
    return {"mount_info": mount_info, "mem_total": mem_total}


def create_memory_disk(path: str, size: int) -> dict:
    conf = _read_file('/proc/meminfo')
    mem_total = int(re.search(r"MemTotal:\s*(\d+) kB", conf).group(1))
    if size * 1024 > mem_total / 2:
        raise Exception("Memory disk size cannot exceed 50% of physical memory size")
    if not path.startswith('/'):
        raise Exception("Please input absolute path")

    if path == '/tmp':
        os.makedirs('/tmp_backup', exist_ok=True)
        _run_cmd(r'\cp -a -r /tmp/* /tmp_backup/')
    else:
        os.makedirs(path, exist_ok=True)
        if os.path.isdir(path) and os.listdir(path):
            raise Exception("该目录已存在文件，请更换目录")

    _mount_tmpfs(path, size)
    return {"status": True, "message": "Memory disk created successfully"}


def delete_memory_disk(path: str) -> dict:
    mount_file = _get_plugin_path('mount.json')
    mount_info = {}
    if os.path.exists(mount_file):
        mount_info = json.loads(_read_file(mount_file))

    if path in mount_info:
        del mount_info[path]
        _write_file(mount_file, json.dumps(mount_info))
        if path == '/tmp':
            os.makedirs('/tmp_backup', exist_ok=True)
            _run_cmd(r'\cp -a -r /tmp/* /tmp_backup/')
        fstab = _read_file('/etc/fstab')
        fstab = re.sub(rf"tmpfs\s*{re.escape(path)}\s.*?\n", '', fstab)
        _write_file('/etc/fstab', fstab)
        _run_cmd(f'umount {path}')
        if path == '/tmp':
            _run_cmd(r'\cp -a -r /tmp_backup/* /tmp/')
            shutil.rmtree('/tmp_backup', ignore_errors=True)
        return {"status": True, "message": "Unmounted successfully"}
    return {"status": False, "message": "Unmount failed"}


def _mount_tmpfs(mount_path: str, mount_size: int):
    mount_file = _get_plugin_path('mount.json')
    mount_info = json.loads(_read_file(mount_file)) if os.path.exists(mount_file) else {}

    parent = '/'.join(mount_path.split('/')[:-1])
    if parent in mount_info:
        raise Exception("不允许挂载到已挂载的子目录下")

    fstab = _read_file('/etc/fstab')
    statement = f"tmpfs {mount_path} tmpfs size={mount_size}m 0 0\n"
    pattern = rf"tmpfs\s*{re.escape(mount_path)}\s*tmpfs\s*[0-9a-zA-Z\s=]*"
    if re.search(pattern, fstab):
        fstab = re.sub(pattern, statement.strip(), fstab)
    else:
        fstab += statement
    _write_file('/etc/fstab', fstab)
    _run_cmd(f'umount {mount_path}')
    _run_cmd('mount -a')

    mount_info[mount_path] = {"size": mount_size}
    _write_file(mount_file, json.dumps(mount_info))


def _get_plugin_path(filename: str) -> str:
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "system")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, filename)


# ---------- Hosts ----------

def get_hosts_list() -> dict:
    hosts = {}
    for line in _read_file('/etc/hosts').splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            status = 0
            line = line[1:].strip()
        else:
            status = 1
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        ip, domain = parts
        if not _check_ip(ip):
            continue
        hosts[domain] = {"domain": domain, "ip": ip, "status": status}
    return hosts


def add_hosts(domain: str, ip: str) -> dict:
    if not _check_ip(ip):
        raise Exception("IP address format is incorrect")
    lines = _read_file('/etc/hosts').splitlines(keepends=True)
    found = False
    for i, line in enumerate(lines):
        if domain in line:
            lines[i] = f"{ip}\t{domain}\n"
            found = True
            break
    if not found:
        lines.append(f"{ip}\t{domain}\n")
    _write_file('/etc/hosts', ''.join(lines))
    _run_cmd('systemctl restart NetworkManager.service 2>/dev/null || true')
    return {"status": True, "message": "Hosts added successfully"}


def delete_hosts(domain: str) -> dict:
    lines = _read_file('/etc/hosts').splitlines(keepends=True)
    new_lines = [l for l in lines if domain not in l]
    _write_file('/etc/hosts', ''.join(new_lines))
    _run_cmd('systemctl restart NetworkManager.service 2>/dev/null || true')
    return {"status": True, "message": "Hosts deleted successfully"}


def toggle_hosts(domain: str, act: str) -> dict:
    lines = _read_file('/etc/hosts').splitlines(keepends=True)
    for i, line in enumerate(lines):
        if domain in line:
            if act == 'pause' and not line.startswith('#'):
                lines[i] = f"#{line}"
            elif act == 'resume' and line.startswith('#'):
                lines[i] = line.lstrip('#')
    _write_file('/etc/hosts', ''.join(lines))
    _run_cmd('systemctl restart NetworkManager.service 2>/dev/null || true')
    msg = "Hosts paused successfully" if act == 'pause' else "Hosts resumed successfully"
    return {"status": True, "message": msg}


# ---------- 工具函数 ----------

def _read_file(path: str) -> str:
    if not os.path.exists(path):
        return ''
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def _write_file(path: str, content: str, append: bool = False):
    mode = 'a' if append else 'w'
    with open(path, mode, encoding='utf-8') as f:
        f.write(content)


def _run_cmd(cmd: str) -> str:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"Command execution failed: {cmd}, Error: {e}")
        return ''


def _sed_i(pattern: str, file_path: str):
    _run_cmd(f"sed -i '{pattern}' {file_path}")


def _get_dir_size(path: str) -> int:
    try:
        result = _run_cmd(f'du -sb {path} 2>/dev/null')
        if result:
            return int(result.split()[0])
    except:
        pass
    return 0


def _get_distro() -> str:
    try:
        import distro
        return distro.name()
    except:
        try:
            result = _run_cmd('cat /etc/os-release | grep "^NAME="')
            return result.replace('NAME=', '').replace('"', '').strip()
        except:
            return 'linux'