<template>
  <a-drawer
    :visible="visible"
    @update:visible="(val) => $emit('update:visible', val)"
    :title="t('editSSLCert')"
    :width="600"
    :footer="true"
    :mask-closable="false"
    :loading="loading"
    @cancel="handleCancel"
  >
    <a-form :model="form" layout="vertical">
      <a-form-item :label="t('certName')">
        <a-input
          v-model="form.name"
          disabled
        />
      </a-form-item>
      <a-form-item :label="t('privateKey')" required>
        <a-textarea
          v-model="form.key"
          :placeholder="t('enterPrivateKey')"
          :auto-size="{ minRows: 8, maxRows: 12 }"
          allow-clear
        />
      </a-form-item>
      <a-form-item :label="t('certContent')" required>
        <a-textarea
          v-model="form.pem"
          :placeholder="t('enterCertContent')"
          :auto-size="{ minRows: 8, maxRows: 12 }"
          allow-clear
        />
      </a-form-item>
    </a-form>
    <template #footer>
      <a-space>
        <a-button @click="handleCancel">{{ t('cancel') }}</a-button>
        <a-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ t('confirm') }}
        </a-button>
      </a-space>
    </template>
  </a-drawer>
</template>

<script setup>
import { reactive, ref, watch } from 'vue';
import { t } from '../../utils/locale';
import { updateSSLCert, getSSLCertDetail } from '../../api/waf';
import { Message } from '@arco-design/web-vue';

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

const emit = defineEmits(['update:visible', 'success']);

const submitting = ref(false);
const loading = ref(false);

const form = reactive({
  name: '',
  key: '',
  pem: ''
});

const resetForm = () => {
  form.name = '';
  form.key = '';
  form.pem = '';
};

const loadCertInfo = async () => {
  if (props.certInfo && props.certInfo.id) {
    form.name = props.certInfo.name || '';
    try {
      loading.value = true;
      const response = await getSSLCertDetail(props.certInfo.id);
      if (response) {
        form.key = response.key || '';
        form.pem = response.pem || '';
      }
    } catch (error) {
      console.error('获取SSL证书详情失败:', error);
      Message.error(t.value('getSSLCertDetailFailed'));
    } finally {
      loading.value = false;
    }
  }
};

const handleCancel = () => {
  emit('update:visible', false);
  resetForm();
};

const handleSubmit = async () => {
  if (!form.key.trim()) {
    Message.error(t.value('privateKeyRequired'));
    return;
  }
  if (!form.pem.trim()) {
    Message.error(t.value('certContentRequired'));
    return;
  }

  try {
    submitting.value = true;
    await updateSSLCert(props.certInfo.id, {
      key: form.key.trim(),
      pem: form.pem.trim()
    });
    Message.success(t.value('updateSSLCertSuccess'));
    emit('success');
    emit('update:visible', false);
    resetForm();
  } catch (error) {
    console.error('更新SSL证书失败:', error);
    Message.error(t.value('updateSSLCertFailed'));
  } finally {
    submitting.value = false;
  }
};

watch(() => props.visible, (newVal) => {
  if (newVal) {
    loadCertInfo();
  }
});

watch(() => props.certInfo, () => {
  if (props.visible) {
    loadCertInfo();
  }
}, { immediate: true });
</script>

<style scoped>
</style>
