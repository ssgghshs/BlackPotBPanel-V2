<template>
  <div class="ds-chat">
    <!-- 遮罩（移动端） -->
    <div v-if="sidebarOpen && isMobile" class="ds-overlay" @click="sidebarOpen = false"></div>

    <!-- 侧边栏 -->
    <aside class="ds-sidebar" :class="{ open: sidebarOpen, collapsed: !sidebarOpen && !isMobile }">
      <div class="ds-sidebar-header">
        <button class="ds-btn-new" @click="handleNewChat">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          <span v-if="sidebarOpen">{{ t('newChat') }}</span>
        </button>
      </div>

      <div class="ds-conv-list">
        <div v-if="loadingConversations" class="ds-list-loading"><a-spin /></div>
        <div v-else-if="conversations.length === 0" class="ds-list-empty"><a-empty /></div>
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="ds-conv-item"
          :class="{ active: conv.id === currentConversationId }"
          @click="switchConversation(conv.id)"
        >
          <template v-if="editingTitleId === conv.id">
            <input
              v-model="editingTitleValue"
              class="ds-title-input"
              @blur="saveTitle(conv)"
              @keydown.enter="saveTitle(conv)"
              @keydown.escape="cancelEditTitle"
              @click.stop
              ref="titleInputRef"
            />
          </template>
          <template v-else>
            <span class="ds-conv-title" @dblclick.stop="startEditTitle(conv)">{{ conv.title }}</span>
            <span class="ds-conv-time" v-if="conv.updated_at">{{ formatTime(conv.updated_at) }}</span>
          </template>
          <button class="ds-btn-edit" @click.stop="startEditTitle(conv)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
          <button class="ds-btn-del" @click.stop="confirmDeleteChat(conv)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          </button>
        </div>
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="ds-main">
      <!-- 顶部栏 -->
      <header class="ds-topbar">
        <button class="ds-btn-menu" @click="sidebarOpen = !sidebarOpen">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>
        <span class="ds-title">{{ t('aiChat') }}</span>
      </header>

      <!-- 消息区 -->
      <div class="ds-messages" ref="messageListRef">
        <div v-if="messages.length === 0 && !streaming" class="ds-welcome">
          <div class="ds-welcome-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          </div>
          <h2>{{ t('aiChat') }}</h2>
          <p class="ds-welcome-sub">{{ t('noMessages') }}</p>
        </div>

        <div v-for="(msg, idx) in messages" :key="msg.id || idx" class="ds-msg" :class="msg.role">
          <div class="ds-msg-avatar">
            <div class="ds-avatar" :class="msg.role">
              {{ msg.role === 'user' ? 'U' : 'AI' }}
            </div>
          </div>
          <div class="ds-msg-body">
            <div class="ds-msg-content" v-html="renderMessage(msg.content)"></div>
            <div class="ds-msg-actions">
              <button class="ds-act-btn" title="复制" @click="copyMessage(msg.content)">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              </button>
              <button class="ds-act-btn ds-act-del" title="删除" @click="confirmDeleteMessage(msg)">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </button>
            </div>
          </div>
        </div>

        <div v-if="streaming && (streamingContent || streamingReasoning || streamingToolStatus || pendingConfirm)" class="ds-msg assistant">
          <div class="ds-msg-avatar">
            <div class="ds-avatar assistant">AI</div>
          </div>
          <div class="ds-msg-body">
            <!-- 思考过程 -->
            <div v-if="streamingReasoning" class="ds-reasoning-block">
              <div class="ds-reasoning-header">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
                <span>{{ t('thinking') }}</span>
              </div>
              <div class="ds-reasoning-content">{{ streamingReasoning }}</div>
            </div>
            <!-- 工具执行状态 -->
            <div v-if="streamingToolStatus" class="ds-tool-status">
              <a-spin :size="14" />
              <span>{{ t('executingTool')}}: {{ streamingToolStatus }}</span>
            </div>
            <!-- 高风险操作确认（内联卡片） -->
            <div v-if="pendingConfirm" class="ds-confirm-card">
              <div class="ds-confirm-header">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                <span>{{ t('highRiskConfirmTitle') }}</span>
              </div>
              <div class="ds-confirm-body">
                <p class="ds-confirm-tool"><strong>{{ pendingConfirm.tool_name }}</strong></p>
                <pre class="ds-confirm-args">{{ JSON.stringify(pendingConfirm.arguments, null, 2) }}</pre>
              </div>
              <div class="ds-confirm-actions">
                <button class="ds-btn-confirm-allow" @click="handleConfirmAllow">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                  {{ t('confirmAllow') }}
                </button>
                <button class="ds-btn-confirm-deny" @click="handleConfirmDeny">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  {{ t('confirmDeny') }}
                </button>
              </div>
            </div>
            <!-- 流式文本 -->
            <div v-if="streamingContent" class="ds-msg-content" v-html="renderMessage(streamingContent)"></div>
          </div>
        </div>

        <!-- AI 思考前摇（无内容时） -->
        <div v-if="streaming && !streamingContent && !streamingReasoning && !streamingToolStatus" class="ds-msg assistant">
          <div class="ds-msg-avatar">
            <div class="ds-avatar assistant">AI</div>
          </div>
          <div class="ds-msg-body">
            <div class="ds-msg-content ds-thinking-indicator">
              <span class="ds-dot ds-dot-1">.</span>
              <span class="ds-dot ds-dot-2">.</span>
              <span class="ds-dot ds-dot-3">.</span>
            </div>
          </div>
        </div>

        <div v-if="loadingMessages" class="ds-msg-loading">
          <a-spin :size="18" />
        </div>
      </div>

      <!-- 输入区 -->
      <div class="ds-input-area">
        <div class="ds-input-box" @drop.prevent="handleDrop" @dragover.prevent="dragOver = true" @dragleave.prevent="dragOver = false" :class="{ 'ds-drag-over': dragOver }">
          <textarea
            v-model="inputMessage"
            :placeholder="selectedModelId ? t('typeYourMessage') : t('selectModel')"
            :disabled="!selectedModelId || streaming"
            rows="1"
            class="ds-textarea"
            @keydown="onInputKeydown"
            @input="autoResize"
            @paste="handlePaste"
          ></textarea>
          <!-- 已勾选的工具标签（智能 OFF 时显示） -->
          <div v-if="!smartMode && selectedToolTags.length > 0" class="ds-tool-tags">
            <span
              v-for="tag in selectedToolTags"
              :key="tag.id"
              class="ds-tool-tag"
            >
              <span>{{ tag.name }}</span>
              <button class="ds-tool-tag-del" @click="removeTool(tag.id)" title="移除">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </span>
          </div>
          <!-- 已上传的文件列表 -->
          <div v-if="attachedFiles.length > 0" class="ds-file-list">
            <span
              v-for="(f, fi) in attachedFiles"
              :key="fi"
              class="ds-file-chip"
              :title="f.path"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>
              <span class="ds-file-chip-name">{{ f.name }}</span>
              <button class="ds-tool-tag-del" @click="removeFile(fi)" title="移除">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </span>
          </div>
          <div class="ds-input-toolbar">
            <div class="ds-input-left">
              <a-dropdown trigger="click" :popup-visible="selectOpen" @popup-visible-change="selectOpen = $event" position="top">
                <a-input :model-value="selectedModelName" :placeholder="t('selectModel')" readonly size="mini" class="ds-input-model-select" :style="{ maxWidth: '200px', cursor: 'pointer' }" />
                <template #content>
                  <div class="ds-custom-select">
                    <template v-for="(models, providerKey) in groupedModels" :key="providerKey">
                      <div class="ds-custom-group-label">{{ providerNameMap[providerKey] || providerKey }}</div>
                      <div
                        v-for="m in models"
                        :key="m.id"
                        class="ds-custom-option"
                        :class="{ active: m.id === selectedModelId }"
                        @click="selectModel(m.id)"
                      >{{ m.name }}</div>
                    </template>
                  </div>
                </template>
              </a-dropdown>
              <!-- 附件上传按钮（下拉菜单：本地上传 / 服务器文件选择） -->
              <a-dropdown trigger="click" position="top">
                <button class="ds-btn-toolcfg" :class="{ active: attachedFiles.length > 0 }">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
                  <span>{{ t('attachments') }}</span>
                </button>
                <template #content>
                  <div class="ds-toolcfg-menu">
                    <label class="ds-toolcfg-item" @click.stop="triggerFileInput">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                      <span>{{ t('uploadLocalFile') }}</span>
                    </label>
                    <label class="ds-toolcfg-item" @click.stop="openServerFilePicker">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                      <span>{{ t('selectServerFile') }}</span>
                    </label>
                  </div>
                </template>
              </a-dropdown>
              <input ref="fileInputRef" type="file" multiple class="ds-file-input-hidden" @change="handleFileSelected" />
              <!-- MiniFileManager 服务器文件选择 -->
              <MiniFileManager
                v-model:visible="miniFileVisible"
                :initial-path="serverFilePath"
                :select-mode="'file'"
                @select="onServerFileSelected"
              />
              <!-- 智能模式开关按钮 -->
              <button class="ds-btn-toolcfg" :class="{ active: smartMode }" @click="smartMode = !smartMode">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l2 7h7l-5.5 4 2 7L12 16l-5.5 4 2-7L3 9h7z"/></svg>
                <span>{{ t('smartMode') }}</span>
              </button>
              <!-- 联网搜索 + 工具独立按钮（关闭智能模式时显示） -->
              <template v-if="!smartMode">
                <!-- 工具选择下拉按钮 -->
                <a-dropdown trigger="click" position="top">
                  <button class="ds-btn-toolcfg" :class="{ active: hasAnyToolChecked }">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="9" x2="15" y2="9"/><line x1="9" y1="13" x2="13" y2="13"/></svg>
                    <span>{{ t('tools') }}</span>
                  </button>
                  <template #content>
                    <div class="ds-toolcfg-menu">
                      <label
                        v-for="ts in toolsets"
                        :key="ts.id"
                        class="ds-toolcfg-item"
                        @click.stop="checkedToolsets[ts.id] = !checkedToolsets[ts.id]"
                      >
                        <svg v-if="checkedToolsets[ts.id]" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                        <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/></svg>
                        <span>{{ ts.name }}</span>
                      </label>
                    </div>
                  </template>
                </a-dropdown>
                 <!-- 联网搜索开关按钮 -->
                <button class="ds-btn-toolcfg" :class="{ active: webSearchEnabled }" @click="webSearchEnabled = !webSearchEnabled">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  <span>{{ t('webSearch') }}</span>
                </button>
              </template>
            </div>
            <button
              v-if="streaming"
              class="ds-btn-send ds-btn-stop"
              @click="stopStreaming"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
            </button>
            <button
              v-else
              class="ds-btn-send"
              :disabled="(!inputMessage.trim() && attachedFiles.length === 0) || !selectedModelId || sending"
              @click="sendMessage"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 删除对话确认 -->
    <a-modal
      :visible="deleteModalVisible"
      @ok="handleDeleteChat"
      @cancel="cancelDelete"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
      :simple="true"
    >
      <template #title>{{ t('deleteChat') }}</template>
      <div>{{ t('confirmDeleteChat') }}</div>
    </a-modal>

    <!-- 删除消息确认 -->
    <a-modal
      :visible="deleteMsgModalVisible"
      @ok="handleDeleteMessage"
      @cancel="cancelDeleteMessage"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
      :simple="true"
    >
      <template #title>{{ t('deleteChat') }}</template>
      <div>{{ t('confirmDeleteChat') }}</div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { t } from '../../utils/locale'
