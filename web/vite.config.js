import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
// 导入插件（导出的是对象，不是函数）
import monacoEditorPlugin from 'vite-plugin-monaco-editor'

export default defineConfig({
  plugins: [
    vue(),
    monacoEditorPlugin,
  ],

  monacoEditorPlugin: {
    languageWorkers: ['editorWorkerService', 'typescript', 'json', 'html', 'css', 'shell']
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api/v2': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v2/, ''),
        ws: true
      },
      '/docs': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true
      },
      '/openapi.json': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true
      },
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          monaco: ['monaco-editor']
        }
      }
    }
  },

  optimizeDeps: {
    include: [
      'monaco-editor/esm/vs/language/json/json.worker',
      'monaco-editor/esm/vs/language/css/css.worker',
      'monaco-editor/esm/vs/language/html/html.worker',
      'monaco-editor/esm/vs/language/typescript/ts.worker',
      'monaco-editor/esm/vs/editor/editor.worker'
    ]
  }
})