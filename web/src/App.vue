<template>
  <a-config-provider :locale="locale">
    <div class="app-container">
      <!-- 全局加载动画 -->
      <div v-if="isLoading" class="global-loading">
        <a-spin dot class="loading-spinner" />
      </div>
      <!-- 路由视图 -->
      <router-view v-show="!isLoading" />
    </div>
  </a-config-provider>
</template>

<script setup>
// 引入全局语言状态管理
import { locale } from './utils/locale';
import { isLoading } from './utils/loading';
import { onMounted, watch } from 'vue';
import { fetchCurrentUser } from './stores/user';

// 监听主题变化
const handleThemeChange = () => {
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme === 'dark') {
    document.body.setAttribute('arco-theme', 'dark');
  } else {
    document.body.removeAttribute('arco-theme');
  }
};

// 组件挂载时设置主题和获取用户信息
onMounted(() => {
  handleThemeChange();
  // 获取当前用户信息
  fetchCurrentUser();
  
  // 监听本地存储变化
  window.addEventListener('storage', (e) => {
    if (e.key === 'theme') {
      handleThemeChange();
    }
  });
});

// 监听路由变化时也检查主题设置
import { useRoute } from 'vue-router';
const route = useRoute();
watch(() => route.path, () => {
  // 延迟一小段时间确保DOM更新后再检查主题
  setTimeout(handleThemeChange, 100);
});
</script>

<style scoped>
.app-container {
  position: relative;
  min-height: 100vh;
}

.global-loading {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: rgba(255, 255, 255, 0.712);
  z-index: 9999;
}

.loading-spinner {
  transform: scale(2); /* 按照规范放大2倍 */
}
</style>

<!-- 全局样式 -->
<style>
/* 确保应用容器在亮色主题下有合适的背景 */
.app-container {
  background-color: var(--color-bg-1);
}

/* 确保应用容器在暗色主题下有合适的背景 */
body[arco-theme="dark"] .app-container {
  background-color: var(--color-bg-1);
}

/* 隐藏全局滚动条 */
::-webkit-scrollbar {
  display: none;
}

/* 兼容其他浏览器 */
html {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

body {
  overflow-x: hidden;
  font-family: "Courier New", Courier, monospace;
}

/* 为xterm.js组件设置全局字体 */
.xterm {
  font-family: "Courier New", Courier, monospace !important;
  font-size: 14px !important;
}

.xterm-screen {
  font-family: "Courier New", Courier, monospace !important;
}

.xterm-viewport {
  font-family: "Courier New", Courier, monospace !important;
}

.xterm-char-measure-element {
  font-family: "Courier New", Courier, monospace !important;
}

textarea {
  font-family: "Courier New", Courier, monospace !important;
}
</style>