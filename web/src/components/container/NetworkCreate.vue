<template>
  <a-drawer
    v-model:visible="isVisible"
    :title="t('createNetwork')"
    placement="right"
    :width="isMobile ? '90%' : 800"
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
      <!-- 网络名称 -->
      <a-form-item :label="t('networkName')" field="name">
        <a-input
          v-model="formData.name"
          :placeholder="t('pleaseInputNetworkName')"
          allow-clear
        />
      </a-form-item>

      <!-- 网络驱动 -->
      <a-form-item :label="t('driver')" field="driver">
        <a-select
          v-model="formData.driver"
          :placeholder="t('pleaseSelectDriver')"
        >
          <a-option value="bridge">bridge</a-option>
          <a-option value="overlay">overlay</a-option>
          <a-option value="macvlan">macvlan</a-option>
          <a-option value="ipvlan">ipvlan</a-option>
          <a-option value="none">none</a-option>
        </a-select>
      </a-form-item>

      <!-- 内部网络 -->
      <a-form-item>
        <div style="display: flex; align-items: center;">
          <span style="margin-right: 12px;">{{ t('internalNetwork')}}</span>
          <a-switch v-model="formData.internal" :checked-children="t('yes')" :unchecked-children="t('no')" />
        </div>
      </a-form-item>

      <!-- 启用IPv6 -->
      <a-form-item>
        <div style="display: flex; align-items: center;">
          <span style="margin-right: 12px;">{{ t('enableIPv6')}}</span>
          <a-switch v-model="formData.enableIPv6" :checked-children="t('yes')" :unchecked-children="t('no')" />
        </div>
      </a-form-item>

      <!-- 可附加 -->
      <a-form-item>
        <div style="display: flex; align-items: center;">
          <span style="margin-right: 12px;">{{ t('attachable')}}</span>
          <a-switch v-model="formData.attachable" :checked-children="t('yes')" :unchecked-children="t('no')" />
        </div>
      </a-form-item>

      <!-- 检查重复 -->
      <a-form-item>
        <div style="display: flex; align-items: center;">
          <span style="margin-right: 12px;">{{ t('checkDuplicate')}}</span>
          <a-switch v-model="formData.check_duplicate" :checked-children="t('yes')" :unchecked-children="t('no')" />
        </div>
      </a-form-item>

      <!-- 高级选项 -->
      <a-collapse>
        <a-collapse-item name="advanced" :header="t('advancedOptions')">
        
          <!-- IPAM配置 -->
          <div class="ipam-section">
            <div class="section-header">
              <span>{{ t('ipamConfiguration') || 'IPAM配置' }}</span>
              <a-button
                type="outline"
                size="small"
                @click="addIpamConfig"
                :disabled="isSubmitting"
              >
                {{ t('add') }}
              </a-button>
            </div>
            <div v-if="formData.ipamConfigList && formData.ipamConfigList.length > 0">
              <div v-for="(config, index) in formData.ipamConfigList" :key="index" class="ipam-config-item">
                <div class="config-row">
                  <a-input
                    v-model="config.Subnet"
                    :placeholder="t('subnetDescription')"
                    style="margin-right: 8px; flex: 1"
                    allow-clear
                    :disabled="isSubmitting"
                  />
                  <a-input
                    v-model="config.Gateway"
                    :placeholder="t('gatewayDescription')"
                    style="margin-right: 8px; flex: 1"
                    allow-clear
                    :disabled="isSubmitting"
                  />
                </div>
                <div class="config-row">
                  <a-input
                    v-model="config.IPRange"
                    :placeholder="t('ipRange')"
                    style="margin-right: 8px; flex: 1"
                    allow-clear
                    :disabled="isSubmitting"
                  />
                  <a-input
                    v-model="config.AuxAddress"
                    :placeholder="t('auxAddress')"
                    style="margin-right: 8px; flex: 1"
                    allow-clear
                    :disabled="isSubmitting"
                  />
                  <a-button
                    type="outline"
                    danger
                    size="small"
                    @click="removeIpamConfig(index)"
                    :disabled="isSubmitting || formData.ipamConfigList.length <= 1"
                  >
                    {{ t('delete') }}
                  </a-button>
                </div>
              </div>
            </div>
          </div>

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
                {{ t('add') }}
              </a-button>
            </div>
            <div
              v-for="(opt, index) in formData.optionsList"
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
              v-for="(label, index) in formData.labelsList"
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
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue';
import { t } from '../../utils/locale';
import { createNetwork } from '../../api/container';
import { Message } from '@arco-design/web-vue';
import { Drawer as ADrawer, Form as AForm, FormItem as AFormItem, Input as AInput, Select as ASelect, Option as AOption, Button as AButton, Switch as ASwitch, Collapse as ACollapse, CollapseItem as ACollapseItem } from '@arco-design/web-vue';

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
// 响应式布局相关
const isMobile = ref(false);

