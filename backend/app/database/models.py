from sqlalchemy import Column, Integer, String, DateTime, Text, SmallInteger, UniqueConstraint
from config.database import DatabaseBase
from datetime import datetime
from config.settings import settings
import pytz


def get_localized_datetime():
    try:
        timezone_str = settings.TIMEZONE if hasattr(settings, 'TIMEZONE') else 'UTC'
        if timezone_str == 'UTC':
            tz = pytz.UTC
        else:
            tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        return now
    except Exception as e:
        print(f"时区配置错误，使用UTC: {e}")
        return datetime.now(pytz.UTC)


class SqliteDatabase(DatabaseBase):
    """SQLite 数据库注册表"""
    __tablename__ = "panel_sqlite_databases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, comment="数据库名称")
    path = Column(String(512), nullable=False, unique=True, comment="数据库文件路径")
    description = Column(String(256), nullable=True, comment="备注描述")
    created_at = Column(DateTime, default=get_localized_datetime)
    updated_at = Column(DateTime, default=get_localized_datetime, onupdate=get_localized_datetime)

    def __repr__(self):
        return f"<SqliteDatabase(id={self.id}, name='{self.name}', path='{self.path}')>"


class SqliteBackup(DatabaseBase):
    """SQLite 备份记录"""
    __tablename__ = "panel_sqlite_backups"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(Integer, nullable=False, comment="关联的数据库ID")
    database_name = Column(String(128), nullable=False, comment="数据库名称")
    backup_path = Column(String(512), nullable=False, comment="备份文件路径")
    file_size = Column(Integer, default=0, comment="备份文件大小(字节)")
    status = Column(SmallInteger, default=1, comment="1成功 0失败 2进行中")
    description = Column(String(256), nullable=True, comment="备注描述")
    created_at = Column(DateTime, default=get_localized_datetime)

    def __repr__(self):
        return f"<SqliteBackup(id={self.id}, database_name='{self.database_name}')>"


class MysqlServer(DatabaseBase):
    """MySQL 服务器连接配置"""
    __tablename__ = "panel_mysql_servers"
    __table_args__ = (
        UniqueConstraint('host', 'port', 'username', name='uq_mysql_server_connection'),
    )

    id = Column(Integer, primary_key=True, index=True)
    host = Column(String(256), nullable=False, comment="服务器地址")
    port = Column(Integer, default=3306, nullable=False, comment="端口")
    username = Column(String(128), nullable=False, comment="用户名")
    password = Column(String(512), nullable=False, comment="密码")
    description = Column(String(256), nullable=True, comment="备注描述")
    created_at = Column(DateTime, default=get_localized_datetime)
    updated_at = Column(DateTime, default=get_localized_datetime, onupdate=get_localized_datetime)

    def __repr__(self):
        return f"<MysqlServer(id={self.id}, host='{self.host}', port={self.port})>"


class MysqlBackup(DatabaseBase):
    """MySQL 备份记录"""
    __tablename__ = "panel_mysql_backups"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, nullable=False, comment="关联的服务器ID")
    database_name = Column(String(128), nullable=False, comment="数据库名称")
    backup_path = Column(String(512), nullable=False, comment="备份文件路径")
    file_size = Column(Integer, default=0, comment="备份文件大小(字节)")
    status = Column(SmallInteger, default=1, comment="1成功 0失败 2进行中")
    description = Column(String(256), nullable=True, comment="备注描述")
    created_at = Column(DateTime, default=get_localized_datetime)

    def __repr__(self):
        return f"<MysqlBackup(id={self.id}, database_name='{self.database_name}')>"


class PostgresqlServer(DatabaseBase):
    """PostgreSQL 服务器连接配置"""
    __tablename__ = "panel_postgresql_servers"
    __table_args__ = (
        UniqueConstraint('host', 'port', 'username', name='uq_pgsql_server_connection'),
    )

    id = Column(Integer, primary_key=True, index=True)
    host = Column(String(256), nullable=False, comment="服务器地址")
    port = Column(Integer, default=5432, nullable=False, comment="端口")
    username = Column(String(128), nullable=False, comment="用户名")
    password = Column(String(512), nullable=False, comment="密码")
    description = Column(String(256), nullable=True, comment="备注描述")
    created_at = Column(DateTime, default=get_localized_datetime)
    updated_at = Column(DateTime, default=get_localized_datetime, onupdate=get_localized_datetime)

    def __repr__(self):
        return f"<PostgresqlServer(id={self.id}, host='{self.host}', port={self.port})>"


class PostgresqlBackup(DatabaseBase):
    """PostgreSQL 备份记录"""
    __tablename__ = "panel_postgresql_backups"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, nullable=False, comment="关联的服务器ID")
    database_name = Column(String(128), nullable=False, comment="数据库名称")
    backup_path = Column(String(512), nullable=False, comment="备份文件路径")
    file_size = Column(Integer, default=0, comment="备份文件大小(字节)")
    status = Column(SmallInteger, default=1, comment="1成功 0失败 2进行中")
    description = Column(String(256), nullable=True, comment="备注描述")
    created_at = Column(DateTime, default=get_localized_datetime)

    def __repr__(self):
        return f"<PostgresqlBackup(id={self.id}, database_name='{self.database_name}')>"
