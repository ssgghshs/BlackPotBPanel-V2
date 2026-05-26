import request from '../utils/request'

// ==================== SQLite数据库管理 ====================

// 获取 SQLite 数据库列表
export function getSqliteList(params) {
  return request({
    url: '/database/sqlite/list',
    method: 'get',
    params
  })
}

// 添加 SQLite 数据库
export function addSqliteDatabase(data) {
  return request({
    url: '/database/sqlite/add',
    method: 'post',
    data
  })
}

// 更新 SQLite 数据库信息
export function updateSqliteDatabase(id, data) {
  return request({
    url: `/database/sqlite/${id}/update`,
    method: 'post',
    data
  })
}

// 删除 SQLite 数据库
export function deleteSqliteDatabase(id) {
  return request({
    url: `/database/sqlite/${id}/delete`,
    method: 'post'
  })
}

// ==================== SQLite表管理 ====================

// 获取数据库表列表
export function getSqliteTables(databaseId) {
  return request({
    url: `/database/sqlite/${databaseId}/tables`,
    method: 'get'
  })
}

// 获取表的列信息
export function getSqliteTableColumns(databaseId, table) {
  return request({
    url: `/database/sqlite/${databaseId}/table/${table}/columns`,
    method: 'get'
  })
}

// 获取表数据（分页）
export function getSqliteTableData(databaseId, table, params) {
  return request({
    url: `/database/sqlite/${databaseId}/table/${table}/data`,
    method: 'get',
    params
  })
}

// 创建表
export function createSqliteTable(databaseId, data) {
  return request({
    url: `/database/sqlite/${databaseId}/table/create`,
    method: 'post',
    data
  })
}

// 删除表
export function deleteSqliteTable(databaseId, table) {
  return request({
    url: `/database/sqlite/${databaseId}/table/${table}/delete`,
    method: 'post'
  })
}



// ==================== SQLite数据操作 ====================

// 添加数据
export function addSqliteData(databaseId, data) {
  return request({
    url: `/database/sqlite/${databaseId}/data/add`,
    method: 'post',
    data
  })
}

// 更新数据
export function updateSqliteData(databaseId, data) {
  return request({
    url: `/database/sqlite/${databaseId}/data/update`,
    method: 'post',
    data
  })
}

// 删除数据
export function deleteSqliteData(databaseId, data) {
  return request({
    url: `/database/sqlite/${databaseId}/data/delete`,
    method: 'post',
    data
  })
}

// ==================== SQLite 执行 ====================

// 执行 SQL 语句（写操作）
export function executeSql(databaseId, data) {
  return request({
    url: `/database/sqlite/${databaseId}/execute`,
    method: 'post',
    data
  })
}

// 执行查询 SQL（读操作）
export function querySql(databaseId, data) {
  return request({
    url: `/database/sqlite/${databaseId}/query`,
    method: 'post',
    data
  })
}

// ==================== SQLite备份管理 ====================

// 获取备份列表
export function getSqliteBackups(params) {
  return request({
    url: '/database/sqlite/backup/list',
    method: 'get',
    params
  })
}

// 创建备份
export function createSqliteBackup(databaseId) {
  return request({
    url: `/database/sqlite/${databaseId}/backup/create`,
    method: 'post'
  })
}

// 删除备份
export function deleteSqliteBackup(backupId) {
  return request({
    url: `/database/sqlite/backup/${backupId}/delete`,
    method: 'post'
  })
}

// 恢复备份
export function restoreSqliteBackup(backupId) {
  return request({
    url: `/database/sqlite/backup/${backupId}/restore`,
    method: 'post'
  })
}


// ==================== MySQL 服务器管理 ====================

// 获取 MySQL 服务器列表
export function getMysqlServers(params) {
  return request({
    url: '/database/mysql/servers',
    method: 'get',
    params
  })
}

