import psutil
import platform
import os

def debug_disk_usage():
    """调试磁盘使用率获取功能"""
    print("系统类型:", platform.system())
    print("Python版本:", platform.python_version())
    print("psutil版本:", getattr(psutil, '__version__', '未知'))
    
    try:
        if platform.system() == "Windows":
            # 获取所有磁盘分区
            print("\n获取磁盘分区信息:")
            disk_partitions = psutil.disk_partitions()
            for i, partition in enumerate(disk_partitions):
                print(f"  分区 {i+1}:")
                print(f"    设备: {partition.device}")
                print(f"    挂载点: {partition.mountpoint}")
                print(f"    文件系统: {partition.fstype}")
                print(f"    选项: {partition.opts}")
                
                # 检查路径是否存在
                path_exists = os.path.exists(partition.mountpoint)
                print(f"    路径存在: {path_exists}")
                
                # 尝试获取每个分区的使用情况
                if path_exists:
                    try:
                        print(f"    尝试获取使用情况...")
                        disk = psutil.disk_usage(partition.mountpoint)
                        disk_percent = round((disk.used / disk.total) * 100, 2)
                        disk_total_gb = round(disk.total / (1024**3), 2)
                        disk_used_gb = round(disk.used / (1024**3), 2)
                        print(f"    使用率: {disk_percent}%")
                        print(f"    总容量: {disk_total_gb} GB")
                        print(f"    已使用: {disk_used_gb} GB")
                    except Exception as e:
                        print(f"    获取使用情况失败: {e}")
                        
                        # 尝试使用Windows特定的API
                        try:
                            import ctypes
                            from ctypes import wintypes
                            
                            print(f"    尝试使用Windows API...")
                            
                            # 定义Windows API结构
                            class ULARGE_INTEGER(ctypes.Structure):
                                _fields_ = [("LowPart", wintypes.DWORD),
                                           ("HighPart", wintypes.DWORD)]
                            
                            # 调用Windows GetDiskFreeSpaceEx API
                            def get_disk_usage_win(path):
                                free_bytes = ULARGE_INTEGER()
                                total_bytes = ULARGE_INTEGER()
                                total_free_bytes = ULARGE_INTEGER()
                                
                                ret = ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                                    path,
                                    ctypes.byref(free_bytes),
                                    ctypes.byref(total_bytes),
                                    ctypes.byref(total_free_bytes)
                                )
                                
                                if ret:
                                    total = (total_bytes.HighPart << 32) + total_bytes.LowPart
                                    free = (free_bytes.HighPart << 32) + free_bytes.LowPart
                                    used = total - free
                                    return total, used
                                else:
                                    raise Exception("无法获取磁盘空间信息")
                            
                            # 获取磁盘使用情况
                            total, used = get_disk_usage_win(partition.mountpoint)
                            disk_percent = round((used / total) * 100, 2)
                            disk_total_gb = round(total / (1024**3), 2)
                            disk_used_gb = round(used / (1024**3), 2)
                            print(f"    Windows API获取使用率: {disk_percent}%")
                            print(f"    Windows API获取总容量: {disk_total_gb} GB")
                            print(f"    Windows API获取已使用: {disk_used_gb} GB")
                        except Exception as win_api_error:
                            print(f"    Windows API也失败: {win_api_error}")
                
                print()
            
            # 特别测试C盘
            print("特别测试C盘:")
            c_drive = "C:\\"
            c_drive_exists = os.path.exists(c_drive)
            print(f"  C盘路径存在: {c_drive_exists}")
            
            if c_drive_exists:
                try:
                    print(f"  尝试获取C盘使用情况...")
                    disk = psutil.disk_usage(c_drive)
                    disk_percent = round((disk.used / disk.total) * 100, 2)
                    disk_total_gb = round(disk.total / (1024**3), 2)
                    disk_used_gb = round(disk.used / (1024**3), 2)
                    print(f"  C盘使用率: {disk_percent}%")
                    print(f"  C盘总容量: {disk_total_gb} GB")
                    print(f"  C盘已使用: {disk_used_gb} GB")
                except Exception as e:
                    print(f"  获取C盘使用情况失败: {e}")
        else:
            # Unix/Linux系统使用根目录
            print("\nUnix/Linux系统测试:")
            disk = psutil.disk_usage("/")
            disk_percent = round((disk.used / disk.total) * 100, 2)
            disk_total_gb = round(disk.total / (1024**3), 2)
            disk_used_gb = round(disk.used / (1024**3), 2)
            print(f"  根目录使用率: {disk_percent}%")
            print(f"  根目录总容量: {disk_total_gb} GB")
            print(f"  根目录已使用: {disk_used_gb} GB")
            
    except Exception as e:
        print(f"调试过程中发生错误: {e}")

if __name__ == "__main__":
    debug_disk_usage()