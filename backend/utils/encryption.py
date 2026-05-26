"""
SSH密码加密工具模块
用于加密和解密SSH连接密码
"""
from passlib.context import CryptContext
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# 创建密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SSHEncryption:
    """SSH密码加密解密工具类"""
    
    def __init__(self):
        # 生成或加载加密密钥
        self.key = self._get_or_create_key()
        self.cipher_suite = Fernet(self.key)
    
    def _get_or_create_key(self):
        """获取或创建加密密钥"""
        key_file = "data/encryption.key"
        
        # 确保data目录存在
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        
        if os.path.exists(key_file):
            # 如果密钥文件存在，读取密钥
            with open(key_file, "rb") as f:
                key = f.read()
        else:
            # 如果密钥文件不存在，生成新密钥并保存
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
        
        return key
    
    def encrypt_password(self, password: str) -> str:
        """
        加密SSH密码
        
        Args:
            password (str): 明文密码
            
        Returns:
            str: 加密后的密码
        """
        if not password:
            return ""
        
        # 使用Fernet加密
        encrypted_password = self.cipher_suite.encrypt(password.encode())
        # 将加密后的字节转换为base64字符串以便存储
        return base64.urlsafe_b64encode(encrypted_password).decode()
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """
        解密SSH密码
        
        Args:
            encrypted_password (str): 加密后的密码
            
        Returns:
            str: 解密后的明文密码
        """
        if not encrypted_password:
            return ""
        
        try:
            # 将base64字符串转换回字节
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_password.encode())
            # 解密
            decrypted_password = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_password.decode()
        except Exception as e:
            print(f"密码解密失败: {e}")
            return ""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        验证密码（用于用户认证等场景）
        
        Args:
            plain_password (str): 明文密码
            hashed_password (str): 哈希后的密码
            
        Returns:
            bool: 密码是否匹配
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        获取密码的哈希值（用于用户认证等场景）
        
        Args:
            password (str): 明文密码
            
        Returns:
            str: 哈希后的密码
        """
        return pwd_context.hash(password)

# 创建全局加密实例
ssh_encryption = SSHEncryption()

# 导出常用函数
encrypt_password = ssh_encryption.encrypt_password
decrypt_password = ssh_encryption.decrypt_password