import request from '../utils/request'

//获取WAF基本概况
export function getWAFBasicInfo() {
  return request({
    url: '/waf/overview',
    method: 'get'
  })
}

// 获取SSL证书列表
export function getSSLCertList(params) {
  return request({
    url: '/waf/ssl-certs/list',
    method: 'get',
    params
  })
}

// 创建SSL证书
export function createSSLCert(data) {
  return request({
    url: '/waf/ssl-certs/create',
    method: 'post',
    data
  })
}

// 删除SSL证书
export function deleteSSLCert(cert_id) {
  return request({
    url: `/waf/ssl-certs/${cert_id}/delete`,
    method: 'post'
  })
}


// 更新SSL证书
export function updateSSLCert(cert_id, data) {
  return request({
    url: `/waf/ssl-certs/${cert_id}/update`,
    method: 'post',
    data
  })
}

// 获取SSL证书详情
export function getSSLCertDetail(cert_id) {
  return request({
    url: `/waf/ssl-certs/${cert_id}/detail`,
    method: 'get'
  })
}


// 获取WAF容器状态
export function getWAFContainerStatus() {
  return request({
    url: '/waf/waf/status',
    method: 'get'
  })
}

// 操作WAF容器（启动/停止/重启）
export function operateWAFContainer(action) {
  return request({
    url: '/waf/waf/operate',
    method: 'post',
    data: { action }
  })
}

// 检测WAF容器是否存在（是否安装）
export function checkWAFContainerExists() {
  return request({
    url: '/waf/waf/exists',
    method: 'get'
  })
}


// 获取WAF拦截日志
export function getBlockLog(params) {
  return request({
    url: '/waf/logs/list',
    method: 'get',
    params
  })
}

// 清理WAF拦截日志
export function cleanBlockLog(data) {
  return request({
    url: '/waf/logs/clean',
    method: 'post',
    data
  })
}

// 获取WAF BOT验证日志
export function getBotLog(params) {
  return request({
    url: '/waf/logs/bot/list',
    method: 'get',
    params
  })
}


// 清理WAF BOT验证日志
export function cleanBotLog(data) {
  return request({
    url: '/waf/logs/bot/clean',
    method: 'post',
    data
  })
}

// 获取WAF黑白名单日志
export function getBlackWhiteLog(params) {
  return request({
    url: '/waf/logs/blackwhite/list',
    method: 'get',
    params
  })
}

// 清理WAF黑白名单日志
export function cleanBlackWhiteLog(data) {
  return request({
    url: '/waf/logs/blackwhite/clean',
    method: 'post',
    data
  })
}

// 获取WAF黑白名单配置
export function getBlackWhiteList() {
  return request({
    url: '/waf/rules/ipblackwhite/list',
    method: 'get'
  })
}


// 添加WAF黑白名单配置
export function addBlackWhiteGroup(list_type, data) {
  return request({
    url: `/waf/rules/ipblackwhite/${list_type}/add`,
    method: 'post',
    data
  })
}

// 更新WAF黑白名单配置
export function updateBlackWhiteGroup(list_type, group_name, data) {
  return request({
    url: `/waf/rules/ipblackwhite/${list_type}/${group_name}/update`,
    method: 'post',
    data
  })
}

// 删除WAF黑白名单配置
export function deleteBlackWhiteGroup(list_type, group_name) {
  return request({
    url: `/waf/rules/ipblackwhite/${list_type}/${group_name}/delete`,
    method: 'post'
  })
}

//拉黑IP
export function blockIP(data) {
  return request({
    url: `/waf/rules/ipblackwhite/block`,
    method: 'post',
    data
  })
}

//url白名单配置
export function getURLWhiteList() {
  return request({
    url: '/waf/rules/urlwhitelist/list',
    method: 'get'
  })
}

//更新url白名单配置
export function updateURLWhiteList(data) {
  return request({
    url: '/waf/rules/urlwhitelist/update',
    method: 'post',
    data
  })
}

//获取站点列表
export function getSiteList() {
  return request({
    url: '/waf/sites/list',
    method: 'get'
  })
}

// 获取站点日志
export function getSiteLogs(site_name) {
  return request({
    url: `/waf/sites/${site_name}/logs`,
    method: 'get'
  })
}

