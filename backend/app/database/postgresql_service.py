import os
import re
import asyncio
import logging
from typing import List, Optional, Tuple, Any
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import models, schemas
from config.settings import settings

logger = logging.getLogger(__name__)


def get_pgsql_connection(host: str, port: int, username: str, password: str, database: str = None):
    """创建 PostgreSQL 连接"""
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            dbname=database or 'postgres',
            connect_timeout=10
        )
        return conn
    except Exception as e:
        logger.error(f"PostgreSQL 连接失败: {e}")
        raise


async def test_connection(host: str, port: int, username: str, password: str) -> dict:
    """测试 PostgreSQL 连接（异步安全，支持超时）"""
    try:
        conn = await asyncio.wait_for(
            asyncio.to_thread(
                get_pgsql_connection,
                host, port, username, password
            ),
            timeout=15
        )
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        conn.close()
        return {
            "success": True,
            "message": "连接成功",
            "version": version[0] if version else 'Unknown'
        }
    except asyncio.TimeoutError:
        error_msg = f"连接超时（15秒）"
        logger.error(f"PostgreSQL 连接超时: {host}:{port}")
        return {"success": False, "message": error_msg}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}


# ==================== 服务器管理 ====================

async def get_servers(db: AsyncSession, skip: int = 0, limit: int = 100) -> Tuple[List[models.PostgresqlServer], int]:
    """获取 PostgreSQL 服务器列表"""
    result = await db.execute(
        select(models.PostgresqlServer)
        .order_by(desc(models.PostgresqlServer.id))
        .offset(skip)
        .limit(limit)
    )
    items = result.scalars().all()
    total_result = await db.execute(select(models.PostgresqlServer))
    total = len(total_result.scalars().all())
    return items, total


async def get_server(db: AsyncSession, server_id: int) -> Optional[models.PostgresqlServer]:
    """获取单个服务器"""
    result = await db.execute(
        select(models.PostgresqlServer).where(models.PostgresqlServer.id == server_id)
    )
    return result.scalar_one_or_none()


async def create_server(db: AsyncSession, data: schemas.PostgresqlServerCreate) -> models.PostgresqlServer:
    """添加 PostgreSQL 服务器"""
    result = await db.execute(
        select(models.PostgresqlServer).where(
            models.PostgresqlServer.host == data.host,
            models.PostgresqlServer.port == data.port,
            models.PostgresqlServer.username == data.username
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise Exception("具有相同设置的服务器连接已存在")

    test_result = await test_connection(data.host, data.port, data.username, data.password)
    if not test_result["success"]:
        raise Exception(test_result["message"])

    db_server = models.PostgresqlServer(
        host=data.host,
        port=data.port,
        username=data.username,
        password=data.password,
        description=data.description
    )
    db.add(db_server)
    await db.commit()
    await db.refresh(db_server)
    return db_server


async def update_server(db: AsyncSession, server_id: int, data: schemas.PostgresqlServerUpdate) -> Optional[models.PostgresqlServer]:
    """更新 PostgreSQL 服务器"""
    db_server = await get_server(db, server_id)
    if not db_server:
        return None

    update_data = data.dict(exclude_unset=True)

    if any(k in update_data for k in ['host', 'port', 'username', 'password']):
        host = update_data.get('host', db_server.host)
        port = update_data.get('port', db_server.port)
        username = update_data.get('username', db_server.username)
        password = update_data.get('password', db_server.password)
        test_result = await test_connection(host, port, username, password)
        if not test_result["success"]:
            raise Exception(test_result["message"])

    for key, value in update_data.items():
        setattr(db_server, key, value)

    await db.commit()
    await db.refresh(db_server)
    return db_server


async def delete_server(db: AsyncSession, server_id: int) -> bool:
    """删除 PostgreSQL 服务器"""
    db_server = await get_server(db, server_id)
    if not db_server:
        return False
    await db.delete(db_server)
    await db.commit()
    return True


# ==================== 数据库管理 ====================

async def get_databases(server_id: int, db: AsyncSession) -> List[str]:
    """获取数据库列表"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password)
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT datname FROM pg_database
            WHERE datistemplate = false
              AND has_database_privilege(datname, 'CONNECT')
            ORDER BY datname
        """)
        rows = cursor.fetchall()
        return [row['datname'] for row in rows]
    finally:
        conn.close()


async def create_database(server_id: int, data: schemas.PostgresqlCreateDatabaseRequest, db: AsyncSession) -> dict:
    """创建数据库"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password)
    try:
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(f'CREATE DATABASE "{data.name}"')
        return {"success": True, "message": f"数据库 {data.name} 创建成功"}
    except Exception as e:
        return {"success": False, "message": f"创建失败: {str(e)}"}
    finally:
        conn.close()


async def delete_database(server_id: int, database_name: str, db: AsyncSession) -> dict:
    """删除数据库"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password)
    try:
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
        return {"success": True, "message": f"数据库 {database_name} 删除成功"}
    except Exception as e:
        return {"success": False, "message": f"删除失败: {str(e)}"}
    finally:
        conn.close()


# ==================== 表管理 ====================

async def get_tables(server_id: int, database_name: str, db: AsyncSession) -> List[dict]:
    """获取表列表"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT tablename as name,
                   COALESCE(n_live_tup, 0) as rows,
                   pg_size_pretty(pg_total_relation_size(pg_tables.schemaname || '.' || tablename)) as size
            FROM pg_catalog.pg_tables
            LEFT JOIN pg_catalog.pg_stat_user_tables ON tablename = relname AND pg_tables.schemaname = pg_stat_user_tables.schemaname
            WHERE pg_tables.schemaname = 'public'
            ORDER BY tablename
        """)
        return cursor.fetchall()
    finally:
        conn.close()


