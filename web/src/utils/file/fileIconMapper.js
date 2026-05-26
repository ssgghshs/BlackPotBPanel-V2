import { 
  IconFolder, 
  IconFile,
  IconMosaic,
  IconCodeSquare,
  IconCode,
  IconCodeBlock
} from '@arco-design/web-vue/es/icon';
import * as AntdIcons from '@ant-design/icons-vue';
import TsIcon from '../../components/icon/file/TsIcon.vue'
import JsIcon from '../../components/icon/file/JsIcon.vue'
import JsxIcon from '../../components/icon/file/JsxIcon.vue'
import JavaIcon from '../../components/icon/file/JavaIcon.vue'
import CppIcon from '../../components/icon/file/CppIcon.vue'
import PhpIcon from '../../components/icon/file/PhpIcon.vue'
import PythonIcon from '../../components/icon/file/PythonIcon.vue'
import VueIcon from '../../components/icon/file/VueIcon.vue'
import HtmlIcon from '../../components/icon/file/HtmlIcon.vue'
import RubyIcon from '../../components/icon/file/RubyIcon.vue'
import CssIcon from '../../components/icon/file/CssIcon.vue'
import GoIcon from '../../components/icon/file/GoIcon.vue'
import RustIcon from '../../components/icon/file/RustIcon.vue'
import MarkdownIcon from '../../components/icon/file/MarkdownIcon.vue'
import LuaIcon from '../../components/icon/file/LuaIcon.vue'
import SqlIcon from '../../components/icon/file/SqlIcon.vue'
import YmlIcon from '../../components/icon/file/YmlIcon.vue'
import JsonIcon from '../../components/icon/file/JsonIcon.vue'
import ConfIcon from '../../components/icon/file/ConfIcon.vue'
import KotlinIcon from '../../components/icon/file/KotlinIcon.vue'
import TerminalIcon from '../../components/icon/TerminalIcon.vue'




/**
 * 获取文件图标组件
 * @param {Object} record - 文件记录对象
 * @param {boolean} record.is_directory - 是否为目录
 * @param {string} record.filename - 文件名
 * @returns {Component} 图标组件
 */
