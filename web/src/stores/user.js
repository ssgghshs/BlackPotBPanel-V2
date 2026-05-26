import { ref } from 'vue'
import { getCurrentUser } from '../api/user'

// 创建响应式的用户状态
export const currentUser = ref(null)
export const isAdmin = ref(false)

// 获取当前用户信息
export const fetchCurrentUser = async () => {
  try {
    const user = await getCurrentUser()
    currentUser.value = user
    // 判断是否为管理员（角色为admin）
    isAdmin.value = user && user.role === 'admin'
    return user
  } catch (error) {
    console.error('获取当前用户信息失败:', error)
    currentUser.value = null
    isAdmin.value = false
    return null
  }
}

// 清除用户信息
export const clearUser = () => {
  currentUser.value = null
  isAdmin.value = false
}

// 判断用户是否为审计员
export const isAuditor = () => {
  return currentUser.value && currentUser.value.role === 'auditor'
}

// 判断用户是否为操作员
export const isOperator = () => {
  return currentUser.value && currentUser.value.role === 'operator'
}

// 判断用户是否具有特定角色
export const hasRole = (role) => {
  return currentUser.value && currentUser.value.role === role
}

// 获取用户角色
export const getUserRole = () => {
  return currentUser.value ? currentUser.value.role : null
}