async def create_table(server_id: int, database_name: str, sql: str, db: AsyncSession) -> dict:
    """创建表"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        return {"success": True, "message": "表创建成功"}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


async def delete_table(server_id: int, database_name: str, table_name: str, db: AsyncSession) -> dict:
    """删除表"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor()
        cursor.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        conn.commit()
        return {"success": True, "message": "表删除成功"}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


async def get_table_columns(server_id: int, database_name: str, table_name: str, db: AsyncSession) -> List[dict]:
    """获取表列信息"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT c.column_name, c.data_type, c.is_nullable, c.column_default,
                   COALESCE(pk.is_primary, '') as key
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT kcu.column_name, 'PRI' as is_primary
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                WHERE tc.table_name = %s
                    AND tc.table_schema = 'public'
                    AND tc.constraint_type = 'PRIMARY KEY'
            ) pk ON pk.column_name = c.column_name
            WHERE c.table_name = %s AND c.table_schema = 'public'
            ORDER BY c.ordinal_position
        """, (table_name, table_name))
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                'field': row['column_name'],
                'type': row['data_type'],
                'null': row['is_nullable'],
                'key': row['key'],
                'default': row['column_default'],
                'extra': ''
            })
        return result
    finally:
        conn.close()


async def get_table_data(
    server_id: int, database_name: str, table_name: str,
    page: int = 1, page_size: int = 50,
    search: Optional[str] = None, order: Optional[str] = None,
    db: AsyncSession = None
) -> dict:
    """获取表数据"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        columns_info = await get_table_columns(server_id, database_name, table_name, db)
        columns = [col['field'] for col in columns_info] if columns_info else []

        where_clause = ""
        params = []
        if search and columns:
            conditions = [f'"{col}"::text ILIKE %s' for col in columns]
            params = [f"%{search}%"] * len(columns)
            where_clause = f"WHERE {' OR '.join(conditions)}"

        order_clause = ""
        if order:
            safe_order = re.sub(r'[^a-zA-Z0-9_\s,.]', '', order)
            if safe_order:
                order_clause = f"ORDER BY {safe_order}"

        try:
            cursor.execute(f'SELECT COUNT(*) as total FROM "{table_name}" {where_clause}', params)
            total = cursor.fetchone()['total']
        except Exception as e:
            error_msg = str(e)
            if 'permission denied' in error_msg.lower():
                return {
                    "columns": columns,
                    "data": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "error": f"No permission to access table: {table_name}"
                }
            raise

        offset = (page - 1) * page_size
        query_params = params + [page_size, offset]
        cursor.execute(
            f'SELECT * FROM "{table_name}" {where_clause} {order_clause} LIMIT %s OFFSET %s',
            query_params
        )
        rows = cursor.fetchall()

        data = []
        for row in rows:
            row_dict = {}
            for key, value in row.items():
                if isinstance(value, datetime):
                    row_dict[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(value, (bytes, bytearray)):
                    row_dict[key] = str(value)
                else:
                    row_dict[key] = value
            data.append(row_dict)

        return {
            "columns": columns,
            "data": data,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    finally:
        conn.close()


# ==================== SQL 执行 ====================

async def execute_sql(server_id: int, database_name: str, sql: str, db: AsyncSession) -> dict:
    """执行 SQL 语句"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(sql)
        conn.commit()

        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            data = []
            for row in rows:
                row_dict = {}
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row_dict[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, (bytes, bytearray)):
                        row_dict[key] = str(value)
                    else:
                        row_dict[key] = value
                data.append(row_dict)
            return {
                "success": True,
                "message": f"执行成功，返回 {len(data)} 行",
                "columns": columns,
                "data": data,
                "affected_rows": cursor.rowcount
            }

        return {
            "success": True,
            "message": f"执行成功，影响 {cursor.rowcount} 行",
            "affected_rows": cursor.rowcount
        }
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


