from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import settings
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# 创建主数据库引擎
engine = create_async_engine(
    settings.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///"),
    connect_args={"check_same_thread": False}  # 仅适用于SQLite
)

# 创建脚本数据库引擎
script_engine = create_async_engine(
    settings.SCRIPT_DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///"),
    connect_args={"check_same_thread": False}  # 仅适用于SQLite
)

# 创建容器数据库引擎
container_engine = create_async_engine(
    settings.CONTAINER_DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///"),
    connect_args={"check_same_thread": False}  # 仅适用于SQLite
)

# 创建防火墙数据库引擎
firewall_engine = create_async_engine(
    settings.FIREWALL_DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///"),
    connect_args={"check_same_thread": False}  # 仅适用于SQLite
)

# 创建WAF数据库引擎
waf_engine = create_async_engine(
    settings.WAF_DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///"),
    connect_args={"check_same_thread": False}  # 仅适用于SQLite
)

# 创建Cronab数据库引擎
crontab_engine = create_async_engine(
    settings.CRONAB_DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///"),
    connect_args={"check_same_thread": False}  # 仅适用于SQLite
)

# 创建数据库数据库引擎
database_engine = create_async_engine(
    settings.DATABASE_DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///"),
    connect_args={"check_same_thread": False}  # 仅适用于SQLite
)

# 创建主数据库异步会话工厂
AsyncSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine, 
    class_=AsyncSession
)

# 创建脚本数据库异步会话工厂
ScriptAsyncSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=script_engine, 
    class_=AsyncSession
)

# 创建容器数据库异步会话工厂
ContainerAsyncSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=container_engine, 
    class_=AsyncSession
)

# 创建防火墙数据库异步会话工厂
FirewallAsyncSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=firewall_engine, 
    class_=AsyncSession
)

# 创建WAF数据库异步会话工厂
WafAsyncSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=waf_engine, 
    class_=AsyncSession
)

# 创建Cronab数据库异步会话工厂
CrontabAsyncSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=crontab_engine, 
    class_=AsyncSession
)

# 创建数据库数据库异步会话工厂
DatabaseAsyncSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=database_engine, 
    class_=AsyncSession
)

# 创建主数据库基础模型类
Base = declarative_base()

# 创建脚本数据库基础模型类
ScriptBase = declarative_base()

# 创建容器数据库基础模型类
ContainerBase = declarative_base()

# 创建防火墙数据库基础模型类
FirewallBase = declarative_base()

# 创建WAF数据库基础模型类
WafBase = declarative_base()

# 创建Cronab数据库基础模型类
CrontabTaskBase = declarative_base()

# 创建数据库数据库基础模型类
DatabaseBase = declarative_base()



async def get_db():
    """获取主数据库异步会话"""
    async with AsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def get_script_db():
    """获取脚本数据库异步会话"""
    async with ScriptAsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def get_container_db():
    """获取容器数据库异步会话"""
    async with ContainerAsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def get_firewall_db():
    """获取防火墙数据库异步会话"""
    async with FirewallAsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def get_waf_db():
    """获取WAF数据库异步会话"""
    async with WafAsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise
            
async def get_crontab_db():
    """获取Cronab数据库异步会话"""
    async with CrontabAsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise

async def get_database_db():
    """获取数据库数据库异步会话"""
    async with DatabaseAsyncSessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise