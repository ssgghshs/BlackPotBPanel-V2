import request from '../utils/request'

// 创建用户
export function createUser(data) {
  return request({
    url: '/users/create',
    method: 'post',
    data
  })
}

// 获取验证码
export function getCaptcha() {
  return request({
    url: '/users/captcha',
    method: 'get'
  })
}

// 用户登录
export function login(data, captchaId) {
  return request({
    url: '/users/login',
    method: 'post',
    data,
    headers: {
      'captcha-id': captchaId
    }
  })
}

// 用户退出登录
export function logout() {
  return request({
    url: '/users/logout',
    method: 'post'
  })
}

// 获取当前用户信息
export function getCurrentUser() {
  return request({
    url: '/users/me',
    method: 'get'
  })
}

// 更新当前用户信息
export function updateCurrentUser(data) {
  return request({
    url: '/users/me/update',
    method: 'post',
    data
  })
}

// 获取用户列表（需要管理员权限）
export function getUserList(params) {
  return request({
    url: '/users/list',
    method: 'get',
    params
  })
}

// 获取指定用户信息
export function getUserById(id) {
  return request({
    url: `/users/${id}/detail`,
    method: 'get'
  })
}



// 修改当前用户密码
export function changePassword(data) {
  return request({
    url: '/users/me/password',
    method: 'post',
    data
  })
}

// 修改指定用户信息（需要管理员权限）
export function updateUser(id, data) {
  return request({
    url: `/users/${id}/update`,
    method: 'post',
    data
  })
}

// 删除用户
export function deleteUser(id) {
  return request({
    url: `/users/${id}/delete`,
    method: 'post'
  })
}