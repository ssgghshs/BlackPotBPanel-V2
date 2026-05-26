import os
import sys
import asyncio
import logging
import subprocess
from typing import Dict, Optional
from app.system import schemas

logger = logging.getLogger(__name__)

# 获取配置文件路径
ENV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "setting.conf")

# 定义不同用户角色可以访问的配置项
ADMIN_CONFIG_FIELDS = [
    'DATABASE_URL', 'APP_NAME', 'VERSION', 'DEBUG', 'SECRET_KEY', 
    'ALGORITHM', 'ACCESS_TOKEN_EXPIRE_MINUTES', 'TIMEZONE', 'ENABLE_DOCS',
    'LANGUAGE', 'THEME', 'LOGIN_NOTIFY', 'RECYCLE', 'HOST', 'PORT', 'SSL_ENABLED'
]
USER_CONFIG_FIELDS = ['APP_NAME', 'VERSION', 'TIMEZONE', 'LANGUAGE', 'THEME', 'LOGIN_NOTIFY', 'RECYCLE']

# 定义不同用户角色可以修改的配置项（VERSION 不允许修改，TIMEZONE、HOST、PORT、SSL_ENABLED 只有管理员可修改）
ADMIN_CONFIG_EDITABLE = [
    'DATABASE_URL', 'APP_NAME', 'DEBUG', 'SECRET_KEY', 
    'ALGORITHM', 'ACCESS_TOKEN_EXPIRE_MINUTES', 'TIMEZONE', 'ENABLE_DOCS',
    'LANGUAGE', 'THEME', 'LOGIN_NOTIFY', 'RECYCLE', 'HOST', 'PORT', 'SSL_ENABLED'
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