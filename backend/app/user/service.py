import uuid
import base64
import os
import logging
import time
from typing import Dict, List, Optional

from fastapi import HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta

from app.user import schemas, models
from app.user.schemas import RoleEnum
from middleware.auth import (
    authenticate_user, create_access_token, get_current_active_user,
    verify_password, revoke_token,
)
from config.settings import settings
from utils.captcha import generate_captcha, verify_captcha
from app.log import schemas as log_schemas, service as log_service
import geoip2.database
import ipaddress

logger = logging.getLogger(__name__)

ENV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "setting.conf")
DEFAULT_PASSWORD = "admin@123"

# 存储验证码的字典
CAPTCHA_STORE: Dict[str, str] = {}

# IP 登录失败限制
MAX_LOGIN_FAILURES = 5
LOGIN_LOCKOUT_SECONDS = 200
IP_FAILURE_MAP: Dict[str, List[float]] = {}


def read_security_entrance() -> str:
    if os.path.exists(ENV_FILE_PATH):
        with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith("SECURITY_ENTRANCE="):
                    val = line.split("=", 1)[1].strip()
                    return val
    return ""


def is_private_ip(ip_address: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_address)
        return ip.is_private
    except ValueError:
        return False


def get_location_from_ip(ip_address: str) -> str:
    if not ip_address or ip_address in ["127.0.0.1", "localhost", "::1"]:
        return "Local Address"
    if is_private_ip(ip_address):
        return "Intranet address"
    try:
        db_path = settings.GEOIP_CITY_DB_PATH
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)
        if not os.path.exists(db_path):
            logger.error(f"Failed to obtain geographic location information: {db_path}")
            return "未知位置"
        with geoip2.database.Reader(db_path) as reader:
            response = reader.city(ip_address)
            country = response.country.name or ""
            city = response.city.name or ""
            location = f"{country} {city}".strip()
            return location if location else "Unknown location"
    except Exception as e:
        logger.error(f"Failed to obtain geographic location information: {e}")
        return "Unknown location"


def _cleanup_ip_failures():
    now = time.time()
    cutoff = now - LOGIN_LOCKOUT_SECONDS
    expired_ips = [ip for ip, times in IP_FAILURE_MAP.items()
                   if all(t < cutoff for t in times)]
    for ip in expired_ips:
        del IP_FAILURE_MAP[ip]


def get_ip_block_remaining(ip_address: str) -> int:
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
    if not settings.LOGIN_LIMIT:
        return
    now = time.time()
    if ip_address not in IP_FAILURE_MAP:
        IP_FAILURE_MAP[ip_address] = []
    IP_FAILURE_MAP[ip_address].append(now)
    _cleanup_ip_failures()


def _clear_ip_failures(ip_address: str):
    IP_FAILURE_MAP.pop(ip_address, None)


