<template>
  <a-card class="sec-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('sshManger') }}</span>
        <a-tag :color="sshInfo.status ? 'green' : 'red'">
          {{ sshInfo.status ? t('running') : t('stopped') }}
        </a-tag>
        <div class="ssh-actions">
          <a-link type="text" size="small" :loading="sshLoading.stop" @click="handleSSHAction('stop')" :disabled="!sshInfo.status || sshLoading.stop">
            {{ t('stop') }}
          </a-link>
          <a-link type="text" size="small" :loading="sshLoading.restart" @click="handleSSHAction('restart')" :disabled="!sshInfo.status || sshLoading.restart">
            {{ t('restart') }}
          </a-link>
          <a-link type="text" size="small" :loading="sshLoading.start" @click="handleSSHAction('start')" :disabled="sshInfo.status || sshLoading.start">
            {{ t('start') }}
          </a-link>
        </div>
      </div>
    </template>

    <!--  内容区域  -->
    <a-tabs v-model:active-key="activeTab" default-active-key="1" position="left" @change="handleTabChange" :destroy-on-hide="false">
      <a-tab-pane key="1" :title="t('BasicSetting') ">
        <div class="ssh-settings">
          <div class="additional-actions">
              <a-button type="primary" @click="handleTabChange('2')">{{ t('moreConfig') }}</a-button>
            <a-button type="primary" @click="handleOpenAuthKeysDrawer">
              {{ t('authorizationKey') }}
            </a-button>
          </div>
          <a-form layout="vertical" class="ssh-form" :model="sshInfo" v-if="!loading">
            <a-form-item :label="t('sshPort')" >
              <div class="port-input-container">
                <a-input 
                  v-model="sshInfo.port"
                />
                <a-button 
                  type="outline" 
                  @click="handlePortSave"
                  :loading="updatingConfig"
                  style="margin-left: 8px;"
                >
                  {{ t('save') }}
                </a-button>
              </div>
            </a-form-item>
            
            <a-form-item :label="t('allowRootLogin')">
              <a-select 
                v-model="sshInfo.permitRootLogin"
                @change="handleConfigChange('permitRootLogin', sshInfo.permitRootLogin, sshInfo.permitRootLogin)"
              >
                <a-option value="yes">yes-{{ t('allowLoginAsRoot') }}</a-option>
                <a-option value="no">no-{{ t('denyLoginAsRoot') }}</a-option>
                <a-option value="force-command-only">force-command-only-{{ t('onlyExecuteCommand') }}</a-option>
                <a-option value="without-password">without-password-{{ t('loginWithoutPassword') }}</a-option>
              </a-select>
            </a-form-item>
            
            <a-form-item :label="t('passwordAuthentication')">
              <div class="switch-container">
                <a-switch 
                  v-model="sshInfo.passwordAuthEnabled" 
                  @change="(checked) => {
                    const newValue = checked ? 'yes' : 'no';
                    const oldValue = sshInfo.passwordAuthentication;
                    sshInfo.passwordAuthentication = newValue; // 先临时更新，等待确认
                    handleConfigChange('passwordAuthentication', newValue, oldValue);
                  }"
                />
                <span class="switch-label">{{ sshInfo.passwordAuthEnabled ? t('enable') : t('disable') }}</span>
              </div>
            </a-form-item>
            
            <a-form-item :label="t('pubkeyAuthentication')">
              <div class="switch-container">
                <a-switch 
                  v-model="sshInfo.pubkeyAuthEnabled" 
                  @change="(checked) => {
                    const newValue = checked ? 'yes' : 'no';
                    const oldValue = sshInfo.pubkeyAuthentication;
                    sshInfo.pubkeyAuthentication = newValue; // 先临时更新，等待确认
                    handleConfigChange('pubkeyAuthentication', newValue, oldValue);
                  }"
                />
                <span class="switch-label">{{ sshInfo.pubkeyAuthEnabled ? t('enable') : t('disable') }}</span>
              </div>
            </a-form-item>
            
            <a-form-item :label="t('useDNS')">
              <div class="switch-container">
                <a-switch 
                  v-model="sshInfo.dnsEnabled" 
                  @change="(checked) => {
                    const newValue = checked ? 'yes' : 'no';
                    const oldValue = sshInfo.useDNS;
                    sshInfo.useDNS = newValue; // 先临时更新，等待确认
                    handleConfigChange('useDNS', newValue, oldValue);
                  }"
                />
                <span class="switch-label">{{ sshInfo.dnsEnabled ? t('enable') : t('disable') }}</span>
              </div>
            </a-form-item>
          </a-form>
          <div v-else class="loading-container">
            <a-spin :tip="t('loading')" />
          </div>
        </div>
      </a-tab-pane>
      <a-tab-pane key="2" :title="t('configFile')">
        <div class="config-file-container">
          <div class="config-actions">
            <a-button type="primary" @click="fetchSSHConfigFileContent" :loading="configFileLoading">
              {{ t('refresh') }}
            </a-button>
            <a-button :loading="savingConfig" @click="saveSSHConfig">
              {{ t('save') }}
            </a-button>
          </div>
          <div ref="monacoEditorRef" class="monaco-editor-container"></div>
        </div>
      </a-tab-pane>     
      <a-tab-pane key="3" :title="t('loginLogs')">
        <SshLoginLog />
      </a-tab-pane>
    </a-tabs>
  </a-card>

  <!-- 确认修改对话框 -->
  <a-modal
    v-model:visible="showConfirmDialog"
    :title="t('confirmUpdate')"
    @ok="handleConfirmUpdate"
    @cancel="handleCancelUpdate"
    :ok-loading="updatingConfig"
    :cancel-text="t('cancel')"
    :ok-text="t('confirm')"
  >
    <div>
      <p>{{ t('confirmUpdateConfig', { field: getFieldLabel(pendingConfig.field), value: pendingConfig.value }) }}</p>
    </div>
  </a-modal>
  
  <!-- SSH操作确认对话框 -->
  <a-modal
    v-model:visible="showSSHActionDialog"
    :title="t('confirmAction')"
    @ok="handleConfirmSSHAction"
    @cancel="handleCancelSSHAction"
    :ok-loading="sshLoading[pendingAction]"
    :cancel-text="t('cancel')"
    :ok-text="t('confirm')"
  >
    <div>
      <p>{{ t('confirmSSHAction', { action: getActionLabel(pendingAction) }) }}</p>
    </div>
  </a-modal>
  
  <!-- SSH重启提示对话框 -->
  <a-modal
    v-model:visible="showRestartDialog"
    :title="t('restartSSH')"
    @ok="handleConfirmRestartSSH"
    @cancel="handleCancelRestartSSH"
    :ok-loading="sshLoading.restart"
    :cancel-text="t('cancel')"
    :ok-text="t('confirm')"
  >
    <div>
      <p>{{ t('restartSSHNotice') }}</p>
    </div>
  </a-modal>
  
  <!-- authorized_keys抽屉组件 -->
  <a-drawer
    v-model:visible="showAuthKeysDrawer"
    :title="t('authorizationKey')"
    size="large"
    :width="800"
    :footer="false"
    :placement="'right'"
    :destroy-on-close="false"
    :mask-closable="true"
  >
    <div class="auth-keys-container">
      <div class="auth-keys-actions">
        <a-button type="primary" @click="fetchAuthorizedKeysContent" :loading="loadingAuthKeys">
          {{ t('refresh') }}
        </a-button>
        <a-button type="primary" :loading="savingAuthKeys" @click="saveAuthorizedKeys">
          {{ t('save') }}
        </a-button>
      </div>
      <div ref="authKeysEditorRef" class="monaco-editor-container"></div>
    </div>
  </a-drawer>
