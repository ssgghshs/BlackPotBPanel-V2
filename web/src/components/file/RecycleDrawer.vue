<template>
  <a-drawer
    :visible="visible"
    :title="t('recycle')"
    placement="right"
    :width="isMobile ? '100%' : '1000px'"
    :footer="null"
    @cancel="handleCancel"
    @before-ok="handleBeforeOk"
    unmountOnClose
  >
    <div class="recycle-drawer-content">
      <!-- 按钮区域 -->
      <div class="recycle-btn-group">
        <!-- 启用/禁用回收站功能 -->
        <span class="recycle-switch-wrapper">
          {{ t('recycle') }}
          <a-switch v-model="recycleEnabled" @change="handleSwitchChange" />
        </span>
        <!-- 清空回收站按钮 -->
        <a-button size="small" type="primary" @click="handleClearRecycle">
          {{ t('clearRecycle') }}
        </a-button>
        <!-- 批量恢复按钮 -->
        <a-button 
          size="small" 
          type="outline" 
          :disabled="selectedRowKeys.length === 0"
          @click="handleBatchRestore"
        >
          {{ t('unpause') }} ({{ selectedRowKeys.length }})
        </a-button>
        <!-- 批量删除按钮 -->
        <a-button 
          size="small" 
          type="outline" 
          status="danger"
          :disabled="selectedRowKeys.length === 0"
          @click="handleBatchDelete"
        >
          {{ t('delete') }} ({{ selectedRowKeys.length }})
        </a-button>
        <!-- 文件名称搜索框 -->
        <div class="recycle-search-wrapper">
          <a-input-search
            v-model="searchKeyword"
            :placeholder="t('searchFile')"
            size="small"
            @search="handleSearch"
            @input="handleSearch"
            style="width: 200px;"
          />
        </div>
      </div>
      
      <!-- 回收站文件表格 -->
      <div >
        <a-table
          :columns="columns"
          :data="filteredRecycleFiles"
          :loading="loading"
          v-model:pagination="pagination"
          :scroll="{ y: 'calc(100vh - 250px)' }"
          row-key="rname"
          :row-selection="rowSelection"
          v-model:selectedKeys="selectedRowKeys"
          @page-change="handlePageChange"
          @page-size-change="handlePageSizeChange"
        >
          <template #name="{ record }">
            <div class="file-name-cell">
              <component 
                :is="getFileIcon(transformRecord(record))" 
                :style="{ color: getFileIconColor(transformRecord(record)) }"
                class="file-icon"
              />
              <span class="file-name-text">{{ record.name }}</span>
            </div>
          </template>
          
          <template #dname="{ record }">
            <a-tooltip :content="record.dname" position="top">
              <span class="original-location-text">{{ record.dname }}</span>
            </a-tooltip>
          </template>
          
          <template #size="{ record }">
            <span>{{ formatFileSize(record.size) }}</span>
          </template>
          
          <template #time="{ record }">
            <span>{{ formatTime(record.time) }}</span>
          </template>
          
          <template #operations="{ record }">
            <a-link type="text" size="small" @click="handleRestore(record)">
              {{ t('unpause') }}
            </a-link>
            <a-link type="text" size="small" status="danger" @click="handleDelete(record)">
              {{ t('delete') }}
            </a-link>
          </template>
        </a-table>
      </div>
    </div>
  </a-drawer>
  
  <!-- 清空回收站确认对话框 -->
  <a-modal
    v-model:visible="showClearConfirm"
    :title="t('confirmClearRecycle')"
    @ok="handleConfirmClear"
    @cancel="showClearConfirm = false"
    :cancel-text="t('cancel')"
    :ok-text="t('confirm')"
  >
    <div>
      <p>{{ t('confirmClearRecycleContent') }}</p>
    </div>
  </a-modal>
  
  <!-- 恢复文件确认对话框 -->
  <a-modal
    v-model:visible="showRestoreConfirm"
    :title="t('confirmRestore')"
    @ok="handleConfirmRestore"
    @cancel="handleCancelRestore"
    :cancel-text="t('cancel')"
    :ok-text="t('confirm')"
  >
    <div>
      <p>{{ t('confirmRestoreContent') }}</p>
      <a-radio-group v-model="restoreLocation" class="restore-location-radio" style="margin-top: 16px;">
        <a-radio value="original">{{ t('restoreToOriginalLocation') }}</a-radio>
        <a-radio value="custom">{{ t('restoreToCustomLocation') }}</a-radio>
      </a-radio-group>
      
      <a-input
        v-if="restoreLocation === 'custom'"
        v-model="customRestorePath"
        :placeholder="t('enterCustomPath')"
        style="margin-top: 16px;"
      >
        <template #suffix>
          <IconFolder @click="showMiniFileManager = true" style="cursor: pointer; color: #165DFF;" />
        </template>
      </a-input>
    </div>
  </a-modal>
  
  <!-- MiniFileManager组件 -->
  <MiniFileManager
    v-model:visible="showMiniFileManager"
    :initial-path="'/'"
    :select-mode="'directory'"
    @select="handlePathSelect"
  />
  
  <!-- 删除文件确认对话框 -->
  <a-modal
    v-model:visible="showDeleteConfirm"
    :title="t('confirmDelete')"
    @ok="handleConfirmDelete"
    @cancel="handleCancelDelete"
    :cancel-text="t('cancel')"
    :ok-text="t('confirm')"
  >
    <div>
      <p>{{ t('confirmDeleteContent') }}</p>
      <p style="margin-top: 16px; color: var(--color-text-2);">{{ currentDeleteRecord?.name }}</p>
    </div>
  </a-modal>
  
  <!-- 批量恢复确认对话框 -->
  <a-modal
    v-model:visible="showBatchRestoreConfirm"
    :title="t('confirmBatchRestore')"
    @ok="handleConfirmBatchRestore"
    @cancel="handleCancelBatchRestore"
    :cancel-text="t('cancel')"
    :ok-text="t('confirm')"
    width="600px"
  >
    <div>
      <p>{{ t('confirmBatchRestoreContent') }}</p>
      <div style="margin-top: 16px; max-height: 300px; overflow-y: auto; border: 1px solid var(--color-border-2); border-radius: 4px; padding: 12px;">
        <div 
          v-for="file in selectedFiles" 
          :key="file.rname"
          style="display: flex; align-items: center; gap: 8px; padding: 8px; border-bottom: 1px solid var(--color-border-1);"
        >
          <component 
            :is="getFileIcon(transformRecord(file))" 
            :style="{ color: getFileIconColor(transformRecord(file)) }"
            style="font-size: 16px;"
          />
          <div style="flex: 1; overflow: hidden;">
            <div style="font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              {{ file.name }}
            </div>
            <div style="font-size: 12px; color: var(--color-text-3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              {{ file.dname }}
            </div>
          </div>
        </div>
      </div>
      <p style="margin-top: 12px; color: var(--color-text-3); font-size: 13px;">
        {{ t('batchRestoreNote') }}
      </p>
    </div>
  </a-modal>
  
  <!-- 批量删除确认对话框 -->
  <a-modal
    v-model:visible="showBatchDeleteConfirm"
    :title="t('confirmBatchDelete')"
    @ok="handleConfirmBatchDelete"
    @cancel="handleCancelBatchDelete"
    :cancel-text="t('cancel')"
    :ok-text="t('confirm')"
    width="600px"
  >
    <div>
      <p style="color: var(--color-danger-6); font-weight: 500;">{{ t('confirmBatchDeleteContent') }}</p>
      <div style="margin-top: 16px; max-height: 300px; overflow-y: auto; border: 1px solid var(--color-border-2); border-radius: 4px; padding: 12px;">
        <div 
          v-for="file in selectedFiles" 
          :key="file.rname"
          style="display: flex; align-items: center; gap: 8px; padding: 8px; border-bottom: 1px solid var(--color-border-1);"
        >
          <component 
            :is="getFileIcon(transformRecord(file))" 
            :style="{ color: getFileIconColor(transformRecord(file)) }"
            style="font-size: 16px;"
          />
          <div style="flex: 1; overflow: hidden;">
            <div style="font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              {{ file.name }}
            </div>
            <div style="font-size: 12px; color: var(--color-text-3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              {{ file.dname }}
            </div>
          </div>
        </div>
      </div>
      <p style="margin-top: 12px; color: var(--color-danger-6); font-size: 13px;">
        {{ t('batchDeleteNote') }}
      </p>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { getRecycleConfig, updateRecycleConfig, clearRecycle, getRecycleFiles, 
  restoreRecycleFile, deleteRecycleFile, restoreRecycleFilesBatch, deleteRecycleFilesBatch } from '../../api/file'
