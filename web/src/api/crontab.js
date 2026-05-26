import request from '../utils/request'

// 获取计划任务周期类型列表
export function getCrontabTypes() {
  return request({
    url: '/crontab/types',
    method: 'get'
  })
}

// 获取计划任务列表
export function getCrontabList(params) {
  return request({
    url: '/crontab/list',
    method: 'get',
    params
  })
}

// 获取单个计划任务详情
export function getCrontabTask(id) {
  return request({
    url: `/crontab/${id}`,
    method: 'get'
  })
}

// 创建计划任务
export function createCrontabTask(data) {
  return request({
    url: '/crontab/create',
    method: 'post',
    data
  })
}

// 更新计划任务
export function updateCrontabTask(id, data) {
  return request({
    url: `/crontab/${id}/update`,
    method: 'post',
    data
  })
}

// 删除计划任务
export function deleteCrontabTask(id) {
  return request({
    url: `/crontab/${id}/delete`,
    method: 'post'
  })
}

// 切换计划任务状态
export function toggleCrontabTask(id) {
  return request({
    url: `/crontab/${id}/toggle`,
    method: 'post'
  })
}

// 立即执行计划任务
export function runCrontabTaskNow(id) {
  return request({
    url: `/crontab/${id}/run`,
    method: 'post'
  })
}

// 获取计划任务执行日志
export function getCrontabTaskLog(id, lines = 100) {
  return request({
    url: `/crontab/${id}/log`,
    method: 'get',
    params: { lines }
  })
}

// 清空计划任务执行日志
export function clearCrontabTaskLog(id) {
  return request({
    url: `/crontab/${id}/log/clear`,
    method: 'post'
  })
}