</template>

<script setup>
import { reactive, onMounted, onBeforeUnmount, ref } from 'vue';
import { t } from '../../utils/locale'
import { getLocalSSHConfig, operateLocalSSHService, getSSHConfigContent, updateSSHConfig, getAuthorizedKeysContent } from '../../api/host'
import { saveFileContent } from '../../api/file'
import { Message } from '@arco-design/web-vue';
import SshLoginLog from '../../components/security/SshLoginLog.vue';


// 加载状态
const loading = ref(true);
// 配置文件相关状态
const configFileLoading = ref(false);
const savingConfig = ref(false);
const configFileContent = ref('');
const monacoEditorRef = ref(null);
let monacoEditor = null;
// SSH操作loading状态
const sshLoading = reactive({
  stop: false,
  restart: false,
  start: false
});
// 确认对话框相关状态
const showConfirmDialog = ref(false);
const pendingConfig = ref({
  field: '',
  value: '',
  originalValue: ''
});
const updatingConfig = ref(false);

// SSH操作确认对话框相关状态
const showSSHActionDialog = ref(false);
const pendingAction = ref('');

// SSH重启提示对话框相关状态
const showRestartDialog = ref(false);

// authorized_keys抽屉相关状态
const showAuthKeysDrawer = ref(false);
const authKeysContent = ref('');
const authKeysPath = ref('');
const loadingAuthKeys = ref(false);
const savingAuthKeys = ref(false);
const authKeysEditorRef = ref(null);
let authKeysEditor = null;