async def query_sql(server_id: int, database_name: str, sql: str, db: AsyncSession) -> dict:
    """执行查询 SQL"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(sql)
        rows = cursor.fetchall()

        columns = []
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]

        data = []
        for row in rows:
            row_dict = {}
            for key, value in row.items():
                if isinstance(value, datetime):
                    row_dict[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(value, (bytes, bytearray)):
                    row_dict[key] = str(value)
                else:
                    row_dict[key] = value
            data.append(row_dict)

        return {"success": True, "message": "查询成功", "columns": columns, "data": data}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


# ==================== 数据操作 ====================

async def add_data(server_id: int, database_name: str, table_name: str, data: dict, db: AsyncSession) -> dict:
    """添加数据"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor()
        columns = ', '.join([f'"{k}"' for k in data.keys()])
        placeholders = ', '.join(['%s' for _ in data.values()])
        values = list(data.values())

        cursor.execute(f'INSERT INTO "{table_name}" ({columns}) VALUES ({placeholders})', values)
        conn.commit()
        return {"success": True, "message": "添加成功", "affected_rows": 1}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


async def update_data(server_id: int, database_name: str, table_name: str, where_data: dict, new_data: dict, db: AsyncSession) -> dict:
    """更新数据"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor()
        set_clause = ', '.join([f'"{k}"=%s' for k in new_data.keys()])
        where_clause = ' AND '.join([f'"{k}"=%s' for k in where_data.keys()])
        values = list(new_data.values()) + list(where_data.values())

        cursor.execute(f'UPDATE "{table_name}" SET {set_clause} WHERE {where_clause}', values)
        conn.commit()
        return {"success": True, "message": "更新成功", "affected_rows": cursor.rowcount}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


async def delete_data(server_id: int, database_name: str, table_name: str, where_data: dict, db: AsyncSession) -> dict:
    """删除数据"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor()
        where_clause = ' AND '.join([f'"{k}"=%s' for k in where_data.keys()])
        values = list(where_data.values())

        cursor.execute(f'DELETE FROM "{table_name}" WHERE {where_clause}', values)
        conn.commit()
        return {"success": True, "message": "删除成功", "affected_rows": cursor.rowcount}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


# ==================== 用户管理 ====================

