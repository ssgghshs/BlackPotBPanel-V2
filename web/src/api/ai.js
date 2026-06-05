import request from '../utils/request'

// ==================== AI 模型配置管理 ====================

// 获取 AI 模型列表
export function getAiModelList(params) {
  return request({
    url: '/ai/models/list',
    method: 'get',
    params
  })
}

// 获取单个 AI 模型详情
export function getAiModel(id) {
  return request({
    url: `/ai/models/${id}`,
    method: 'get'
  })
}

// 创建 AI 模型
export function createAiModel(data) {
  return request({
    url: '/ai/models/create',
    method: 'post',
    data
  })
}

// 更新 AI 模型
export function updateAiModel(id, data) {
  return request({
    url: `/ai/models/${id}/update`,
    method: 'post',
    data
  })
}

// 删除 AI 模型
export function deleteAiModel(id) {
  return request({
    url: `/ai/models/${id}/delete`,
    method: 'post'
  })
}

// 发现模型（通过 OpenAI 兼容 API）
export function discoverAiModels(data) {
  return request({
    url: '/ai/models/discover',
    method: 'post',
    data
  })
}

// ==================== AI 对话管理 ====================

// 获取对话列表
export function getAiConversations(params) {
  return request({
    url: '/ai/conversations/list',
    method: 'get',
    params
  })
}

// 获取单个对话详情
export function getAiConversation(id) {
  return request({
    url: `/ai/conversations/${id}`,
    method: 'get'
  })
}

// 创建对话
export function createAiConversation(data) {
  return request({
    url: '/ai/conversations/create',
    method: 'post',
    data
  })
}

// 更新对话
export function updateAiConversation(id, data) {
  return request({
    url: `/ai/conversations/${id}/update`,
    method: 'post',
    data
  })
}

// 切换对话使用的模型
export function switchAiConversationModel(id, data) {
  return request({
    url: `/ai/conversations/${id}/switch-model`,
    method: 'post',
    data
  })
}

// 删除对话
export function deleteAiConversation(id) {
  return request({
    url: `/ai/conversations/${id}/delete`,
    method: 'post'
  })
}

// 获取对话消息
export function getAiMessages(conversationId, params) {
  return request({
    url: `/ai/conversations/${conversationId}/messages`,
    method: 'get',
    params
  })
}

// 删除单条消息
export function deleteAiMessage(conversationId, messageId) {
  return request({
    url: `/ai/conversations/${conversationId}/messages/${messageId}/delete`,
    method: 'post'
  })
}

// ==================== AI 流式聊天 ====================

// 流式聊天（SSE），返回 Response 对象供前端读取 ReadableStream
export function streamChatWithAi(data, signal) {
  const token = localStorage.getItem('access_token')
  return fetch('/api/v2/ai/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : ''
    },
    body: JSON.stringify(data),
    signal
  })
}


// ==================== AI 工具确认 ====================

// 确认/拒绝高风险工具执行
export function confirmAiTool(data) {
  return request({
    url: '/ai/chat/confirm',
    method: 'post',
    data
  })
}

// ==================== AI 工具集 ====================

// 获取可用工具集列表
export function getAiToolsets() {
  return request({
    url: '/ai/tools/toolsets',
    method: 'get'
  })
}


// ==================== AI 文件上传 ====================

// 上传文件供 AI 对话使用
export function uploadAiFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/ai/upload',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}


// ==================== AI 用量统计 ====================

// 获取用量统计
export function getAiUsage(params) {
  return request({
    url: '/ai/usage',
    method: 'get',
    params
  })
}

// 导出用量数据
export function exportAiUsage(params) {
  return request({
    url: '/ai/usage/export',
    method: 'get',
    params
  })
}

// 重置用量
export function resetAiUsage() {
  return request({
    url: '/ai/usage/reset',
    method: 'post'
  })
}
