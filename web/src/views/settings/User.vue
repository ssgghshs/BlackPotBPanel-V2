<template>
  <div v-if="isAdmin">
    <a-card class="settings-container">
      <template #title>
        <div class="card-header">
          <span class="title">{{ t('user') }}</span>
          <!-- 将添加用户按钮移到标题行 -->
          <div class="header-actions">
            <a-button type="outline" @click="showAddUserDrawer">{{ t('add') }}</a-button>
          </div>
        </div>
      </template>

      <!-- 内容区域 -->
      <!-- 移除了原来的toolbar div -->
      
      <a-table 
        :columns="columns" 
        :data="userData" 
        :loading="loading" 
        :pagination="pagination" 
        @page-change="handlePageChange"
        :scroll="{ x: 1200, y: 400 }"
        :scrollbar="true"
      >
        <template #is_active="{ record }">
          <a-tag :color="record.is_active === 1 ? 'green' : 'red'">
            {{ record.is_active === 1 ? t('active') : t('inactive') }}
          </a-tag>
        </template>
        <template #created_at="{ record }">
          {{ formatDate(record.created_at) }}
        </template>
        <template #actions="{ record }">
          <a-link type="text" size="small" @click="showEditUserDrawer(record)">{{ t('edit') }}</a-link>
          <a-link type="text" size="small" @click="confirmDeleteUser(record)">{{ t('delete') }}</a-link>
        </template>
      </a-table>
    </a-card>
  </div>

  <a-card class="profile-container">
    <template #title>
      <div class="card-header">
        <span class="title">{{ t('profile') }}</span>
        <div class="header-actions">
          <a-button type="outline" @click="handleSaveProfile">{{ t('save') }}</a-button>
        </div>
      </div>
    </template>

    <!--  内容区域  -->
    <div class="content-area">
      <a-spin :loading="profileLoading">
        <a-form :model="profileFormState" layout="horizontal">
          <a-form-item :label="t('username') + ':'" class="form-item">
            <a-input v-model="profileFormState.username" />
          </a-form-item>
          <a-form-item :label="t('email') + ':'" class="form-item">
            <a-input v-model="profileFormState.email" />
          </a-form-item>
          <a-form-item :label="t('password') + ':'" class="form-item">
            <a-input-password v-model="profileFormState.password" :placeholder="t('password')" />
          </a-form-item>
          <a-form-item :label="t('confirmPassword') + ':'" class="form-item" v-if="profileFormState.password">
            <a-input-password v-model="profileFormState.confirmPassword" :placeholder="t('confirmPassword')" />
          </a-form-item>
        </a-form>
      </a-spin>
    </div>
  </a-card>
  
  <!-- 添加用户抽屉 -->
  <a-drawer 
    :width="isMobile ? '90%' : 500" 
    :visible="addUserVisible" 
    @ok="handleAddUser" 
    @cancel="handleCancelAddUser" 
    unmountOnClose
  >
    <template #title>
      {{ t('add') }}
    </template>
    <a-form :model="addUserForm" :rules="addUserRules" ref="addUserFormRef" layout="vertical">
      <a-form-item field="username" :label="t('username')">
        <a-input v-model="addUserForm.username" :placeholder="t('username')" />
      </a-form-item>
      
      <a-form-item field="email" :label="t('email')">
        <a-input v-model="addUserForm.email" :placeholder="t('email')" />
      </a-form-item>
      
      <a-form-item field="password" :label="t('password')">
        <a-input-password v-model="addUserForm.password" :placeholder="t('password')" />
      </a-form-item>
      
      <a-form-item field="confirmPassword" :label="t('confirmPassword')">
        <a-input-password v-model="addUserForm.confirmPassword" :placeholder="t('confirmPassword')" />
      </a-form-item>
      
      <a-form-item field="role" :label="t('role')">
        <a-select v-model="addUserForm.role" :placeholder="t('selectRole')">
          <a-option value="admin">{{ t('admin') }}</a-option>
          <a-option value="auditor">{{ t('auditor') }}</a-option>
          <a-option value="operator">{{ t('operator') }}</a-option>
        </a-select>
      </a-form-item>
    </a-form>
  </a-drawer>
  
  <!-- 编辑用户抽屉 -->
  <a-drawer 
    :width="isMobile ? '90%' : 500" 
    :visible="editUserVisible" 
    @ok="handleEditUser" 
    @cancel="handleCancelEditUser" 
    unmountOnClose
  >
    <template #title>
      {{ t('edit') }}
    </template>
    <a-form :model="editUserForm" :rules="editUserRules" ref="editUserFormRef" layout="vertical">
      <a-form-item field="username" :label="t('username')">
        <a-input v-model="editUserForm.username" :placeholder="t('username')" disabled />
      </a-form-item>
      
      <a-form-item field="email" :label="t('email')">
        <a-input v-model="editUserForm.email" :placeholder="t('email')" />
      </a-form-item>
      
      <a-form-item field="password" :label="t('password')">
        <a-input-password v-model="editUserForm.password" :placeholder="t('password')" />
      </a-form-item>
      
      <a-form-item field="role" :label="t('role')" :disabled="isRoleEditDisabled">
        <a-select v-model="editUserForm.role" :placeholder="t('selectRole')" :disabled="isRoleEditDisabled">
          <a-option value="admin">{{ t('admin') }}</a-option>
          <a-option value="auditor">{{ t('auditor') }}</a-option>
          <a-option value="operator">{{ t('operator') }}</a-option>
        </a-select>
        <div v-if="isRoleEditDisabled" class="role-disabled-hint"></div>
      </a-form-item>
    </a-form>
  </a-drawer>
  

  
  <!-- 删除确认对话框 -->
  <a-modal :visible="deleteModalVisible" @ok="handleDeleteUser" @cancel="cancelDeleteUser" :ok-text="t('confirm')" :cancel-text="t('cancel')">
    <template #title>
      {{ t('delete') }}
    </template>
    <div>
      <p>{{ t('confirmDeleteUser') }} {{ deleteUserTarget.username }}?</p>
    </div>
  </a-modal>