const checkIsMobile = () => {
  isMobile.value = window.innerWidth < 768;
};

// 表单数据
const formData = reactive({
  name: '',
  driver: 'bridge',
  optionsList: [{ key: '', value: '' }],
  ipam: {
    Driver: 'default',
    Config: []
  },
  ipamConfigList: [{
    Subnet: '',
    Gateway: '',
    IPRange: '',
    AuxAddress: ''
  }],
  internal: false,
  enableIPv6: false,
  labelsList: [{ key: '', value: '' }],
  check_duplicate: true,
  attachable: false
});

// 表单验证规则
const formRules = computed(() => ({
  name: [
    {
      required: true,
      message: t.value('networkNameRequired') ,
      trigger: 'blur'
    },
    {
      pattern: /^[a-zA-Z0-9][a-zA-Z0-9_.-]*$/,
      message: t.value('networkNameInvalid'),
      trigger: 'blur'
    }
  ],
  driver: [
    {
      required: true,
      message: t.value('driverRequired'),
      trigger: 'change'
    }
  ]
}));

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
    formData.driver = 'bridge';
    formData.optionsList = [{ key: '', value: '' }];
    formData.ipam = {
      Driver: 'default',
      Config: []
    };
    formData.ipamConfigList = [{
      Subnet: '',
      Gateway: '',
      IPRange: '',
      AuxAddress: ''
    }];
    formData.internal = false;
    formData.enableIPv6 = false;
    formData.labelsList = [{ key: '', value: '' }];
    formData.check_duplicate = true;
    formData.attachable = false;
    
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
  formData.optionsList.push({ key: '', value: '' });
};

// 移除驱动选项
const removeDriverOpt = (index) => {
  if (formData.optionsList.length > 1) {
    formData.optionsList.splice(index, 1);
  } else {
    formData.optionsList[0] = { key: '', value: '' };
    Message.warning(t.value('atLeastOneItem') || '至少保留一项');
  }
};

// 添加标签
const addLabel = () => {
  formData.labelsList.push({ key: '', value: '' });
};

// 移除标签
const removeLabel = (index) => {
  if (formData.labelsList.length > 1) {
    formData.labelsList.splice(index, 1);
  } else {
    formData.labelsList[0] = { key: '', value: '' };
    Message.warning(t.value('atLeastOneItem') || '至少保留一项');
  }
};

// 添加IPAM配置
const addIpamConfig = () => {
  formData.ipamConfigList.push({
    Subnet: '',
    Gateway: '',
    IPRange: '',
    AuxAddress: ''
  });
};

// 移除IPAM配置
const removeIpamConfig = (index) => {
  if (formData.ipamConfigList.length > 1) {
    formData.ipamConfigList.splice(index, 1);
  } else {
    Message.warning(t.value('atLeastOneIpamConfig') || '至少保留一项IPAM配置');
  }
};

// 解析AuxAddress字符串为对象
const parseAuxAddress = (auxAddressStr) => {
  if (!auxAddressStr) return {};
  
  const auxAddressObj = {};
  const pairs = auxAddressStr.split(',');
  
  for (const pair of pairs) {
    const [key, value] = pair.split('=').map(s => s.trim());
    if (key && value) {
      auxAddressObj[key] = value;
    }
  }
  
  return auxAddressObj;
};

