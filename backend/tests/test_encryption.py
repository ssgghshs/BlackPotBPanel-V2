"""
SSH密码加密测试脚本
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.encryption import SSHEncryption

def test_encryption():
    """测试加密功能"""
    print("测试SSH密码加密功能...")
    
    # 创建加密实例
    encryption = SSHEncryption()
    
    # 测试密码
    test_password = "my_secret_ssh_password_123"
    print(f"原始密码: {test_password}")
    
    # 加密密码
    encrypted = encryption.encrypt_password(test_password)
    print(f"加密后的密码: {encrypted}")
    
    # 解密密码
    decrypted = encryption.decrypt_password(encrypted)
    print(f"解密后的密码: {decrypted}")
    
    # 验证密码是否匹配
    if test_password == decrypted:
        print("✓ 加密/解密测试通过")
    else:
        print("✗ 加密/解密测试失败")
    
    # 测试空密码
    empty_encrypted = encryption.encrypt_password("")
    empty_decrypted = encryption.decrypt_password(empty_encrypted)
    if empty_decrypted == "":
        print("✓ 空密码处理测试通过")
    else:
        print("✗ 空密码处理测试失败")
    
    print("测试完成!")

if __name__ == "__main__":
    test_encryption()