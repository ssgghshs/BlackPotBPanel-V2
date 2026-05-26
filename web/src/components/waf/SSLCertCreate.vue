<template>
  <a-drawer
    :visible="visible"
    @update:visible="(val) => $emit('update:visible', val)"
    :title="t('createSSLCert')"
    :width="600"
    :footer="true"
    :mask-closable="false"
    @cancel="handleCancel"
  >
    <a-form :model="form" layout="vertical">
      <a-form-item :label="t('certName')" required>
        <a-input
          v-model="form.name"
          :placeholder="t('enterCertName')"
          allow-clear
        />
      </a-form-item>
      <a-form-item :label="t('privateKey')" required>
        <div class="cert-container">
          <a-textarea
            v-model="form.key"
            :placeholder="t('enterPrivateKey')"
            :auto-size="{ minRows: 6, maxRows: 12 }"
            class="cert-textarea"
            allow-clear
          />
          <div class="cert-actions">
            <a-upload
              :auto-upload="false"
              :show-file-list="false"
              accept=".key"
              @change="handleKeyUpload"
            >
              <template #upload-button>
                <a-button size="small">
                  <template #icon><icon-upload /></template>
                  {{ t('uploadFile') }}
                </a-button>
              </template>
            </a-upload>
            <a-button size="small" @click="form.key = ''" v-if="form.key">
              <template #icon><icon-delete /></template>
              {{ t('clear') }}
            </a-button>
          </div>
        </div>
      </a-form-item>
      <a-form-item :label="t('certContent')" required>
        <div class="cert-container">
          <a-textarea
            v-model="form.pem"
            :placeholder="t('enterCertContent')"
            :auto-size="{ minRows: 6, maxRows: 12 }"
            class="cert-textarea"
            allow-clear
          />
          <div class="cert-actions">
            <a-upload
              :auto-upload="false"
              :show-file-list="false"
              accept=".pem,.crt,.cer"
              @change="handlePemUpload"
            >
              <template #upload-button>
                <a-button size="small">
                  <template #icon><icon-upload /></template>
                  {{ t('uploadFile') }}
                </a-button>
              </template>
            </a-upload>
            <a-button size="small" @click="form.pem = ''" v-if="form.pem">
              <template #icon><icon-delete /></template>
              {{ t('clear') }}
            </a-button>
          </div>
        </div>
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
import { reactive, ref } from 'vue';
import { t } from '../../utils/locale';
import { createSSLCert } from '../../api/waf';
import { Message } from '@arco-design/web-vue';
import { IconUpload, IconDelete } from '@arco-design/web-vue/es/icon';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:visible', 'success']);

const submitting = ref(false);

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

const handleCancel = () => {
  emit('update:visible', false);
  resetForm();
};

const readFileContent = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      resolve(e.target.result);
    };
    reader.onerror = (e) => {
      reject(new Error('Failed to read file'));
    };
    reader.readAsText(file);
  });
};

const handleKeyUpload = async (fileList) => {
  const file = fileList[fileList.length - 1]?.file;
  if (!file) return;
  
  try {
    const content = await readFileContent(file);
    form.key = content;
    Message.success(t.value('uploadKeySuccess'));
    if (!form.name) {
      const fileName = file.name.replace(/\.(key|pem|crt|cer)$/i, '');
      form.name = fileName;
    }
  } catch (error) {
    console.error('读取私钥文件失败:', error);
    Message.error(t.value('uploadKeyFailed'));
  }
};

const handlePemUpload = async (fileList) => {
  const file = fileList[fileList.length - 1]?.file;
  if (!file) return;
  
  try {
    const content = await readFileContent(file);
    form.pem = content;
    Message.success(t.value('uploadCertSuccess'));
    if (!form.name) {
      const fileName = file.name.replace(/\.(key|pem|crt|cer)$/i, '');
      form.name = fileName;
    }
  } catch (error) {
    console.error('读取证书文件失败:', error);
    Message.error(t.value('uploadCertFailed'));
  }
};

const handleSubmit = async () => {
  if (!form.name.trim()) {
    Message.error(t.value('certNameRequired'));
    return;
  }
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
    await createSSLCert({
      name: form.name.trim(),
      key: form.key.trim(),
      pem: form.pem.trim()
    });
    Message.success(t.value('createSSLCertSuccess'));
    emit('success');
    emit('update:visible', false);
    resetForm();
  } catch (error) {
    console.error('创建SSL证书失败:', error);
    Message.error(t.value('createSSLCertFailed'));
  } finally {
    submitting.value = false;
  }
};
</script>

<style scoped>
.cert-container {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.cert-textarea {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace !important;
  font-size: 12px !important;
  line-height: 1.4 !important;
}

.cert-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 8px;
}
</style>