async def get_users(server_id: int, db: AsyncSession) -> List[dict]:
    """获取 PostgreSQL 用户列表"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password)
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT rolname as username, rolcanlogin as can_login,
                   rolsuper as is_superuser, rolcreatedb as can_create_db
            FROM pg_catalog.pg_roles
            WHERE rolname NOT LIKE 'pg_%' AND rolname != 'postgres'
            ORDER BY rolname
        """)
        return cursor.fetchall()
    finally:
        conn.close()


async def create_user(server_id: int, data: schemas.PostgresqlCreateUserRequest, db: AsyncSession) -> dict:
    """创建 PostgreSQL 用户"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password)
    try:
        cursor = conn.cursor()
        cursor.execute(f'CREATE ROLE "{data.username}" WITH LOGIN PASSWORD %s', (data.password,))
        conn.commit()
        return {"success": True, "message": f"用户 {data.username} 创建成功"}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


async def delete_user(server_id: int, data: schemas.PostgresqlDeleteUserRequest, db: AsyncSession) -> dict:
    """删除 PostgreSQL 用户"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password)
    try:
        cursor = conn.cursor()
        cursor.execute(f'REASSIGN OWNED BY "{data.username}" TO postgres')
        cursor.execute(f'DROP OWNED BY "{data.username}"')
        cursor.execute(f'DROP ROLE IF EXISTS "{data.username}"')
        conn.commit()
        return {"success": True, "message": f"用户 {data.username} 删除成功"}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


async def alter_user(server_id: int, data: schemas.PostgresqlAlterUserRequest, db: AsyncSession) -> dict:
    """修改 PostgreSQL 用户"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password)
    try:
        cursor = conn.cursor()
        if data.new_password:
            cursor.execute(f'ALTER ROLE "{data.username}" WITH PASSWORD %s', (data.new_password,))
        if data.new_username and data.new_username != data.username:
            cursor.execute(f'ALTER ROLE "{data.username}" RENAME TO "{data.new_username}"')
        conn.commit()
        return {"success": True, "message": "用户修改成功"}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


async def grant_privileges(server_id: int, data: schemas.PostgresqlGrantRequest, db: AsyncSession) -> dict:
    """授予 PostgreSQL 用户权限"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password)
    try:
        cursor = conn.cursor()

        db_level_privileges = ['ALL', 'ALL PRIVILEGES', 'CREATE', 'CONNECT', 'TEMP', 'TEMPORARY']
        db_privs = [p for p in data.privileges if p.upper() in db_level_privileges]
        table_privs = [p for p in data.privileges if p.upper() not in db_level_privileges]

        priv_str = ', '.join(data.privileges)

        if data.database_name == '*':
            if table_privs:
                cursor.execute(f'GRANT {", ".join(table_privs)} ON ALL TABLES IN SCHEMA public TO "{data.username}"')
        else:
            if db_privs:
                cursor.execute(f'GRANT {", ".join(db_privs)} ON DATABASE "{data.database_name}" TO "{data.username}"')
            if table_privs:
                cursor.execute(f'GRANT {", ".join(table_privs)} ON ALL TABLES IN SCHEMA public TO "{data.username}"')

        conn.commit()
        return {"success": True, "message": f"权限授予成功"}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


# ==================== 备份管理 ====================

async def get_backups(db: AsyncSession, server_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> Tuple[List[models.PostgresqlBackup], int]:
    """获取备份列表"""
    query = select(models.PostgresqlBackup)
    if server_id:
        query = query.where(models.PostgresqlBackup.server_id == server_id)

    query = query.order_by(desc(models.PostgresqlBackup.id)).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    count_query = select(models.PostgresqlBackup)
    if server_id:
        count_query = count_query.where(models.PostgresqlBackup.server_id == server_id)
    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())

    return items, total


