import asyncio
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.ext.asyncio import AsyncSession
from . import models, schemas
import os
import stat
import shutil
import pwd
import grp
from datetime import datetime, timezone
import time
from typing import List, Dict, Any, Optional, Tuple
from fastapi import UploadFile
import httpx
import uuid
import re

# 导入系统配置
from config.settings import settings

# 获取配置文件路径
import os
ENV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "setting.conf")

UPLOAD_FOLDER = "uploads"

# 获取回收站路径
RECYCLE_PATH = settings.RECYCLE_PATH

# 存储下载任务的全局变量
download_tasks = {}

# 创建全局线程池执行器
executor = ThreadPoolExecutor(max_workers=4)


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

def get_recycle_config() -> bool:
    """获取回收站配置"""
    try:
        # 首先尝试从环境变量获取
        recycle_env = os.environ.get('RECYCLE')
        if recycle_env is not None:
            return recycle_env.lower() == 'true'
        
        # 然后尝试从配置文件获取
        configs = read_env_file()
        if 'RECYCLE' in configs:
            return configs['RECYCLE'].lower() == 'true'
        
        # 最后使用默认值
        return settings.RECYCLE
    except Exception as e:
        # 发生错误时使用默认值
        return settings.RECYCLE

def move_to_recycle_bin(full_path: str) -> bool:
    """将文件或目录移动到回收站"""
    try:
        # 定义回收站路径
        recycle_path = RECYCLE_PATH
        
        # 检查是否试图移动回收站目录本身
        if os.path.abspath(full_path) == os.path.abspath(recycle_path):
            raise ValueError("不允许将回收站目录移动到回收站")
        
        # 确保回收站目录存在
        os.makedirs(recycle_path, exist_ok=True)
        
        # 获取原始路径和文件名
        dir_path = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        
        # 替换路径分隔符为_bp_
        dir_path_normalized = dir_path.replace("/", "_bp_").replace("\\", "_bp_")
        
        # 生成新的文件名：路径+_bp_+文件名+_t_+时间戳
        timestamp = time.time()
        new_filename = f"{dir_path_normalized}_bp_{filename}_t_{timestamp}"
        
        # 构建回收站中的完整路径
        recycle_file_path = os.path.join(recycle_path, new_filename)
        
        # 移动文件或目录到回收站
        shutil.move(full_path, recycle_file_path)
        
        return True
    except Exception as e:
        raise Exception(f"移动文件到回收站失败: {str(e)}")

def format_permissions(mode: int) -> str:
    """将文件权限模式转换为简化的数字表示（如 777, 755）"""
    # 所有者权限
    owner = ((mode & stat.S_IRUSR) and 4) | ((mode & stat.S_IWUSR) and 2) | ((mode & stat.S_IXUSR) and 1)
    
    # 组权限
    group = ((mode & stat.S_IRGRP) and 4) | ((mode & stat.S_IWGRP) and 2) | ((mode & stat.S_IXGRP) and 1)
    
    # 其他用户权限
    others = ((mode & stat.S_IROTH) and 4) | ((mode & stat.S_IWOTH) and 2) | ((mode & stat.S_IXOTH) and 1)
    
    # 返回三位数字格式的权限字符串
    return f"{owner}{group}{others}"


def format_file_size(size_bytes: int) -> str:
    """将字节大小格式化为带单位的字符串"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    size_float = float(size_bytes)  # 转换为浮点数
    i = 0
    while size_float >= 1024.0 and i < len(size_names) - 1:
        size_float /= 1024.0
        i += 1
    
    # 如果是整数，不显示小数点
    if size_float == int(size_float):
        return f"{int(size_float)} {size_names[i]}"
    else:
        return f"{size_float:.1f} {size_names[i]}"


async def get_files_by_path(path: str = "/") -> List[Dict[str, Any]]:
    """获取指定路径下的文件列表"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"路径 {path} 不存在")
    
    files = []
    try:
        # 使用 scandir 提供更好的性能，并确保能获取所有文件包括隐藏文件
        with os.scandir(path) as entries:
            for entry in entries:
                # 获取文件状态信息（不跟踪符号链接）
                stat_info = entry.stat(follow_symlinks=False)
                
                # 检查是否为符号链接
                is_symlink = entry.is_symlink()
                
                # 获取文件大小
                file_size = stat_info.st_size
                
                # 获取用户和用户组信息
                try:
                    user_info = pwd.getpwuid(stat_info.st_uid)
                    user_name = user_info.pw_name
                except KeyError:
                    user_name = str(stat_info.st_uid)
                
                try:
                    group_info = grp.getgrgid(stat_info.st_gid)
                    group_name = group_info.gr_name
                except KeyError:
                    group_name = str(stat_info.st_gid)
                
                # 如果是符号链接，获取目标路径
                target_path = ""
                if is_symlink:
                    try:
                        target_path = os.readlink(entry.path)
                    except (OSError, IOError):
                        target_path = "(无效链接)"
                
                # 如果是符号链接，修改文件名格式为 "filename -> target_path"
                display_name = entry.name
                if is_symlink and target_path:
                    display_name = f"{entry.name} -> {target_path}"
                
                # 对于符号链接，检查目标是否为目录
                is_dir = entry.is_dir(follow_symlinks=False)
                if is_symlink:
                    # 检查符号链接指向的目标是否为目录
                    try:
                        target_full_path = os.path.join(path, target_path)
                        is_dir = os.path.isdir(target_full_path)
                    except:
                        # 如果无法访问目标，保持原有判断
                        pass
                
                files.append({
                    "filename": display_name,
                    "size": format_file_size(file_size),  # 格式化文件大小
                    "is_directory": is_dir,
                    "modified_time": datetime.fromtimestamp(stat_info.st_mtime),
                    "permissions": format_permissions(stat_info.st_mode),
                    "user": user_name,
                    "group": group_name,
                    "is_symlink": is_symlink,
                    "target_path": target_path if is_symlink else "",
                    "path": entry.path
                })
    except (OSError, IOError) as e:
        # 如果 scandir 失败，回退到 listdir
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            # 获取文件状态信息（不跟踪符号链接）
            stat_info = os.lstat(item_path)
            
            # 检查是否为符号链接
            is_symlink = os.path.islink(item_path)
            
            # 获取文件大小
            file_size = stat_info.st_size
            
            # 获取用户和用户组信息
            try:
                user_info = pwd.getpwuid(stat_info.st_uid)
                user_name = user_info.pw_name
            except KeyError:
                user_name = str(stat_info.st_uid)
            
            try:
                group_info = grp.getgrgid(stat_info.st_gid)
                group_name = group_info.gr_name
            except KeyError:
                group_name = str(stat_info.st_gid)
            
            # 如果是符号链接，获取目标路径
            target_path = ""
            if is_symlink:
                try:
                    target_path = os.readlink(item_path)
                except (OSError, IOError):
                    target_path = "(无效链接)"
            
            # 如果是符号链接，修改文件名格式为 "filename -> target_path"
            display_name = item
            if is_symlink and target_path:
                display_name = f"{item} -> {target_path}"
            
            # 对于符号链接，检查目标是否为目录
            is_dir = os.path.isdir(item_path)
            if is_symlink:
                # 检查符号链接指向的目标是否为目录
                try:
                    target_full_path = os.path.join(path, target_path)
                    is_dir = os.path.isdir(target_full_path)
                except:
                    # 如果无法访问目标，保持原有判断
                    pass
            
            files.append({
                "filename": display_name,
                "size": format_file_size(file_size),  # 格式化文件大小
                "is_directory": is_dir,
                "modified_time": datetime.fromtimestamp(stat_info.st_mtime),
                "permissions": format_permissions(stat_info.st_mode),
                "user": user_name,
                "group": group_name,
                "is_symlink": is_symlink,
                "target_path": target_path if is_symlink else "",
                "path": item_path
            })
    
    return files


async def clean_recycle_files() -> bool:
    """清理回收站文件，删除所有回收站中的文件和目录"""
    recycle_path = RECYCLE_PATH
    
    # 如果回收站目录不存在，直接返回成功
    if not os.path.exists(recycle_path):
        return True
    
    try:
        # 遍历回收站目录中的所有文件和子目录
        for item in os.listdir(recycle_path):
            item_path = os.path.join(recycle_path, item)
            
            # 如果是文件，直接删除
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            # 如果是目录，递归删除
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        
        return True
    except Exception as e:
        raise Exception(f"清理回收站失败: {str(e)}")


