// 主机管理API
import request from '../utils/request'

// 获取主机列表
export function getHosts(params) {
  return request('/host/list', {
    method: 'GET',
    params,
  })
}

// 获取文件传输专用主机列表（简化版）
export function getFileTransferHosts() {
  return request('/host/transferhosts', {
    method: 'GET',
  })
}

// 创建主机
export function createHost(data) {
  return request('/host/create', {
    method: 'POST',
    data,
  })
}

// 获取主机详情
export function getHost(id) {
  return request(`/host/${id}/detail`, {
    method: 'GET',
  })
}

// 更新主机
export function updateHost(id, data) {
  return request(`/host/${id}/update`, {
    method: 'POST',
    data,
  })
}

// 删除主机
export function deleteHost(id) {
  return request(`/host/${id}/delete`, {
    method: 'POST',
  })
}

// 检测主机状态
export function checkHostStatus(id) {
  return request(`/host/${id}/status`, {
    method: 'GET',
  })
}

// 测试SSH连接
export function testSSHConnection(id) {
  return request(`/host/${id}/ssh_test`, {
    method: 'POST',
  })
}

// 生成终端连接令牌
export function generateTerminalToken(id) {
  return request(`/host/${id}/terminal_token`, {
    method: 'POST',
  })
}

// 连接本机SSH
export function connectLocalhostSSH() {
  return request('/host/connect_localhost', {
    method: 'POST',
  })
}

// 建立WebSocket终端连接（开发）
// export function connectTerminal(hostId, token) {
//   // 获取当前的baseURL（去除http/https前缀）
//   const baseURL = request.defaults.baseURL || 'http://localhost:8000';
//   // 确定使用ws还是wss协议
//   let protocol = 'ws';
//   let hostURL = baseURL.replace(/^(https?:\/\/)/, '');
  
//   // 如果当前页面是HTTPS，则使用WSS协议
//   if (window.location.protocol === 'https:') {
//     protocol = 'wss';
//   } else if (baseURL.startsWith('https')) {
//     protocol = 'wss';
//   }
  
//   // 如果baseURL包含端口，需要正确处理
//   const url = `${protocol}://${hostURL}/host/ws/terminal/${hostId}?token=${encodeURIComponent(token)}`;
  
//   // 创建WebSocket连接
//   return new WebSocket(url);
// }

// 建立WebSocket终端连接（生产）
export function connectTerminal(hostId, token) {
  // 根据当前页面协议确定WebSocket协议
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  
  // 构建相对于当前页面的WebSocket URL
  const basePath = window.location.host; // 获取当前域名和端口
  const url = `${protocol}//${basePath}/api/v2/host/ws/terminal/${hostId}?token=${encodeURIComponent(token)}`;
  
  // 创建WebSocket连接
  return new WebSocket(url);
}



// HostCommand 相关的 API 接口
// 创建主机命令
export function createHostCommand(data) {
  return request('/host/commands/create', {
    method: 'POST',
    data,
  })
}

// 获取主机命令列表
export function getHostCommands(params) {
  return request('/host/commands/list', {
    method: 'GET',
    params,
  })
}

// 获取主机命令详情
export function getHostCommand(id) {
  return request(`/host/commands/${id}/detail`, {
    method: 'GET',
  })
}

// 更新主机命令
export function updateHostCommand(id, data) {
  return request(`/host/commands/${id}/update`, {
    method: 'POST',
    data,
  })
}

// 删除主机命令
export function deleteHostCommand(id) {
  return request(`/host/commands/${id}/delete`, {
    method: 'POST',
  })
}

// 获取本机SSH配置信息
export function getLocalSSHConfig() {
  return request('/host/ssh/config', {
    method: 'GET',
  })
}


// 更新SSH配置参数
export function updateSSHConfig(data) {
  return request('/host/ssh/config/update', {
    method: 'POST',
    data,
  })
}


// 操作本机SSH服务
export function operateLocalSSHService(data) {
  return request('/host/ssh/set', {
    method: 'POST',
    data,
  })
}

// 获取SSH配置文件内容
export function getSSHConfigContent() {
  return request('/host/ssh/config/file', {
    method: 'GET',
  })
}

// 获取SSH authorized_keys文件内容
export function getAuthorizedKeysContent() {
  return request('/host/ssh/authkeys/file', {
    method: 'GET',
  })
}


// 获取SSH登录日志列表
export function getSSHLoginLogs(data) {
  return request('/host/ssh/log', {
    method: 'POST',
    data,
  })
}

// 清理SSH登录日志
export function cleanSSHLoginLogs() {
  return request('/host/ssh/log/cleanup', {
    method: 'POST',
  })
}

// 导出SSH登录日志
export function exportSSHLoginLogs(data) {
  return request('/host/ssh/log/export', {
    method: 'POST',
    data,
  })
}


//获取远程主机文件列表（通过SSH）
export function getRemoteFileList(hostId, params) {
  return request(`/host/${hostId}/files/list`, {
    method: 'GET',
    params,
  })
}

//在远程主机上创建文件或文件夹（通过SSH）
export function createRemoteFile(hostId, data) {
  return request(`/host/${hostId}/files/create`, {
    method: 'POST',
    data,
  })
}

//上传文件到远程主机（通过SFTP）
export function uploadFileToRemote(hostId, formData, params) {
  return request(`/host/${hostId}/files/upload`, {
    method: 'POST',
    data: formData,
    params,
  })
}

// 删除远程主机文件/文件夹（通过SSH）
export function deleteRemoteFile(hostId, data) {
  return request(`/host/${hostId}/files/delete`, {
    method: 'POST',
    data,
  })
}

//启动 SCP 文件传输任务，支持双向传输
export function startSCPTransfer(hostId, data) {
  return request(`/host/${hostId}/files/scp-transfer`, {
    method: 'POST',
    data,
  })
}

//取消 SCP 传输任务
export function cancelSCPTransfer(taskId) {
  return request(`/host/scp-transfer/${taskId}/cancel`, {
    method: 'POST',
  })
}


//WebSocket 实时传输进度
export function connectSCPProgress(task_id) {
  // 根据当前页面协议确定WebSocket协议
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  
  // 构建相对于当前页面的WebSocket URL
  const basePath = window.location.host; // 获取当前域名和端口
  const url = `${protocol}//${basePath}/api/v2/host/ws/scp-progress/${task_id}`;
  
  // 创建WebSocket连接
  return new WebSocket(url);
}






