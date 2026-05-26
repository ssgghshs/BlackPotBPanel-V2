from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from typing import List
import os
import logging
import tempfile
from datetime import datetime
import asyncio
from middleware.auth import get_current_active_user
from config.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.log import service, schemas
from sqlalchemy import delete

from app.user.schemas import RoleEnum


async def cleanup_file(file_path: str):
    """异步清理临时文件"""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        logger.error(f"清理临时文件失败: {str(e)}")

# 配置日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["logs"])

# 获取日志目录路径 - 修正路径计算方式
# 从当前文件向上回溯到backend目录，然后进入logs目录
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(current_dir))
LOGS_DIR = os.path.join(backend_dir, "logs")

# 系统日志API

@router.get("/files", response_model=List[str])
async def get_log_files(current_user = Depends(get_current_active_user)):
    """获取日志文件列表"""
    try:
        # 调试信息
        logger.info(f"Current file path: {__file__}")
        logger.info(f"Computed log directory path: {LOGS_DIR}")
        logger.info(f"Does the log directory exist: {os.path.exists(LOGS_DIR)}")
        
        if not os.path.exists(LOGS_DIR):
            logger.error(f"Log directory does not exist: {LOGS_DIR}")
            return []
        
        log_files = []
        for file in os.listdir(LOGS_DIR):
            if file.endswith(".log"):
                log_files.append(file)
        
        # 按文件名排序
        log_files.sort(reverse=True)
        logger.info(f"Found log file: {log_files}")
        return log_files
    except Exception as e:
        logger.error(f"Failed to retrieve the log file list: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve the log file list: {str(e)}"
        )

@router.get("/content/{filename}")
async def get_log_content(filename: str, current_user = Depends(get_current_active_user)):
    """获取日志文件内容"""
    try:
        # 验证文件名是否合法
        if not filename.endswith(".log"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件名必须以.log结尾"
            )
        
        # 防止路径遍历攻击
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的文件名"
            )
        
        file_path = os.path.join(LOGS_DIR, filename)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="日志文件不存在"
            )
        
        # 读取文件内容
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return {"filename": filename, "content": content}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取日志文件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"读取日志文件失败: {str(e)}"
        )


@router.post("/clear/delete")
async def clear_logs(
        current_user=Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
):
    """清理系统日志文件（除当日日志外）"""
    try:
        # 检查日志目录是否存在
        if not os.path.exists(LOGS_DIR):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="日志目录不存在"
            )

        # 获取今天的日期，用于识别当日日志文件
        today = datetime.now().strftime("%Y-%m-%d")
        today_log_filename = f"app_{today}.log"

        # 获取所有日志文件
        log_files = []
        deleted_files = []

        for file in os.listdir(LOGS_DIR):
            if file.endswith(".log"):
                log_files.append(file)
                # 跳过当日日志文件
                if file == today_log_filename:
                    continue
                # 删除非当日日志文件
                file_path = os.path.join(LOGS_DIR, file)
                os.remove(file_path)
                deleted_files.append(file)

        logger.info(
            f"Successfully cleaned up {len(deleted_files)} log files (today's log {today_log_filename} was not cleaned) ")
        return {
            "message": f"Successfully cleaned up {len(deleted_files)} log files (today's log {today_log_filename} was not cleaned) ",
            "deleted_files": deleted_files,
            "skipped_files": [today_log_filename] if today_log_filename in log_files else []
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clean log files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clean log files: {str(e)}"
        )


@router.post("/clear/{filename}/delete")
async def clear_log_file(
        filename: str,
        current_user=Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
):
    """清理指定系统日志文件"""
    try:
        # 验证文件名是否合法
        if not filename.endswith(".log"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件名必须以.log结尾"
            )

        # 防止路径遍历攻击
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的文件名"
            )

        # 检查日志目录是否存在
        if not os.path.exists(LOGS_DIR):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="日志目录不存在"
            )

        # 获取今天的日期，用于识别当日日志文件
        today = datetime.now().strftime("%Y-%m-%d")
        today_log_filename = f"app_{today}.log"

        # 禁止删除当日日志文件
        if filename == today_log_filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能删除当日日志文件"
            )

        file_path = os.path.join(LOGS_DIR, filename)

        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="日志文件不存在"
            )

        # 删除指定日志文件
        os.remove(file_path)

        logger.info(f"Successfully deleted the log file: {filename}")
        return {
            "message": f"Successfully deleted the log file: {filename}",
            "deleted_file": filename
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete log file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete log file: {str(e)}"
        )


