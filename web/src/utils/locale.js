import { ref, watch, computed } from 'vue'
import zhCN from '@arco-design/web-vue/es/locale/lang/zh-cn'
import enUS from '@arco-design/web-vue/es/locale/lang/en-us'
import zhTW from '@arco-design/web-vue/es/locale/lang/zh-tw'
import jaJP from '@arco-design/web-vue/es/locale/lang/ja-jp'
import koKR from '@arco-design/web-vue/es/locale/lang/ko-kr'

// 导入外部翻译数据
import zhCNTranslations from './modules/zh-CN.json'
import enUSTranslations from './modules/en-US.json'
import zhTWTranslations from './modules/zh-TW.json'
import jaJPTranslations from './modules/ja-JP.json'
import koKRTranslations from './modules/ko-KR.json'

// 创建响应式的语言状态
export const currentLocale = ref('zh-CN')
export const locale = ref(zhCN)

// 切换语言的函数
export const changeLocale = (value) => {
  currentLocale.value = value
  locale.value = value === 'zh-CN' ? zhCN : value === 'zh-TW' ? zhTW : value === 'ja-JP' ? jaJP : value === 'ko-KR' ? koKR : enUS

  // 保存到本地存储
  localStorage.setItem('locale', value)
}

// 获取当前语言
export const getCurrentLocale = () => {
  return currentLocale.value
}

// 获取当前语言包
export const getCurrentLocalePackage = () => {
  return locale.value
}

// 页面加载时从本地存储恢复语言设置
const savedLocale = localStorage.getItem('locale')
if (savedLocale) {
  changeLocale(savedLocale)
}

// 监听语言变化，自动保存到本地存储
watch(currentLocale, (newLocale) => {
  localStorage.setItem('locale', newLocale)
})

// 创建一个计算属性，用于简化文本的国际化处理
export const t = computed(() => {
  // 使用导入的外部翻译数据
  const translations = {
    'zh-CN': zhCNTranslations,
    'en-US': enUSTranslations,
    'zh-TW': zhTWTranslations,
    'ja-JP': jaJPTranslations,
    'ko-KR': koKRTranslations
  }

  return (key, params) => {
    // 检查 translations 对象是否存在
    if (!translations) {
      console.warn('Translations object is not defined');
      return key;
    }

    // 检查当前语言包是否存在
    if (!translations[currentLocale.value]) {
      console.warn(`Locale translations not found for ${currentLocale.value}`);
      return key;
    }

    // 检查键是否存在
    if (translations[currentLocale.value][key] === undefined) {
      console.warn(`Translation key '${key}' not found for locale ${currentLocale.value}`);
      return key;
    }

    let text = translations[currentLocale.value][key];

    // 支持参数插值，如 {count}
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), v);
      }
    }

    return text;
  };
})