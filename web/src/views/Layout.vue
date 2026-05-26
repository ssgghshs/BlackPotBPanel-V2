<template>
  <div class="layout-container">
    <!-- 移动端菜单切换按钮 -->
    <div v-if="isMobile" class="mobile-menu-toggle" @click="toggleMobileMenu">
      <icon-menu />
    </div>
    
    <!-- 侧边栏导航 -->
    <div 
      class="layout-sider" 
      :style="{ width: siderWidth + 'px' }"
      :class="{ 'mobile-overlay': isMobile }"
    >
      <div class="sider-header">
        <!-- 预留区域 -->
        <div class="logo-container" :class="{ 'collapsed': isMenuCollapsed }">
          <img src="/favicon.ico" alt="Logo" class="logo-image" />
        </div>
      </div>
      <NavigationMenu @collapse="onMenuCollapse" @close="toggleMobileMenu" />
    </div>
    
    <!-- 主内容区域 -->
    <div class="layout-content">
      <!-- 页面内容 -->
      <div class="layout-main">
        <router-view />
      </div>
    </div>
    
    <!-- 登录成功提示框 -->
    <div v-if="showLoginSuccessNotification && isLoginNotificationEnabled" class="login-success-notification">
      <div class="notification-content">
        <icon-check-circle-fill class="success-icon" />
        <div class="notification-text">
          <div class="notification-title">{{ t('loginSuccess') }}</div>
          <div class="notification-message">{{ t('welcome') }}, {{ username }}!</div>
          <div class="notification-details">
            <div class="notification-detail-item">
              <span class="detail-label">{{ t('loginTime') }}:</span>
              <span class="detail-value">{{ loginTime }}</span>
            </div>
            <div v-if="ipAddress" class="notification-detail-item">
              <span class="detail-label">{{ t('ipAddress') }}:</span>
              <span class="detail-value">{{ ipAddress }}</span>
            </div>
            <div v-if="location" class="notification-detail-item">
              <span class="detail-label">{{ t('location') }}:</span>
              <span class="detail-value">{{ location }}</span>
            </div>
          </div>
        </div>
        <icon-close class="close-icon" @click="closeNotification" />
      </div>
    </div>
    
    <!-- 移动端遮罩层 -->
    <div 
      v-if="isMobile && isMobileMenuOpen" 
      class="mobile-overlay-mask" 
      @click="toggleMobileMenu"
    ></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import NavigationMenu from '../components/NavigationMenu.vue';
import { IconMenu, IconCheckCircleFill, IconClose } from '@arco-design/web-vue/es/icon';
import { t } from '../utils/locale';
import { getCurrentUser } from '../api/user';
import { getMyLoginLogs } from '../api/log';

const siderWidth = ref(200);
const isMenuCollapsed = ref(false);
const isMobile = ref(false);
const isMobileMenuOpen = ref(false);
const showLoginSuccessNotification = ref(false);
const username = ref('');
const loginTime = ref('');
const ipAddress = ref(''); // 添加IP地址
const location = ref(''); // 添加地理位置
const isLoginNotificationEnabled = ref(true); // 默认开启登录提示

// 检查是否为移动端设备
const checkIsMobile = () => {
  const mobileBreakpoint = 768;
  isMobile.value = window.innerWidth <= mobileBreakpoint;
  
  // 移动端默认收起侧边栏
  if (isMobile.value) {
    isMenuCollapsed.value = true;
    siderWidth.value = 0; // 移动端初始隐藏侧边栏
  } else {
    isMenuCollapsed.value = false;
    siderWidth.value = 200;
  }
};

const onMenuCollapse = (collapsed) => {
  isMenuCollapsed.value = collapsed;
  if (isMobile.value) {
    siderWidth.value = collapsed ? 0 : 200;
  } else {
    siderWidth.value = collapsed ? 90 : 200;
  }
};

// 移动端菜单切换
const toggleMobileMenu = () => {
  isMobileMenuOpen.value = !isMobileMenuOpen.value;
  siderWidth.value = isMobileMenuOpen.value ? 200 : 0;
};

// 窗口大小改变时重新检测
const handleResize = () => {
  checkIsMobile();
  // 如果从移动端切换到桌面端，重置菜单状态
  if (!isMobile.value) {
    isMobileMenuOpen.value = false;
  }
};

// 获取用户信息
const fetchUserInfo = async () => {
  try {
    console.log('开始获取用户信息');
    const response = await getCurrentUser();
    console.log('用户信息响应:', response);
    const userData = response?.data || response;
    username.value = userData?.username || userData?.name || 'User';
    console.log('获取到的用户名:', username.value);
  } catch (error) {
    console.error('获取用户信息失败:', error);
    username.value = 'User';
  }
};

