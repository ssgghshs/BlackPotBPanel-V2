<template>
  <div class="login-wrapper">
    <div class="login-container">
      <!-- 左侧插图区域 -->
      <div class="login-illustration">
        <img src="/login.png" alt="Login Illustration" class="illustration-image" />
      </div>
      
      <!-- 右侧登录表单区域 -->
      <div class="login-form-section">
      <!-- 语言切换下拉菜单 -->
      <div class="language-switch">
        <select v-model="currentLocale" @change="onLocaleChange" class="language-select">
          <option value="zh-CN">中文</option>
          <option value="en-US">English</option>
          <option value="zh-TW">繁體中文</option>
          <option value="ja-JP">日本語</option>
          <option value="ko-KR">한국어</option>
        </select>
      </div>
      
      <div class="login-header">
        <h2>{{ t('userLogin') }}</h2>
        <p>{{ t('welcome') }}</p>
      </div>
      
      <!-- 使用 ConfigProvider 包裹表单以支持国际化 -->
      <a-config-provider :locale="locale">
        <a-form :model="loginForm" :rules="rules" ref="formRef" @submit="handleLogin" layout="vertical">
          <a-form-item field="username" :label="t('username')">
            <a-input 
              v-model="loginForm.username" 
              :placeholder="t('enterUsername')" 
              size="large"
              allow-clear
            >
              <template #prefix>
                <icon-user />
              </template>
            </a-input>
          </a-form-item>
          
          <a-form-item field="password" :label="t('password')">
            <a-input-password 
              v-model="loginForm.password" 
              :placeholder="t('enterPassword')" 
              size="large"
              allow-clear
            >
              <template #prefix>
                <icon-lock />
              </template>
            </a-input-password>
          </a-form-item>
          
          <!-- 验证码输入框 -->
          <a-form-item field="captcha" :label="t('captcha')">
            <a-row :gutter="8">
              <a-col :span="16">
                <a-input
                  v-model="loginForm.captcha"
                  :placeholder="t('enterCaptcha')"
                  size="large"
                  allow-clear
                  captcha-input
                >
                  <template #prefix>
                    <icon-safe />
                  </template>
                </a-input>
              </a-col>
              <a-col :span="8">
                <div class="captcha-container" @click="refreshCaptcha">
                  <img 
                    v-if="captchaImage" 
                    :src="captchaImage" 
                    :alt="t('captcha')" 
                    class="captcha-image"
                  />
                  <div v-else class="captcha-placeholder">
                    {{ t('loadingCaptcha') }}
                  </div>
                </div>
              </a-col>
            </a-row>
          </a-form-item>
          
          <a-form-item>
            <a-button 
              type="primary" 
              html-type="submit" 
              :loading="loading" 
              long
              size="large"
            >
              {{ loading ? t('loggingIn') : t('login') }}
            </a-button>
          </a-form-item>
        </a-form>
      </a-config-provider>
      
      <div class="login-footer">
        <p>{{ t('defaultAccount') }}</p>
      </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Notification } from '@arco-design/web-vue'
import { IconUser, IconLock, IconSafe } from '@arco-design/web-vue/es/icon'
import { login, getCaptcha } from '../api/user'  // 使用封装的登录方法
// 引入全局语言状态管理
import { currentLocale, locale, changeLocale, t } from '../utils/locale'
import { fetchCurrentUser } from '../stores/user'
// 引入系统设置API
import { getCommonSettings, updateCommonSettings } from '../api/system'

const router = useRouter()
const loading = ref(false)
const formRef = ref()
const captchaImage = ref('')
const captchaId = ref('')

// 页面加载时获取通用设置并应用
onMounted(async () => {
  try {
    // 首先尝试从后端获取通用设置
    const settingsResponse = await getCommonSettings();
    const { LANGUAGE, THEME, LOGIN_NOTIFY } = settingsResponse;
    
    // 应用语言设置
    if (LANGUAGE) {
      changeLocale(LANGUAGE);
      localStorage.setItem('locale', LANGUAGE);
    }
    
    // 应用主题设置
    if (THEME) {
      if (THEME === 'dark') {
        document.body.setAttribute('arco-theme', 'dark');
      } else {
        document.body.removeAttribute('arco-theme');
      }
      localStorage.setItem('theme', THEME);
    }
  } catch (error) {
    console.error('获取通用设置失败:', error);
    // 出错时从本地存储恢复设置
    const savedLocale = localStorage.getItem('locale');
    if (savedLocale) {
      changeLocale(savedLocale);
    }
    
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
      document.body.setAttribute('arco-theme', 'dark');
    }
  } finally {
    // 无论如何都获取验证码
    refreshCaptcha();
  }
});