// 获取配置项的标签名称
const getFieldLabel = (field) => {
  const labels = {
    port: t.value('sshPort'),
    passwordAuthentication: t.value('passwordAuthentication'),
    pubkeyAuthentication: t.value('pubkeyAuthentication'),
    permitRootLogin: t.value('allowRootLogin'),
    useDNS: t.value('useDNS')
  };
  return labels[field] || field;
};

// 获取操作标签名称
const getActionLabel = (action) => {
  const labels = {
    stop: t.value('stop'),
    restart: t.value('restart'),
    start: t.value('start')
  };
  return labels[action] || action;
};

// 处理配置项修改
const handleConfigChange = (field, value, originalValue) => {
  pendingConfig.value = {
    field,
    value,
    originalValue
  };
  showConfirmDialog.value = true;
};

// 处理端口保存
const handlePortSave = () => {
  // 验证端口号是否为有效的数字
  const port = sshInfo.port;
  const portNum = parseInt(port);
  
  if (!port || isNaN(portNum) || portNum < 1 || portNum > 65535) {
    Message.error(t.value('sshPortInvalid'));
    return;
  }
  
  // 获取原始端口值（这里暂时使用当前值，实际中应该有一个保存原始值的变量）
  // 由于没有明确的原始值存储，我们需要在fetchSSHInfo中保存
  const originalPort = sshInfo.originalPort || port;
  
  // 调用handleConfigChange显示确认对话框
  handleConfigChange('port', port, originalPort);
};

// SSH信息数据
const sshInfo = reactive({
  install: false,
  status: false,
  port: '',
  passwordAuthentication: 'no',
  pubkeyAuthentication: 'no',
  permitRootLogin: 'no',
  useDNS: 'no',
  currentUser: '',
  // 辅助布尔值用于开关绑定
  passwordAuthEnabled: false,
  pubkeyAuthEnabled: false,
  dnsEnabled: false
})

// 获取SSH配置信息
const fetchSSHInfo = async (showMessage = false) => {
  loading.value = true;
  try {
    const response = await getLocalSSHConfig();
    console.log('获取到的SSH配置数据:', response); // 添加调试日志
    
    // 确保response是对象类型
    if (typeof response === 'object' && response !== null) {
      // 保存原始端口值，用于取消操作时恢复
      sshInfo.originalPort = response.port || '';
      // 直接更新需要的字段，而不是Object.assign整个对象
      sshInfo.port = response.port || '';
      sshInfo.permitRootLogin = response.permitRootLogin || 'no';
      sshInfo.passwordAuthentication = response.passwordAuthentication || 'no';
      sshInfo.pubkeyAuthentication = response.pubkeyAuthentication || 'no';
      sshInfo.useDNS = response.useDNS || 'no';
      sshInfo.status = response.status || false;
      sshInfo.install = response.install || false;
      sshInfo.currentUser = response.currentUser || '';
      
      // 初始化辅助布尔值
      sshInfo.passwordAuthEnabled = response.passwordAuthentication === 'yes';
      sshInfo.pubkeyAuthEnabled = response.pubkeyAuthentication === 'yes';
      sshInfo.dnsEnabled = response.useDNS === 'yes';
      
      // 只在明确要求时显示成功消息（例如用户点击刷新按钮）
      if (showMessage) {
        Message.success(t.value('fetchSuccess'));
      }
    }
  } catch (error) {
    console.error('获取SSH配置信息失败:', error);
    Message.error(t.value('fetchFailed') + ': ' + (error.message || t.value('unknownError')));
  } finally {
    loading.value = false;
  }
}

// 实际执行SSH服务操作
const executeSSHAction = async (action) => {
  try {
    // 设置当前操作的loading状态
    sshLoading[action] = true;
    
    // 准备请求数据
    const requestData = { action };
    
    // 调用API执行SSH服务操作
    await operateLocalSSHService(requestData);
    
    Message.success(t.value('operationSuccess'));
    
    // 重新获取SSH信息以更新状态
    await fetchSSHInfo();
  } catch (error) {
    Message.error(t.value('operationFailed'));
    console.error('SSH服务操作失败:', error);
    // 失败时重新获取最新状态
    await fetchSSHInfo();
  } finally {
    // 取消loading状态
    sshLoading[action] = false;
  }
};

