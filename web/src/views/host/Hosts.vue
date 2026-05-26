<template>
  <a-card class="ansible-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('hosts') }}</span>
        <!-- 添加主机按钮 -->
        <div class="header-actions">
          <a-button type="outline" @click="showAddHostDrawer">{{ t('createHost') }}</a-button>
        </div>
      </div>
    </template> 

    <a-table 
      :columns="columns" 
      :data="hostData" 
      :loading="loading" 
      :pagination="pagination" 
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
      :scroll="scroll"
    >
      <template #auth_method="{ record }">
        <a-tag :color="record.auth_method === 'password' ? 'blue' : 'green'">
          {{ record.auth_method === 'password' ? t('passwordAuth') : t('keyAuth') }}
        </a-tag>
      </template>
      <template #status="{ record }">
        <a-tag :color="record.status === 'online' ? 'green' : 'red'">
          {{ record.status === 'online' ? t('online') : t('offline') }}
        </a-tag>
        <a-button type="text" size="small" @click="checkHostStatusForRecord(record)">
          <icon-refresh />
        </a-button>
      </template>
      <template #created_at="{ record }">
        {{ formatDate(record.created_at) }}
      </template>
      <template #actions="{ record }">
        <a-button type="text" size="small" @click="showEditHostDrawer(record)">{{ t('edit') }}</a-button>
        <a-dropdown>
          <a-button type="text" size="small">
            {{ t('more') }}
            <icon-down />
          </a-button>
          <template #content>
            <a-doption @click="handleTerminalConnection(record)">
              <CodeOutlined />
              {{ t('connect') }}
            </a-doption>
            <a-doption @click="confirmDeleteHost(record)">
              <icon-delete />
              {{ t('delete') }}
            </a-doption>
          </template>
        </a-dropdown>
      </template>
    </a-table>
  </a-card>

  <!-- 添加主机抽屉 -->
  <a-drawer 
    :width="isMobile ? '90%' : 500" 
    :visible="addHostVisible" 
    :footer="true"
    @cancel="handleCancelAddHost" 
    unmountOnClose
  >
    <template #title>
      {{ t('createHost') }}
    </template>
    <a-form :model="addHostForm" :rules="addHostRules" ref="addHostFormRef" layout="vertical">
      <a-form-item field="comment" :label="t('comment')">
        <a-input v-model="addHostForm.comment" :placeholder="t('comment')" />
      </a-form-item>
      
      <a-form-item field="address" :label="t('ipAddress')">
        <a-input v-model="addHostForm.address" :placeholder="t('ipAddress')" />
      </a-form-item>
      
      <a-form-item field="username" :label="t('username')">
        <a-input v-model="addHostForm.username" :placeholder="t('username')" />
      </a-form-item>
      
      <a-form-item field="port" :label="t('port')">
        <a-input-number v-model="addHostForm.port" :placeholder="t('port')" :min="1" :max="65535" />
      </a-form-item>
      
      <a-form-item field="auth_method" :label="t('authMethod')">
        <a-select v-model="addHostForm.auth_method" :placeholder="t('authMethod')">
          <a-option value="password">{{ t('passwordAuth') }}</a-option>
          <a-option value="key">{{ t('keyAuth') }}</a-option>
        </a-select>
      </a-form-item>
      
      <a-form-item field="password" :label="t('password')" v-if="addHostForm.auth_method === 'password'">
        <a-input-password v-model="addHostForm.password" :placeholder="t('password')" />
      </a-form-item>
      
      <!-- 密钥认证相关字段 -->
      <a-form-item field="private_key" :label="t('privateKey')" v-if="addHostForm.auth_method === 'key'">
        <a-textarea 
          v-model="addHostForm.private_key" 
          :placeholder="t('enterPrivateKey')" 
          :auto-size="{ minRows: 4, maxRows: 10 }"
          class="private-key-textarea"
        />
      </a-form-item>
      
      <!-- 私钥密码字段 -->
      <a-form-item field="private_key_password" :label="t('privateKeyPassword')" v-if="addHostForm.auth_method === 'key'">
        <a-input-password v-model="addHostForm.private_key_password" :placeholder="t('privateKeyPassword')" />
      </a-form-item>
      
      <div class="key-upload-row" v-if="addHostForm.auth_method === 'key'">
        <a-upload
          :custom-request="handlePrivateKeyUpload"
          :show-file-list="false"
          :accept="'.pem,.key'"
        >
          <a-button size="small" type="outline">{{ t('uploadPrivateKey') }}</a-button>
        </a-upload>
      </div>
    </a-form>
    
    <template #footer>
      <a-button @click="handleCancelAddHost">{{ t('cancel') }}</a-button>
      <a-button type="primary" @click="handleAddHost" :loading="addHostLoading">{{ t('save') }}</a-button>
    </template>
  </a-drawer>
  
  <!-- 编辑主机抽屉 -->
  <a-drawer 
    :width="isMobile ? '90%' : 500" 
    :visible="editHostVisible" 
    :footer="true"
    @cancel="handleCancelEditHost" 
    unmountOnClose
  >
    <template #title>
      {{ t('edit') }}
    </template>
    <a-form :model="editHostForm" :rules="editHostRules" ref="editHostFormRef" layout="vertical">
      <a-form-item field="comment" :label="t('comment')">
        <a-input v-model="editHostForm.comment" :placeholder="t('comment')" />
      </a-form-item>
      
      <a-form-item field="address" :label="t('address')">
        <a-input v-model="editHostForm.address" :placeholder="t('address')" />
      </a-form-item>
      
      <a-form-item field="username" :label="t('username')">
        <a-input v-model="editHostForm.username" :placeholder="t('username')" />
      </a-form-item>
      
      <a-form-item field="port" :label="t('port')">
        <a-input-number v-model="editHostForm.port" :placeholder="t('port')" :min="1" :max="65535" />
      </a-form-item>
      
      <a-form-item field="auth_method" :label="t('authMethod')">
        <a-select v-model="editHostForm.auth_method" :placeholder="t('authMethod')">
          <a-option value="password">{{ t('passwordAuth') }}</a-option>
          <a-option value="key">{{ t('keyAuth') }}</a-option>
        </a-select>
      </a-form-item>
      
      <a-form-item field="password" :label="t('password')" v-if="editHostForm.auth_method === 'password'">
        <a-input-password v-model="editHostForm.password" :placeholder="t('password')" />
      </a-form-item>
      
      <!-- 密钥认证相关字段 -->
      <a-form-item field="private_key" :label="t('privateKey')" v-if="editHostForm.auth_method === 'key'">
        <a-textarea 
          v-model="editHostForm.private_key" 
          :placeholder="t('enterPrivateKey')" 
          :auto-size="{ minRows: 4, maxRows: 10 }"
          class="private-key-textarea"
        />
      </a-form-item>
      
      <!-- 私钥密码字段 -->
      <a-form-item field="private_key_password" :label="t('privateKeyPassword')" v-if="editHostForm.auth_method === 'key'">
        <a-input-password v-model="editHostForm.private_key_password" :placeholder="t('privateKeyPassword')" />
      </a-form-item>
      
      <div class="key-upload-row" v-if="editHostForm.auth_method === 'key'">
        <a-upload
          :custom-request="handlePrivateKeyUploadEdit"
          :show-file-list="false"
          :accept="'.pem,.key'"
        >
          <a-button size="small" type="outline">{{ t('uploadPrivateKey') }}</a-button>
        </a-upload>
      </div>
    </a-form>
    
    <template #footer>
      <a-button @click="handleCancelEditHost">{{ t('cancel') }}</a-button>
      <a-button type="primary" @click="handleEditHost" :loading="editHostLoading">{{ t('save') }}</a-button>
      <a-button type="primary" @click="testSSHConnectionForEditedHost" :loading="sshTestLoading">
        {{ t('testSSHConnection') }}
      </a-button>
    </template>
  </a-drawer>
  
  <!-- 删除确认对话框 -->
  <a-modal :visible="deleteModalVisible" @ok="handleDeleteHost" @cancel="cancelDeleteHost" :ok-text="t('confirm')" :cancel-text="t('cancel')">
    <template #title>
      {{ t('delete') }}
    </template>
    <div>
      <p>{{ t('confirmDeleteHost') }} {{ deleteHostTarget.address }}?</p>
    </div>
  </a-modal>
  
  <!-- SSH连接测试结果对话框 -->
  <a-modal :visible="sshTestVisible" @ok="closeSSHTest" @cancel="closeSSHTest" :ok-text="t('confirm')" :cancel-text="t('cancel')">
    <template #title>
      {{ t('sshConnectionTest') }}
    </template>
    <div>
      <a-alert v-if="sshTestResult.success" type="success" :title="t('sshConnectionSuccess')">
        {{ t('sshConnectionSuccessMessage') }}
      </a-alert>
      <a-alert v-else type="error" :title="t('sshConnectionFailed')">
        {{ sshTestResult.message }}
      </a-alert>
    </div>
  </a-modal>
  
  <!-- 终端连接抽屉 -->
  <TerminalDrawer 
    v-model:visible="terminalDrawerVisible" 
    :host-info="selectedHost"
    @close="handleTerminalClose"
  />
