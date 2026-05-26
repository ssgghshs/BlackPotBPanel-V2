import request from '../utils/request'

// Firewall API

// 获取防火墙统计信息
export function firewallInfoGet() {
    return request({
        url: '/firewall/info',
        method: 'get'
    })
}

// 设置防火墙状态
export function firewallStatusSet(status) {
    return request({
        url: '/firewall/status/set',
        method: 'post',
        data: { status }
    })
}

// 设置禁Ping（0=允许, 1=禁止）
export function firewallSetPing(status) {
    return request({ 
        url: '/firewall/ping/set', 
        method: 'post', 
        data: { status } 
    })
}

// 获取端口规则列表
export function firewallGetPortRules(params) {
    return request({ 
        url: '/firewall/port_rules/list', 
        method: 'get', 
        params 
    })
}

// 添加端口规则
export function firewallAddPortRule(data) {
    return request({ 
        url: '/firewall/port_rules/create', 
        method: 'post', 
        data 
    })
}

// 删除端口规则（支持系统规则 id=0）
export function firewallDeletePortRule(data) {
    return request({ 
        url: '/firewall/port_rules/delete', 
        method: 'post',
        data
    })
}

// 修改端口规则
export function firewallUpdatePortRule(id, data) {
    return request({
        url: `/firewall/port_rules/${id}/update`,
        method: 'post',
        data
    })
}

// 获取IP规则列表
export function firewallGetIpRules(params) {
    return request({ 
        url: '/firewall/ip_rules/list', 
        method: 'get', 
        params 
    })
}

// 添加IP规则
export function firewallAddIpRule(data) {
    return request({ 
        url: '/firewall/ip_rules/create', 
        method: 'post', 
        data 
    })
}

// 删除IP规则（支持系统规则 id=0）
export function firewallDeleteIpRule(data) {
    return request({ 
        url: '/firewall/ip_rules/delete', 
        method: 'post',
        data
    })
}

// 修改IP规则
export function firewallUpdateIpRule(id, data) {
    return request({
        url: `/firewall/ip_rules/${id}/update`,
        method: 'post',
        data
    })
}

// 获取端口转发规则列表
export function firewallGetForwards(params) {
    return request({ 
        url: '/firewall/forwards/list', 
        method: 'get', 
        params 
    })
}

// 添加端口转发规则
export function firewallAddForward(data) {
  return request({ 
        url: '/firewall/forwards/create', 
        method: 'post', 
        data 
    })
}

// 删除端口转发规则
export function firewallDeleteForward(id) {
    return request({ 
        url: `/firewall/forwards/${id}/delete`, 
        method: 'post' 
    })
}

// 修改端口转发规则
export function firewallUpdateForward(id, data) {
    return request({
        url: `/firewall/forwards/${id}/update`,
        method: 'post',
        data
    })
}


// 获取可用国家列表
export function firewallGetCountries() {
    return request({
        url: '/firewall/country_rules/countries',
        method: 'get'
    })
}

// 获取地区规则列表
export function firewallGetCountryRules(params) {
    return request({
        url: '/firewall/country_rules/list',
        method: 'get',
        params
    })
}

// 添加地区规则
export function firewallAddCountryRule(data) {
    return request({
        url: '/firewall/country_rules/create',
        method: 'post',
        data
    })
}

// 删除地区规则
export function firewallDeleteCountryRule(data) {
    return request({
        url: '/firewall/country_rules/delete',
        method: 'post',
        data
    })
}

// 批量删除地区规则
export function firewallBatchDeleteCountryRules(data) {
    return request({
        url: '/firewall/country_rules/batch_delete',
        method: 'post',
        data
    })
}

// 修改地区规则
export function firewallUpdateCountryRule(id, data) {
    return request({
        url: `/firewall/country_rules/${id}/update`,
        method: 'post',
        data
    })
}

// 进程相关API

// 获取进程列表
export function processesGet(params) {
    return request({
        url: '/service/processes',
        method: 'get',
        params
    })
}

// 获取进程详情
export function processGetDetail(pid) {
    return request({
        url: `/service/process/${pid}`,
        method: 'get'
    })
}

// 终止进程
export function processTerminate(pid) {
    return request({
        url: `/service/process/${pid}/terminate`,
        method: 'post'
    })
}

// 获取网络连接列表
export function networkGetConnections(params) {
    return request({
        url: '/service/network/connections',
        method: 'get',
        params
    })
}

// 获取系统信息，包括DNS地址、内存信息、Swap信息、时区、当前时间和主机名
export function systemInfoGet() {
    return request({
        url: '/service/info',
        method: 'get'
    })
}
