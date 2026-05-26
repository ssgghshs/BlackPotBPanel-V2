<template>
  <a-drawer
    :width="isMobile ? '90%' : 800"
    :visible="visible"
    :footer="false"
    :mask-closable="false"
    @cancel="handleClose"
    unmountOnClose
  >
    <template #title>
      {{ t('terminalConnection') }} - {{ hostInfo.address }}
    </template>
    
    <div class="terminal-container">
      <!-- 固定的终端背景框 -->
      <div ref="terminalRef" class="terminal-element"></div>
      
      <!-- 在终端背景框上显示状态信息 -->
      <div v-if="connectionStatus === 'connecting'" class="terminal-overlay">
        <div class="status-info">
          <a-spin />
          <span>{{ t('connectingToHost') }}...</span>
        </div>
      </div>
      
      <div v-else-if="connectionStatus === 'disconnected'" class="terminal-overlay">
        <div class="status-info">
          <a-alert type="warning" :title="t('connectionClosed')">
            {{ disconnectReason || t('connectionClosedMessage') }}
          </a-alert>
          <div class="action-buttons">
            <a-button type="primary" @click="initConnection">
              {{ t('reconnect') }}
            </a-button>
          </div>
        </div>
      </div>
      
      <div v-else-if="connectionStatus === 'error'" class="terminal-overlay">
        <div class="status-info">
          <a-alert type="error" :title="t('connectionFailed')">
            {{ errorMessage || t('connectionFailedMessage') }}
          </a-alert>
          <div class="action-buttons">
            <a-button type="primary" @click="initConnection">
              {{ t('retry') }}
            </a-button>
          </div>
        </div>
      </div>
      
      <!-- 工具栏始终显示 -->
      <div class="terminal-toolbar">
        <a-button 
          type="primary" 
          size="small" 
          @click="initConnection" 
          :disabled="connectionStatus === 'connecting' || connectionStatus === 'connected'"
        >
          {{ t('connect') }}
        </a-button>
        <a-button 
          type="primary" 
          size="small" 
          @click="handleReconnect" 
          :disabled="connectionStatus === 'connecting'"
        >
          {{ t('reconnect') }}
        </a-button>
        <a-button 
          type="outline" 
          size="small" 
          @click="handleDisconnect"
          :disabled="connectionStatus !== 'connected'"
        >
          {{ t('disconnect') }}
        </a-button>
        <a-button 
          type="outline" 
          size="small" 
          @click="clearTerminal"
        >
          {{ t('clear') }}
        </a-button>
      </div>
    </div>
  </a-drawer>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { t } from '../../utils/locale';
import { Message } from '@arco-design/web-vue';
import { generateTerminalToken, connectTerminal } from '../../api/host';

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  hostInfo: {
    type: Object,
    default: () => ({})
  }
});

// Emits
const emit = defineEmits(['update:visible', 'close']);

// 响应式数据
const isMobile = ref(false);
const connectionStatus = ref('disconnected'); // connecting, connected, disconnected, error
const errorMessage = ref('');
const disconnectReason = ref('');
const terminalRef = ref(null);
const websocket = ref(null);
const isConnecting = ref(false);
const connectTimeout = ref(null);

// xterm.js 相关
const term = ref(null);
const fitAddon = ref(null);

// 安全销毁终端和插件
const safeDisposeTerminal = () => {
  // 先销毁插件
  if (fitAddon.value) {
    try {
      // 检查插件是否已经被加载
      if (term.value && term.value._addonManager) {
        const addons = term.value._addonManager._addons;
        if (addons && addons.has && addons.has(fitAddon.value)) {
          fitAddon.value.dispose();
        }
      } else {
        // 如果终端不存在或没有插件管理器，直接销毁插件
        fitAddon.value.dispose();
      }
    } catch (e) {
      console.warn('FitAddon dispose warning (可忽略):', e.message);
    }
    fitAddon.value = null;
  }

  // 再销毁终端
  if (term.value) {
    try {
      term.value.dispose();
    } catch (e) {
      // console.warn('Terminal dispose warning (可忽略):', e.message);
    }
    term.value = null;
  }
};

// 移动端检测
const checkIsMobile = () => {
  isMobile.value = window.innerWidth <= 768;
};

