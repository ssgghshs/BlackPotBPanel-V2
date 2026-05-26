<template>
  <!-- 右键菜单 -->
  <div 
    v-if="visible" 
    class="context-menu"
    ref="menuRef"
    :style="{ left: calculatedPosition.left + 'px', top: calculatedPosition.top + 'px' }"
    @click.stop
  >
    <div class="context-menu-item" @click="handleDetails">
      <icon-info-circle />
      {{ t('details') }}
    </div>
    <div class="context-menu-item" @click="handleDownload" v-if="record && !record.is_directory">
      <icon-download />
      {{ t('download') }}
    </div>
    <div class="context-menu-item" @click="handleOpen" v-if="record && !record.is_directory && canOpenFile(record.filename)">
      <icon-edit />
      {{ t('open') }}
    </div>
    <div class="context-menu-item" @click="handleOpenImage" v-if="record && !record.is_directory && isImageFile(record.filename)">
      <icon-image />
      {{ t('openImage') }}
    </div>
    <div class="context-menu-item" @click="handleRename">
      <icon-edit />
      {{ t('rename') }}
    </div>
    <div class="context-menu-item" @click="handleMove">
      <icon-edit />
      {{ t('move') }}
    </div>
    <div class="context-menu-item" @click="handleCopy">
      <icon-copy />
      {{ t('copy') }}
    </div>
    <div class="context-menu-item" @click="handleCompress">
      <icon-edit />
      {{ t('compress') }}
    </div>
    <div class="context-menu-item" @click="handleDecompress" v-if="record && !record.is_directory && isCompressedFile(record.filename)">
      <icon-edit />
      {{ t('decompress') }}
    </div>
    <div class="context-menu-item" @click="handlePermissions">
      <icon-safe />
      {{ t('permissions') }}
    </div>
    <div class="context-menu-item" @click="handleDelete">
      <icon-delete />
      {{ t('delete') }}
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
import { ref, watch, nextTick } from 'vue';
import { 
  IconInfoCircle,
  IconDownload,
  IconEdit,
  IconImage,
  IconSafe,
  IconCopy,
  IconDelete
} from '@arco-design/web-vue/es/icon';
import { t } from '../../utils/locale';
import { isImageFile, isCompressedFile, canOpenFile } from '../../utils/file/fileIconMapper';

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
  record: {
    type: Object,
    default: null
  },
  tabKey: {
    type: String,
    default: ''
  }
});

const emit = defineEmits([
  'close',
  'details',
  'download',
  'open',
  'open-image',
  'rename',
  'move',
  'copy',
  'compress',
  'decompress',
  'permissions',
  'delete'
]);

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

const handleClose = () => {
  emit('close');
};

const handleDetails = () => {
  emit('details');
  handleClose();
};

const handleDownload = () => {
  emit('download');
  handleClose();
};

const handleOpen = () => {
  emit('open');
  handleClose();
};

const handleOpenImage = () => {
  emit('open-image');
  handleClose();
};

const handleRename = () => {
  emit('rename');
  handleClose();
};

const handleMove = () => {
  emit('move');
  handleClose();
};

const handleCopy = () => {
  emit('copy');
  handleClose();
};

const handleCompress = () => {
  emit('compress');
  handleClose();
};

const handleDecompress = () => {
  emit('decompress');
  handleClose();
};

const handlePermissions = () => {
  emit('permissions');
  handleClose();
};

const handleDelete = () => {
  emit('delete');
  handleClose();
};
</script>

<style scoped>
/* 右键菜单样式 */
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

.context-menu-item:hover {
  background-color: var(--color-fill-2);
}

.context-menu-item:active {
  background-color: var(--color-fill-3);
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