import {
  getAiModelList,
  getAiConversations,
  createAiConversation,
  deleteAiConversation,
  updateAiConversation,
  getAiMessages,
  deleteAiMessage,
  switchAiConversationModel,
  streamChatWithAi,
  confirmAiTool,
  getAiToolsets,
  uploadAiFile,
} from '../../api/ai'
import { Message } from '@arco-design/web-vue'
import { renderMessage } from '../../utils/ai/md'
import MiniFileManager from '../../components/file/MiniFileManager.vue'

// ============ 状态 ============
const isMobile = ref(window.innerWidth <= 768)
const sidebarOpen = ref(!isMobile.value)
const selectedModelId = ref(null)
const modelList = ref([])
const conversations = ref([])
const currentConversationId = ref(null)
const messages = ref([])
const inputMessage = ref('')
const sending = ref(false)
const streaming = ref(false)
const streamingContent = ref('')
const streamingReasoning = ref('')
const streamingToolStatus = ref('')
const loadingConversations = ref(false)
const loadingMessages = ref(false)
const messageListRef = ref(null)
const abortController = ref(null)

// 高风险操作确认（内联卡片）
const pendingConfirm = ref(null)

// 文件上传
const attachedFiles = ref([])  // { path, name, size }
const fileInputRef = ref(null)
const uploading = ref(false)
const dragOver = ref(false)

