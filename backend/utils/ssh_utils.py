import re
import os
import subprocess
import logging
import shutil
import datetime

logger = logging.getLogger(__name__)

class SSHConfigParser:
    """SSH配置文件解析器"""
    
    @staticmethod
    def parse_config_file(config_path: str) -> dict:
        """解析SSH配置文件
        
        Args:
            config_path: SSH配置文件路径
            
        Returns:
            dict: 包含解析后配置的字典
        """
        config = {}
        
        try:
            with open(config_path, 'r') as f:
                content = f.read()
                
                # 解析端口
                port_match = re.search(r'^Port\s+(\d+)', content, re.MULTILINE)
                if port_match:
                    config["port"] = port_match.group(1)
                
                # 解析密码认证
                pass_auth_match = re.search(r'^PasswordAuthentication\s+(yes|no)', content, re.MULTILINE)
                if pass_auth_match:
                    config["passwordAuthentication"] = pass_auth_match.group(1)
                
                # 解析公钥认证
                pubkey_auth_match = re.search(r'^PubkeyAuthentication\s+(yes|no)', content, re.MULTILINE)
                if pubkey_auth_match:
                    config["pubkeyAuthentication"] = pubkey_auth_match.group(1)
                
                # 解析允许root登录
                root_login_match = re.search(r'^PermitRootLogin\s+(yes|no|without-password|forced-commands-only)', content, re.MULTILINE)
                if root_login_match:
                    config["permitRootLogin"] = root_login_match.group(1)
                
                # 解析UseDNS
                use_dns_match = re.search(r'^UseDNS\s+(yes|no)', content, re.MULTILINE)
                if use_dns_match:
                    config["useDNS"] = use_dns_match.group(1)
                    
                # 解析更多配置项可以在这里添加
                
        except Exception as e:
            logger.error(f"解析SSH配置文件 {config_path} 失败: {e}")
            
        return config
    
    @staticmethod
    def update_config_file(config_path: str, updates: dict) -> tuple[bool, str]:
        """更新SSH配置文件
        
        Args:
            config_path: SSH配置文件路径
            updates: 要更新的配置项字典，格式为 {"配置项": "新值"}
            
        Returns:
            tuple[bool, str]: (是否更新成功, 消息)
        """
        try:
            # 检查配置文件是否存在
            if not os.path.exists(config_path):
                return False, f"配置文件不存在: {config_path}"
            
            # 备份原文件
            backup_path = f"{config_path}.bak"
            with open(config_path, 'r') as src:
                with open(backup_path, 'w') as dst:
                    dst.write(src.read())
            
            # 读取原文件内容
            with open(config_path, 'r') as f:
                content = f.read()
            
            # 定义配置项的正则表达式模式（全部使用小写键名以确保匹配正确）
            patterns = {
                "port": r'^Port\s+\d+',
                "passwordauthentication": r'^PasswordAuthentication\s+(yes|no)',
                "pubkeyauthentication": r'^PubkeyAuthentication\s+(yes|no)',
                "permitrootlogin": r'^PermitRootLogin\s+(yes|no|without-password|forced-commands-only)',
                "usedns": r'^UseDNS\s+(yes|no)'
            }
            
            # 配置项对应的正确格式（使用小写键名与patterns字典保持一致）
            formats = {
                "port": "Port {}",
                "passwordauthentication": "PasswordAuthentication {}",
                "pubkeyauthentication": "PubkeyAuthentication {}",
                "permitrootlogin": "PermitRootLogin {}",
                "usedns": "UseDNS {}"
            }
            
            # 检查和更新每个配置项
            for key, value in updates.items():
                # 跳过None值
                if value is None:
                    continue
                
                # 转换键名为小写以匹配patterns字典
                key_lower = key.lower()
                # 确保patterns字典中的键都是小写形式进行匹配
                if key_lower in patterns:
                    # 检查是否存在该配置项
                    if re.search(patterns[key_lower], content, re.MULTILINE):
                        # 替换现有配置
                        content = re.sub(
                            patterns[key_lower],
                            formats[key_lower].format(value),
                            content,
                            flags=re.MULTILINE
                        )
                    else:
                        # 如果不存在，追加到文件末尾
                        content += f"\n{formats[key_lower].format(value)}"
                    
                    logger.info(f"Updated SSH config item {key} to {value}")
            
            # 写入更新后的内容
            with open(config_path, 'w') as f:
                f.write(content)
            
            return True, "SSH配置文件更新成功"
            
        except PermissionError:
            logger.error(f"权限不足，无法写入配置文件: {config_path}")
            return False, "权限不足，无法写入配置文件"
        except Exception as e:
            logger.error(f"更新SSH配置文件 {config_path} 失败: {e}")
            return False, f"更新配置文件失败: {str(e)}"


