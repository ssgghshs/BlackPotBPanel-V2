<template>
  <a-drawer
    v-model:visible="isVisible"
    :title="t('createContainer')"
    placement="right"
    :width="isMobile ? '90%' : 900"
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
      <a-form-item :label="t('name')" field="name">
        <a-input v-model="formData.name" :placeholder="t('nameInput')" allow-clear />
      </a-form-item>
      <a-form-item :label="t('image')" field="image">
        <a-select 
          v-model="formData.image" 
          :placeholder="t('imageInput')" 
          allow-clear 
          show-search 
          style="width: 100%"
        >
          <a-option 
            v-for="option in imageOptions" 
            :key="option.option" 
            :value="option.option"
          >
            {{ option.option }}
          </a-option>
        </a-select>
      </a-form-item>

      <a-card class="tabs-container" :bordered="true">
        <a-tabs :default-active-key="'ports'">
          <a-tab-pane key="ports" :title="t('ports')">
          <a-form-item>
            <div class="radio-group">
              <a-radio v-model="formData.publishAllPorts" value="custom">{{ t('customPorts')}}</a-radio>
              <a-radio v-model="formData.publishAllPorts" value="all">{{ t('publishAllPorts') }}</a-radio>
            </div>
          </a-form-item>
          <div v-if="formData.publishAllPorts === 'custom'" class="section-header">
            <a-button type="outline" size="small" @click="addPort">{{ t('add') }}</a-button>
          </div>
          <div v-if="formData.publishAllPorts === 'custom'" v-for="(p, idx) in formData.exposedPorts" :key="idx" class="grid-4">
            <a-input v-model="p.hostIP" :placeholder="t('hostIP')" allow-clear />
            <a-input v-model="p.hostPort" :placeholder="t('hostPortOrRange')" allow-clear />
            <a-input v-model="p.containerPort" :placeholder="t('containerPortOrRange')" allow-clear />
            <a-select v-model="p.protocol" :placeholder="'protocol'">
              <a-option value="tcp">TCP</a-option>
              <a-option value="udp">UDP</a-option>
            </a-select>
            <a-button type="outline" danger size="small" @click="removePort(idx)">{{ t('delete') }}</a-button>
          </div>
        </a-tab-pane>
          <a-tab-pane key="network" :title="t('network')">
            <div class="network-grid">
            <div class="network-column">
              <a-form-item :label="t('network')">
                <a-select 
                  v-model="formData.network" 
                  allow-clear 
                  style="width: 100%"
                >
                  <a-option 
                    v-for="option in networkOptions" 
                    :key="option.option" 
                    :value="option.option"
                  >
                    {{ option.option }}
                  </a-option>
                </a-select>
              </a-form-item>
              <a-form-item :label="t('domainName')">
                <a-input v-model="formData.domainName" allow-clear />
              </a-form-item>
              <a-form-item :label="'IPv4'">
                <a-input v-model="formData.ipv4" :placeholder="t('ipv4Input')" allow-clear />
              </a-form-item>
              <a-form-item :label="'DNS'">
                <div class="dns-container">
                  <div class="section-header">
                    <a-button type="outline" size="small" @click="addDNS">{{ t('add') }}</a-button>
                  </div>
                  <div v-for="(dns, idx) in formData.dnsList" :key="idx" class="dns-item">
                    <a-input v-model="dns.value" :placeholder="t('dnsInputHint')" allow-clear />
                    <a-button type="outline" danger size="small" @click="removeDNS(idx)">{{ t('delete') }}</a-button>
                  </div>
                </div>
              </a-form-item>
            </div>
            <div class="network-column">
              <a-form-item :label="t('hostname')">
                <a-input v-model="formData.hostname" allow-clear />
              </a-form-item>
              <a-form-item :label="'MAC'">
                <a-input v-model="formData.macAddr" allow-clear />
              </a-form-item>
              <a-form-item :label="'IPv6'">
                <a-input v-model="formData.ipv6" :placeholder="t('ipv6Input')" allow-clear />
              </a-form-item>
            </div>
          </div>
        </a-tab-pane>
        <a-tab-pane key="command" :title="t('command')">
          <a-form-item :label="'Entrypoint'">
            <a-input-tag v-model="formData.entrypoint" :placeholder="t('entrypointInput')" allow-clear />
          </a-form-item>
          <a-form-item :label="'Cmd'">
            <a-input-tag v-model="formData.cmd" :placeholder="t('cmdInput')" allow-clear />
          </a-form-item>
          <a-form-item :label="t('workingDir')">
            <a-input v-model="formData.workingDir" allow-clear />
          </a-form-item>
          <a-form-item :label="t('user')">
            <a-input v-model="formData.user" allow-clear />
          </a-form-item>
          <div class="grid-2">
            <a-form-item>
              <div class="inline-switch">
                <a-checkbox v-model="formData.tty" />
                <span>{{ t('pseudoTerminal') }}</span>
              </div>
            </a-form-item>
            <a-form-item>
              <div class="inline-switch">
                <a-checkbox v-model="formData.openStdin" />
                <span>{{ t('stdin') }}</span>
              </div>
            </a-form-item>
            <a-form-item>
              <div class="inline-switch">
                <a-checkbox v-model="formData.privileged" />
                <span>{{ t('privileged') }}</span>
              </div>
            </a-form-item>
            <a-form-item>
              <div class="inline-switch">
                <a-checkbox v-model="formData.autoRemove" />
                <span>{{ t('autoRemove') }}</span>
              </div>
            </a-form-item>
          </div>
        </a-tab-pane>
        <a-tab-pane key="resources" :title="t('resource')">
          <div class="resource-container">
            <div class="resource-item">
              <span class="resource-label">{{ t('cpuWeight') }}</span>
              <a-slider 
                v-model="formData.cpuShares" 
                :min="0" 
                :max="1024" 
                :step="1"
                class="resource-slider"
              />
              <a-input-number 
                v-model="formData.cpuShares" 
                :min="0" 
                :max="1024" 
                :step="1"
                class="resource-input"
              />
              <span class="resource-hint">{{ t('cpuWeightMax') }}</span>
            </div>
            <div class="resource-item">
              <span class="resource-label">{{ t('cpuLimit') }}</span>
              <a-slider 
                v-model="formData.nanoCPUs" 
                :min="0" 
                :max="resourcesLimit.cpus" 
                :step="1"
                class="resource-slider"
              />
              <a-input-number 
                v-model="formData.nanoCPUs" 
                :min="0" 
                :max="resourcesLimit.cpus" 
                :step="1"
                class="resource-input"
              />
              <span class="resource-hint">{{ t('cpuLimitMax') }}</span>
            </div>
            <div class="resource-item">
              <span class="resource-label">{{ t('memoryLimit') }}</span>
              <a-slider 
                v-model="formData.memory" 
                :min="0" 
                :max="resourcesLimit.total_memory" 
                :step="128"
                class="resource-slider"
              />
              <a-input-number 
                v-model="formData.memory" 
                :min="0" 
                :max="resourcesLimit.total_memory" 
                :step="128"
                class="resource-input"
              />
              <span class="resource-hint">{{ t('memoryLimitMax') }}</span>
            </div>
          </div>
        </a-tab-pane>
        <a-tab-pane key="restart" :title="t('restartPolicy')">
            <div class="checkbox-group">
              <a-radio 
                v-model="formData.restartPolicy" 
                value="no"
              >{{ t('noRestart') }}</a-radio>
              <a-radio 
                v-model="formData.restartPolicy" 
                value="always"
              >{{ t('always') }}</a-radio>
              <a-radio 
                v-model="formData.restartPolicy" 
                value="on-failure"
              >{{ t('onFailure') }}</a-radio>
              <a-radio 
                v-model="formData.restartPolicy" 
                value="unless-stopped"
              >{{ t('unlessStopped') }}</a-radio>
            </div>
        </a-tab-pane>
        <a-tab-pane key="volumes" :title="t('volumes')">
          <div class="section-header">
            <a-button type="outline" size="small" @click="addVolume">{{ t('add') }}</a-button>
          </div>
          <div v-for="(v, idx) in formData.volumes" :key="idx">
            <div class="grid-5">
              <a-select v-model="v.type" style="min-width: 100px" @change="handleVolumeTypeChange(v, idx)">
                <a-option value="bind">{{ t('directory') }}</a-option>
                <a-option value="volume">{{ t('volumes') }}</a-option>
              </a-select>
              <a-select
                v-if="v.type === 'volume'"
                v-model="v.sourceDir"
                :placeholder="t('sourceDirorVolume')"
                allow-clear
                show-search
                allow-custom-value
                allow-create
                style="width: 100%"
              >
                <a-option
                  v-for="option in volumeOptions"
                  :key="option.option"
                  :value="option.option"
                  :title="option.option"
                >
                  {{ option.option.length > 20 ? option.option.substring(0, 15) + '...' + option.option.substring(option.option.length - 5) : option.option }}
                </a-option>
              </a-select>
              <a-input
                v-else
                v-model="v.sourceDir"
                :placeholder="t('sourceDirorVolume')"
                allow-clear
              />
              <a-input v-model="v.containerDir" :placeholder="t('containerDir')" allow-clear />
              <a-select v-model="v.mode" style="min-width: 100px">
                <a-option value="rw">{{ t('rw') }}</a-option>
                <a-option value="ro">{{ t('ro') }}</a-option>
              </a-select>
              <div v-if="v.type === 'bind'">
                <a-select v-model="v.shared" :placeholder="t('shared')" allow-clear>
                  <a-option value="shared">shared</a-option>
                  <a-option value="slave">slave</a-option>
                  <a-option value="private">private</a-option>
                  <a-option value="rslave">rslave</a-option>
                  <a-option value="rprivate">rprivate</a-option>
                </a-select>
              </div>
              <div v-else style="min-width: 120px;"></div>
              <a-button type="outline" danger size="small" @click="removeVolume(idx)">{{ t('delete') }}</a-button>
            </div>
          </div>
        </a-tab-pane>
        <a-tab-pane key="labels_env" :title="t('labels') + ' / ' + 'Env'">
            <a-form-item :label="t('labels')">
              <div class="label-env-container">
                <div class="section-header">
                  <a-button type="outline" size="small" @click="addLabel">{{ t('add') }}</a-button>
                </div>
                <div v-for="(label, idx) in formData.labelList" :key="idx" class="label-env-item">
                  <a-input v-model="label.key" :placeholder="t('key')" allow-clear />
                  <a-input v-model="label.value" :placeholder="t('value')" allow-clear />
                  <a-button type="outline" danger size="small" @click="removeLabel(idx)">{{ t('delete') }}</a-button>
                </div>
              </div>
            </a-form-item>
            <a-form-item :label="'Env'">
              <div class="label-env-container">
                <div class="section-header">
                  <a-button type="outline" size="small" @click="addEnv">{{ t('add') }}</a-button>
                </div>
                <div v-for="(env, idx) in formData.envList" :key="idx" class="label-env-item">
                  <a-input v-model="env.key" :placeholder="t('key')" allow-clear />
                  <a-input v-model="env.value" :placeholder="t('value')" allow-clear />
                  <a-button type="outline" danger size="small" @click="removeEnv(idx)">{{ t('delete') }}</a-button>
                </div>
              </div>
            </a-form-item>
          </a-tab-pane>
      </a-tabs>
      </a-card>
    </a-form>

    <div class="drawer-footer">
      <a-button @click="handleClose" :disabled="isSubmitting" style="margin-right: 8px">{{ t('cancel') }}</a-button>
      <a-button type="primary" @click="handleSubmit" :loading="isSubmitting">{{ t('confirm') }}</a-button>
    </div>
  </a-drawer>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue';