import { t } from '../../utils/locale'
import { Message } from '@arco-design/web-vue'
import { getFileIcon, getFileIconColor } from '../../utils/file/fileIconMapper'
import MiniFileManager from './MiniFileManager.vue'
import { IconFolder} from '@arco-design/web-vue/es/icon';

// 定义组件属性
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  isMobile: {
    type: Boolean,
    default: false
  }
})

// 定义事件发射
const emit = defineEmits(['update:visible', 'close'])

// 回收站开关状态
const recycleEnabled = ref(false)

// 清空回收站确认对话框状态
const showClearConfirm = ref(false)

// 恢复文件确认对话框状态
const showRestoreConfirm = ref(false)

// 恢复位置选择：'original' 或 'custom'
const restoreLocation = ref('original')

// 自定义恢复路径
const customRestorePath = ref('')

// 当前要恢复的文件记录
const currentRestoreRecord = ref(null)

// MiniFileManager显示状态
const showMiniFileManager = ref(false)

// 删除文件确认对话框状态
const showDeleteConfirm = ref(false)

// 当前要删除的文件记录
const currentDeleteRecord = ref(null)

// 批量恢复确认对话框状态
const showBatchRestoreConfirm = ref(false)

// 批量删除确认对话框状态
const showBatchDeleteConfirm = ref(false)