async def create_backup(server_id: int, database_name: str, db: AsyncSession) -> models.PostgresqlBackup:
    """创建备份（纯 Python 实现，无需 pg_dump）"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    backup_dir = os.path.join(settings.BACKUP_PATH, "postgresql", str(server_id), database_name)
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{database_name}_{timestamp}.sql"
    backup_path = os.path.join(backup_dir, backup_filename)

    try:
        conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(f"-- PostgreSQL backup: {database_name}\n")
            f.write(f"-- Time: {timestamp}\n")
            f.write(f"-- Generated by BlackPotBPanel\n\n")

            f.write(f"SET statement_timeout = 0;\n")
            f.write(f"SET lock_timeout = 0;\n")
            f.write(f"SET client_encoding = 'UTF8';\n\n")

            # 1. 获取所有表
            cursor.execute("""
                SELECT tablename FROM pg_catalog.pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)
            tables = [row['tablename'] for row in cursor.fetchall()]

            if not tables:
                f.write("-- No tables found\n")

            for table_name in tables:
                f.write(f"\n--\n-- Table structure for {table_name}\n--\n\n")

                # 1a. 获取 CREATE TABLE DDL
                cursor.execute("""
                    SELECT column_name, data_type, character_maximum_length,
                           is_nullable, column_default, ordinal_position
                    FROM information_schema.columns
                    WHERE table_name = %s AND table_schema = 'public'
                    ORDER BY ordinal_position
                """, (table_name,))
                columns = cursor.fetchall()

                # 获取主键
                cursor.execute("""
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    WHERE tc.table_name = %s
                        AND tc.table_schema = 'public'
                        AND tc.constraint_type = 'PRIMARY KEY'
                    ORDER BY kcu.ordinal_position
                """, (table_name,))
                pk_cols = [row['column_name'] for row in cursor.fetchall()]

                # 生成 CREATE TABLE
                col_defs = []
                for col in columns:
                    col_def = f'    "{col["column_name"]}" {col["data_type"]}'
                    if col["data_type"] in ('character varying', 'varchar') and col["character_maximum_length"]:
                        col_def = f'    "{col["column_name"]}" varchar({col["character_maximum_length"]})'
                    if col["is_nullable"] == 'NO':
                        col_def += ' NOT NULL'
                    if col["column_default"]:
                        col_def += f' DEFAULT {col["column_default"]}'
                    col_defs.append(col_def)

                if pk_cols:
                    col_defs.append(f'    PRIMARY KEY ({", ".join(pk_cols)})')

                f.write(f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n')
                f.write(',\n'.join(col_defs))
                f.write('\n);\n\n')

                # 获取所有序列（serial 类型），导出当前值
                cursor.execute("""
                    SELECT pg_get_serial_sequence('"' || %s || '"', column_name) as seq_name,
                           column_name
                    FROM information_schema.columns
                    WHERE table_name = %s AND table_schema = 'public'
                      AND column_default LIKE 'nextval%%'
                """, (table_name, table_name))
                seq_rows = cursor.fetchall()
                for sr in seq_rows:
                    if sr['seq_name']:
                        try:
                            cursor.execute("SELECT pg_catalog.currval(%s) as currval", (sr['seq_name'],))
                            cv = cursor.fetchone()
                            if cv and cv['currval'] is not None:
                                f.write(f"SELECT pg_catalog.setval('{sr['seq_name']}', {cv['currval']}, true);\n")
                        except Exception:
                            pass

                # 2. 导出数据（INSERT 语句）
                cursor.execute(f'SELECT * FROM "{table_name}"')
                data_rows = cursor.fetchall()
                if data_rows:
                    data_cols = list(data_rows[0].keys())
                    safe_cols = [f'"{c}"' for c in data_cols]
                    f.write(f'-- Data for {table_name}\n')

                    for row in data_rows:
                        values = []
                        for c in data_cols:
                            val = row[c]
                            if val is None:
                                values.append('NULL')
                            elif isinstance(val, bool):
                                values.append('TRUE' if val else 'FALSE')
                            elif isinstance(val, (int, float)):
                                values.append(str(val))
                            elif isinstance(val, datetime):
                                values.append(f"'{val.isoformat()}'")
                            elif isinstance(val, (bytes, bytearray)):
                                escape_val = val.decode('utf-8', errors='replace').replace("'", "''")
                                values.append(f"E'{escape_val}'")
                            else:
                                escape_val = str(val).replace("'", "''")
                                values.append(f"'{escape_val}'")
                        f.write(f'INSERT INTO "{table_name}" ({", ".join(safe_cols)}) VALUES ({", ".join(values)});\n')

                # 3. 索引
                cursor.execute("""
                    SELECT indexdef FROM pg_catalog.pg_indexes
                    WHERE tablename = %s AND schemaname = 'public'
                """, (table_name,))
                for idx_row in cursor.fetchall():
                    f.write(f"{idx_row['indexdef']};\n")

            f.write("\n-- Backup complete\n")

        conn.close()

        file_size = os.path.getsize(backup_path)

        db_backup = models.PostgresqlBackup(
            server_id=server_id,
            database_name=database_name,
            backup_path=backup_path,
            file_size=file_size,
            status=1,
            description=f"手动备份 {timestamp}"
        )
        db.add(db_backup)
        await db.commit()
        await db.refresh(db_backup)
        return db_backup

    except Exception as e:
        if os.path.exists(backup_path):
            os.remove(backup_path)
        raise Exception(f"备份失败: {str(e)}")


async def restore_backup(backup_id: int, db: AsyncSession) -> bool:
    """恢复备份（纯 Python 实现，无需 psql）"""
    result = await db.execute(
        select(models.PostgresqlBackup).where(models.PostgresqlBackup.id == backup_id)
    )
    backup = result.scalar_one_or_none()
    if not backup:
        raise Exception("备份不存在")

    if not os.path.exists(backup.backup_path):
        raise Exception("备份文件不存在")

    db_server = await get_server(db, backup.server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = None
    try:
        conn = get_pgsql_connection(db_server.host, db_server.port, db_server.username, db_server.password, backup.database_name)
        cursor = conn.cursor()

        with open(backup.backup_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # 按分号分割 SQL 语句，逐条执行
        statements = []
        current_stmt = []
        in_dollar_tag = False
        dollar_tag = None

        for line in sql_content.split('\n'):
            stripped = line.strip()

            if not stripped or stripped.startswith('--'):
                continue

            if stripped.startswith('SET '):
                continue

            # 检测美元符号引用的开始/结束
            if not in_dollar_tag:
                import re as _re
                m = _re.match(r'^\$\$', stripped)
                if m:
                    in_dollar_tag = True
                else:
                    m = _re.match(r'^\$(\w*)\$', stripped)
                    if m:
                        in_dollar_tag = True
                        dollar_tag = m.group(1)
            else:
                if dollar_tag:
                    if f'${dollar_tag}$' in stripped:
                        in_dollar_tag = False
                        dollar_tag = None
                elif '$$' in stripped:
                    in_dollar_tag = False

            current_stmt.append(line)

            if not in_dollar_tag and ';' in line:
                stmt = ' '.join(current_stmt).strip()
                if stmt:
                    statements.append(stmt)
                current_stmt = []

        if current_stmt:
            stmt = ' '.join(current_stmt).strip()
            if stmt:
                statements.append(stmt)

        conn.autocommit = False

        for stmt in statements:
            try:
                cursor.execute(stmt)
                conn.commit()
            except Exception as stmt_err:
                conn.rollback()
                logger.warning(f"恢复时跳过语句: {stmt_err}. SQL: {stmt[:200]}")

        return True

    except Exception as e:
        if conn:
            conn.rollback()
        raise Exception(f"恢复失败: {str(e)}")
    finally:
        if conn:
            conn.close()


async def delete_backup(db: AsyncSession, backup_id: int) -> bool:
    """删除备份"""
    result = await db.execute(
        select(models.PostgresqlBackup).where(models.PostgresqlBackup.id == backup_id)
    )
    backup = result.scalar_one_or_none()
    if not backup:
        return False

    if os.path.exists(backup.backup_path):
        os.remove(backup.backup_path)

    await db.delete(backup)
    await db.commit()
    return True
