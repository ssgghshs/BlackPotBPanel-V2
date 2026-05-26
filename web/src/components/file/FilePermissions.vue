<template>
  <!-- 权限修改弹窗 -->
  <a-modal 
    v-model:visible="modalVisible" 
    :title="t('changePermissions')"
    @ok="handleChangePermissions"
    width="600px"
  >
    <a-form :model="formData" layout="vertical">
      <!-- 权限复选框区域 -->
      <div class="permissions-checkbox-container">
        <!-- 所有者 -->
        <div class="permission-group">
          <div class="permission-group-title">{{ t('owner') }}</div>
          <div class="permission-checkboxes">
            <a-checkbox v-model="formData.ownerRead" @change="updatePermissionsFromCheckboxes">
              {{ t('read')}}
            </a-checkbox>
            <a-checkbox v-model="formData.ownerWrite" @change="updatePermissionsFromCheckboxes">
              {{ t('write')}}
            </a-checkbox>
            <a-checkbox v-model="formData.ownerExecute" @change="updatePermissionsFromCheckboxes">
              {{ t('execute')}}
            </a-checkbox>
          </div>
        </div>

        <!-- 用户组 -->
        <div class="permission-group">
          <div class="permission-group-title">{{ t('group') }}</div>
          <div class="permission-checkboxes">
            <a-checkbox v-model="formData.groupRead" @change="updatePermissionsFromCheckboxes">
              {{ t('read')}}
            </a-checkbox>
            <a-checkbox v-model="formData.groupWrite" @change="updatePermissionsFromCheckboxes">
              {{ t('write')}}
            </a-checkbox>
            <a-checkbox v-model="formData.groupExecute" @change="updatePermissionsFromCheckboxes">
              {{ t('execute')}}
            </a-checkbox>
          </div>
        </div>

        <!-- 公共 -->
        <div class="permission-group">
          <div class="permission-group-title">{{ t('public')}}</div>
          <div class="permission-checkboxes">
            <a-checkbox v-model="formData.publicRead" @change="updatePermissionsFromCheckboxes">
              {{ t('read')}}
            </a-checkbox>
            <a-checkbox v-model="formData.publicWrite" @change="updatePermissionsFromCheckboxes">
              {{ t('write')}}
            </a-checkbox>
            <a-checkbox v-model="formData.publicExecute" @change="updatePermissionsFromCheckboxes">
              {{ t('execute')}}
            </a-checkbox>
          </div>
        </div>
      </div>

      <!-- 三个输入框一排布局 -->
      <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-top: 5px;">
        <!-- 权限数字输入框 -->
        <div style="flex: 1; min-width: 140px;">
          <a-form-item 
            :label="t('permissions')" 
            :colon="false" 
            :label-col="{ style: { fontSize: '14px', marginBottom: '4px' } }"
            :wrapper-col="{ style: { paddingBottom: 0 } }"
          >
            <a-input 
              v-model="formData.permissions" 
              :placeholder="t('enterPermissions')"
              maxlength="3"
              @input="updateCheckboxesFromPermissions"
              style="width: 100%;"
              size="small"
            />
          </a-form-item>
          <div style="font-size: 11px; color: #86909c; margin-top: -10px; margin-bottom: 4px; line-height: 1.3;">
            {{ t('permissionsHint')}}
          </div>
        </div>

        <!-- 用户输入框 -->
        <div style="flex: 1; min-width: 140px;">
          <a-form-item 
            :label="t('user')" 
            :colon="false" 
            :label-col="{ style: { fontSize: '14px', marginBottom: '4px' } }"
            :wrapper-col="{ style: { paddingBottom: 0 } }"
          >
            <a-input 
              v-model="formData.user" 
              :placeholder="t('enterUser')"
              style="width: 100%;"
              size="small"
            />
          </a-form-item>
          <div style="font-size: 11px; color: #86909c; margin-top: -10px; margin-bottom: 4px; line-height: 1.3;">
            {{ t('userHint')}}
          </div>
        </div>

        <!-- 用户组输入框 -->
        <div style="flex: 1; min-width: 140px;">
          <a-form-item 
            :label="t('group')" 
            :colon="false" 
            :label-col="{ style: { fontSize: '14px', marginBottom: '4px' } }"
            :wrapper-col="{ style: { paddingBottom: 0 } }"
          >
            <a-input 
              v-model="formData.group" 
              :placeholder="t('enterGroup')"
              style="width: 100%;"
              size="small"
            />
          </a-form-item>
          <div style="font-size: 11px; color: #86909c; margin-top: -10px; margin-bottom: 4px; line-height: 1.3;">
            {{ t('groupHint')}}
          </div>
        </div>
      </div>

      <!-- 应用到子目录复选框 -->
      <a-form-item style="margin-top: 10px;">
        <a-checkbox v-model="formData.recursive">
          {{ t('applyToSubdirectories')}}
        </a-checkbox>
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup>
import { reactive, watch, computed } from 'vue';
import { t } from '../../utils/locale';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  record: {
    type: Object,
    default: null
  },
  permissions: {
    type: String,
    default: '755'
  },
  user: {
    type: String,
    default: ''
  },
  group: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['update:visible', 'submit']);

