<template>
  <a-card class="ai-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('modelManagement') }}</span>
        <a-space style="margin-left: auto;">
          <a-button type="outline" size="small" @click="openDiscoverModal">
            {{ t('discover') }}
          </a-button>
          <a-button type="primary" size="small" @click="openCreateDrawer">
            {{ t('addModel') }}
          </a-button>
        </a-space>
      </div>
    </template>

    <a-table
      :columns="columns"
      :data="modelData"
      :loading="loading"
      :pagination="pagination"
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
      :scroll="scroll"
    >
      <template #provider="{ record }">
        <a-tag>{{ record.provider }}</a-tag>
      </template>
      <template #model_type="{ record }">
        <a-tag color="arcoblue">{{ record.model_type }}</a-tag>
      </template>
      <template #is_enabled="{ record }">
        <a-switch
          :model-value="record.is_enabled"
          @change="(val) => handleToggleEnabled(record, val)"
          :loading="togglingId === record.id"
        />
      </template>
      <template #is_default="{ record }">
        <a-tag v-if="record.is_default" color="green">{{ t('isDefault') }}</a-tag>
        <span v-else>-</span>
      </template>
      <template #actions="{ record }">
        <a-space>
          <a-link @click="openEditDrawer(record)">{{ t('edit') }}</a-link>
          <a-link status="danger" @click="confirmDelete(record)">{{ t('delete') }}</a-link>
        </a-space>
      </template>
    </a-table>
  </a-card>

  <!-- 添加/编辑抽屉 -->
  <a-drawer
    :visible="formDrawerVisible"
    @cancel="closeFormDrawer"
    :width="isMobile ? '100%' : 650"
    :footer="false"
    :mask-closable="false"
  >
    <template #title>
      {{ editingId ? t('editModel') : t('addModel') }}
    </template>

    <a-form :model="formData" :rules="formRules" ref="formRef" layout="vertical" @submit="handleSave">
      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item field="name" :label="t('modelName')">
            <a-input v-model="formData.name" :placeholder="t('enterModelName')" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item field="model_name" :label="t('modelIdentifier')">
            <a-input v-model="formData.model_name" :placeholder="t('enterModelIdentifier')" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item field="provider" :label="t('provider')">
            <a-select v-model="formData.provider" :placeholder="t('selectProvider')">
              <a-option v-for="p in providerOptions" :key="p" :value="p" :label="p" />
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item field="model_type" :label="t('modelType')">
            <a-select v-model="formData.model_type" :placeholder="t('selectModelType')">
              <a-option v-for="mt in modelTypeOptions" :key="mt" :value="mt" :label="mt" />
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <a-form-item field="api_base" :label="t('apiAddress')">
        <a-input v-model="formData.api_base" :placeholder="t('enterApiAddress')" />
      </a-form-item>

      <a-form-item field="api_key" :label="t('apiKey')">
        <a-input-password v-model="formData.api_key" :placeholder="t('enterApiKey')" />
      </a-form-item>

      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item field="api_secret" :label="t('apiSecret')">
            <a-input-password v-model="formData.api_secret" placeholder="API Secret" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item field="api_version" :label="t('apiVersion')">
            <a-input v-model="formData.api_version" placeholder="API Version" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item field="max_tokens" :label="t('maxTokens')">
            <a-input-number v-model="formData.max_tokens" :min="1" :max="999999" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item field="context_length" :label="t('contextLength')">
            <a-input-number v-model="formData.context_length" :min="1" :max="9999999" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item field="temperature" :label="t('temperature') + ' (' + formData.temperature / 100 + ')'">
            <a-slider v-model="formData.temperature" :min="0" :max="200" :step="1" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item field="top_p" :label="t('topP') + ' (0-100)'">
            <a-input-number v-model="formData.top_p" :min="0" :max="100" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-row :gutter="16">
        <a-col :span="8">
          <a-form-item field="is_enabled" :label="t('isEnabled')">
            <a-switch v-model="formData.is_enabled" />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item field="is_default" :label="t('isDefault')">
            <a-switch v-model="formData.is_default" />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item field="sort_order" :label="t('sortOrder')">
            <a-input-number v-model="formData.sort_order" :min="0" :max="999" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-form-item>
        <a-space>
          <a-button type="primary" html-type="submit" :loading="saving">
            {{ editingId ? t('update') : t('create') }}
          </a-button>
          <a-button @click="closeFormDrawer">{{ t('cancel') }}</a-button>
        </a-space>
      </a-form-item>
    </a-form>
  </a-drawer>

  <!-- 删除确认 -->
  <a-modal
    :visible="deleteModalVisible"
    @ok="handleDelete"
    @cancel="cancelDelete"
    :ok-text="t('confirm')"
    :cancel-text="t('cancel')"
  >
    <template #title>{{ t('delete') }}</template>
    <div>
      <p>{{ t('confirmDeleteModel', { name: deleteTarget.name }) }}</p>
    </div>
  </a-modal>

  <!-- 发现模型抽屉 -->
  <a-drawer
    :visible="discoverDrawerVisible"
    @cancel="closeDiscoverDrawer"
    :width="isMobile ? '100%' : 550"
    :footer="false"
  >
    <template #title>{{ t('discover') }}</template>
    <div>
      <p class="desc">{{ t('discoverModelHint') }}</p>
      <a-form layout="vertical" :model="discoverForm">
        <a-form-item :label="t('baseUrl')">
          <a-input v-model="discoverBaseUrl" placeholder="https://api.openai.com" />
        </a-form-item>
        <a-form-item :label="t('apiKey')">
          <a-input-password v-model="discoverApiKey" :placeholder="t('enterApiKey')" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="handleDiscover" :loading="discovering" :disabled="!discoverBaseUrl || !discoverApiKey">
            {{ t('discover') }}
          </a-button>
        </a-form-item>
      </a-form>
      <div v-if="discovering" style="text-align: center; padding: 20px;">
        <a-spin :size="24" />
        <p style="margin-top: 8px;">{{ t('discovering') }}</p>
      </div>
      <div v-if="discoveredModels.length > 0" style="margin-top: 12px;">
        <p><strong>{{ t('modelIdentifier') }} ({{ t('clickToAdd') }}):</strong></p>
        <a-list :data="discoveredModels" size="small">
          <template #item="{ item }">
            <a-list-item
              style="cursor: pointer;"
              @click="addFromDiscovered(item)"
            >
              <a-list-item-meta>
                <template #title>
                  <a-link>{{ item }}</a-link>
                </template>
                <template #description>
                  <a-tag color="green" size="small">{{ t('clickToAdd') }}</a-tag>
                </template>
              </a-list-item-meta>
            </a-list-item>
          </template>
        </a-list>
      </div>
    </div>
  </a-drawer>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { t } from '../../utils/locale'
