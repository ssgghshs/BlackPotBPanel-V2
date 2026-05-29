from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from config.database import get_db
from app.user import schemas, models
from app.user.schemas import RoleEnum
from middleware import auth
import uuid
import base64
from utils.captcha import generate_captcha, verify_captcha
from middleware.auth import authenticate_user, create_access_token, get_current_active_user, verify_password
from datetime import timedelta
from config.settings import settings
from app.log import schemas as log_schemas, service as log_service

import geoip2.database
import os
import ipaddress
import logging
import time
from typing import Dict, List

# 配置日志记录器
logger = logging.getLogger(__name__)

ENV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "setting.conf")


def _read_security_entrance() -> str:
    """从 setting.conf 动态读取安全入口"""
    if os.path.exists(ENV_FILE_PATH):
        with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith("SECURITY_ENTRANCE="):
                    val = line.split("=", 1)[1].strip()
                    return val
    return ""


# 存储验证码的字典（在生产环境中应该使用Redis等）
CAPTCHA_STORE = {}

# IP 登录失败限制（当 LOGIN_LIMIT=True 时生效）
MAX_LOGIN_FAILURES = 5           # 最大失败次数
LOGIN_LOCKOUT_SECONDS = 200      # 锁定时间（秒）
IP_FAILURE_MAP: Dict[str, List[float]] = {}  # IP -> [失败时间戳列表]


def _cleanup_ip_failures():
    """清理已过期的 IP 失败记录，防止内存泄漏"""
    now = time.time()
    cutoff = now - LOGIN_LOCKOUT_SECONDS
    expired_ips = [ip for ip, times in IP_FAILURE_MAP.items()
                   if all(t < cutoff for t in times)]
    for ip in expired_ips:
        del IP_FAILURE_MAP[ip]


def _get_ip_block_remaining(ip_address: str) -> int:
    """检查 IP 是否被锁定，返回剩余锁定秒数（0 表示未被锁定）"""
    if not settings.LOGIN_LIMIT:
        return 0
    now = time.time()
    cutoff = now - LOGIN_LOCKOUT_SECONDS
    failures = [t for t in IP_FAILURE_MAP.get(ip_address, []) if t >= cutoff]
    IP_FAILURE_MAP[ip_address] = failures
    if len(failures) < MAX_LOGIN_FAILURES:
        return 0
    oldest = min(failures)
    remaining = int(LOGIN_LOCKOUT_SECONDS - (now - oldest)) + 1
    return max(1, remaining)


def _record_ip_failure(ip_address: str):
    """记录一次 IP 登录失败"""
    if not settings.LOGIN_LIMIT:
        return
    now = time.time()
    if ip_address not in IP_FAILURE_MAP:
        IP_FAILURE_MAP[ip_address] = []
    IP_FAILURE_MAP[ip_address].append(now)
    _cleanup_ip_failures()


def _clear_ip_failures(ip_address: str):
    """登录成功后清除该 IP 的失败记录"""
    IP_FAILURE_MAP.pop(ip_address, None)

router = APIRouter(prefix="/users", tags=["users"])

# 默认密码常量
DEFAULT_PASSWORD = "admin@123"

def is_private_ip(ip_address: str) -> bool:
    """判断IP地址是否为内网地址"""
    try:
        ip = ipaddress.ip_address(ip_address)
        # 检查是否为私有地址
        return ip.is_private
    except ValueError:
        # 如果不是有效的IP地址，返回False
        return False

def get_location_from_ip(ip_address: str) -> str:
    """通过IP地址获取地理位置信息"""
    if not ip_address or ip_address in ["127.0.0.1", "localhost", "::1"]:
        return "Local Address"
    
    # 检查是否为内网地址
    if is_private_ip(ip_address):
        return "Intranet address"
    
    try:
        # 使用 settings 中的 GEOIP_CITY_DB_PATH
        db_path = settings.GEOIP_CITY_DB_PATH
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)
        
        # 检查数据库文件是否存在
        if not os.path.exists(db_path):
            logger.error(f"Failed to obtain geographic location information: {db_path}")
            return "未知位置"
        
        # 使用GeoIP2解析IP地址
        with geoip2.database.Reader(db_path) as reader:
            response = reader.city(ip_address)
            country = response.country.name or ""
            city = response.city.name or ""
            location = f"{country} {city}".strip()
            return location if location else "Unknown location"
    except Exception as e:
        logger.error(f"Failed to obtain geographic location information: {e}")
        return "Unknown location"