// 处理SSH服务操作（显示确认对话框）
const handleSSHAction = (action) => {
  pendingAction.value = action;
  showSSHActionDialog.value = true;
};

// 处理确认SSH操作
const handleConfirmSSHAction = async () => {
  if (pendingAction.value) {
    await executeSSHAction(pendingAction.value);
    showSSHActionDialog.value = false;
  }
};

// 处理取消SSH操作
const handleCancelSSHAction = () => {
  pendingAction.value = '';
  showSSHActionDialog.value = false;
};

// 处理确认重启SSH
const handleConfirmRestartSSH = async () => {
  // 调用现有的executeSSHAction函数执行重启操作
  await executeSSHAction('restart');
  showRestartDialog.value = false;
};

// 处理取消重启SSH
const handleCancelRestartSSH = () => {
  showRestartDialog.value = false;
};

// 更新SSH配置项
const updateSSHConfigItem = async (field, value) => {
  // 显示更新中的提示
  const loadingMessage = Message.loading({
    content: t.value('updating'),
    duration: 0 // 持续显示直到手动关闭
  });
  
  try {
    // 准备请求数据，只包含需要更新的字段
    const requestData = {
      [field]: value
    };
    
    // 调用API更新配置
    const response = await updateSSHConfig(requestData);
    
    // 关闭加载提示
    loadingMessage.close();
    
    // 检查响应状态 - 兼容多种响应格式
    // 1. 如果响应有 code 字段，检查是否为 200
    // 2. 如果没有 code 字段但请求成功（没抛出异常），也认为是成功
    const isSuccess = !response || response.code === 200 || response.code === undefined;
    
    if (isSuccess) {
      // 显示成功提示，包含具体更新的配置项
      Message.success(`${t.value('updateSuccess')}`);
      
      // 重新获取SSH信息以更新状态
      await fetchSSHInfo();
    } else {
      // 如果有明确的失败响应
      throw new Error(response?.message || t.value('updateFailed'));
    }
  } catch (error) {
    // 关闭加载提示
    loadingMessage.close();
    
    // 显示详细的错误信息
    const errorMsg = error.response?.data?.message || error.message || t.value('updateFailed');
    Message.error(`${getFieldLabel(field)} ${t.value('updateFailed')}: ${errorMsg}`);
    console.error('Update SSH config error:', error);
    throw error; // 抛出错误，让调用者知道更新失败
  }
};

// 处理确认更新
const handleConfirmUpdate = async () => {
  const { field, value } = pendingConfig.value;
  
  if (!field) return;
  
  updatingConfig.value = true;
  try {
    await updateSSHConfigItem(field, value);
    showConfirmDialog.value = false;
  } catch (error) {
    // 如果更新失败，恢复原始值（对于开关类型的字段，需要同步辅助布尔值）
    if (field === 'passwordAuthentication') {
      sshInfo.passwordAuthEnabled = pendingConfig.value.originalValue === 'yes';
      sshInfo.passwordAuthentication = pendingConfig.value.originalValue;
    } else if (field === 'pubkeyAuthentication') {
      sshInfo.pubkeyAuthEnabled = pendingConfig.value.originalValue === 'yes';
      sshInfo.pubkeyAuthentication = pendingConfig.value.originalValue;
    } else if (field === 'useDNS') {
      sshInfo.dnsEnabled = pendingConfig.value.originalValue === 'yes';
      sshInfo.useDNS = pendingConfig.value.originalValue;
    } else if (field === 'port' || field === 'permitRootLogin') {
      sshInfo[field] = pendingConfig.value.originalValue;
    }
  } finally {
    updatingConfig.value = false;
  }
};

// 处理取消更新
const handleCancelUpdate = () => {
  const { field, originalValue } = pendingConfig.value;
  
  // 恢复原始值
  if (field === 'passwordAuthentication') {
    sshInfo.passwordAuthentication = originalValue;
    sshInfo.passwordAuthEnabled = originalValue === 'yes';
  } else if (field === 'pubkeyAuthentication') {
    sshInfo.pubkeyAuthentication = originalValue;
    sshInfo.pubkeyAuthEnabled = originalValue === 'yes';
  } else if (field === 'useDNS') {
    sshInfo.useDNS = originalValue;
    sshInfo.dnsEnabled = originalValue === 'yes';
  } else if (field === 'port' || field === 'permitRootLogin') {
    sshInfo[field] = originalValue;
  }
  
  showConfirmDialog.value = false;
};