import {
  getAiModelList,
  createAiModel,
  updateAiModel,
  deleteAiModel,
  discoverAiModels
} from '../../api/ai'
import { Message } from '@arco-design/web-vue'

const modelData = ref([])
const loading = ref(false)
const saving = ref(false)
const togglingId = ref(null)
const isMobile = ref(false)

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true
})

const scroll = reactive({ x: 1200, y: 400 })

const providerOptions = [
  'openai', 'deepseek', 'ollama', 'longcat', 'vllm',
  'openrouter', 'azure', 'anthropic', 'google', 'zhipu',
  'baidu', 'alibaba', 'xiaomi', 'custom'
]

const modelTypeOptions = ['LLM', 'EMBEDDING', 'TTS', 'STT', 'IMAGE']

const columns = computed(() => [
  { title: t.value('id'), dataIndex: 'id', width: 60 },
  { title: t.value('modelName'), dataIndex: 'name', width: 140, ellipsis: true },
  { title: t.value('modelIdentifier'), dataIndex: 'model_name', width: 140, ellipsis: true },
  { title: t.value('provider'), slotName: 'provider', width: 100 },
  { title: t.value('modelType'), slotName: 'model_type', width: 90 },
  { title: t.value('apiAddress'), dataIndex: 'api_base', width: 180, ellipsis: true },
  { title: t.value('maxTokens'), dataIndex: 'max_tokens', width: 90 },
  { title: t.value('isDefault'), slotName: 'is_default', width: 80 },
  { title: t.value('isEnabled'), slotName: 'is_enabled', width: 70 },
  { title: t.value('actions'), slotName: 'actions', width: 120, fixed: 'right' }
])