</template>

<script setup>
import { reactive, ref, onMounted, computed, onMounted as onMountedVue, onUnmounted } from 'vue';
import { t } from '../../utils/locale';
import { getUserList, createUser, updateUser, deleteUser, getCurrentUser, updateCurrentUser } from '../../api/user';
import { Message, Modal } from '@arco-design/web-vue';
import { useRouter } from 'vue-router';
// 导入用户状态
import { currentUser, isAdmin } from '../../stores/user';

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

const router = useRouter();

const formState = reactive({
  closePanel: false,
  theme: '',
  panelName: ''
});

// 表格相关数据
const userData = ref([]);
const loading = ref(false);
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50]
});

// 个人信息相关数据
const profileData = ref([]);
const profileLoading = ref(false);
const profileFormState = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
});

// 添加用户抽屉相关
const addUserVisible = ref(false);
const addUserFormRef = ref();
const addUserForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  role: 'operator'
});

// 编辑用户抽屉相关
const editUserVisible = ref(false);
const editUserFormRef = ref();
const editUserForm = reactive({
  id: 0,
  username: '',
  email: '',
  password: '',
  role: 'operator',
  is_admin: false  // 添加这个属性来标记是否是管理员账户
});

// 删除用户相关
const deleteModalVisible = ref(false);
const deleteUserTarget = reactive({
  id: 0,
  username: ''
});

// 国际化文本计算属性
const idText = computed(() => t.value('id'));
const usernameText = computed(() => t.value('username'));
const emailText = computed(() => t.value('email'));
const roleText = computed(() => t.value('role'));
const statusText = computed(() => t.value('status'));
const createdAtText = computed(() => t.value('createTime'));
const actionsText = computed(() => t.value('actions'));
const activeText = computed(() => t.value('active'));
const inactiveText = computed(() => t.value('inactive'));
const editText = computed(() => t.value('edit'));
const deleteText = computed(() => t.value('delete'));
const fetchUserListFailedText = computed(() => t.value('createUserFailed'));
const enter_usernameText = computed(() => t.value('username'));
const enter_emailText = computed(() => t.value('email'));
const enter_passwordText = computed(() => t.value('password'));
const enter_confirm_passwordText = computed(() => t.value('confirmPassword'));

// 计算属性：判断是否禁用角色编辑
const isRoleEditDisabled = computed(() => {
  // 如果用户名和角色都是admin，则禁用角色编辑
  return editUserForm.username === 'admin' && editUserForm.role === 'admin';
});