// 语言切换处理函数
const onLocaleChange = (event) => {
  const selectedLocale = event.target.value;
  changeLocale(selectedLocale);
  // 只在前端切换语言，不立即调用接口
  console.log('语言在前端已切换:', selectedLocale);
};

// 刷新验证码
const refreshCaptcha = async () => {
  try {
    const response = await getCaptcha();
    captchaId.value = response.captcha_id;
    captchaImage.value = response.captcha_image;
  } catch (error) {
    console.error('获取验证码失败:', error);
    Notification.error(t.value('getCaptchaFailed'));
  }
};

const loginForm = reactive({
  username: '',
  password: '',
  captcha: ''
})

const rules = computed(() => ({
  username: [
    { required: true, message: t.value('enterUsername') }
  ],
  password: [
    { required: true, message: t.value('enterPassword') }
  ],
  captcha: [
    { required: true, message: t.value('enterCaptcha') }
  ]
}))

const handleLogin = async (data) => {
  // 先进行表单验证
  const errors = await formRef.value?.validate().catch(error => {
    // 表单验证失败，直接返回，不执行登录逻辑
    console.log('表单验证失败:', error);
    return false;
  });
  
  // 如果验证失败或者返回了错误，则不继续执行登录逻辑
  if (errors === false || (errors && Object.keys(errors).length > 0)) {
    return;
  }
  
  // 只有表单验证通过后才执行登录逻辑
  loading.value = true
  
  // 使用封装的登录方法
  try {
    const response = await login({
      username: loginForm.username,
      password: loginForm.password,
      captcha: loginForm.captcha
    }, captchaId.value)
    
    // 保存token到localStorage
    const token = response.access_token
    localStorage.setItem('access_token', token)
    
    // 保存是否使用默认密码的标记到localStorage
    if (response.is_default_password) {
      localStorage.setItem('isDefaultPassword', 'true');
    } else {
      localStorage.removeItem('isDefaultPassword');
    }
    
    // 获取当前用户信息
    await fetchCurrentUser()
    
    // 登录成功后，调用updateCommonSettings更新语言设置
    try {
      await updateCommonSettings({ LANGUAGE: currentLocale.value });
      console.log('登录成功后语言设置更新成功:', currentLocale.value);
    } catch (error) {
      console.error('登录成功后更新语言设置失败:', error);
      // 静默失败，不影响用户体验
    }
    
    Notification.success(t.value('loginSuccess'))
    
    // 跳转到首页，并添加登录成功的参数
    router.push('/home?login_success=true')
  } catch (error) {
    console.error('登录失败:', error)
    // 优先使用本地化的错误消息，如果后端返回了具体的错误信息则也显示出来
    const backendMessage = error.response?.data?.detail;
    if (backendMessage) {
      // 将后端错误信息映射到本地化文本
      if (backendMessage.includes('Incorrect username or password')) {
        Notification.error(t.value('loginFailed'))
      } else if (backendMessage.includes('Incorrect captcha')) {
        Notification.error(t.value('captchaIncorrect'))
        // 验证码错误时刷新验证码
        refreshCaptcha();
      } else if (backendMessage.includes('Invalid captcha ID')) {
        Notification.error(t.value('captchaExpired'))
        // 验证码过期时刷新验证码
        refreshCaptcha();
      } else {
        Notification.error(t.value('loginFailed') + ': ' + backendMessage)
      }
    } else {
      Notification.error(t.value('loginFailed'))
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: var(--color-bg-1);
}

.login-container {
  display: flex;
  max-width: 1440px;
  width: 108%;
  margin: 0 auto;
  background: #ffffff;
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  overflow: hidden;
}

/* 左侧插图区域 */
.login-illustration {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary-1) 0%, var(--color-primary-2) 100%);
  padding: 0;
  overflow: hidden;
}

.illustration-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  -webkit-user-drag: none;
  -khtml-user-drag: none;
  -moz-user-drag: none;
  -o-user-drag: none;
  user-drag: none;
}

/* 右侧登录表单区域 */
.login-form-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  position: relative;
  background: #ffffff;
  max-width: 400px;
  margin: 0 auto;
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h2 {
  font-size: 24px;
  color: #333;
  margin-bottom: 10px;
}

.login-header p {
  color: #666;
  font-size: 14px;
}

/* 语言切换按钮定位在右侧区域右上角 */
.language-switch {
  position: absolute;
  top: 20px;
  right: 20px;
}