import { t } from '../../utils/locale';
import { createContainer, getContainerNodeResourcesLimit, getImageOptions, getNetworkOptions, getVolumeOptions } from '../../api/container';
import { Message } from '@arco-design/web-vue';
import { Drawer as ADrawer, Form as AForm, FormItem as AFormItem, Input as AInput, InputTag as AInputTag, InputNumber as AInputNumber, Select as ASelect, Option as AOption, Button as AButton, Switch as ASwitch, Tabs as ATabs, TabPane as ATabPane, Card as ACard, Radio as ARadio, Checkbox as ACheckbox, Slider as ASlider } from '@arco-design/web-vue';

const props = defineProps({
  visible: { type: Boolean, default: false }
});
const emit = defineEmits(['update:visible', 'success', 'close']);

const isVisible = ref(false);
const selectedHostId = ref(null);
const isSubmitting = ref(false);
const formRef = ref(null);
// 资源数据相关状态
const resourcesLimit = ref({});
const imageOptions = ref([]);
const networkOptions = ref([]);
const volumeOptions = ref([]);
const isLoading = ref(false);
// 响应式布局相关
const isMobile = ref(false);

const checkIsMobile = () => {
  isMobile.value = window.innerWidth < 768;
};

const formData = reactive({
  name: '',
  image: '',
  network: '',
  hostname: '',
  domainName: '',
  macAddr: '',
  dns: [],
  dnsList: [],
  ipv4: '',
  ipv6: '',
  publishAllPorts: 'custom',
  exposedPorts: [],
  tty: false,
  openStdin: false,
  workingDir: '',
  user: '',
  cmd: [],
  entrypoint: [],
  cpuShares: 0,
  nanoCPUs: 0,
  memory: 0,
  privileged: false,
  autoRemove: false,
  volumes: [],
  labels: [],
  labelList: [],
  env: [],
  envList: [],
  restartPolicy: 'no'
});