// 表格列定义
const columns = computed(() => [
  {
    title: idText.value,
    dataIndex: 'id',
    width: 80
  },
  {
    title: usernameText.value,
    dataIndex: 'username',
  },
  {
    title: emailText.value,
    dataIndex: 'email',
  },
  {
    title: roleText.value,
    dataIndex: 'role',
    width: 120
  },
  {
    title: statusText.value,
    dataIndex: 'is_active',
    slotName: 'is_active',
    width: 120
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

// 添加用户表单验证规则
const addUserRules = computed(() => ({
  username: [
    { required: true, message: enter_usernameText.value }
  ],
  email: [
    { required: true, message: enter_emailText.value },
    { type: 'email', message: t.value('emailFormatError') }
  ],
  password: [
    { required: true, message: enter_passwordText.value },
    { minLength: 6, message: t.value('passwordMinLength') }
  ],
  confirmPassword: [
    { required: true, message: enter_confirm_passwordText.value },
    { 
      validator: (value, cb) => {
        if (addUserForm.password && value !== addUserForm.password) {
          cb(t.value('passwordNotMatch'));
        } else {
          cb();
        }
      }
    }
  ]
}));

// 编辑用户表单验证规则
const editUserRules = computed(() => ({
  email: [
    { required: true, message: enter_emailText.value },
    { type: 'email', message: t.value('emailFormatError') }
  ],
  password: [
    { minLength: 6, message: t.value('passwordMinLength') }
  ]
}));

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleString();
};

// 获取当前用户信息
const fetchCurrentUser = async () => {
  try {
    profileLoading.value = true;
    const response = await getCurrentUser();
    
    // 保存当前用户信息到store
    currentUser.value = response;
    
    // 填充表单数据
    profileFormState.username = response.username;
    profileFormState.email = response.email;
    profileFormState.status = response.is_active === 1 ? t.value('active') : t.value('inactive');
    profileFormState.createTime = formatDate(response.created_at);
    
    // 调试信息
    console.log('获取到的用户信息:', response);
    console.log('Store中的isAdmin:', isAdmin.value);
    console.log('Store中的currentUser:', currentUser.value);
  } catch (error) {
    console.error('获取当前用户信息失败:', error);
    Message.error(t.value('fetchUserListFailed'));
  } finally {
    profileLoading.value = false;
  }
};

// 获取用户列表
const fetchUserList = async (page = 1) => {
  try {
    // 检查当前用户是否为admin（使用从store导入的isAdmin状态）
    if (!isAdmin.value) {
      // 非admin用户无权限访问用户列表
      userData.value = [];
      pagination.total = 0;
      return;
    }
    
    loading.value = true;
    const response = await getUserList({
      page: page,
      size: pagination.pageSize
    });
    
    console.log('API响应数据:', response); // 调试信息
    
    // 根据实际API响应结构调整
    if (response && Array.isArray(response)) {
      // 如果响应直接是数组
      userData.value = response;
      pagination.total = response.length;
    } else if (response && response.items && Array.isArray(response.items)) {
      // 如果响应包含items字段
      userData.value = response.items;
      pagination.total = response.total || response.items.length;
    } else if (response && response.data && Array.isArray(response.data)) {
      // 如果响应包含data字段且为数组
      userData.value = response.data;
      pagination.total = response.total || response.data.length;
    } else if (response && response.data && response.data.items && Array.isArray(response.data.items)) {
      // 如果响应包含data.items字段
      userData.value = response.data.items;
      pagination.total = response.data.total || response.data.items.length;
    } else {
      // 如果以上都不匹配，使用空数组
      userData.value = [];
      pagination.total = 0;
    }
    
    console.log('处理后的用户数据:', userData.value); // 调试信息
  } catch (error) {
    console.error('获取用户列表失败:', error);
    Message.error(fetchUserListFailedText.value);
    userData.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

// 处理分页变化
const handlePageChange = (page) => {
  pagination.current = page;
  fetchUserList(page);
};

// 显示编辑用户抽屉
const showEditUserDrawer = (record) => {
  // 填充表单数据
  editUserForm.id = record.id;
  editUserForm.username = record.username;
  editUserForm.email = record.email;
  editUserForm.password = '';
  editUserForm.role = record.role || 'operator';
  
  // 不再需要is_admin标志，因为用户名字段现在总是禁用的
  editUserForm.is_admin = false;
  
  editUserVisible.value = true;
};

// 显示删除用户确认对话框
const confirmDeleteUser = (record) => {
  // 检查是否是用户名和角色都为admin的账户
  if (record.username === 'admin' && record.role === 'admin') {
    Message.warning(t.value('adminUserCannotDelete'));
    return;
  }
  
  deleteUserTarget.id = record.id;
  deleteUserTarget.username = record.username;
  deleteModalVisible.value = true;
};

// 处理删除用户
const handleDeleteUser = async () => {
  try {
    await deleteUser(deleteUserTarget.id);
    Message.success(t.value('deleteUserSuccess'));
    deleteModalVisible.value = false;
    
    // 重新获取用户列表
    fetchUserList();
  } catch (error) {
    console.error('删除用户失败:', error);
    Message.error(t.value('deleteUserFailed'));
    deleteModalVisible.value = false;
  }
};

// 取消删除用户
const cancelDeleteUser = () => {
  deleteModalVisible.value = false;
};

// 处理编辑用户
const handleEditUser = async () => {
  try {
    // 先进行表单验证
    const errors = await editUserFormRef.value?.validate().catch(error => {
      // 表单验证失败，直接返回，不执行编辑用户逻辑
      console.log('表单验证失败:', error);
      return false;
    });
    
    // 如果验证失败或者返回了错误，则不继续执行编辑用户逻辑
    if (errors === false || (errors && Object.keys(errors).length > 0)) {
      return;
    }
    
    // 准备要发送的数据（不包含用户名，因为用户名字段已禁用）
    const updateData = {
      email: editUserForm.email,
      role: editUserForm.role
    };
    
    // 只有当密码不为空时才发送密码字段
    if (editUserForm.password) {
      updateData.password = editUserForm.password;
    }
    
    // 调用API更新用户
    const response = await updateUser(editUserForm.id, updateData);
    
    Message.success(t.value('editUserSuccess'));
    editUserVisible.value = false;
    
    // 重新获取用户列表
    fetchUserList();
    
    // 如果编辑的是当前用户，刷新个人信息
    if (editUserForm.id === profileData.value.find(item => item.label === t.value('id'))?.value) {
      fetchCurrentUser();
    }
  } catch (error) {
    console.error('编辑用户失败:', error);
    Message.error(t.value('editUserFailed'));
  }
};

// 取消编辑用户
const handleCancelEditUser = () => {
  editUserVisible.value = false;
  
  // 重置表单
  editUserForm.id = 0;
  editUserForm.username = '';
  editUserForm.email = '';
  editUserForm.password = '';
  editUserForm.role = 'operator';
  
  // 清除表单验证状态
  editUserFormRef.value?.resetFields();
};

// 显示添加用户抽屉
const showAddUserDrawer = () => {
  addUserVisible.value = true;
};

// 处理保存个人信息
const handleSaveProfile = async () => {
  try {
    // 如果输入了密码，需要验证密码确认
    if (profileFormState.password && profileFormState.password !== profileFormState.confirmPassword) {
      Message.error(t.value('passwordNotMatch'));
      return;
    }
    
    // 检查是否尝试修改用户名为admin且角色为admin的用户的用户名
    if (currentUser.value?.username === 'admin' && currentUser.value?.role === 'admin' && profileFormState.username !== 'admin') {
      Message.error(t.value('adminUsernameCannotChange'));
      return;
    }
    
    // 保存原始用户名用于比较
    const originalUsername = currentUser.value?.username;
    
    // 准备要发送的数据（如果密码为空则不发送密码字段）
    const updateData = {
      username: profileFormState.username,
      email: profileFormState.email
    };
    
    // 只有当密码不为空时才发送密码字段
    if (profileFormState.password) {
      updateData.password = profileFormState.password;
    }
    
    // 调用API更新当前用户信息
    const response = await updateCurrentUser(updateData);
    
    // 检查是否修改了密码
    if (profileFormState.password) {
      // 如果修改了密码，则需要重新登录
      Message.success(t.value('editProfileSuccessWithPassword'));
      // 延迟清除token并跳转，确保消息能显示
      setTimeout(() => {
        // 清除本地存储的token
        localStorage.removeItem('access_token');
        // 跳转到登录页面
        router.push('/login');
      }, 1500);
    } else {
      // 检查用户名是否被修改
      if (originalUsername && originalUsername !== profileFormState.username) {
        // 用户名被修改
        Message.success(t.value('editUsernameSuccess'));
      } else {
        // 其他信息被修改
        Message.success(t.value('editProfileSuccess'));
      }
      // 清除密码字段
      profileFormState.password = '';
      profileFormState.confirmPassword = '';
      // 重新获取当前用户信息
      fetchCurrentUser();
    }
  } catch (error) {
    console.error('保存个人信息失败:', error);
    // 显示更详细的错误信息
    const errorMessage = error.response?.data?.detail || error.message || t.value('editProfileFailed');
    Message.error(errorMessage);
  }
};

// 处理添加用户
const handleAddUser = async () => {
  try {
    // 先进行表单验证
    const errors = await addUserFormRef.value?.validate().catch(error => {
      // 表单验证失败，直接返回，不执行添加用户逻辑
      console.log('表单验证失败:', error);
      return false;
    });
    
    // 如果验证失败或者返回了错误，则不继续执行添加用户逻辑
    if (errors === false || (errors && Object.keys(errors).length > 0)) {
      return;
    }
    
    // 检查是否尝试创建用户名为admin的新用户（避免与系统默认admin用户冲突）
    if (addUserForm.username === 'admin') {
      Message.error(t.value('adminUsernameCannotChange'));
      return;
    }
    
    // 再次检查密码确认（双重保险）
    if (addUserForm.password !== addUserForm.confirmPassword) {
      Message.error(t.value('passwordNotMatch'));
      return;
    }
    
    // 调用API创建用户
    const response = await createUser({
      username: addUserForm.username,
      email: addUserForm.email,
      password: addUserForm.password,
      role: addUserForm.role
    });
    
    Message.success(t.value('createUserSuccess'));
    addUserVisible.value = false;
    
    // 重置表单
    addUserForm.username = '';
    addUserForm.email = '';
    addUserForm.password = '';
    addUserForm.confirmPassword = '';
    addUserForm.role = 'operator';
    
    // 重新获取用户列表
    fetchUserList();
  } catch (error) {
    console.error('添加用户失败:', error);
    Message.error(t.value('createUserFailed'));
  }
};

// 取消添加用户
const handleCancelAddUser = () => {
  addUserVisible.value = false;
  
  // 重置表单
  addUserForm.username = '';
  addUserForm.email = '';
  addUserForm.password = '';
  addUserForm.confirmPassword = '';
  addUserForm.role = 'operator';
  
  // 清除表单验证状态
  addUserFormRef.value?.resetFields();
};


// 保存设置
const saveSettings = () => {
  // 在这里处理保存逻辑
};

// 组件挂载时获取用户列表和当前用户信息
onMounted(() => {
  fetchCurrentUser().then(() => {
    fetchUserList();
  });
});
</script>

<style scoped>
.settings-container {
  padding: 20px;
  margin-bottom: 20px; /* 添加底部边距 */
}

.profile-container {
  padding: 20px;
}

.content-area {
  margin-top: 20px;
}

:deep(.arco-form) {
  width: 300px; /* 设置表单宽度为300px */
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between; /* 修改为space-between以在两端对齐 */
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
  margin-left: auto; /* 将按钮推到右侧 */
}

/* 调整表单项样式，使标签和控件在同一行 */
:deep(.form-item .arco-form-item-label) {
  white-space: nowrap;
  padding-right: 10px;
}

.desc {
  margin-top: 4px;
  color: #8c8c8c;
  font-size: 12px;
}

/* 根据需要调整其他样式 */

.role-disabled-hint {
  font-size: 12px;
  color: #86909c;
  margin-top: 4px;
}
</style>

<!-- 使用非scoped样式确保在所有主题下保持一致 -->
<style>
/* 确保卡片容器在所有主题下保持白色背景 */
.profile-container :deep(.arco-card) {
  background: #ffffff !important;
  border: 1px solid #ebebeb !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
}

/* 确保表单标签在所有主题下保持黑色文字 */
.profile-container :deep(.arco-form-item-label) {
  color: #333 !important;
}

/* 确保描述文字在所有主题下保持灰色 */
.desc {
  color: #8c8c8c !important;
}

/* 确保输入框在所有主题下保持白色背景 */
.profile-container :deep(.arco-input-wrapper) {
  background-color: #ffffff !important;
  border-color: #ebebeb !important;
  color: #333 !important;
}

.profile-container :deep(.arco-input-wrapper:hover) {
  background-color: #ffffff !important;
  border-color: #cccccc !important;
}

.profile-container :deep(.arco-input-wrapper:focus) {
  background-color: #ffffff !important;
  border-color: #3c7eff !important;
  box-shadow: 0 0 0 2px rgba(64, 132, 255, 0.2) !important;
}

.profile-container :deep(.arco-input) {
  color: #333 !important;
}

.profile-container :deep(.arco-input::placeholder) {
  color: #999 !important;
}
</style>