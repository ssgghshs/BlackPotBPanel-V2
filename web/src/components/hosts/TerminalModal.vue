<template>
  <a-modal
    :width="isMobile ? '95%' : isFullscreen ? '100%' : 800"
    :visible="visible"
    :footer="false"
    :mask-closable="false"
    :unmount-on-close="true"
    :fullscreen="isFullscreen"
    @cancel="handleClose"
    class="terminal-modal"
    :class="{ 'fullscreen-modal': isFullscreen }"
  >
    <template #title>
      <div class="terminal-title">
        <div class="terminal-header">
          <a-button 
            type="text" 
            size="small" 
            @click="toggleFullscreen"
            :title="isFullscreen ? t('fullscreen') : t('fullscreen')"
            class="fullscreen-btn"
          >
            <template #icon>
              <icon-fullscreen-exit v-if="isFullscreen" />
              <icon-fullscreen v-else />
            </template>
          </a-button>
          <span class="terminal-title-text">{{ t('terminalConnection') }}</span>
        </div>
      </div>
    </template>

    <div class="terminal-container">
      <!-- 连接本机SSH表单 -->
      <div v-if="showConnectForm" class="connect-form">
        <a-form :model="connectForm" layout="vertical" @submit="handleConnect">
          <a-form-item field="address" :label="t('hostAddress')" required>
            <a-input v-model="connectForm.address" disabled />
          </a-form-item>

          <a-form-item field="username" :label="t('username')" required>
            <a-input v-model="connectForm.username" />
          </a-form-item>

          <a-form-item field="password" :label="t('password')">
            <a-input-password v-model="connectForm.password" />
          </a-form-item>

          <a-form-item field="port" :label="t('port')" required>
            <a-input-number v-model="connectForm.port" :min="1" :max="65535" />
          </a-form-item>

          <a-form-item>
            <a-button type="primary" html-type="submit" :loading="connecting" block>
              {{ connecting ? t('connecting') : t('connect') }}
            </a-button>
          </a-form-item>
        </a-form>
      </div>

      <!-- 连接状态显示 -->
      <div v-else-if="connecting" class="connecting-status">
        <a-spin />
        <p>{{ t('connectingToHost') }}...</p>
      </div>

      <!-- 终端连接成功显示 -->
      <div v-else ref="terminalRef" class="terminal-element"></div>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { t } from '../../utils/locale';
import { Message } from '@arco-design/web-vue';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';
import { connectLocalhostSSH, connectTerminal, updateHost } from '../../api/host';
import { IconFullscreen, IconFullscreenExit } from '@arco-design/web-vue/es/icon';

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  hostInfo: {
    type: Object,
    default: () => ({}),
  },
  // 添加当前路径属性
  currentPath: {
    type: String,
    default: '/opt/blackpotbpanel-v2/server'
  }
});

// Emits
const emit = defineEmits(['update:visible', 'close']);

// 响应式数据
const isMobile = ref(false);
const isFullscreen = ref(false);
const showConnectForm = ref(false);
const connecting = ref(false);
const connectForm = ref({
  address: '127.0.0.1',
  username: '',
  password: '',
  port: 22
});
const terminalRef = ref(null);
const term = ref(null);
const fitAddon = ref(null);
const websocket = ref(null);

// 检测移动端
const checkIsMobile = () => {
  isMobile.value = window.innerWidth <= 768;
};

// 切换全屏
const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value;
  // 在下一个tick中调整终端大小
  nextTick(() => {
    if (fitAddon.value && term.value) {
      try {
        fitAddon.value.fit();
      } catch (e) {
        console.warn('Fit addon error:', e);
      }
    }
  });
};