function triggerFileInput() {
  fileInputRef.value?.click()
}

async function handleFileSelected(e) {
  const files = e.target.files
  if (!files || files.length === 0) return
  uploadFiles(Array.from(files))
  e.target.value = ''  // 清空 input 允许重复选同一文件
}

function handlePaste(e) {
  const items = e.clipboardData?.items
  if (!items) return
  const files = []
  for (const item of items) {
    if (item.type.startsWith('image/') || item.kind === 'file') {
      const file = item.getAsFile()
      if (file) files.push(file)
    }
  }
  if (files.length > 0) {
    e.preventDefault()
    uploadFiles(files)
  }
}

function handleDrop(e) {
  dragOver.value = false
  const files = e.dataTransfer?.files
  if (files && files.length > 0) {
    uploadFiles(Array.from(files))
  }
}

async function uploadFiles(fileList) {
  uploading.value = true
  let successCount = 0
  for (const file of fileList) {
    try {
      const res = await uploadAiFile(file)
      attachedFiles.value.push({
        path: res.path,
        name: res.name,
        size: res.size,
      })
      successCount++
    } catch {
      Message.error(`上传失败: ${file.name}`)
    }
  }
  uploading.value = false
}

function removeFile(index) {
  attachedFiles.value.splice(index, 1)
}

// 服务器文件选择（MiniFileManager）
const miniFileVisible = ref(false)
const serverFilePath = ref('/')

function openServerFilePicker() {
  serverFilePath.value = '/'
  miniFileVisible.value = true
}

function onServerFileSelected(selection) {
  // selection: { path: string, name?: string }
  if (!selection || !selection.path) return
  const fullPath = selection.name
    ? (selection.path === '/' ? `/${selection.name}` : `${selection.path}/${selection.name}`)
    : selection.path
  // 检查是否已存在
  if (attachedFiles.value.some(f => f.path === fullPath)) return
  attachedFiles.value.push({
    path: fullPath,
    name: selection.name || selection.path.split('/').pop() || '目录',
    size: 0,
    isServerFile: true,
  })
}

// 智能模式（默认开启）
const smartMode = ref(true)

// 联网搜索独立开关
const webSearchEnabled = ref(false)

// 工具集列表（从后端动态加载，关闭智能模式时手动选择）
const toolsets = ref([])
const checkedToolsets = ref({})  // { 'system': true, 'file': false, ... }

// 加载工具集列表
async function loadToolsets() {
  try {
    const res = await getAiToolsets()
    toolsets.value = res.toolsets || []
    // 默认全不勾选
    const initChecked = {}
    for (const ts of toolsets.value) {
      initChecked[ts.id] = false
    }
    checkedToolsets.value = initChecked
  } catch {
    // 静默失败
  }
}

// 从勾选的工具集 + 联网搜索开关中提取工具 ID 列表（仅智能模式 OFF 时使用）
const enabledTools = computed(() => {
  // 智能模式 ON：不传 enabled_tools，一切由后端自动管理
  if (smartMode.value) return null

  const toolIds = new Set()

  // 联网搜索独立开关
  if (webSearchEnabled.value) {
    toolIds.add('web_search')
  }

  // 手动勾选的工具集
  for (const ts of toolsets.value) {
    if (checkedToolsets.value[ts.id]) {
      for (const t of (ts.tools || [])) {
        toolIds.add(t)
      }
    }
  }

  return toolIds.size > 0 ? Array.from(toolIds) : null
})

// 是否有任意工具被勾选（用于工具按钮高亮）
const hasAnyToolChecked = computed(() => {
  for (const ts of toolsets.value) {
    if (checkedToolsets.value[ts.id]) return true
  }
  return false
})

// 已勾选工具标签列表（显示在输入框上方）
const selectedToolTags = computed(() => {
  return toolsets.value.filter(ts => checkedToolsets.value[ts.id])
})

// 移除工具（点击标签 × 按钮）
function removeTool(toolsetId) {
  checkedToolsets.value[toolsetId] = false
}

// 自定义模型选择下拉
const selectOpen = ref(false)
const selectedModelName = computed(() => {
  const m = modelList.value.find(x => x.id === selectedModelId.value)
  return m ? m.name : ''
})
function selectModel(id) {
  selectedModelId.value = id
  selectOpen.value = false
  onModelChange()
}