// 添加 MySQL 服务器
export function addMysqlServer(data) {
  return request({
    url: '/database/mysql/servers/add',
    method: 'post',
    data
  })
}

// 更新 MySQL 服务器
export function updateMysqlServer(serverId, data) {
  return request({
    url: `/database/mysql/servers/${serverId}/update`,
    method: 'post',
    data
  })
}

// 删除 MySQL 服务器
export function deleteMysqlServer(serverId) {
  return request({
    url: `/database/mysql/servers/${serverId}/delete`,
    method: 'post'
  })
}

// 测试 MySQL 连接
export function testMysqlConnection(serverId) {
  return request({
    url: `/database/mysql/servers/${serverId}/test`,
    method: 'post'
  })
}

// ==================== MySQL 数据库管理 ====================

// 获取 MySQL 数据库列表
export function getMysqlDatabases(serverId) {
  return request({
    url: `/database/mysql/${serverId}/databases`,
    method: 'get'
  })
}

// 创建 MySQL 数据库
export function createMysqlDatabase(serverId, data) {
  return request({
    url: `/database/mysql/${serverId}/databases/create`,
    method: 'post',
    data
  })
}

// 删除 MySQL 数据库
export function deleteMysqlDatabase(serverId, databaseName) {
  return request({
    url: `/database/mysql/${serverId}/databases/${databaseName}/delete`,
    method: 'post'
  })
}

// ==================== MySQL 表管理 ====================

// 获取 MySQL 表列表
export function getMysqlTables(serverId, databaseName) {
  return request({
    url: `/database/mysql/${serverId}/database/${databaseName}/tables`,
    method: 'get'
  })
}

// 创建 MySQL 表
export function createMysqlTable(serverId, databaseName, data) {
  return request({
    url: `/database/mysql/${serverId}/database/${databaseName}/table/create`,
    method: 'post',
    data
  })
}

// 获取 MySQL 表列信息
export function getMysqlTableColumns(serverId, databaseName, tableName) {
  return request({
    url: `/database/mysql/${serverId}/database/${databaseName}/table/${tableName}/columns`,
    method: 'get'
  })
}

// 获取 MySQL 表数据
export function getMysqlTableData(serverId, databaseName, tableName, params) {
  return request({
    url: `/database/mysql/${serverId}/database/${databaseName}/table/${tableName}/data`,
    method: 'get',
    params
  })
}


// 删除 MySQL 表
export function deleteMysqlTable(serverId, databaseName, tableName) {
  return request({
    url: `/database/mysql/${serverId}/database/${databaseName}/table/${tableName}/delete`,
    method: 'post'
  })
}



// ==================== MySQL 数据操作 ====================

// 添加数据
export function addMysqlData(serverId, databaseName, data) {
  return request({
    url: `/database/mysql/${serverId}/database/${databaseName}/data/add`,
    method: 'post',
    data
  })
}

// 更新数据
export function updateMysqlData(serverId, databaseName, data) {
  return request({
    url: `/database/mysql/${serverId}/database/${databaseName}/data/update`,
    method: 'post',
    data
  })
}

// 删除数据
export function deleteMysqlData(serverId, databaseName, data) {
  return request({
    url: `/database/mysql/${serverId}/database/${databaseName}/data/delete`,
    method: 'post',
    data
  })
}

// ==================== MySQL SQL 执行 ====================

// 执行 SQL 语句
export function executeMysqlSql(serverId, databaseName, data) {
  return request({
    url: `/database/mysql/${serverId}/database/${databaseName}/execute`,
    method: 'post',
    data
  })
}

// 执行查询 SQL
export function queryMysqlSql(serverId, databaseName, data) {
  return request({
    url: `/database/mysql/${serverId}/database/${databaseName}/query`,
    method: 'post',
    data
  })
}

// ==================== MySQL 备份管理 ====================

// 获取 MySQL 备份列表
export function getMysqlBackups(params) {
  return request({
    url: '/database/mysql/backup/list',
    method: 'get',
    params
  })
}

