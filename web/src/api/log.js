import request from '../utils/request'


// 系统日志API
// 获取日志文件列表
export function getLogFiles() {
  return request({
    url: '/logs/files',
    method: 'get'
  })
}

// 获取日志文件内容
export function getLogContent(filename) {
  return request({
    url: `/logs/content/${filename}`,
    method: 'get'
  })
}

// 清理系统日志
export function clearLogs() {
  return request({
    url: '/logs/clear/delete',
    method: 'post'
  })
}

// 清理指定系统日志文件
export function clearLogFile(filename) {
  return request({
    url: `/logs/clear/${filename}/delete`,
    method: 'post'
  })
}


// 导出指定日志文件（触发下载）
export function exportLogFile(filename) {
  return request({
    url: `/logs/export/${filename}`,
    method: 'get',
    responseType: 'blob', // ⚠️ 必须设置，否则文件流会被当作 JSON 解析报错
  })
}


// 登录日志API
// 获取登录日志列表
export function getLoginLogs(params) {
  return request({
    url: '/logs/login',
    method: 'get',
    params
  })
}

// 获取特定用户的登录日志
export function getUserLoginLogs(userId, params) {
  return request({
    url: `/logs/login/user/${userId}`,
    method: 'get',
    params
  })
}

// 获取当前用户的登录日志
export function getMyLoginLogs(params) {
  return request({
    url: '/logs/login/me',
    method: 'get',
    params
  })
}

// 导出登录日志
export function exportLoginLogs(params) {
  return request({
    url: '/logs/login/export',
    method: 'get',
    responseType: 'blob', // ⚠️ 必须设置，否则文件流会被当作 JSON 解析报错
    params
  })
}

// 清理登录日志（仅管理员）
export function clearLoginLogs() {
  return request({
    url: '/logs/login/clear/delete',
    method: 'post'
  })
}



// 访问日志API
// 创建或更新访问日志配置（仅管理员）
export function createAccessLogConfig(data) {
  return request({
    url: '/logs/access-config',
    method: 'post',
    data
  })
}

// 获取访问日志配置列表（仅管理员）
export function getAccessLogConfigs(params) {
  return request({
    url: '/logs/access-config',
    method: 'get',
    params
  })
}

// 获取最新的访问日志配置
export function getLatestAccessLogConfig() {
  return request({
    url: '/logs/access-config/latest',
    method: 'get'
  })
}

// 获取访问日志内容（access.log 或 error.log）
export function getAccessLogContent(params) {
  return request({
    url: '/logs/access-content',
    method: 'get',
    params
  })
}

// 导出访问日志文件（access.log 或 error.log）
export function exportAccessLog(logType) {
  return request({
    url: '/logs/access-export',
    method: 'get',
    params: {
      log_type: logType
    },
    responseType: 'blob' // ⚠️ 必须设置，否则文件流会被当作 JSON 解析报错
  })
}

// 清理访问日志文件（access.log 或 error.log）
export function clearAccessLog(logType) {
  return request({
    url: '/logs/access-clear/delete',
    method: 'post',
    params: {
      log_type: logType
    }
  })
}
