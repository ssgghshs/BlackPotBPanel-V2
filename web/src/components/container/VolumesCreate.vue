<template>
  <a-drawer
    v-model:visible="isVisible"
    :title="t('createVolume')"
    placement="right"
    :width="isMobile ? '90%' : '600px'"
    :footer="false"
    @close="handleClose"
  >
    <a-form
      :model="formData"
      :rules="formRules"
      ref="formRef"
      :label-col="{ span: 6 }"
      :wrapper-col="{ span: 18 }"
    >
      <!-- 存储卷名称 -->
      <a-form-item :label="t('name')" field="name">
        <a-input
          v-model="formData.name"
          :placeholder="t('volumeNamePlaceholder')"
          allow-clear
        />
      </a-form-item>

      <!-- 存储卷驱动 -->
      <a-form-item :label="t('driver')" field="driver">
        <a-select
          v-model="formData.driver"
          :placeholder="t('selectDriver')"
        >
          <a-option value="local">local</a-option>
        </a-select>
      </a-form-item>

      <!-- 高级选项 -->
      <a-collapse>
        <a-collapse-item name="advanced" :header="t('advancedOptions')">
          <!-- 驱动选项 -->
          <div class="driver-opts-section">
            <div class="section-header">
              <span>{{ t('driverOptions') }}</span>
              <a-button
                type="outline"
                size="small"
                @click="addDriverOpt"
                :disabled="isSubmitting"
              >
                {{ t('add')}}
              </a-button>
            </div>
            <div
              v-for="(opt, index) in formData.driver_opts"
              :key="index"
              class="key-value-item"
            >
              <a-input
                v-model="opt.key"
                :placeholder="t('key')"
                style="margin-right: 8px; flex: 1"
                allow-clear
                :disabled="isSubmitting"
              />
              <a-input
                v-model="opt.value"
                :placeholder="t('value')"
                style="margin-right: 8px; flex: 1"
                allow-clear
                :disabled="isSubmitting"
              />
              <a-button
                type="outline"
                danger
                size="small"
                @click="removeDriverOpt(index)"
                :disabled="isSubmitting"
              >
                {{ t('delete') }}
              </a-button>
            </div>
          </div>

          <!-- 标签 -->
          <div class="labels-section">
            <div class="section-header">
              <span>{{ t('labels') }}</span>
              <a-button
                type="outline"
                size="small"
                @click="addLabel"
                :disabled="isSubmitting"
              >
                {{ t('add') }}
              </a-button>
            </div>
            <div
              v-for="(label, index) in formData.labels"
              :key="index"
              class="key-value-item"
            >
              <a-input
                v-model="label.key"
                :placeholder="t('key')"
                style="margin-right: 8px; flex: 1"
                allow-clear
                :disabled="isSubmitting"
              />
              <a-input
                v-model="label.value"
                :placeholder="t('value')"
                style="margin-right: 8px; flex: 1"
                allow-clear
                :disabled="isSubmitting"
              />
              <a-button
                type="outline"
                danger
                size="small"
                @click="removeLabel(index)"
                :disabled="isSubmitting"
              >
                {{ t('delete') }}
              </a-button>
            </div>
          </div>
        </a-collapse-item>
      </a-collapse>
    </a-form>

    <!-- 底部操作按钮 -->
    <div class="drawer-footer">
      <a-button
        @click="handleClose"
        :disabled="isSubmitting"
        style="margin-right: 8px"
      >
        {{ t('cancel') }}
      </a-button>
      <a-button
        type="primary"
        @click="handleSubmit"
        :loading="isSubmitting"
      >
        {{ t('confirm') }}
      </a-button>
    </div>
  </a-drawer>
</template>

<script setup>
import { ref, reactive, watch, onMounted, onUnmounted } from 'vue';
import { t } from '../../utils/locale';
import { createVolume as createVolumeApi } from '../../api/container';
import { Message } from '@arco-design/web-vue';
import {
  Drawer as ADrawer,
  Form as AForm,
  FormItem as AFormItem,
  Input as AInput,
  Select as ASelect,
  Option as AOption,
  Button as AButton,
  Collapse as ACollapse,
  CollapseItem as ACollapseItem
} from '@arco-design/web-vue';

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
});

// Emits
const emit = defineEmits(['update:visible', 'success', 'close']);

// 响应式数据
const isVisible = ref(false);
const selectedHostId = ref(null);
const isSubmitting = ref(false);
const formRef = ref(null);
const isMobile = ref(false);

