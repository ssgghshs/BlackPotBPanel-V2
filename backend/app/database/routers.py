from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from middleware.auth import get_current_active_user
from config.database import get_database_db
from app.database import service, schemas
from app.database import mysql_service
from app.database import postgresql_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/database", tags=["database"])


# ==================== SQLite数据库管理 ====================

@router.get("/sqlite/list", response_model=schemas.SqliteDatabaseListResponse)
async def get_sqlite_databases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取 SQLite 数据库列表"""
    try:
        items, total = await service.get_databases(db, skip=skip, limit=limit)
        return schemas.SqliteDatabaseListResponse(
            total=total,
            items=items,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        logger.error(f"获取数据库列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sqlite/add", response_model=schemas.SqliteDatabase)
async def add_sqlite_database(
    database_in: schemas.SqliteDatabaseCreate,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """添加 SQLite 数据库"""
    try:
        result = await service.create_database(db, database_in)
        return result
    except Exception as e:
        logger.error(f"添加数据库失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sqlite/{database_id}/update", response_model=schemas.SqliteDatabase)
async def update_sqlite_database(
    database_id: int,
    database_in: schemas.SqliteDatabaseUpdate,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """更新数据库信息"""
    try:
        result = await service.update_database(db, database_id, database_in)
        if not result:
            raise HTTPException(status_code=404, detail="数据库不存在")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新数据库失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sqlite/{database_id}/delete")
async def delete_sqlite_database(
    database_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """删除数据库"""
    try:
        result = await service.delete_database(db, database_id)
        if not result:
            raise HTTPException(status_code=404, detail="数据库不存在")
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除数据库失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== SQLite表管理 ====================

@router.get("/sqlite/{database_id}/tables")
async def get_sqlite_tables(
    database_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取数据库表列表"""
    try:
        result = await service.get_tables(db, database_id)
        return result
    except Exception as e:
        logger.error(f"获取表列表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sqlite/{database_id}/table/{table}/columns")
