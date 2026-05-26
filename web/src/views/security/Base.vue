<template>
  <div class="security-container">
    <nav class="horizontal-menu">
      <ul>
        <li><router-link to="/security/firewall">{{ t('firewall') }}</router-link></li>
        <li><router-link to="/security/ssh-manager">{{ t('sshManger') }}</router-link></li>
        <li><router-link to="/security/process">{{ t('process') }}</router-link></li>
        <li><router-link to="/security/network-list">{{ t('network') }}</router-link></li>
      </ul>
    </nav>
    <router-view />
  </div>
</template>

<script setup>
import { t } from '../../utils/locale';
</script>

<style scoped>
.security-container {
  padding: 5px 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
</style>

<!-- 使用非scoped样式确保在所有主题下保持一致 -->
<style>
/* 水平菜单容器 */
.horizontal-menu {
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
  padding: 6px 8px;
  margin-bottom: 20px;
  overflow: hidden;
  display: flex;
  align-items: center;
  border: 1px solid #ebebeb;
}

/* 暗色主题下水平菜单容器 */
body[arco-theme="dark"] .horizontal-menu {
  background: #232324 !important;
  border: 1px solid #424244 !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3) !important;
}

.horizontal-menu ul {
  display: flex;
  list-style: none;
  padding: 0;
  margin: 0;
  gap: 12px;
}

.horizontal-menu li {
  margin: 0;
}

.horizontal-menu a {
  display: flex;
  align-items: center;
  text-decoration: none;
  color: #666;
  font-size: 14px;
  padding: 8px 12px;
  border-radius: 6px;
  transition: all 0.2s ease;
  position: relative;
  cursor: pointer;
}

/* 暗色主题下菜单项 */
body[arco-theme="dark"] .horizontal-menu a {
  color: #cccccc !important;
  background: transparent !important;
}

.horizontal-menu a::before {
  margin-right: 8px;
  font-size: 14px;
  display: inline-block;
}

/* 悬停状态 */
.horizontal-menu a:hover {
  background-color: #e8f4ff;
  color: #333;
}

/* 暗色主题下悬停状态 */
body[arco-theme="dark"] .horizontal-menu a:hover {
  background-color: #373739 !important;
  color: #ffffff !important;
}

/* 激活状态（选中项） */
.horizontal-menu a.router-link-active {
  background-color: var(--color-primary-light-1);
  color: rgb(var(--primary-6));
  font-weight: 500;
}

/* 暗色主题下激活状态 */
body[arco-theme="dark"] .horizontal-menu a.router-link-active {
  background-color: rgba(64, 132, 255, 0.2) !important;
  color: #3c7eff !important;
}

/* 激活状态下的下划线 */
.horizontal-menu a.router-link-active::after {
  content: "";
  position: absolute;
  left: 25%;
  bottom: 0;
  width: 50%;
  height: 2px;
  background-color: rgb(var(--primary-6));
  border-radius: 1px;
}

/* 适配不同路由路径的激活状态 */
.horizontal-menu a.router-link-active,
.horizontal-menu a.router-link-exact-active {
  background-color: var(--color-primary-light-1);
  color: rgb(var(--primary-6));
}

/* 暗色主题下激活状态 */
body[arco-theme="dark"] .horizontal-menu a.router-link-active,
body[arco-theme="dark"] .horizontal-menu a.router-link-exact-active {
  background-color: rgba(64, 132, 255, 0.2) !important;
  color: #3c7eff !important;
}
</style>