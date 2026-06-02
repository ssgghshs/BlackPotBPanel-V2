<template>
  <a-drawer
    :visible="visible"
    @update:visible="(val) => $emit('update:visible', val)"
    :title="t('createSSLCert')"
    :width="700"
    :footer="true"
    :mask-closable="false"
    @cancel="handleCancel"
  >
    <a-tabs v-model:active-key="activeTab">
      <a-tab-pane key="upload" :title="t('uploadCertificate')">
        <a-form :model="uploadForm" layout="vertical">
          <a-form-item :label="t('certName')" required>
            <a-input
              v-model="uploadForm.name"
              :placeholder="t('enterCertName')"
              allow-clear
            />
          </a-form-item>
          <a-form-item :label="t('privateKey')" required>
            <div class="cert-container">
              <a-textarea
                v-model="uploadForm.key"
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
                <a-button size="small" @click="uploadForm.key = ''" v-if="uploadForm.key">
                  <template #icon><icon-delete /></template>
                  {{ t('clear') }}
                </a-button>
              </div>
            </div>
          </a-form-item>
          <a-form-item :label="t('certContent')" required>
            <div class="cert-container">
              <a-textarea
                v-model="uploadForm.pem"
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
                <a-button size="small" @click="uploadForm.pem = ''" v-if="uploadForm.pem">
                  <template #icon><icon-delete /></template>
                  {{ t('clear') }}
                </a-button>
              </div>
            </div>
          </a-form-item>
        </a-form>
      </a-tab-pane>
      <a-tab-pane key="self-signed" :title="t('selfSignedCert')">
        <a-form :model="selfSignedForm" layout="vertical">
          <a-form-item :label="t('certName')" required>
            <a-input
              v-model="selfSignedForm.name"
              :placeholder="t('enterCertName')"
              allow-clear
            />
          </a-form-item>
          <a-form-item :label="t('domainName')" required>
            <a-input
              v-model="selfSignedForm.domain"
              :placeholder="t('enterDomain')"
              allow-clear
            />
          </a-form-item>
          <a-form-item :label="t('keySize')">
            <a-select v-model="selfSignedForm.keySize" :style="{ width: '100%' }">
              <a-option :value="2048">2048</a-option>
              <a-option :value="4096">4096</a-option>
            </a-select>
          </a-form-item>
          <a-form-item :label="t('daysValid')">
            <a-input-number
              v-model="selfSignedForm.daysValid"
              :min="1"
              :max="3650"
              :placeholder="t('enterDaysValid')"
              :style="{ width: '100%' }"
            />
          </a-form-item>
          <a-form-item :label="t('organization')">
            <a-input
              v-model="selfSignedForm.organization"
              :placeholder="t('enterOrganization')"
              allow-clear
            />
          </a-form-item>
          <a-form-item :label="t('signatureAlgorithm')">
            <a-select v-model="selfSignedForm.signatureAlgorithm" :style="{ width: '100%' }">
              <a-option value="SHA256">SHA256</a-option>
              <a-option value="SHA384">SHA384</a-option>
              <a-option value="SHA512">SHA512</a-option>
            </a-select>
          </a-form-item>
        </a-form>
      </a-tab-pane>
    </a-tabs>
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
import { createSSLCert, generateSelfSignedCert } from '../../api/waf';
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
const activeTab = ref('upload');

const uploadForm = reactive({
  name: '',
  key: '',
  pem: ''
});

const selfSignedForm = reactive({
  name: '',
  domain: '',
  keySize: 2048,
  daysValid: 365,
  organization: 'Self-Signed',
  signatureAlgorithm: 'SHA256'
});

const resetForms = () => {
  uploadForm.name = '';
  uploadForm.key = '';
  uploadForm.pem = '';
  selfSignedForm.name = '';
  selfSignedForm.domain = '';
  selfSignedForm.keySize = 2048;
  selfSignedForm.daysValid = 365;
  selfSignedForm.organization = 'Self-Signed';
  selfSignedForm.signatureAlgorithm = 'SHA256';
};

const handleCancel = () => {
  emit('update:visible', false);
  resetForms();
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
    uploadForm.key = content;
    Message.success(t.value('uploadKeySuccess'));
    if (!uploadForm.name) {
      const fileName = file.name.replace(/\.(key|pem|crt|cer)$/i, '');
      uploadForm.name = fileName;
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
    uploadForm.pem = content;
    Message.success(t.value('uploadCertSuccess'));
    if (!uploadForm.name) {
      const fileName = file.name.replace(/\.(key|pem|crt|cer)$/i, '');
      uploadForm.name = fileName;
    }
  } catch (error) {
    console.error('读取证书文件失败:', error);
    Message.error(t.value('uploadCertFailed'));
  }
};

const handleSubmit = async () => {
  if (activeTab.value === 'upload') {
    if (!uploadForm.name.trim()) {
      Message.error(t.value('certNameRequired'));
      return;
    }
    if (!uploadForm.key.trim()) {
      Message.error(t.value('privateKeyRequired'));
      return;
    }
    if (!uploadForm.pem.trim()) {
      Message.error(t.value('certContentRequired'));
      return;
    }

    try {
      submitting.value = true;
      await createSSLCert({
        name: uploadForm.name.trim(),
        key: uploadForm.key.trim(),
        pem: uploadForm.pem.trim()
      });
      Message.success(t.value('createSSLCertSuccess'));
      emit('success');
      emit('update:visible', false);
      resetForms();
    } catch (error) {
      console.error('创建SSL证书失败:', error);
      Message.error(t.value('createSSLCertFailed'));
    } finally {
      submitting.value = false;
    }
  } else {
    if (!selfSignedForm.name.trim()) {
      Message.error(t.value('certNameRequired'));
      return;
    }
    if (!selfSignedForm.domain.trim()) {
      Message.error(t.value('domainRequired'));
      return;
    }

    try {
      submitting.value = true;
      await generateSelfSignedCert({
        name: selfSignedForm.name.trim(),
        domain: selfSignedForm.domain.trim(),
        key_size: selfSignedForm.keySize,
        days_valid: selfSignedForm.daysValid,
        organization: selfSignedForm.organization.trim() || 'Self-Signed',
        signature_algorithm: selfSignedForm.signatureAlgorithm
      });
      Message.success(t.value('generateSelfSignedCertSuccess'));
      emit('success');
      emit('update:visible', false);
      resetForms();
    } catch (error) {
      console.error('生成自签证书失败:', error);
      Message.error(t.value('generateSelfSignedCertFailed'));
    } finally {
      submitting.value = false;
    }
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
