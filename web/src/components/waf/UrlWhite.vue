<template>
  <div class="url-white-container">
    <div class="table-container">
      <!-- 正常路由表格 -->
      <div class="section">
        <div class="search-filters">
          <div class="flex-grow"></div>
          <a-button type="outline" size="small" @click="fetchURLWhiteList" :loading="loading" class="refresh-btn">
            {{ t('refresh') }}
          </a-button>
          <a-button type="outline" size="small" @click="handleEdit('normal_routes')">{{ t('edit') }}</a-button>
        </div>
        <h3 class="section-title">{{ t('normalRoutes') }}</h3>
        <a-table 
          :columns="normalRoutesColumns" 
          :data="[{ routes: urlWhiteList.normal_routes }]" 
          :loading="loading"
          :pagination="false"
          :scroll="scroll"
          row-key="id"
        >
          <template #routes="{ record }">
            <div class="route-list">
              <a-tag v-for="(route, index) in record.routes" :key="index" size="small" class="route-tag">
                {{ route }}
              </a-tag>
            </div>
          </template>
        </a-table>
      </div>

      <!-- 静态路径表格 -->
      <div class="section">
        <h3 class="section-title">{{ t('staticPaths') }}</h3>
        <a-table 
          :columns="staticPathsColumns" 
          :data="[{ paths: urlWhiteList.static_paths }]" 
          :loading="loading"
          :pagination="false"
          :scroll="scroll"
          row-key="id"
        >
          <template #paths="{ record }">
            <div class="path-list">
              <a-tag v-for="(path, index) in record.paths" :key="index" size="small" class="path-tag">
                {{ path }}
              </a-tag>
            </div>
          </template>
        </a-table>
      </div>

      <!-- 静态扩展名表格 -->
      <div class="section">
        <h3 class="section-title">{{ t('staticExtensions') }}</h3>
        <a-table 
          :columns="staticExtensionsColumns" 
          :data="[{ extensions: urlWhiteList.static_extensions }]" 
          :loading="loading"
          :pagination="false"
          :scroll="scroll"
          row-key="id"
        >
          <template #extensions="{ record }">
            <div class="extension-list">
              <a-tag v-for="(ext, index) in record.extensions" :key="index" size="small" class="extension-tag">
                {{ ext }}
              </a-tag>
            </div>
          </template>
        </a-table>
      </div>
    </div>

    <!-- 编辑抽屉 -->
    <a-drawer
      v-model:visible="editModalVisible"
      :title="editTitle"
      width="600px"
      @close="handleEditCancel"
      :footer="false"
    >
      <div class="drawer-content">
        <a-form :model="editForm" layout="vertical">
          <a-form-item :label="t('normalRoutes')">
            <a-textarea v-model="editForm.normalRoutesText" :placeholder="t('normalRoutesPlaceholder')" :rows="5" />
          </a-form-item>
          <a-form-item :label="t('staticPaths')">
            <a-textarea v-model="editForm.staticPathsText" :placeholder="t('staticPathsPlaceholder')" :rows="5" />
          </a-form-item>
          <a-form-item :label="t('staticExtensions')">
            <a-textarea v-model="editForm.staticExtensionsText" :placeholder="t('staticExtensionsPlaceholder')" :rows="5" />
          </a-form-item>
          <div class="drawer-footer">
            <a-button @click="handleEditCancel">{{ t('cancel') }}</a-button>
            <a-button type="primary" @click="handleEditSubmit">{{ t('confirm') }}</a-button>
          </div>
        </a-form>
      </div>
    </a-drawer>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue';
import { t } from '../../utils/locale';
import { getURLWhiteList, updateURLWhiteList } from '../../api/waf';
import { Message } from '@arco-design/web-vue';

const loading = ref(false);
const urlWhiteList = reactive({
  enabled: false,
  normal_routes: [],
  static_paths: [],
  static_extensions: []
});

// 编辑相关
const editModalVisible = ref(false);
const editForm = reactive({
  enabled: false,
  normalRoutesText: '',
  staticPathsText: '',
  staticExtensionsText: ''
});

const scroll = {
  x: 800,
  y: 400
};

// 编辑标题
const editTitle = computed(() => t.value('edit'));

// 正常路由表格列
const normalRoutesColumns = [
  {
    title: t.value('route'),
    dataIndex: 'routes',
    slotName: 'routes',
    width: 800
  }
];

// 静态路径表格列
const staticPathsColumns = [
  {
    title: t.value('path'),
    dataIndex: 'paths',
    slotName: 'paths',
    width: 800
  }
];

// 静态扩展名表格列
const staticExtensionsColumns = [
  {
    title: t.value('extension'),
    dataIndex: 'extensions',
    slotName: 'extensions',
    width: 800
  }
];

// 获取URL白名单数据
const fetchURLWhiteList = async () => {
  loading.value = true;
  try {
    const response = await getURLWhiteList();
    if (response) {
      urlWhiteList.enabled = response.enabled || false;
      urlWhiteList.normal_routes = response.normal_routes || [];
      urlWhiteList.static_paths = response.static_paths || [];
      urlWhiteList.static_extensions = response.static_extensions || [];
    }
  } catch (error) {
    console.error('获取URL白名单失败:', error);
    Message.error(t.value('fetchFailed'));
  } finally {
    loading.value = false;
  }
};

// 处理编辑
const handleEdit = (editType) => {
  // 填充表单数据
  editForm.enabled = urlWhiteList.enabled;
  editForm.normalRoutesText = urlWhiteList.normal_routes.join('\n');
  editForm.staticPathsText = urlWhiteList.static_paths.join('\n');
  editForm.staticExtensionsText = urlWhiteList.static_extensions.join('\n');
  
  editModalVisible.value = true;
};

// 处理编辑提交
const handleEditSubmit = async () => {
  try {
    const normal_routes = editForm.normalRoutesText.split('\n').filter(route => route.trim());
    const static_paths = editForm.staticPathsText.split('\n').filter(path => path.trim());
    const static_extensions = editForm.staticExtensionsText.split('\n').filter(ext => ext.trim());
    
    const formData = {
      enabled: editForm.enabled,
      normal_routes,
      static_paths,
      static_extensions
    };
    
    await updateURLWhiteList(formData);
    Message.success(t.value('updateSuccess'));
    
    editModalVisible.value = false;
    await fetchURLWhiteList();
  } catch (error) {
    console.error('更新URL白名单失败:', error);
    Message.error(t.value('updateFailed'));
  }
};

// 处理编辑取消
const handleEditCancel = () => {
  editModalVisible.value = false;
  // 重置表单
  editForm.enabled = false;
  editForm.normalRoutesText = '';
  editForm.staticPathsText = '';
  editForm.staticExtensionsText = '';
};

onMounted(() => {
  fetchURLWhiteList();
});
</script>

<style scoped>
.url-white-container {
  padding: 20px;
}

.table-container {
  padding: 20px;
}

.search-filters {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 15px;
}

.flex-grow {
  flex-grow: 1;
}

.section {
  margin-bottom: 30px;
}

.section-title {
  font-size: 1.1em;
  font-weight: 500;
  margin-bottom: 15px;
  color: var(--primary-color);
}

.route-list,
.path-list,
.extension-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 100px;
  overflow-y: auto;
}

.route-tag,
.path-tag,
.extension-tag {
  margin-bottom: 4px;
}

.drawer-content {
  padding: 20px;
}

.drawer-footer {
  margin-top: 30px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .search-filters {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>