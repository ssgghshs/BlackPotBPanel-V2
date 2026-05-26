import os
import re
import time
import shutil
import sqlite3
import logging
from typing import List, Optional, Tuple, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete
from sqlalchemy.orm import Session as SyncSession

from app.database import models, schemas
from config.settings import settings

logger = logging.getLogger(__name__)

VALID_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
VALID_ORDER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*(\s+(ASC|DESC))?$', re.IGNORECASE)


def validate_identifier(name: str) -> bool:
    return bool(VALID_IDENTIFIER_PATTERN.match(name))


def validate_order_clause(order: str) -> bool:
    parts = order.split(',')
    for part in parts:
        if not VALID_ORDER_PATTERN.match(part.strip()):
            return False
    return True


async def get_databases(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[models.SqliteDatabase], int]:
    """获取 SQLite 数据库列表"""
    try:
        # 查询总数
        count_result = await db.execute(
            select(models.SqliteDatabase)
        )
        all_items = count_result.scalars().all()
        total = len(all_items)

        # 分页查询
        result = await db.execute(
            select(models.SqliteDatabase)
            .order_by(desc(models.SqliteDatabase.id))
            .offset(skip)
            .limit(limit)
        )
        items = result.scalars().all()

        # 更新文件信息
        for item in items:
            if os.path.exists(item.path):
                try:
                    stat = os.stat(item.path)
                    item._file_size = stat.st_size
                    item._file_exists = True
                except:
                    item._file_size = 0
                    item._file_exists = False
            else:
                item._file_size = 0
                item._file_exists = False

        return list(items), total
    except Exception as e:
        logger.error(f"获取数据库列表失败: {e}")
        return [], 0


