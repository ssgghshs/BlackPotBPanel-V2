"""
SSH连接测试脚本
"""
import sys
import os
import asyncio

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.host import service
from app.host.schemas import HostCreate
from config.database import get_db

async def test_ssh_connection():
    """测试SSH连接功能"""
    print("测试SSH连接功能...")
    
    # 获取数据库会话
    async for db in get_db():
        try:
            # 创建一个测试主机
            test_host_data = HostCreate(
                comment="Test Host",
                address="192.168.223.180",
                username="root",
                port=22,
                password="123",
                auth_method="password"
            )
            
            # 创建主机
            host = await service.create_host(db, test_host_data)
            host_id = getattr(host, 'id')
            print(f"创建测试主机: {host_id}")
            
            # 获取SSH配置信息
            ssh_config = await service.get_host(db, host_id)
            print(f"SSH配置信息: {ssh_config}")
            
            # 测试获取主机列表
            hosts = await service.get_hosts(db)
            print(f"主机列表数量: {len(hosts)}")
            
            # 删除测试主机
            result = await service.delete_host(db, host_id)
            print(f"删除测试主机结果: {result}")
            
        except Exception as e:
            print(f"测试过程中出现错误: {e}")
        finally:
            await db.close()
            break
    
    print("测试完成!")

if __name__ == "__main__":
    asyncio.run(test_ssh_connection())