// 获取SSH配置文件内容
const fetchSSHConfigFileContent = async () => {
  configFileLoading.value = true;
  try {
    const res = await getSSHConfigContent();
    if (res && res.content) {
      configFileContent.value = res.content;
      if (monacoEditor) {
        monacoEditor.setValue(res.content);
      }
    }
  } catch (error) {
    Message.error(error.msg || `${t.value('fetch')} ${t.value('ssh')} ${t.value('config')} ${t.value('failed')}`);
    // console.error('Fetch SSH config file error:', error);
  } finally {
    configFileLoading.value = false;
  }
};

// 保存SSH配置文件内容
const saveSSHConfig = async () => {
  if (!monacoEditor) {
    Message.error(`${t.value('editor')} ${t.value('not')} ${t.value('initialized')}`);
    return;
  }
  
  savingConfig.value = true;
  try {
    // 从编辑器获取内容
    const content = monacoEditor.getValue();
    
    // 获取配置文件路径信息
    const res = await getSSHConfigContent();
    if (res && res.path) {
      // 将path分离为目录路径和文件名
      const pathParts = res.path.split('/');
      const filename = pathParts.pop(); // 获取最后一部分作为文件名
      const path = pathParts.join('/'); // 其余部分作为目录路径
      
      // 调用saveFileContent方法保存文件
      await saveFileContent({
        path,
        filename,
        content
      });
      
      // 保存成功，显示重启提示对话框
      showRestartDialog.value = true;
    } else {
      // 如果没有获取到路径信息，抛出错误并提供更详细的信息
      const errorMsg = res ? '配置文件路径信息缺失' : '获取配置文件信息失败';
      throw new Error(errorMsg);
    }
  } catch (error) {
    // 显示错误信息，优先使用error.message，然后是error.msg，最后是默认错误信息
    Message.error(error.message || error.msg || t.value('saveFileFailed'));
    // console.error('Save SSH config file error:', error);
  } finally {
    savingConfig.value = false;
  }
};

// 获取authorized_keys文件内容
const fetchAuthorizedKeysContent = async () => {
  loadingAuthKeys.value = true;
  try {
    const res = await getAuthorizedKeysContent();
    if (res && res.content) {
      authKeysContent.value = res.content;
      authKeysPath.value = res.path || '';
      if (authKeysEditor) {
        authKeysEditor.setValue(res.content);
      }
    }
  } catch (error) {
    Message.error(error.msg || `${t.value('fetch')} authorized_keys ${t.value('failed')}`);
  } finally {
    loadingAuthKeys.value = false;
  }
};

// 保存authorized_keys文件内容
const saveAuthorizedKeys = async () => {
  if (!authKeysEditor) {
    Message.error(`${t.value('editor')} ${t.value('not')} ${t.value('initialized')}`);
    return;
  }
  
  savingAuthKeys.value = true;
  try {
    // 从编辑器获取内容
    const content = authKeysEditor.getValue();
    
    // 获取配置文件路径信息
    const res = await getAuthorizedKeysContent();
    if (res && res.path) {
      // 将path分离为目录路径和文件名
      const pathParts = res.path.split('/');
      const filename = pathParts.pop(); // 获取最后一部分作为文件名
      const path = pathParts.join('/'); // 其余部分作为目录路径
      
      // 调用saveFileContent方法保存文件
      await saveFileContent({
        path,
        filename,
        content
      });
      
      // 保存成功，显示成功提示
      Message.success(t.value('fileSaved'));
    } else {
      // 如果没有获取到路径信息，抛出错误
      const errorMsg = res ? '配置文件路径信息缺失' : '获取配置文件信息失败';
      throw new Error(errorMsg);
    }
  } catch (error) {
    // 显示错误信息
    Message.error(error.message || error.msg || t.value('saveFileFailed'));
  } finally {
    savingAuthKeys.value = false;
  }
};