// 使用 computed 属性来处理 v-model
const modalVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
});

const formData = reactive({
  permissions: '755',
  user: '',
  group: '',
  recursive: false,
  // 所有者权限
  ownerRead: true,
  ownerWrite: true,
  ownerExecute: true,
  // 用户组权限
  groupRead: true,
  groupWrite: false,
  groupExecute: true,
  // 公共权限
  publicRead: true,
  publicWrite: false,
  publicExecute: true
});

// 监听 props 变化，更新表单数据
watch(() => props.visible, (newVal) => {
  if (newVal) {
    formData.permissions = props.permissions || '755';
    formData.user = props.user || '';
    formData.group = props.group || '';
    updateCheckboxesFromPermissions();
  }
});

// 从权限字符串更新复选框状态
const updateCheckboxesFromPermissions = () => {
  const perms = formData.permissions || '755';
  if (!/^[0-7]{3}$/.test(perms)) {
    return;
  }
  
  const owner = parseInt(perms[0]);
  const group = parseInt(perms[1]);
  const pub = parseInt(perms[2]);
  
  // 所有者权限
  formData.ownerRead = (owner & 4) !== 0;
  formData.ownerWrite = (owner & 2) !== 0;
  formData.ownerExecute = (owner & 1) !== 0;
  
  // 用户组权限
  formData.groupRead = (group & 4) !== 0;
  formData.groupWrite = (group & 2) !== 0;
  formData.groupExecute = (group & 1) !== 0;
  
  // 公共权限
  formData.publicRead = (pub & 4) !== 0;
  formData.publicWrite = (pub & 2) !== 0;
  formData.publicExecute = (pub & 1) !== 0;
};

// 从复选框状态更新权限字符串
const updatePermissionsFromCheckboxes = () => {
  const owner = 
    (formData.ownerRead ? 4 : 0) +
    (formData.ownerWrite ? 2 : 0) +
    (formData.ownerExecute ? 1 : 0);
  
  const group = 
    (formData.groupRead ? 4 : 0) +
    (formData.groupWrite ? 2 : 0) +
    (formData.groupExecute ? 1 : 0);
  
  const pub = 
    (formData.publicRead ? 4 : 0) +
    (formData.publicWrite ? 2 : 0) +
    (formData.publicExecute ? 1 : 0);
  
  formData.permissions = `${owner}${group}${pub}`;
};

const handleChangePermissions = () => {
  emit('submit', {
    record: props.record,
    permissions: formData.permissions,
    user: formData.user,
    group: formData.group,
    recursive: formData.recursive
  });
};
</script>

<style scoped>
/* 权限修改弹窗样式 */
.permissions-checkbox-container {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.permission-group {
  flex: 1;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 16px;
  background: var(--color-fill-1);
}

.permission-group-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 12px;
  color: var(--color-text-1);
  text-align: center;
}

.permission-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.permission-checkboxes .arco-checkbox {
  margin: 0;
}

/* 响应式优化 */
@media (max-width: 768px) {
  .permissions-checkbox-container {
    flex-direction: column;
    gap: 12px;
  }
  
  .permission-group {
    padding: 12px;
  }
}
</style>