// 表单
const formDrawerVisible = ref(false)
const formRef = ref()
const editingId = ref(null)
const formData = reactive({
  name: '',
  model_name: '',
  provider: 'openai',
  model_type: 'LLM',
  api_base: '',
  api_key: '',
  api_secret: '',
  api_version: '',
  max_tokens: 4096,
  context_length: 8192,
  temperature: 70,
  top_p: 100,
  is_enabled: true,
  is_default: false,
  sort_order: 0
})

const formRules = computed(() => ({
  name: [{ required: true, message: t.value('enterModelName') }],
  model_name: [{ required: true, message: t.value('enterModelIdentifier') }],
  provider: [{ required: true, message: t.value('selectProvider') }],
  model_type: [{ required: true, message: t.value('selectModelType') }]
}))

// 删除
const deleteModalVisible = ref(false)
const deleteTarget = reactive({ id: 0, name: '' })

// 发现模型
const discoverDrawerVisible = ref(false)
const discoverBaseUrl = ref('')
const discoverApiKey = ref('')
const discovering = ref(false)
const discoveredModels = ref([])
const discoverForm = reactive({})

// 表格数据加载
async function fetchModels(page = 1) {
  try {
    loading.value = true
    const res = await getAiModelList({ skip: (page - 1) * pagination.pageSize, limit: pagination.pageSize })
    modelData.value = res.items || []
    pagination.total = res.total || 0
  } catch {
    Message.error(t.value('getModelListFailed'))
  } finally {
    loading.value = false
  }
}

function handlePageChange(page) {
  pagination.current = page
  fetchModels(page)
}

function handlePageSizeChange(size) {
  pagination.pageSize = size
  pagination.current = 1
  fetchModels(1)
}

// 打开创建抽屉
function openCreateDrawer() {
  editingId.value = null
  formData.name = ''
  formData.model_name = ''
  formData.provider = 'openai'
  formData.model_type = 'LLM'
  formData.api_base = ''
  formData.api_key = ''
  formData.api_secret = ''
  formData.api_version = ''
  formData.max_tokens = 4096
  formData.context_length = 8192
  formData.temperature = 70
  formData.top_p = 100
  formData.is_enabled = true
  formData.is_default = false
  formData.sort_order = 0
  formDrawerVisible.value = true
}

// 打开编辑抽屉
function openEditDrawer(record) {
  editingId.value = record.id
  formData.name = record.name
  formData.model_name = record.model_name
  formData.provider = record.provider
  formData.model_type = record.model_type
  formData.api_base = record.api_base || ''
  formData.api_key = record.api_key || ''
  formData.api_secret = record.api_secret || ''
  formData.api_version = record.api_version || ''
  formData.max_tokens = record.max_tokens
  formData.context_length = record.context_length
  formData.temperature = record.temperature
  formData.top_p = record.top_p
  formData.is_enabled = record.is_enabled
  formData.is_default = record.is_default
  formData.sort_order = record.sort_order || 0
  formDrawerVisible.value = true
}

function closeFormDrawer() {
  formDrawerVisible.value = false
}