export const getFileIcon = (record) => {
  // 添加对 record 和 filename 的检查
  if (!record) {
    return IconFile;
  }
  
  if (record.is_directory) {
    return IconFolder;
  }
  
  // 确保 filename 存在且为字符串
  const fileName = record.filename && typeof record.filename === 'string' 
    ? record.filename.toLowerCase() 
    : '';

  // 压缩文件
  if (fileName.endsWith('.zip') || fileName.endsWith('.tar.gz') || fileName.endsWith('.tar') || 
      fileName.endsWith('.gz') || fileName.endsWith('.rar') || fileName.endsWith('.7z') || 
      fileName.endsWith('.tar.bz2') || fileName.endsWith('.tar.xz') || fileName.endsWith('.tgz')) {
    return AntdIcons.FileZipOutlined;
  }
  
  // 图片文件
  if (fileName.endsWith('.jpg') || fileName.endsWith('.jpeg')) {
    return AntdIcons.FileJpgOutlined;
  }
  
  if (fileName.endsWith('.png') || fileName.endsWith('.gif') || fileName.endsWith('.bmp') || 
      fileName.endsWith('.webp') || fileName.endsWith('.svg') || fileName.endsWith('.ico')) {
    return IconMosaic;
  }
  
  // 文档文件
  if (fileName.endsWith('.pdf')) {
    return AntdIcons.FilePdfOutlined;
  }
  
  if (fileName.endsWith('.doc') || fileName.endsWith('.docx')) {
    return AntdIcons.FileWordOutlined;
  }
  
  if (fileName.endsWith('.xls') || fileName.endsWith('.xlsx')) {
    return AntdIcons.FileExcelOutlined;
  }
  
  if (fileName.endsWith('.ppt') || fileName.endsWith('.pptx')) {
    return AntdIcons.FilePptOutlined;
  }
  
  // 特定编程语言文件 - 使用自定义图标
  if (fileName.endsWith('.ts')) {
    return TsIcon;
  }
  
  if (fileName.endsWith('.js')) {
    return JsIcon;
  }

  if (fileName.endsWith('.jsx') || fileName.endsWith('.tsx')) {
    return JsxIcon;
  }
  
  if (fileName.endsWith('.java')) {
    return JavaIcon;
  }
  
  if (fileName.endsWith('.cpp') || fileName.endsWith('.c') || fileName.endsWith('.h')) {
    return CppIcon;
  }
  
  if (fileName.endsWith('.php')) {
    return PhpIcon;
  }
  
  if (fileName.endsWith('.py')) {
    return PythonIcon;
  }
  
  if (fileName.endsWith('.rb')) {
    return RubyIcon;
  }
  
  if (fileName.endsWith('.vue')) {
    return VueIcon;
  }
  
  if (fileName.endsWith('.html') || fileName.endsWith('.htm')) {
    return HtmlIcon;
  }
  
  if (fileName.endsWith('.css')) {
    return CssIcon;
  }
  
  if (fileName.endsWith('.go')) {
    return GoIcon;
  }
  
  if (fileName.endsWith('.rs')) {
    return RustIcon;
  }
  
  if (fileName.endsWith('.md')) {
    return MarkdownIcon;
  }
  
  if (fileName.endsWith('.lua')) {
    return LuaIcon;
  }
  
  if (fileName.endsWith('.sql')) {
    return SqlIcon;
  }
  
  if (fileName.endsWith('.yml') || fileName.endsWith('.yaml')) {
    return YmlIcon;
  }
  
  if (fileName.endsWith('.conf')) {
    return ConfIcon;
  }
  
  if (fileName.endsWith('.kt')) {
    return KotlinIcon;
  }
  
  if (fileName.endsWith('.sh') || fileName.endsWith('.bat') || fileName.endsWith('.ps1')) {
    return TerminalIcon;
  }
  
  // 其他代码文件
  if (fileName.endsWith('.pl') || fileName.endsWith('.tcl') ||
      fileName.endsWith('.cs') || fileName.endsWith('.swift') || fileName.endsWith('.dart') || 
      fileName.endsWith('.r') || fileName.endsWith('.scala') || fileName.endsWith('.groovy') || 
      fileName.endsWith('.cfg') || fileName.endsWith('.ini')
    ) {
    return IconCodeSquare;
  }
  
  // XML文件
  if (fileName.endsWith('.xml')) {
    return IconCode;
  }
  
  if (fileName.endsWith('.json')) {
    return JsonIcon;
  }
  
  // 音频文件
  if (fileName.endsWith('.mp3') || fileName.endsWith('.wav') || fileName.endsWith('.flac') || 
      fileName.endsWith('.aac') || fileName.endsWith('.ogg')) {
    return AntdIcons.AudioOutlined;
  }
  
  // 视频文件
  if (fileName.endsWith('.mp4') || fileName.endsWith('.avi') || fileName.endsWith('.mkv') || 
      fileName.endsWith('.mov') || fileName.endsWith('.wmv') || fileName.endsWith('.flv')) {
    return AntdIcons.VideoCameraOutlined;
  }
  
  // 文本文件
  if (fileName.endsWith('.txt') || fileName.endsWith('.md') || fileName.endsWith('.log') || 
      fileName.endsWith('.csv') ) {
    return AntdIcons.FileTextOutlined;
  }
  
  // 脚本文件（没有后缀的可执行文件）
  if (!fileName.includes('.')) {
    const executableScripts = [
      'install', 'configure', 'make', 'build', 'run', 'start', 'stop', 
      'restart', 'setup', 'init', 'deploy', 'test', 'clean', 'compile',
      'update', 'upgrade', 'backup', 'restore', 'migrate', 'generate',
      'create', 'delete', 'sync', 'watch', 'serve', 'dev', 'prod',
      'debug', 'release', 'package', 'publish', 'unpublish', 'login',
      'logout', 'register', 'reset', 'verify', 'import', 'export'
    ];
    
    if (executableScripts.includes(fileName)) {
      return AntdIcons.FileTextOutlined;
    }
    
    return AntdIcons.FileTextOutlined;
  }
  
  return IconFile;
};