// 处理关闭
const handleClose = () => {
  // 退出全屏模式
  isFullscreen.value = false;
  
  // 清理窗口大小调整事件监听器
  if (window.handleWindowResize) {
    window.removeEventListener('resize', window.handleWindowResize);
    window.handleWindowResize = null;
  }
  
  // 安全地清理WebSocket资源
  if (websocket.value) {
    try {
      websocket.value.close();
    } catch (e) {

    }
    websocket.value = null;
  }

  // 安全地清理终端资源
  if (term.value) {
    try {
      // 先清理插件再销毁终端（完全避免在未加载时调用dispose）
      if (fitAddon.value) {
        // 仅在确认插件已加载的情况下才尝试销毁
        // 通过检查插件是否具有已知方法来判断是否已加载
        const loadedAddonMethods = ['fit', 'activate', 'dispose'];
        const isLoaded = loadedAddonMethods.every(method =>
          typeof fitAddon.value[method] === 'function'
        );

        if (isLoaded) {
          try {
            fitAddon.value.dispose();
          } catch (e) {

          }
        }
      }
      fitAddon.value = null;

      // 销毁终端
      try {
        term.value.dispose();
      } catch (e) {

      }
    } catch (e) {

    }
    term.value = null;
  }

  // 重置状态
  showConnectForm.value = false;
  connecting.value = false;

  emit('update:visible', false);
  emit('close');
};

// 初始化连接
const initConnection = async () => {
  try {
    connecting.value = true;

    // 调用后端接口连接本机SSH
    const responseData = await connectLocalhostSSH();

    // 打印响应数据以调试
    console.log('连接本机SSH响应数据:', responseData);

    // 检查响应数据是否存在
    if (responseData) {
      if (responseData.success) {
        // 连接成功，建立WebSocket终端连接
        websocket.value = connectTerminal(responseData.host_id, responseData.token);
        setupWebSocket();
        // 隐藏连接表单，显示终端界面
        showConnectForm.value = false;
      } else {
        // 连接失败，显示连接表单
        showConnectForm.value = true;
        // 填充返回的主机信息
        if (responseData.host_info) {
          connectForm.value = {
            address: responseData.host_info.address || '127.0.0.1',
            username: responseData.host_info.username || '',
            password: '',
            port: responseData.host_info.port || 22
          };
        }
      }
    } else {
      // 响应数据为空
      throw new Error('Empty response data');
    }
  } catch (error) {
    console.error('连接本机SSH失败:', error);
    Message.error(t.value('connectionFailed') + ': ' + (error.message || t.value('unknownError')));
    showConnectForm.value = true;
  } finally {
    connecting.value = false;
  }
};

