import request from '../request';

/**
 * 将 image:// 协议路径转为后端 API 图标路由
 * @param {string} logo - 原始 logo 路径（可能以 image:// 开头）
 * @param {string} storeName - 商店标识名
 * @returns {string} 转换后的 URL
 */
export function resolveStoreLogo(logo, storeName) {
  if (!logo || !logo.startsWith('image://')) return logo || '';
  const relativePath = logo.replace('image://', '');
  const baseURL = request.defaults.baseURL;
  return `${baseURL}/container/store/${storeName}/icon/${relativePath}`;
}