// 获取最近的登录日志
const fetchRecentLoginLog = async () => {
  try {
    console.log('开始获取登录日志');
    const response = await getMyLoginLogs({ limit: 1 });
    console.log('登录日志响应:', response);
    const loginLogs = Array.isArray(response) ? response : (response.data || []);
    if (loginLogs.length > 0) {
      const latestLogin = loginLogs[0];
      console.log('最新的登录记录:', latestLogin);
      // 格式化登录时间
      const date = new Date(latestLogin.login_time);
      loginTime.value = date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      });
      
      // 设置IP地址和地理位置
      ipAddress.value = latestLogin.ip_address || '';
      location.value = latestLogin.location || '';
    } else {
      // 如果没有登录日志，使用当前时间
      console.log('没有登录日志，使用当前时间');
      const now = new Date();
      loginTime.value = now.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      });
    }
    console.log('格式化后的登录时间:', loginTime.value);
  } catch (error) {
    console.error('获取登录日志失败:', error);
    // 如果获取失败，使用当前时间
    const now = new Date();
    loginTime.value = now.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  }
};

// 显示登录成功提示
const showLoginSuccessNotificationFunc = async () => {
  console.log('检查是否需要显示登录成功提示');
  // 检查URL参数，如果有login_success=true则显示提示
  const urlParams = new URLSearchParams(window.location.search);
  const loginSuccess = urlParams.get('login_success');
  
  // 检查登录提示是否启用
  const loginNotificationSetting = localStorage.getItem('loginNotification');
  isLoginNotificationEnabled.value = loginNotificationSetting !== 'false'; // 默认为true，除非明确设置为false
  
  // 也检查sessionStorage中的标记
  const hasShown = sessionStorage.getItem('loginSuccessNotificationShown');
  console.log('URL参数login_success:', loginSuccess);
  console.log('sessionStorage标记:', hasShown);
  console.log('登录提示是否启用:', isLoginNotificationEnabled.value);
  
  // 如果URL参数为true或者sessionStorage中没有标记，并且登录提示已启用，则显示提示
  if ((loginSuccess === 'true' || !hasShown) && isLoginNotificationEnabled.value) {
    console.log('准备显示登录成功提示');
    await fetchUserInfo();
    await fetchRecentLoginLog();
    showLoginSuccessNotification.value = true;
    // 设置sessionStorage标记
    sessionStorage.setItem('loginSuccessNotificationShown', 'true');
    console.log('已设置sessionStorage标记');
    
    // 5秒后自动关闭提示
    setTimeout(() => {
      showLoginSuccessNotification.value = false;
    }, 5000);
  } else {
    console.log('不显示登录成功提示：已显示过或URL参数不匹配或登录提示未启用');
  }
};

// 强制显示登录成功提示（用于调试）
const forceShowLoginSuccessNotification = async () => {
  console.log('强制显示登录成功提示');
  // 检查登录提示是否启用
  const loginNotificationSetting = localStorage.getItem('loginNotification');
  isLoginNotificationEnabled.value = loginNotificationSetting !== 'false';
  
  if (isLoginNotificationEnabled.value) {
    await fetchUserInfo();
    await fetchRecentLoginLog();
    showLoginSuccessNotification.value = true;
    // 注意：这里不清除sessionStorage标记，以免影响正常流程
  }
};

// 关闭提示框
const closeNotification = () => {
  console.log('用户关闭了登录成功提示');
  showLoginSuccessNotification.value = false;
};

// 提供一个方法供其他组件调用以显示提示
window.showLoginSuccess = async () => {
  console.log('外部调用显示登录成功提示');
  // 检查登录提示是否启用
  const loginNotificationSetting = localStorage.getItem('loginNotification');
  isLoginNotificationEnabled.value = loginNotificationSetting !== 'false';
  
  if (isLoginNotificationEnabled.value) {
    await fetchUserInfo();
    await fetchRecentLoginLog();
    showLoginSuccessNotification.value = true;
    sessionStorage.setItem('loginSuccessNotificationShown', 'true');
    
    // 5秒后自动关闭提示
    setTimeout(() => {
      showLoginSuccessNotification.value = false;
    }, 5000);
  }
};

// 提供强制显示方法供调试使用
window.forceShowLoginSuccess = forceShowLoginSuccessNotification;