// 删除
const deleteModalVisible = ref(false)
const deleteTarget = ref(null)

// 删除消息
const deleteMsgModalVisible = ref(false)
const deleteMsgTarget = ref(null)

// 标题编辑
const editingTitleId = ref(null)
const editingTitleValue = ref('')
const titleInputRef = ref(null)

// ============ 模型分组 ============
const providerNameMap = {
  openai: 'OpenAI',
  deepseek: 'DeepSeek',
  ollama: 'Ollama',
  longcat: 'Longcat',
  vllm: 'vLLM',
  openrouter: 'OpenRouter',
  azure: 'Azure',
  anthropic: 'Anthropic',
  google: 'Google',
  zhipu: '智谱AI',
  baidu: '百度文心',
  alibaba: '阿里通义',
  xiaomi: '小米MiMo',
  custom: '自定义',
}

const groupedModels = computed(() => {
  const groups = {}
  for (const m of modelList.value) {
    const key = m.provider || 'other'
    if (!groups[key]) groups[key] = []
    groups[key].push(m)
  }
  return groups
})

// ============ 响应式 ============
window.addEventListener('resize', () => {
  isMobile.value = window.innerWidth <= 768
})

// ============ 模型加载 ============
async function loadModels() {
  try {
    const res = await getAiModelList({ limit: 500 })
    modelList.value = res.items || []
    if (modelList.value.length > 0 && !selectedModelId.value) {
      const defaultModel = modelList.value.find(m => m.is_default)
      selectedModelId.value = defaultModel ? defaultModel.id : modelList.value[0].id
    }
  } catch {
    // silent
  }
}

// ============ 对话管理 ============
async function loadConversations() {
  loadingConversations.value = true
  try {
    const res = await getAiConversations({ limit: 100 })
    conversations.value = res.items || []
  } catch {
    Message.error(t.value('loadConversationsFailed'))
  } finally {
    loadingConversations.value = false
  }
}

async function switchConversation(convId) {
  if (convId === currentConversationId.value) return
  currentConversationId.value = convId
  if (isMobile.value) sidebarOpen.value = false
  await loadMessages(convId)
}

async function loadMessages(convId) {
  loadingMessages.value = true
  messages.value = []
  try {
    const res = await getAiMessages(convId, { limit: 200 })
    messages.value = res.items || []
    await scrollToBottom()
  } catch {
    Message.error(t.value('loadMessagesFailed'))
  } finally {
    loadingMessages.value = false
  }
}

function handleNewChat() {
  currentConversationId.value = null
  messages.value = []
  inputMessage.value = ''
  if (isMobile.value) sidebarOpen.value = false
}

function confirmDeleteChat(conv) {
  deleteTarget.value = conv
  deleteModalVisible.value = true
}

function cancelDelete() {
  deleteModalVisible.value = false
  deleteTarget.value = null
}

async function handleDeleteChat() {
  if (!deleteTarget.value) return
  try {
    await deleteAiConversation(deleteTarget.value.id)
    Message.success(t.value('deleteChatSuccess'))
    conversations.value = conversations.value.filter(c => c.id !== deleteTarget.value.id)
    if (currentConversationId.value === deleteTarget.value.id) {
      currentConversationId.value = null
      messages.value = []
    }
  } catch {
    Message.error(t.value('deleteConversationFailed'))
  } finally {
    deleteModalVisible.value = false
    deleteTarget.value = null
  }
}

// ============ 删除消息 ============
function confirmDeleteMessage(msg) {
  deleteMsgTarget.value = msg
  deleteMsgModalVisible.value = true
}

function cancelDeleteMessage() {
  deleteMsgModalVisible.value = false
  deleteMsgTarget.value = null
}

async function handleDeleteMessage() {
  if (!deleteMsgTarget.value || !currentConversationId.value) return
  try {
    await deleteAiMessage(currentConversationId.value, deleteMsgTarget.value.id)
    Message.success(t.value('deleteChatSuccess'))
    messages.value = messages.value.filter(m => m.id !== deleteMsgTarget.value.id)
  } catch {
    Message.error(t.value('deleteConversationFailed'))
  } finally {
    deleteMsgModalVisible.value = false
    deleteMsgTarget.value = null
  }
}

// ============ 复制消息 ============
function copyMessage(content) {
  try {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(content).then(() => {
        Message.success(t.value('copySuccess'))
      }).catch(() => fallbackCopy(content))
    } else {
      fallbackCopy(content)
    }
  } catch {
    fallbackCopy(content)
  }
}

function fallbackCopy(text) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  try {
    document.execCommand('copy')
    Message.success(t.value('copySuccess'))
  } catch {
    Message.error(t.value('copyFailed'))
  }
  document.body.removeChild(textarea)
}

// ============ 标题编辑 ============
function startEditTitle(conv) {
  editingTitleId.value = conv.id
  editingTitleValue.value = conv.title
  nextTick(() => {
    const el = titleInputRef.value
    if (el && el.length) {
      el[el.length - 1]?.focus?.()
    } else if (el) {
      el.focus?.()
    }
  })
}

async function saveTitle(conv) {
  const newTitle = editingTitleValue.value.trim()
  if (!newTitle || newTitle === conv.title) {
    cancelEditTitle()
    return
  }
  try {
    await updateAiConversation(conv.id, { title: newTitle })
    conv.title = newTitle
  } catch {
    // silent
  } finally {
    cancelEditTitle()
  }
}

function cancelEditTitle() {
  editingTitleId.value = null
  editingTitleValue.value = ''
}