async def create_user(db: AsyncSession, user: schemas.UserCreate, current_user: models.User) -> models.User:
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    result = await db.execute(select(models.User).filter(models.User.username == user.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    result = await db.execute(select(models.User).filter(models.User.email == user.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    db_user = models.User(username=user.username, email=user.email, role=user.role)
    db_user.set_password(user.password)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_captcha() -> dict:
    captcha_text, captcha_image = generate_captcha()
    captcha_id = str(uuid.uuid4())
    CAPTCHA_STORE[captcha_id] = captcha_text
    if len(CAPTCHA_STORE) > 1000:
        oldest_key = next(iter(CAPTCHA_STORE))
        del CAPTCHA_STORE[oldest_key]
    return {"captcha_id": captcha_id, "captcha_image": f"data:image/png;base64,{captcha_image}"}


async def login(request: Request, form_data: schemas.UserLogin, db: AsyncSession) -> dict:
    captcha_id = request.headers.get("captcha-id")
    if not captcha_id or captcha_id not in CAPTCHA_STORE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid captcha ID")

    correct_captcha = CAPTCHA_STORE[captcha_id]
    if not verify_captcha(form_data.captcha, correct_captcha):
        del CAPTCHA_STORE[captcha_id]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect captcha")
    del CAPTCHA_STORE[captcha_id]

    entrance = read_security_entrance()
    if entrance:
        entrance_header = request.headers.get("EntranceCode", "")
        try:
            decoded_entrance = base64.b64decode(entrance_header).decode("utf-8")
        except Exception:
            decoded_entrance = ""
        if decoded_entrance != entrance:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid security entrance")

    ip_address = request.client.host if request.client else None

    if ip_address:
        block_remaining = get_ip_block_remaining(ip_address)
        if block_remaining > 0:
            logger.warning(f"IP {ip_address} 因登录失败过多被限制，剩余 {block_remaining} 秒")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"登录失败次数过多，请等待 {block_remaining} 秒后重试",
            )

    user = await authenticate_user(db, form_data.username, form_data.password, models.User)
    user_agent = request.headers.get("user-agent")
    location = get_location_from_ip(ip_address)

    if not user:
        if ip_address:
            _record_ip_failure(ip_address)
        try:
            login_log = log_schemas.LoginLogCreate(
                user_id=0, username=form_data.username,
                ip_address=ip_address, user_agent=user_agent,
                status="failed", location=location
            )
            await log_service.create_login_log(db, login_log)
        except Exception as log_error:
            logger.error(f"记录登录日志失败: {log_error}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if ip_address:
        _clear_ip_failures(ip_address)

    is_default_password = verify_password(DEFAULT_PASSWORD, user.hashed_password)

    try:
        login_log = log_schemas.LoginLogCreate(
            user_id=user.id, username=form_data.username,
            ip_address=ip_address, user_agent=user_agent,
            status="success", location=location
        )
        await log_service.create_login_log(db, login_log)
    except Exception as log_error:
        logger.error(f"记录登录日志失败: {log_error}")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": form_data.username}, expires_delta=access_token_expires)

    return {"access_token": access_token, "token_type": "bearer", "is_default_password": is_default_password}


async def get_user(db: AsyncSession, user_id: int, current_user: models.User) -> models.User:
    if current_user.id != user_id and current_user.role != RoleEnum.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user


async def get_users(db: AsyncSession, skip: int, limit: int, current_user: models.User) -> list[models.User]:
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    result = await db.execute(select(models.User).offset(skip).limit(limit))
    return result.scalars().all()


async def update_current_user(db: AsyncSession, user_update: schemas.UserUpdate, current_user: models.User) -> models.User:
    if user_update.username and user_update.username != current_user.username:
        result = await db.execute(select(models.User).filter(models.User.username == user_update.username))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
        current_user.username = user_update.username

    if user_update.email and user_update.email != current_user.email:
        result = await db.execute(select(models.User).filter(models.User.email == user_update.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        current_user.email = user_update.email

    if user_update.password:
        current_user.set_password(user_update.password)

    if user_update.role is not None:
        current_user.role = user_update.role.value

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user


async def update_user(db: AsyncSession, user_id: int, user_update: schemas.UserUpdate, current_user: models.User) -> models.User:
    if current_user.id != user_id and current_user.role != RoleEnum.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user_update.username and user_update.username != db_user.username:
        result = await db.execute(select(models.User).filter(models.User.username == user_update.username))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
        db_user.username = user_update.username

    if user_update.email and user_update.email != db_user.email:
        result = await db.execute(select(models.User).filter(models.User.email == user_update.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        db_user.email = user_update.email

    if user_update.password:
        db_user.set_password(user_update.password)

    if user_update.role is not None:
        db_user.role = user_update.role.value

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def delete_user(db: AsyncSession, user_id: int, current_user: models.User) -> None:
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    if current_user.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")

    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(db_user)
    await db.commit()


async def change_password(db: AsyncSession, password_change: schemas.PasswordChange, current_user: models.User) -> models.User:
    if not verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.set_password(password_change.new_password)
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user


async def logout(request: Request, current_user: models.User) -> dict:
    authorization = request.headers.get("Authorization")
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    if token:
        revoke_token(token)
        logger.info(f"User {current_user.username} logged out successfully")
    else:
        logger.warning(f"No token found for user {current_user.username} during logout")
    return {"message": "Logout successful"}
