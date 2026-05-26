"""
真正的SSH连接测试脚本
"""
import sys
import os
import asyncio

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.host.ssh_service import SSHService

async def test_real_ssh_connection():
    """测试真正的SSH连接功能"""
    print("测试真正的SSH连接功能...")
    
    # 注意：请将以下SSH连接信息替换为实际可用的SSH服务器信息
    # 仅用于测试目的，不要提交真实的服务器信息
    test_host = "192.168.223.180"  # 替换为实际的主机地址
    test_port = 22
    test_username = "root"   # 替换为实际的用户名
    test_password = "123"  # 替换为实际的密码
    
    try:
        # 测试SSH连接
        print(f"正在测试连接到 {test_host}:{test_port}...")
        success, message = await SSHService.test_ssh_connection(
            host=test_host,
            port=test_port,
            username=test_username,
            password=test_password
        )
        
        if success:
            print(f"✓ SSH连接成功: {message}")
        else:
            print(f"✗ SSH连接失败: {message}")
            
        # 测试执行命令
        if success:
            print("正在测试执行命令...")
            cmd_success, output, error = await SSHService.execute_ssh_command(
                host=test_host,
                port=test_port,
                username=test_username,
                password=test_password,
                command="uptime"
            )
            
            if cmd_success:
                print(f"✓ 命令执行成功:\n{output}")
            else:
                print(f"✗ 命令执行失败: {error}")
                
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
    
    print("测试完成!")

if __name__ == "__main__":
    asyncio.run(test_real_ssh_connection())