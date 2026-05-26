<template>
  <div class="waf-container">
    <div v-if="checking" class="waf-checking">
      <a-spin :tip="t('loading')" />
    </div>

    <template v-else>
      <nav class="horizontal-menu">
        <ul>
          <li v-for="item in menuItems" :key="item.to">
            <router-link v-if="wafInstalled" :to="item.to">{{ item.label }}</router-link>
            <a v-else class="menu-link-disabled">{{ item.label }}</a>
          </li>
        </ul>
      </nav>

      <router-view v-if="wafInstalled" />

      <div v-else class="waf-stopped-hint">
        <a-result status="warning" :title="t('wafNotInstalled')">
          <template #subtitle>
            {{ t('wafNotInstalledHint') }}
          </template>
          <template #extra>
            <a-button type="primary" @click="handleRefresh">{{ t('refresh') }}</a-button>
          </template>
        </a-result>
        <div class="install-guide">
          <div class="install-guide-title">{{ t('wafInstallGuide') }}</div>
          <div class="install-step">
            <span class="step-label">{{ t('step1') }}</span>
            <code class="install-code">{{ t('wafInstallStep1') }}</code>
          </div>
          <div class="install-step">
            <span class="step-label">{{ t('step2') }}</span>
            <code class="install-code">{{ t('wafInstallStep2') }}</code>
          </div>
          <div class="install-step">
            <span class="step-label">{{ t('step3') }}</span>
            <code class="install-code">{{ t('wafInstallStep3') }}</code>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { t } from '../../utils/locale';
import { checkWAFContainerExists } from '../../api/waf';

const checking = ref(true);
const wafInstalled = ref(false);

const menuItems = computed(() => [
  { to: '/waf/basic', label: t.value('overview') },
  { to: '/waf/sites', label: t.value('siteslist') },
  { to: '/waf/blackwhite', label: t.value('blackwhite') },
  { to: '/waf/ssl', label: 'SSL' },
  { to: '/waf/rules', label: t.value('protectionRules') },
  { to: '/waf/log', label: 'WAF' + t.value('log') },
  { to: '/waf/global', label: t.value('globalSetting') },
]);

const fetchStatus = async () => {
  checking.value = true;
  try {
    const res = await checkWAFContainerExists();
    wafInstalled.value = !!(res && res.exists);
  } catch {
    wafInstalled.value = false;
  } finally {
    checking.value = false;
  }
};

const handleRefresh = () => {
  fetchStatus();
};

onMounted(() => {
  fetchStatus();
});
</script>

<style scoped>
.waf-container {
  padding: 5px 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.waf-checking {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

.waf-stopped-hint {
  padding: 60px 20px;
  text-align: center;
}

.install-guide {
  margin-top: 24px;
  padding: 20px 24px;
  background: var(--color-fill-1);
  border: 1px solid var(--color-fill-3);
  border-radius: 8px;
  max-width: 520px;
  margin-left: auto;
  margin-right: auto;
  text-align: left;
}

.install-guide-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-1);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-fill-3);
}

.install-step {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.step-label {
  font-size: 13px;
  color: var(--color-text-3);
  white-space: nowrap;
  min-width: 56px;
}

.install-code {
  font-size: 13px;
  color: var(--color-text-1);
  background: var(--color-fill-2);
  padding: 6px 12px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  word-break: break-all;
  flex: 1;
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

.menu-link-disabled {
  color: #ccc !important;
  cursor: not-allowed !important;
}

body[arco-theme="dark"] .menu-link-disabled {
  color: #555 !important;
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