async def get_sqlite_table_columns(
    database_id: int,
    table: str,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取表的列信息"""
    try:
        result = await service.get_table_columns(db, database_id, table)
        return {"columns": result}
    except Exception as e:
        logger.error(f"获取列信息失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sqlite/{database_id}/table/{table}/data")
async def get_sqlite_table_data(
    database_id: int,
    table: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    search: Optional[str] = None,
    order: Optional[str] = None,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取表数据"""
    try:
        result = await service.get_table_data(
            db, database_id, table,
            page=page, page_size=page_size,
            search=search, order=order
        )
        return result
    except Exception as e:
        logger.error(f"获取表数据失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sqlite/{database_id}/table/create")
async def create_sqlite_table(
    database_id: int,
    request: schemas.SqliteCreateTableRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """创建表"""
    try:
        result = await service.create_table(db, database_id, request.sql)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sqlite/{database_id}/table/{table}/delete")
async def delete_sqlite_table(
    database_id: int,
    table: str,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """删除表"""
    try:
        result = await service.delete_table(db, database_id, table)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== SQLite数据操作 ====================

@router.post("/sqlite/{database_id}/data/add")
async def add_sqlite_data(
    database_id: int,
    request: schemas.SqliteAddDataRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """添加数据"""
    try:
        result = await service.add_table_data(db, database_id, request.table, request.data)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加数据失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sqlite/{database_id}/data/update")
async def update_sqlite_data(
    database_id: int,
    request: schemas.SqliteUpdateDataRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """更新数据"""
    try:
        result = await service.update_table_data(
            db, database_id, request.table,
            request.where_data, request.new_data
        )
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新数据失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sqlite/{database_id}/data/delete")
async def delete_sqlite_data(
    database_id: int,
    request: schemas.SqliteDeleteDataRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """删除数据"""
    try:
        result = await service.delete_table_data(db, database_id, request.table, request.where_data)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除数据失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== SQLiteSQL执行 ====================

@router.post("/sqlite/{database_id}/execute")
async def execute_sql(
    database_id: int,
    request: schemas.SqliteExecuteRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """执行 SQL 语句"""
    try:
        result = await service.execute_sql(db, database_id, request.sql)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行 SQL 失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sqlite/{database_id}/query")
async def query_sql(
    database_id: int,
    request: schemas.SqliteQueryRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """执行查询 SQL"""
    try:
        result = await service.query_sql(db, database_id, request.sql)
        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询 SQL 失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== PostgreSQL 备份管理 ====================

@router.get("/pgsql/backup/list")
async def get_pgsql_backups(
    server_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取 PostgreSQL 备份列表"""
    try:
        items, total = await postgresql_service.get_backups(db, server_id=server_id, skip=skip, limit=limit)
        return {
            "total": total,
            "items": [
                {
                    "id": item.id,
                    "server_id": item.server_id,
                    "database_name": item.database_name,
                    "backup_path": item.backup_path,
                    "file_size": item.file_size,
                    "status": item.status,
                    "description": item.description,
                    "created_at": str(item.created_at) if item.created_at else None
                }
                for item in items
            ]
        }
    except Exception as e:
        logger.error(f"获取备份列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pgsql/{server_id}/database/{database_name}/backup/create")
async def create_pgsql_backup(
    server_id: int,
    database_name: str,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """创建 PostgreSQL 备份"""
    try:
        result = await postgresql_service.create_backup(server_id, database_name, db)
        return {
            "id": result.id,
            "server_id": result.server_id,
            "database_name": result.database_name,
            "backup_path": result.backup_path,
            "file_size": result.file_size,
            "status": result.status,
            "created_at": str(result.created_at) if result.created_at else None
        }
    except Exception as e:
        logger.error(f"创建备份失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pgsql/backup/{backup_id}/restore")
async def restore_pgsql_backup(
    backup_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """恢复 PostgreSQL 备份"""
    try:
        result = await postgresql_service.restore_backup(backup_id, db)
        if not result:
            raise HTTPException(status_code=400, detail="恢复备份失败")
        return {"success": True, "message": "恢复成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复备份失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pgsql/backup/{backup_id}/delete")
async def delete_pgsql_backup(
    backup_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """删除 PostgreSQL 备份"""
    try:
        result = await postgresql_service.delete_backup(db, backup_id)
        if not result:
            raise HTTPException(status_code=404, detail="备份不存在")
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除备份失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== SQLite备份管理 ====================

@router.get("/sqlite/backup/list", response_model=schemas.SqliteBackupListResponse)
async def get_sqlite_backups(
    database_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取备份列表"""
    try:
        items, total = await service.get_backups(db, database_id=database_id, skip=skip, limit=limit)
        return schemas.SqliteBackupListResponse(
            total=total,
            items=items,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        logger.error(f"获取备份列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sqlite/{database_id}/backup/create", response_model=schemas.SqliteBackup)
async def create_sqlite_backup(
    database_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """创建备份"""
    try:
        result = await service.create_backup(db, database_id)
        return result
    except Exception as e:
        logger.error(f"创建备份失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sqlite/backup/{backup_id}/delete")
async def delete_sqlite_backup(
    backup_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """删除备份"""
    try:
        result = await service.delete_backup(db, backup_id)
        if not result:
            raise HTTPException(status_code=404, detail="备份不存在")
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除备份失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sqlite/backup/{backup_id}/restore")
async def restore_sqlite_backup(
    backup_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """恢复备份"""
    try:
        result = await service.restore_backup(db, backup_id)
        if not result:
            raise HTTPException(status_code=400, detail="恢复备份失败")
        return {"success": True, "message": "恢复成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复备份失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== MySQL服务器管理 ====================

@router.get("/mysql/servers")
async def get_mysql_servers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取 MySQL 服务器列表"""
    try:
        items, total = await mysql_service.get_servers(db, skip=skip, limit=limit)
        return {
            "total": total,
            "items": [
                {
                    "id": item.id,
                    "host": item.host,
                    "port": item.port,
                    "username": item.username,
                    "description": item.description,
                    "created_at": str(item.created_at) if item.created_at else None,
                    "updated_at": str(item.updated_at) if item.updated_at else None
                }
                for item in items
            ]
        }
    except Exception as e:
        logger.error(f"获取 MySQL 服务器列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mysql/servers/add")
async def add_mysql_server(
    server_in: schemas.MysqlServerCreate,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """添加 MySQL 服务器"""
    try:
        result = await mysql_service.create_server(db, server_in)
        return {
            "id": result.id,
            "host": result.host,
            "port": result.port,
            "username": result.username,
            "description": result.description,
            "created_at": str(result.created_at) if result.created_at else None
        }
    except Exception as e:
        logger.error(f"添加 MySQL 服务器失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mysql/servers/{server_id}/update")
async def update_mysql_server(
    server_id: int,
    server_in: schemas.MysqlServerUpdate,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """更新 MySQL 服务器"""
    try:
        result = await mysql_service.update_server(db, server_id, server_in)
        if not result:
            raise HTTPException(status_code=404, detail="服务器不存在")
        return {"success": True, "message": "更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新 MySQL 服务器失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mysql/servers/{server_id}/delete")
async def delete_mysql_server(
    server_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """删除 MySQL 服务器"""
    try:
        result = await mysql_service.delete_server(db, server_id)
        if not result:
            raise HTTPException(status_code=404, detail="服务器不存在")
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除 MySQL 服务器失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mysql/servers/{server_id}/test")
async def test_mysql_connection(
    server_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """测试 MySQL 连接"""
    try:
        db_server = await mysql_service.get_server(db, server_id)
        if not db_server:
            raise HTTPException(status_code=404, detail="服务器不存在")
        result = await mysql_service.test_connection(
            db_server.host, db_server.port, db_server.username, db_server.password
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试连接失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== MySQL数据库管理 ====================

@router.get("/mysql/{server_id}/databases")
async def get_mysql_databases(
    server_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取 MySQL 数据库列表"""
    try:
        databases = await mysql_service.get_databases(server_id, db)
        return {"databases": databases}
    except Exception as e:
        logger.error(f"获取数据库列表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mysql/{server_id}/databases/create")
async def create_mysql_database(
    server_id: int,
    request: schemas.MysqlCreateDatabaseRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """创建 MySQL 数据库"""
    try:
        result = await mysql_service.create_database(server_id, request, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建数据库失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mysql/{server_id}/databases/{database_name}/delete")
async def delete_mysql_database(
    server_id: int,
    database_name: str,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """删除 MySQL 数据库"""
    try:
        result = await mysql_service.delete_database(server_id, database_name, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除数据库失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== MySQL表管理 ====================

@router.get("/mysql/{server_id}/database/{database_name}/tables")
async def get_mysql_tables(
    server_id: int,
    database_name: str,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取 MySQL 表列表"""
    try:
        tables = await mysql_service.get_tables(server_id, database_name, db)
        return {"tables": tables}
    except Exception as e:
        logger.error(f"获取表列表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mysql/{server_id}/database/{database_name}/table/create")
async def create_mysql_table(
    server_id: int,
    database_name: str,
    request: schemas.MysqlCreateTableRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """创建 MySQL 表"""
    try:
        result = await mysql_service.create_table(server_id, database_name, request.sql, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mysql/{server_id}/database/{database_name}/table/{table_name}/delete")
async def delete_mysql_table(
    server_id: int,
    database_name: str,
    table_name: str,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """删除 MySQL 表"""
    try:
        result = await mysql_service.delete_table(server_id, database_name, table_name, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mysql/{server_id}/database/{database_name}/table/{table_name}/columns")
async def get_mysql_table_columns(
    server_id: int,
    database_name: str,
    table_name: str,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取 MySQL 表列信息"""
    try:
        columns = await mysql_service.get_table_columns(server_id, database_name, table_name, db)
        return {"columns": columns}
    except Exception as e:
        logger.error(f"获取列信息失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mysql/{server_id}/database/{database_name}/table/{table_name}/data")
async def get_mysql_table_data(
    server_id: int,
    database_name: str,
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    search: Optional[str] = None,
    order: Optional[str] = None,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取 MySQL 表数据"""
    try:
        result = await mysql_service.get_table_data(
            server_id, database_name, table_name,
            page=page, page_size=page_size,
            search=search, order=order, db=db
        )
        return result
    except Exception as e:
        logger.error(f"获取表数据失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== MySQL数据操作 ====================

@router.post("/mysql/{server_id}/database/{database_name}/data/add")
async def add_mysql_data(
    server_id: int,
    database_name: str,
    request: schemas.SqliteAddDataRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """添加数据"""
    try:
        result = await mysql_service.add_data(server_id, database_name, request.table, request.data, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加数据失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mysql/{server_id}/database/{database_name}/data/update")
async def update_mysql_data(
    server_id: int,
    database_name: str,
    request: schemas.SqliteUpdateDataRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """更新数据"""
    try:
        result = await mysql_service.update_data(
            server_id, database_name, request.table,
            request.where_data, request.new_data, db
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新数据失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mysql/{server_id}/database/{database_name}/data/delete")
async def delete_mysql_data(
    server_id: int,
    database_name: str,
    request: schemas.SqliteDeleteDataRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """删除数据"""
    try:
        result = await mysql_service.delete_data(server_id, database_name, request.table, request.where_data, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除数据失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== MySQL SQL执行 ====================

@router.post("/mysql/{server_id}/database/{database_name}/execute")
async def execute_mysql_sql(
    server_id: int,
    database_name: str,
    request: schemas.MysqlExecuteRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """执行 SQL 语句"""
    try:
        result = await mysql_service.execute_sql(server_id, database_name, request.sql, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行 SQL 失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mysql/{server_id}/database/{database_name}/query")
async def query_mysql_sql(
    server_id: int,
    database_name: str,
    request: schemas.MysqlExecuteRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """执行查询 SQL"""
    try:
        result = await mysql_service.query_sql(server_id, database_name, request.sql, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询 SQL 失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== MySQL用户管理 ====================

@router.get("/mysql/{server_id}/users")
async def get_mysql_users(
    server_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取 MySQL 用户列表"""
    try:
        users = await mysql_service.get_users(server_id, db)
        return {"users": users}
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mysql/{server_id}/users/create")
async def create_mysql_user(
    server_id: int,
    request: schemas.MysqlCreateUserRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """创建 MySQL 用户"""
    try:
        result = await mysql_service.create_user(server_id, request, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建用户失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mysql/{server_id}/users/delete")
async def delete_mysql_user(
    server_id: int,
    request: schemas.MysqlDeleteUserRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """删除 MySQL 用户"""
    try:
        result = await mysql_service.delete_user(server_id, request.username, request.host, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mysql/{server_id}/users/update")
async def update_mysql_user(
    server_id: int,
    request: schemas.MysqlUpdateUserRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """更新 MySQL 用户"""
    try:
        result = await mysql_service.update_user(server_id, request, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mysql/{server_id}/users/grant")
async def grant_mysql_privileges(
    server_id: int,
    request: schemas.MysqlGrantRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """授权 MySQL 用户"""
    try:
        result = await mysql_service.grant_privileges(server_id, request, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"授权失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== MySQL备份管理 ====================

@router.get("/mysql/backup/list")
async def get_mysql_backups(
    server_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取 MySQL 备份列表"""
    try:
        items, total = await mysql_service.get_backups(db, server_id=server_id, skip=skip, limit=limit)
        return {
            "total": total,
            "items": [
                {
                    "id": item.id,
                    "server_id": item.server_id,
                    "database_name": item.database_name,
                    "backup_path": item.backup_path,
                    "file_size": item.file_size,
                    "status": item.status,
                    "description": item.description,
                    "created_at": str(item.created_at) if item.created_at else None
                }
                for item in items
            ]
        }
    except Exception as e:
        logger.error(f"获取备份列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mysql/{server_id}/database/{database_name}/backup/create")
async def create_mysql_backup(
    server_id: int,
    database_name: str,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """创建 MySQL 备份"""
    try:
        result = await mysql_service.create_backup(server_id, database_name, db)
        return {
            "id": result.id,
            "server_id": result.server_id,
            "database_name": result.database_name,
            "backup_path": result.backup_path,
            "file_size": result.file_size,
            "status": result.status,
            "created_at": str(result.created_at) if result.created_at else None
        }
    except Exception as e:
        logger.error(f"创建备份失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mysql/backup/{backup_id}/restore")
async def restore_mysql_backup(
    backup_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """恢复 MySQL 备份"""
    try:
        result = await mysql_service.restore_backup(backup_id, db)
        if not result:
            raise HTTPException(status_code=400, detail="恢复备份失败")
        return {"success": True, "message": "恢复成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复备份失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mysql/backup/{backup_id}/delete")
async def delete_mysql_backup(
    backup_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """删除 MySQL 备份"""
    try:
        result = await mysql_service.delete_backup(db, backup_id)
        if not result:
            raise HTTPException(status_code=404, detail="备份不存在")
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除备份失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== PostgreSQL 服务器管理 ====================

@router.get("/pgsql/servers")
async def get_pgsql_servers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取 PostgreSQL 服务器列表"""
    try:
        items, total = await postgresql_service.get_servers(db, skip=skip, limit=limit)
        return {
            "total": total,
            "items": [
                {
                    "id": item.id,
                    "host": item.host,
                    "port": item.port,
                    "username": item.username,
                    "description": item.description,
                    "created_at": str(item.created_at) if item.created_at else None,
                    "updated_at": str(item.updated_at) if item.updated_at else None
                }
                for item in items
            ]
        }
    except Exception as e:
        logger.error(f"获取 PostgreSQL 服务器列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pgsql/servers/add")
async def add_pgsql_server(
    server_in: schemas.PostgresqlServerCreate,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """添加 PostgreSQL 服务器"""
    try:
        result = await postgresql_service.create_server(db, server_in)
        return {
            "id": result.id,
            "host": result.host,
            "port": result.port,
            "username": result.username,
            "description": result.description,
            "created_at": str(result.created_at) if result.created_at else None
        }
    except Exception as e:
        logger.error(f"添加 PostgreSQL 服务器失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pgsql/servers/{server_id}/update")
async def update_pgsql_server(
    server_id: int,
    server_in: schemas.PostgresqlServerUpdate,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """更新 PostgreSQL 服务器"""
    try:
        result = await postgresql_service.update_server(db, server_id, server_in)
        if not result:
            raise HTTPException(status_code=404, detail="服务器不存在")
        return {"success": True, "message": "更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新 PostgreSQL 服务器失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pgsql/servers/{server_id}/delete")
async def delete_pgsql_server(
    server_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """删除 PostgreSQL 服务器"""
    try:
        result = await postgresql_service.delete_server(db, server_id)
        if not result:
            raise HTTPException(status_code=404, detail="服务器不存在")
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除 PostgreSQL 服务器失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pgsql/servers/{server_id}/test")
async def test_pgsql_connection(
    server_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """测试 PostgreSQL 连接"""
    try:
        db_server = await postgresql_service.get_server(db, server_id)
        if not db_server:
            raise HTTPException(status_code=404, detail="服务器不存在")
        result = await postgresql_service.test_connection(
            db_server.host, db_server.port, db_server.username, db_server.password
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试连接失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== PostgreSQL 数据库管理 ====================

@router.get("/pgsql/{server_id}/databases")
async def get_pgsql_databases(
    server_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取 PostgreSQL 数据库列表"""
    try:
        databases = await postgresql_service.get_databases(server_id, db)
        return {"databases": databases}
    except Exception as e:
        logger.error(f"获取数据库列表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pgsql/{server_id}/databases/create")
async def create_pgsql_database(
    server_id: int,
    request: schemas.PostgresqlCreateDatabaseRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """创建 PostgreSQL 数据库"""
    try:
        result = await postgresql_service.create_database(server_id, request, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建数据库失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pgsql/{server_id}/databases/{database_name}/delete")
async def delete_pgsql_database(
    server_id: int,
    database_name: str,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """删除 PostgreSQL 数据库"""
    try:
        result = await postgresql_service.delete_database(server_id, database_name, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除数据库失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== PostgreSQL 表管理 ====================

@router.get("/pgsql/{server_id}/database/{database_name}/tables")
async def get_pgsql_tables(
    server_id: int,
    database_name: str,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取 PostgreSQL 表列表"""
    try:
        tables = await postgresql_service.get_tables(server_id, database_name, db)
        return {"tables": tables}
    except Exception as e:
        logger.error(f"获取表列表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pgsql/{server_id}/database/{database_name}/table/create")
async def create_pgsql_table(
    server_id: int,
    database_name: str,
    request: schemas.PostgresqlCreateTableRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """创建 PostgreSQL 表"""
    try:
        result = await postgresql_service.create_table(server_id, database_name, request.sql, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pgsql/{server_id}/database/{database_name}/table/{table_name}/delete")
async def delete_pgsql_table(
    server_id: int,
    database_name: str,
    table_name: str,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """删除 PostgreSQL 表"""
    try:
        result = await postgresql_service.delete_table(server_id, database_name, table_name, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pgsql/{server_id}/database/{database_name}/table/{table_name}/columns")
async def get_pgsql_table_columns(
    server_id: int,
    database_name: str,
    table_name: str,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取 PostgreSQL 表列信息"""
    try:
        columns = await postgresql_service.get_table_columns(server_id, database_name, table_name, db)
        return {"columns": columns}
    except Exception as e:
        logger.error(f"获取列信息失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pgsql/{server_id}/database/{database_name}/table/{table_name}/data")
async def get_pgsql_table_data(
    server_id: int,
    database_name: str,
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    search: Optional[str] = None,
    order: Optional[str] = None,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取 PostgreSQL 表数据"""
    try:
        result = await postgresql_service.get_table_data(
            server_id, database_name, table_name,
            page=page, page_size=page_size,
            search=search, order=order,
            db=db
        )
        return result
    except Exception as e:
        logger.error(f"获取表数据失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== PostgreSQL 数据操作 ====================

@router.post("/pgsql/{server_id}/database/{database_name}/data/add")
async def add_pgsql_data(
    server_id: int,
    database_name: str,
    request: schemas.SqliteAddDataRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """添加数据"""
    try:
        result = await postgresql_service.add_data(server_id, database_name, request.table, request.data, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加数据失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pgsql/{server_id}/database/{database_name}/data/update")
async def update_pgsql_data(
    server_id: int,
    database_name: str,
    request: schemas.SqliteUpdateDataRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """更新数据"""
    try:
        result = await postgresql_service.update_data(server_id, database_name, request.table, request.where_data, request.new_data, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新数据失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pgsql/{server_id}/database/{database_name}/data/delete")
async def delete_pgsql_data(
    server_id: int,
    database_name: str,
    request: schemas.SqliteDeleteDataRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """删除数据"""
    try:
        result = await postgresql_service.delete_data(server_id, database_name, request.table, request.where_data, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除数据失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== PostgreSQL 用户管理 ====================

@router.get("/pgsql/{server_id}/users")
async def get_pgsql_users(
    server_id: int,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """获取 PostgreSQL 用户列表"""
    try:
        users = await postgresql_service.get_users(server_id, db)
        return {"users": users}
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pgsql/{server_id}/users/create")
async def create_pgsql_user(
    server_id: int,
    request: schemas.PostgresqlCreateUserRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """创建 PostgreSQL 用户"""
    try:
        result = await postgresql_service.create_user(server_id, request, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建用户失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pgsql/{server_id}/users/delete")
async def delete_pgsql_user(
    server_id: int,
    request: schemas.PostgresqlDeleteUserRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """删除 PostgreSQL 用户"""
    try:
        result = await postgresql_service.delete_user(server_id, request, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pgsql/{server_id}/users/alter")
async def alter_pgsql_user(
    server_id: int,
    request: schemas.PostgresqlAlterUserRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """修改 PostgreSQL 用户"""
    try:
        result = await postgresql_service.alter_user(server_id, request, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"修改用户失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pgsql/{server_id}/users/grant")
async def grant_pgsql_privileges(
    server_id: int,
    request: schemas.PostgresqlGrantRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """授予 PostgreSQL 用户权限"""
    try:
        result = await postgresql_service.grant_privileges(server_id, request, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"授予权限失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== PostgreSQL SQL 执行 ====================

@router.post("/pgsql/{server_id}/database/{database_name}/execute")
async def execute_pgsql_sql(
    server_id: int,
    database_name: str,
    request: schemas.PostgresqlExecuteRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """执行 SQL 语句"""
    try:
        result = await postgresql_service.execute_sql(server_id, database_name, request.sql, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行 SQL 失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pgsql/{server_id}/database/{database_name}/query")
async def query_pgsql_sql(
    server_id: int,
    database_name: str,
    request: schemas.PostgresqlQueryRequest,
    db: AsyncSession = Depends(get_database_db),
    current_user: dict = Depends(get_current_active_user)
):
    """执行查询 SQL"""
    try:
        result = await postgresql_service.query_sql(server_id, database_name, request.sql, db)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询 SQL 失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))