// 保存
async function handleSave() {
  const valid = await formRef.value.validate()
  if (valid) return
  saving.value = true
  try {
    const payload = {
      name: formData.name,
      model_name: formData.model_name,
      provider: formData.provider,
      model_type: formData.model_type,
      api_base: formData.api_base,
      api_key: formData.api_key,
      api_secret: formData.api_secret,
      api_version: formData.api_version,
      max_tokens: formData.max_tokens,
      context_length: formData.context_length,
      temperature: formData.temperature,
      top_p: formData.top_p,
      is_enabled: formData.is_enabled,
      is_default: formData.is_default,
      sort_order: formData.sort_order
    }
    if (editingId.value) {
      await updateAiModel(editingId.value, payload)
      Message.success(t.value('updateModelSuccess'))
    } else {
      await createAiModel(payload)
      Message.success(t.value('createModelSuccess'))
    }
    closeFormDrawer()
    await fetchModels(pagination.current)
  } catch (e) {
    const errMsg = e?.response?.data?.detail
    if (errMsg) {
      Message.error(errMsg)
    } else {
      Message.error(editingId.value ? t.value('updateModelFailed') : t.value('createModelFailed'))
    }
  } finally {
    saving.value = false
  }
}

// 切换启用状态
async function handleToggleEnabled(record, val) {
  togglingId.value = record.id
  try {
    await updateAiModel(record.id, { is_enabled: val })
    Message.success(t.value('updateModelSuccess'))
    await fetchModels(pagination.current)
  } catch {
    Message.error(t.value('updateModelFailed'))
  } finally {
    togglingId.value = null
  }
}

// 删除
function confirmDelete(record) {
  deleteTarget.id = record.id
  deleteTarget.name = record.name
  deleteModalVisible.value = true
}

function cancelDelete() {
  deleteModalVisible.value = false
}

async function handleDelete() {
  try {
    await deleteAiModel(deleteTarget.id)
    Message.success(t.value('deleteModelSuccess'))
    deleteModalVisible.value = false
    await fetchModels(pagination.current)
  } catch {
    Message.error(t.value('deleteModelFailed'))
    deleteModalVisible.value = false
  }
}

// 发现模型
function openDiscoverModal() {
  discoverBaseUrl.value = ''
  discoverApiKey.value = ''
  discoveredModels.value = []
  discoverDrawerVisible.value = true
}

function closeDiscoverDrawer() {
  discoverDrawerVisible.value = false
}

async function handleDiscover() {
  discovering.value = true
  discoveredModels.value = []
  try {
    const res = await discoverAiModels({ base_url: discoverBaseUrl.value, api_key: discoverApiKey.value })
    discoveredModels.value = res.models || []
    if (discoveredModels.value.length === 0) {
      Message.info(t.value('getModelListFailed'))
    }
  } catch (e) {
    const errMsg = e?.response?.data?.detail
    Message.error(errMsg || t.value('getModelListFailed'))
  } finally {
    discovering.value = false
  }
}

// 从发现结果直接添加模型，预填创建表单
function addFromDiscovered(modelId) {
  closeDiscoverDrawer()
  let provider = 'openai'
  const url = discoverBaseUrl.value.toLowerCase()
  if (url.includes('deepseek')) provider = 'deepseek'
  else if (url.includes('ollama')) provider = 'ollama'
  else if (url.includes('vllm')) provider = 'vllm'
  else if (url.includes('openrouter')) provider = 'openrouter'
  else if (url.includes('azure')) provider = 'azure'
  else if (url.includes('google')) provider = 'google'

  openCreateDrawer()
  formData.model_name = modelId
  formData.name = modelId
  formData.provider = provider
  formData.api_base = discoverBaseUrl.value
  formData.api_key = discoverApiKey.value
}

onMounted(() => {
  fetchModels()
})
</script>

<style scoped>
.ai-container {
  padding: 20px;
  overflow: hidden;
  box-sizing: border-box;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 15px;
  font-size: 1.3em;
  padding: 20px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.title {
  margin: 0;
  padding: 0;
}

.desc {
  margin-top: 4px;
  color: #8c8c8c;
  font-size: 12px;
}
</style>
