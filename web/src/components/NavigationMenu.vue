<template>
  <div class="navigation-menu">
    <a-menu
      :style="{ width: '100%', height: '100%' }"
      :selected-keys="selectedKeys"
      :collapse="isMenuCollapsed"
      @menu-item-click="onMenuItemClick"
    >
      <!-- 仪表盘 - 仅对非auditor角色显示 -->
      <a-tooltip :content="t('dashboard')" :disabled="!isMenuCollapsed" mini position="right">
        <a-menu-item key="dashboard">
          <template #icon><icon-dashboard /></template>
          <span v-show="!isMenuCollapsed">{{ t('dashboard') }}</span>
        </a-menu-item>
      </a-tooltip>

      <a-tooltip v-if="!isAuditor()" :content="t('container')" :disabled="!isMenuCollapsed" mini position="right">
        <a-menu-item key="container">
          <template #icon><DockerIcon/></template>
          <span v-show="!isMenuCollapsed">{{ t('container') }}</span>
        </a-menu-item>
      </a-tooltip>

      <a-tooltip v-if="!isAuditor()" :content="t('terminal')" :disabled="!isMenuCollapsed" mini position="right">
        <a-menu-item key="host">
          <template #icon><TerminalIcon/></template>
          <span v-show="!isMenuCollapsed">{{ t('terminal') }}</span>
        </a-menu-item>
      </a-tooltip>      
  
      <a-tooltip v-if="!isAuditor()" :content="t('file')" :disabled="!isMenuCollapsed" mini position="right">
        <a-menu-item key="file">
          <template #icon><icon-folder /></template>
          <span v-show="!isMenuCollapsed">{{ t('file') }}</span>
        </a-menu-item>
      </a-tooltip>

      <!-- 数据库管理 -->
      <a-tooltip v-if="!isAuditor()" :content="t('database')" :disabled="!isMenuCollapsed" mini position="right">
        <a-menu-item key="database">
          <template #icon><DatabaseIcon/></template>
          <span v-show="!isMenuCollapsed">{{ t('database') }}</span>
        </a-menu-item>
      </a-tooltip>

      <a-tooltip v-if="!isAuditor()" :content="t('systemService')" :disabled="!isMenuCollapsed" mini position="right">
        <a-menu-item key="security">
          <template #icon><icon-mobile /></template>
          <span v-show="!isMenuCollapsed">{{ t('systemService') }}</span>
        </a-menu-item>
      </a-tooltip>

      <a-tooltip v-if="!isAuditor()" :content="t('waf')" :disabled="!isMenuCollapsed" mini position="right">
        <a-menu-item key="waf">
          <template #icon><icon-safe /></template>
          <span v-show="!isMenuCollapsed">{{ t('waf') }}</span>
        </a-menu-item>
      </a-tooltip>

      <a-tooltip :content="t('logs')" :disabled="!isMenuCollapsed" mini position="right">
        <a-menu-item key="logs">
          <template #icon><icon-bookmark/></template>
          <span v-show="!isMenuCollapsed">{{ t('logs') }}</span>
        </a-menu-item>
      </a-tooltip>      

      <!-- 系统设置 -->
      <a-tooltip :content="t('settings')" :disabled="!isMenuCollapsed" mini position="right">
        <a-menu-item key="settings">
          <template #icon><icon-settings /></template>
          <span v-show="!isMenuCollapsed">{{ t('settings') }}</span>
        </a-menu-item>
      </a-tooltip>

      <!-- 退出登录菜单项 -->
      <a-tooltip :content="t('logout')" :disabled="!isMenuCollapsed" mini position="right">
        <a-menu-item key="logout" @click="handleLogout">
          <template #icon><icon-to-right /></template>
          <span v-show="!isMenuCollapsed">{{ t('logout') }}</span>
        </a-menu-item>
      </a-tooltip>

    </a-menu>
    
    <!-- 收起/展开按钮 -->
    <div class="collapse-button" @click="toggleMenu">
      <icon-left v-if="!isMenuCollapsed" />
      <icon-right v-else />
    </div>
    
    <!-- 移动端关闭按钮 -->
    <div class="mobile-close-button" @click="emit('close')">
      <icon-close />
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import {
  IconDashboard,
  IconUser,
  IconSettings,
  IconToRight,
  IconBookmark,
  IconFolder,
  IconLeft,
  IconRight,
  IconClose,
  IconMobile,
  IconSafe
} from '@arco-design/web-vue/es/icon';
import { Tooltip } from '@arco-design/web-vue';
// 引入全局语言状态管理
import { t } from '../utils/locale';
import { clearUser, currentUser, isAuditor } from '../stores/user';
import { logout as logoutApi } from '../api/user';
import DockerIcon from "./icon/DockerIcon.vue";
import TerminalIcon from './icon/TerminalIcon.vue';
import DatabaseIcon from './icon/DatabaseIcon.vue';