const formRules = {
  name: [
    { 
      required: true, 
      message: t.value('pleaseInputName'), 
      trigger: 'blur' 
    }
  ],
  image: [
    {
      required: true, 
      message: t.value('pleaseInputImage'), 
      trigger: 'blur' 
    }
  ]
};

watch(() => props.visible, (nv) => {
  isVisible.value = nv;
  if (nv) {
    resetForm();
    // 组件打开时，自动请求数据
    if (selectedHostId.value) {
      fetchAllData(selectedHostId.value);
    }
  }
}, { immediate: true });

const handleContainerHostChange = (event) => {
  if (event && event.detail && event.detail.hostId) {
    const newHostId = event.detail.hostId;
    if (newHostId !== selectedHostId.value) {
      selectedHostId.value = newHostId;
      // 如果组件已打开，重新获取数据
      if (isVisible.value) {
        fetchAllData(newHostId);
      }
    }
  }
};

onMounted(() => {
  window.addEventListener('containerHostChanged', handleContainerHostChange);
  window.addEventListener('resize', checkIsMobile);
  checkIsMobile();
  const saved = localStorage.getItem('selectedContainerHostId');
  if (saved) selectedHostId.value = saved;
});
onUnmounted(() => {
  window.removeEventListener('containerHostChanged', handleContainerHostChange);
  window.removeEventListener('resize', checkIsMobile);
});

