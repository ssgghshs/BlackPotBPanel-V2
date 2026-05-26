<template>
  <div class="screen-setting">
    <div class="action-row">
      <a-form :model="form" layout="inline" @submit-success="handleSubmit">
        <a-form-item :label="t('screenTitle')" :wrapper-col-props="{ span: 6 }">
          <a-input
            v-model="form.title"
            allow-clear
          />
        </a-form-item>

        <a-form-item :label="t('screenTheme')" :wrapper-col-props="{ span: 6 }">
          <a-select v-model="form.theme" :options="themeOptions" />
        </a-form-item>

        <a-form-item :label="t('screenSwitch')" :wrapper-col-props="{ span: 4 }">
          <a-switch v-model="form.screen" />
        </a-form-item>

        <a-form-item :wrapper-col-props="{ span: 4 }">
          <a-button type="primary" html-type="submit" :loading="loading">
            {{ t('save') }}
          </a-button>
        </a-form-item>
      </a-form>

      <a-button type="text" @click="goToBigScreen">
        {{ t('goToBigScreen') }}
      </a-button>
    </div>

    <div class="preview-container">
      <div class="preview-header">
        <span>{{ t('screenPreview') }}</span>
      </div>
      <ScreenPreview :title="form.title" :theme="form.theme" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { t } from '../../utils/locale';
import { getBigScreenConfig, updateBigScreenConfig } from '../../api/waf';
import { Message } from '@arco-design/web-vue';
import ScreenPreview from './ScreenPreview.vue';

const presetThemes = [
  { name: t.value('deepBlueTech'), value: '#0a1929', colors: ['#0a1929', '#1a2a4a', '#0d1f3c'] },
  { name: t.value('purpleRainbow'), value: '#1a0a2e', colors: ['#1a0a2e', '#2d1b4e', '#1f0d3c'] },
  { name: t.value('greenEco'), value: '#0a2e1a', colors: ['#0a2e1a', '#1a4a2e', '#0d3c1f'] },
  { name: t.value('redAlert'), value: '#2e0a0a', colors: ['#2e0a0a', '#4a1a1a', '#3c0d0d'] },
  { name: t.value('orangeVital'), value: '#2e1a0a', colors: ['#2e1a0a', '#4a2e1a', '#3c1f0d'] },
  { name: t.value('cyanFresh'), value: '#0a2e2e', colors: ['#0a2e2e', '#1a4a4a', '#0d3c3c'] }
];

const themeOptions = computed(() =>
  presetThemes.map(theme => ({
    label: theme.name,
    value: theme.value
  }))
);

const form = reactive({
  title: '',
  theme: '#0a1929',
  screen: true
});

const loading = ref(false);

const goToBigScreen = () => {
  window.open('/bigscreen', '_blank');
};

const fetchConfig = async () => {
  try {
    const res = await getBigScreenConfig();
    if (res) {
      form.title = res.title || '';
      form.theme = res.theme || '#0a1929';
      form.screen = res.screen !== false;
    }
  } catch (error) {
    console.error('获取大屏配置失败:', error);
    Message.error(t.value('getConfigFailed'));
  }
};

const handleSubmit = async () => {
  loading.value = true;
  try {
    await updateBigScreenConfig({
      title: form.title,
      theme: form.theme,
      screen: form.screen
    });
    Message.success(t.value('saveSuccess'));
  } catch (error) {
    console.error('保存大屏配置失败:', error);
    Message.error(t.value('saveFailed'));
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchConfig();
});
</script>

<style scoped>
.screen-setting {
  padding: 20px;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.preview-container {
  margin-top: 24px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  overflow: hidden;
  height: 500px;
  display: flex;
  flex-direction: column;
}

.preview-header {
  padding: 12px 16px;
  background: var(--arco-color-primary-1);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  font-size: 14px;
  color: var(--arco-color-primary-2);
  flex-shrink: 0;
}

.preview-container :deep(.screen-preview) {
  flex: 1;
  min-height: 0;
}
</style>
