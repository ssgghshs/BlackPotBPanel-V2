<template>
  <div class="ds-chat">
    <!-- 遮罩（移动端） -->
    <div v-if="sidebarOpen && isMobile" class="ds-overlay" @click="sidebarOpen = false"></div>

    <!-- 侧边栏 -->
    <aside class="ds-sidebar" :class="{ open: sidebarOpen }">
      <div class="ds-sidebar-header">
        <button class="ds-btn-new" @click="handleNewChat">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          {{ t('newChat') }}
        </button>
      </div>

      <div class="ds-conv-list">
        <div v-if="loadingConversations" class="ds-list-loading"><a-spin /></div>
        <div v-else-if="conversations.length === 0" class="ds-list-empty">{{ t('noConversations') }}</div>
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
        <div class="ds-model-picker">
          <select v-model="selectedModelId" class="ds-model-select" @change="onModelChange">
            <option v-for="m in modelList" :key="m.id" :value="m.id">{{ m.name }}</option>
          </select>
        </div>
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

        <div v-if="streaming && streamingContent" class="ds-msg assistant">
          <div class="ds-msg-avatar">
            <div class="ds-avatar assistant">AI</div>
          </div>
          <div class="ds-msg-body">
            <div class="ds-msg-content" v-html="renderMessage(streamingContent)"></div>
          </div>
        </div>

        <div v-if="loadingMessages" class="ds-msg-loading">
          <a-spin :size="18" />
        </div>
      </div>

      <!-- 输入区 -->
      <div class="ds-input-area">
        <div class="ds-input-box">
          <textarea
            v-model="inputMessage"
            :placeholder="selectedModelId ? t('typeYourMessage') : t('selectModel')"
            :disabled="!selectedModelId || streaming"
            rows="1"
            class="ds-textarea"
            @keydown="onInputKeydown"
            @input="autoResize"
          ></textarea>
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
            :disabled="!inputMessage.trim() || !selectedModelId || sending"
            @click="sendMessage"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          </button>
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
import { ref, onMounted, nextTick } from 'vue'
import { t } from '../../utils/locale'
import {
  getAiModelList,
  getAiConversations,
  createAiConversation,
  deleteAiConversation,
  updateAiConversation,
  getAiMessages,
  deleteAiMessage,
  streamChatWithAi,
} from '../../api/ai'
import { Message } from '@arco-design/web-vue'

// ============ 状态 ============
const sidebarOpen = ref(false)
const isMobile = ref(window.innerWidth <= 768)
const selectedModelId = ref(null)
const modelList = ref([])
const conversations = ref([])
const currentConversationId = ref(null)
const messages = ref([])
const inputMessage = ref('')
const sending = ref(false)
const streaming = ref(false)
const streamingContent = ref('')
const loadingConversations = ref(false)
const loadingMessages = ref(false)
const messageListRef = ref(null)
const abortController = ref(null)

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

async function handleNewChat() {
  if (!selectedModelId.value) {
    Message.warning(t.value('modelNotSelected'))
    return
  }
  try {
    const selectedModel = modelList.value.find(m => m.id === selectedModelId.value)
    const conv = await createAiConversation({
      model_id: selectedModelId.value,
      model_name: selectedModel ? selectedModel.model_name : '',
      title: t.value('newChat')
    })
    conversations.value.unshift(conv)
    currentConversationId.value = conv.id
    messages.value = []
    inputMessage.value = ''
    await scrollToBottom()
    if (isMobile.value) sidebarOpen.value = false
  } catch {
    Message.error(t.value('createConversationFailed'))
  }
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
  if (!text || !selectedModelId.value) return

  inputMessage.value = ''
  resetTextarea()

  if (!currentConversationId.value) {
    try {
      const selectedModel = modelList.value.find(m => m.id === selectedModelId.value)
      const conv = await createAiConversation({
        model_id: selectedModelId.value,
        model_name: selectedModel ? selectedModel.model_name : '',
        title: text.slice(0, 100)
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
    await streamChat(text)
  } catch {
    Message.error(t.value('sendMessageFailed'))
  } finally {
    sending.value = false
    await scrollToBottom()
  }
}

async function streamChat(text) {
  streaming.value = true
  streamingContent.value = ''
  abortController.value = new AbortController()

  try {
    const response = await streamChatWithAi({
      model_id: selectedModelId.value,
      conversation_id: currentConversationId.value,
      message: text
    }, abortController.value.signal)

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
    if (streamingContent.value) {
      messages.value.push({ id: Date.now(), role: 'assistant', content: streamingContent.value })
      streamingContent.value = ''
    }
    abortController.value = null
  }
}

function stopStreaming() {
  abortController.value?.abort()
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

function onModelChange() {}

function renderMessage(content) {
  if (!content) return ''
  let html = content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  html = html.replace(/\n/g, '<br>')
  return html
}

// ============ 初始化 ============
onMounted(async () => {
  await loadModels()
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

.ds-sidebar-header {
  padding: 12px;
  border-bottom: 1px solid var(--color-border-2);
}

.ds-btn-new {
  width: 100%;
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

.ds-model-picker {
  flex: 1;
}

.ds-model-select {
  width: auto;
  padding: 6px 28px 6px 12px;
  border: 1px solid var(--color-border-2);
  border-radius: 6px;
  background: var(--color-bg-1);
  color: var(--color-text-1);
  font-size: 13px;
  outline: none;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23888' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
}

.ds-model-select:focus {
  border-color: rgb(var(--primary-6));
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
  max-width: 720px;
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
  white-space: pre-wrap;
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

/* ===== 输入区 ===== */
.ds-input-area {
  padding: 12px 16px 16px;
  border-top: 1px solid var(--color-border-2);
}

.ds-input-box {
  max-width: 720px;
  margin: 0 auto;
  display: flex;
  align-items: flex-end;
  gap: 8px;
  border: 1px solid var(--color-border-2);
  border-radius: 12px;
  padding: 8px 8px 8px 16px;
  background: var(--color-bg-2);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.ds-input-box:focus-within {
  border-color: rgb(var(--primary-6));
  box-shadow: 0 0 0 2px rgba(var(--primary-6), 0.1);
}

.ds-textarea {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  color: var(--color-text-1);
  font-size: 15px;
  line-height: 1.5;
  font-family: inherit;
  max-height: 200px;
  min-height: 24px;
}

.ds-textarea::placeholder {
  color: var(--color-text-3);
}

.ds-btn-send {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 8px;
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
</style>
