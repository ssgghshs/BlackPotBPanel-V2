import os
import re
import time
import asyncio
import shutil
import logging
from typing import List, Optional, Tuple, Any
from datetime import datetime

import pymysql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import models, schemas
from config.settings import settings

logger = logging.getLogger(__name__)


def get_mysql_connection(host: str, port: int, username: str, password: str, database: str = None):
    """创建 MySQL 连接"""
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10
        )
        return conn
    except Exception as e:
        logger.error(f"MySQL 连接失败: {e}")
        raise


async def test_connection(host: str, port: int, username: str, password: str) -> dict:
    """测试 MySQL 连接（异步安全，支持超时）"""
    try:
        conn = await asyncio.wait_for(
            asyncio.to_thread(
                get_mysql_connection,
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
            "version": version.get('VERSION()', 'Unknown') if version else 'Unknown'
        }
    except asyncio.TimeoutError:
        error_msg = f"连接超时（15秒）"
        logger.error(f"MySQL 连接超时: {host}:{port}")
        return {
            "success": False,
            "message": error_msg
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"连接失败: {str(e)}"
        }


# ==================== 服务器管理 ====================

async def get_servers(db: AsyncSession, skip: int = 0, limit: int = 100) -> Tuple[List[models.MysqlServer], int]:
    """获取 MySQL 服务器列表"""
    result = await db.execute(
        select(models.MysqlServer)
        .order_by(desc(models.MysqlServer.id))
        .offset(skip)
        .limit(limit)
    )
    items = result.scalars().all()
    total_result = await db.execute(select(models.MysqlServer))
    total = len(total_result.scalars().all())
    return items, total


async def get_server(db: AsyncSession, server_id: int) -> Optional[models.MysqlServer]:
    """获取单个服务器"""
    result = await db.execute(
        select(models.MysqlServer).where(models.MysqlServer.id == server_id)
    )
    return result.scalar_one_or_none()


async def create_server(db: AsyncSession, data: schemas.MysqlServerCreate) -> models.MysqlServer:
    """添加 MySQL 服务器"""
    # 检查是否已存在相同连接
    result = await db.execute(
        select(models.MysqlServer).where(
            models.MysqlServer.host == data.host,
            models.MysqlServer.port == data.port,
            models.MysqlServer.username == data.username
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise Exception(f"A server connection with the same settings already exists")

    test_result = await test_connection(data.host, data.port, data.username, data.password)
    if not test_result["success"]:
        raise Exception(test_result["message"])

    db_server = models.MysqlServer(
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


async def update_server(db: AsyncSession, server_id: int, data: schemas.MysqlServerUpdate) -> Optional[models.MysqlServer]:
    """更新 MySQL 服务器"""
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
    """删除 MySQL 服务器"""
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

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password)
    try:
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        result = cursor.fetchall()
        databases = [row['Database'] for row in result if row['Database'] not in ['information_schema', 'performance_schema', 'sys']]
        return databases
    finally:
        conn.close()


async def create_database(server_id: int, data: schemas.MysqlCreateDatabaseRequest, db: AsyncSession) -> dict:
    """创建数据库"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password)
    try:
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE `{data.name}` CHARACTER SET {data.charset}")
        conn.commit()
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

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password)
    try:
        cursor = conn.cursor()
        cursor.execute(f"DROP DATABASE `{database_name}`")
        conn.commit()
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

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TABLE_NAME as name, TABLE_ROWS as `rows`, ENGINE as engine,
                   ROUND(DATA_LENGTH + INDEX_LENGTH) as size
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_NAME
        """, (database_name,))
        return cursor.fetchall()
    finally:
        conn.close()


async def create_table(server_id: int, database_name: str, sql: str, db: AsyncSession) -> dict:
    """创建表"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
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

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor()
        cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
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

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor()
        cursor.execute(f"SHOW FULL COLUMNS FROM `{table_name}`")
        columns = cursor.fetchall()
        result = []
        for col in columns:
            result.append({
                "field": col.get('Field', ''),
                "type": col.get('Type', ''),
                "null": col.get('Null', ''),
                "key": col.get('Key', ''),
                "default": col.get('Default', None),
                "extra": col.get('Extra', '')
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

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor()

        columns_info = await get_table_columns(server_id, database_name, table_name, db)
        columns = [col['field'] for col in columns_info] if columns_info else []

        where_clause = ""
        params = []
        if search and columns:
            conditions = [f"`{col}` LIKE %s" for col in columns]
            params = [f"%{search}%"] * len(columns)
            where_clause = f"WHERE {' OR '.join(conditions)}"

        order_clause = ""
        if order:
            order_clause = f"ORDER BY {order}"

        cursor.execute(f"SELECT COUNT(*) as total FROM `{table_name}` {where_clause}", params)
        total = cursor.fetchone()['total']

        offset = (page - 1) * page_size
        query_params = params + [page_size, offset]
        cursor.execute(f"SELECT * FROM `{table_name}` {where_clause} {order_clause} LIMIT %s OFFSET %s", query_params)
        rows = cursor.fetchall()

        data = []
        for row in rows:
            row_dict = {}
            for key, value in row.items():
                if isinstance(value, (bytes, bytearray)):
                    row_dict[key] = str(value)
                elif isinstance(value, datetime):
                    row_dict[key] = value.strftime('%Y-%m-%d %H:%M:%S')
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


async def execute_sql(server_id: int, database_name: str, sql: str, db: AsyncSession) -> dict:
    """执行 SQL 语句"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        affected_rows = cursor.rowcount

        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            data = []
            for row in rows:
                row_dict = {}
                for key, value in row.items():
                    if isinstance(value, (bytes, bytearray)):
                        row_dict[key] = str(value)
                    elif isinstance(value, datetime):
                        row_dict[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        row_dict[key] = value
                data.append(row_dict)
            return {
                "success": True,
                "message": f"执行成功，返回 {len(data)} 行",
                "columns": columns,
                "data": data,
                "affected_rows": affected_rows
            }

        return {
            "success": True,
            "message": f"执行成功，影响 {affected_rows} 行",
            "affected_rows": affected_rows
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

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()

        columns = []
        if rows:
            columns = list(rows[0].keys())

        data = []
        for row in rows:
            row_dict = {}
            for key, value in row.items():
                if isinstance(value, (bytes, bytearray)):
                    row_dict[key] = str(value)
                elif isinstance(value, datetime):
                    row_dict[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    row_dict[key] = value
            data.append(row_dict)

        return {
            "success": True,
            "message": "查询成功",
            "columns": columns,
            "data": data
        }
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

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor()
        columns = ', '.join([f'`{k}`' for k in data.keys()])
        placeholders = ', '.join(['%s' for _ in data.values()])
        values = list(data.values())

        sql = f"INSERT INTO `{table_name}` ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, values)
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

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor()
        set_clause = ', '.join([f'`{k}`=%s' for k in new_data.keys()])
        where_clause = ' AND '.join([f'`{k}`=%s' for k in where_data.keys()])
        values = list(new_data.values()) + list(where_data.values())

        sql = f"UPDATE `{table_name}` SET {set_clause} WHERE {where_clause}"
        cursor.execute(sql, values)
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

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password, database_name)
    try:
        cursor = conn.cursor()
        where_clause = ' AND '.join([f'`{k}`=%s' for k in where_data.keys()])
        values = list(where_data.values())

        sql = f"DELETE FROM `{table_name}` WHERE {where_clause}"
        cursor.execute(sql, values)
        conn.commit()
        return {"success": True, "message": "删除成功", "affected_rows": cursor.rowcount}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


# ==================== 用户管理 ====================

async def get_users(server_id: int, db: AsyncSession) -> List[dict]:
    """获取 MySQL 用户列表（含权限信息）"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT User, Host FROM mysql.user ORDER BY User, Host")
        raw_users = cursor.fetchall()

        grant_pattern = re.compile(
            r"GRANT\s+(.+?)\s+ON\s+(.+)\.(.+?)\s+TO",
            re.IGNORECASE
        )

        users = []
        for row in raw_users:
            username = row.get('User') if isinstance(row, dict) else row[0]
            host = row.get('Host') if isinstance(row, dict) else row[1]

            cursor.execute("SHOW GRANTS FOR `" + username + "`@`" + host + "`")
            grant_rows = cursor.fetchall()

            grants = []
            for grant_row in grant_rows:
                grant_str = list(grant_row.values())[0] if isinstance(grant_row, dict) else grant_row[0]

                match = grant_pattern.search(grant_str)
                if match:
                    privileges_str = match.group(1).strip()
                    db_name = match.group(2).strip().strip('`')

                    if privileges_str.upper() == 'ALL PRIVILEGES':
                        privileges = ['ALL PRIVILEGES']
                    else:
                        privileges = [p.strip() for p in privileges_str.split(',')]

                    grants.append({
                        "database_name": db_name,
                        "privileges": privileges
                    })

            users.append({
                "User": username,
                "Host": host,
                "grants": grants
            })

        return users
    finally:
        conn.close()


async def create_user(server_id: int, data: schemas.MysqlCreateUserRequest, db: AsyncSession) -> dict:
    """创建 MySQL 用户"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password)
    try:
        cursor = conn.cursor()
        safe_username = data.username.replace('%', '%%')
        safe_host = data.host.replace('%', '%%')
        sql = "CREATE USER `" + safe_username + "`@`" + safe_host + "` IDENTIFIED BY %s"
        cursor.execute(sql, (data.password,))
        conn.commit()
        return {"success": True, "message": "用户 " + data.username + " 创建成功"}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


async def delete_user(server_id: int, username: str, host: str, db: AsyncSession) -> dict:
    """删除 MySQL 用户"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password)
    try:
        cursor = conn.cursor()
        safe_username = username
        safe_host = host
        sql = "DROP USER `" + safe_username + "`@`" + safe_host + "`"
        cursor.execute(sql)
        conn.commit()
        return {"success": True, "message": "用户 " + username + " 删除成功"}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


async def update_user(server_id: int, data: schemas.MysqlUpdateUserRequest, db: AsyncSession) -> dict:
    """更新 MySQL 用户（修改密码、重命名）"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password)
    try:
        cursor = conn.cursor()

        # 如果用户名或主机名变更，检查目标用户是否已存在
        if data.new_username or data.new_host:
            new_user = data.new_username or data.username
            new_host = data.new_host or data.host
            cursor.execute("SELECT COUNT(*) as cnt FROM mysql.user WHERE User = %s AND Host = %s", (new_user, new_host))
            result = cursor.fetchone()
            if result and result.get('cnt', 0) > 0:
                return {"success": False, "message": "目标用户 '" + new_user + "'@'" + new_host + "' 已存在"}
            # 先创建新用户，再删除旧用户
            safe_new_user = new_user.replace('%', '%%')
            safe_new_host = new_host.replace('%', '%%')
            cursor.execute("CREATE USER `" + safe_new_user + "`@`" + safe_new_host + "` IDENTIFIED BY %s", (data.new_password or '',))
            # 如果只改主机，复制旧用户的权限
            if not data.new_username:
                old_user = data.username
                old_host = data.host
                cursor.execute("SHOW GRANTS FOR `" + old_user + "`@`" + old_host + "`")
                grants = cursor.fetchall()
                for grant_row in grants:
                    grant_stmt = list(grant_row.values())[0]
                    if 'IDENTIFIED BY' in grant_stmt.upper():
                        grant_prefix = grant_stmt.split('IDENTIFIED BY')[0]
                    else:
                        grant_prefix = grant_stmt.rsplit(' TO', 1)[0]
                    grant_prefix = grant_prefix + ' TO `' + new_user + '`@`' + new_host + '`'
                    try:
                        cursor.execute(grant_prefix)
                    except Exception:
                        pass
            cursor.execute("DROP USER `" + data.username + "`@`" + data.host + "`")
        else:
            # 仅修改密码
            if data.new_password:
                safe_old_user = data.username.replace('%', '%%')
                safe_old_host = data.host.replace('%', '%%')
                cursor.execute("ALTER USER `" + safe_old_user + "`@`" + safe_old_host + "` IDENTIFIED BY %s", (data.new_password,))

        cursor.execute("FLUSH PRIVILEGES")
        conn.commit()
        return {"success": True, "message": "用户 " + data.username + " 更新成功"}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


async def grant_privileges(server_id: int, data: schemas.MysqlGrantRequest, db: AsyncSession) -> dict:
    """授权用户"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    conn = get_mysql_connection(db_server.host, db_server.port, db_server.username, db_server.password)
    try:
        cursor = conn.cursor()
        privileges = ', '.join(data.privileges)
        safe_username = data.username
        safe_host = data.host
        safe_db = data.database_name
        sql = "GRANT " + privileges + " ON `" + safe_db + "`.* TO `" + safe_username + "`@`" + safe_host + "`"
        cursor.execute(sql)
        cursor.execute("FLUSH PRIVILEGES")
        conn.commit()
        return {"success": True, "message": "授权成功"}
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


# ==================== 备份管理 ====================

async def get_backups(db: AsyncSession, server_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> Tuple[List[models.MysqlBackup], int]:
    """获取备份列表"""
    query = select(models.MysqlBackup)
    if server_id:
        query = query.where(models.MysqlBackup.server_id == server_id)

    query = query.order_by(desc(models.MysqlBackup.id)).offset(skip).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    count_query = select(models.MysqlBackup)
    if server_id:
        count_query = count_query.where(models.MysqlBackup.server_id == server_id)
    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())

    return items, total


async def create_backup(server_id: int, database_name: str, db: AsyncSession) -> models.MysqlBackup:
    """创建备份"""
    db_server = await get_server(db, server_id)
    if not db_server:
        raise Exception("服务器不存在")

    backup_dir = os.path.join(settings.BACKUP_PATH, "mysql", str(server_id), database_name)
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{database_name}_{timestamp}.sql"
    backup_path = os.path.join(backup_dir, backup_filename)

    try:
        import subprocess
        cmd = [
            "mysqldump",
            f"--host={db_server.host}",
            f"--port={db_server.port}",
            f"--user={db_server.username}",
            f"--password={db_server.password}",
            "--single-transaction",
            "--routines",
            "--triggers",
            "--events",
            database_name
        ]

        env = os.environ.copy()
        env['MYSQL_PWD'] = db_server.password

        with open(backup_path, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env, timeout=3600)

        if result.returncode != 0:
            error_msg = result.stderr.decode('utf-8', errors='ignore')
            raise Exception(f"备份失败: {error_msg}")

        file_size = os.path.getsize(backup_path)

        db_backup = models.MysqlBackup(
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
    """恢复备份"""
    result = await db.execute(
        select(models.MysqlBackup).where(models.MysqlBackup.id == backup_id)
    )
    backup = result.scalar_one_or_none()
    if not backup:
        raise Exception("备份不存在")

    if not os.path.exists(backup.backup_path):
        raise Exception("备份文件不存在")

    db_server = await get_server(db, backup.server_id)
    if not db_server:
        raise Exception("服务器不存在")

    try:
        import subprocess
        cmd = [
            "mysql",
            f"--host={db_server.host}",
            f"--port={db_server.port}",
            f"--user={db_server.username}",
            f"--password={db_server.password}",
            backup.database_name
        ]

        env = os.environ.copy()
        env['MYSQL_PWD'] = db_server.password

        with open(backup.backup_path, 'r') as f:
            result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, env=env, timeout=3600)

        if result.returncode != 0:
            error_msg = result.stderr.decode('utf-8', errors='ignore')
            raise Exception(f"恢复失败: {error_msg}")

        return True

    except Exception as e:
        raise Exception(f"恢复失败: {str(e)}")


async def delete_backup(db: AsyncSession, backup_id: int) -> bool:
    """删除备份"""
    result = await db.execute(
        select(models.MysqlBackup).where(models.MysqlBackup.id == backup_id)
    )
    backup = result.scalar_one_or_none()
    if not backup:
        return False

    if os.path.exists(backup.backup_path):
        os.remove(backup.backup_path)

    await db.delete(backup)
    await db.commit()
    return True