async def get_recycle_files() -> List[Dict[str, Any]]:
    """获取回收站中的文件和目录列表
    
    Returns:
        List[Dict]: 包含回收站文件信息的列表，每个字典包含以下字段：
            rname: 回收站中的文件名
            dname: 原始路径
            name: 原始文件名
            time: 修改时间
            size: 文件大小
            is_directory: 是否为目录
    """
    recycle_path = RECYCLE_PATH
    
    # 如果回收站目录不存在，返回空列表
    if not os.path.exists(recycle_path):
        return []
    
    files = []
    try:
        # 遍历回收站目录中的所有文件和子目录
        for item in os.listdir(recycle_path):
            item_path = os.path.join(recycle_path, item)
            
            # 获取文件状态信息
            stat_info = os.lstat(item_path)
            
            # 解析原始路径和文件名
            # 文件名格式为: 路径_bp_文件名_t_时间戳
            parts = item.split("_t_")
            if len(parts) == 2:
                path_and_name = parts[0]
                
                # 分离路径和文件名
                path_parts = path_and_name.split("_bp_")
                if len(path_parts) >= 2:
                    original_filename = path_parts[-1]
                    original_path_parts = path_parts[:-1]
                    # 恢复原始路径
                    original_path = "/".join(original_path_parts).replace("_bp_", "/")
                    original_full_path = f"{original_path}/{original_filename}" if original_path else original_filename
                else:
                    original_filename = path_and_name
                    original_full_path = original_filename
            else:
                # 如果文件名格式不符合预期，使用默认值
                original_filename = item
                original_full_path = item
            
            # 直接使用文件的修改时间，确保准确性
            # 使用 fromtimestamp 处理本地时间，确保与系统时间一致
            modified_time = datetime.fromtimestamp(stat_info.st_mtime)
            formatted_time = modified_time.strftime('%Y-%m-%dT%H:%M:%S')
            
            # 获取文件大小
            if os.path.isfile(item_path) or os.path.islink(item_path):
                file_size = stat_info.st_size
            elif os.path.isdir(item_path):
                # 对于目录，计算目录大小
                try:
                    file_size = sum(os.path.getsize(os.path.join(dirpath, filename)) 
                                   for dirpath, dirnames, filenames in os.walk(item_path) 
                                   for filename in filenames)
                except:
                    file_size = 0
            else:
                file_size = 0
            
            files.append({
                "rname": item,
                "dname": original_full_path,
                "name": original_filename,
                "time": formatted_time,
                "size": file_size,
                "is_directory": os.path.isdir(item_path)
            })
        
        return files
    except Exception as e:
        raise Exception(f"获取回收站文件列表失败: {str(e)}")


async def restore_recycle_file(recycle_filename: str, target_path: Optional[str] = None) -> bool:
    """从回收站恢复文件或目录到原始位置或指定位置
    
    Args:
        recycle_filename: 回收站中的文件名
        target_path: 可选，指定的恢复目标路径
        
    Returns:
        bool: 恢复是否成功
    """
    recycle_path = RECYCLE_PATH
    
    # 检查回收站目录是否存在
    if not os.path.exists(recycle_path):
        raise FileNotFoundError("回收站目录不存在")
    
    # 构建回收站中的完整文件路径
    recycle_file_path = os.path.join(recycle_path, recycle_filename)
    
    # 检查文件是否存在
    if not os.path.lexists(recycle_file_path):
        raise FileNotFoundError(f"回收站中的文件 {recycle_filename} 不存在")
    
    try:
        # 解析原始路径和文件名
        # 文件名格式为: 路径_bp_文件名_t_时间戳
        parts = recycle_filename.split("_t_")
        if len(parts) == 2:
            path_and_name = parts[0]
            
            # 分离路径和文件名
            path_parts = path_and_name.split("_bp_")
            if len(path_parts) >= 2:
                original_filename = path_parts[-1]
                original_path_parts = path_parts[:-1]
                # 恢复原始路径
                original_path = "/".join(original_path_parts).replace("_bp_", "/")
            else:
                original_filename = path_and_name
                original_path = ""
        else:
            # 如果文件名格式不符合预期，直接使用文件名作为原始文件名
            original_filename = recycle_filename
            original_path = ""
        
        # 确定最终恢复路径
        final_path = target_path if target_path else original_path
        
        # 构建完整的目标路径
        if final_path:
            # 确保目标路径存在
            os.makedirs(final_path, exist_ok=True)
            final_full_path = os.path.join(final_path, original_filename)
        else:
            final_full_path = original_filename
        
        # 检查目标位置是否已存在同名文件
        if os.path.exists(final_full_path):
            raise FileExistsError(f"目标位置已存在同名文件或目录 {original_filename}")
        
        # 将文件从回收站移动到目标位置
        shutil.move(recycle_file_path, final_full_path)
        
        return True
    except Exception as e:
        raise Exception(f"恢复文件失败: {str(e)}")


async def delete_recycle_file(recycle_filename: str) -> bool:
    """删除回收站中的单个文件或目录
    
    Args:
        recycle_filename: 回收站中的文件名
        
    Returns:
        bool: 删除是否成功
    """
    recycle_path = RECYCLE_PATH
    
    # 检查回收站目录是否存在
    if not os.path.exists(recycle_path):
        raise FileNotFoundError("回收站目录不存在")
    
    # 构建回收站中的完整文件路径
    recycle_file_path = os.path.join(recycle_path, recycle_filename)
    
    # 检查文件是否存在
    if not os.path.lexists(recycle_file_path):
        raise FileNotFoundError(f"回收站中的文件 {recycle_filename} 不存在")
    
    try:
        # 根据文件类型选择删除方式
        if os.path.isfile(recycle_file_path) or os.path.islink(recycle_file_path):
            # 删除文件或符号链接
            os.unlink(recycle_file_path)
        elif os.path.isdir(recycle_file_path):
            # 递归删除目录
            shutil.rmtree(recycle_file_path)
        
        return True
    except Exception as e:
        raise Exception(f"删除回收站文件失败: {str(e)}")


async def restore_recycle_files_batch(recycle_filenames: List[str]) -> Dict[str, Any]:
    """批量从回收站恢复文件或目录到原始位置
    
    Args:
        recycle_filenames: 回收站中的文件名列表
        
    Returns:
        Dict[str, Any]: 恢复结果，包含成功和失败的统计信息
    """
    success_count = 0
    failed_count = 0
    failed_files = []
    
    for recycle_filename in recycle_filenames:
        try:
            # 调用单个恢复函数，不指定target_path，默认恢复到原始位置
            await restore_recycle_file(recycle_filename)
            success_count += 1
        except Exception as e:
            failed_count += 1
            failed_files.append({
                "filename": recycle_filename,
                "error": str(e)
            })
    
    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "failed_files": failed_files
    }


async def delete_recycle_files_batch(recycle_filenames: List[str]) -> Dict[str, Any]:
    """批量从回收站删除文件或目录
    
    Args:
        recycle_filenames: 回收站中的文件名列表
        
    Returns:
        Dict[str, Any]: 删除结果，包含成功和失败的统计信息
    """
    success_count = 0
    failed_count = 0
    failed_files = []
    
    for recycle_filename in recycle_filenames:
        try:
            # 调用单个删除函数
            await delete_recycle_file(recycle_filename)
            success_count += 1
        except Exception as e:
            failed_count += 1
            failed_files.append({
                "filename": recycle_filename,
                "error": str(e)
            })
    
    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "failed_files": failed_files
    }