/**
 * 获取文件图标颜色
 * @param {Object} record - 文件记录对象
 * @param {boolean} record.is_directory - 是否为目录
 * @param {string} record.filename - 文件名
 * @returns {string} 颜色值
 */
export const getFileIconColor = (record) => {
  // 添加对 record 的检查
  if (!record) {
    return '#9E9E9E';
  }
  
  if (record.is_directory) {
    return '#FFB300';
  }
  
  // 确保 filename 存在且为字符串
  const fileName = record.filename && typeof record.filename === 'string' 
    ? record.filename.toLowerCase() 
    : '';
  
  // 使用自定义图标的文件类型 - 返回 undefined 让图标使用自身原色
  if (fileName.endsWith('.ts') || fileName.endsWith('.tsx') ||
      fileName.endsWith('.js') || fileName.endsWith('.jsx') ||
      fileName.endsWith('.java') ||
      fileName.endsWith('.cpp') || fileName.endsWith('.c') || fileName.endsWith('.h') ||
      fileName.endsWith('.php') ||
      fileName.endsWith('.py') ||
      fileName.endsWith('.rb') ||
      fileName.endsWith('.vue') ||
      fileName.endsWith('.html') || fileName.endsWith('.htm') ||
      fileName.endsWith('.css') ||
      fileName.endsWith('.go') ||
      fileName.endsWith('.rs') ||
      fileName.endsWith('.md') ||
      fileName.endsWith('.lua') ||
      fileName.endsWith('.sql') ||
      fileName.endsWith('.yml') ||
      fileName.endsWith('.yaml') ||
      fileName.endsWith('.json') ||
      fileName.endsWith('.conf') ||
      fileName.endsWith('.cfg') ||
      fileName.endsWith('.ini') ||
      fileName.endsWith('.kt')) {
    return undefined;
  }
  
  // 其他代码文件
  if (fileName.endsWith('.pl') || fileName.endsWith('.tcl') ||
      fileName.endsWith('.sh') || fileName.endsWith('.bat') || fileName.endsWith('.ps1') ||
      fileName.endsWith('.cs') || fileName.endsWith('.swift') || fileName.endsWith('.dart') || 
      fileName.endsWith('.r') || fileName.endsWith('.scala') || fileName.endsWith('.groovy') ||
      fileName.endsWith('.txt') || fileName.endsWith('.log') || 
      fileName.endsWith('.csv') ||
      fileName.endsWith('.env') || fileName.endsWith('.config')) {
    return '#9E9E9E';
  }
  
  // XML文件
  if (fileName.endsWith('.xml')) {
    return '#4CAF50';
  }
  
  // 图片文件
  if (fileName.endsWith('.jpg') || fileName.endsWith('.jpeg') || fileName.endsWith('.png') || 
      fileName.endsWith('.gif') || fileName.endsWith('.bmp') || fileName.endsWith('.webp') || 
      fileName.endsWith('.svg') || fileName.endsWith('.ico')) {
    return '#2196F3';
  }
  
  // 压缩文件
  if (fileName.endsWith('.zip') || fileName.endsWith('.tar.gz') || fileName.endsWith('.tar') || 
      fileName.endsWith('.gz') || fileName.endsWith('.rar') || fileName.endsWith('.7z') || fileName.endsWith('.tgz')) {
    return '#FF9800';
  }
  
  // 文档文件
  if (fileName.endsWith('.pdf') || fileName.endsWith('.doc') || fileName.endsWith('.docx') ||
      fileName.endsWith('.xls') || fileName.endsWith('.xlsx') || fileName.endsWith('.ppt') || 
      fileName.endsWith('.pptx')) {
    return '#F44336';
  }
  
  // 音频文件
  if (fileName.endsWith('.mp3') || fileName.endsWith('.wav') || fileName.endsWith('.flac') || 
      fileName.endsWith('.aac') || fileName.endsWith('.ogg')) {
    return '#9C27B0';
  }
  
  // 视频文件
  if (fileName.endsWith('.mp4') || fileName.endsWith('.avi') || fileName.endsWith('.mkv') || 
      fileName.endsWith('.mov') || fileName.endsWith('.wmv') || fileName.endsWith('.flv')) {
    return '#E91E63';
  }
  
  // 脚本文件（没有后缀的可执行文件）
  if (!fileName.includes('.')) {
    const executableScripts = [
      'install', 'configure', 'make', 'build', 'run', 'start', 'stop', 
      'restart', 'setup', 'init', 'deploy', 'test', 'clean', 'compile',
      'update', 'upgrade', 'backup', 'restore', 'migrate', 'generate',
      'create', 'delete', 'sync', 'watch', 'serve', 'dev', 'prod',
      'debug', 'release', 'package', 'publish', 'unpublish', 'login',
      'logout', 'register', 'reset', 'verify', 'import', 'export'
    ];
    
    if (executableScripts.includes(fileName)) {
      return '#9E9E9E';
    }
    
    return '#9E9E9E';
  }
  
  return '#9E9E9E';
};

