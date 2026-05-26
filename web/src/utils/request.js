import axios from 'axios'

// 创建 axios 实例
const service = axios.create({
  baseURL: '/api/v2', // 根据项目规范，设置为本地开发环境地址
  timeout: 600000, // 增加超时时间到10分钟，以适应大文件上传
  maxBodyLength: 1024 * 1024 * 1024, // 允许1GB的请求体大小
  headers: {
    // 避免设置content-type，让浏览器自动处理multipart/form-data格式
  }
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    // 从 localStorage 获取 token
    const token = localStorage.getItem('access_token')
    if (token) {
      // 在请求头中添加 Authorization 字段
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    console.log('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  response => {
    // 对响应数据做处理
    return response.data
  },
  error => {
    console.log('响应错误:', error)
    // 如果是 401 错误，清除 token 并跳转到登录页
    // 但要避免在登录页面本身造成无限重定向
    if (error.response && error.response.status === 401) {
      // 检查当前是否已经在登录页面
      if (window.location.pathname !== '/login' && window.location.pathname !== '/Login') {
        localStorage.removeItem('access_token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default service