// 选中的行keys
const selectedRowKeys = ref([])

// 选中的文件列表
const selectedFiles = ref([])

// 表格行选择配置
const rowSelection = {
  type: 'checkbox',
  showCheckedAll: true,
  fixed: true
}

// 回收站文件列表
const recycleFiles = ref([])

// 过滤后的回收站文件列表（用于搜索）
const filteredRecycleFiles = ref([])

// 加载状态
const loading = ref(false)

// 所有回收站文件数据（用于前端分页和搜索）
const allRecycleFiles = ref([])

// 搜索关键词
const searchKeyword = ref('')

// 分页相关数据
const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  showPageSize: true,
  pageSizeOptions: [10, 20, 50, 100],
})

// 表格列定义
const columns = [
  {
    title: t.value('name'),
    dataIndex: 'name',
    slotName: 'name',
    ellipsis: true,
    width: 200
  },
  {
    title: t.value('originalLocation'),
    dataIndex: 'dname',
    slotName: 'dname',
    ellipsis: true,
    width: 200
  },
  {
    title: t.value('size'),
    dataIndex: 'size',
    slotName: 'size',
    width: 100
  },
  {
    title: t.value('deleteTime'),
    dataIndex: 'time',
    slotName: 'time',
    width: 150
  },
  {
    title: t.value('actions'),
    slotName: 'operations',
    width: 120
  }
]

// 转换记录格式以适配图标组件
const transformRecord = (record) => {
  return {
    is_directory: record.is_directory || false,
    filename: record.name || ''
  };
}