/**
 * 检查文件是否为图片格式
 * @param {string} filename - 文件名
 * @returns {boolean}
 */
export const isImageFile = (filename) => {
  if (!filename || typeof filename !== 'string') {
    return false;
  }
  
  const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico'];
  const lowerFilename = filename.toLowerCase();
  return imageExtensions.some(ext => lowerFilename.endsWith(ext));
};

/**
 * 检查文件是否为压缩文件
 * @param {string} filename - 文件名
 * @returns {boolean}
 */
export const isCompressedFile = (filename) => {
  if (!filename || typeof filename !== 'string') {
    return false;
  }
  
  const compressedExtensions = ['.zip', '.tar', '.tar.gz', '.gz', '.rar', '.7z', '.tgz'];
  const lowerFilename = filename.toLowerCase();
  return compressedExtensions.some(ext => lowerFilename.endsWith(ext));
};

/**
 * 获取文件语言类型用于 Monaco Editor 语法高亮
 * @param {string} filename - 文件名
 * @returns {string} 语言标识
 */
export const getFileLanguage = (fileName) => {
  if (!fileName || typeof fileName !== 'string') {
    return 'plaintext';
  }
  
  const name = fileName.toLowerCase();
  
  if (name.endsWith('.js') || name.endsWith('.jsx')) {
    return 'javascript';
  }
  
  if (name.endsWith('.ts') || name.endsWith('.tsx')) {
    return 'typescript';
  }
  
  if (name.endsWith('.py')) {
    return 'python';
  }
  
  if (name.endsWith('.html') || name.endsWith('.htm') || name.endsWith('.vue')) {
    return 'html';
  }
  
  if (name.endsWith('.css')) {
    return 'css';
  }
  
  if (name.endsWith('.scss')) {
    return 'scss';
  }
  
  if (name.endsWith('.json')) {
    return 'json';
  }
  
  if (name.endsWith('.xml')) {
    return 'xml';
  }
  
  if (name.endsWith('.java')) {
    return 'java';
  }
  
  if (name.endsWith('.c') || name.endsWith('.cpp') || name.endsWith('.h')) {
    return 'cpp';
  }
  
  if (name.endsWith('.cs')) {
    return 'csharp';
  }
  
  if (name.endsWith('.php')) {
    return 'php';
  }
  
  if (name.endsWith('.sql')) {
    return 'sql';
  }
  
  if (name.endsWith('.sh') || name.endsWith('.bash') || name.endsWith('.zsh')) {
    return 'shell';
  }
  
  if (name.endsWith('.rb')) {
    return 'ruby';
  }
  
  if (name.endsWith('.go')) {
    return 'go';
  }
  
  if (name.endsWith('.rs')) {
    return 'rust';
  }
  
  if (name.endsWith('.md')) {
    return 'plaintext';
  }
  
  if (name.endsWith('.yaml') || name.endsWith('.yml')) {
    return 'yaml';
  }
  
  return 'plaintext';
};

/**
 * 检查文件是否可以打开编辑
 * @param {string} filename - 文件名
 * @returns {boolean}
 */
export const canOpenFile = (filename) => {
  if (!filename || typeof filename !== 'string') {
    return false;
  }
  
  return true;
};