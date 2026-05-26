from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Any


class SqliteDatabaseBase(BaseModel):
    name: str
    path: str
    description: Optional[str] = None


class SqliteDatabaseCreate(SqliteDatabaseBase):
    pass


class SqliteDatabaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class SqliteDatabase(SqliteDatabaseBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SqliteDatabaseListResponse(BaseModel):
    total: int
    items: List[SqliteDatabase]
    skip: int
    limit: int


class SqliteTableInfo(BaseModel):
    name: str
    count: int


class SqliteColumnInfo(BaseModel):
    cid: int
    name: str
    type: str
    notnull: int
    default_value: Any = None
    pk: int


class SqliteTableDataResponse(BaseModel):
    columns: List[SqliteColumnInfo]
    data: List[dict]
    total: int
    page: int
    page_size: int


class SqliteExecuteRequest(BaseModel):
    database_id: int
    sql: str


class SqliteExecuteResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    affected_rows: Optional[int] = None


class SqliteQueryRequest(BaseModel):
    database_id: int
    sql: str


class SqliteQueryResponse(BaseModel):
    success: bool
    message: str
    columns: Optional[List[str]] = None
    data: Optional[List[dict]] = None


class SqliteBackupBase(BaseModel):
    database_id: int
    database_name: str
    description: Optional[str] = None


class SqliteBackupCreate(SqliteBackupBase):
    pass


class SqliteBackup(SqliteBackupBase):
    id: int
    backup_path: str
    file_size: int
    status: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SqliteBackupListResponse(BaseModel):
    total: int
    items: List[SqliteBackup]
    skip: int
    limit: int


class SqliteUpdateDataRequest(BaseModel):
    table: str
    where_data: dict
    new_data: dict


class SqliteDeleteDataRequest(BaseModel):
    table: str
    where_data: dict


class SqliteAddDataRequest(BaseModel):
    table: str
    data: dict


class SqliteCreateTableRequest(BaseModel):
    sql: str


# ==================== MySQL Schemas ====================

class MysqlServerBase(BaseModel):
    host: str
    port: int = 3306
    username: str
    password: str
    description: Optional[str] = None


class MysqlServerCreate(MysqlServerBase):
    pass


class MysqlServerUpdate(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    description: Optional[str] = None


class MysqlServerResponse(MysqlServerBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MysqlServerListResponse(BaseModel):
    total: int
    items: List[MysqlServerResponse]


class MysqlDatabaseInfo(BaseModel):
    name: str


class MysqlTableInfo(BaseModel):
    name: str
    rows: Optional[int] = None
    engine: Optional[str] = None
    size: Optional[str] = None


class MysqlColumnInfo(BaseModel):
    field: str
    type: str
    null: str
    key: str
    default: Optional[str] = None
    extra: str


class MysqlTableDataResponse(BaseModel):
    columns: List[str]
    data: List[dict]
    total: int
    page: int
    page_size: int


class MysqlExecuteRequest(BaseModel):
    sql: str


class MysqlExecuteResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    affected_rows: Optional[int] = None


class MysqlQueryResponse(BaseModel):
    success: bool
    message: str
    columns: Optional[List[str]] = None
    data: Optional[List[dict]] = None


class MysqlCreateDatabaseRequest(BaseModel):
    name: str
    charset: str = "utf8mb4"


class MysqlCreateTableRequest(BaseModel):
    sql: str


class MysqlCreateUserRequest(BaseModel):
    username: str
    password: str
    host: str = "%"


class MysqlDeleteUserRequest(BaseModel):
    username: str
    host: str = "%"


class MysqlUpdateUserRequest(BaseModel):
    username: str
    host: str = "%"
    new_username: Optional[str] = None
    new_password: Optional[str] = None
    new_host: Optional[str] = None


class MysqlGrantRequest(BaseModel):
    username: str
    database_name: str
    host: str = "%"
    privileges: List[str] = ["ALL PRIVILEGES"]


class MysqlBackupListResponse(BaseModel):
    total: int
    items: List[Any]


# ==================== PostgreSQL Schemas ====================

class PostgresqlServerBase(BaseModel):
    host: str
    port: int = 5432
    username: str
    password: str
    description: Optional[str] = None


class PostgresqlServerCreate(PostgresqlServerBase):
    pass


class PostgresqlServerUpdate(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    description: Optional[str] = None


class PostgresqlServerResponse(PostgresqlServerBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PostgresqlServerListResponse(BaseModel):
    total: int
    items: List[PostgresqlServerResponse]


class PostgresqlDatabaseInfo(BaseModel):
    name: str


class PostgresqlTableInfo(BaseModel):
    name: str
    rows: Optional[int] = None
    size: Optional[str] = None


class PostgresqlColumnInfo(BaseModel):
    field: str
    type: str
    null: str
    key: str = ''
    default: Optional[str] = None
    extra: str = ''


class PostgresqlTableDataResponse(BaseModel):
    columns: List[str]
    data: List[dict]
    total: int
    page: int
    page_size: int


class PostgresqlExecuteRequest(BaseModel):
    sql: str


class PostgresqlQueryRequest(BaseModel):
    sql: str


class PostgresqlExecuteResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    affected_rows: Optional[int] = None


class PostgresqlQueryResponse(BaseModel):
    success: bool
    message: str
    columns: Optional[List[str]] = None
    data: Optional[List[dict]] = None


class PostgresqlCreateDatabaseRequest(BaseModel):
    name: str


class PostgresqlCreateTableRequest(BaseModel):
    sql: str


class PostgresqlCreateUserRequest(BaseModel):
    username: str
    password: str


class PostgresqlDeleteUserRequest(BaseModel):
    username: str


class PostgresqlAlterUserRequest(BaseModel):
    username: str
    new_username: Optional[str] = None
    new_password: Optional[str] = None


class PostgresqlGrantRequest(BaseModel):
    username: str
    database_name: str
    privileges: List[str] = ["ALL"]


class PostgresqlBackupListResponse(BaseModel):
    total: int
    items: List[Any]
