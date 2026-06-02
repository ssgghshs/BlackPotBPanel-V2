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

// 生成 API 密钥
export function generateApiKey() {
  return request({
    url: '/system/config/api/generate-key',
    method: 'post'
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

// 获取系统设置
export function getSystemSettings() {
  return request({
    url: '/system/settings',
    method: 'get'
  })
}

// 设置DNS
export function setDNS(data) {
  return request({
    url: '/system/dns/set',
    method: 'post',
    data
  })
}

// 测试DNS
export function testDNS(data) {
  return request({
    url: '/system/dns/test',
    method: 'post',
    data
  })
}

// 设置Swap
export function setSwap(data) {
  return request({
    url: '/system/swap/set',
    method: 'post',
    data
  })
}

// 设置时区
export function setTimezone(data) {
  return request({
    url: '/system/timezone/set',
    method: 'post',
    data
  })
}

// 同步时间
export function syncTime() {
  return request({
    url: '/system/time/sync',
    method: 'post'
  })
}

// 修改系统密码
export function setSystemPassword(data) {
  return request({
    url: '/system/password',
    method: 'post',
    data
  })
}

// 创建内存盘
export function createMemoryDisk(data) {
  return request({
    url: '/system/memory-disk',
    method: 'post',
    data
  })
}

// 删除内存盘
export function deleteMemoryDisk(data) {
  return request({
    url: '/system/memory-disk/delete',
    method: 'post',
    data
  })
}

// 添加/修改Hosts
export function addHosts(data) {
  return request({
    url: '/system/hosts',
    method: 'post',
    data
  })
}

// 删除Hosts
export function deleteHosts(data) {
  return request({
    url: '/system/hosts/delete',
    method: 'post',
    data
  })
}

// 暂停/启用Hosts
export function toggleHosts(data) {
  return request({
    url: '/system/hosts/toggle',
    method: 'post',
    data
  })
}