// 监听visible属性变化，当抽屉打开时获取配置和文件列表
watch(() => props.visible, async (newVal) => {
  if (newVal) {
    try {
      // 获取回收站配置
      const response = await getRecycleConfig()
      console.log('获取到的回收站配置:', response) // 调试信息
      // 根据返回的RECYCLE值设置开关状态
      recycleEnabled.value = response.RECYCLE === "True"
      console.log('设置开关状态为:', recycleEnabled.value) // 调试信息
      
      // 获取回收站文件列表
      await loadRecycleFiles()
    } catch (error) {
      console.error('获取回收站配置失败:', error)
    }
  }
})

// 加载回收站文件列表
const loadRecycleFiles = async () => {
  try {
    loading.value = true
    const current = pagination.value.current || 1
    const pageSize = pagination.value.pageSize || 10
    const skip = (current - 1) * pageSize
    console.log('loadRecycleFiles - current:', current, 'pageSize:', pageSize, 'skip:', skip)
    const response = await getRecycleFiles({
      skip: skip,
      limit: pageSize
    })
    allRecycleFiles.value = response.data.data || []
    pagination.value.total = response.data.total || 0
    // 直接使用后端返回的分页数据
    recycleFiles.value = allRecycleFiles.value
    // 应用搜索过滤
    applySearchFilter()
  } catch (error) {
    console.error('获取回收站文件列表失败:', error)
    Message.error(t.value('loadRecycleFilesFailed'))
  } finally {
    loading.value = false
  }
}

// 应用搜索过滤
const applySearchFilter = () => {
  if (!searchKeyword.value.trim()) {
    // 如果没有搜索关键词，显示所有文件
    filteredRecycleFiles.value = recycleFiles.value
    return
  }
  
  const keyword = searchKeyword.value.toLowerCase()
  // 根据文件名过滤文件
  filteredRecycleFiles.value = recycleFiles.value.filter(file => 
    file.name.toLowerCase().includes(keyword)
  )
}

// 处理搜索事件
const handleSearch = () => {
  // 应用搜索过滤
  applySearchFilter()
}

// 更新选中的文件列表
const updateSelectedFiles = () => {
  selectedFiles.value = filteredRecycleFiles.value.filter(file => 
    selectedRowKeys.value.includes(file.rname)
  )
}

// 监听选中状态变化，自动更新选中的文件列表
watch(selectedRowKeys, () => {
  updateSelectedFiles()
}, { deep: true })

// 处理页码变化
const handlePageChange = (page) => {
  // Arco Design 的 @page-change 直接返回页码数字
  pagination.value.current = typeof page === 'number' ? page : (page.page || page.current || 1)
  // 清空选中状态
  selectedRowKeys.value = []
  selectedFiles.value = []
  // 重新加载数据
  loadRecycleFiles()
}

// 处理每页条数变化
const handlePageSizeChange = (pageSize) => {
  pagination.value.pageSize = typeof pageSize === 'number' ? pageSize : 10
  pagination.value.current = 1
  // 清空选中状态
  selectedRowKeys.value = []
  selectedFiles.value = []
  // 重新加载数据
  loadRecycleFiles()
}