export default {
  components: {
    DockerIcon,
    IconDashboard,
    IconUser,
    IconSettings,
    IconToRight,
    IconBookmark,
    IconFolder,
    IconLeft,
    IconRight,
    IconClose,
    TerminalIcon,
    IconMobile,
    IconSafe,
    DatabaseIcon,
    ATooltip: Tooltip
  },
  setup(props, { emit }) {
    const router = useRouter();
    const route = useRoute();
    
    // 菜单收起状态
    const isMenuCollapsed = ref(false);

    // 计算当前选中的菜单项
    const selectedKeys = computed(() => {
      const path = route.path;
      if (path === '/home') {
        return ['dashboard'];
      } else if (path.startsWith('/host')) {
        return ['host'];
      } else if (path.startsWith('/container')) {
        return ['container'];
      } else if (path.startsWith('/logs')) {
        return ['logs'];
      } else if (path.startsWith('/file')) {
        return ['file'];
      } else if (path.startsWith('/security')) {
        return ['security'];
      } else if (path.startsWith('/waf')) {
        return ['waf'];       
      } else if (path.startsWith('/settings')) {
        return ['settings'];
      } else if (path.startsWith('/database')) {
        return ['database'];
      }
      return ['dashboard'];
    });

    // 处理菜单项点击
    const onMenuItemClick = (key) => {
      switch (key) {
        case 'dashboard':
          router.push('/home');
          break;
        case 'host':
          router.push('/host');
          break;
        case 'container':
          router.push('/container');
          break;
        case 'logs':
          router.push('/logs');
          break;
        case 'file':
          router.push('/file');
          break;
        case 'security':
          router.push('/security');
          break;
        case 'waf':
          router.push('/waf');
          break;
        case 'settings':
          router.push('/settings');
          break;
        case 'database':
          router.push('/database');
          break;
      }
    };

    // 处理退出登录逻辑
    const handleLogout = async () => {
      try {
        // 调用后端退出登录接口
        await logoutApi();
      } catch (error) {
        console.error('退出登录失败:', error);
      } finally {
        // 无论API调用成功失败，都清除本地存储的token
        localStorage.removeItem('access_token');
        // 清除用户信息
        clearUser();
        // 跳转到登录页
        router.push('/login');
      }
    };
    
    // 切换菜单收起状态
    const toggleMenu = () => {
      isMenuCollapsed.value = !isMenuCollapsed.value;
      // 通知父组件菜单状态变化
      emit('collapse', isMenuCollapsed.value);
    };
    
    // 移动端关闭菜单
    const closeMenu = () => {
      emit('close');
    };
    
    // 监听路由变化，在移动端自动关闭菜单
    watch(() => route.path, () => {
      // 在移动端自动关闭菜单
      if (window.innerWidth <= 768) {
        emit('close');
      }
    });

    return {
      selectedKeys,
      onMenuItemClick,
      handleLogout,
      t,
      isMenuCollapsed,
      toggleMenu,
      closeMenu,
      currentUser,
      isAuditor
    };
  }
};
</script>

<style scoped>
.navigation-menu {
  height: 100%;
  width: 100%;
  position: relative;
}

/* 卡片样式菜单项 */
:deep(.arco-menu-item) {
  border-radius: 12px !important;
  margin: 6px 12px !important;
  padding: 6px 16px !important; /* 调整垂直padding从12px到6px */
  transition: all 0.3s ease !important;
  background-color: var(--color-bg-2) !important;
  border: 1px solid var(--color-border-2) !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
  min-height: 32px; /* 调整最小高度从40px到32px */
}

