import psutil
import platform

def test_disk_usage():
    """测试修复后的磁盘使用率获取功能"""
    print("系统类型:", platform.system())
    print("Python版本:", platform.python_version())
    print("psutil版本:", getattr(psutil, '__version__', '未知'))
    
    try:
        # 获取所有磁盘分区
        print("\n获取磁盘分区信息:")
        disk_partitions = psutil.disk_partitions()
        all_disks_info = []
        
        for i, partition in enumerate(disk_partitions):
            print(f"  分区 {i+1}:")
            print(f"    设备: {partition.device}")
            print(f"    挂载点: {partition.mountpoint}")
            print(f"    文件系统: {partition.fstype}")
            print(f"    选项: {partition.opts}")
            
            # 尝试获取每个分区的使用情况
            try:
                print(f"    尝试获取使用情况...")
                disk = psutil.disk_usage(partition.mountpoint)
                disk_percent = round((disk.used / disk.total) * 100, 2)
                disk_total_gb = round(disk.total / (1024**3), 2)
                disk_used_gb = round(disk.used / (1024**3), 2)
                print(f"    使用率: {disk_percent}%")
                print(f"    总容量: {disk_total_gb} GB")
                print(f"    已使用: {disk_used_gb} GB")
                
                # 添加到所有磁盘信息列表
                all_disks_info.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "percent": disk_percent,
                    "total": disk_total_gb,
                    "used": disk_used_gb
                })
            except Exception as e:
                print(f"    获取使用情况失败: {e}")
                # 添加失败的磁盘信息
                all_disks_info.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "percent": 0,
                    "total": 0,
                    "used": 0,
                    "error": str(e)
                })
        
        print(f"\n总共找到 {len(all_disks_info)} 个磁盘分区")
        for disk in all_disks_info:
            print(f"  {disk['device']} ({disk['mountpoint']}) - {disk.get('percent', 0)}%")
            
    except Exception as e:
        print(f"测试过程中发生错误: {e}")

if __name__ == "__main__":
    test_disk_usage()