onMounted(() => {
  console.log('Layout.vue组件已挂载');
  checkIsMobile();
  window.addEventListener('resize', handleResize);
  
  // 显示登录成功提示
  showLoginSuccessNotificationFunc();
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.layout-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.layout-sider {
  height: 100%;
  background-color: var(--color-bg-2);
  border-right: 1px solid var(--color-border);
  transition: width 0.2s ease;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 100;
}

/* 暗色主题下侧边栏 */
:global(body[arco-theme="dark"]) .layout-sider {
  background-color: #17171a;
  border-right: 1px solid #424244;
}

.sider-header {
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Logo容器样式 */
.logo-container {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background-color: #f0f0f0;
  transition: all 0.2s ease; /* 添加过渡效果 */
}

/* 暗色主题下Logo容器 */
:global(body[arco-theme="dark"]) .logo-container {
  background-color: #2e2e30;
}

/* Logo图片样式 */
.logo-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: all 0.2s ease; /* 添加过渡效果 */
}

/* 收起状态下的Logo容器样式 */
.logo-container.collapsed {
  width: 30px;
  height: 30px;
}

.layout-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: var(--color-bg-1); /* 使用Arco Design的CSS变量 */
}

.layout-main {
  flex: 1;
  overflow: auto;
  padding: 20px;
  background-color: var(--color-bg-1); /* 使用Arco Design的CSS变量 */
}

/* 暗色主题下主内容区域 */
:global(body[arco-theme="dark"]) .layout-content {
  background-color: var(--color-bg-1);
}

:global(body[arco-theme="dark"]) .layout-main {
  background-color: var(--color-bg-1);
}

/* 移动端菜单切换按钮 */
.mobile-menu-toggle {
  position: fixed;
  top: 16px;
  left: 16px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: var(--color-bg-2);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 99;
}

/* 暗色主题下移动端菜单切换按钮 */
:global(body[arco-theme="dark"]) .mobile-menu-toggle {
  background-color: #17171a;
  border: 1px solid #424244;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.mobile-menu-toggle:hover {
  background-color: var(--color-fill-2);
  transform: scale(1.05);
}

/* 暗色主题下移动端菜单切换按钮悬停 */
:global(body[arco-theme="dark"]) .mobile-menu-toggle:hover {
  background-color: #2a2a2c;
}

.mobile-menu-toggle .arco-icon {
  font-size: 20px;
  color: var(--color-text-1);
}

:global(body[arco-theme="dark"]) .mobile-menu-toggle .arco-icon {
  color: #c3c0c0;
}

/* 移动端侧边栏覆盖样式 */
.layout-sider.mobile-overlay {
  position: fixed;
  height: 100vh;
  z-index: 101;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
}

:global(body[arco-theme="dark"]) .layout-sider.mobile-overlay {
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.3);
}

/* 移动端遮罩层 */
.mobile-overlay-mask {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.3);
  z-index: 100;
}

/* 登录成功提示框 */
.login-success-notification {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 320px;
  background: var(--color-bg-5); /* 使用Arco Design的CSS变量 */
  border: 1px solid var(--color-border); /* 使用Arco Design的CSS变量 */
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  animation: slideInUp 0.3s ease;
}

/* 暗色主题下提示框 */
:global(body[arco-theme="dark"]) .login-success-notification {
  background: var(--color-bg-5); /* 使用Arco Design的CSS变量 */
  border: 1px solid var(--color-border); /* 使用Arco Design的CSS变量 */
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

@keyframes slideInUp {
  from {
    transform: translate3d(0, 100%, 0);
    opacity: 0;
  }
  to {
    transform: translate3d(0, 0, 0);
    opacity: 1;
  }
}

.notification-content {
  display: flex;
  align-items: flex-start;
  padding: 16px;
  gap: 12px;
}

.success-icon {
  font-size: 24px;
  color: var(--color-success); /* 使用Arco Design的CSS变量 */
  flex-shrink: 0;
  margin-top: 2px;
}

.notification-text {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--color-text-1); /* 使用Arco Design的CSS变量 */
  margin-bottom: 4px;
}

/* 暗色主题下标题 */
:global(body[arco-theme="dark"]) .notification-title {
  color: var(--color-text-1); /* 使用Arco Design的CSS变量 */
}

.notification-message {
  font-size: 14px;
  color: var(--color-text-2); /* 使用Arco Design的CSS变量 */
  margin-bottom: 8px;
  word-break: break-all;
}

/* 暗色主题下消息 */
:global(body[arco-theme="dark"]) .notification-message {
  color: var(--color-text-2); /* 使用Arco Design的CSS变量 */
}

.notification-details {
  font-size: 12px;
  color: var(--color-text-3); /* 使用Arco Design的CSS变量 */
  margin-top: 8px;
}

/* 暗色主题下详情 */
:global(body[arco-theme="dark"]) .notification-details {
  color: var(--color-text-3); /* 使用Arco Design的CSS变量 */
}

.notification-detail-item {
  display: flex;
  margin-bottom: 4px;
}

.notification-detail-item:last-child {
  margin-bottom: 0;
}

.detail-label {
  font-weight: 500;
  margin-right: 4px;
  flex-shrink: 0;
}

.detail-value {
  flex: 1;
  min-width: 0;
  word-break: break-all;
}

.close-icon {
  font-size: 16px;
  color: var(--color-text-3); /* 使用Arco Design的CSS变量 */
  cursor: pointer;
  flex-shrink: 0;
  margin-top: 2px;
}

.close-icon:hover {
  color: var(--color-text-2); /* 使用Arco Design的CSS变量 */
}

/* 暗色主题下关闭图标 */
:global(body[arco-theme="dark"]) .close-icon {
  color: var(--color-text-3); /* 使用Arco Design的CSS变量 */
}

:global(body[arco-theme="dark"]) .close-icon:hover {
  color: var(--color-text-2); /* 使用Arco Design的CSS变量 */
}

/* 移动端适配 */
@media (max-width: 768px) {
  .login-success-notification {
    width: calc(100% - 40px);
    bottom: 10px;
    right: 10px;
  }
  
  .notification-content {
    padding: 12px;
  }
  
  .notification-title {
    font-size: 14px;
  }
  
  .notification-message {
    font-size: 13px;
  }
}
</style>