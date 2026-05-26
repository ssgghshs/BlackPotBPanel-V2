// 文件管理API
import request from '../utils/request'

export function getFileList(params) { 
    return request({
        url: '/file/list',
        method: 'get',
        params
    })
}

// 搜索文件
export function searchFiles(params, data) {
    return request({
        url: '/file/search',
        method: 'post',
        params,
        data
    })
}


export function createDirectory(data) {
    return request({
        url: '/file/create_directory',
        method: 'post',
        data
    })
}

// 计算文件夹大小
export function getDirectorySize(params) {
    return request({
        url: '/file/dirsize',
        method: 'get',
        params
    })
}

export function createFile(data) {
    return request({
        url: '/file/create_file',
        method: 'post',
        data
    })
}

export function uploadFile(data, config = {}) {
    return request({
        url: '/file/upload',
        method: 'post',
        data,
        // 移除显式设置的Content-Type，让浏览器自动处理multipart/form-data格式
        // 这对于正确处理文件上传边界很重要
        timeout: 600000, // 增加到10分钟超时时间，与request.js中的全局设置保持一致
        ...config // 合并额外的配置，包括onUploadProgress
    })
}

export function deleteFile(data) {
    return request({
        url: '/file/delete',
        method: 'post',
        data
    })
}

// 批量删除文件或目录
export function deleteFilesBatch(data) {
    return request({
        url: '/file/delete_batch',
        method: 'post',
        data
    })
}

// 批量压缩
export function compressFilesBatch(data) {
    return request({
        url: '/file/compress_batch',
        method: 'post',
        data
    })
}



// 开发环境下载文件（支持断点续传和认证）- 前端192.168.1.1:5173，后端192.168.1.1:8000
// export function downloadFile(params) {
//     // 检查当前环境，如果是开发环境（端口5173），则直接构建后端8000端口URL
//     const isDev = window.location.port === '5173';
    
//     // 构建下载URL
//     let url;
//     if (isDev) {
//         const protocol = window.location.protocol;
//         const host = window.location.hostname;
//         url = `${protocol}//${host}:8000/file/download?`;
//     } else {
//         // 生产环境URL（当未注释生产环境版本时使用）
//         url = '/api/v2/file/download?';
//     }
    
//     // 构建查询参数
//     const queryParams = new URLSearchParams();
//     if (params.path) {
//         queryParams.append('path', params.path);
//     }
//     if (params.filename) {
//         queryParams.append('filename', params.filename);
//     }
    
//     // 从localStorage获取token并添加到URL
//     const token = localStorage.getItem('access_token');
//     if (token) {
//         queryParams.append('token', token);
//     }
    
//     // 使用window.open直接打开下载链接，实现流式下载
//     // 这样用户可以复制下载链接并在其他浏览器窗口中使用
//     window.open(url + queryParams.toString(), '_blank');
    
//     return { success: true };
// }

// 生产环境下载文件（支持断点续传）- 前端192.168.1.1:5173，后端通过/api/v2代理

export function downloadFile(params) {
    // 构建下载URL
    let url = '/api/v2/file/download?';
    
    // 构建查询参数
    const queryParams = new URLSearchParams();
    if (params.path) {
        queryParams.append('path', params.path);
    }
    if (params.filename) {
        queryParams.append('filename', params.filename);
    }
    
    // 从localStorage获取token并添加到URL
    const token = localStorage.getItem('access_token');
    if (token) {
        queryParams.append('token', token);
    }
    
    // 使用window.open直接打开下载链接，实现流式下载
    // 这样用户可以复制下载链接并在其他浏览器窗口中使用
    window.open(url + queryParams.toString(), '_blank');
    
    return { success: true };
}

export function renameFile(data) {
    return request({
        url: '/file/rename',
        method: 'post',
        data
    })
}

export function changePermissions(data) {
    return request({
        url: '/file/permissions',
        method: 'post',
        data
    })
}

// 批量权限
export function changePermissionsBatch(data) {
    return request({
        url: '/file/permissions_batch',
        method: 'post',
        data
    })
}


export function getFileContent(params) {
    return request({
        url: '/file/content',
        method: 'get',
        params
    })
}

// 保存文件内容
export function saveFileContent(data) {
    return request({
        url: '/file/content',
        method: 'post',
        data
    })
}

export function getImageContent(params) {
    return request({
        url: '/file/image',
        method: 'get',
        params,
        responseType: 'blob'
    })
}

export function moveFileOrDirectory(data) {
    return request({
        url: '/file/move',
        method: 'post',
        data
    })
}

export function copyFileOrDirectory(data) {
    return request({
        url: '/file/copy',
        method: 'post',
        data
    })
}

export function compressFiles(data) {
    return request({
        url: '/file/compress',
        method: 'post',
        data,
        timeout: 300000 // 为压缩操作设置60秒超时时间
    })
}

export function decompressFile(data) {
    return request({
        url: '/file/decompress',
        method: 'post',
        data,
        timeout: 300000 // 为解压操作设置60秒超时时间
    })
}

export function getFileTree(params) {
    return request({
        url: '/file/tree',
        method: 'get',
        params
    })
}

// 添加创建符号链接的接口
export function createSymlink(data) {
    return request({
        url: '/file/create_symlink',
        method: 'post',
        data
    })
}

// 添加远程下载文件的接口
export function downloadRemoteFile(data) {
    return request({
        url: '/file/download_remote',
        method: 'post',
        data,
        timeout: 300000 // 为远程下载设置5分钟超时时间
    })
}

// 添加获取下载进度的接口
export function getDownloadProgress(downloadId) {
    return request({
        url: `/file/download_progress/${downloadId}`,
        method: 'get'
    })
}

// 添加获取下载任务列表的接口
export function getDownloadTasks() {
    return request({
        url: '/file/download_tasks',
        method: 'get'
    })
}

// 添加获取单个下载任务详情的接口
export function getDownloadTask(downloadId) {
    return request({
        url: `/file/download_task/${downloadId}`,
        method: 'get'
    })
}

// 添加取消下载任务并删除记录的接口
export function cancelAndDeleteDownloadTask(downloadId) {
    return request({
        url: `/file/download_task/${downloadId}`,
        method: 'post'
    })
}

// 获取回收站配置
export function getRecycleConfig() {
    return request({
        url: '/system/config/recycle',
        method: 'get'
    })
}

// 更新回收站配置
export function updateRecycleConfig(data) {
    return request({
        url: '/system/config/recycle/update',
        method: 'post',
        data
    })
}

// 清空回收站
export function clearRecycle() {
    return request({
        url: '/file/recycle/clear',
        method: 'post'
    })
}

// 获取回收站文件列表
export function getRecycleFiles(params) {
    return request({
        url: '/file/recycle/list',
        method: 'get',
        params
    })
}

// 恢复回收站文件
export function restoreRecycleFile(data) {
    return request({
        url: '/file/recycle/restore',
        method: 'post',
        data
    })
}

// 批量恢复回收站文件
export function restoreRecycleFilesBatch(data) {
    return request({
        url: '/file/recycle/restore_batch',
        method: 'post',
        data
    })
}

// 删除回收站文件
export function deleteRecycleFile(data) {
    return request({
        url: '/file/recycle/delete',
        method: 'post',
        data
    })
}

// 批量删除回收站文件
export function deleteRecycleFilesBatch(data) {
    return request({
        url: '/file/recycle/delete_batch',
        method: 'post',
        data
    })
}