async def get_database(
    db: AsyncSession,
    database_id: int
) -> Optional[models.SqliteDatabase]:
    """获取单个数据库"""
    try:
        result = await db.execute(
            select(models.SqliteDatabase).where(models.SqliteDatabase.id == database_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"获取数据库失败: {e}")
        return None


async def create_database(
    db: AsyncSession,
    database_in: schemas.SqliteDatabaseCreate
) -> Optional[models.SqliteDatabase]:
    """添加 SQLite 数据库"""
    try:
        # 检查路径是否存在
        if not os.path.exists(database_in.path):
            raise Exception("数据库文件不存在")

        # 检查是否为有效的 SQLite 文件
        if not _is_valid_sqlite_file(database_in.path):
            raise Exception("不是有效的 SQLite 数据库文件")

        # 检查是否已存在
        result = await db.execute(
            select(models.SqliteDatabase).where(models.SqliteDatabase.path == database_in.path)
        )
        if result.scalar_one_or_none():
            raise Exception("数据库已存在")

        # 创建记录
        db_item = models.SqliteDatabase(
            name=database_in.name,
            path=database_in.path,
            description=database_in.description
        )
        db.add(db_item)
        await db.commit()
        await db.refresh(db_item)

        return db_item
    except Exception as e:
        logger.error(f"添加数据库失败: {e}")
        await db.rollback()
        raise


async def update_database(
    db: AsyncSession,
    database_id: int,
    database_in: schemas.SqliteDatabaseUpdate
) -> Optional[models.SqliteDatabase]:
    """更新数据库信息"""
    try:
        db_item = await get_database(db, database_id)
        if not db_item:
            return None

        if database_in.name is not None:
            db_item.name = database_in.name
        if database_in.description is not None:
            db_item.description = database_in.description

        await db.commit()
        await db.refresh(db_item)

        return db_item
    except Exception as e:
        logger.error(f"更新数据库失败: {e}")
        await db.rollback()
        return None


async def delete_database(
    db: AsyncSession,
    database_id: int
) -> bool:
    """删除数据库（仅删除注册记录，不删除文件）"""
    try:
        db_item = await get_database(db, database_id)
        if not db_item:
            return False

        await db.delete(db_item)
        await db.commit()

        return True
    except Exception as e:
        logger.error(f"删除数据库失败: {e}")
        await db.rollback()
        return False


async def get_tables(
    db: AsyncSession,
    database_id: int
) -> List[schemas.SqliteTableInfo]:
    """获取数据库表列表"""
    try:
        db_item = await get_database(db, database_id)
        if not db_item:
            raise Exception("数据库不存在")

        if not os.path.exists(db_item.path):
            raise Exception("数据库文件不存在")

        # 使用 sqlite3 直接查询
        conn = sqlite3.connect(db_item.path)
        cursor = conn.cursor()

        # 获取表列表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()

        result = []
        for table in tables:
            table_name = table[0]
            # 获取记录数
            cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            count = cursor.fetchone()[0]
            result.append(schemas.SqliteTableInfo(name=table_name, count=count))

        conn.close()

        return result
    except Exception as e:
        logger.error(f"获取表列表失败: {e}")
        raise


async def get_table_columns(
    db: AsyncSession,
    database_id: int,
    table: str
) -> List[schemas.SqliteColumnInfo]:
    """获取表的列信息"""
    try:
        if not validate_identifier(table):
            raise Exception("无效的表名")

        db_item = await get_database(db, database_id)
        if not db_item:
            raise Exception("数据库不存在")

        conn = sqlite3.connect(db_item.path)
        cursor = conn.cursor()

        cursor.execute(f"PRAGMA table_info([{table}])")
        columns = cursor.fetchall()

        result = []
        for col in columns:
            result.append(schemas.SqliteColumnInfo(
                cid=col[0],
                name=col[1],
                type=col[2],
                notnull=col[3],
                default_value=col[4],
                pk=col[5]
            ))

        conn.close()

        return result
    except Exception as e:
        logger.error(f"获取列信息失败: {e}")
        raise


async def get_table_data(
    db: AsyncSession,
    database_id: int,
    table: str,
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
    order: Optional[str] = None
) -> schemas.SqliteTableDataResponse:
    """获取表数据"""
    try:
        if not validate_identifier(table):
            raise Exception("无效的表名")

        db_item = await get_database(db, database_id)
        if not db_item:
            raise Exception("数据库不存在")

        conn = sqlite3.connect(db_item.path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 获取列信息
        columns = await get_table_columns(db, database_id, table)

        # 构建查询 - 使用参数化查询防止 SQL 注入
        where_clause = ""
        params = []
        if search:
            conditions = []
            for col in columns:
                conditions.append(f"[{col.name}] LIKE ?")
                params.append(f"%{search}%")
            where_clause = f"WHERE {' OR '.join(conditions)}"

        order_clause = ""
        if order:
            if not validate_order_clause(order):
                raise Exception("无效的排序参数")
            order_clause = f"ORDER BY {order}"

        # 获取总数
        cursor.execute(f"SELECT COUNT(*) FROM [{table}] {where_clause}", params)
        total = cursor.fetchone()[0]

        # 分页查询
        offset = (page - 1) * page_size
        query_params = params + [page_size, offset]
        cursor.execute(f"SELECT * FROM [{table}] {where_clause} {order_clause} LIMIT ? OFFSET ?", query_params)
        rows = cursor.fetchall()

        data = []
        for row in rows:
            row_dict = dict(row)
            # 处理 bytes 类型
            for key, value in row_dict.items():
                if isinstance(value, (bytes, bytearray)):
                    row_dict[key] = str(value)
            data.append(row_dict)

        conn.close()

        return schemas.SqliteTableDataResponse(
            columns=columns,
            data=data,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"获取表数据失败: {e}")
        raise


async def execute_sql(
    db: AsyncSession,
    database_id: int,
    sql: str
) -> schemas.SqliteExecuteResponse:
    """执行 SQL 语句"""
    try:
        db_item = await get_database(db, database_id)
        if not db_item:
            raise Exception("数据库不存在")

        conn = sqlite3.connect(db_item.path)
        cursor = conn.cursor()

        cursor.execute(sql)
        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()

        return schemas.SqliteExecuteResponse(
            success=True,
            message="执行成功",
            affected_rows=affected_rows
        )
    except Exception as e:
        logger.error(f"执行 SQL 失败: {e}")
        return schemas.SqliteExecuteResponse(
            success=False,
            message=str(e)
        )


async def query_sql(
    db: AsyncSession,
    database_id: int,
    sql: str
) -> schemas.SqliteQueryResponse:
    """执行查询 SQL"""
    try:
        db_item = await get_database(db, database_id)
        if not db_item:
            raise Exception("数据库不存在")

        conn = sqlite3.connect(db_item.path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(sql)
        rows = cursor.fetchall()

        columns = [description[0] for description in cursor.description] if cursor.description else []
        data = [dict(row) for row in rows]

        conn.close()

        return schemas.SqliteQueryResponse(
            success=True,
            message="查询成功",
            columns=columns,
            data=data
        )
    except Exception as e:
        logger.error(f"查询 SQL 失败: {e}")
        return schemas.SqliteQueryResponse(
            success=False,
            message=str(e)
        )


async def create_table(
    db: AsyncSession,
    database_id: int,
    sql: str
) -> schemas.SqliteExecuteResponse:
    """创建表"""
    try:
        db_item = await get_database(db, database_id)
        if not db_item:
            raise Exception("数据库不存在")

        table_match = re.search(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\[`]?(\w+)[\]`]?", sql, re.IGNORECASE)
        if not table_match:
            raise Exception("无法从 SQL 语句中解析出表名")
        table = table_match.group(1)

        conn = sqlite3.connect(db_item.path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if cursor.fetchone():
            conn.close()
            return schemas.SqliteExecuteResponse(
                success=False,
                message=f"表 {table} 已存在"
            )

        cursor.execute(sql)
        conn.commit()
        conn.close()

        return schemas.SqliteExecuteResponse(
            success=True,
            message=f"表 {table} 创建成功"
        )
    except Exception as e:
        logger.error(f"创建表失败: {e}")
        return schemas.SqliteExecuteResponse(
            success=False,
            message=str(e)
        )


async def delete_table(
    db: AsyncSession,
    database_id: int,
    table: str
) -> schemas.SqliteExecuteResponse:
    """删除表"""
    try:
        db_item = await get_database(db, database_id)
        if not db_item:
            raise Exception("数据库不存在")

        conn = sqlite3.connect(db_item.path)
        cursor = conn.cursor()

        cursor.execute(f"DROP TABLE IF EXISTS [{table}]")
        conn.commit()
        conn.close()

        return schemas.SqliteExecuteResponse(
            success=True,
            message=f"表 {table} 删除成功"
        )
    except Exception as e:
        logger.error(f"删除表失败: {e}")
        return schemas.SqliteExecuteResponse(
            success=False,
            message=str(e)
        )


async def add_table_data(
    db: AsyncSession,
    database_id: int,
    table: str,
    data: dict
) -> schemas.SqliteExecuteResponse:
    """添加数据"""
    try:
        if not validate_identifier(table):
            raise Exception("无效的表名")
        for col_name in data.keys():
            if not validate_identifier(col_name):
                raise Exception(f"无效的列名: {col_name}")

        db_item = await get_database(db, database_id)
        if not db_item:
            raise Exception("数据库不存在")

        conn = sqlite3.connect(db_item.path)
        cursor = conn.cursor()

        columns = ', '.join([f'[{k}]' for k in data.keys()])
        placeholders = ', '.join(['?' for _ in data.values()])
        values = list(data.values())

        cursor.execute(f"INSERT INTO [{table}] ({columns}) VALUES ({placeholders})", values)
        conn.commit()
        conn.close()

        return schemas.SqliteExecuteResponse(
            success=True,
            message="添加数据成功",
            affected_rows=1
        )
    except Exception as e:
        logger.error(f"添加数据失败: {e}")
        return schemas.SqliteExecuteResponse(
            success=False,
            message=str(e)
        )


async def update_table_data(
    db: AsyncSession,
    database_id: int,
    table: str,
    where_data: dict,
    new_data: dict
) -> schemas.SqliteExecuteResponse:
    """更新数据"""
    try:
        if not validate_identifier(table):
            raise Exception("无效的表名")
        for col_name in list(where_data.keys()) + list(new_data.keys()):
            if not validate_identifier(col_name):
                raise Exception(f"无效的列名: {col_name}")

        db_item = await get_database(db, database_id)
        if not db_item:
            raise Exception("数据库不存在")

        conn = sqlite3.connect(db_item.path)
        cursor = conn.cursor()

        set_clause = ', '.join([f'[{k}]=?' for k in new_data.keys()])
        where_clause = ' AND '.join([f'[{k}]=?' for k in where_data.keys()])

        values = list(new_data.values()) + list(where_data.values())

        cursor.execute(f"UPDATE [{table}] SET {set_clause} WHERE {where_clause}", values)
        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()

        return schemas.SqliteExecuteResponse(
            success=True,
            message="更新数据成功",
            affected_rows=affected_rows
        )
    except Exception as e:
        logger.error(f"更新数据失败: {e}")
        return schemas.SqliteExecuteResponse(
            success=False,
            message=str(e)
        )


async def delete_table_data(
    db: AsyncSession,
    database_id: int,
    table: str,
    where_data: dict
) -> schemas.SqliteExecuteResponse:
    """删除数据"""
    try:
        if not validate_identifier(table):
            raise Exception("无效的表名")
        for col_name in where_data.keys():
            if not validate_identifier(col_name):
                raise Exception(f"无效的列名: {col_name}")

        db_item = await get_database(db, database_id)
        if not db_item:
            raise Exception("数据库不存在")

        conn = sqlite3.connect(db_item.path)
        cursor = conn.cursor()

        where_clause = ' AND '.join([f'[{k}]=?' for k in where_data.keys()])
        values = list(where_data.values())

        cursor.execute(f"DELETE FROM [{table}] WHERE {where_clause}", values)
        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()

        return schemas.SqliteExecuteResponse(
            success=True,
            message="删除数据成功",
            affected_rows=affected_rows
        )
    except Exception as e:
        logger.error(f"删除数据失败: {e}")
        return schemas.SqliteExecuteResponse(
            success=False,
            message=str(e)
        )


async def get_backups(
    db: AsyncSession,
    database_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> Tuple[List[models.SqliteBackup], int]:
    """获取备份列表"""
    try:
        query = select(models.SqliteBackup)
        if database_id:
            query = query.where(models.SqliteBackup.database_id == database_id)

        # 查询总数
        count_result = await db.execute(query)
        all_items = count_result.scalars().all()
        total = len(all_items)

        # 分页查询
        result = await db.execute(
            query.order_by(desc(models.SqliteBackup.id))
            .offset(skip)
            .limit(limit)
        )
        items = result.scalars().all()

        return list(items), total
    except Exception as e:
        logger.error(f"获取备份列表失败: {e}")
        return [], 0


async def create_backup(
    db: AsyncSession,
    database_id: int
) -> Optional[models.SqliteBackup]:
    """创建备份"""
    try:
        db_item = await get_database(db, database_id)
        if not db_item:
            raise Exception("数据库不存在")

        if not os.path.exists(db_item.path):
            raise Exception("数据库文件不存在")

        # 创建备份目录
        backup_dir = os.path.join(settings.BACKUP_PATH, "sqlite", str(database_id))
        os.makedirs(backup_dir, exist_ok=True)

        # 生成备份文件名
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        backup_filename = f"{timestamp}_{os.path.basename(db_item.path)}"
        backup_path = os.path.join(backup_dir, backup_filename)

        # 复制文件
        shutil.copy2(db_item.path, backup_path)

        # 获取文件大小
        file_size = os.path.getsize(backup_path)

        # 创建备份记录
        backup = models.SqliteBackup(
            database_id=database_id,
            database_name=db_item.name,
            backup_path=backup_path,
            file_size=file_size,
            status=1
        )
        db.add(backup)
        await db.commit()
        await db.refresh(backup)

        return backup
    except Exception as e:
        logger.error(f"创建备份失败: {e}")
        await db.rollback()
        raise


async def delete_backup(
    db: AsyncSession,
    backup_id: int
) -> bool:
    """删除备份"""
    try:
        result = await db.execute(
            select(models.SqliteBackup).where(models.SqliteBackup.id == backup_id)
        )
        backup = result.scalar_one_or_none()
        if not backup:
            return False

        # 删除备份文件
        if os.path.exists(backup.backup_path):
            os.remove(backup.backup_path)

        await db.delete(backup)
        await db.commit()

        return True
    except Exception as e:
        logger.error(f"删除备份失败: {e}")
        await db.rollback()
        return False


async def restore_backup(
    db: AsyncSession,
    backup_id: int
) -> bool:
    """恢复备份"""
    try:
        result = await db.execute(
            select(models.SqliteBackup).where(models.SqliteBackup.id == backup_id)
        )
        backup = result.scalar_one_or_none()
        if not backup:
            raise Exception("备份不存在")

        if not os.path.exists(backup.backup_path):
            raise Exception("备份文件不存在")

        db_item = await get_database(db, backup.database_id)
        if not db_item:
            raise Exception("数据库不存在")

        # 恢复备份
        shutil.copy2(backup.backup_path, db_item.path)

        return True
    except Exception as e:
        logger.error(f"恢复备份失败: {e}")
        raise


def _is_valid_sqlite_file(file_path: str) -> bool:
    """检查是否为有效的 SQLite 文件"""
    try:
        # 检查文件头
        with open(file_path, 'rb') as f:
            header = f.read(16)
            if header.startswith(b'SQLite format 3'):
                return True
        return False
    except:
        return False