@router.post("/create", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: schemas.UserCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # 只有管理员可以创建用户
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # 检查用户名是否已存在
        result = await db.execute(select(models.User).filter(models.User.username == user.username))
        db_user = result.scalar_one_or_none()
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # 检查邮箱是否已存在
        result = await db.execute(select(models.User).filter(models.User.email == user.email))
        db_user = result.scalar_one_or_none()
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # 创建新用户
        db_user = models.User(
            username=user.username,
            email=user.email,
            role=user.role
        )
        db_user.set_password(user.password)
        
        db.add(db_user)
    
        
        await db.commit()
        await db.refresh(db_user)
        
        return db_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建用户失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.get("/captcha", response_model=schemas.CaptchaResponse)
async def get_captcha():
    """获取验证码图片"""
    # 生成验证码
    captcha_text, captcha_image = generate_captcha()
    
    # 生成唯一的验证码ID
    captcha_id = str(uuid.uuid4())
    
    # 存储验证码（在生产环境中应该使用Redis等）
    CAPTCHA_STORE[captcha_id] = captcha_text
    
    # 为了防止内存泄漏，只保留最近的1000个验证码
    if len(CAPTCHA_STORE) > 1000:
        # 删除最早的验证码
        oldest_key = next(iter(CAPTCHA_STORE))
        del CAPTCHA_STORE[oldest_key]
    
    return {
        "captcha_id": captcha_id,
        "captcha_image": f"data:image/png;base64,{captcha_image}"
    }


@router.post("/login", response_model=schemas.TokenWithDefaultPasswordCheck)
async def login(request: Request, form_data: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录接口"""
    # 验证验证码
    captcha_id = request.headers.get("captcha-id")
    if not captcha_id or captcha_id not in CAPTCHA_STORE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid captcha ID"
        )
    
    correct_captcha = CAPTCHA_STORE[captcha_id]
    if not verify_captcha(form_data.captcha, correct_captcha):
        # 验证失败后删除验证码，防止暴力破解
        del CAPTCHA_STORE[captcha_id]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect captcha"
        )
    
    # 验证成功后删除验证码
    del CAPTCHA_STORE[captcha_id]

    # 安全入口校验
    entrance = _read_security_entrance()
    if entrance:
        entrance_header = request.headers.get("EntranceCode", "")
        try:
            decoded_entrance = base64.b64decode(entrance_header).decode("utf-8")
        except Exception:
            decoded_entrance = ""
        if decoded_entrance != entrance:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid security entrance",
            )

    # 获取客户端IP
    ip_address = request.client.host if request.client else None

    # IP 登录频率限制检查
    if ip_address:
        block_remaining = _get_ip_block_remaining(ip_address)
        if block_remaining > 0:
            logger.warning(f"IP {ip_address} 因登录失败过多被限制，剩余 {block_remaining} 秒")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"登录失败次数过多，请等待 {block_remaining} 秒后重试",
            )

    user = await authenticate_user(db, form_data.username, form_data.password, models.User)
    
    # 获取User-Agent
    user_agent = request.headers.get("user-agent")
    
    # 获取地理位置信息
    location = get_location_from_ip(ip_address)
    
    if not user:
        # 记录 IP 登录失败
        if ip_address:
            _record_ip_failure(ip_address)
        
        # 记录失败的登录尝试
        try:
            login_log = log_schemas.LoginLogCreate(
                user_id=0,  # 未知用户ID
                username=form_data.username,
                ip_address=ip_address,
                user_agent=user_agent,
                status="failed",
                location=location
            )
            await log_service.create_login_log(db, login_log)
        except Exception as log_error:
            logger.error(f"记录登录日志失败: {log_error}")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 登录成功，清除该 IP 的失败记录
    if ip_address:
        _clear_ip_failures(ip_address)
    
    # 检查用户是否使用默认密码
    is_default_password = verify_password(DEFAULT_PASSWORD, user.hashed_password)
    
    # 记录成功的登录
    try:
        login_log = log_schemas.LoginLogCreate(
            user_id=user.id,
            username=form_data.username,  # 使用表单数据中的用户名，避免触发延迟加载
            ip_address=ip_address,
            user_agent=user_agent,
            status="success",
            location=location
        )
        await log_service.create_login_log(db, login_log)
    except Exception as log_error:
        logger.error(f"记录登录日志失败: {log_error}")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "is_default_password": is_default_password
    }


@router.get("/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user


@router.post("/me/update", response_model=schemas.UserResponse)
async def update_current_user(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """更新当前用户信息"""
    try:
        # 记录更新的字段信息
        update_fields = []
        original_username = current_user.username
        original_email = current_user.email

        # 检查用户名是否被修改
        if user_update.username and user_update.username != current_user.username:
            # 移除了对管理员用户修改用户名的限制
            
            # 检查新用户名是否已存在
            result = await db.execute(select(models.User).filter(models.User.username == user_update.username))
            existing_user = result.scalar_one_or_none()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )
            current_user.username = user_update.username
            update_fields.append(f"用户名: {original_username} -> {user_update.username}")

        # 检查邮箱是否已存在（如果要更新邮箱）
        if user_update.email and user_update.email != current_user.email:
            result = await db.execute(select(models.User).filter(models.User.email == user_update.email))
            existing_user = result.scalar_one_or_none()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            current_user.email = user_update.email
            update_fields.append(f"邮箱: {original_email} -> {user_update.email}")

        # 如果提供了新密码，则更新密码
        if user_update.password:
            current_user.set_password(user_update.password)
            update_fields.append("密码已更新")

        # 更新角色（如果提供了）
        if user_update.role is not None:
            current_user.role = user_update.role.value
            update_fields.append(f"角色: {user_update.role.value}")

        # 提交更改到数据库
        db.add(current_user)
        await db.commit()
        await db.refresh(current_user)

        return current_user

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:

        logger.error(f"更新用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user information"
        )


@router.get("/{user_id}/detail", response_model=schemas.UserResponse)
async def get_user(user_id: int, 
                   current_user: models.User = Depends(get_current_active_user),
                   db: AsyncSession = Depends(get_db)):
    # 检查请求的用户ID是否是当前用户或当前用户是管理员
    if current_user.id != user_id and current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
        
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return db_user


@router.get("/list", response_model=list[schemas.UserResponse])
async def get_users(skip: int = 0, limit: int = 100,
                    current_user: models.User = Depends(get_current_active_user),
                    db: AsyncSession = Depends(get_db)):
    # 只有管理员可以获取用户列表
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
        
    result = await db.execute(select(models.User).offset(skip).limit(limit))
    users = result.scalars().all()
    return users


@router.post("/{user_id}/update", response_model=schemas.UserResponse)
async def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """更新用户信息"""
    # 检查权限：只有管理员或用户自己可以更新用户信息
    if current_user.id != user_id and current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # 查找要更新的用户
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # 检查用户名是否已存在（如果要更新用户名）
    if user_update.username and user_update.username != db_user.username:
        result = await db.execute(select(models.User).filter(models.User.username == user_update.username))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        db_user.username = user_update.username
    
    # 检查邮箱是否已存在（如果要更新邮箱）
    if user_update.email and user_update.email != db_user.email:
        result = await db.execute(select(models.User).filter(models.User.email == user_update.email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        db_user.email = user_update.email
    
    # 如果提供了新密码，则更新密码
    if user_update.password:
        db_user.set_password(user_update.password)
    
    # 更新角色（如果提供了）
    if user_update.role is not None:
        db_user.role = user_update.role.value
    
    # 提交更改到数据库
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return db_user


@router.post("/{user_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """删除用户"""
    # 只有管理员可以删除用户
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # 不能删除自己
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    # 查找要删除的用户
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        # 从数据库中删除用户
        await db.delete(db_user)
        await db.commit()
        
        # 返回204状态码表示删除成功（无内容返回）
        return
        
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


@router.post("/me/password", response_model=schemas.UserResponse)
async def change_password(
    password_change: schemas.PasswordChange,
    current_user: models.User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """修改当前用户密码"""
    # 验证当前密码是否正确
    if not verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # 设置新密码
    current_user.set_password(password_change.new_password)
    
    # 提交更改到数据库
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    return current_user

@router.post("/logout")
async def logout(
    request: Request,
    current_user: models.User = Depends(get_current_active_user)
):
    """用户退出登录接口
    
    将当前用户的token加入黑名单，使其失效
    """
    # 尝试从Authorization头获取token
    authorization = request.headers.get("Authorization")
    token = None
    
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    
    # 如果找到token，则将其加入黑名单
    if token:
        from middleware.auth import revoke_token
        revoke_token(token)
        logger.info(f"User {current_user.username} logged out successfully")
    else:
        logger.warning(f"No token found for user {current_user.username} during logout")
    
    return {"message": "Logout successful"}