</template>

<script setup>
import { reactive, ref, onMounted, computed, onMounted as onMountedVue, onUnmounted } from 'vue';
import { t } from '../../utils/locale';
import { getHosts, createHost, updateHost, deleteHost, testSSHConnection, checkHostStatus } from '../../api/host';
import { Message } from '@arco-design/web-vue';
import { IconRefresh , IconDown , IconDelete} from '@arco-design/web-vue/es/icon';
import { CodeOutlined } from '@ant-design/icons-vue';
import TerminalDrawer from '../../components/hosts/TerminalDrawer.vue';

// 移动端检测
const isMobile = ref(false);

const checkIsMobile = () => {
  isMobile.value = window.innerWidth <= 768;
};

onMountedVue(() => {
  checkIsMobile();
  window.addEventListener('resize', checkIsMobile);
});

onUnmounted(() => {
  window.removeEventListener('resize', checkIsMobile);
});

// 表格相关数据
const hostData = ref([]);
const loading = ref(false);
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true
});

// 表格滚动配置
const scroll = {
  x: 1300,
  y: 400
};

// 表格列定义
const columns = computed(() => [
  {
    title: idText.value,
    dataIndex: 'id',
    width: 80
  },
  {
    title: commentText.value,
    dataIndex: 'comment',
    width: 150
  },
  {
    title: addressText.value,
    dataIndex: 'address',
    width: 160
  },
  {
    title: usernameText.value,
    dataIndex: 'username',
    width: 140
  },
  {
    title: portText.value,
    dataIndex: 'port',
    width: 100
  },
  {
    title: authMethodText.value,
    dataIndex: 'auth_method',
    slotName: 'auth_method',
    width: 140
  },
  {
    title: statusText.value,
    dataIndex: 'status',
    slotName: 'status',
    width: 140
  },
  {
    title: createdAtText.value,
    dataIndex: 'created_at',
    slotName: 'created_at',
    width: 200
  },
  {
    title: actionsText.value,
    slotName: 'actions',
    width: 150
  }
]);

// 添加主机抽屉相关
const addHostVisible = ref(false);
const addHostFormRef = ref();
const addHostForm = reactive({
  comment: '',
  address: '',
  username: '',
  port: 22,
  password: '',
  private_key: '',
  private_key_password: '', // 添加私钥密码字段
  auth_method: 'password'
});
const addHostLoading = ref(false);
const newlyCreatedHostId = ref(null);

// 编辑主机抽屉相关
const editHostVisible = ref(false);
const editHostFormRef = ref();
const editHostForm = reactive({
  id: 0,
  comment: '',
  address: '',
  username: '',
  port: 22,
  password: '',
  private_key: '',
  private_key_password: '', // 添加私钥密码字段
  auth_method: 'password'
});
const editHostLoading = ref(false);

// 删除主机相关
const deleteModalVisible = ref(false);
const deleteHostTarget = reactive({
  id: 0,
  address: ''
});

// SSH连接测试相关
const sshTestVisible = ref(false);
const sshTestResult = reactive({
  success: false,
  message: ''
});
const sshTestLoading = ref(false);

// 终端抽屉相关
const terminalDrawerVisible = ref(false);
const selectedHost = ref({});

// 国际化文本计算属性
const idText = computed(() => t.value('id'));
const commentText = computed(() => t.value('comment'));
const addressText = computed(() => t.value('ipAddress'));
const usernameText = computed(() => t.value('username'));
const portText = computed(() => t.value('port'));
const authMethodText = computed(() => t.value('authMethod'));
const statusText = computed(() => t.value('status'));
const createdAtText = computed(() => t.value('createdAt'));
const actionsText = computed(() => t.value('actions'));
const onlineText = computed(() => t.value('online'));
const offlineText = computed(() => t.value('offline'));
const enterCommentText = computed(() => t.value('comment'));
const enterAddressText = computed(() => t.value('ipAddress'));
const enterUsernameText = computed(() => t.value('username'));
const enterPortText = computed(() => t.value('port'));
const enterAuthMethodText = computed(() => t.value('authMethod'));
const enterPasswordText = computed(() => t.value('password'));
const moreText = computed(() => t.value('more'));