async def search_files_in_directory(path: str, keyword: str) -> List[Dict[str, Any]]:
    """搜索指定目录及其子目录中匹配关键词的文件
    
    Args:
        path: 要搜索的根目录路径
        keyword: 搜索关键词
    
    Returns:
        匹配文件的列表，格式与get_files_by_path返回相同
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"路径 {path} 不存在")
    
    if not os.path.isdir(path):
        raise ValueError(f"路径 {path} 不是一个目录")
    
    # 安全检查：防止路径遍历攻击
    if ".." in keyword or keyword.startswith("/"):
        raise ValueError("搜索关键词包含非法字符")
    
    # 将搜索操作放在线程池中执行，避免阻塞事件循环
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, _search_files_sync, path, keyword)
    return result


def _search_files_sync(path: str, keyword: str) -> List[Dict[str, Any]]:
    """同步搜索文件的辅助函数"""
    matched_files = []
    
    # 编译正则表达式，支持大小写不敏感的搜索
    try:
        # 尝试将关键词作为正则表达式
        pattern = re.compile(keyword, re.IGNORECASE)
    except re.error:
        # 如果不是有效的正则表达式，则转义并作为普通字符串搜索
        escaped_keyword = re.escape(keyword)
        pattern = re.compile(escaped_keyword, re.IGNORECASE)
    
    try:
        # 遍历目录及其子目录
        for root, dirs, files in os.walk(path):
            # 处理文件
            for filename in files:
                # 检查文件名是否匹配关键词
                if pattern.search(filename):
                    file_path = os.path.join(root, filename)
                    # 安全检查：确保文件路径仍在原始路径内
                    if not os.path.abspath(file_path).startswith(os.path.abspath(path)):
                        continue
                    
                    try:
                        # 获取文件信息，不跟踪符号链接
                        stat_info = os.lstat(file_path)
                        is_symlink = os.path.islink(file_path)
                        
                        # 获取文件大小
                        file_size = stat_info.st_size
                        
                        # 获取用户和用户组信息
                        try:
                            user_info = pwd.getpwuid(stat_info.st_uid)
                            user_name = user_info.pw_name
                        except KeyError:
                            user_name = str(stat_info.st_uid)
                        
                        try:
                            group_info = grp.getgrgid(stat_info.st_gid)
                            group_name = group_info.gr_name
                        except KeyError:
                            group_name = str(stat_info.st_gid)
                        
                        # 如果是符号链接，获取目标路径
                        target_path = ""
                        if is_symlink:
                            try:
                                target_path = os.readlink(file_path)
                            except (OSError, IOError):
                                target_path = "(无效链接)"
                        
                        # 如果是符号链接，修改文件名格式
                        display_name = filename
                        if is_symlink and target_path:
                            display_name = f"{filename} -> {target_path}"
                        
                        # 计算相对路径，用于显示
                        relative_path = os.path.relpath(file_path, path)
                        
                        matched_files.append({
                            "filename": relative_path,  # 使用相对路径作为文件名
                            "size": format_file_size(file_size),
                            "is_directory": False,
                            "modified_time": datetime.fromtimestamp(stat_info.st_mtime),
                            "permissions": format_permissions(stat_info.st_mode),
                            "user": user_name,
                            "group": group_name,
                            "is_symlink": is_symlink,
                            "target_path": target_path if is_symlink else "",
                            "path": file_path
                            # 移除relative_path字段
                        })
                    except Exception:
                        # 忽略单个文件的错误，继续处理其他文件
                        pass
                
            # 处理目录
            for dirname in dirs:
                # 检查目录名是否匹配关键词
                if pattern.search(dirname):
                    dir_path = os.path.join(root, dirname)
                    # 安全检查：确保目录路径仍在原始路径内
                    if not os.path.abspath(dir_path).startswith(os.path.abspath(path)):
                        continue
                    
                    try:
                        # 获取目录信息，不跟踪符号链接
                        stat_info = os.lstat(dir_path)
                        is_symlink = os.path.islink(dir_path)
                        
                        # 获取用户和用户组信息
                        try:
                            user_info = pwd.getpwuid(stat_info.st_uid)
                            user_name = user_info.pw_name
                        except KeyError:
                            user_name = str(stat_info.st_uid)
                        
                        try:
                            group_info = grp.getgrgid(stat_info.st_gid)
                            group_name = group_info.gr_name
                        except KeyError:
                            group_name = str(stat_info.st_gid)
                        
                        # 如果是符号链接，获取目标路径
                        target_path = ""
                        if is_symlink:
                            try:
                                target_path = os.readlink(dir_path)
                            except (OSError, IOError):
                                target_path = "(无效链接)"
                        
                        # 如果是符号链接，修改目录名格式
                        display_name = dirname
                        if is_symlink and target_path:
                            display_name = f"{dirname} -> {target_path}"
                        
                        # 计算相对路径，用于显示
                        relative_path = os.path.relpath(dir_path, path)
                        
                        matched_files.append({
                            "filename": relative_path,  # 使用相对路径作为文件名
                            "size": "0 B",  # 目录大小显示为0 B
                            "is_directory": True,
                            "modified_time": datetime.fromtimestamp(stat_info.st_mtime),
                            "permissions": format_permissions(stat_info.st_mode),
                            "user": user_name,
                            "group": group_name,
                            "is_symlink": is_symlink,
                            "target_path": target_path if is_symlink else "",
                            "path": dir_path
                            # 移除relative_path字段
                        })
                    except Exception:
                        # 忽略单个目录的错误，继续处理其他目录
                        pass
    except (OSError, IOError) as e:
        # 捕获遍历过程中的错误，但继续执行
        print(f"搜索过程中出错: {e}")
    
    return matched_files


async def create_directory(path: str, dir_name: str) -> bool:
    """在指定路径下创建新目录"""
    try:
        # 确保目录名不包含路径遍历字符
        if ".." in dir_name or dir_name.startswith("/"):
            raise ValueError("无效的目录名")
        
        # 构建完整路径
        full_path = os.path.join(path, dir_name)
        
        # 检查目录是否已存在
        if os.path.exists(full_path):
            raise FileExistsError(f"目录 {dir_name} 已存在")
        
        # 创建目录
        os.makedirs(full_path)
        return True
    except Exception as e:
        raise e


async def create_file(path: str, file_name: str, content: str = "") -> bool:
    """在指定路径下创建新文件"""
    try:
        # 确保文件名不包含路径遍历字符
        if ".." in file_name or file_name.startswith("/"):
            raise ValueError("无效的文件名")
        
        # 构建完整路径
        full_path = os.path.join(path, file_name)
        
        # 检查文件是否已存在
        if os.path.exists(full_path):
            raise FileExistsError(f"文件 {file_name} 已存在")
        
        # 创建文件并写入内容
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True
    except Exception as e:
        raise e


async def upload_file(path: str, file: UploadFile, overwrite: bool = False) -> bool:
    """上传文件到指定路径 - 优化版本：使用流式传输提升大文件上传性能"""
    try:
        # 检查文件名是否存在
        if not file.filename:
            raise ValueError("文件名不能为空")
        
        # 确保文件名不包含路径遍历字符
        if ".." in file.filename or file.filename.startswith("/"):
            raise ValueError("无效的文件名")
        
        # 构建完整路径
        full_path = os.path.join(path, file.filename)
        
        # 检查文件是否已存在
        if os.path.exists(full_path):
            if overwrite:
                os.remove(full_path)
            else:
                raise FileExistsError(f"文件 {file.filename} 已存在")
        
        # 使用流式传输，每次读取固定大小的块，而不是一次性读取整个文件
        # 这对于大文件上传非常重要，可以显著减少内存占用并提高性能
        chunk_size = 1024 * 1024  # 1MB块，可根据需要调整
        
        with open(full_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
        
        return True
    except Exception as e:
        raise e


async def delete_file(path: str, filename: str) -> bool:
    """删除指定路径下的文件或目录"""
    try:
        # 如果文件名是格式化后的符号链接格式 "filename -> target_path"，提取原始文件名
        if " -> " in filename:
            filename = filename.split(" -> ")[0]
        
        # 确保文件名不包含路径遍历字符
        if ".." in filename or filename.startswith("/"):
            raise ValueError("无效的文件名")
        
        # 构建完整路径
        full_path = os.path.join(path, filename)
        
        # 检查是否试图删除回收站目录
        recycle_path = RECYCLE_PATH
        if os.path.abspath(full_path) == os.path.abspath(recycle_path):
            raise ValueError("不允许删除回收站目录")
        
        # 检查文件或目录是否存在
        if not os.path.lexists(full_path):
            raise FileNotFoundError(f"文件或目录 {filename} 不存在")
        
        # 获取回收站配置
        recycle_enabled = get_recycle_config()
        
        if recycle_enabled:
            # 如果启用了回收站，将文件移动到回收站
            result = move_to_recycle_bin(full_path)
        else:
            # 如果未启用回收站，直接删除文件或目录
            # 删除文件或目录（对符号链接使用 unlink）
            if os.path.islink(full_path) or os.path.isfile(full_path):
                os.unlink(full_path)  # unlink 可以安全地删除符号链接
            elif os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                raise ValueError(f"{filename} 既不是文件也不是目录")
        
        return True
    except Exception as e:
        raise e


async def delete_files_batch(path: str, filenames: List[str]) -> Dict[str, Any]:
    """批量删除指定路径下的文件或目录
    
    Args:
        path: 文件所在路径
        filenames: 要删除的文件名列表
        
    Returns:
        Dict: 包含成功数量、失败数量和失败文件详情的字典
    """
    success_count = 0
    failed_count = 0
    failed_files = []
    
    for filename in filenames:
        try:
            await delete_file(path, filename)
            success_count += 1
        except Exception as e:
            failed_count += 1
            failed_files.append({
                "filename": filename,
                "error": str(e)
            })
    
    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "failed_files": failed_files
    }


async def move_file_or_directory(source_path: str, source_name: str, destination_path: str, destination_name: str = "", overwrite: bool = False) -> bool:
    """移动文件或目录到指定路径"""
    try:
        # 如果文件名是格式化后的符号链接格式 "filename -> target_path"，提取原始文件名
        if " -> " in source_name:
            source_name = source_name.split(" -> ")[0]
        
        # 确保源文件名和目标路径不包含路径遍历字符
        # 允许以 / 开头的绝对路径，但防止路径遍历攻击
        if ".." in source_name or ".." in destination_path:
            raise ValueError("无效的文件名或路径")
        
        # 如果没有指定目标名称，则使用源名称
        if destination_name == "":
            destination_name = source_name
            
        # 构建完整源路径和目标路径
        full_source_path = os.path.join(source_path, source_name)
        full_destination_path = os.path.join(destination_path, destination_name)
        
        # 检查源文件或目录是否存在
        if not os.path.exists(full_source_path):
            raise FileNotFoundError(f"源文件或目录 {source_name} 不存在")
        
        # 检查目标路径是否存在同名文件或目录
        if os.path.exists(full_destination_path):
            if not overwrite:
                raise FileExistsError(f"目标路径已存在同名文件或目录 {destination_name}")
            if os.path.isdir(full_destination_path):
                raise ValueError(f"目标路径已存在同名目录 {destination_name}，不支持覆盖目录")
            os.remove(full_destination_path)
        
        # 创建目标目录（如果不存在）
        os.makedirs(destination_path, exist_ok=True)
        
        # 移动文件或目录
        shutil.move(full_source_path, full_destination_path)
        
        return True
    except Exception as e:
        raise e


async def download_file(path: str, filename: str, start: int = 0, end: Optional[int] = None) -> Tuple[bytes, int, str]:
    """
    下载指定路径下的文件，支持范围请求
    
    Args:
        path: 文件所在路径
        filename: 文件名
        start: 开始位置（用于断点续传）
        end: 结束位置（用于断点续传）
        
    Returns:
        Tuple[文件内容字节, 文件总大小, 原始文件名]
    """
    try:
        # 处理符号链接文件名格式
        original_filename = filename
        if " -> " in filename:
            original_filename = filename.split(" -> ")[0]
        
        # 安全检查：防止路径遍历攻击
        if ".." in original_filename or original_filename.startswith("/"):
            raise ValueError("文件名包含非法字符")
        
        # 构建完整文件路径并标准化
        full_path = os.path.abspath(os.path.join(path, original_filename))
        
        # 验证文件存在
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"文件 {original_filename} 不存在")
        
        # 验证是否为文件
        if not os.path.isfile(full_path):
            raise ValueError(f"{original_filename} 不是一个文件")
        
        # 获取文件大小
        file_size = os.path.getsize(full_path)
        
        # 处理范围请求参数
        if end is None or end >= file_size:
            end = file_size - 1
        
        # 验证范围有效性
        if start < 0 or end >= file_size or start > end:
            raise ValueError("请求的范围无效")
        
        # 读取指定范围的文件内容
        with open(full_path, "rb") as f:
            f.seek(start)
            content = f.read(end - start + 1)
        
        return content, file_size, original_filename
    except Exception as e:
        raise e


async def rename_file(path: str, old_name: str, new_name: str) -> bool:
    """重命名指定路径下的文件或目录"""
    try:
        # 如果文件名是格式化后的符号链接格式 "filename -> target_path"，提取原始文件名
        if " -> " in old_name:
            old_name = old_name.split(" -> ")[0]
        
        # 确保文件名不包含路径遍历字符
        if ".." in old_name or old_name.startswith("/") or ".." in new_name or new_name.startswith("/"):
            raise ValueError("无效的文件名")
        
        # 构建完整路径
        old_path = os.path.join(path, old_name)
        new_path = os.path.join(path, new_name)
        
        # 检查原文件或目录是否存在
        if not os.path.exists(old_path):
            raise FileNotFoundError(f"文件或目录 {old_name} 不存在")
        
        # 检查新文件名是否已存在
        if os.path.exists(new_path):
            raise FileExistsError(f"文件或目录 {new_name} 已存在")
        
        # 重命名文件或目录
        os.rename(old_path, new_path)
        
        return True
    except Exception as e:
        raise e


import pwd
import grp

async def change_permissions(path: str, filename: str, permissions: str = None, user: str = None, group: str = None, recursive: bool = False) -> bool:
    """修改文件/目录权限、所有者和所属组
    
    Args:
        path: 基础路径
        filename: 文件名
        permissions: 权限模式(3位数字)
        user: 所有者用户名
        group: 所属组名
        recursive: 是否递归应用到子目录
    
    Returns:
        bool: 操作是否成功
    """
    try:
        # 如果文件名是格式化后的符号链接格式 "filename -> target_path"，提取原始文件名
        if " -> " in filename:
            filename = filename.split(" -> ")[0]
        
        # 确保文件名不包含路径遍历字符
        if ".." in filename or filename.startswith("/"):
            raise ValueError("无效的文件名")
            
        # 构建完整路径
        full_path = os.path.join(path, filename)
        
        # 检查文件或目录是否存在
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"文件或目录 {filename} 不存在")
        
        # 获取用户ID和组ID（如果提供了用户名和组名）
        uid = None
        gid = None
        
        if user:
            try:
                user_info = pwd.getpwnam(user)
                uid = user_info.pw_uid
            except KeyError:
                raise ValueError(f"用户 {user} 不存在")
        
        if group:
            try:
                group_info = grp.getgrnam(group)
                gid = group_info.gr_gid
            except KeyError:
                raise ValueError(f"用户组 {group} 不存在")
        
        # 将权限字符串转换为八进制数（如果提供了权限参数）
        mode = None
        if permissions:
            try:
                mode = int(permissions, 8)
            except ValueError:
                raise ValueError("权限格式不正确，应为3位八进制数(0-7)")
        
        # 定义单个文件/目录的修改函数
        def modify_path(target_path):
            # 如果是符号链接，跳过修改（避免修改到目标文件）
            if os.path.islink(target_path):
                return
            
            # 修改权限
            if mode is not None:
                os.chmod(target_path, mode)
            
            # 修改所有者和所属组
            if uid is not None or gid is not None:
                # 如果只提供了其中一个，保持另一个不变
                try:
                    os.chown(target_path, uid if uid is not None else -1, gid if gid is not None else -1)
                except OSError as e:
                    # 处理权限不足等错误
                    raise PermissionError(f"无法修改 {os.path.basename(target_path)} 的所有者/所属组: {str(e)}")
        
        # 根据是否递归决定操作方式
        if recursive and os.path.isdir(full_path):
            # 递归处理目录下的所有文件和子目录
            for root, dirs, files_list in os.walk(full_path):
                # 先修改目录本身
                modify_path(root)
                # 修改当前目录下的所有文件
                for file_name in files_list:
                    file_path = os.path.join(root, file_name)
                    modify_path(file_path)
        else:
            # 只修改指定的文件或目录
            modify_path(full_path)
        
        return True
    except Exception as e:
        raise e


async def change_permissions_batch(path: str, filenames: List[str], permissions: str = None, user: str = None, group: str = None, recursive: bool = False) -> Dict[str, Any]:
    """批量修改文件/目录权限、所有者和所属组
    
    Args:
        path: 基础路径
        filenames: 文件名列表
        permissions: 权限模式(3位数字)
        user: 所有者用户名
        group: 所属组名
        recursive: 是否递归应用到子目录
    
    Returns:
        Dict: 包含成功和失败信息的结果字典
    """
    success_count = 0
    failed_count = 0
    failed_files = []
    
    for filename in filenames:
        try:
            await change_permissions(path, filename, permissions, user, group, recursive)
            success_count += 1
        except Exception as e:
            failed_count += 1
            failed_files.append({
                "filename": filename,
                "error": str(e)
            })
    
    return {
        "success_count": success_count,
        "failed_count": failed_count,
        "failed_files": failed_files
    }


async def get_file_content(path: str, filename: str) -> str:
    """获取指定文件的内容"""
    try:
        # 如果文件名是格式化后的符号链接格式 "filename -> target_path"，提取原始文件名
        if " -> " in filename:
            filename = filename.split(" -> ")[0]
        
        # 确保文件名不包含路径遍历字符
        if ".." in filename or filename.startswith("/"):
            raise ValueError("Invalid file")
        
        # 构建完整路径
        full_path = os.path.join(path, filename)
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File {filename} not found")
        
        # 检查是否为文件
        if not os.path.isfile(full_path):
            raise ValueError(f"{filename} is not a file")
        
        # 检查文件大小，避免读取过大的文件
        file_size = os.path.getsize(full_path)
        if file_size > 10 * 1024 * 1024:  # 限制为10MB
            raise ValueError("File is too large to read")
        
        # 检查文件后缀，如果为.db文件则直接返回不支持
        _, file_extension = os.path.splitext(filename.lower())
        if file_extension == '.db':
            raise ValueError("File format not supported: .db files")
        
        # 读取文件内容，首先尝试UTF-8编码
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError as e:
            # 如果UTF-8解码失败，尝试其他编码
            encodings_to_try = ['gbk', 'latin-1', 'big5', 'utf-16']
            content = None
            last_error = str(e)
            
            for encoding in encodings_to_try:
                try:
                    with open(full_path, "r", encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError as encoding_error:
                    last_error = str(encoding_error)
                    continue
                except Exception as encoding_error:
                    last_error = str(encoding_error)
                    continue
            
            # 如果所有编码都失败了，抛出自定义错误
            if content is None:
                raise ValueError(f"File encoding not supported: {last_error}")
        
        return content
    except Exception as e:
        raise e


async def save_file_content(path: str, filename: str, content: str) -> bool:
    """保存文件内容"""
    try:
        # 如果文件名是格式化后的符号链接格式 "filename -> target_path"，提取原始文件名
        if " -> " in filename:
            filename = filename.split(" -> ")[0]
        
        # 确保文件名不包含路径遍历字符
        if ".." in filename or filename.startswith("/"):
            raise ValueError("无效的文件名")
        
        # 构建完整路径
        full_path = os.path.join(path, filename)
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"文件 {filename} 不存在")
        
        # 检查是否为文件
        if not os.path.isfile(full_path):
            raise ValueError(f"{filename} 不是一个文件")
        
        # 保存文件内容
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True
    except Exception as e:
        raise e


async def get_image_content(path: str, filename: str) -> bytes:
    """获取指定图片文件的内容"""
    try:
        # 如果文件名是格式化后的符号链接格式 "filename -> target_path"，提取原始文件名
        if " -> " in filename:
            filename = filename.split(" -> ")[0]
        
        # 确保文件名不包含路径遍历字符
        if ".." in filename or filename.startswith("/"):
            raise ValueError("无效的文件名")
        
        # 构建完整路径
        full_path = os.path.join(path, filename)
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"图片文件 {filename} 不存在")
        
        # 检查是否为文件
        if not os.path.isfile(full_path):
            raise ValueError(f"{filename} 不是一个文件")
        
        # 检查文件扩展名是否为图片格式
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico'}
        _, ext = os.path.splitext(filename.lower())
        if ext not in image_extensions:
            raise ValueError(f"{filename} 不是支持的图片格式")
        
        # 读取图片文件内容
        with open(full_path, "rb") as f:
            content = f.read()
        
        return content
    except Exception as e:
        raise e


async def copy_file_or_directory(source_path: str, source_name: str, destination_path: str, destination_name: str = "", overwrite: bool = False) -> bool:
    """复制文件或目录到指定路径"""
    try:
        # 如果文件名是格式化后的符号链接格式 "filename -> target_path"，提取原始文件名
        if " -> " in source_name:
            source_name = source_name.split(" -> ")[0]
        
        # 确保源文件名和目标路径不包含路径遍历字符
        # 允许以 / 开头的绝对路径，但防止路径遍历攻击
        if ".." in source_name or ".." in destination_path:
            raise ValueError("无效的文件名或路径")
        
        # 如果没有指定目标名称，则使用源名称
        if destination_name == "":
            destination_name = source_name
            
        # 构建完整源路径和目标路径
        full_source_path = os.path.join(source_path, source_name)
        full_destination_path = os.path.join(destination_path, destination_name)
        
        # 检查源文件或目录是否存在
        if not os.path.exists(full_source_path):
            raise FileNotFoundError(f"源文件或目录 {source_name} 不存在")
        
        # 检查目标路径是否存在同名文件或目录
        if os.path.exists(full_destination_path):
            if not overwrite:
                raise FileExistsError(f"目标路径已存在同名文件或目录 {destination_name}")
            if os.path.isdir(full_destination_path):
                raise ValueError(f"目标路径已存在同名目录 {destination_name}，不支持覆盖目录")
            os.remove(full_destination_path)
        
        # 创建目标目录（如果不存在）
        os.makedirs(destination_path, exist_ok=True)
        
        # 复制文件或目录
        if os.path.isfile(full_source_path):
            shutil.copy2(full_source_path, full_destination_path)
        elif os.path.isdir(full_source_path):
            shutil.copytree(full_source_path, full_destination_path)
        else:
            raise ValueError(f"{source_name} 既不是文件也不是目录")
        
        return True
    except Exception as e:
        raise e


async def compress_files(source_path: str, source_names: List[str], destination_path: str, archive_name: str) -> bool:
    """压缩文件或目录到指定路径"""
    # 将CPU密集型操作提交到线程池执行
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _sync_compress_files, source_path, source_names, destination_path, archive_name)


def _sync_compress_files(source_path: str, source_names: List[str], destination_path: str, archive_name: str) -> bool:
    """同步执行压缩操作"""
    try:
        import zipfile
        import tarfile
        import os.path
        
        # 确保目标路径不包含路径遍历字符
        if ".." in destination_path:
            raise ValueError("无效的路径")
        
        # 构建完整目标路径
        full_destination_path = os.path.join(destination_path, archive_name)
        
        # 检查目标文件是否已存在
        if os.path.exists(full_destination_path):
            raise FileExistsError(f"目标文件 {archive_name} 已存在")
        
        # 创建目标目录（如果不存在）
        os.makedirs(destination_path, exist_ok=True)
        
        # 根据目标文件扩展名选择压缩方式
        archive_lower = archive_name.lower()
        
        if archive_lower.endswith('.zip'):
            # 创建ZIP压缩文件
            with zipfile.ZipFile(full_destination_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                for source_name in source_names:
                    # 确保源文件名不包含路径遍历字符
                    if ".." in source_name:
                        raise ValueError("无效的文件名")
                    
                    # 构建完整源路径
                    full_source_path = os.path.join(source_path, source_name)
                    
                    # 检查源文件或目录是否存在
                    if not os.path.exists(full_source_path):
                        raise FileNotFoundError(f"源文件或目录 {source_name} 不存在")
                    
                    # 添加文件或目录到压缩文件
                    if os.path.isfile(full_source_path):
                        # 检查是否为符号链接
                        if os.path.islink(full_source_path):
                            # 对于符号链接，保存链接信息而不是目标文件内容
                            link_target = os.readlink(full_source_path)
                            zip_info = zipfile.ZipInfo(source_name)
                            zip_info.external_attr = 0o120755 << 16  # 设置符号链接权限
                            zipf.writestr(zip_info, link_target)
                        else:
                            # 添加单个文件
                            zipf.write(full_source_path, source_name)
                    elif os.path.isdir(full_source_path):
                        # 添加整个目录
                        for root, dirs, files in os.walk(full_source_path, followlinks=False):
                            # 处理目录
                            for dir_name in dirs:
                                dir_path = os.path.join(root, dir_name)
                                arcname = os.path.relpath(dir_path, source_path)
                                # 检查是否为符号链接目录
                                if os.path.islink(dir_path):
                                    link_target = os.readlink(dir_path)
                                    zip_info = zipfile.ZipInfo(arcname + "/")
                                    zip_info.external_attr = 0o120755 << 16  # 设置符号链接权限
                                    zipf.writestr(zip_info, link_target)
                            
                            # 处理文件
                            for file in files:
                                file_path = os.path.join(root, file)
                                # 计算相对路径
                                arcname = os.path.relpath(file_path, source_path)
                                # 检查是否为符号链接
                                if os.path.islink(file_path):
                                    # 对于符号链接，保存链接信息而不是目标文件内容
                                    link_target = os.readlink(file_path)
                                    zip_info = zipfile.ZipInfo(arcname)
                                    zip_info.external_attr = 0o120755 << 16  # 设置符号链接权限
                                    zipf.writestr(zip_info, link_target)
                                else:
                                    zipf.write(file_path, arcname)
        
        elif archive_lower.endswith('.tar'):
            # 创建TAR压缩文件
            with tarfile.open(full_destination_path, 'w') as tarf:
                for source_name in source_names:
                    # 确保源文件名不包含路径遍历字符
                    if ".." in source_name:
                        raise ValueError("无效的文件名")
                    
                    # 构建完整源路径
                    full_source_path = os.path.join(source_path, source_name)
                    
                    # 检查源文件或目录是否存在
                    if not os.path.exists(full_source_path):
                        raise FileNotFoundError(f"源文件或目录 {source_name} 不存在")
                    
                    # 添加文件或目录到压缩文件，保留符号链接
                    tarf.add(full_source_path, arcname=source_name, recursive=True, filter=_tar_filter)
        
        elif archive_lower.endswith('.tar.gz') or archive_lower.endswith('.tgz'):
            # 创建TAR.GZ压缩文件
            with tarfile.open(full_destination_path, 'w:gz') as tarf:
                for source_name in source_names:
                    # 确保源文件名不包含路径遍历字符
                    if ".." in source_name:
                        raise ValueError("无效的文件名")
                    
                    # 构建完整源路径
                    full_source_path = os.path.join(source_path, source_name)
                    
                    # 检查源文件或目录是否存在
                    if not os.path.exists(full_source_path):
                        raise FileNotFoundError(f"源文件或目录 {source_name} 不存在")
                    
                    # 添加文件或目录到压缩文件，保留符号链接
                    tarf.add(full_source_path, arcname=source_name, recursive=True, filter=_tar_filter)
        
        elif archive_lower.endswith('.tar.bz2') or archive_lower.endswith('.tbz2'):
            # 创建TAR.BZ2压缩文件
            with tarfile.open(full_destination_path, 'w:bz2') as tarf:
                for source_name in source_names:
                    # 确保源文件名不包含路径遍历字符
                    if ".." in source_name:
                        raise ValueError("无效的文件名")
                    
                    # 构建完整源路径
                    full_source_path = os.path.join(source_path, source_name)
                    
                    # 检查源文件或目录是否存在
                    if not os.path.exists(full_source_path):
                        raise FileNotFoundError(f"源文件或目录 {source_name} 不存在")
                    
                    # 添加文件或目录到压缩文件，保留符号链接
                    tarf.add(full_source_path, arcname=source_name, recursive=True, filter=_tar_filter)
        
        elif archive_lower.endswith('.tar.xz') or archive_lower.endswith('.txz'):
            # 创建TAR.XZ压缩文件
            with tarfile.open(full_destination_path, 'w:xz') as tarf:
                for source_name in source_names:
                    # 确保源文件名不包含路径遍历字符
                    if ".." in source_name:
                        raise ValueError("无效的文件名")
                    
                    # 构建完整源路径
                    full_source_path = os.path.join(source_path, source_name)
                    
                    # 检查源文件或目录是否存在
                    if not os.path.exists(full_source_path):
                        raise FileNotFoundError(f"源文件或目录 {source_name} 不存在")
                    
                    # 添加文件或目录到压缩文件，保留符号链接
                    tarf.add(full_source_path, arcname=source_name, recursive=True, filter=_tar_filter)
        
        else:
            # 不支持的格式，默认使用ZIP格式
            with zipfile.ZipFile(full_destination_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                for source_name in source_names:
                    # 确保源文件名不包含路径遍历字符
                    if ".." in source_name:
                        raise ValueError("无效的文件名")
                    
                    # 构建完整源路径
                    full_source_path = os.path.join(source_path, source_name)
                    
                    # 检查源文件或目录是否存在
                    if not os.path.exists(full_source_path):
                        raise FileNotFoundError(f"源文件或目录 {source_name} 不存在")
                    
                    # 添加文件或目录到压缩文件
                    if os.path.isfile(full_source_path):
                        # 检查是否为符号链接
                        if os.path.islink(full_source_path):
                            # 对于符号链接，保存链接信息而不是目标文件内容
                            link_target = os.readlink(full_source_path)
                            zip_info = zipfile.ZipInfo(source_name)
                            zip_info.external_attr = 0o120755 << 16  # 设置符号链接权限
                            zipf.writestr(zip_info, link_target)
                        else:
                            # 添加单个文件
                            zipf.write(full_source_path, source_name)
                    elif os.path.isdir(full_source_path):
                        # 添加整个目录
                        for root, dirs, files in os.walk(full_source_path, followlinks=False):
                            # 处理目录
                            for dir_name in dirs:
                                dir_path = os.path.join(root, dir_name)
                                arcname = os.path.relpath(dir_path, source_path)
                                # 检查是否为符号链接目录
                                if os.path.islink(dir_path):
                                    link_target = os.readlink(dir_path)
                                    zip_info = zipfile.ZipInfo(arcname + "/")
                                    zip_info.external_attr = 0o120755 << 16  # 设置符号链接权限
                                    zipf.writestr(zip_info, link_target)
                            
                            # 处理文件
                            for file in files:
                                file_path = os.path.join(root, file)
                                # 计算相对路径
                                arcname = os.path.relpath(file_path, source_path)
                                # 检查是否为符号链接
                                if os.path.islink(file_path):
                                    # 对于符号链接，保存链接信息而不是目标文件内容
                                    link_target = os.readlink(file_path)
                                    zip_info = zipfile.ZipInfo(arcname)
                                    zip_info.external_attr = 0o120755 << 16  # 设置符号链接权限
                                    zipf.writestr(zip_info, link_target)
                                else:
                                    zipf.write(file_path, arcname)
        
        return True
    except Exception as e:
        raise e


def _tar_filter(tarinfo):
    """TAR文件过滤器，用于处理符号链接等特殊文件"""
    # 保留符号链接信息
    if tarinfo.issym():
        # 确保符号链接信息正确
        pass
    return tarinfo


async def decompress_file(source_path: str, source_name: str, destination_path: str) -> bool:
    """解压文件到指定路径"""
    # 将CPU密集型操作提交到线程池执行
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _sync_decompress_file, source_path, source_name, destination_path)

def _sync_decompress_file(source_path: str, source_name: str, destination_path: str) -> bool:
    """同步执行解压操作"""
    try:
        import zipfile
        import tarfile
        import os.path
        
        # 确保源文件名和目标路径不包含路径遍历字符
        if ".." in source_name or ".." in destination_path:
            raise ValueError("无效的文件名或路径")
        
        # 构建完整源路径
        full_source_path = os.path.join(source_path, source_name)
        
        # 检查源文件是否存在
        if not os.path.exists(full_source_path):
            raise FileNotFoundError(f"源文件 {source_name} 不存在")
        
        # 创建目标目录（如果不存在）
        os.makedirs(destination_path, exist_ok=True)
        
        # 根据文件扩展名选择解压方式
        file_lower = source_name.lower()
        
        if file_lower.endswith('.zip'):
            # 解压ZIP文件
            with zipfile.ZipFile(full_source_path, 'r') as zipf:
                # 检查zip文件中的文件名是否包含路径遍历字符
                for name in zipf.namelist():
                    if ".." in name:
                        raise ValueError("压缩文件包含无效的文件名")
                
                # 解压所有文件
                zipf.extractall(destination_path)
        
        elif file_lower.endswith('.tar'):
            # 解压TAR文件
            with tarfile.open(full_source_path, 'r') as tarf:
                # 检查tar文件中的文件名是否包含路径遍历字符
                for member in tarf.getmembers():
                    if ".." in member.name:
                        raise ValueError("压缩文件包含无效的文件名")
                
                # 解压所有文件并恢复权限和元数据
                tarf.extractall(destination_path)
                
                # 恢复文件权限和时间戳
                for member in tarf.getmembers():
                    member_path = os.path.join(destination_path, member.name)
                    if member.isfile() and hasattr(member, 'mode'):
                        try:
                            os.chmod(member_path, member.mode)
                        except:
                            pass  # 忽略权限设置错误
                        
                        # 恢复时间戳
                        if hasattr(member, 'mtime'):
                            try:
                                os.utime(member_path, (member.mtime, member.mtime))
                            except:
                                pass  # 忽略时间戳设置错误
        
        elif file_lower.endswith('.tar.gz') or file_lower.endswith('.tgz'):
            # 解压TAR.GZ文件
            with tarfile.open(full_source_path, 'r:gz') as tarf:
                # 检查tar文件中的文件名是否包含路径遍历字符
                for member in tarf.getmembers():
                    if ".." in member.name:
                        raise ValueError("压缩文件包含无效的文件名")
                
                # 解压所有文件并恢复权限和元数据
                tarf.extractall(destination_path)
                
                # 恢复文件权限和时间戳
                for member in tarf.getmembers():
                    member_path = os.path.join(destination_path, member.name)
                    if member.isfile() and hasattr(member, 'mode'):
                        try:
                            os.chmod(member_path, member.mode)
                        except:
                            pass  # 忽略权限设置错误
                        
                        # 恢复时间戳
                        if hasattr(member, 'mtime'):
                            try:
                                os.utime(member_path, (member.mtime, member.mtime))
                            except:
                                pass  # 忽略时间戳设置错误
        
        elif file_lower.endswith('.tar.bz2') or file_lower.endswith('.tbz2'):
            # 解压TAR.BZ2文件
            with tarfile.open(full_source_path, 'r:bz2') as tarf:
                # 检查tar文件中的文件名是否包含路径遍历字符
                for member in tarf.getmembers():
                    if ".." in member.name:
                        raise ValueError("压缩文件包含无效的文件名")
                
                # 解压所有文件并恢复权限和元数据
                tarf.extractall(destination_path)
                
                # 恢复文件权限和时间戳
                for member in tarf.getmembers():
                    member_path = os.path.join(destination_path, member.name)
                    if member.isfile() and hasattr(member, 'mode'):
                        try:
                            os.chmod(member_path, member.mode)
                        except:
                            pass  # 忽略权限设置错误
                        
                        # 恢复时间戳
                        if hasattr(member, 'mtime'):
                            try:
                                os.utime(member_path, (member.mtime, member.mtime))
                            except:
                                pass  # 忽略时间戳设置错误
        
        elif file_lower.endswith('.tar.xz') or file_lower.endswith('.txz'):
            # 解压TAR.XZ文件
            with tarfile.open(full_source_path, 'r:xz') as tarf:
                # 检查tar文件中的文件名是否包含路径遍历字符
                for member in tarf.getmembers():
                    if ".." in member.name:
                        raise ValueError("压缩文件包含无效的文件名")
                
                # 解压所有文件并恢复权限和元数据
                tarf.extractall(destination_path)
                
                # 恢复文件权限和时间戳
                for member in tarf.getmembers():
                    member_path = os.path.join(destination_path, member.name)
                    if member.isfile() and hasattr(member, 'mode'):
                        try:
                            os.chmod(member_path, member.mode)
                        except:
                            pass  # 忽略权限设置错误
                        
                        # 恢复时间戳
                        if hasattr(member, 'mtime'):
                            try:
                                os.utime(member_path, (member.mtime, member.mtime))
                            except:
                                pass  # 忽略时间戳设置错误
        
        else:
            # 不支持的格式
            supported_formats = ".zip, .tar, .tar.gz, .tgz, .tar.bz2, .tbz2, .tar.xz, .txz"
            raise ValueError(f"不支持的压缩文件格式: {source_name}。支持的格式: {supported_formats}")
        
        return True
    except Exception as e:
        raise e


async def create_symlink(source_path: str, source_name: str, destination_path: str, destination_name: str) -> bool:
    """创建软链接"""
    try:
        # 确保文件名不包含路径遍历字符
        if ".." in source_name or source_name.startswith("/") or ".." in destination_name or destination_name.startswith("/"):
            raise ValueError("无效的文件名")
        
        # 构建完整源路径和目标路径
        full_source_path = os.path.join(source_path, source_name)
        full_destination_path = os.path.join(destination_path, destination_name)
        
        # 检查源文件或目录是否存在
        if not os.path.exists(full_source_path):
            raise FileNotFoundError(f"源文件或目录 {source_name} 不存在")
        
        # 检查目标路径是否存在同名文件或目录
        if os.path.exists(full_destination_path):
            raise FileExistsError(f"目标路径已存在同名文件或目录 {destination_name}")
        
        # 创建目标目录（如果不存在）
        os.makedirs(destination_path, exist_ok=True)
        
        # 创建符号链接
        os.symlink(full_source_path, full_destination_path)
        
        return True
    except Exception as e:
        raise e


# 添加创建硬链接的函数
async def create_hardlink(source_path: str, source_name: str, destination_path: str, destination_name: str) -> bool:
    """创建硬链接"""
    try:
        # 确保文件名不包含路径遍历字符
        if ".." in source_name or source_name.startswith("/") or ".." in destination_name or destination_name.startswith("/"):
            raise ValueError("无效的文件名")
        
        # 构建完整源路径和目标路径
        full_source_path = os.path.join(source_path, source_name)
        full_destination_path = os.path.join(destination_path, destination_name)
        
        # 检查源文件是否存在
        if not os.path.exists(full_source_path):
            raise FileNotFoundError(f"源文件 {source_name} 不存在")
        
        # 硬链接不能是目录
        if os.path.isdir(full_source_path):
            raise ValueError("不能为目录创建硬链接")
        
        # 检查目标路径是否存在同名文件或目录
        if os.path.exists(full_destination_path):
            raise FileExistsError(f"目标路径已存在同名文件或目录 {destination_name}")
        
        # 创建目标目录（如果不存在）
        os.makedirs(destination_path, exist_ok=True)
        
        # 创建硬链接
        os.link(full_source_path, full_destination_path)
        
        return True
    except Exception as e:
        raise e


async def get_file_tree(path: str, max_depth: int = 3) -> Dict[str, Any]:
    """获取指定路径下的文件树结构"""
    async def _build_tree(current_path: str, depth: int = 0) -> Dict[str, Any]:
        if depth > max_depth:
            return {"filename": os.path.basename(current_path), "is_directory": True, "children": [], "truncated": True}
        
        if not os.path.exists(current_path):
            raise FileNotFoundError(f"路径 {current_path} 不存在")
        
        try:
            # 获取当前目录的基本信息
            stat_info = os.stat(current_path)
            
            # 获取用户和用户组信息
            try:
                user_info = pwd.getpwuid(stat_info.st_uid)
                user_name = user_info.pw_name
            except KeyError:
                user_name = str(stat_info.st_uid)
            
            try:
                group_info = grp.getgrgid(stat_info.st_gid)
                group_name = group_info.gr_name
            except KeyError:
                group_name = str(stat_info.st_gid)
            
            tree_node = {
                "filename": os.path.basename(current_path) if current_path != "/" else "/",
                "size": format_file_size(stat_info.st_size),
                "is_directory": os.path.isdir(current_path),
                "modified_time": datetime.fromtimestamp(stat_info.st_mtime),
                "permissions": format_permissions(stat_info.st_mode),
                "user": user_name,
                "group": group_name,
                "children": []
            }
            
            # 如果是目录，递归获取子文件和子目录
            if os.path.isdir(current_path) and depth < max_depth:
                try:
                    # 使用 scandir 提供更好的性能
                    with os.scandir(current_path) as entries:
                        for entry in entries:
                            try:
                                child_node = await _build_tree(entry.path, depth + 1)
                                tree_node["children"].append(child_node)
                            except (OSError, IOError):
                                # 跳过无法访问的文件或目录
                                continue
                except (OSError, IOError):
                    # 如果 scandir 失败，回退到 listdir
                    try:
                        for item in os.listdir(current_path):
                            item_path = os.path.join(current_path, item)
                            try:
                                child_node = await _build_tree(item_path, depth + 1)
                                tree_node["children"].append(child_node)
                            except (OSError, IOError):
                                # 跳过无法访问的文件或目录
                                continue
                    except (OSError, IOError):
                        # 如果都无法访问，标记为无法读取
                        tree_node["children"] = []
                        tree_node["error"] = "无法读取目录内容"
            
            return tree_node
        except Exception as e:
            raise e
    
    return await _build_tree(path)


async def get_directory_size(path: str) -> int:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _sync_get_directory_size, path)

def _sync_get_directory_size(path: str) -> int:
    if not os.path.exists(path):
        raise FileNotFoundError(f"路径 {path} 不存在")
    if not os.path.isdir(path):
        raise ValueError(f"{path} 不是目录")
    total = 0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_file(follow_symlinks=False):
                            try:
                                total += entry.stat(follow_symlinks=False).st_size
                            except Exception:
                                continue
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                    except Exception:
                        continue
        except Exception:
            continue
    return total


# 后台下载任务函数
async def background_download_task(download_id: str, url: str, destination_path: str, filename: str = "", verify_ssl: bool = True):
    """后台执行下载任务"""
    try:
        from urllib.parse import urlparse
        import time
        # 延迟导入httpx以避免导入错误
        import httpx
        
        # 初始化进度
        download_tasks[download_id] = {
            "status": "starting",
            "progress": 0,
            "filename": filename,
            "url": url,
            "destination_path": destination_path,
            "total_size": 0,
            "downloaded_size": 0,
            "created_at": datetime.now(),
            "completed_at": None,
            "error": None
        }
        
        # 验证URL格式
        if not url.startswith(("http://", "https://")):
            download_tasks[download_id]["status"] = "error"
            download_tasks[download_id]["error"] = "无效的URL格式，必须以http://或https://开头"
            return
        
        # 如果没有指定文件名，从URL中提取
        if not filename:
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            # 如果无法从URL中提取文件名，使用时间戳作为文件名
            if not filename or '.' not in filename:
                filename = f"downloaded_file_{int(time.time())}"
        
        # 更新进度中的文件名
        download_tasks[download_id]["filename"] = filename
        
        # 确保文件名不包含路径遍历字符
        if ".." in filename or filename.startswith("/"):
            download_tasks[download_id]["status"] = "error"
            download_tasks[download_id]["error"] = "无效的文件名"
            return
        
        # 构建完整目标路径
        full_destination_path = os.path.join(destination_path, filename)
        
        # 检查目标路径是否存在同名文件
        if os.path.exists(full_destination_path):
            download_tasks[download_id]["status"] = "error"
            download_tasks[download_id]["error"] = f"目标路径已存在同名文件 {filename}"
            return
        
        # 创建目标目录（如果不存在）
        os.makedirs(destination_path, exist_ok=True)
        
        # 设置请求头，模拟浏览器请求
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # 更新进度状态
        download_tasks[download_id]["status"] = "downloading"
        
        # 使用异步HTTP客户端下载文件，根据verify_ssl参数决定是否验证SSL证书
        async with httpx.AsyncClient(headers=headers, timeout=300.0, verify=verify_ssl) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()  # 检查HTTP错误
                
                # 获取文件总大小
                total_size = int(response.headers.get('content-length', 0))
                download_tasks[download_id]["total_size"] = total_size
                
                # 保存文件
                downloaded_size = 0
                with open(full_destination_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        # 更新进度
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            download_tasks[download_id]["progress"] = min(progress, 100)
                        download_tasks[download_id]["downloaded_size"] = downloaded_size
        
        # 更新进度状态为完成
        download_tasks[download_id]["status"] = "completed"
        download_tasks[download_id]["progress"] = 100
        download_tasks[download_id]["completed_at"] = datetime.now()
        
    except Exception as e:
        # 更新进度状态为错误
        if download_id in download_tasks:
            download_tasks[download_id]["status"] = "error"
            download_tasks[download_id]["error"] = str(e)
            download_tasks[download_id]["completed_at"] = datetime.now()


async def start_remote_download(url: str, destination_path: str, filename: str = "", verify_ssl: bool = True) -> str:
    """启动远程下载任务"""
    # 生成下载ID
    download_id = str(uuid.uuid4())
    
    # 在后台启动下载任务，传递SSL证书验证参数
    asyncio.create_task(background_download_task(download_id, url, destination_path, filename, verify_ssl))
    
    return download_id


async def get_download_task_list() -> List[Dict]:
    """获取下载任务列表"""
    task_list = []
    for download_id, task_info in download_tasks.items():
        task_list.append({
            "download_id": download_id,
            "status": task_info["status"],
            "progress": task_info["progress"],
            "filename": task_info["filename"],
            "url": task_info["url"],
            "destination_path": task_info["destination_path"],
            "total_size": task_info["total_size"],
            "downloaded_size": task_info["downloaded_size"],
            "created_at": task_info["created_at"],
            "completed_at": task_info["completed_at"],
            "error": task_info["error"]
        })
    return task_list


async def get_download_task(download_id: str) -> Dict:
    """获取单个下载任务详情"""
    if download_id in download_tasks:
        task_info = download_tasks[download_id]
        return {
            "download_id": download_id,
            "status": task_info["status"],
            "progress": task_info["progress"],
            "filename": task_info["filename"],
            "url": task_info["url"],
            "destination_path": task_info["destination_path"],
            "total_size": task_info["total_size"],
            "downloaded_size": task_info["downloaded_size"],
            "created_at": task_info["created_at"],
            "completed_at": task_info["completed_at"],
            "error": task_info["error"]
        }
    else:
        return {
            "download_id": download_id,
            "status": "not_found",
            "progress": 0,
            "filename": "",
            "url": "",
            "destination_path": "",
            "total_size": 0,
            "downloaded_size": 0,
            "created_at": None,
            "completed_at": None,
            "error": "下载任务不存在"
        }


async def cancel_download_task(download_id: str) -> bool:
    """取消下载任务（终止下载）"""
    if download_id in download_tasks:
        task_info = download_tasks[download_id]
        # 如果任务正在进行中，将其标记为已取消
        if task_info["status"] == "downloading":
            task_info["status"] = "cancelled"
            task_info["completed_at"] = datetime.now()
            task_info["error"] = "下载任务已被用户取消"
        # 如果任务已启动但未开始下载，直接移除
        elif task_info["status"] == "starting":
            del download_tasks[download_id]
        # 对于已完成、错误或已取消的任务，不进行任何操作
        return True
    return False


async def delete_download_task_record(download_id: str) -> bool:
    """删除下载任务记录，并删除已下载的文件"""
    if download_id in download_tasks:
        # 只有已完成、错误或已取消的任务才能被删除记录
        status = download_tasks[download_id]["status"]
        if status in ["completed", "error", "cancelled"]:
            # 获取任务信息
            task_info = download_tasks[download_id]
            
            # 如果是已取消的任务，删除已下载的部分文件
            if status == "cancelled" and "destination_path" in task_info and "filename" in task_info:
                try:
                    file_path = os.path.join(task_info["destination_path"], task_info["filename"])
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    # 记录删除文件时的错误，但不中断删除任务记录的操作
                    print(f"删除已下载文件时出错: {e}")
            
            # 删除任务记录
            del download_tasks[download_id]
            return True
        else:
            # 进行中的任务不能删除记录
            return False
    return False
