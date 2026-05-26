import request from '../utils/request';

// 获取脚本列表
export function getScriptList(params) {
  return request('/script/list', {
    method: 'GET',
    params,
  });
}


// 创建脚本
export function createScript(data) {
  return request('/script/create', {
    method: 'POST',
    data,
  });
}

// 更新脚本
export function updateScript(scriptId, data) {
  return request(`/script/scripts/${scriptId}/update`, {
    method: 'POST',
    data,
  });
}

// 删除脚本
export function deleteScript(scriptId) {
  return request(`/script/scripts/${scriptId}/delete`, {
    method: 'POST',
  });
}


// 获取脚本解释器列表
export function getScriptTypeList() {
  return request('/script/script-types/list', {
    method: 'GET',
  });
}


// 创建脚本解释器
export function createScriptType(data) {
  return request('/script/script-types/create', {
    method: 'POST',
    data,
  });
}

// 更新脚本解释器
export function updateScriptType(scriptTypeId, data) {
  return request(`/script/script-types/${scriptTypeId}/update`, {
    method: 'POST',
    data,
  });
}

// 删除脚本解释器
export function deleteScriptType(scriptTypeId) {
  return request(`/script/script-types/${scriptTypeId}/delete`, {
    method: 'POST',
  });
}




// 建立WebSocket连接用于实时脚本执行（开发）
// export function connectScriptExecutionWebSocket(executionId) {
//   // 获取当前的baseURL
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
  
//   // 构建WebSocket URL
//   const url = `${protocol}://${hostURL}/script/execute/ws/${executionId}`;
  
//   // 创建WebSocket连接
//   return new WebSocket(url);
// }

// 建立WebSocket连接用于实时脚本执行（生产）
export function connectScriptExecutionWebSocket(executionId) {
  // 根据当前页面协议确定WebSocket协议
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  
  // 构建相对于当前页面的WebSocket URL
  const basePath = window.location.host; // 获取当前域名和端口
  const url = `${protocol}//${basePath}/api/v2/script/execute/ws/${executionId}`;
  
  // 创建WebSocket连接
  return new WebSocket(url);
}