const resetForm = () => {
  try {
    if (formRef.value) formRef.value.resetFields();
    formData.name = '';
    formData.image = '';
    formData.network = 'bridge';
    formData.hostname = '';
    formData.domainName = '';
    formData.macAddr = '';
    formData.dns = [];
    formData.dnsList = [];
    formData.ipv4 = '';
    formData.ipv6 = '';
    formData.publishAllPorts = 'custom';
    formData.exposedPorts = [];
    formData.tty = false;
    formData.openStdin = false;
    formData.workingDir = '';
    formData.user = '';
    formData.cmd = [];
    formData.entrypoint = [];
    formData.cpuShares = 0;
    formData.nanoCPUs = 0;
    formData.memory = 0;
    formData.privileged = false;
    formData.autoRemove = false;
    formData.volumes = [];
    formData.labels = [];
    formData.labelList = [];
    formData.env = [];
    formData.envList = [];
    formData.restartPolicy = 'no';
    if (!selectedHostId.value) {
      const saved = localStorage.getItem('selectedContainerHostId');
      if (saved) selectedHostId.value = saved;
    }
  } catch (e) {
    console.error(e);
  }
};

const addDNS = () => {
  formData.dnsList.push({ value: '' });
};
const removeDNS = (i) => {
  formData.dnsList.splice(i, 1);
};

const addLabel = () => {
  formData.labelList.push({ key: '', value: '' });
};
const removeLabel = (i) => {
  formData.labelList.splice(i, 1);
};

const addEnv = () => {
  formData.envList.push({ key: '', value: '' });
};
const removeEnv = (i) => {
  formData.envList.splice(i, 1);
};

// 格式化DNS、labels和env数据
const formatMultiValueFields = () => {
  // 处理DNS
  formData.dns = formData.dnsList
    .filter(item => item.value.trim())
    .map(item => item.value.trim());
    
  // 处理labels
  formData.labels = formData.labelList
    .filter(item => item.key.trim() && item.value.trim())
    .map(item => `${item.key.trim()}=${item.value.trim()}`);
    
  // 处理env
  formData.env = formData.envList
    .filter(item => item.key.trim() && item.value.trim())
    .map(item => `${item.key.trim()}=${item.value.trim()}`);
};

const addPort = () => {
  formData.exposedPorts.push({ hostIP: '', hostPort: '', containerPort: '', protocol: 'tcp' });
};
const removePort = (i) => {
  formData.exposedPorts.splice(i, 1);
};
const addVolume = () => {
  formData.volumes.push({ type: 'bind', sourceDir: '', containerDir: '', mode: 'rw', shared: 'private' });
};

// 处理存储卷类型变化的方法
const handleVolumeTypeChange = (volume, index) => {
  // 当从volume切换到bind时，清空sourceDir
  if (volume.type === 'bind') {
    volume.sourceDir = '';
  }
};
const removeVolume = (i) => {
  formData.volumes.splice(i, 1);
};