// 检查是否为移动设备
const checkIsMobile = () => {
  isMobile.value = window.innerWidth < 768;
};

// 表单数据
const formData = reactive({
  name: '',
  driver: 'local',
  driver_opts: [{
    key: '',
    value: ''
  }],
  labels: [{
    key: '',
    value: ''
  }]
});

// 表单验证规则
const formRules = {
  name: [
    {
      required: true,
      message: t.value('volumeNameRequired'),
      trigger: ['blur', 'submit']
    },
    {
      pattern: /^[a-zA-Z0-9][a-zA-Z0-9_.-]*$/,
      message: t.value('volumeNameInvalid'),
      trigger: ['blur', 'submit']
    }
  ],
  driver: [
    {
      required: true,
      message: t.value('driverRequired'), 
      trigger: ['change', 'submit']
    }
  ]
};

// 监听props变化
watch(
  () => props.visible,
  (newVal) => {
    isVisible.value = newVal;
    // 当抽屉打开时，重置表单
    if (newVal) {
      resetForm();
    }
  },
  { immediate: true }
);

// 监听宿主变化事件
const handleContainerHostChange = (event) => {
  try {
    if (event && event.detail && event.detail.hostId) {
      selectedHostId.value = event.detail.hostId;
    }
  } catch (error) {
    console.error('Error handling container host change:', error);
  }
};

// 重置表单
const resetForm = () => {
  try {
    if (formRef.value) {
      formRef.value.resetFields();
    }
    formData.name = '';
    formData.driver = 'local';
    formData.driver_opts = [{ key: '', value: '' }];
    formData.labels = [{ key: '', value: '' }];
    
    // 确保有选中的宿主ID
    if (!selectedHostId.value) {
      const savedHostId = localStorage.getItem('selectedContainerHostId');
      if (savedHostId) {
        selectedHostId.value = savedHostId;
      }
    }
  } catch (error) {
    console.error('Error resetting form:', error);
  }
};

// 添加驱动选项
const addDriverOpt = () => {
  formData.driver_opts.push({ key: '', value: '' });
};

// 移除驱动选项
const removeDriverOpt = (index) => {
  if (formData.driver_opts.length > 1) {
    formData.driver_opts.splice(index, 1);
  } else {
    formData.driver_opts[0] = { key: '', value: '' };
    Message.warning(t.value('atLeastOneItem') || '至少保留一项');
  }
};

// 添加标签
const addLabel = () => {
  formData.labels.push({ key: '', value: '' });
};

// 移除标签
const removeLabel = (index) => {
  if (formData.labels.length > 1) {
    formData.labels.splice(index, 1);
  } else {
    formData.labels[0] = { key: '', value: '' };
    Message.warning(t.value('atLeastOneItem'));
  }
};