// 添加主机表单验证规则
const addHostRules = computed(() => ({
  comment: [
    { required: false }
  ],
  address: [
    { required: true, message: enterAddressText.value }
  ],
  username: [
    { required: true, message: enterUsernameText.value }
  ],
  port: [
    { required: true, message: enterPortText.value }
  ],
  auth_method: [
    { required: true, message: enterAuthMethodText.value }
  ],
  password: [
    { required: addHostForm.auth_method === 'password', message: enterPasswordText.value }
  ],
  private_key: [
    { required: addHostForm.auth_method === 'key', message: t.value('enterPrivateKey') }
  ],
  private_key_password: [
    { required: false }
  ]
}));

// 编辑主机表单验证规则
const editHostRules = computed(() => ({
  comment: [
    { required: false }
  ],
  address: [
    { required: true, message: enterAddressText.value }
  ],
  username: [
    { required: true, message: enterUsernameText.value }
  ],
  port: [
    { required: true, message: enterPortText.value }
  ],
  auth_method: [
    { required: true, message: enterAuthMethodText.value }
  ],
  password: [
    { required: editHostForm.auth_method === 'password', message: enterPasswordText.value }
  ],
  private_key: [
    { required: editHostForm.auth_method === 'key', message: t.value('enterPrivateKey') }
  ],
  private_key_password: [
    { required: false }
  ]
}));

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleString();
};