// 清理站点日志
export function cleanSiteLogs(site_name, data) {
  return request({
    url: `/waf/sites/${site_name}/logs/clear`,
    method: 'post',
    data
  })
}

// 更新站点基本配置
export function updateBasicSiteConfig(site_name, data) {
  return request({
    url: `/waf/sites/${site_name}/basic/update`,
    method: 'post',
    data
  })
}

// 更新站点SSL配置
export function updateSiteSSLConfig(site_name, data) {
  return request({
    url: `/waf/sites/${site_name}/ssl/update`,
    method: 'post',
    data
  })
}

// 更新站点漏洞防护配置
export function updateSiteProtectionConfig(site_name, data) {
  return request({
    url: `/waf/sites/${site_name}/protection/update`,
    method: 'post',
    data
  })
}

// 获取站点配置文件内容
export function getSiteConfig(site_name) {
  return request({
    url: `/waf/sites/${site_name}/config`,
    method: 'get'
  })
}

// 更新站点配置文件内容
export function updateSiteConfig(site_name, data) {
  return request({
    url: `/waf/sites/${site_name}/config/update`,
    method: 'post',
    data
  })
}

// 获取WAF QPS和请求统计
export function getWAFQPS() {
  return request({
    url: '/waf/qps',
    method: 'get'
  })
}

//获取客户端统计和响应状态统计
export function getClientStats() {
  return request({
    url: '/waf/client-stats',
    method: 'get'
  })
}

// 获取大屏配置
export function getBigScreenConfig() {
  return request({
    url: '/waf/bigscreen/config',
    method: 'get'
  })
}


// 更新大屏配置
export function updateBigScreenConfig(data) {
  return request({
    url: '/waf/bigscreen/config/update',
    method: 'post',
    data
  })
}



// 获取WAF HTML页面列表
export function getHtmlPageList() {
  return request({
    url: '/waf/html-pages/list',
    method: 'get'
  })
}

// 更新WAF HTML页面内容
export function updateHtmlPageContent(file_name, data) {
  return request({
    url: `/waf/html-pages/${file_name}/update`,
    method: 'post',
    data
  })
}

// 删除站点
export function deleteSite(site_name) {
  return request({
    url: `/waf/sites/${site_name}/delete`,
    method: 'post'
  })
}

// 创建站点
export function createSite(data) {
  return request({
    url: '/waf/sites/create',
    method: 'post',
    data
  })
}

/// 获取WAF地点统计
export function getLocationStats() {
  return request({
    url: '/waf/location/stats',
    method: 'get'
  })
}


// 获取防护规则配置
export function getProtectionRules() {
  return request({
    url: '/waf/rules/protection',
    method: 'get'
  })
}

// 更新防护规则配置
export function updateProtectionRule(ruleKey, data) {
  return request({
    url: `/waf/rules/protection/${ruleKey}/update`,
    method: 'post',
    data
  })
}

// 获取全局nginx配置
export function getGlobalConfig() {
  return request({
    url: '/waf/nginx/config',
    method: 'get'
  })
}

// 更新全局nginx配置
export function updateGlobalConfig(data) {
  return request({
    url: '/waf/nginx/config/update',
    method: 'post',
    data
  })
}


// 获取威胁情报平台配置
export function getThreatIntelConfig() {
  return request({
    url: '/waf/threat-intel/config',
    method: 'get'
  })
}

// 更新威胁情报平台配置
export function updateThreatIntelConfig(data) {
  return request({
    url: '/waf/threat-intel/config/update',
    method: 'post',
    data
  })
}

// 测试威胁情报平台API Key是否可用
export function testThreatIntelApi(data) {
  return request({
    url: '/waf/threat-intel/test',
    method: 'post',
    data
  })
}

// 同步威胁情报黑名单到WAF
export function syncThreatIntelBlacklist() {
  return request({
    url: '/waf/threat-intel/sync',
    method: 'post'
  })
}

// 综合分析指定IP
export function analyzeThreatIntelIp(data) {
  return request({
    url: '/waf/threat-intel/analyze',
    method: 'post',
    data
  })
}