// 创建 MySQL 备份
export function createMysqlBackup(serverId, databaseName) {
  return request({
    url: `/database/mysql/${serverId}/database/${databaseName}/backup/create`,
    method: 'post'
  })
}

// 恢复 MySQL 备份
export function restoreMysqlBackup(backupId) {
  return request({
    url: `/database/mysql/backup/${backupId}/restore`,
    method: 'post'
  })
}

// 删除 MySQL 备份
export function deleteMysqlBackup(backupId) {
  return request({
    url: `/database/mysql/backup/${backupId}/delete`,
    method: 'post'
  })
}


// ==================== MySQL 用户管理 ====================
//获取MySQL用户列表
export function getMysqlUsers(serverId) {
  return request({
    url: `/database/mysql/${serverId}/users`,
    method: 'get'
  })
}
//创建MySQL用户
export function createMysqlUser(serverId, data) {
  return request({
    url: `/database/mysql/${serverId}/users/create`,
    method: 'post',
    data
  })
}
// 删除MySQL用户
export function deleteMysqlUser(serverId, data) {
  return request({
    url: `/database/mysql/${serverId}/users/delete`,
    method: 'post',
    data
  })
}
// 更新MySQL用户
export function updateMysqlUser(serverId, data) {
  return request({
    url: `/database/mysql/${serverId}/users/update`,
    method: 'post',
    data
  })
}

// 授权MySQL用户
export function grantMysqlPrivileges(serverId, data) {
  return request({
    url: `/database/mysql/${serverId}/users/grant`,
    method: 'post',
    data
  })
}


// ==================== PostgreSQL 服务器管理 ====================

// 获取 PostgreSQL 服务器列表
export function getPgsqlServers(params) {
  return request({
    url: '/database/pgsql/servers',
    method: 'get',
    params
  })
}

// 添加 PostgreSQL 服务器
export function addPgsqlServer(data) {
  return request({
    url: '/database/pgsql/servers/add',
    method: 'post',
    data
  })
}

// 更新 PostgreSQL 服务器
export function updatePgsqlServer(serverId, data) {
  return request({
    url: `/database/pgsql/servers/${serverId}/update`,
    method: 'post',
    data
  })
}

// 删除 PostgreSQL 服务器
export function deletePgsqlServer(serverId) {
  return request({
    url: `/database/pgsql/servers/${serverId}/delete`,
    method: 'post'
  })
}

// 测试 PostgreSQL 连接
export function testPgsqlConnection(serverId) {
  return request({
    url: `/database/pgsql/servers/${serverId}/test`,
    method: 'post'
  })
}

// ==================== PostgreSQL 数据库管理 ====================

// 获取 PostgreSQL 数据库列表
export function getPgsqlDatabases(serverId) {
  return request({
    url: `/database/pgsql/${serverId}/databases`,
    method: 'get'
  })
}

// 创建 PostgreSQL 数据库
export function createPgsqlDatabase(serverId, data) {
  return request({
    url: `/database/pgsql/${serverId}/databases/create`,
    method: 'post',
    data
  })
}

// 删除 PostgreSQL 数据库
export function deletePgsqlDatabase(serverId, databaseName) {
  return request({
    url: `/database/pgsql/${serverId}/databases/${databaseName}/delete`,
    method: 'post'
  })
}

// ==================== PostgreSQL 表管理 ====================

// 获取 PostgreSQL 表列表
export function getPgsqlTables(serverId, databaseName) {
  return request({
    url: `/database/pgsql/${serverId}/database/${databaseName}/tables`,
    method: 'get'
  })
}

// 创建 PostgreSQL 表
export function createPgsqlTable(serverId, databaseName, data) {
  return request({
    url: `/database/pgsql/${serverId}/database/${databaseName}/table/create`,
    method: 'post',
    data
  })
}

