"""
SSH连接服务模块
"""
import paramiko
import asyncio
from typing import Optional, Tuple, Any
import logging
from io import StringIO
from paramiko import RSAKey, Ed25519Key, DSSKey, ECDSAKey

logger = logging.getLogger(__name__)

class SSHConnectionError(Exception):
    """SSH连接异常"""
    pass

class SSHService:
    """SSH服务类"""
    
    @staticmethod
    def _load_private_key(private_key_content: str, password: Optional[str] = None) -> Optional[Any]:
        """
        加载不同格式的私钥
        
        Args:
            private_key_content: 私钥内容
            password: 私钥密码（可选）
            
        Returns:
            加载成功的密钥对象，失败返回None
        """
        # 验证输入
        if not private_key_content or not isinstance(private_key_content, str):
            logger.error("无效的私钥内容")
            return None
            
        key_file = StringIO(private_key_content)
        key_types = [
            (RSAKey, "RSA"),
            (Ed25519Key, "ED25519"),
            (DSSKey, "DSA"),
            (ECDSAKey, "ECDSA")
        ]
        
        # 记录尝试的密钥格式和错误
        attempted_formats = []
        
        for key_class, key_name in key_types:
            try:
                # 重置文件指针
                key_file.seek(0)
                
                if password:
                    pkey = key_class.from_private_key(key_file, password=password)
                else:
                    pkey = key_class.from_private_key(key_file)
                
                logger.info(f"成功加载{key_name}格式密钥")
                return pkey
            except paramiko.PasswordRequiredException:
                # 需要密码但未提供
                # logger.debug(f"{key_name}密钥需要密码")
                attempted_formats.append(f"{key_name}: 需要密码")
            except paramiko.SSHException as e:
                # SSH相关错误
                # logger.debug(f"尝试加载{key_name}格式密钥失败: {str(e)}")
                attempted_formats.append(f"{key_name}: {str(e)}")
            except Exception as e:
                # 其他未预期的错误
                logger.error(f"加载{key_name}格式密钥时发生未预期错误: {str(e)}", exc_info=True)
                attempted_formats.append(f"{key_name}: 未预期错误")
        
        # 所有格式都尝试失败
        logger.warning(f"无法加载私钥，尝试了以下格式: {attempted_formats}")
        return None
    
    @staticmethod
    async def test_ssh_connection(
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        private_key_password: Optional[str] = None,
        timeout: int = 10
    ) -> Tuple[bool, str]:
        """
        测试SSH连接
        
        Args:
            host: 主机地址
            port: 端口
            username: 用户名
            password: 密码（密码认证时使用）
            private_key: 私钥内容（密钥认证时使用）
            private_key_password: 私钥密码（用于解密私钥）
            timeout: 连接超时时间
            
        Returns:
            Tuple[bool, str]: (连接是否成功, 结果信息)
        """
        def _connect_and_test():
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                # 根据认证方式连接
                if password:
                    # 密码认证
                    ssh_client.connect(
                        hostname=host,
                        port=port,
                        username=username,
                        password=password,
                        timeout=timeout
                    )
                elif private_key:
                    # 密钥认证 - 使用通用密钥加载函数
                    pkey = SSHService._load_private_key(private_key, private_key_password)
                    if pkey:
                        ssh_client.connect(
                            hostname=host,
                            port=port,
                            username=username,
                            pkey=pkey,
                            timeout=timeout
                        )
                    else:
                        return False, "无法加载私钥，不支持的密钥格式或密码错误"
                else:
                    return False, "未提供有效的认证信息"
                
                # 执行简单命令测试连接
                stdin, stdout, stderr = ssh_client.exec_command("echo 'SSH连接测试成功'")
                
                output = stdout.read().decode().strip()
                error = stderr.read().decode().strip()
                
                if error:
                    return False, f"SSH连接测试失败: {error}"
                    
                return True, output
                
            except paramiko.AuthenticationException:
                return False, "SSH认证失败，请检查用户名和密码/密钥"
            except paramiko.SSHException as e:
                return False, f"SSH连接错误: {str(e)}"
            except Exception as e:
                return False, f"SSH连接失败: {str(e)}"
            finally:
                ssh_client.close()
        
        # 在线程池中执行阻塞的SSH连接操作
        return await asyncio.get_event_loop().run_in_executor(None, _connect_and_test)
    
    @staticmethod
    async def execute_ssh_command(
        host: str,
        port: int,
        username: str,
        command: str,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        private_key_password: Optional[str] = None,
        timeout: int = 30
    ) -> Tuple[bool, str, str]:
        """
        执行SSH命令
        
        Args:
            host: 主机地址
            port: 端口
            username: 用户名
            command: 要执行的命令
            password: 密码（密码认证时使用）
            private_key: 私钥内容（密钥认证时使用）
            private_key_password: 私钥密码（用于解密私钥）
            timeout: 连接超时时间
            
        Returns:
            Tuple[bool, str, str]: (执行是否成功, 标准输出, 错误输出)
        """
        def _connect_and_execute():
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            try:
                # 根据认证方式连接
                if password:
                    # 密码认证
                    ssh_client.connect(
                        hostname=host,
                        port=port,
                        username=username,
                        password=password,
                        timeout=timeout
                    )
                elif private_key:
                    # 密钥认证 - 使用通用密钥加载函数
                    pkey = SSHService._load_private_key(private_key, private_key_password)
                    if pkey:
                        ssh_client.connect(
                            hostname=host,
                            port=port,
                            username=username,
                            pkey=pkey,
                            timeout=timeout
                        )
                    else:
                        return False, "", "无法加载私钥，不支持的密钥格式或密码错误"
                else:
                    return False, "", "未提供有效的认证信息"
                
                # 执行命令
                stdin, stdout, stderr = ssh_client.exec_command(command)
                
                # 获取原始输出
                raw_output = stdout.read().decode()
                raw_error = stderr.read().decode()
                
                # 初始化过滤后的输出
                filtered_output = raw_output
                filtered_error = raw_error
                
                # 只有当命令包含'export INIT_SCRIPT='且包含'base64 -d'时才应用过滤逻辑
                # 这样可以避免影响其他普通命令的执行结果
                import re
                if 'export INIT_SCRIPT=' in command and 'base64 -d' in command:
                    # 过滤export INIT_SCRIPT命令本身的显示，使用更宽松的正则表达式以适应不同格式
                    filtered_output = re.sub(r'export\s+INIT_SCRIPT=\$\(echo\s+\'[^\']*\'\s*\|\s*base64\s*-d.*?\)', '', raw_output, flags=re.DOTALL)
                    filtered_output = re.sub(r'export\s+INIT_SCRIPT=', '', filtered_output)
                    
                    # 使用更精确的正则表达式过滤base64相关内容，避免影响普通输出
                    # 只过滤看起来像完整base64编码块的内容
                    filtered_output = re.sub(r'^([A-Za-z0-9+/]{4})*([A-Za-z0-9+/]{3}=|[A-Za-z0-9+/]{2}==)?\s*$', '', filtered_output, flags=re.MULTILINE)
                    
                    # 过滤错误输出中的相关信息，使用更宽松的正则表达式
                    filtered_error = re.sub(r'export\s+INIT_SCRIPT=\$\(echo\s+\'[^\']*\'\s*\|\s*base64\s*-d.*?\)', '', raw_error, flags=re.DOTALL)
                    filtered_error = re.sub(r'export\s+INIT_SCRIPT=', '', filtered_error)
                    
                    # 清理多余的空行和空白字符
                    filtered_output = '\n'.join([line for line in filtered_output.split('\n') if line.strip()])
                    filtered_error = '\n'.join([line for line in filtered_error.split('\n') if line.strip()])
                
                return True, filtered_output, filtered_error
                
            except paramiko.AuthenticationException:
                return False, "", "SSH认证失败，请检查用户名和密码/密钥"
            except paramiko.SSHException as e:
                return False, "", f"SSH连接错误: {str(e)}"
            except Exception as e:
                return False, "", f"SSH命令执行失败: {str(e)}"
            finally:
                ssh_client.close()
        
        # 在线程池中执行阻塞的SSH连接操作
        return await asyncio.get_event_loop().run_in_executor(None, _connect_and_execute)