.login-footer {
  margin-top: 20px;
  text-align: center;
}

.login-footer p {
  color: #999;
  font-size: 12px;
  margin: 0;
}

/* 验证码样式 */
.captcha-container {
  height: 40px;
  cursor: pointer;
  border: 1px solid #ebebeb;
  border-radius: 4px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
}

.captcha-image {
  height: 100%;
  width: 100%;
  object-fit: cover;
}

.captcha-placeholder {
  color: #999;
  font-size: 12px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .login-wrapper {
    padding: 20px;
  }
  
  .login-container {
    flex-direction: column;
    width: 100%;
  }
  
  .login-illustration {
    flex: none;
    height: 30vh;
    padding: 0;
  }
  
  .login-form-section {
    flex: none;
    padding: 20px;
  }
  
  .language-switch {
    top: 10px;
    right: 10px;
  }
}
</style>

<!-- 使用非scoped样式确保所有组件在所有主题下保持一致 -->
<style>
/* 确保登录容器在所有主题下保持白色背景 */
.login-container {
  background: #ffffff !important;
}

/* 确保右侧登录表单区域在所有主题下保持白色背景 */
.login-form-section {
  background: #ffffff !important;
}

/* 确保标题在所有主题下保持黑色文字 */
.login-header h2 {
  color: #333 !important;
}

/* 确保副标题在所有主题下保持灰色文字 */
.login-header p {
  color: #666 !important;
}

/* 确保页脚在所有主题下保持灰色文字 */
.login-footer p {
  color: #999 !important;
}

/* 确保语言切换按钮在所有主题下保持一致样式 */
.language-switch .arco-btn {
  color: #333 !important;
  background-color: #f0f0f0 !important;
  border: 1px solid #e0e0e0 !important;
}

.language-switch .arco-btn:hover {
  background-color: #e0e0e0 !important;
  border: 1px solid #d0d0d0 !important;
}

/* 确保表单标签在所有主题下保持黑色文字 */
.login-form-section .arco-form-item-label {
  color: #333 !important;
}

/* 确保输入框在所有主题下保持白色背景和黑色文字 */
.login-form-section .arco-input-wrapper {
  background-color: #ffffff !important;
  border: 1px solid #ebebeb !important;
  color: #333 !important;
}

.login-form-section .arco-input-wrapper:hover {
  background-color: #ffffff !important;
  border: 1px solid #cccccc !important;
}

.login-form-section .arco-input-wrapper:focus {
  background-color: #ffffff !important;
  border: 1px solid #3c7eff !important;
  box-shadow: 0 0 0 2px rgba(64, 132, 255, 0.2) !important;
}

.login-form-section .arco-input {
  color: #333 !important;
}

.login-form-section .arco-input::placeholder {
  color: #999 !important;
}

/* 确保密码框在所有主题下保持白色背景和黑色文字 */
.login-form-section .arco-input-password {
  background-color: #ffffff !important;
  border: 1px solid #ebebeb !important;
  color: #333 !important;
}

.login-form-section .arco-input-password:hover {
  background-color: #ffffff !important;
  border: 1px solid #cccccc !important;
}

.login-form-section .arco-input-password:focus {
  background-color: #ffffff !important;
  border: 1px solid #3c7eff !important;
  box-shadow: 0 0 0 2px rgba(64, 132, 255, 0.2) !important;
}

.login-form-section .arco-input-password .arco-input {
  color: #333 !important;
}

.login-form-section .arco-input-password .arco-input::placeholder {
  color: #999 !important;
}

/* 确保按钮在所有主题下保持一致样式 */
.login-form-section .arco-btn-primary {
  background-color: #165dff !important;
  border: 1px solid #165dff !important;
  color: #ffffff !important;
}

.login-form-section .arco-btn-primary:hover {
  background-color: #4080ff !important;
  border: 1px solid #4080ff !important;
}

.login-form-section .arco-btn-primary:active {
  background-color: #0e42d2 !important;
  border: 1px solid #0e42d2 !important;
}

/* 自定义语言切换下拉菜单样式 */
.language-switch select {
  padding: 6px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background-color: #ffffff;
  color: #333;
  font-size: 14px;
  cursor: pointer;
}

.language-switch select:hover {
  border-color: #cccccc;
}

.language-switch select:focus {
  outline: none;
  border-color: #3c7eff;
  box-shadow: 0 0 0 2px rgba(64, 132, 255, 0.2);
}

/* 确保深色主题下也不受影响 */
body[arco-theme="dark"] .language-switch select {
  background-color: #ffffff;
  color: #333;
  border-color: #e0e0e0;
}

