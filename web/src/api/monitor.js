// 监控模块API
import request from '../utils/request';

// 获取主机详细信息
export function getHostInfo() {
  return request('/monitor/host-info', {
    method: 'GET'
  }); 
}

// 获取系统信息（CPU使用率、内存使用率、硬盘使用率、负载）
export function getSystemInfo() {
  return request('/monitor/system-info', {
    method: 'GET'
  });
}

// 获取网络流量监控信息
export function getNetworkTraffic() {
  return request('/monitor/network-traffic', {
    method: 'GET'
  });
}

// 获取磁盘I/O监控信息
export function getDiskIO() {
  return request('/monitor/disk-io', {
    method: 'GET'
  });
}

// 获取面板资源占用
export function getPanelResource() {
  return request('/monitor/panel-resource', {
    method: 'GET'
  });
}