/* 收起状态下的菜单项样式 */
:deep(.arco-menu.arco-menu-collapsed .arco-menu-item) {
  margin: 6px 12px !important; /* 保持左右margin一致 */
  padding: 8px 0 !important; /* 只移除水平padding */
  justify-content: center;
  min-height: 40px; /* 保持最小高度一致 */
  display: flex;
  align-items: center;
}

/* 收起状态下的菜单项文本 */
:deep(.arco-menu.arco-menu-collapsed .arco-menu-item span) {
  display: none !important;
}

/* 收起状态下的图标 */
:deep(.arco-menu.arco-menu-collapsed .arco-menu-item .arco-icon) {
  font-size: 24px !important;
  width: 24px !important;
  height: 20px !important;
  margin: 0 auto;
}

/* 暗色主题下菜单项 */
:global(body[arco-theme="dark"]) :deep(.arco-menu-item) {
  background-color: #232324 !important;
  border: 1px solid #424244 !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3) !important;
  color: #ffffff !important;
}

:deep(.arco-menu-item:hover) {
  background-color: var(--color-fill-2) !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
  transform: translateY(-2px) !important;
  border-color: var(--color-primary-light-3) !important;
}

/* 暗色主题下菜单项悬停 */
:global(body[arco-theme="dark"]) :deep(.arco-menu-item:hover) {
  background-color: #373739 !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
  border-color: #5c5c5f !important;
}

:deep(.arco-menu-item.arco-menu-selected) {
  background-color: var(--color-primary-light-1) !important;
  color: rgb(var(--primary-6)) !important;
  border-color: rgb(var(--primary-6)) !important;
  box-shadow: 0 4px 16px rgba(var(--primary-6), 0.2) !important;
}

/* 暗色主题下选中菜单项 */
:global(body[arco-theme="dark"]) :deep(.arco-menu-item.arco-menu-selected) {
  background-color: rgba(64, 132, 255, 0.2) !important;
  color: #3c7eff !important;
  border-color: #3c7eff !important;
  box-shadow: 0 4px 16px rgba(64, 132, 255, 0.3) !important;
}

/* 图标尺寸优化 */
:deep(.arco-menu-item .arco-icon) {
  font-size: 18px !important;
  width: 18px !important;
  height: 18px !important;
}

/* 暗色主题下图标颜色 */
:global(body[arco-theme="dark"]) :deep(.arco-menu-item .arco-icon) {
  color: #ffffff !important;
}

:global(body[arco-theme="dark"]) :deep(.arco-menu-item.arco-menu-selected .arco-icon) {
  color: #3c7eff !important;
}

/* 收起按钮样式 */
.collapse-button {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background-color: var(--color-bg-2);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  z-index: 100;
}

/* 暗色主题下收起按钮 */
:global(body[arco-theme="dark"]) .collapse-button {
  background-color: #232324;
  border: 1px solid #424244;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.collapse-button:hover {
  background-color: var(--color-fill-2);
  transform: translateX(-50%) scale(1.1);
}

/* 暗色主题下收起按钮悬停 */
:global(body[arco-theme="dark"]) .collapse-button:hover {
  background-color: #373739;
}

.collapse-button .arco-icon {
  font-size: 14px;
  color: var(--color-text-1);
}

:global(body[arco-theme="dark"]) .collapse-button .arco-icon {
  color: #ffffff;
}

/* 移动端关闭按钮样式 */
.mobile-close-button {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: var(--color-bg-2);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  z-index: 101;
  display: none; /* 默认隐藏 */
}

/* 在移动端显示关闭按钮 */
@media (max-width: 768px) {
  .mobile-close-button {
    display: flex;
  }
}

/* 暗色主题下移动端关闭按钮 */
:global(body[arco-theme="dark"]) .mobile-close-button {
  background-color: #232324;
  border: 1px solid #424244;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.mobile-close-button:hover {
  background-color: var(--color-fill-2);
  transform: scale(1.1);
}

/* 暗色主题下移动端关闭按钮悬停 */
:global(body[arco-theme="dark"]) .mobile-close-button:hover {
  background-color: #373739;
}

.mobile-close-button .arco-icon {
  font-size: 16px;
  color: var(--color-text-1);
}

:global(body[arco-theme="dark"]) .mobile-close-button .arco-icon {
  color: #ffffff;
}
</style>