// ============ 发送消息 ============
async function sendMessage() {
  const text = inputMessage.value.trim()
  if ((!text && attachedFiles.value.length === 0) || !selectedModelId.value) return

  // 在清空前保存文件路径和第一个文件名
  const currentFiles = attachedFiles.value.map(f => f.path)
  const firstFileName = attachedFiles.value.length > 0 ? attachedFiles.value[0].name : ''

  inputMessage.value = ''
  attachedFiles.value = []
  resetTextarea()

  if (!currentConversationId.value) {
    try {
      const selectedModel = modelList.value.find(m => m.id === selectedModelId.value)
      const conv = await createAiConversation({
        model_id: selectedModelId.value,
        model_name: selectedModel ? selectedModel.model_name : '',
        title: text.slice(0, 100) || firstFileName || t('aiChat'),
      })
      conversations.value.unshift(conv)
      currentConversationId.value = conv.id
    } catch {
      Message.error(t.value('createConversationFailed'))
      return
    }
  }

  messages.value.push({ id: Date.now(), role: 'user', content: text })
  await scrollToBottom()

  sending.value = true
  try {
    await streamChat(text, currentFiles)
  } catch {
    Message.error(t.value('sendMessageFailed'))
  } finally {
    sending.value = false
    await scrollToBottom()
  }
}

async function streamChat(text, files = []) {
  streaming.value = true
  streamingContent.value = ''
  streamingReasoning.value = ''
  streamingToolStatus.value = ''
  abortController.value = new AbortController()

  try {
    const requestBody = {
      model_id: selectedModelId.value,
      conversation_id: currentConversationId.value,
      message: text,
      smart_mode: smartMode.value,
      files: files,
    }
    // 组装启用的工具（联网搜索 + 手动勾选的工具集）
    if (enabledTools.value && enabledTools.value.length > 0) {
      requestBody.enabled_tools = enabledTools.value
    }
    const response = await streamChatWithAi(requestBody, abortController.value.signal)

    if (!response.ok) throw new Error(`HTTP ${response.status}`)

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (!line.trim() || !line.startsWith('data: ')) continue
        const data = line.slice(6)
        if (data === '[DONE]') break
        try {
          const event = JSON.parse(data)
          if (event.type === 'session') {
            currentConversationId.value = event.conversation_id
          } else if (event.type === 'content') {
            streamingContent.value += event.content
            await scrollToBottom()
          } else if (event.type === 'reasoning') {
            streamingReasoning.value += event.content
            await scrollToBottom()
          } else if (event.type === 'tool_confirm') {
            // 高风险操作，内联确认卡片
            pendingConfirm.value = {
              tool_name: event.tool_name,
              call_id: event.call_id,
              arguments: event.arguments || {},
            }
            await scrollToBottom()
          } else if (event.type === 'tool_executing') {
            streamingToolStatus.value = event.tool_name
            await scrollToBottom()
          } else if (event.type === 'tool_result') {
            streamingToolStatus.value = ''
          } else if (event.type === 'stop') {
            // Agent 正常结束
            break
          } else if (event.type === 'error') {
            Message.error(event.message || t.value('sendMessageFailed'))
          }
        } catch {}
      }
    }
  } catch (err) {
    if (err.name === 'AbortError') return
    throw err
  } finally {
    streaming.value = false
    streamingToolStatus.value = ''
    pendingConfirm.value = null
    const finalContent = streamingContent.value
    if (finalContent) {
      messages.value.push({ id: Date.now(), role: 'assistant', content: finalContent })
      streamingContent.value = ''
    }
    streamingReasoning.value = ''
    abortController.value = null
    // 刷新会话列表（获取自动生成的标题）
    await loadConversations()
  }
}

function stopStreaming() {
  abortController.value?.abort()
}

// ============ 高风险操作确认（内联卡片） ============
async function handleConfirmAllow() {
  const pc = pendingConfirm.value
  if (!pc || !pc.call_id || !currentConversationId.value) return
  try {
    await confirmAiTool({
      conversation_id: currentConversationId.value,
      call_id: pc.call_id,
      confirmed: true,
    })
    pendingConfirm.value = null
  } catch {
    Message.error(t.value('toolConfirmFailed'))
  }
}

async function handleConfirmDeny() {
  const pc = pendingConfirm.value
  if (!pc || !pc.call_id || !currentConversationId.value) return
  try {
    await confirmAiTool({
      conversation_id: currentConversationId.value,
      call_id: pc.call_id,
      confirmed: false,
    })
    pendingConfirm.value = null
  } catch {
    Message.error(t.value('toolConfirmFailed'))
  }
}

// ============ 工具函数 ============
async function scrollToBottom() {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

function onInputKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 200) + 'px'
}

function resetTextarea() {
  nextTick(() => {
    const el = document.querySelector('.ds-textarea')
    if (el) el.style.height = 'auto'
  })
}

function onModelChange() {
  // 切换模型时更新当前对话的模型信息
  if (currentConversationId.value) {
    const selectedModel = modelList.value.find(m => m.id === selectedModelId.value)
    if (selectedModel) {
      switchAiConversationModel(currentConversationId.value, {
        model_id: selectedModel.id,
        model_name: selectedModel.model_name
      }).then(() => {
        // 模型切换后重新加载消息（旧模型的回复已被后端清除）
        loadMessages(currentConversationId.value)
      }).catch(() => {})
    }
  }
}

function formatTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now - d
  // 今天
  if (diff < 86400000 && d.getDate() === now.getDate()) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  // 昨天
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  if (d.getDate() === yesterday.getDate() && d.getMonth() === yesterday.getMonth() && d.getFullYear() === yesterday.getFullYear()) {
    return '昨天 ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  // 今年
  if (d.getFullYear() === now.getFullYear()) {
    return (d.getMonth() + 1) + '/' + d.getDate() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  // 更早
  return d.getFullYear() + '/' + (d.getMonth() + 1) + '/' + d.getDate()
}

// ============ 初始化 ============
onMounted(async () => {
  await loadModels()
  await loadToolsets()
  await loadConversations()
})
</script>

<style scoped>
/* ===== 全局 ===== */
.ds-chat {
  display: flex;
  height: calc(100vh - 140px);
  background: var(--color-bg-1);
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* ===== 遮罩 ===== */
.ds-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  z-index: 99;
}

/* ===== 侧边栏 ===== */
.ds-sidebar {
  width: 260px;
  min-width: 260px;
  background: var(--color-bg-2);
  border-right: 1px solid var(--color-border-2);
  display: flex;
  flex-direction: column;
  transition: transform 0.25s ease;
  z-index: 100;
}

@media (max-width: 768px) {
  .ds-sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    transform: translateX(-100%);
    box-shadow: 2px 0 12px rgba(0,0,0,0.15);
  }
  .ds-sidebar.open {
    transform: translateX(0);
  }
}

/* 桌面端收起 */
.ds-sidebar.collapsed {
  width: 52px;
  min-width: 52px;
  overflow: hidden;
}

.ds-sidebar.collapsed .ds-sidebar-header {
  flex-direction: column;
  padding: 8px;
}

.ds-sidebar.collapsed .ds-btn-new {
  padding: 8px;
}

.ds-sidebar.collapsed .ds-conv-list,
.ds-sidebar.collapsed .ds-btn-new span {
  display: none;
}

.ds-sidebar-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
}

.ds-btn-new {
  flex: 1;
  padding: 10px;
  border: 1px solid var(--color-border-2);
  border-radius: 8px;
  background: transparent;
  color: var(--color-text-1);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 14px;
  transition: background 0.2s;
}

.ds-btn-new:hover {
  background: var(--color-fill-2);
}

.ds-btn-sidebar-toggle {
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-border-2);
  border-radius: 8px;
  background: transparent;
  color: var(--color-text-2);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.2s, color 0.2s;
}

.ds-btn-sidebar-toggle:hover {
  background: var(--color-fill-2);
  color: var(--color-text-1);
}

.ds-conv-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.ds-list-loading,
.ds-list-empty {
  text-align: center;
  padding: 24px;
  color: var(--color-text-3);
  font-size: 13px;
}

.ds-conv-item {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  cursor: pointer;
  gap: 4px;
  border-radius: 0;
  transition: background 0.15s;
  margin: 0 0;
  border-bottom: 1px solid var(--color-border-2);
  flex-wrap: wrap;
}

.ds-conv-item:last-child {
  border-bottom: none;
}

.ds-conv-item:hover {
  background: var(--color-fill-2);
}

.ds-conv-item.active {
  background: var(--color-primary-light-1);
}

.ds-conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  color: var(--color-text-1);
  min-width: 0;
}

.ds-conv-time {
  font-size: 11px;
  color: var(--color-text-4);
  white-space: nowrap;
  margin-left: auto;
  padding-left: 8px;
  flex-shrink: 0;
}

.ds-title-input {
  flex: 1;
  padding: 4px 8px;
  border: 1px solid rgb(var(--primary-6));
  border-radius: 4px;
  outline: none;
  font-size: 14px;
  background: var(--color-bg-1);
  color: var(--color-text-1);
}

.ds-btn-del,
.ds-btn-edit {
  opacity: 0;
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  color: var(--color-text-3);
  border-radius: 4px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.ds-conv-item:hover .ds-btn-del,
.ds-conv-item:hover .ds-btn-edit {
  opacity: 1;
}

.ds-btn-del:hover {
  color: rgb(var(--danger-6));
  background: var(--color-fill-3);
}

.ds-btn-edit:hover {
  color: rgb(var(--primary-6));
  background: var(--color-fill-3);
}

/* ===== 主区域 ===== */
.ds-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  position: relative;
}

/* ===== 顶部栏 ===== */
.ds-topbar {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid var(--color-border-2);
  gap: 12px;
  min-height: 48px;
}

.ds-btn-menu {
  background: none;
  border: none;
  padding: 6px;
  cursor: pointer;
  color: var(--color-text-2);
  border-radius: 6px;
  display: flex;
}

.ds-btn-menu:hover {
  background: var(--color-fill-2);
  color: var(--color-text-1);
}

.ds-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-1);
}

/* ===== 消息区 ===== */
.ds-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 16px;
  scroll-behavior: smooth;
}

.ds-welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-3);
  text-align: center;
}

.ds-welcome-icon {
  margin-bottom: 16px;
  opacity: 0.4;
}

.ds-welcome h2 {
  margin: 0 0 8px;
  font-weight: 600;
  font-size: 20px;
  color: var(--color-text-1);
}

.ds-welcome-sub {
  margin: 0;
  font-size: 14px;
}

.ds-msg {
  display: flex;
  gap: 12px;
  max-width: 860px;
  margin: 0 auto 20px;
  animation: dsFadeIn 0.2s ease;
}

@keyframes dsFadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.ds-msg.user {
  flex-direction: row-reverse;
  margin-left: auto;
}

.ds-msg-avatar {
  flex-shrink: 0;
}

.ds-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
}

.ds-avatar.assistant {
  background: rgb(var(--primary-6));
  color: #fff;
}

.ds-avatar.user {
  background: var(--color-fill-3);
  color: var(--color-text-2);
}

.ds-msg-body {
  max-width: calc(100% - 44px);
}