@router.get("/export/{filename}")
async def export_log_file(
    filename: str,
    current_user=Depends(get_current_active_user)
):
    """
    导出指定的日志文件
    - 验证文件名安全性
    - 检查文件是否存在
    - 返回文件下载
    """
    try:
        # 1. 验证文件名格式
        if not filename.endswith(".log"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件名必须以 .log 结尾"
            )

        # 2. 防止路径遍历攻击
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的文件名，禁止路径遍历"
            )

        # 3. 检查日志目录是否存在
        if not os.path.exists(LOGS_DIR):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="日志目录不存在，请联系管理员"
            )

        # 4. 构建文件路径
        file_path = os.path.join(LOGS_DIR, filename)

        # 5. 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"日志文件 '{filename}' 不存在"
            )

        # 6. 写本地日志
        logger.info(f"用户 {current_user.username} 导出日志文件: {filename}")

        # 7. 返回文件下载响应
        # 处理中文文件名的编码问题
        from urllib.parse import quote
        encoded_filename = quote(filename.encode('utf-8'))
        
        return FileResponse(
            path=file_path,
            filename=filename,  # 下载时的文件名
            media_type='application/octet-stream',  # 强制下载
            # 可选：设置 headers
            headers={
                "Content-Disposition": f'attachment; filename*=UTF-8''{encoded_filename}',
            }
        )

    except HTTPException:
        # 重新抛出已知异常
        raise
    except Exception as e:
        # 捕获未知异常
        logger.error(f"导出日志文件失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出日志文件失败: {str(e)}"
        )



# 登录日志API

