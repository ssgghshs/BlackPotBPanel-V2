<template>
  <div class="footer-container">
    <nav class="horizontal-menu">
      <span class="footer-item">BlackPotBPanel</span>
      <span class="footer-separator">|</span>
      <a class="footer-item" href="https://gitee.com/ssgghshs/blackpotbpanel-v2/blob/master/README.md" target="_blank"><icon-file />{{ t('doc') }}</a>
      <span class="footer-separator">|</span>
      <a class="footer-item" href="https://github.com/ssgghshs/blackpotbpanel-v2" target="_blank">
        <icon-github />
      </a>
      <span class="footer-separator">|</span>
      <a class="footer-item" href="https://gitee.com/ssgghshs/blackpotbpanel-v2" target="_blank">
        <Gitee />
      </a>
    </nav>
    <router-view />
  </div>
</template>

<script setup>
import { t } from '../utils/locale';
import { IconGithub, IconFile } from '@arco-design/web-vue/es/icon';
import Gitee from '../components/icon/Gitee.vue';
</script>

<style scoped>
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


.footer-item {
  display: inline-flex;
  align-items: center;
  margin: 0;
  padding: 0 8px;
  white-space: nowrap;
}

.footer-separator {
  color: #999;
  font-size: 12px;
}

.github-icon {
  cursor: pointer;
  transition: transform 0.2s ease;
}

.github-icon:hover {
  transform: scale(1.1);
}

.footer-container {
  padding: 5px 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  text-align: center;
}

/* 确保版本号文本不是蓝色 */
.footer-container {
  color: var(--text-color);
}

/* 暗色主题下的颜色 */
body[arco-theme="dark"] .footer-container {
  color: #cccccc !important;
}
</style>

<!-- 使用非scoped样式确保在所有主题下保持一致 -->
<style>


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