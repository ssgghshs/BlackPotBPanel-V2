<template>
  <a-drawer
    :visible="visible"
    @update:visible="(val) => $emit('update:visible', val)"
    :title="t('sslCertDetail')"
    :width="700"
    :footer="false"
    :mask-closable="true"
    @cancel="handleCancel"
  >
    <a-descriptions :column="1" bordered v-if="certDetail">
      <a-descriptions-item :label="t('certName')">
        {{ certDetail.name }}
      </a-descriptions-item>
      <a-descriptions-item :label="t('domain')">
        {{ certDetail.domain || '-' }}
      </a-descriptions-item>
      <a-descriptions-item :label="t('issuer')">
        {{ certDetail.issuer || '-' }}
      </a-descriptions-item>
      <a-descriptions-item :label="t('expiryDate')">
        {{ formatDate(certDetail.expiry_date) }}
      </a-descriptions-item>
      <a-descriptions-item :label="t('createTime')">
        {{ formatDate(certDetail.created_at) }}
      </a-descriptions-item>
      <a-descriptions-item :label="t('updateTime')">
        {{ formatDate(certDetail.updated_at) }}
      </a-descriptions-item>
    </a-descriptions>

    <a-divider />

    <div class="cert-content-section">
      <div class="section-header">
        <span class="section-title">{{ t('privateKey') }}</span>
        <a-button type="text" size="small" @click="copyContent(certDetail?.key)">
          <icon-copy />
          {{ t('copy') }}
        </a-button>
      </div>
      <a-textarea
        :model-value="certDetail?.key"
        readonly
        :auto-size="{ minRows: 6, maxRows: 10 }"
        class="cert-textarea"
      />
    </div>

    <a-divider />

    <div class="cert-content-section">
      <div class="section-header">
        <span class="section-title">{{ t('certContent') }}</span>
        <a-button type="text" size="small" @click="copyContent(certDetail?.pem)">
          <icon-copy />
          {{ t('copy') }}
        </a-button>
      </div>
      <a-textarea
        :model-value="certDetail?.pem"
        readonly
        :auto-size="{ minRows: 6, maxRows: 10 }"
        class="cert-textarea"
      />
    </div>
  </a-drawer>
</template>

<script setup>
import { ref, watch } from 'vue';
import { t } from '../../utils/locale';
import { getSSLCertDetail } from '../../api/waf';
import { Message } from '@arco-design/web-vue';
import { IconCopy } from '@arco-design/web-vue/es/icon';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  certInfo: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['update:visible']);

const certDetail = ref(null);
const loading = ref(false);

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleString();
};

// 复制内容到剪贴板
const copyContent = async (content) => {
  if (!content) {
    Message.warning(t.value('noContentToCopy'));
    return;
  }
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(content);
    } else {
      const textarea = document.createElement('textarea');
      textarea.value = content;
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
    Message.success(t.value('copySuccess'));
  } catch (error) {
    console.error('复制失败:', error);
    Message.error(t.value('copyFailed'));
  }
};

const handleCancel = () => {
  emit('update:visible', false);
};

// 获取SSL证书详情
const fetchCertDetail = async (certId) => {
  if (!certId) return;
  
  try {
    loading.value = true;
    const response = await getSSLCertDetail(certId);
    if (response) {
      certDetail.value = response;
    }
  } catch (error) {
    console.error('获取SSL证书详情失败:', error);
    Message.error(t.value('getSSLCertDetailFailed'));
  } finally {
    loading.value = false;
  }
};

// 监听visible变化，当抽屉打开时获取详情
watch(() => props.visible, (newVal) => {
  if (newVal && props.certInfo?.id) {
    fetchCertDetail(props.certInfo.id);
  }
});

// 监听certInfo变化
watch(() => props.certInfo, (newVal) => {
  if (newVal?.id && props.visible) {
    fetchCertDetail(newVal.id);
  }
}, { immediate: true });
</script>

<style scoped>
.cert-content-section {
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.section-title {
  font-weight: 500;
  font-size: 14px;
}

.cert-textarea {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}
</style>
