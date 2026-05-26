from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.log import models, schemas

async def create_login_log(db: AsyncSession, login_log: schemas.LoginLogCreate):
    """创建登录日志"""
    db_login_log = models.LoginLog(**login_log.dict())
    db.add(db_login_log)
    await db.commit()
    await db.refresh(db_login_log)
    return db_login_log

async def get_login_logs(db: AsyncSession, skip: int = 0, limit: int = 100):
    """获取登录日志列表，按登录时间倒序排列（最新在前）"""
    result = await db.execute(
        select(models.LoginLog)
        .order_by(models.LoginLog.login_time.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def get_user_login_logs(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    """获取特定用户的登录日志，按登录时间倒序排列（最新在前）"""
    result = await db.execute(
        select(models.LoginLog)
        .filter(models.LoginLog.user_id == user_id)
        .order_by(models.LoginLog.login_time.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


# 访问日志相关服务函数
async def create_access_log(db: AsyncSession, access_log: schemas.AccessLogCreate):
    """创建访问日志配置"""
    db_access_log = models.AccessLog(
        access_log_path=access_log.access_log_path,
        error_log_path=access_log.error_log_path
    )
    db.add(db_access_log)
    await db.commit()
    await db.refresh(db_access_log)
    return db_access_log

async def get_access_logs(db: AsyncSession, skip: int = 0, limit: int = 100):
    """获取访问日志配置列表"""
    result = await db.execute(
        select(models.AccessLog)
        .order_by(models.AccessLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def get_latest_access_log(db: AsyncSession):
    """获取最新的访问日志配置"""
    result = await db.execute(
        select(models.AccessLog)
        .order_by(models.AccessLog.created_at.desc())
        .limit(1)
    )
    return result.scalars().first()