// 初始化Monaco编辑器
const initMonacoEditor = async () => {
  if (!monacoEditorRef.value || monacoEditor) return;
  
  try {
    // 动态导入monaco-editor
    const monaco = await import('monaco-editor');
    
    // 创建编辑器实例
    monacoEditor = monaco.editor.create(monacoEditorRef.value, {
      value: configFileContent.value,
      language: 'ssh-config',
      theme: 'vs-dark',
      automaticLayout: true,
      minimap: { enabled: true },
      scrollBeyondLastLine: false,
      fontSize: 14,
      tabSize: 2
    });
    
    // 如果是首次初始化且内容为空，获取配置文件内容
    if (!configFileContent.value) {
      fetchSSHConfigFileContent();
    }
    
  } catch (error) {
    console.error('Failed to load Monaco Editor:', error);
    Message.error(`${t.value('load')} Monaco Editor ${t.value('failed')}`);
  }
};

// 当前活动标签页
  const activeTab = ref('1');

  // 处理标签页切换
  const handleTabChange = (key) => {
    activeTab.value = key;
    // 即使编辑器已经初始化，如果用户切换到配置文件标签页且内容为空，仍然获取配置文件内容
    if (key === '2' && !configFileContent.value) {
      fetchSSHConfigFileContent();
    }
  };
  
  // 处理打开authorized_keys抽屉
  const handleOpenAuthKeysDrawer = async () => {
    showAuthKeysDrawer.value = true;
    
    // 添加一个微任务延迟，确保抽屉DOM已渲染
    await new Promise(resolve => setTimeout(resolve, 0));
    
    // 初始化编辑器
    if (authKeysEditorRef.value && !authKeysEditor) {
      await initAuthKeysEditor();
    }
    
    // 获取文件内容
    await fetchAuthorizedKeysContent();
  };

  // 组件挂载时获取数据并初始化编辑器
  onMounted(async () => {
    await fetchSSHInfo();
    // 添加一个微任务延迟，确保DOM已完全渲染
    await new Promise(resolve => setTimeout(resolve, 0));
    // 组件挂载后立即初始化编辑器，不再等待标签页切换
    if (monacoEditorRef.value && !monacoEditor) {
      initMonacoEditor();
    }
  });

// 初始化authorized_keys的Monaco编辑器
const initAuthKeysEditor = async () => {
  if (!authKeysEditorRef.value || authKeysEditor) return;
  
  try {
    // 动态导入monaco-editor
    const monaco = await import('monaco-editor');
    
    // 创建编辑器实例
    authKeysEditor = monaco.editor.create(authKeysEditorRef.value, {
      value: authKeysContent.value,
      language: 'plaintext',
      theme: 'vs-dark',
      automaticLayout: true,
      minimap: { enabled: true },
      scrollBeyondLastLine: false,
      fontSize: 14,
      tabSize: 2
    });
  } catch (error) {
    console.error('Failed to load Monaco Editor:', error);
    Message.error(`${t.value('load')} Monaco Editor ${t.value('failed')}`);
  }
};

// 组件卸载时销毁编辑器和清理资源
onBeforeUnmount(() => {
  // 销毁编辑器实例
  if (monacoEditor) {
    monacoEditor.dispose();
    monacoEditor = null;
  }
  
  // 销毁authorized_keys编辑器实例
  if (authKeysEditor) {
    authKeysEditor.dispose();
    authKeysEditor = null;
  }
  
  // 清理引用和状态
  configFileContent.value = '';
  configFileLoading.value = false;
  savingConfig.value = false;
  authKeysContent.value = '';
  authKeysPath.value = '';
  loadingAuthKeys.value = false;
  savingAuthKeys.value = false;
});
</script>

<style scoped>
.sec-container {
  padding: 20px;
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

.ssh-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 配置文件编辑器样式 */
.config-file-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 600px;
}

.config-actions {
  margin-bottom: 16px;
  display: flex;
  gap: 12px;
}

.monaco-editor-container {
  flex: 1;
  min-height: 500px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  overflow: hidden;
}


/* authorized_keys抽屉样式 */
.auth-keys-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.auth-keys-actions {
  margin-bottom: 16px;
  display: flex;
  gap: 8px;
}

.monaco-editor-container {
  flex: 1;
  min-height: 400px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
}

.ssh-settings {
  padding: 20px;
}

.ssh-form {
  max-width: 600px;
}

.switch-container {
  display: flex;
  align-items: center;
}

.additional-actions {
  margin-bottom: 20px;
  display: flex;
  gap: 12px;
}

.port-input-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.port-input-container .ant-input {
  width: 150px;
  gap: 10px;
}

.switch-label {
  color: #666;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}

/* 根据需要调整其他样式 */
</style>