// 获取主机列表
const fetchHostList = async (page = 1) => {
  try {
    loading.value = true;
    const response = await getHosts({
      skip: (page - 1) * pagination.pageSize,
      limit: pagination.pageSize
    });
    
    console.log('API响应数据:', response);
    
    // 根据实际API响应结构调整
    let hosts = [];
    let total = 0;
    
    if (response && Array.isArray(response)) {
      // 如果响应直接是数组
      hosts = response;
      total = response.length;
    } else if (response && response.items && Array.isArray(response.items)) {
      // 如果响应包含items字段
      hosts = response.items;
      total = response.total || response.items.length;
    } else if (response && response.data && Array.isArray(response.data)) {
      // 如果响应包含data字段且为数组
      hosts = response.data;
      total = response.total || response.data.length;
    } else if (response && response.data && response.data.items && Array.isArray(response.data.items)) {
      // 如果响应包含data.items字段
      hosts = response.data.items;
      total = response.data.total || response.data.items.length;
    } else {
      // 如果以上都不匹配，使用空数组
      hosts = [];
      total = 0;
    }
    
    // 为每个主机添加状态字段，默认为unknown
    hostData.value = hosts.map(host => ({
      ...host,
      status: 'unknown'
    }));
    
    pagination.total = total;
    console.log('处理后的主机数据:', hostData.value);
    
    // 自动检测所有主机的状态
    checkAllHostStatus();
  } catch (error) {
    console.error('获取主机列表失败:', error);
    Message.error(t.value('getHostListFailed'));
    hostData.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

// 自动检测所有主机的状态
const checkAllHostStatus = async () => {
  // 遍历所有主机，检测它们的状态
  for (const host of hostData.value) {
    // 使用setTimeout避免同时发起太多请求
    setTimeout(async () => {
      try {
        // 调用API检测主机状态
        const result = await checkHostStatus(host.id);
        
        // 更新主机状态
        if (result.success && result.data) {
          host.status = result.data.is_alive ? 'online' : 'offline';
        } else {
          host.status = 'offline';
        }
      } catch (error) {
        console.error('检测主机状态失败:', error);
        host.status = 'offline';
      }
    }, 100); // 间隔100ms发起请求
  }
};

// 处理分页变化
const handlePageChange = (page) => {
  pagination.current = page;
  fetchHostList(page);
};

// 处理分页大小变化
const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1; // 重置到第一页
  fetchHostList(1);
};

// 显示添加主机抽屉
const showAddHostDrawer = () => {
  addHostVisible.value = true;
  newlyCreatedHostId.value = null; // 重置新创建的主机ID
};

// 处理添加主机
const handleAddHost = async () => {
  try {
    addHostLoading.value = true;
    
    // 先进行表单验证
    const errors = await addHostFormRef.value?.validate().catch(error => {
      console.log('表单验证失败:', error);
      return false;
    });
    
    // 如果验证失败或者返回了错误，则不继续执行添加主机逻辑
    if (errors === false || (errors && Object.keys(errors).length > 0)) {
      addHostLoading.value = false;
      return;
    }
    
    // 准备要发送的数据
    const hostData = {
      comment: addHostForm.comment,
      address: addHostForm.address,
      username: addHostForm.username,
      port: addHostForm.port,
      auth_method: addHostForm.auth_method
    };
    
    // 根据认证方式添加相应字段
    if (addHostForm.auth_method === 'password' && addHostForm.password) {
      hostData.password = addHostForm.password;
    } else if (addHostForm.auth_method === 'key') {
      if (addHostForm.private_key) {
        hostData.private_key = addHostForm.private_key;
      }
      if (addHostForm.private_key_password) {
        hostData.private_key_password = addHostForm.private_key_password;
      }
    }
    
    // 调用API创建主机
    const response = await createHost(hostData);
    
    Message.success(t.value('createHostSuccess'));
    
    // 保存新创建的主机ID，用于后续测试
    newlyCreatedHostId.value = response.id;
    
    // 关闭抽屉
    addHostVisible.value = false;
    
    // 重置表单
    addHostForm.comment = '';
    addHostForm.address = '';
    addHostForm.username = '';
    addHostForm.port = 22;
    addHostForm.password = '';
    addHostForm.auth_method = 'password';
    addHostForm.private_key = ''; // 重置私钥字段
    newlyCreatedHostId.value = null; // 重置新创建的主机ID
    
    // 清除表单验证状态
    addHostFormRef.value?.resetFields();
    
    // 重新获取主机列表
    fetchHostList();
  } catch (error) {
    console.error('添加主机失败:', error);
    Message.error(t.value('createHostFailed'));
  } finally {
    addHostLoading.value = false;
  }
};

// 取消添加主机
const handleCancelAddHost = () => {
  addHostVisible.value = false;
  
  // 重置表单
  addHostForm.comment = '';
  addHostForm.address = '';
  addHostForm.username = '';
  addHostForm.port = 22;
  addHostForm.password = '';
  addHostForm.auth_method = 'password';
  addHostForm.private_key = ''; // 重置私钥字段
  newlyCreatedHostId.value = null; // 重置新创建的主机ID
  
  // 清除表单验证状态
  addHostFormRef.value?.resetFields();
};

// 显示编辑主机抽屉
const showEditHostDrawer = (record) => {
  // 填充表单数据
  editHostForm.id = record.id;
  editHostForm.comment = record.comment || '';
  editHostForm.address = record.address;
  editHostForm.username = record.username;
  editHostForm.port = record.port;
  editHostForm.auth_method = record.auth_method;
  editHostForm.password = '';
  // 从record中获取私钥信息
  editHostForm.private_key = record.private_key;
  editHostForm.private_key_password = '';
  
  editHostVisible.value = true;
};

// 处理编辑主机
const handleEditHost = async () => {
  try {
    editHostLoading.value = true;
    
    // 先进行表单验证
    const errors = await editHostFormRef.value?.validate().catch(error => {
      console.log('表单验证失败:', error);
      return false;
    });
    
    // 如果验证失败或者返回了错误，则不继续执行编辑主机逻辑
    if (errors === false || (errors && Object.keys(errors).length > 0)) {
      editHostLoading.value = false;
      return;
    }
    
    // 准备要发送的数据
    const hostData = {
      comment: editHostForm.comment,
      address: editHostForm.address,
      username: editHostForm.username,
      port: editHostForm.port,
      auth_method: editHostForm.auth_method
    };
    
    // 根据认证方式添加相应字段
    if (editHostForm.auth_method === 'password' && editHostForm.password) {
      hostData.password = editHostForm.password;
    } else if (editHostForm.auth_method === 'key') {
      if (editHostForm.private_key) {
        hostData.private_key = editHostForm.private_key;
      }
      if (editHostForm.private_key_password) {
        hostData.private_key_password = editHostForm.private_key_password;
      }
    }
    
    // 调用API更新主机
    const response = await updateHost(editHostForm.id, hostData);
    
    Message.success(t.value('editHostSuccess'));
    
    // 重新获取主机列表
    fetchHostList();
  } catch (error) {
    console.error('编辑主机失败:', error);
    Message.error(t.value('editHostFailed'));
  } finally {
    editHostLoading.value = false;
  }
};

// 处理私钥文件上传（添加主机）
const handlePrivateKeyUpload = (fileObj) => {
  const file = fileObj.file;
  const reader = new FileReader();
  reader.onload = (e) => {
    addHostForm.private_key = e.target.result;
  };
  reader.readAsText(file);
};

// 处理私钥文件上传（编辑主机）
const handlePrivateKeyUploadEdit = (fileObj) => {
  const file = fileObj.file;
  const reader = new FileReader();
  reader.onload = (e) => {
    editHostForm.private_key = e.target.result;
  };
  reader.readAsText(file);
};

// 取消编辑主机
const handleCancelEditHost = () => {
  editHostVisible.value = false;
  
  // 重置表单
  editHostForm.id = 0;
  editHostForm.comment = '';
  editHostForm.address = '';
  editHostForm.username = '';
  editHostForm.port = 22;
  editHostForm.password = '';
  editHostForm.auth_method = 'password';
  editHostForm.private_key = ''; // 重置私钥字段
  editHostForm.private_key_password = ''; // 重置私钥密码字段
  
  // 清除表单验证状态
  editHostFormRef.value?.resetFields();
};

// 显示删除主机确认对话框
const confirmDeleteHost = (record) => {
  // 检查是否为系统创建的本机配置（127.0.0.1且is_system_created为true），如果是则不允许删除
  if (record.address === '127.0.0.1' && record.is_system_created) {
    Message.error(t.value('cannotDeleteLocalhost'));
    return;
  }
  
  deleteHostTarget.id = record.id;
  deleteHostTarget.address = record.address;
  deleteModalVisible.value = true;
};

// 处理删除主机
const handleDeleteHost = async () => {
  try {
    await deleteHost(deleteHostTarget.id);
    Message.success(t.value('deleteHostSuccess'));
    deleteModalVisible.value = false;
    
    // 重新获取主机列表
    fetchHostList();
  } catch (error) {
    console.error('删除主机失败:', error);
    Message.error(t.value('deleteHostFailed'));
    deleteModalVisible.value = false;
  }
};

// 取消删除主机
const cancelDeleteHost = () => {
  deleteModalVisible.value = false;
};

// 获取SSH配置信息
const handleSSHConnectionTest = async (record) => {
  try {
    // 调用API测试SSH连接
    const result = await testSSHConnection(record.id);
    
    // 显示SSH连接测试结果
    sshTestResult.success = result.success;
    sshTestResult.message = result.message;
    sshTestVisible.value = true;
    
    console.log('SSH连接测试结果:', result);
  } catch (error) {
    console.error('SSH连接测试失败:', error);
    sshTestResult.success = false;
    sshTestResult.message = error.response?.data?.detail || t.value('sshConnectionFailedMessage');
    sshTestVisible.value = true;
  }
};

// 关闭SSH连接测试对话框
const closeSSHTest = () => {
  sshTestVisible.value = false;
};


// 测试编辑主机的SSH连接
const testSSHConnectionForEditedHost = async () => {
  if (!editHostForm.id) {
    Message.error(t.value('noHostToTest'));
    return;
  }
  
  try {
    sshTestLoading.value = true;
    
    // 调用API测试SSH连接
    const result = await testSSHConnection(editHostForm.id);
    
    // 显示SSH连接测试结果
    sshTestResult.success = result.success;
    sshTestResult.message = result.message;
    sshTestVisible.value = true;
    
    console.log('SSH连接测试结果:', result);
  } catch (error) {
    console.error('SSH连接测试失败:', error);
    sshTestResult.success = false;
    sshTestResult.message = error.response?.data?.detail || t.value('sshConnectionFailedMessage');
    sshTestVisible.value = true;
  } finally {
    sshTestLoading.value = false;
  }
};

// 检测主机状态
const checkHostStatusForRecord = async (record) => {
  try {
    // 显示加载状态
    const originalStatus = record.status;
    record.status = 'checking';
    
    // 调用API检测主机状态
    const result = await checkHostStatus(record.id);
    
    // 更新主机状态
    if (result.success && result.data) {
      record.status = result.data.is_alive ? 'online' : 'offline';
      Message.success(t.value('checkHostStatusSuccess'));
    } else {
      record.status = 'offline';
      Message.error(t.value('checkHostStatusFailed'));
    }
  } catch (error) {
    console.error('检测主机状态失败:', error);
    record.status = 'offline';
    Message.error(t.value('checkHostStatusFailed') + ': ' + (error.response?.data?.detail || error.message));
  }
};

// 处理终端连接
const handleTerminalConnection = (record) => {
  selectedHost.value = record;
  terminalDrawerVisible.value = true;
};

// 处理终端关闭
const handleTerminalClose = () => {
  terminalDrawerVisible.value = false;
  selectedHost.value = {};
};

// 组件挂载时获取主机列表
onMounted(() => {
  fetchHostList();
});
</script>

<style scoped>
.ansible-container {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  font-size: 1.3em;
  padding: 20px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.title {
  margin: 0;
  padding: 0;
}

/* 添加按钮容器样式 */
.header-actions {
  margin-left: auto;
}

.desc {
  margin-top: 4px;
  color: #8c8c8c;
  font-size: 12px;
}

/* 密钥上传按钮样式 */
.key-upload-row {
  margin-top: 10px;
  margin-bottom: 20px;
}

/* 私钥输入框样式 */
.private-key-textarea {
  width: 100%;
}

/* 根据需要调整其他样式 */
</style>