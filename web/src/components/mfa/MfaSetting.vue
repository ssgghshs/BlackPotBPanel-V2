<template>
  <a-drawer
    :visible="visible"
    :title="t('mfa')"
    @cancel="handleClose"
    :width="600"
    :footer="true"
    :mask-closable="false"
  >
    <a-alert type="warning" show-icon :closable="false" style="margin-bottom: 16px;">
      {{ t('mfaAlert') }}
    </a-alert>

    <a-form :model="form" layout="vertical">
      <a-form-item :label="t('mfaHelper1')">
        <ul style="margin: 0; padding-left: 16px;">
          <li>Google Authenticator</li>
          <li>Microsoft Authenticator</li>
          <li>1Password</li>
          <li>Authy</li>
          <li>LastPass</li>
        </ul>
      </a-form-item>

      <a-form-item :label="t('mfaHelper2')">
        <div style="text-align: center;">
          <img v-if="qrImage" :src="qrImage" alt="QR Code" style="width: 200px; height: 200px;" />
          <a-skeleton v-else :animation="true" style="width: 200px; height: 200px; margin: 0 auto;" />
        </div>
        <div style="margin-top: 8px; word-break: break-all; font-size: 12px;">
          <span>{{ t('secret') }}: {{ form.secret }}</span>
          <a-button
            type="text"
            size="mini"
            style="margin-left: 4px;"
            @click="copySecret"
          >
            <template #icon><icon-copy /></template>
          </a-button>
        </div>
      </a-form-item>

      <a-form-item :label="t('mfaInterval')">
        <a-input-number v-model="form.interval" :min="15" :max="60" :step="1" :style="{ width: '120px' }" />
      </a-form-item>

      <a-form-item :label="t('mfaCode')" required>
        <a-input v-model="form.code" :placeholder="t('mfaHelper3')" maxlength="6" />
      </a-form-item>
    </a-form>

    <template #footer>
      <a-button @click="handleClose" style="margin-right: 8px;">{{ t('cancel') }}</a-button>
      <a-button type="primary" :loading="loading" @click="onBind">{{ t('confirm') }}</a-button>
    </template>
  </a-drawer>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { Message } from '@arco-design/web-vue'
import { IconCopy } from '@arco-design/web-vue/es/icon'
import { loadMFA, bindMFA } from '../../api/system'
import { t } from '../../utils/locale'

const visible = ref(false)
const loading = ref(false)
const qrImage = ref('')

const emit = defineEmits(['close'])

const form = reactive({
  secret: '',
  code: '',
  interval: 30
})

const acceptParams = () => {
  loadMfaCode()
  visible.value = true
}

const loadMfaCode = async () => {
  try {
    const res = await loadMFA()
    // res = { code: 200, message: "...", data: { secret, qr_image } }
    const data = res.data
    form.secret = data.secret
    qrImage.value = data.qr_image
  } catch (error) {
    Message.error(t.value('loadFailed'))
  }
}

const copySecret = () => {
  try {
    navigator.clipboard.writeText(form.secret)
    Message.success(t.value('copySuccess'))
  } catch {
    // fallback
    const textarea = document.createElement('textarea')
    textarea.value = form.secret
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    Message.success(t.value('copySuccess'))
  }
}

const onBind = async () => {
  if (!form.code || form.code.length !== 6) {
    Message.error(t.value('mfaHelper3'))
    return
  }
  loading.value = true
  try {
    await bindMFA({
      MFA_ENABLED: true,
      MFA_INTERVAL: form.interval,
      MFA_SECRET: form.secret
    })
    Message.success(t.value('bindSuccess'))
    visible.value = false
    emit('close')
  } catch (error) {
    Message.error(error.response?.data?.detail || t.value('bindFailed'))
  } finally {
    loading.value = false
  }
}

const handleClose = () => {
  visible.value = false
  emit('close')
}

defineExpose({ acceptParams })
</script>
