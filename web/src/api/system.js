import request from '../utils/request'

// 获取环境配置
export function getEnvConfig() {
  return request({
    url: '/system/config',
    method: 'get'
  })
}

// 更新环境配置
export function updateEnvConfig(data) {
  return request({
    url: '/system/config/update',
    method: 'post',
    data
  })
}

// 获取通用设置
export function getCommonSettings() {
  return request({
    url: '/system/config/common',
    method: 'get'
  })
}

// 更新通用设置
export function updateCommonSettings(data) {
  return request({
    url: '/system/config/common/update',
    method: 'post',
    data
  })
}


// 重启服务
export function restartService() {
  return request({
    url: '/system/restart',
    method: 'post'
  })
}

// 获取SSL证书内容
export function getSSLCert() {
  return request({
    url: '/system/config/ssl',
    method: 'get'
  })
}

// 更新SSL证书内容
export function updateSSLCert(data) {
  return request({
    url: '/system/config/ssl/update',
    method: 'post',
    data
  })
}