class SSHServiceChecker:
    """SSH服务状态检查器"""
    
    @staticmethod
    def find_ssh_config() -> str:
        """查找SSH配置文件路径
        
        Returns:
            str: SSH配置文件路径，如果未找到返回空字符串
        """
        # 常见的sshd_config文件路径
        sshd_config_paths = [
            "/etc/ssh/sshd_config",  # Linux
            "/etc/sshd_config",      # 某些系统
            "/usr/local/etc/ssh/sshd_config",  # BSD系统
        ]
        
        # Windows系统的SSH配置路径
        if os.name == 'nt':
            windows_ssh_config = "C:\\ProgramData\\ssh\\sshd_config"
            if os.path.exists(windows_ssh_config):
                return windows_ssh_config
        
        # 检查其他路径
        for path in sshd_config_paths:
            if os.path.exists(path):
                return path
                
        return ""
    
    @staticmethod
    def find_authorized_keys() -> str:
        """查找authorized_keys文件路径
        
        Returns:
            str: authorized_keys文件路径，如果未找到返回空字符串
        """
        # 常见的authorized_keys文件路径
        authorized_keys_paths = []
        
        # Linux/Unix系统路径
        if os.name != 'nt':
            # 系统级authorized_keys
            authorized_keys_paths.append("/etc/ssh/authorized_keys")
            # root用户的authorized_keys
            authorized_keys_paths.append("/root/.ssh/authorized_keys")
            # 当前用户的authorized_keys
            home_dir = os.path.expanduser("~")
            authorized_keys_paths.append(os.path.join(home_dir, ".ssh", "authorized_keys"))
        else:
            # Windows系统路径
            # 当前用户的authorized_keys
            home_dir = os.path.expanduser("~")
            authorized_keys_paths.append(os.path.join(home_dir, ".ssh", "authorized_keys"))
            # 系统级authorized_keys
            authorized_keys_paths.append("C:\\ProgramData\\ssh\\administrators_authorized_keys")
        
        # 检查路径是否存在
        for path in authorized_keys_paths:
            if os.path.exists(path):
                return path
                
        return ""
    
    @staticmethod
    def is_ssh_installed() -> bool:
        """检查SSH是否安装
        
        Returns:
            bool: SSH是否安装
        """
        # 通过查找配置文件来判断是否安装
        config_path = SSHServiceChecker.find_ssh_config()
        if config_path:
            return True
        
        # Windows系统特殊检查
        if os.name == 'nt':
            try:
                result = subprocess.run(["powershell", "Get-WindowsCapability", "-Online", "-Name", "OpenSSH.Server*"], 
                                       capture_output=True, text=True, timeout=10)
                if "State : Installed" in result.stdout:
                    return True
            except Exception as e:
                logger.error(f"检查Windows SSH安装状态失败: {e}")
        
        # 检查SSH命令是否可用
        try:
            # 尝试运行sshd命令检查版本
            commands = ["/usr/bin/sshd", "--version"]
            subprocess.run(commands, capture_output=True, text=True, timeout=5)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
                pass
                
        return False
    
    @staticmethod
    def get_ssh_config_content() -> tuple[str, str, bool]:
        """获取SSH配置文件的路径和内容
        
        Returns:
            tuple[str, str, bool]: (配置文件路径, 配置文件内容, 是否成功)
        """
        try:
            # 查找配置文件路径
            config_path = SSHServiceChecker.find_ssh_config()
            if not config_path:
                return "", "配置文件不存在", False
            
            # 读取配置文件内容
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            return config_path, content, True
            
        except PermissionError:
            logger.error(f"权限不足，无法读取配置文件")
            return "", "权限不足，无法读取配置文件", False
        except UnicodeDecodeError:
            # 尝试使用其他编码读取
            try:
                config_path = SSHServiceChecker.find_ssh_config()
                with open(config_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                return config_path, content, True
            except Exception as e:
                logger.error(f"读取配置文件时编码错误: {e}")
                return "", f"读取配置文件时编码错误: {str(e)}", False
        except Exception as e:
            logger.error(f"获取SSH配置文件内容失败: {e}")
            return "", f"获取配置文件内容失败: {str(e)}", False
    
    @staticmethod
    async def get_ssh_config_content_async() -> tuple[str, str, bool]:
        """异步获取SSH配置文件的路径和内容
        
        Returns:
            tuple[str, str, bool]: (配置文件路径, 配置文件内容, 是否成功)
        """
        import asyncio
        import functools
        
        loop = asyncio.get_event_loop()
        # 使用线程池执行器来运行阻塞的文件读取操作
        return await loop.run_in_executor(
            None, 
            functools.partial(SSHServiceChecker._sync_get_ssh_config_content)
        )
    
    @staticmethod
    def _sync_get_ssh_config_content() -> tuple[str, str, bool]:
        """同步获取SSH配置文件的路径和内容（在异步方法中在线程池中运行）
        
        Returns:
            tuple[str, str, bool]: (配置文件路径, 配置文件内容, 是否成功)
        """
        try:
            # 查找配置文件路径
            config_path = SSHServiceChecker.find_ssh_config()
            if not config_path:
                return "", "配置文件不存在", False
            
            # 读取配置文件内容
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            return config_path, content, True
            
        except PermissionError:
            logger.error(f"权限不足，无法读取配置文件")
            return "", "权限不足，无法读取配置文件", False
        except UnicodeDecodeError:
            # 尝试使用其他编码读取
            try:
                config_path = SSHServiceChecker.find_ssh_config()
                with open(config_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                return config_path, content, True
            except Exception as e:
                logger.error(f"读取配置文件时编码错误: {e}")
                return "", f"读取配置文件时编码错误: {str(e)}", False
        except Exception as e:
            logger.error(f"获取SSH配置文件内容失败: {e}")
            return "", f"获取配置文件内容失败: {str(e)}", False
    
    @staticmethod
    def get_authorized_keys_content() -> tuple[str, str, bool]:
        """获取authorized_keys文件的路径和内容
        
        Returns:
            tuple[str, str, bool]: (authorized_keys文件路径, 文件内容, 是否成功)
        """
        try:
            # 查找authorized_keys文件路径
            keys_path = SSHServiceChecker.find_authorized_keys()
            if not keys_path:
                return "", "authorized_keys文件不存在", False
            
            # 读取authorized_keys文件内容
            with open(keys_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            return keys_path, content, True
            
        except PermissionError:
            logger.error(f"权限不足，无法读取authorized_keys文件")
            return "", "权限不足，无法读取authorized_keys文件", False
        except UnicodeDecodeError:
            # 尝试使用其他编码读取
            try:
                keys_path = SSHServiceChecker.find_authorized_keys()
                with open(keys_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                return keys_path, content, True
            except Exception as e:
                logger.error(f"读取authorized_keys文件时编码错误: {e}")
                return "", f"读取authorized_keys文件时编码错误: {str(e)}", False
        except Exception as e:
            logger.error(f"获取authorized_keys文件内容失败: {e}")
            return "", f"获取authorized_keys文件内容失败: {str(e)}", False
    
    @staticmethod
    async def get_authorized_keys_content_async() -> tuple[str, str, bool]:
        """异步获取authorized_keys文件的路径和内容
        
        Returns:
            tuple[str, str, bool]: (authorized_keys文件路径, 文件内容, 是否成功)
        """
        import asyncio
        import functools
        
        loop = asyncio.get_event_loop()
        # 使用线程池执行器来运行阻塞的文件读取操作
        return await loop.run_in_executor(
            None, 
            functools.partial(SSHServiceChecker._sync_get_authorized_keys_content)
        )
    
    @staticmethod
    def _sync_get_authorized_keys_content() -> tuple[str, str, bool]:
        """同步获取authorized_keys文件的路径和内容（在异步方法中在线程池中运行）
        
        Returns:
            tuple[str, str, bool]: (authorized_keys文件路径, 文件内容, 是否成功)
        """
        try:
            # 查找authorized_keys文件路径
            keys_path = SSHServiceChecker.find_authorized_keys()
            if not keys_path:
                return "", "authorized_keys文件不存在", False
            
            # 读取authorized_keys文件内容
            with open(keys_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            return keys_path, content, True
            
        except PermissionError:
            logger.error(f"权限不足，无法读取authorized_keys文件")
            return "", "权限不足，无法读取authorized_keys文件", False
        except UnicodeDecodeError:
            # 尝试使用其他编码读取
            try:
                keys_path = SSHServiceChecker.find_authorized_keys()
                with open(keys_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                return keys_path, content, True
            except Exception as e:
                logger.error(f"读取authorized_keys文件时编码错误: {e}")
                return "", f"读取authorized_keys文件时编码错误: {str(e)}", False
        except Exception as e:
            logger.error(f"获取authorized_keys文件内容失败: {e}")
            return "", f"获取authorized_keys文件内容失败: {str(e)}", False
    
    @staticmethod
    def is_ssh_running() -> bool:
        """检查SSH服务是否正在运行
        
        Returns:
            bool: SSH服务是否正在运行
        """
        # 首先尝试通过服务管理命令检查状态
        # Windows系统特殊处理
        if os.name == 'nt':
            try:
                # 使用PowerShell检查sshd服务状态
                result = subprocess.run(["powershell", "Get-Service", "sshd"], 
                                      capture_output=True, text=True, timeout=5)
                # 精确检查服务状态，只在明确显示Running时返回True
                if "Status      : Running" in result.stdout or "状态      : 正在运行" in result.stdout:
                    return True
                # 如果明确显示Stopped，则直接返回False
                elif "Status      : Stopped" in result.stdout or "状态      : 已停止" in result.stdout:
                    return False
            except Exception as e:
                logger.error(f"检查Windows SSH服务状态失败: {e}")
        
        # Linux/Unix系统检查
        else:
            try:
                # 尝试使用不同的命令检查SSH服务状态
                status_commands = [
                    ["/usr/bin/systemctl", "is-active", "sshd"],
                    ["/usr/bin/service", "sshd", "status"],
                    ["/usr/bin/service", "ssh", "status"],
                    ["/etc/init.d/sshd", "status"],
                    ["/etc/init.d/ssh", "status"]
                ]
                
                for cmd in status_commands:
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                        # 对于systemctl is-active，只有返回active才表示运行中
                        if cmd[0] == "systemctl" and cmd[1] == "is-active":
                            if result.returncode == 0 and "active" in result.stdout.lower():
                                return True
                        # 其他命令检查更严格的条件
                        elif result.returncode == 0 and ("active (running)" in result.stdout.lower() or "running" in result.stdout.lower()):
                            return True
                        # 如果命令执行成功但明确显示inactive，则直接返回False
                        elif result.returncode != 0 and "inactive" in result.stdout.lower():
                            return False
                    except (subprocess.SubprocessError, FileNotFoundError):
                        continue
            except Exception as e:
                logger.error(f"检查SSH服务状态失败: {e}")
        
        # 作为备选方案，检查22端口是否在监听（但这不是最可靠的方法）
        # 注意：端口监听可能存在延迟或其他程序占用的情况
        try:
            # 使用更严格的端口检查方法，确保是sshd进程在监听
            if os.name == 'nt':
                # Windows使用PowerShell获取更详细的进程信息
                try:
                    # 查找监听22端口的进程
                    result = subprocess.run(["powershell", "Get-NetTCPConnection -LocalPort 22 -State Listen | Select-Object OwningProcess"], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and "OwningProcess" in result.stdout and not "无匹配" in result.stdout:
                        # 获取进程ID
                        pid_match = re.search(r'\d+', result.stdout)
                        if pid_match:
                            pid = pid_match.group()
                            # 检查进程名称
                            proc_result = subprocess.run(["powershell", f"Get-Process -Id {pid} | Select-Object ProcessName"], 
                                                       capture_output=True, text=True, timeout=5)
                            # 检查是否是sshd进程
                            if "sshd" in proc_result.stdout.lower():
                                return True
                except Exception:
                    # 如果上面的命令失败，退回到简单的netstat检查
                    result = subprocess.run(["/usr/bin/netstat", "-ano"], capture_output=True, text=True, timeout=5)
                    if ":22" in result.stdout and "LISTENING" in result.stdout:
                        # 记录警告，表示这种方式不够准确
                        logger.warning("使用简单端口检查判断SSH状态，结果可能不准确")
            else:
                # Unix/Linux使用更可靠的端口和进程检查
                try:
                    # 使用lsof检查是否是sshd进程监听22端口
                    result = subprocess.run(["/usr/bin/lsof", "-i", ":22", "-sTCP:LISTEN"], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and "sshd" in result.stdout:
                        return True
                except (subprocess.SubprocessError, FileNotFoundError):
                    # 如果lsof不可用，尝试netstat或ss但只作为参考
                    for cmd in [["/usr/bin/netstat", "-tlnp"], ["/usr/bin/ss", "-tlnp"]]:
                        try:
                            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                            # 寻找sshd进程监听22端口的明确证据
                            if re.search(r':22\s+.*sshd', result.stdout):
                                return True
                        except (subprocess.SubprocessError, FileNotFoundError):
                            continue
        except Exception as e:
            logger.error(f"检查SSH端口状态失败: {e}")
        
        # 默认返回False，表示服务未运行
        return False
    
    @staticmethod
    def operate_ssh_service(action: str) -> tuple[bool, str]:
        """操作SSH服务（启动/停止/重启）
        
        Args:
            action: 操作类型，支持 'start', 'stop', 'restart'
            
        Returns:
            tuple[bool, str]: (操作是否成功, 操作消息)
        """
        if action not in ['start', 'stop', 'restart']:
            return False, f"不支持的操作类型: {action}"
        
        # Windows系统处理
        if os.name == 'nt':
            try:
                # 使用PowerShell操作服务
                if action == 'start':
                    cmd = ["powershell", "Start-Service", "sshd"]
                    success_msg = "SSH服务已成功启动"
                    error_msg = "启动SSH服务失败"
                elif action == 'stop':
                    cmd = ["powershell", "Stop-Service", "sshd"]
                    success_msg = "SSH服务已成功停止"
                    error_msg = "停止SSH服务失败"
                else:  # restart
                    cmd = ["powershell", "Restart-Service", "sshd"]
                    success_msg = "SSH服务已成功重启"
                    error_msg = "重启SSH服务失败"
                
                # 执行命令
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    return True, success_msg
                else:
                    error_detail = result.stderr.strip() if result.stderr.strip() else result.stdout.strip()
                    return False, f"{error_msg}: {error_detail}"
            except Exception as e:
                logger.error(f"Windows操作SSH服务失败: {e}")
                return False, f"操作SSH服务时发生异常: {str(e)}"
        
        # Linux/Unix系统处理
        try:
            # 定义不同的服务管理命令模板
            command_templates = [
                ["/usr/bin/systemctl", action, "sshd"],
                ["/usr/bin/service", "sshd", action],
                ["/usr/bin/service", "ssh", action],
                [f"/etc/init.d/sshd", action],
                [f"/etc/init.d/ssh", action]
            ]
            
            # 尝试不同的命令直到成功
            for cmd_template in command_templates:
                try:
                    # 尝试执行命令
                    result = subprocess.run(cmd_template, capture_output=True, text=True, timeout=15)
                    
                    # 检查命令是否成功执行
                    if result.returncode == 0:
                        # 确定成功消息
                        if action == 'start':
                            success_msg = "SSH服务已成功启动"
                        elif action == 'stop':
                            success_msg = "SSH服务已成功停止"
                        else:  # restart
                            success_msg = "SSH服务已成功重启"
                        return True, success_msg
                    
                except (subprocess.SubprocessError, FileNotFoundError):
                    # 命令不存在或执行失败，尝试下一个
                    continue
            
            # 所有命令都失败
            return False, f"无法执行{action}操作，可能需要管理员权限或SSH服务不存在"
            
        except Exception as e:
            logger.error(f"操作SSH服务失败: {e}")
            return False, f"操作SSH服务时发生异常: {str(e)}"
    
    @staticmethod
    def update_ssh_config(config_updates: dict) -> tuple[bool, str]:
        """更新SSH配置并重启服务以应用更改
        
        Args:
            config_updates: 要更新的配置项字典
            
        Returns:
            tuple[bool, str]: (是否更新成功, 消息)
        """
        # 获取SSH配置文件路径
        config_path = SSHServiceChecker.find_ssh_config()
        if not config_path:
            return False, "无法确定SSH配置文件路径"
        
        # 使用SSHConfigParser更新配置文件
        success, message = SSHConfigParser.update_config_file(config_path, config_updates)
        if not success:
            return success, message
        
        # 更新成功后，尝试重启SSH服务以应用更改
        # 先检查服务是否在运行
        was_running = SSHServiceChecker.is_ssh_running()
        
        # 重启SSH服务
        _, restart_message = SSHServiceChecker.operate_ssh_service("restart")
        
        # 如果服务原本在运行，返回重启消息；如果原本未运行，保持未运行状态
        if was_running:
            return success, f"{message}，已重启SSH服务以应用更改"
        else:
            # 如果服务原本未运行，重启后停止服务，保持原来的状态
            SSHServiceChecker.operate_ssh_service("stop")
            return success, f"{message}，配置已更新但SSH服务仍处于停止状态"


def get_default_ssh_config() -> dict:
    """获取默认SSH配置
    
    Returns:
        dict: 默认SSH配置字典
    """
    return {
        "port": "22",
        "passwordAuthentication": "yes",
        "pubkeyAuthentication": "yes",
        "permitRootLogin": "yes",
        "useDNS": "yes"
    }


class SSHLogReader:
    """SSH日志读取器，用于获取和解析SSH登录日志"""
    
    # 常见的SSH日志文件路径
    SSH_LOG_PATHS = [
        "/var/log/secure",       # CentOS/RHEL
        "/var/log/auth.log",     # Debian/Ubuntu
        "/var/log/messages",     # 某些系统
        "/var/log/sshd.log",     # 自定义路径
    ]
    
    @staticmethod
    def find_ssh_log_file() -> str:
        """查找SSH日志文件路径
        
        Returns:
            str: SSH日志文件路径，如果未找到返回空字符串
        """
        # 检查常见的日志文件路径
        for path in SSHLogReader.SSH_LOG_PATHS:
            if os.path.exists(path):
                return path
                
        # Windows系统检查
        if os.name == 'nt':
            windows_log_paths = [
                "C:\ProgramData\ssh\logs\sshd.log",
                "C:\Windows\System32\winevt\Logs\Security.evtx",  # Windows事件日志
            ]
            for path in windows_log_paths:
                if os.path.exists(path):
                    return path
                    
        return ""
    
    @staticmethod
    def parse_ssh_log_entry(log_line: str) -> dict:
        """解析单行SSH日志条目
        
        Args:
            log_line: 日志行字符串
            
        Returns:
            dict: 解析后的日志条目字典，如果不是SSH登录日志则返回None
        """
        
        # 尝试解析成功登录
        success_pattern = r'(\w+\s+\d+\s+\d+:\d+:\d+)\s+[^\s]+\s+sshd\[\d+\]:\s+Accepted\s+(password|publickey)\s+for\s+(\w+)\s+from\s+([\d\.]+)\s+port\s+(\d+)'
        success_match = re.search(success_pattern, log_line)
        
        if success_match:
            # 获取原始时间字符串
            raw_time = success_match.group(1)
            # 添加当前年份并重新格式化
            current_year = datetime.datetime.now().year
            formatted_time = SSHLogReader._format_log_time(raw_time, current_year)
            
            return {
                "time": formatted_time,
                "method": success_match.group(2),
                "username": success_match.group(3),
                "ip": success_match.group(4),
                "port": success_match.group(5),
                "status": "success",
                "raw": log_line
            }
        
        # 尝试解析失败登录
        failed_pattern = r'(\w+\s+\d+\s+\d+:\d+:\d+)\s+[^\s]+\s+sshd\[\d+\]:\s+Failed\s+(password|publickey)\s+for\s+(invalid\s+user\s+)?(\w+)?\s+from\s+([\d\.]+)\s+port\s+(\d+)'
        failed_match = re.search(failed_pattern, log_line)
        
        if failed_match:
            username = failed_match.group(4) if failed_match.group(4) else "invalid"
            # 获取原始时间字符串
            raw_time = failed_match.group(1)
            # 添加当前年份并重新格式化
            current_year = datetime.datetime.now().year
            formatted_time = SSHLogReader._format_log_time(raw_time, current_year)
            
            return {
                "time": formatted_time,
                "method": failed_match.group(2),
                "username": username,
                "ip": failed_match.group(5),
                "port": failed_match.group(6),
                "status": "failed",
                "raw": log_line
            }
        
        return None
    
    @staticmethod
    def get_ssh_logs(start: int = 0, limit: int = 100, keyword: str = None, status: str = None) -> tuple[list, int]:
        """获取SSH登录日志
        
        Args:
            start: 起始索引
            limit: 返回条数限制
            keyword: 搜索关键字
            status: 状态过滤，可选值: 'success', 'failed', None
            
        Returns:
            tuple[list, int]: (日志条目列表, 总条数)
        """
        try:
            # 查找日志文件
            log_path = SSHLogReader.find_ssh_log_file()
            if not log_path:
                logger.error("未找到SSH日志文件")
                return [], 0
            
            # 读取日志文件内容
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                log_lines = f.readlines()
            
            # 解析和过滤日志
            parsed_logs = []
            for line in reversed(log_lines):  # 倒序读取，最新的在前面
                parsed = SSHLogReader.parse_ssh_log_entry(line.strip())
                if parsed:
                    # 应用过滤条件
                    match_keyword = True
                    match_status = True
                    
                    if keyword:
                        match_keyword = (keyword.lower() in parsed['username'].lower() or 
                                        keyword.lower() in parsed['ip'].lower())
                    
                    if status:
                        match_status = (parsed['status'] == status)
                    
                    if match_keyword and match_status:
                        parsed_logs.append(parsed)
            
            # 计算总数和分页
            total = len(parsed_logs)
            paginated_logs = parsed_logs[start:start + limit]
            
            return paginated_logs, total
            
        except PermissionError:
            logger.error(f"权限不足，无法读取日志文件: {log_path}")
            return [], 0
        except Exception as e:
            logger.error(f"获取SSH登录日志失败: {e}")
            return [], 0
    
    @staticmethod
    def _format_log_time(raw_time: str, year: int) -> str:
        """将原始日志时间字符串格式化为带年份的标准格式
        
        Args:
            raw_time: 原始时间字符串，格式如 "Nov 22 00:46:20"
            year: 要添加的年份
            
        Returns:
            str: 格式化后的时间字符串，格式如 "2025-11-22 00:46:20"
        """
        try:
            # 解析原始时间字符串
            dt = datetime.datetime.strptime(raw_time, "%b %d %H:%M:%S")
            # 添加年份
            dt = dt.replace(year=year)
            # 返回格式化后的时间字符串
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            # 如果解析失败，返回原始时间字符串
            return raw_time
    
    @staticmethod
    def get_ssh_logs_by_command(start: int = 0, limit: int = 100, keyword: str = None, status: str = None) -> tuple[list, int]:
        """使用命令行工具获取SSH登录日志（适用于无法直接读取日志文件的情况）
        
        Args:
            start: 起始索引
            limit: 返回条数限制
            keyword: 搜索关键字
            status: 状态过滤，可选值: 'success', 'failed', None
            
        Returns:
            tuple[list, int]: (日志条目列表, 总条数)
        """
        try:
            # 根据操作系统选择命令
            if os.name == 'nt':
                # Windows系统使用PowerShell查询事件日志
                cmd = ["powershell", "Get-WinEvent", "-FilterHashtable", 
                       "@{LogName='Security'; ID=4624,4625}", "-MaxEvents", "1000"]
            else:
                # Linux/Unix系统使用grep搜索日志
                cmd_parts = ["/usr/bin/grep", "sshd", "-E", 
                             "(Accepted|Failed) (password|publickey) for"]
                
                # 添加日志文件路径
                log_path = SSHLogReader.find_ssh_log_file()
                if log_path:
                    cmd_parts.append(log_path)
                else:
                    # 如果找不到日志文件，尝试搜索所有可能的位置
                    cmd_parts.extend(["/var/log/auth.log", "/var/log/secure", "/var/log/messages"])
                
                cmd = cmd_parts
            
            # 执行命令
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            # 处理结果
            log_lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # 解析和过滤日志
            parsed_logs = []
            for line in reversed(log_lines):
                parsed = SSHLogReader.parse_ssh_log_entry(line.strip())
                if parsed:
                    # 应用过滤条件
                    match_keyword = True
                    match_status = True
                    
                    if keyword:
                        match_keyword = (keyword.lower() in parsed['username'].lower() or 
                                        keyword.lower() in parsed['ip'].lower())
                    
                    if status:
                        match_status = (parsed['status'] == status)
                    
                    if match_keyword and match_status:
                        parsed_logs.append(parsed)
            
            # 计算总数和分页
            total = len(parsed_logs)
            paginated_logs = parsed_logs[start:start + limit]
            
            return paginated_logs, total
            
        except subprocess.SubprocessError as e:
            logger.error(f"执行命令获取SSH日志失败: {e}")
            return [], 0
        except Exception as e:
            logger.error(f"使用命令行获取SSH登录日志失败: {e}")
            return [], 0
    
    @staticmethod
    def clean_ssh_logs(before_date: str = None, keep_days: int = None) -> tuple[bool, str, int]:
        """清理SSH登录日志
        
        Args:
            before_date: 删除此日期之前的日志，格式: 'YYYY-MM-DD'
            keep_days: 保留最近N天的日志，删除更早的日志
            
        Returns:
            tuple[bool, str, int]: (是否成功, 消息, 清理的日志数量)
        """
        try:
            # 确定截止日期
            cutoff_date = None
            if before_date:
                try:
                    cutoff_date = datetime.datetime.strptime(before_date, "%Y-%m-%d").date()
                except ValueError:
                    return False, "无效的日期格式，请使用YYYY-MM-DD格式", 0
            elif keep_days is not None:
                if not isinstance(keep_days, int) or keep_days < 0:
                    return False, "保留天数必须是非负整数", 0
                current_date = datetime.datetime.now().date()
                cutoff_date = current_date - datetime.timedelta(days=keep_days)
            else:
                return False, "必须提供截止日期或保留天数", 0
            
            # 查找日志文件
            log_path = SSHLogReader.find_ssh_log_file()
            if not log_path:
                return False, "未找到SSH日志文件", 0
            
            # 读取原始日志
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                log_lines = f.readlines()
            
            # 过滤日志行
            preserved_lines = []
            cleaned_count = 0
            current_year = datetime.datetime.now().year
            
            # 特殊处理：当keep_days=0时，清理所有SSH日志
            is_full_cleanup = (keep_days == 0)
            
            for line in log_lines:
                parsed = SSHLogReader.parse_ssh_log_entry(line.strip())
                if parsed:
                    if is_full_cleanup:
                        # 完全清理模式：所有SSH登录日志都删除
                        cleaned_count += 1
                    else:
                        # 正常模式：根据日期过滤
                        # 解析日志时间
                        log_time_str = parsed['time']
                        try:
                            # 尝试解析完整时间格式
                            log_date = datetime.datetime.strptime(log_time_str, "%Y-%m-%d %H:%M:%S").date()
                        except ValueError:
                            # 如果解析失败，保留该行
                            preserved_lines.append(line)
                            continue
                        
                        # 比较日期决定是否保留
                        if log_date >= cutoff_date:
                            preserved_lines.append(line)
                        else:
                            cleaned_count += 1
                else:
                    # 不是SSH登录日志，保留
                    preserved_lines.append(line)
            
            # 写回过滤后的日志
            # 在生产环境中，建议先备份原始日志
            backup_path = f"{log_path}.bak.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            try:
                # 先备份
                shutil.copy2(log_path, backup_path)
                # 再写入新内容
                with open(log_path, 'w', encoding='utf-8', errors='ignore') as f:
                    f.writelines(preserved_lines)
            except PermissionError:
                return False, "权限不足，无法修改日志文件", 0
            except Exception as e:
                logger.error(f"写入日志文件失败: {e}")
                return False, f"写入日志文件失败: {str(e)}", 0
            
            # Windows系统特殊处理：如果是事件日志，可能需要使用PowerShell清理
            if os.name == 'nt' and log_path.endswith('.evtx'):
                try:
                    # 转换cutoff_date为PowerShell格式
                    ps_date_format = cutoff_date.strftime("%Y-%m-%d")
                    # 使用PowerShell清理事件日志
                    ps_command = f"Get-WinEvent -FilterHashtable @{{LogName='Security'; ID=4624,4625}} | Where-Object {{$_.TimeCreated -lt '{ps_date_format}'}} | Remove-WinEvent"
                    result = subprocess.run(["powershell", "-Command", ps_command], 
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode != 0:
                        logger.warning(f"Windows事件日志清理可能不完全: {result.stderr}")
                except Exception as e:
                    logger.warning(f"清理Windows事件日志时发生警告: {e}")
                    # 不返回错误，因为文件日志已经清理成功
            
            return True, f"成功清理了{cleaned_count}条日志记录", cleaned_count
            
        except PermissionError:
            logger.error(f"权限不足，无法读取日志文件")
            return False, "权限不足，无法读取日志文件", 0
        except Exception as e:
            logger.error(f"清理SSH登录日志失败: {e}")
            return False, f"清理SSH登录日志失败: {str(e)}", 0