.ds-msg.user .ds-msg-body {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.ds-msg-content {
  display: inline-block;
  max-width: 100%;
  padding: 10px 16px;
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.6;
  word-wrap: break-word;
}

.ds-msg.user .ds-msg-content {
  background: rgb(var(--primary-6));
  color: #fff;
  border-bottom-right-radius: 4px;
}

.ds-msg.assistant .ds-msg-content {
  background: var(--color-fill-2);
  color: var(--color-text-1);
  border-bottom-left-radius: 4px;
}

.ds-msg-content :deep(h1),
.ds-msg-content :deep(h2),
.ds-msg-content :deep(h3),
.ds-msg-content :deep(h4) {
  margin: 16px 0 8px;
  font-weight: 600;
  line-height: 1.3;
}
.ds-msg-content :deep(h1) { font-size: 22px; }
.ds-msg-content :deep(h2) { font-size: 19px; }
.ds-msg-content :deep(h3) { font-size: 17px; }

.ds-msg-content :deep(p) {
  margin: 6px 0;
}
.ds-msg-content :deep(p:first-child) {
  margin-top: 0;
}
.ds-msg-content :deep(p:last-child) {
  margin-bottom: 0;
}

.ds-msg-content :deep(code) {
  background: var(--color-fill-3);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', Consolas, monospace;
}

.ds-msg-content :deep(pre) {
  margin: 0;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
  font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', Consolas, monospace;
}

.ds-msg-content :deep(pre code) {
  background: none;
  padding: 0;
  font-size: inherit;
  color: inherit;
}

.ds-code-block {
  margin: 10px 0;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--color-border-2);
  background: var(--color-bg-2);
}

.ds-code-lang {
  display: block;
  padding: 4px 12px;
  font-size: 11px;
  color: var(--color-text-3);
  background: var(--color-fill-1);
  border-bottom: 1px solid var(--color-border-2);
  text-transform: lowercase;
}

.ds-code-block pre {
  padding: 12px 16px;
  margin: 0;
}

.ds-msg-content :deep(blockquote) {
  margin: 8px 0;
  padding: 6px 12px;
  border-left: 3px solid rgb(var(--primary-6));
  background: var(--color-fill-1);
  border-radius: 0 6px 6px 0;
  color: var(--color-text-2);
  font-size: 14px;
}

.ds-msg-content :deep(blockquote p) {
  margin: 2px 0;
}

.ds-msg-content :deep(table) {
  margin: 8px 0;
  border-collapse: collapse;
  font-size: 13px;
  width: 100%;
  overflow-x: auto;
  display: block;
}

.ds-msg-content :deep(th),
.ds-msg-content :deep(td) {
  padding: 6px 12px;
  border: 1px solid var(--color-border-2);
  text-align: left;
  white-space: nowrap;
}

.ds-msg-content :deep(th) {
  background: var(--color-fill-1);
  font-weight: 600;
}

.ds-msg-content :deep(ul),
.ds-msg-content :deep(ol) {
  margin: 6px 0;
  padding-left: 24px;
}

.ds-msg-content :deep(li) {
  margin: 3px 0;
}

.ds-msg-content :deep(hr) {
  margin: 12px 0;
  border: none;
  border-top: 1px solid var(--color-border-2);
}

.ds-msg-content :deep(a) {
  color: rgb(var(--primary-6));
  text-decoration: none;
}
.ds-msg-content :deep(a:hover) {
  text-decoration: underline;
}

.ds-msg-content :deep(img.ds-md-img) {
  max-width: 100%;
  border-radius: 8px;
  margin: 8px 0;
}

.ds-msg-content :deep(del) {
  color: var(--color-text-3);
  text-decoration: line-through;
}

.ds-msg-content :deep(strong) {
  font-weight: 600;
}

.ds-msg-content :deep(em) {
  font-style: italic;
}

.ds-msg-actions {
  display: flex;
  gap: 4px;
  margin-top: 4px;
  opacity: 0;
  transition: opacity 0.15s;
}

.ds-msg-body:hover .ds-msg-actions {
  opacity: 1;
}

.ds-msg.user .ds-msg-actions {
  justify-content: flex-end;
}

.ds-act-btn {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-3);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s;
}

.ds-act-btn:hover {
  background: var(--color-fill-3);
  color: var(--color-text-1);
}

.ds-act-del:hover {
  color: rgb(var(--danger-6));
}

.ds-msg-content :deep(pre) {
  background: var(--color-fill-3);
  border-radius: 8px;
  padding: 12px 16px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
  margin: 8px 0;
}

.ds-msg-content :deep(code) {
  background: var(--color-fill-3);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.ds-msg-loading {
  text-align: center;
  padding: 16px;
}

/* ===== 思考过程块 ===== */
.ds-reasoning-block {
  background: var(--color-fill-2);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
  font-size: 12px;
}

.ds-reasoning-header {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--color-text-3);
  font-weight: 500;
  margin-bottom: 6px;
}

.ds-reasoning-content {
  color: var(--color-text-3);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ===== 已勾选工具标签 ===== */
.ds-tool-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 0 6px;
  flex-wrap: wrap;
}

.ds-tool-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px 2px 10px;
  font-size: 12px;
  border-radius: 4px;
  background: var(--color-primary-light-1);
  color: rgb(var(--primary-6));
  border: 1px solid rgba(var(--primary-6), 0.2);
}

.ds-tool-tag-del {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border: none;
  border-radius: 3px;
  background: transparent;
  color: rgb(var(--primary-6));
  cursor: pointer;
  padding: 0;
  transition: background 0.12s;
}

.ds-tool-tag-del:hover {
  background: rgba(var(--primary-6), 0.15);
}

/* ===== 高风险操作确认卡片（内联） ===== */
.ds-confirm-card {
  margin: 8px 0;
  border: 1px solid rgb(var(--danger-6), 0.3);
  border-radius: 8px;
  background: var(--color-danger-light-1);
  overflow: hidden;
}

.ds-confirm-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  color: rgb(var(--danger-6));
  border-bottom: 1px solid rgb(var(--danger-6), 0.15);
}