// 格式化文件大小
const formatFileSize = (size) => {
  if (size === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let fileSize = size
  while (fileSize >= 1024 && i < units.length - 1) {
    fileSize /= 1024
    i++
  }
  return `${fileSize.toFixed(1)} ${units[i]}`
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return ''
  return time.replace('T', ' ')
}

// 处理还原文件
const handleRestore = (record) => {
  // 保存当前要恢复的文件记录
  currentRestoreRecord.value = record
  // 重置恢复位置为原始位置
  restoreLocation.value = 'original'
  // 重置自定义恢复路径
  customRestorePath.value = ''
  // 显示恢复确认对话框
  showRestoreConfirm.value = true
}

// 处理删除文件
const handleDelete = (record) => {
  // 保存当前要删除的文件记录
  currentDeleteRecord.value = record
  // 显示删除确认对话框
  showDeleteConfirm.value = true
}

// 处理确认删除文件
const handleConfirmDelete = async () => {
  if (!currentDeleteRecord.value) {
    handleCancelDelete()
    return
  }
  
  try {
    // 构建删除请求参数
    const requestData = {
      recycle_filename: currentDeleteRecord.value.rname
    }
    
    // 调用删除文件API
    const response = await deleteRecycleFile(requestData)
    
    // 关闭确认对话框
    showDeleteConfirm.value = false
    
    // 显示成功消息
    Message.success(t.value('deleteSuccess'))
    
    // 重新加载回收站文件列表
    await loadRecycleFiles()
    
    // 重置当前删除记录
    currentDeleteRecord.value = null
  } catch (error) {
    console.error('删除文件失败:', error)
    // 显示错误消息
    Message.error(t.value('deleteFailed'))
  }
}

// 处理取消删除文件
const handleCancelDelete = () => {
  // 关闭确认对话框
  showDeleteConfirm.value = false
  // 重置当前删除记录
  currentDeleteRecord.value = null
}

// 处理清空回收站按钮点击
const handleClearRecycle = () => {
  showClearConfirm.value = true
}

// 处理确认清空回收站
const handleConfirmClear = async () => {
  try {
    // 调用清空回收站API
    const response = await clearRecycle()
    
    // 关闭确认对话框
    showClearConfirm.value = false
    
    // 显示成功消息
    Message.success(response.message || t.value('recycleCleared'))
    
    // 重新加载回收站文件列表
    await loadRecycleFiles()
  } catch (error) {
    console.error('清空回收站失败:', error)
    // 显示错误消息
    Message.error(t.value('clearRecycleFailed'))
  }
}

// 处理确认恢复文件
const handleConfirmRestore = async () => {
  if (!currentRestoreRecord.value) {
    handleCancelRestore()
    return
  }
  
  try {
    // 构建恢复请求参数
    const requestData = {
      recycle_filename: currentRestoreRecord.value.rname
    }
    
    // 如果选择了自定义位置，添加target_path参数
    if (restoreLocation.value === 'custom' && customRestorePath.value.trim()) {
      requestData.target_path = customRestorePath.value.trim()
    }
    
    // 调用恢复文件API
    const response = await restoreRecycleFile(requestData)
    
    // 关闭确认对话框
    showRestoreConfirm.value = false
    
    // 显示成功消息
    Message.success(response.message || t.value('restoreSuccess'))
    
    // 重新加载回收站文件列表
    await loadRecycleFiles()
    
    // 重置当前恢复记录
    currentRestoreRecord.value = null
  } catch (error) {
    console.error('恢复文件失败:', error)
    // 显示错误消息
    Message.error(t.value('restoreFailed'))
  }
}

// 处理取消恢复文件
const handleCancelRestore = () => {
  // 关闭确认对话框
  showRestoreConfirm.value = false
  // 重置当前恢复记录
  currentRestoreRecord.value = null
  // 重置恢复位置为原始位置
  restoreLocation.value = 'original'
  // 重置自定义恢复路径
  customRestorePath.value = ''
}

// 处理MiniFileManager选择路径
const handlePathSelect = (selected) => {
  customRestorePath.value = selected.path
}

// 处理批量恢复按钮点击
const handleBatchRestore = () => {
  if (selectedRowKeys.value.length === 0) {
    Message.warning(t.value('pleaseSelectFiles'))
    return
  }
  // 显示批量恢复确认对话框
  showBatchRestoreConfirm.value = true
}

// 处理确认批量恢复
const handleConfirmBatchRestore = async () => {
  if (selectedRowKeys.value.length === 0) {
    handleCancelBatchRestore()
    return
  }
  
  try {
    // 构建批量恢复请求参数
    const requestData = {
      recycle_filenames: selectedRowKeys.value
    }
    
    // 调用批量恢复API
    const response = await restoreRecycleFilesBatch(requestData)
    
    // 关闭确认对话框
    showBatchRestoreConfirm.value = false
    
    // 显示成功消息
    Message.success(response.message || t.value('batchRestoreSuccess'))
    
    // 清空选中状态
    selectedRowKeys.value = []
    selectedFiles.value = []
    
    // 重新加载回收站文件列表
    await loadRecycleFiles()
  } catch (error) {
    console.error('批量恢复文件失败:', error)
    // 显示错误消息
    Message.error(t.value('batchRestoreFailed'))
  }
}

// 处理取消批量恢复
const handleCancelBatchRestore = () => {
  // 关闭确认对话框
  showBatchRestoreConfirm.value = false
}

// 处理批量删除按钮点击
const handleBatchDelete = () => {
  if (selectedRowKeys.value.length === 0) {
    Message.warning(t.value('pleaseSelectFiles'))
    return
  }
  // 显示批量删除确认对话框
  showBatchDeleteConfirm.value = true
}

// 处理确认批量删除
const handleConfirmBatchDelete = async () => {
  if (selectedRowKeys.value.length === 0) {
    handleCancelBatchDelete()
    return
  }
  
  try {
    // 构建批量删除请求参数
    const requestData = {
      recycle_filenames: selectedRowKeys.value
    }
    
    // 调用批量删除API
    const response = await deleteRecycleFilesBatch(requestData)
    
    // 关闭确认对话框
    showBatchDeleteConfirm.value = false
    
    // 显示成功消息
    Message.success(response.message || t.value('batchDeleteSuccess'))
    
    // 清空选中状态
    selectedRowKeys.value = []
    selectedFiles.value = []
    
    // 重新加载回收站文件列表
    await loadRecycleFiles()
  } catch (error) {
    console.error('批量删除文件失败:', error)
    // 显示错误消息
    Message.error(t.value('batchDeleteFailed'))
  }
}

// 处理取消批量删除
const handleCancelBatchDelete = () => {
  // 关闭确认对话框
  showBatchDeleteConfirm.value = false
}

// 处理开关变更
const handleSwitchChange = async (checked) => {
  try {
    // 发送正确的数据格式给后端
    await updateRecycleConfig({ RECYCLE: checked ? "true" : "false" })
    // 显示成功消息
    Message.success(checked ? t.value('recycleEnabled') : t.value('recycleDisabled'))
  } catch (error) {
    console.error('更新回收站配置失败:', error)
    // 显示错误消息
    Message.error(t.value('updateRecycleConfigFailed'))
    // 如果更新失败，回滚开关状态
    recycleEnabled.value = !checked
  }
}

// 处理取消事件
const handleCancel = () => {
  emit('update:visible', false)
  emit('close')
}

// 处理确认前的逻辑
const handleBeforeOk = async () => {
  emit('update:visible', false)
  emit('close')
  return true
}
</script>

<style scoped>
.recycle-drawer-content {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* 按钮组样式 */
.recycle-btn-group {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.recycle-switch-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.recycle-search-wrapper {
  margin-left: auto;
  display: flex;
  align-items: center;
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



/* 文件名列样式 */
.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-icon {
  font-size: 16px;
}

.file-name-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 原始位置文本样式 */
.original-location-text {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: help;
}

/* 表格样式 */
:deep(.arco-table-th) {
  font-weight: bold;
}

:deep(.arco-table-tr) {
  cursor: context-menu;
}

:deep(.arco-table-tr:hover) {
  background-color: var(--color-fill-1) !important;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .recycle-btn-group {
    flex-wrap: wrap;
  }
  
  .recycle-switch-wrapper {
    margin-left: 0;
    width: 100%;
    justify-content: space-between;
  }
  
  :deep(.arco-table-cell),
  :deep(.arco-table-th) {
    padding: 6px 4px !important;
    font-size: 13px;
  }
  
  :deep(.arco-table-tr) {
    min-height: 36px;
  }
}
</style>