@router.get("/login", response_model=List[schemas.LoginLog])
async def get_login_logs(
    skip: int = 0, 
    limit: int = 100,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取登录日志列表"""
    login_logs = await service.get_login_logs(db, skip=skip, limit=limit)
    return login_logs


@router.get("/login/user/{user_id}", response_model=List[schemas.LoginLog])
async def get_user_login_logs(
    user_id: int,
    skip: int = 0, 
    limit: int = 100,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取特定用户的登录日志"""
    # 只有管理员或用户自己可以查看登录日志
    if current_user.id != user_id and current_user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    login_logs = await service.get_user_login_logs(db, user_id=user_id, skip=skip, limit=limit)
    return login_logs


@router.get("/login/me", response_model=List[schemas.LoginLog])
async def get_my_login_logs(
    skip: int = 0, 
    limit: int = 100,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户的登录日志"""
    login_logs = await service.get_user_login_logs(db, user_id=current_user.id, skip=skip, limit=limit)
    return login_logs


@router.get("/login/export")
async def export_login_logs(
    skip: int = 0,
    limit: int = 1000,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """导出登录日志为CSV文件"""
    
    try:
        # 获取登录日志数据
        login_logs = await service.get_login_logs(db, skip=skip, limit=limit)
        
        # 生成CSV内容
        csv_content = "用户ID,用户名,登录时间,登录IP,设备信息"
        for log in login_logs:
            csv_content += f"{log.user_id},{log.username},{log.login_time},{log.ip_address or ''},{log.user_agent or ''}"
        
        # 创建临时文件
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"login_logs_{timestamp}.csv"
        file_path = os.path.join(temp_dir, filename)
        
        # 写入CSV文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(csv_content)
        
        logger.info(f"管理员 {current_user.username} 导出了 {len(login_logs)} 条登录日志")
        
        # 返回文件下载响应
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="text/csv",
            background=lambda: asyncio.create_task(cleanup_file(file_path)) if os.path.exists(file_path) else None
        );
    except Exception as e:
        logger.error(f"导出登录日志失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出登录日志失败: {str(e)}"
        )



@router.post("/login/clear/delete")
async def clear_login_logs(
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """清理所有登录日志（仅管理员）"""
    if current_user.role != RoleEnum.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以清理登录日志"
        )

    try:
        # 删除所有登录日志记录
        stmt = delete(service.models.LoginLog)
        result = await db.execute(stmt)
        await db.commit()

        deleted_count = result.rowcount
        logger.info(f"成功清理 {deleted_count} 条登录日志记录")

        return {
            "message": f"成功清理 {deleted_count} 条登录日志记录",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"清理登录日志失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理登录日志失败: {str(e)}"
        )



# 访问日志API (Nginx access.log 和 error.log)

@router.get("/access-content")
async def get_access_log_content(
    log_type: str = "access",  # "access" 或 "error"
    lines: int = 100,  # 默认返回最后100行
    current_user = Depends(get_current_active_user)
    # 移除了db参数，因为不再需要数据库连接
):
    """获取访问日志内容（access.log 或 error.log）"""
    # 从配置文件中获取日志文件路径，而不是从环境变量
    from utils.config_manager import config_manager
    config = config_manager.load_config()
    
    # 根据日志类型选择文件路径
    if log_type == "access":
        log_file_path = config.get("access_log_path", "/var/log/nginx/access.log")
    elif log_type == "error":
        log_file_path = config.get("error_log_path", "/var/log/nginx/error.log")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="日志类型必须是 'access' 或 'error'"
        )
    
    # 检查文件是否存在
    if not os.path.exists(log_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"日志文件不存在: {log_file_path}"
        )
    
    try:
        # 确保lines参数是整数类型
        lines = int(lines)
        
        # 读取文件的最后N行
        with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
            # 读取所有行
            all_lines = f.readlines()
            
            # 获取最后N行
            lines_found = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            # 移除行尾的换行符
            lines_found = [line.rstrip('\n').rstrip('\r') for line in lines_found]
        
        return {
            "log_type": log_type,
            "file_path": log_file_path,
            "content": lines_found,
            "line_count": len(lines_found)
        }
    except ValueError as e:
        logger.error(f"参数类型错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"参数类型错误: {str(e)}"
        )
    except Exception as e:
        logger.error(f"读取访问日志文件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"读取访问日志文件失败: {str(e)}"
        )


# 新增：获取访问日志配置（从配置文件获取）
@router.get("/access-config/latest")
async def get_latest_access_log_config(current_user = Depends(get_current_active_user)):
    """获取最新的访问日志配置（从配置文件获取）"""
    try:
        from utils.config_manager import config_manager
        config = config_manager.load_config()
        
        # 使用字符串格式化日期，避免序列化问题
        from datetime import datetime
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]  # 截取微秒到毫秒
        
        config_data = {
            "id": 1,
            "access_log_path": config.get("access_log_path", "/var/log/nginx/access.log"),
            "error_log_path": config.get("error_log_path", "/var/log/nginx/error.log"),
            "created_at": now_str,
            "updated_at": now_str
        }
        
        return config_data
    except Exception as e:
        logger.error(f"获取访问日志配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取访问日志配置失败: {str(e)}"
        )


# 新增：创建或更新访问日志配置（通过配置文件更新）
@router.post("/access-config")
async def create_or_update_access_log_config(
    config_data: dict,
    current_user = Depends(get_current_active_user)
):
    """创建或更新访问日志配置（通过配置文件更新）"""
    try:
        # 从配置数据中获取路径
        access_log_path = config_data.get("access_log_path", "/var/log/nginx/access.log")
        error_log_path = config_data.get("error_log_path", "/var/log/nginx/error.log")
        
        # 准备配置数据
        new_config = {
            "access_log_path": access_log_path,
            "error_log_path": error_log_path
        }
        
        # 保存到配置文件
        from utils.config_manager import config_manager
        success = config_manager.save_config(new_config)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="保存配置文件失败"
            )
        
        # 使用字符串格式化日期，避免序列化问题
        from datetime import datetime
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]  # 截取微秒到毫秒
        
        # 返回保存的配置
        response_data = {
            "id": 1,
            "access_log_path": access_log_path,
            "error_log_path": error_log_path,
            "created_at": now_str,
            "updated_at": now_str,
            "message": "配置已成功保存，无需重启服务即可生效"
        }
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存访问日志配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存访问日志配置失败: {str(e)}"
        )


# 新增：导出访问日志接口
@router.get("/access-export")
async def export_access_log(
    log_type: str = "access",  # "access" 或 "error"
    current_user = Depends(get_current_active_user)
):
    """
    导出访问日志或错误日志文件
    - 验证日志类型和文件路径安全性
    - 检查文件是否存在
    - 返回文件下载响应
    """
    try:
        # 1. 验证日志类型
        if log_type not in ["access", "error"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="日志类型必须是 'access' 或 'error'"
            )

        # 2. 从配置文件中获取日志文件路径
        from utils.config_manager import config_manager
        config = config_manager.load_config()
        
        # 3. 根据日志类型选择文件路径
        if log_type == "access":
            log_file_path = config.get("access_log_path", "/var/log/nginx/access.log")
            filename = "access.log"
        else:
            log_file_path = config.get("error_log_path", "/var/log/nginx/error.log")
            filename = "error.log"

        # 4. 检查文件是否存在
        if not os.path.exists(log_file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"日志文件不存在: {log_file_path}"
            )

        # 5. 记录导出操作日志
        logger.info(f"用户 {current_user.username} 导出了 {log_type} 日志文件: {log_file_path}")

        # 6. 返回文件下载响应
        # 处理中文文件名的编码问题
        from urllib.parse import quote
        encoded_filename = quote(filename.encode('utf-8'))
        
        return FileResponse(
            path=log_file_path,
            filename=filename,
            media_type='application/octet-stream',  # 强制下载
            headers={
                "Content-Disposition": f'attachment; filename*=UTF-8''{encoded_filename}',
            }
        )

    except HTTPException:
        # 重新抛出已知异常
        raise
    except Exception as e:
        # 捕获未知异常
        logger.error(f"导出访问日志文件失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出访问日志文件失败: {str(e)}"
        )


# 新增：清理访问日志接口
@router.post("/access-clear/delete")
async def clear_access_log(
    log_type: str = "access",  # "access" 或 "error"
    current_user = Depends(get_current_active_user)
):
    """
    清理访问日志或错误日志文件
    - 验证日志类型和文件路径安全性
    - 检查文件是否存在
    - 清空日志文件内容
    """
    try:
        # 1. 验证日志类型
        if log_type not in ["access", "error"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="日志类型必须是 'access' 或 'error'"
            )

        # 2. 从配置文件中获取日志文件路径
        from utils.config_manager import config_manager
        config = config_manager.load_config()
        
        # 3. 根据日志类型选择文件路径
        if log_type == "access":
            log_file_path = config.get("access_log_path", "/var/log/nginx/access.log")
        else:
            log_file_path = config.get("error_log_path", "/var/log/nginx/error.log")

        # 4. 检查文件是否存在
        if not os.path.exists(log_file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"日志文件不存在: {log_file_path}"
            )

        # 5. 清空文件内容
        with open(log_file_path, "w", encoding="utf-8") as f:
            f.truncate(0)  # 清空文件内容

        # 6. 记录清理操作日志
        logger.info(f"用户 {current_user.username} 清理了 {log_type} 日志文件: {log_file_path}")

        return {
            "message": f"{log_type} 日志文件已成功清理",
            "log_type": log_type,
            "file_path": log_file_path
        }

    except HTTPException:
        # 重新抛出已知异常
        raise
    except Exception as e:
        # 捕获未知异常
        logger.error(f"清理访问日志文件失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理访问日志文件失败: {str(e)}"
        )