// 初始化连接
const initConnection = async () => {
  if (isConnecting.value) return;
  
  try {
    isConnecting.value = true;
    connectionStatus.value = 'connecting';
    errorMessage.value = '';
    disconnectReason.value = '';
    
    const tokenResponse = await generateTerminalToken(props.hostInfo.id);
    if (!tokenResponse.success || !tokenResponse.token) {
      throw new Error('Failed to generate terminal token');
    }
    
    websocket.value = connectTerminal(props.hostInfo.id, tokenResponse.token);
    
    websocket.value.onopen = handleWebSocketOpen;
    websocket.value.onmessage = handleWebSocketMessage;
    websocket.value.onclose = handleWebSocketClose;
    websocket.value.onerror = handleWebSocketError;
  } catch (error) {
    console.error('连接失败:', error);
    connectionStatus.value = 'error';
    errorMessage.value = error.message || t('connectionFailedMessage');
    Message.error(t('connectionFailed') + ': ' + (error.message || t('unknownError')));
  } finally {
    isConnecting.value = false;
  }
};

// WebSocket 打开
const handleWebSocketOpen = () => {
  connectionStatus.value = 'connected';
  nextTick(() => {
    initializeTerminal();
  });
  Message.success(t.value('connectionSuccessful'));
};

// WebSocket 消息
const handleWebSocketMessage = (event) => {
  if (term.value) {
    try {
      const data = JSON.parse(event.data);
      if (data && typeof data === 'object' && data.error) {
        term.value.write(`\r\n\x1b[1;31m*** 错误: ${data.error} ***\x1b[0m\r\n`);
        return;
      }
    } catch {
      // JSON 解析失败，说明是普通文本
    }
    try {
      term.value.write(event.data);
    } catch (e) {
      console.warn('Terminal write error:', e);
    }
  }
};

// WebSocket 关闭
const handleWebSocketClose = (event) => {
  connectionStatus.value = 'disconnected';
  disconnectReason.value = t.value('userDisconnected');
};

// WebSocket 错误
const handleWebSocketError = (error) => {
  console.error('WebSocket错误:', error);
  connectionStatus.value = 'error';
  errorMessage.value = error.message || t('connectionFailedMessage');
  Message.error(t('connectionFailed') + ': ' + (error.message || t('unknownError')));
};

// 初始化终端
const initializeTerminal = () => {
  if (!terminalRef.value) return;
  
  // 先清理现有的终端和插件
  safeDisposeTerminal();
  
  // ✅ 关键修改：使用推荐的 fontFamily 顺序
  term.value = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    fontFamily: 'Consolas, "Courier New", "SFMono-Regular", "Menlo", "Monaco", "Roboto Mono", "Ubuntu Mono", monospace',
    theme: {
      background: '#000000',
      foreground: '#ffffff',
      cursor: '#ffffff',
      selectionBackground: '#264f78',
      selectionForeground: '#ffffff',
      cursorAccent: '#000000',
      black: '#000000',
      red: '#cd3131',
      green: '#0dbc79',
      yellow: '#e5e510',
      blue: '#2472c8',
      magenta: '#bc3fbc',
      cyan: '#11a8cd',
      white: '#e5e5e5',
      brightBlack: '#666666',
      brightRed: '#f14c4c',
      brightGreen: '#23d18b',
      brightYellow: '#f5f543',
      brightBlue: '#3b8eea',
      brightMagenta: '#d670d6',
      brightCyan: '#29b8db',
      brightWhite: '#e5e5e5',
    },
    allowTransparency: false,
    scrollback: 5000,
    fontWeight: 'normal',
    fontWeightBold: 'bold',
    lineHeight: 1.2,
    letterSpacing: 0,
  });
  
  // 创建并加载 FitAddon
  try {
    fitAddon.value = new FitAddon();
    term.value.loadAddon(fitAddon.value);
    term.value.open(terminalRef.value);
  } catch (e) {
    console.error('Terminal initialization error:', e);
    return;
  }
  
  // ✅ 移除了 setTimeout 字体设置，不再需要

  // 发送用户输入到后端（不进行本地回显，由后端返回）
  term.value.onData((data) => {
    if (websocket.value && websocket.value.readyState === WebSocket.OPEN) {
      const message = JSON.stringify({ type: 'input', data: data });
      websocket.value.send(message);
    }
  });

  // 特殊按键处理
  term.value.attachCustomKeyEventHandler((event) => {
    // 处理 Ctrl+C 特殊情况
    if (event.ctrlKey && event.key === 'c' && event.type === 'keydown') {
      if (websocket.value && websocket.value.readyState === WebSocket.OPEN) {
        const message = JSON.stringify({ type: 'input', data: '\x03' });
        websocket.value.send(message);
        event.preventDefault();
        return false;
      }
    }
    return true;
  });

  // 调整大小
  term.value.onResize(() => {
    sendResize();
  });

  const resizeObserver = new ResizeObserver(() => {
    if (fitAddon.value) {
      try {
        fitAddon.value.fit();
      } catch (e) {
        console.warn('Fit addon error:', e);
      }
    }
  });

  if (terminalRef.value?.parentElement) {
    resizeObserver.observe(terminalRef.value.parentElement);
  }

  const handleWindowResize = () => {
    if (fitAddon.value) {
      try {
        fitAddon.value.fit();
      } catch (e) {
        console.warn('Fit addon error:', e);
      }
    }
  };
  window.addEventListener('resize', handleWindowResize);
  window.handleWindowResize = handleWindowResize;

  try {
    fitAddon.value.fit();
  } catch (e) {
    console.warn('Initial fit error:', e);
  }

  sendResize();
};