.ds-confirm-body {
  padding: 10px 12px;
}

.ds-confirm-tool {
  font-size: 14px;
  margin-bottom: 6px;
}

.ds-confirm-args {
  font-size: 12px;
  background: rgba(0, 0, 0, 0.04);
  padding: 6px 8px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  color: var(--color-text-2);
}

.ds-confirm-actions {
  display: flex;
  gap: 8px;
  padding: 0 12px 10px;
}

.ds-btn-confirm-allow,
.ds-btn-confirm-deny {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  font-size: 12px;
  border-radius: 6px;
  cursor: pointer;
  border: none;
  transition: all 0.12s;
}

.ds-btn-confirm-allow {
  background: rgb(var(--success-6));
  color: #fff;
}
.ds-btn-confirm-allow:hover {
  background: rgb(var(--success-5));
}

.ds-btn-confirm-deny {
  background: var(--color-fill-3);
  color: var(--color-text-2);
}
.ds-btn-confirm-deny:hover {
  background: var(--color-fill-4);
}

/* ===== 联网搜索/工具配置按钮 ===== */
.ds-btn-toolcfg {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 6px;
  cursor: pointer;
  background: var(--color-fill-2);
  color: var(--color-text-3);
  border: 1px solid var(--color-border-2);
  transition: all 0.15s;
  white-space: nowrap;
}

.ds-btn-toolcfg:hover {
  background: var(--color-fill-3);
}

.ds-btn-toolcfg.active {
  background: rgb(var(--primary-6));
  color: #fff;
  border-color: rgb(var(--primary-6));
}

/* 工具配置下拉菜单 */
.ds-toolcfg-menu {
  min-width: 160px;
  padding: 6px 0;
}

.ds-toolcfg-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  font-size: 13px;
  color: var(--color-text-1);
  cursor: pointer;
  transition: background 0.12s;
  user-select: none;
}

.ds-toolcfg-item:hover {
  background: var(--color-fill-2);
}

.ds-toolcfg-item svg {
  flex-shrink: 0;
}

.ds-toolcfg-item svg:first-child {
  color: rgb(var(--primary-6));
}

.ds-toolcfg-divider {
  height: 1px;
  background: var(--color-border-2);
  margin: 4px 0;
}

.ds-toolcfg-label {
  padding: 4px 14px 2px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* ===== 工具执行状态 ===== */
.ds-tool-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--color-primary-light-1);
  border-radius: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  color: rgb(var(--primary-6));
}

/* ===== 输入区 ===== */
.ds-input-area {
  padding: 12px 16px 16px;
  border-top: 1px solid var(--color-border-2);
}

.ds-input-box {
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border: 1px solid var(--color-border-2);
  border-radius: 16px;
  padding: 14px 14px 8px 18px;
  background: var(--color-bg-2);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.ds-input-box:focus-within {
  border-color: rgb(var(--primary-6));
  box-shadow: 0 0 0 2px rgba(var(--primary-6), 0.1);
}

.ds-textarea {
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  color: var(--color-text-1);
  font-size: 16px;
  line-height: 1.6;
  font-family: inherit;
  max-height: 240px;
  min-height: 28px;
}

.ds-textarea::placeholder {
  color: var(--color-text-3);
}

.ds-input-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ds-input-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* ===== 自定义模型选择下拉 ===== */
.ds-custom-select {
  max-height: 320px;
  overflow-y: auto;
  min-width: 180px;
  max-width: 280px;
  padding: 4px 0;
}

.ds-custom-group-label {
  padding: 4px 12px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-3);
  line-height: 1.6;
  cursor: default;
}

.ds-custom-option {
  padding: 6px 12px 6px 12px;
  font-size: 13px;
  color: var(--color-text-1);
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: background 0.15s;
  border-left: 3px solid transparent;
}

.ds-custom-option:hover {
  background: var(--color-fill-2);
}

.ds-custom-option.active {
  color: rgb(var(--primary-6));
  font-weight: 500;
  border-left-color: rgb(var(--primary-6));
  background: var(--color-primary-light-1);
}

.ds-input-model-select {
  width: auto;
}

.ds-input-model-select :deep(.arco-input) {
  cursor: pointer;
  font-size: 12px;
}

.ds-btn-send {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 10px;
  background: rgb(var(--primary-6));
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.2s, opacity 0.2s;
}

.ds-btn-send:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.ds-btn-send:not(:disabled):hover {
  background: rgb(var(--primary-5));
}

.ds-btn-stop {
  background: var(--color-fill-3);
  color: var(--color-text-1);
}

.ds-btn-stop:hover {
  background: var(--color-fill-4);
}

/* ===== 思考前摇动画 ===== */
.ds-thinking-indicator {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 10px 16px !important;
  min-width: 48px;
  justify-content: center;
}

.ds-dot {
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
  color: var(--color-text-3);
  animation: dsBlink 1.4s infinite both;
}

.ds-dot-2 {
  animation-delay: 0.2s;
}

.ds-dot-3 {
  animation-delay: 0.4s;
}

@keyframes dsBlink {
  0%, 80%, 100% { opacity: 0.2; }
  40% { opacity: 1; }
}

/* ===== 文件上传 ===== */
.ds-file-input-hidden {
  display: none;
}

.ds-file-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ds-file-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: var(--color-primary-light-1);
  border: 1px solid rgba(var(--primary-6), 0.2);
  border-radius: 6px;
  font-size: 12px;
  color: rgb(var(--primary-6));
  max-width: 200px;
}

.ds-file-chip-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 140px;
}

.ds-drag-over {
  border-color: rgb(var(--primary-6)) !important;
  background: rgba(var(--primary-6), 0.04);
  box-shadow: 0 0 0 3px rgba(var(--primary-6), 0.12);
}
</style>
