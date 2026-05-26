<template>
  <!-- 操作右键菜单 -->
  <div 
    v-if="visible" 
    class="context-menu"
    ref="menuRef"
    :style="{ left: calculatedPosition.left + 'px', top: calculatedPosition.top + 'px' }"
    @click.stop
  >
    <!-- 刷新 -->
    <div class="context-menu-item" @click="handleRefresh">
      <icon-refresh />
      {{ t('refresh') }}
    </div>
    
    <!-- 创建二级菜单 -->
    <div class="context-menu-submenu">
      <div class="context-menu-item" @click.stop="toggleCreateSubmenu">
        <icon-edit />
        {{ t('create') }}
        <icon-down class="submenu-arrow" :style="{ transform: createSubmenuVisible ? 'rotate(180deg)' : 'rotate(0deg)' }" />
      </div>
      <!-- 二级菜单内容 -->
      <div class="context-submenu" v-if="createSubmenuVisible" @click.stop>
        <div class="context-menu-item" @click="handleCreateFolder">
          <icon-folder />
          {{ t('createFolder') }}
        </div>
        <div class="context-menu-item" @click="handleCreateFile">
          <icon-file />
          {{ t('createFile') }}
        </div>
        <div class="context-menu-item" @click="handleCreateLink">
          <icon-link />
          {{ t('createLink') }}
        </div>
      </div>
    </div>
    
    <!-- 远程下载 -->
    <div class="context-menu-item" @click="handleDownloadRemote">
      <icon-download />
      {{ t('downloadRemote') }}
    </div>
    
    <!-- 上传文件 -->
    <div class="context-menu-item" @click="handleUpload">
      <icon-upload />
      {{ t('uploadFile') }}
    </div>
    
    <!-- 终端连接 -->
    <div class="context-menu-item" @click="handleTerminal">
      <CodeOutlined />
      {{ t('terminalConnection') }}
    </div>
  </div>

  <!-- 遮罩层，用于关闭右键菜单 -->
  <div 
    v-if="visible" 
    class="context-menu-overlay"
    @click="handleClose"
    @contextmenu.prevent="handleClose"
  ></div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue';
import { 
  IconRefresh, 
  IconEdit, 
  IconDown, 
  IconDownload, 
  IconUpload, 
  IconFolder,
  IconFile,
  IconLink
} from '@arco-design/web-vue/es/icon';
import { CodeOutlined } from '@ant-design/icons-vue'
import { t } from '../../utils/locale';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  x: {
    type: Number,
    default: 0
  },
  y: {
    type: Number,
    default: 0
  },
  tabKey: {
    type: String,
    default: ''
  }
});

const emit = defineEmits([
  'close',
  'refresh',
  'createFolder',
  'createFile',
  'createLink',
  'downloadRemote',
  'upload',
  'terminal'
]);

// 二级菜单状态
const createSubmenuVisible = ref(false);

// 菜单元素引用
const menuRef = ref(null);

// 计算后的菜单位置
const calculatedPosition = ref({
  left: 0,
  top: 0
});

// 监听可见性变化，重新计算位置
watch(() => props.visible, (newVisible) => {
  if (newVisible) {
    nextTick(() => {
      calculateMenuPosition();
    });
  }
});

// 监听位置变化，重新计算位置
watch([() => props.x, () => props.y], () => {
  if (props.visible) {
    nextTick(() => {
      calculateMenuPosition();
    });
  }
});

// 计算菜单位置，确保在视口内
const calculateMenuPosition = () => {
  if (!menuRef.value) return;
  
  const menu = menuRef.value;
  const menuRect = menu.getBoundingClientRect();
  
  // 获取视口尺寸
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  
  // 初始位置
  let left = props.x;
  let top = props.y;
  
  // 检查右侧是否超出视口
  if (left + menuRect.width > viewportWidth) {
    left = viewportWidth - menuRect.width - 10;
  }
  
  // 检查底部是否超出视口
  if (top + menuRect.height > viewportHeight) {
    top = viewportHeight - menuRect.height - 10;
  }
  
  // 确保菜单不会超出顶部和左侧
  left = Math.max(left, 10);
  top = Math.max(top, 10);
  
  calculatedPosition.value = { left, top };
};

const toggleCreateSubmenu = () => {
  createSubmenuVisible.value = !createSubmenuVisible.value;
  // 二级菜单展开/折叠时重新计算位置
  nextTick(() => {
    calculateMenuPosition();
  });
};

const handleClose = () => {
  createSubmenuVisible.value = false;
  emit('close');
};

const handleRefresh = () => {
  emit('refresh');
  handleClose();
};

const handleCreateFolder = () => {
  emit('createFolder');
  handleClose();
};

const handleCreateFile = () => {
  emit('createFile');
  handleClose();
};

const handleCreateLink = () => {
  emit('createLink');
  handleClose();
};

const handleDownloadRemote = () => {
  emit('downloadRemote');
  handleClose();
};

const handleUpload = () => {
  emit('upload');
  handleClose();
};

const handleTerminal = () => {
  emit('terminal');
  handleClose();
};
</script>

<style scoped>
/* 右键菜单样式，参考 FileRightMenu.vue */
.context-menu {
  position: fixed;
  background: var(--color-bg-popup);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 9999;
  min-width: 120px;
  padding: 4px 0;
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 14px;
  color: var(--color-text-1);
  transition: background-color 0.2s;
}
/* 确保图标和文字对齐 */
.context-menu-item > * {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 二级菜单箭头样式 */
.submenu-arrow {
  margin-left: auto;
  font-size: 12px;
}


.context-menu-item:hover {
  background-color: var(--color-fill-2);
}

.context-menu-item:active {
  background-color: var(--color-fill-3);
}

/* 二级菜单样式 */
.context-menu-submenu {
  position: relative;
}

/* 二级菜单触发项 */
.context-menu-submenu > .context-menu-item {
  justify-content: space-between;
}

.context-submenu {
  position: absolute;
  top: 0;
  left: 100%;
  background: var(--color-bg-popup);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  min-width: 120px;
  padding: 4px 0;
  z-index: 10000;
}

.submenu-arrow {
  transition: transform 0.2s ease;
  font-size: 12px;
}

.context-menu-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9998;
  background: transparent;
}
</style>