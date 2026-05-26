from datetime import datetime, timedelta
from typing import Optional, Set
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from config.settings import settings
from config.database import get_db
import logging

# 配置日志记录器
logger = logging.getLogger(__name__)

# 简单的内存中token黑名单（生产环境应使用Redis等持久化存储）
TOKEN_BLACKLIST: Set[str] = set()

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希值"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_user(db: AsyncSession, username: str):
    """根据用户名获取用户"""
    # 延迟导入以避免循环导入
    from app.user import models
    
    result = await db.execute(select(models.User).filter(models.User.username == username))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, username: str, password: str, User):
    """验证用户"""
    user = await get_user(db, username)
    if not user:
        return None
    if not verify_password(password, str(user.hashed_password)):
        return None
    return user


from fastapi import Request

def revoke_token(token: str) -> None:
    """将token添加到黑名单，使其失效"""
    try:
        # 解码token获取其过期时间
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], options={"verify_signature": True, "verify_exp": False})
        # 使用token的签名部分作为黑名单的键（更安全）
        TOKEN_BLACKLIST.add(token)
        logger.info(f"Token revoked for user: {payload.get('sub')}")
    except JWTError as e:
        logger.error(f"Failed to revoke token: {e}")
        # 即使解码失败，也将token添加到黑名单，以防万一
        TOKEN_BLACKLIST.add(token)

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    """获取当前用户 - 同时支持从Authorization头和URL查询参数中获取token"""
    # 延迟导入以避免循环导入
    from app.user import models, schemas
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No permission",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 1. 尝试从Authorization头获取token
    authorization = request.headers.get("Authorization")
    token = None
    
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    
    # 2. 如果Authorization头中没有token，尝试从URL查询参数获取
    if not token:
        token = request.query_params.get("token")
    
    # 3. 如果仍然没有token，抛出异常
    if not token:
        raise credentials_exception
    
    # 检查token是否在黑名单中
    if token in TOKEN_BLACKLIST:
        logger.info("Attempt to use revoked token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=str(username))
    except JWTError:
        raise credentials_exception
    
    # 检查 username 是否为 None
    if token_data.username is None:
        raise credentials_exception
        
    user = await get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(current_user = Depends(get_current_user)):
    """获取当前活跃用户"""
    # 延迟导入以避免循环导入
    from app.user import models
    
    # 检查用户是否是models.User实例
    if not isinstance(current_user, models.User):
        raise HTTPException(status_code=400, detail="Invalid user type")
    
    if not bool(current_user.is_active):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_user_from_token(token: str, db: AsyncSession, host_id: int):
    """从令牌获取当前用户（用于WebSocket连接）"""
    # 延迟导入以避免循环导入
    from app.user import models, schemas
    from app.host import service as host_service
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"开始验证令牌: {token}")
    
    # 首先验证令牌的有效性
    from app.host.websocket_terminal import TerminalManager
    terminal_manager = TerminalManager()
    if not await terminal_manager._validate_token(token, host_id):
        logger.warning("令牌验证失败")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 令牌验证成功，获取主机信息
    db_host = await host_service.get_host(db, host_id)
    if not db_host:
        logger.warning(f"找不到主机: {host_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 在这种情况下，我们无法直接从令牌中获取用户信息
    # 因为 HMAC 签名的令牌不包含用户信息
    # 我们需要通过其他方式获取当前用户
    # 这里我们返回 None，让调用者通过其他方式获取用户信息
    logger.info(f"令牌验证成功，host_id: {host_id}")
    return None


async def get_current_active_user_from_token(token: str, db: AsyncSession, host_id: int):
    """从令牌获取当前活跃用户（用于WebSocket连接）"""
    # 延迟导入以避免循环导入
    from app.user import models
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("开始验证用户活跃状态")
    
    # 验证令牌
    user = await get_current_user_from_token(token, db, host_id)
    
    # 在这种情况下，我们需要通过其他方式获取当前用户
    # 由于 HMAC 签名的令牌不包含用户信息，我们需要从请求上下文中获取
    # 但在 WebSocket 连接中，我们没有直接的请求上下文
    # 所以我们需要重新考虑认证方法
    
    # 为了保持向后兼容性，我们暂时返回 None
    # 实际的用户验证应该在 WebSocket 连接建立后进行
    logger.info("令牌验证成功，用户验证将在连接建立后进行")
    return None
