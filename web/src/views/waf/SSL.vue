<template>
  <a-card class="waf-container">
    <template #title>
      <div class="card-header">
        <span class="title">SSL</span>
        <div class="header-actions">
          <a-button type="outline" @click="openCreateDrawer">{{ t('createSSLCert') }}</a-button>
        </div>
      </div>
    </template>

    <!-- SSL证书列表表格 -->
    <a-table 
      :columns="columns" 
      :data="certList" 
      :loading="loading" 
      :pagination="pagination"
      @page-change="handlePageChange"
      @page-size-change="handlePageSizeChange"
      row-key="id"
    >
      <template #domain="{ record }">
        <span>{{ record.domain || '-' }}</span>
      </template>
      <template #issuer="{ record }">
        <span>{{ record.issuer || '-' }}</span>
      </template>
      <template #expiry_date="{ record }">
        <span>{{ formatDate(record.expiry_date) }}</span>
      </template>
      <template #created_at="{ record }">
        <span>{{ formatDate(record.created_at) }}</span>
      </template>
      <template #operation="{ record }">
        <a-button type="text" size="small" @click="handleViewDetail(record)">{{ t('detail') }}</a-button>
        <a-dropdown>
          <a-button type="text" size="small">
            {{ t('more') }}
            <icon-down />
          </a-button>
          <template #content>
            <a-doption key="edit" @click="handleEditCert(record)">
              <icon-edit />
              {{ t('edit') }}
            </a-doption>
            <a-doption key="delete" @click="handleDeleteCert(record)" danger>
              <icon-delete />
              {{ t('delete') }}
            </a-doption>
          </template>
        </a-dropdown>
      </template>
    </a-table>

    <!-- 创建SSL证书抽屉 -->
    <SSLCertCreate 
      v-model:visible="createDrawerVisible"
      @success="handleCreateSuccess"
    />

    <!-- 编辑SSL证书抽屉 -->
    <SSLCertEdit
      v-model:visible="editDrawerVisible"
      :cert-info="selectedCert"
      @success="handleEditSuccess"
    />

    <!-- SSL证书详情抽屉 -->
    <SSLCertDetail
      v-model:visible="detailDrawerVisible"
      :cert-info="selectedCert"
    />

    <!-- 删除SSL证书确认对话框 -->
    <a-modal 
      v-model:visible="deleteModalVisible" 
      :title="t('deleteSSLCertConfirmTitle')" 
      @ok="confirmDeleteCert" 
      @cancel="cancelDeleteCert"
      :ok-text="t('confirm')"
      :cancel-text="t('cancel')"
    >
      <p>{{ t('deleteSSLCertConfirmMessage') }}</p>
    </a-modal>
  </a-card>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue';
import { t } from '../../utils/locale'
import { getSSLCertList, deleteSSLCert } from '../../api/waf'
import { Message } from '@arco-design/web-vue';
import { IconDown, IconEdit, IconDelete } from '@arco-design/web-vue/es/icon';
import SSLCertCreate from '../../components/waf/SSLCertCreate.vue';
import SSLCertDetail from '../../components/waf/SSLCertDetail.vue';
import SSLCertEdit from '../../components/waf/SSLCertEdit.vue';

// 响应式数据
const certList = ref([]);
const loading = ref(false);
const createDrawerVisible = ref(false);
const editDrawerVisible = ref(false);
const detailDrawerVisible = ref(false);
const deleteModalVisible = ref(false);
const selectedCert = ref({});
const certToDelete = ref({});
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showTotal: true,
  showJumper: true,
  pageSizeOptions: [10, 20, 50, 100],
  showPageSize: true
});

// 表格列定义
const columns = computed(() => [
  {
    title: t.value('name'),
    dataIndex: 'name',
    width: 150
  },
  {
    title: t.value('domain'),
    dataIndex: 'domain',
    slotName: 'domain',
    width: 200
  },
  {
    title: t.value('issuer'),
    dataIndex: 'issuer',
    slotName: 'issuer',
    width: 200
  },
  {
    title: t.value('expiryDate'),
    dataIndex: 'expiry_date',
    slotName: 'expiry_date',
    width: 180
  },
  {
    title: t.value('createTime'),
    dataIndex: 'created_at',
    slotName: 'created_at',
    width: 180
  },
  {      
    title: t.value('action'),      
    dataIndex: 'operation',      
    slotName: 'operation',      
    width: 150,      
    fixed: 'right'    }
]);

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleString();
};

// 获取SSL证书列表
const fetchSSLCertList = async (page = 1) => {
  try {
    loading.value = true;
    const response = await getSSLCertList({
      skip: (page - 1) * pagination.pageSize,
      limit: pagination.pageSize
    });
    
    if (response && response.certs && Array.isArray(response.certs)) {
      certList.value = response.certs;
      pagination.total = response.total || response.certs.length;
    } else {
      certList.value = [];
      pagination.total = 0;
    }
  } catch (error) {
    console.error('获取SSL证书列表失败:', error);
    Message.error(t.value('getSSLCertListFailed'));
    certList.value = [];
    pagination.total = 0;
  } finally {
    loading.value = false;
  }
};

// 处理分页变化
const handlePageChange = (page) => {
  pagination.current = page;
  fetchSSLCertList(page);
};

// 处理分页大小变化
const handlePageSizeChange = (pageSize) => {
  pagination.pageSize = pageSize;
  pagination.current = 1;
  fetchSSLCertList(1);
};

// 打开创建SSL证书抽屉
const openCreateDrawer = () => {
  createDrawerVisible.value = true;
};

// 处理创建成功
const handleCreateSuccess = () => {
  fetchSSLCertList();
};

// 查看SSL证书详情
const handleViewDetail = (cert) => {
  selectedCert.value = cert;
  detailDrawerVisible.value = true;
};

// 编辑SSL证书
const handleEditCert = (cert) => {
  selectedCert.value = cert;
  editDrawerVisible.value = true;
};

// 处理编辑成功
const handleEditSuccess = () => {
  fetchSSLCertList(pagination.current);
};

// 显示删除确认对话框
const handleDeleteCert = (cert) => {
  certToDelete.value = cert;
  deleteModalVisible.value = true;
};

// 确认删除SSL证书
const confirmDeleteCert = async () => {
  try {
    loading.value = true;
    await deleteSSLCert(certToDelete.value.id);
    Message.success(t.value('deleteSSLCertSuccess'));
    deleteModalVisible.value = false;
    fetchSSLCertList(pagination.current);
  } catch (error) {
    console.error('删除SSL证书失败:', error);
    Message.error(t.value('deleteSSLCertFailed'));
  } finally {
    loading.value = false;
  }
};

// 取消删除
const cancelDeleteCert = () => {
  deleteModalVisible.value = false;
  certToDelete.value = {};
};

// 组件挂载时获取数据
onMounted(() => {
  fetchSSLCertList();
});
</script>

<style scoped>
.waf-container {
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

.header-actions {
  display: flex;
  gap: 10px;
}

.desc {
  margin-top: 4px;
  color: #8c8c8c;
  font-size: 12px;
}
</style>