// 处理提交
const handleSubmit = async () => {
  try {
    if (!selectedHostId.value) {
      Message.warning(t.value('pleaseSelectHost') || '请先选择容器宿主');
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
    
    // 构建请求数据
    const requestData = {
      name: formData.name.trim(),
      driver: formData.driver,
      options: {},
      ipam: {
        Driver: 'default',
        Config: []
      },
      internal: formData.internal,
      enableIPv6: formData.enableIPv6,
      labels: {},
      check_duplicate: formData.check_duplicate,
      attachable: formData.attachable
    };
    
    // 记录日志
    console.log('表单数据:', formData);
    
    // 添加驱动选项（如果有）
    const options = formData.optionsList
      .filter(opt => opt.key && opt.key.trim())
      .reduce((acc, opt) => {
        acc[opt.key.trim()] = opt.value ? opt.value.trim() : '';
        return acc;
      }, {});
    
    if (Object.keys(options).length > 0) {
      requestData.options = options;
    }
    
    // 添加标签（如果有）
    const labels = formData.labelsList
      .filter(label => label.key && label.key.trim())
      .reduce((acc, label) => {
        acc[label.key.trim()] = label.value ? label.value.trim() : '';
        return acc;
      }, {});
    
    if (Object.keys(labels).length > 0) {
      requestData.labels = labels;
    }
    
    // 处理IPAM配置
    if (formData.ipamConfigList && formData.ipamConfigList.length > 0) {
      const validIpamConfigs = formData.ipamConfigList
        .filter(config => {
          // 至少有一个字段有值才算有效配置
          return config.Subnet || config.Gateway || config.IPRange || config.AuxAddress;
        })
        .map(config => {
          const ipamConfig = {};
          
          if (config.Subnet) ipamConfig.Subnet = config.Subnet.trim();
          if (config.Gateway) ipamConfig.Gateway = config.Gateway.trim();
          if (config.IPRange) ipamConfig.IPRange = config.IPRange.trim();
          if (config.AuxAddress) {
            const auxAddressObj = parseAuxAddress(config.AuxAddress);
            if (Object.keys(auxAddressObj).length > 0) {
              ipamConfig.AuxAddress = auxAddressObj;
            }
          }
          
          return ipamConfig;
        })
        .filter(config => Object.keys(config).length > 0);
      
      if (validIpamConfigs.length > 0) {
        requestData.ipam.Config = validIpamConfigs;
      }
    }
    
    console.log('最终提交的请求数据:', requestData);
    
    // 调用API创建网络
    const response = await createNetwork(selectedHostId.value, requestData);
    
    // 成功处理
    Message.success(t.value('createNetworkSuccess') || '创建网络成功');
    // 先更新本地状态
    isVisible.value = false;
    // 然后按顺序发出事件
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
  } catch (error) {
    // 错误处理
    try {
      console.error('创建网络失败:', error);
      const errorMsg = error.response?.data?.detail || error.message || t.value('createNetworkFailed') || '创建网络失败';
      Message.error(errorMsg);
    } catch (err) {
      console.error('Error displaying error message:', err);
    }
  } finally {
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
    // 添加窗口大小监听
    window.addEventListener('resize', checkIsMobile);
    // 初始化设备状态
    checkIsMobile();
  } catch (error) {
    console.error('Error in onMounted:', error);
  }
});

// 组件卸载时
onUnmounted(() => {
  try {
    // 移除事件监听
    window.removeEventListener('containerHostChanged', handleContainerHostChange);
    // 移除窗口大小监听
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

.config-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.ipam-config-item {
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 12px;
}

body[arco-theme="dark"] .ipam-config-item {
  border-color: #424244;
}

.driver-opts-section,
.labels-section,
.ipam-section {
  margin-bottom: 20px;
}

.driver-opts-section:last-child,
.labels-section:last-child,
.ipam-section:last-child {
  margin-bottom: 0;
}
</style>