// 获取节点资源限制
const fetchResourcesLimit = async (nodeId) => {
  if (!nodeId) return;
  try {
    const data = await getContainerNodeResourcesLimit(nodeId);
    resourcesLimit.value = data;
  } catch (error) {
    console.error('获取节点资源限制失败:', error);
  }
};

// 获取镜像选项列表
const fetchImageOptions = async (nodeId) => {
  if (!nodeId) return;
  try {
    const data = await getImageOptions(nodeId);
    imageOptions.value = data.data || [];
  } catch (error) {
    console.error('获取镜像选项失败:', error);
  }
};

// 获取网络选项列表
const fetchNetworkOptions = async (nodeId) => {
  if (!nodeId) return;
  try {
    const data = await getNetworkOptions(nodeId);
    networkOptions.value = data.data || [];
  } catch (error) {
    console.error('获取网络选项失败:', error);
  }
};

// 获取存储卷选项列表
const fetchVolumeOptions = async (nodeId) => {
  if (!nodeId) return;
  try {
    const data = await getVolumeOptions(nodeId);
    volumeOptions.value = data.data || [];
  } catch (error) {
    console.error('获取存储卷选项失败:', error);
  }
};

// 批量获取所有数据
const fetchAllData = async (nodeId) => {
  if (!nodeId) return;
  
  isLoading.value = true;
  try {
    // 并行请求所有数据
    await Promise.all([
      fetchResourcesLimit(nodeId),
      fetchImageOptions(nodeId),
      fetchNetworkOptions(nodeId),
      fetchVolumeOptions(nodeId)
    ]);
  } catch (error) {
    console.error('获取数据失败:', error);
  } finally {
    isLoading.value = false;
  }
};

// 已使用ARadio的v-model直接绑定，不需要单独的处理函数

const handleClose = () => {
  emit('update:visible', false);
  emit('close');
};

const handleSubmit = async () => {
  if (!formRef.value) return;
  
  // 检查是否选择了主机
  if (!selectedHostId.value) {
    Message.warning(t('pleaseSelectHost'));
    return;
  }
  
  // 先进行表单验证，参考ComposeCreate.vue的处理方式
  const errors = await formRef.value.validate().catch(error => {
    // 表单验证失败，直接返回，不执行API调用
    console.log('表单验证失败:', error);
    return false;
  });
  
  // 如果验证失败或者返回了错误，则不继续执行后续逻辑
  if (errors === false || (errors && Object.keys(errors).length > 0)) {
    return;
  }
  
  // 只有表单验证通过后才执行API调用
  isSubmitting.value = true;
  
  try {
    // 格式化多值字段
    formatMultiValueFields();
    
    // 将publishAllPorts字符串值转换为布尔值提交给后端
    const payload = { 
      ...formData,
      publishAllPorts: formData.publishAllPorts === 'all' 
    };
    await createContainer(selectedHostId.value, payload);
    Message.success(t.value('createSuccess'));
    emit('success');
    emit('update:visible', false);
  } catch (error) {
    console.error('创建容器失败:', error);
    const msg = error?.response?.data?.detail || error?.message || t.value('createFailed');
    Message.error(msg);
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<style scoped>
.drawer-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}
.inline-switch {
      display: flex;
      align-items: center;
      gap: 12px;
      justify-content: flex-start;
    }
.radio-group {
      display: flex;
      gap: 20px;
      align-items: center;
      justify-content: flex-start;
    }
.section-header {
      display: flex;
      justify-content: flex-start;
      margin-bottom: 8px;
    }
.grid-5 {
  display: grid;
  grid-template-columns: 120px 1fr 1fr 120px 120px auto;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.grid-4 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr 120px auto;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.grid-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}
.network-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.network-column {
  display: flex;
  flex-direction: column;
}
.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.dns-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.dns-item {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  align-items: center;
}
.label-env-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.label-env-item {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 8px;
  align-items: center;
}
.resource-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 8px 0;
}
.resource-item {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}
.resource-label {
  min-width: 100px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-1, #1d2129);
  flex-shrink: 0;
}
.resource-slider {
  flex: 1;
  min-width: 0;
}
.resource-input {
  width: 120px;
  flex-shrink: 0;
}
.resource-hint {
  min-width: 120px;
  font-size: 13px;
  color: #86909c;
  flex-shrink: 0;
}
</style>