// 设置WebSocket连接
const setupWebSocket = () => {
  if (!websocket.value) return;

  websocket.value.onopen = () => {
    nextTick(() => {
      initializeTerminal();
    });
    Message.success(t.value('connectionSuccessful'));
  };

  websocket.value.onmessage = (event) => {
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

  websocket.value.onclose = () => {
    Message.info(t.value('connectionClosed'));
  };

  websocket.value.onerror = (error) => {
    console.error('WebSocket错误:', error);
    Message.error(t.value('connectionFailed') + ': ' + (error.message || t.value('unknownError')));
  };
};

// 初始化终端
const initializeTerminal = () => {
  if (!terminalRef.value) return;

  // 清理现有终端
  if (term.value) {
    try {
      // 先清理插件再销毁终端（完全避免在未加载时调用dispose）
      if (fitAddon.value) {
        // 仅在确认插件已加载的情况下才尝试销毁
        // 通过检查插件是否具有已知方法来判断是否已加载
        const loadedAddonMethods = ['fit', 'activate', 'dispose'];
        const isLoaded = loadedAddonMethods.every(method =>
          typeof fitAddon.value[method] === 'function'
        );

        if (isLoaded) {
          try {
            fitAddon.value.dispose();
          } catch (e) {
            console.warn('Fit addon dispose error:', e);
          }
        }
      }
      fitAddon.value = null;

      // 销毁终端
      try {
        term.value.dispose();
      } catch (e) {
        console.warn('Terminal dispose error:', e);
      }
    } catch (e) {
      console.warn('Terminal cleanup error:', e);
    }
    term.value = null;
  }

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

  // 确保在加载插件前终端已准备好
  fitAddon.value = new FitAddon();
  try {
    term.value.loadAddon(fitAddon.value);
  } catch (e) {
    console.error('Failed to load fit addon:', e);
    fitAddon.value = null;
    return;
  }

  term.value.open(terminalRef.value);

  // 调整大小
  term.value.onResize(() => {
    sendResize();
  });

  // 处理从后端接收到的消息
  websocket.value.onmessage = (event) => {
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
    if (fitAddon.value) {
      fitAddon.value.fit();
    }
  } catch (e) {
    console.warn('Initial fit error:', e);
  }
  
  sendResize();
  
  // 如果有当前路径，发送合并命令清理屏幕并切换目录
  if (props.currentPath) {
    // 等待终端初始化完成后再发送命令
    setTimeout(() => {
      if (websocket.value && websocket.value.readyState === WebSocket.OPEN) {
        // 合并clear和cd命令，加快执行速度
        const combinedCommand = `clear && cd ${props.currentPath}\n`;
        const commandMessage = JSON.stringify({ type: 'input', data: combinedCommand });
        websocket.value.send(commandMessage);
      }
    }, 500);
  }
};

// 发送大小
const sendResize = () => {
  if (websocket.value && websocket.value.readyState === WebSocket.OPEN && term.value) {
    const dimensions = { cols: term.value.cols, rows: term.value.rows };
    const message = JSON.stringify({ type: 'resize', data: dimensions });
    websocket.value.send(message);
  }
};

// 处理连接表单提交
const handleConnect = async (formData) => {
  // 注意：Arco Design Vue的表单@submit事件传递的是表单数据对象而非DOM事件对象
  // 因此我们不能调用e.preventDefault()方法

  // 使用formData而不是试图从事件对象中获取数据
  connectForm.value = { ...connectForm.value, ...formData };

  // 设置连接状态
  connecting.value = true;

  try {
    // 先保存主机信息到数据库
    // 从 responseData 中获取 host_id
    const hostData = {
      address: connectForm.value.address,
      username: connectForm.value.username,
      port: connectForm.value.port,
      password: connectForm.value.password,
      auth_method: 'password'
    };

    // 调用API保存主机信息
    // 注意：我们需要使用从 connectLocalhostSSH 响应中获取的 host_id
    // 在这个上下文中，我们暂时使用默认的 localhost host_id (1)
    // 在实际应用中，应该从组件的 props 或状态中获取正确的 host_id
    await updateHost(1, hostData);

    // 保存成功后，重新尝试连接
    await initConnection();

    // 隐藏连接表单，显示终端界面
    showConnectForm.value = false;
  } catch (error) {
    console.error('保存主机信息失败:', error);
    Message.error(t.value('saveHostInfoFailed') + ': ' + (error.message || t.value('unknownError')));
  } finally {
    connecting.value = false;
  }
};

// 监听 visible
watch(
  () => props.visible,
  (newVal) => {
    if (newVal) {
      // 模态框打开时初始化连接
      nextTick(() => {
        initConnection();
      });
    } else {
      // 模态框关闭时清理资源
      // 退出全屏模式
      isFullscreen.value = false;
      
      // 清理窗口大小调整事件监听器
      if (window.handleWindowResize) {
        window.removeEventListener('resize', window.handleWindowResize);
        window.handleWindowResize = null;
      }
      
      // 安全地清理WebSocket资源
      if (websocket.value) {
        try {
          websocket.value.close();
        } catch (e) {
          console.warn('WebSocket close error:', e);
        }
        websocket.value = null;
      }

      // 安全地清理终端资源
      if (term.value) {
        try {
          // 先清理插件再销毁终端（完全避免在未加载时调用dispose）
          if (fitAddon.value) {
            // 仅在确认插件已加载的情况下才尝试销毁
            // 通过检查插件是否具有已知方法来判断是否已加载
            const loadedAddonMethods = ['fit', 'activate', 'dispose'];
            const isLoaded = loadedAddonMethods.every(method =>
              typeof fitAddon.value[method] === 'function'
            );

            if (isLoaded) {
              try {
                fitAddon.value.dispose();
              } catch (e) {
                console.warn('Fit addon dispose error:', e);
              }
            }
          }
          fitAddon.value = null;

          // 销毁终端
          try {
            term.value.dispose();
          } catch (e) {
            console.warn('Terminal dispose error:', e);
          }
        } catch (e) {
          console.warn('Terminal cleanup error:', e);
        }
        term.value = null;
      }

      showConnectForm.value = false;
      connecting.value = false;
    }
  }
);

// 监听全屏状态变化
watch(isFullscreen, (newVal) => {
  if (newVal) {
    document.body.style.overflow = 'hidden';
  } else {
    document.body.style.overflow = '';
  }
  
  // 在下一个tick中调整终端大小
  nextTick(() => {
    if (fitAddon.value && term.value) {
      try {
        fitAddon.value.fit();
        // 发送终端大小调整信息
        sendResize();
      } catch (e) {
        console.warn('Fit addon error:', e);
      }
    }
  });
});

onMounted(() => {
  checkIsMobile();
  window.addEventListener('resize', checkIsMobile);
});

onUnmounted(() => {
  window.removeEventListener('resize', checkIsMobile);
  
  // 恢复body的overflow样式
  document.body.style.overflow = '';

  // 清理窗口大小调整事件监听器
  if (window.handleWindowResize) {
    window.removeEventListener('resize', window.handleWindowResize);
    window.handleWindowResize = null;
  }

  // 清理资源
  if (websocket.value) {
    websocket.value.close();
  }

  // 安全地清理终端资源
  if (term.value) {
    try {
      // 先清理插件再销毁终端（完全避免在未加载时调用dispose）
      if (fitAddon.value) {
        // 仅在确认插件已加载的情况下才尝试销毁
        // 通过检查插件是否具有已知方法来判断是否已加载
        const loadedAddonMethods = ['fit', 'activate', 'dispose'];
        const isLoaded = loadedAddonMethods.every(method =>
          typeof fitAddon.value[method] === 'function'
        );

        if (isLoaded) {
          try {
            fitAddon.value.dispose();
          } catch (e) {
            console.warn('Fit addon dispose error:', e);
          }
        }
      }
      fitAddon.value = null;

      // 销毁终端
      try {
        term.value.dispose();
      } catch (e) {
        console.warn('Terminal dispose error:', e);
      }
    } catch (e) {
      console.warn('Terminal cleanup error:', e);
    }
    term.value = null;
  }
});

</script>

<!-- 全局样式：确保字体生效 -->
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

.terminal-modal :deep(.arco-modal-body) {
  padding: 20px;
  min-height: 200px;
}

.terminal-modal :deep(.arco-modal-header) {
  background: #1a1a1a;
  color: #fff;
  border-bottom: 1px solid #333;
  padding: 12px 20px;
}

.terminal-modal.fullscreen-modal :deep(.arco-modal-header) {
  border-radius: 0;
}

.terminal-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.terminal-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.terminal-title-text {
  font-weight: 500;
}

.terminal-actions {
  display: flex;
  gap: 8px;
}

.terminal-container {
  min-height: 60px;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 540px);
}

.terminal-modal.fullscreen-modal .terminal-container {
  height: calc(100vh - 100px);
}

.connect-form {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.connecting-status {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.connecting-status p {
  margin-top: 16px;
  color: #666;
}

.terminal-element {
  flex: 1;
  background-color: #000000;
  border-radius: 4px;
  overflow: hidden;
  padding: 8px;
}

.fullscreen-btn {
  color: #fff;
  transition: all 0.2s;
}

.fullscreen-btn:hover {
  color: #165dff;
  background-color: rgba(255, 255, 255, 0.1);
}

/* 暗色主题下的全屏按钮样式 */
.arco-modal-header[arco-theme='dark'] .fullscreen-btn {
  color: #fff;
}

.arco-modal-header[arco-theme='dark'] .fullscreen-btn:hover {
  color: #3C8CE7;
  background-color: rgba(255, 255, 255, 0.1);
}

/* 浅色主题下的全屏按钮样式 */
.arco-modal-header:not([arco-theme='dark']) .fullscreen-btn {
  color: #000;
}

.arco-modal-header:not([arco-theme='dark']) .fullscreen-btn:hover {
  color: #165dff;
  background-color: rgba(0, 0, 0, 0.1);
}
</style>