// 删除 PostgreSQL 表
export function deletePgsqlTable(serverId, databaseName, tableName) {
  return request({
    url: `/database/pgsql/${serverId}/database/${databaseName}/table/${tableName}/delete`,
    method: 'post'
  })
}

// 获取 PostgreSQL 表列信息
export function getPgsqlTableColumns(serverId, databaseName, tableName) {
  return request({
    url: `/database/pgsql/${serverId}/database/${databaseName}/table/${tableName}/columns`,
    method: 'get'
  })
}

// 获取 PostgreSQL 表数据
export function getPgsqlTableData(serverId, databaseName, tableName, params) {
  return request({
    url: `/database/pgsql/${serverId}/database/${databaseName}/table/${tableName}/data`,
    method: 'get',
    params
  })
}

// ==================== PostgreSQL 数据操作 ====================

// 添加数据
export function addPgsqlData(serverId, databaseName, data) {
  return request({
    url: `/database/pgsql/${serverId}/database/${databaseName}/data/add`,
    method: 'post',
    data
  })
}

// 更新数据
export function updatePgsqlData(serverId, databaseName, data) {
  return request({
    url: `/database/pgsql/${serverId}/database/${databaseName}/data/update`,
    method: 'post',
    data
  })
}

// 删除数据
export function deletePgsqlData(serverId, databaseName, data) {
  return request({
    url: `/database/pgsql/${serverId}/database/${databaseName}/data/delete`,
    method: 'post',
    data
  })
}

// ==================== PostgreSQL SQL 执行 ====================

// 执行 SQL 语句
export function executePgsqlSql(serverId, databaseName, data) {
  return request({
    url: `/database/pgsql/${serverId}/database/${databaseName}/execute`,
    method: 'post',
    data
  })
}

// 执行查询 SQL
export function queryPgsqlSql(serverId, databaseName, data) {
  return request({
    url: `/database/pgsql/${serverId}/database/${databaseName}/query`,
    method: 'post',
    data
  })
}

// ==================== PostgreSQL 用户管理 ====================

// 获取 PostgreSQL 用户列表
export function getPgsqlUsers(serverId) {
  return request({
    url: `/database/pgsql/${serverId}/users`,
    method: 'get'
  })
}

// 创建 PostgreSQL 用户
export function createPgsqlUser(serverId, data) {
  return request({
    url: `/database/pgsql/${serverId}/users/create`,
    method: 'post',
    data
  })
}

// 删除 PostgreSQL 用户
export function deletePgsqlUser(serverId, data) {
  return request({
    url: `/database/pgsql/${serverId}/users/delete`,
    method: 'post',
    data
  })
}

// 修改 PostgreSQL 用户
export function alterPgsqlUser(serverId, data) {
  return request({
    url: `/database/pgsql/${serverId}/users/alter`,
    method: 'post',
    data
  })
}

// 授予 PostgreSQL 用户权限
export function grantPgsqlPrivileges(serverId, data) {
  return request({
    url: `/database/pgsql/${serverId}/users/grant`,
    method: 'post',
    data
  })
}

// ==================== PostgreSQL 备份管理 ====================

// 获取 PostgreSQL 备份列表
export function getPgsqlBackups(params) {
  return request({
    url: '/database/pgsql/backup/list',
    method: 'get',
    params
  })
}

// 创建 PostgreSQL 备份
export function createPgsqlBackup(serverId, databaseName) {
  return request({
    url: `/database/pgsql/${serverId}/database/${databaseName}/backup/create`,
    method: 'post'
  })
}

// 恢复 PostgreSQL 备份
export function restorePgsqlBackup(backupId) {
  return request({
    url: `/database/pgsql/backup/${backupId}/restore`,
    method: 'post'
  })
}

// 删除 PostgreSQL 备份
export function deletePgsqlBackup(backupId) {
  return request({
    url: `/database/pgsql/backup/${backupId}/delete`,
    method: 'post'
  })
}