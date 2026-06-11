import { marked } from 'marked';
import hljs from 'highlight.js';
import request from '../request';

// marked 配置代码高亮
marked.setOptions({
  highlight: function (code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value;
      } catch (_) {}
    }
    return hljs.highlightAuto(code).value;
  },
  breaks: true,
  gfm: true,
});

/**
 * 将 markdown-file:// 协议路径转为后端 API 读取路由
 * markdown:// 前缀的内容为内联 markdown，直接返回文本
 * @param {string} content - 原始内容（可能以 markdown-file:// 或 markdown:// 开头）
 * @param {string} storeName - 商店标识名
 * @returns {string} 转换后的 URL 或原始文本
 */
export function resolveStoreReadme(content, storeName) {
  if (!content) return '';
  if (content.startsWith('markdown-file://')) {
    const relativePath = content.replace('markdown-file://', '');
    const baseURL = request.defaults.baseURL;
    return `${baseURL}/container/store/${storeName}/readme/${relativePath}`;
  }
  if (content.startsWith('markdown://')) {
    return content.replace('markdown://', '');
  }
  return content;
}

/**
 * 将 Markdown 文本渲染为安全的 HTML
 * @param {string} text - 原始 Markdown 文本
 * @returns {string} 渲染后的 HTML
 */
export function renderStoreReadmeHtml(text) {
  if (!text) return '';
  return marked.parse(text);
}