// 发送大小
const sendResize = () => {
  if (websocket.value && websocket.value.readyState === WebSocket.OPEN && term.value) {
    const dimensions = { cols: term.value.cols, rows: term.value.rows };
    const message = JSON.stringify({ type: 'resize', data: dimensions });
    websocket.value.send(message);
  }
};

// 清屏
const clearTerminal = () => {
  if (term.value) {
    term.value.clear();
  }
};

// 重连
const handleReconnect = () => {
  handleDisconnect();
  if (connectTimeout.value) clearTimeout(connectTimeout.value);
  connectTimeout.value = setTimeout(() => {
    initConnection();
  }, 500);
};

// 断开
const handleDisconnect = () => {
  connectionStatus.value = 'disconnected';
  disconnectReason.value = t.value('userDisconnected');
  isConnecting.value = false;

  if (connectTimeout.value) {
    clearTimeout(connectTimeout.value);
    connectTimeout.value = null;
  }

  if (websocket.value) {
    websocket.value.close();
    websocket.value = null;
  }

  if (window.handleWindowResize) {
    window.removeEventListener('resize', window.handleWindowResize);
    window.handleWindowResize = null;
  }

  // 使用安全销毁方法
  safeDisposeTerminal();
};

// 关闭抽屉
const handleClose = () => {
  handleDisconnect();
  emit('update:visible', false);
  emit('close');
};

// 监听 visible
watch(() => props.visible, (newVal) => {
  if (newVal) {
    if (connectTimeout.value) clearTimeout(connectTimeout.value);
    connectTimeout.value = setTimeout(() => {
      initConnection();
    }, 300);
  } else {
    handleDisconnect();
  }
});

// 监听 hostInfo
watch(() => props.hostInfo, (newVal, oldVal) => {
  if (props.visible && newVal && newVal.id && JSON.stringify(newVal) !== JSON.stringify(oldVal)) {
    handleReconnect();
  }
}, { deep: true });

onMounted(() => {
  checkIsMobile();
  window.addEventListener('resize', checkIsMobile);
});

onUnmounted(() => {
  window.removeEventListener('resize', checkIsMobile);
  handleDisconnect();
});
</script>

<!-- ✅ 全局样式：确保字体生效 -->
<style>
/* 强制覆盖 xterm.js 字体渲染 */
.terminal-element .xterm,
.terminal-element .xterm .xterm-rows span,
.terminal-element .xterm .xterm-screen,
.terminal-element .xterm .xterm-scroll-area,
.terminal-element .xterm .xterm-char-measure-element {
  font-family: Consolas, "Courier New", "SFMono-Regular", "Menlo", "Monaco", "Roboto Mono", "Ubuntu Mono", monospace !important;
  font-size: 14px !important;
  font-weight: normal !important;
}
</style>

<style scoped>
.terminal-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
}

.terminal-element {
  flex: 1;
  background-color: #000000;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 16px;
  padding: 8px;
}

.terminal-overlay {
  position: absolute;
  top: 8px;
  left: 24px;
  right: 24px;
  bottom: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.7);
  border-radius: 4px;
  z-index: 10;
}

.status-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 20px;
  max-width: 80%;
}

.status-info .arco-spin {
  margin-bottom: 16px;
}

.status-info span {
  font-size: 14px;
  color: #fff;
}

.action-buttons {
  margin-top: 20px;
}

.terminal-toolbar {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

:deep(.arco-alert) {
  margin-bottom: 20px;
  color: #fff;
}

:deep(.arco-alert-warning) {
  background-color: rgba(255, 127, 0, 0.2);
  border-color: #faad14;
}

:deep(.arco-alert-error) {
  background-color: rgba(255, 0, 0, 0.2);
  border-color: #f53f3f;
}
</style>