// 处理提交
const handleSubmit = async () => {
  try {
    if (!selectedHostId.value) {
      Message.warning(t.value('pleaseSelectHost'));
      return;
    }

    // 验证表单，捕获验证错误
    const errors = await formRef.value.validate().catch(err => err);
    
    // 如果有验证错误，直接返回
    if (errors) {
      console.log('表单验证失败:', errors);
      return;
    }
    
    // 验证通过，设置提交状态
    isSubmitting.value = true;
    
    // 构建请求数据 - 首先包含所有可能的字段
    const requestData = {
      name: formData.name.trim(), // 简化处理，直接trim
      driver: formData.driver,
      driver_opts: {},
      labels: {}
    };
    
    // 记录日志
    console.log('表单数据:', formData);
    
    // 添加驱动选项（如果有）
    const driverOpts = formData.driver_opts
      .filter(opt => opt.key && opt.key.trim())
      .reduce((acc, opt) => {
        acc[opt.key.trim()] = opt.value ? opt.value.trim() : '';
        return acc;
      }, {});
    
    // 对于local驱动，验证驱动选项是否有效
    if (formData.driver === 'local' && Object.keys(driverOpts).length > 0) {
      // local驱动支持的选项列表
      const validLocalOptions = ['type', 'device', 'o', 'deviceid', 'iops', 'size', 'basesize', 'device_read_iops', 'device_write_iops', 'device_read_bps', 'device_write_bps', 'fsopts', 'context', 'noexec', 'nosuid', 'nodiscard', 'mpol'];
      
      // 检查是否有无效的选项
      const invalidOpts = Object.keys(driverOpts).filter(key => !validLocalOptions.includes(key));
      
      if (invalidOpts.length > 0) {
        throw new Error(`local驱动不支持以下选项: ${invalidOpts.join(', ')}`);
      }
      
      // 特殊选项依赖检查
      // 当使用'o'选项时，必须同时提供'device'选项
      if (driverOpts.hasOwnProperty('o') && !driverOpts.hasOwnProperty('device')) {
        throw new Error('当使用挂载选项(o)时，必须同时提供device选项');
      }
    }
    
    if (Object.keys(driverOpts).length > 0) {
      requestData.driver_opts = driverOpts;
    }
    
    // 添加标签（如果有）
    const labels = formData.labels
      .filter(label => label.key && label.key.trim())
      .reduce((acc, label) => {
        acc[label.key.trim()] = label.value ? label.value.trim() : '';
        return acc;
      }, {});
    
    if (Object.keys(labels).length > 0) {
      requestData.labels = labels;
    }
    
    console.log('最终提交的请求数据:', requestData);
    
    // 确保 createVolumeApi 存在且是函数
    if (typeof createVolumeApi !== 'function') {
      throw new Error('createVolume API function is not available');
    }
    
    const response = await createVolumeApi(selectedHostId.value, requestData);
    
    // 成功处理
    Message.success(t.value('createVolumeSuccess'));
    // 先更新本地状态
    isVisible.value = false;
    // 然后按顺序发出事件，先 success，然后 update:visible，最后 close
    if (typeof emit === 'function') {
      emit('success', response);
      // 使用 setTimeout 确保事件按顺序处理
      setTimeout(() => {
        emit('update:visible', false);
        setTimeout(() => {
          emit('close');
        }, 0);
      }, 0);
    }
    // 不再调用 handleClose() 以避免可能的递归问题
  } catch (error) {
    // 错误处理 - 确保错误处理本身不会抛出异常
    try {
      console.error('创建存储卷失败:', error);
      const errorMsg = error.response?.data?.detail || error.message || t.value('createVolumeFailed');
      Message.error(errorMsg);
    } catch (err) {
      console.error('Error displaying error message:', err);
    }
  } finally {
    // 确保无论成功还是失败都重置提交状态
    isSubmitting.value = false;
  }
};

// 处理关闭
const handleClose = () => {
  try {
    isVisible.value = false;
    // 确保 emit 存在且是函数
    if (typeof emit === 'function') {
      // 先 emit update:visible 来更新父组件中的 v-model
      emit('update:visible', false);
      // 然后 emit close 事件让父组件执行额外逻辑
      // 添加一个小延迟以避免事件处理冲突
      setTimeout(() => {
        emit('close');
      }, 0);
    }
  } catch (error) {
    console.error('Error closing drawer:', error);
    // 即使出错也尝试设置 visible 为 false
    try {
      isVisible.value = false;
    } catch (err) {
      console.error('Failed to set isVisible to false:', err);
    }
  }
};

// 组件挂载时
onMounted(() => {
  try {
    // 从localStorage获取已保存的宿主ID
    const savedHostId = localStorage.getItem('selectedContainerHostId');
    if (savedHostId) {
      selectedHostId.value = savedHostId;
    }
    
    // 监听宿主变化事件
    window.addEventListener('containerHostChanged', handleContainerHostChange);
    
    // 初始化移动端检测
    checkIsMobile();
    // 添加窗口大小变化监听
    window.addEventListener('resize', checkIsMobile);
  } catch (error) {
    console.error('Error in onMounted:', error);
  }
});

// 组件卸载时
onUnmounted(() => {
  try {
    // 移除事件监听
    window.removeEventListener('containerHostChanged', handleContainerHostChange);
    // 移除窗口大小变化监听
    window.removeEventListener('resize', checkIsMobile);
  } catch (error) {
    console.error('Error in onUnmounted:', error);
  }
});
</script>

<style scoped>
.drawer-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 16px 24px;
  background-color: #fff;
  border-top: 1px solid #f0f0f0;
  text-align: right;
}

body[arco-theme="dark"] .drawer-footer {
  background-color: #232324;
  border-top-color: #424244;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-weight: 500;
}

.key-value-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.driver-opts-section,
.labels-section {
  margin-bottom: 20px;
}

.driver-opts-section:last-child,
.labels-section:last-child {
  margin-bottom: 0;
}
</style>
