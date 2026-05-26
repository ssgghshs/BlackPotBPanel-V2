import { ref } from 'vue'

// 全局加载状态
export const isLoading = ref(false)

// 显示加载动画
export const showLoading = () => {
  isLoading.value = true
}

// 隐藏加载动画
export const hideLoading = () => {
  isLoading.value = false
}

// 全局加载计数器（用于多个并发请求）
let loadingCount = 0

// 开始全局加载
export const startGlobalLoading = () => {
  if (loadingCount === 0) {
    showLoading()
  }
  loadingCount++
}

// 结束全局加载
export const endGlobalLoading = () => {
  if (loadingCount > 0) {
    loadingCount--
    if (loadingCount === 0) {
      hideLoading()
    }
  }
}