body[arco-theme="dark"] .language-switch select:hover {
  border-color: #cccccc;
}

body[arco-theme="dark"] .language-switch select:focus {
  border-color: #3c7eff;
  box-shadow: 0 0 0 2px rgba(64, 132, 255, 0.2);
}

/* 确保图标在所有主题下保持黑色 */
.login-form-section .arco-icon {
  color: #333 !important;
}

/* 使用更高级别的选择器确保样式不被覆盖 */
body[arco-theme="dark"] .login-container {
  background: #ffffff !important;
}

body[arco-theme="dark"] .login-form-section {
  background: #ffffff !important;
}

body[arco-theme="dark"] .login-header h2 {
  color: #333 !important;
}

body[arco-theme="dark"] .login-header p {
  color: #666 !important;
}

body[arco-theme="dark"] .login-footer p {
  color: #999 !important;
}

body[arco-theme="dark"] .language-switch .arco-btn {
  color: #333 !important;
  background-color: #f0f0f0 !important;
  border: 1px solid #e0e0e0 !important;
}

body[arco-theme="dark"] .language-switch .arco-btn:hover {
  background-color: #e0e0e0 !important;
  border: 1px solid #d0d0d0 !important;
}

body[arco-theme="dark"] .login-form-section .arco-form-item-label {
  color: #333 !important;
}

body[arco-theme="dark"] .login-form-section .arco-input-wrapper {
  background-color: #ffffff !important;
  border: 1px solid #ebebeb !important;
  color: #333 !important;
}

body[arco-theme="dark"] .login-form-section .arco-input-wrapper:hover {
  background-color: #ffffff !important;
  border: 1px solid #cccccc !important;
}

body[arco-theme="dark"] .login-form-section .arco-input-wrapper:focus {
  background-color: #ffffff !important;
  border: 1px solid #3c7eff !important;
  box-shadow: 0 0 0 2px rgba(64, 132, 255, 0.2) !important;
}

body[arco-theme="dark"] .login-form-section .arco-input {
  color: #333 !important;
}

body[arco-theme="dark"] .login-form-section .arco-input::placeholder {
  color: #999 !important;
}

body[arco-theme="dark"] .login-form-section .arco-input-password {
  background-color: #ffffff !important;
  border: 1px solid #ebebeb !important;
  color: #333 !important;
}

body[arco-theme="dark"] .login-form-section .arco-input-password:hover {
  background-color: #ffffff !important;
  border: 1px solid #cccccc !important;
}

body[arco-theme="dark"] .login-form-section .arco-input-password:focus {
  background-color: #ffffff !important;
  border: 1px solid #3c7eff !important;
  box-shadow: 0 0 0 2px rgba(64, 132, 255, 0.2) !important;
}

body[arco-theme="dark"] .login-form-section .arco-input-password .arco-input {
  color: #333 !important;
}

body[arco-theme="dark"] .login-form-section .arco-input-password .arco-input::placeholder {
  color: #999 !important;
}

body[arco-theme="dark"] .login-form-section .arco-btn-primary {
  background-color: #165dff !important;
  border: 1px solid #165dff !important;
  color: #ffffff !important;
}

body[arco-theme="dark"] .login-form-section .arco-btn-primary:hover {
  background-color: #4080ff !important;
  border: 1px solid #4080ff !important;
}

body[arco-theme="dark"] .login-form-section .arco-btn-primary:active {
  background-color: #0e42d2 !important;
  border: 1px solid #0e42d2 !important;
}

body[arco-theme="dark"] .login-form-section .arco-dropdown {
  background-color: #ffffff !important;
  border: 1px solid #ebebeb !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
}

body[arco-theme="dark"] .login-form-section .arco-dropdown-option {
  color: #333 !important;
}

body[arco-theme="dark"] .login-form-section .arco-dropdown-option:hover {
  background-color: #f0f0f0 !important;
}

body[arco-theme="dark"] .login-form-section .arco-icon {
  color: #333 !important;
}

/* 确保验证码输入框和显示框高度一致 */
.login-form-section .arco-input-wrapper[captcha-input] {
  height: 40px !important;
}

.login-form-section .arco-input[captcha-input] {
  height: 38px !important;
}

/* 确保深色主题下验证码容器也保持一致 */
body[arco-theme="dark"] .login-form-section .arco-input-wrapper[captcha-input] {
  height: 40px !important;
}

body[arco-theme="dark"] .login-form-section .arco-input[captcha-input] {
  height: 38px !important;
}
</style>