// 容器管理API
import request from '../utils/request'

// 容器节点管理
export function getContainerNodes(params) {
    return request({
        url: '/container/nodes',
        method: 'get',
        params
    })
}

// 创建Docker节点
export function createContainerNode(data) {
    return request({
        url: '/container/nodes',
        method: 'post',
        data
    })
}

// 获取Docker节点详情
export function getContainerNode(nodeId) {
    return request({
        url: `/container/nodes/${nodeId}`,
        method: 'get'
    })
}

// 更新Docker节点
export function updateContainerNode(nodeId, data) {
    return request({
        url: `/container/nodes/${nodeId}/update`,
        method: 'post',
        data
    })
}

// 删除Docker节点
export function deleteContainerNode(nodeId) {
    return request({
        url: `/container/nodes/${nodeId}/delete`,
        method: 'post'
    })
}

// 获取Docker节点状态
export function getContainerNodeStatus(nodeId) {
    return request({
        url: `/container/nodes/${nodeId}/status`,
        method: 'get'
    })
}

// 获取Docker节点详细信息
export function getContainerNodeInfo(nodeId) {
    return request({
        url: `/container/nodes/${nodeId}/info`,
        method: 'get',
    })
}

// 获取Docker节点资源限制
export function getContainerNodeResourcesLimit(nodeId) {
    return request({
        url: `/container/nodes/${nodeId}/info/limit`,
        method: 'get',
    })
}


// 容器路由

// 获取节点容器列表
export function getNodeContainers(nodeId) {
    return request({
        url: `/container/nodes/${nodeId}/containers`,
        method: 'get',
    })
}

// 创建容器
export function createContainer(nodeId, data) {
    return request({
        url: `/container/nodes/${nodeId}/containers/create`,
        method: 'post',
        data,
    })
}



// 获取容器详细信息
export function getContainerInspect(nodeId, containerId) {
    return request({
        url: `/container/nodes/${nodeId}/containers/${containerId}/inspect`,
        method: 'get',
    })
}

// 获取容器日志
export function getContainerLogs(nodeId, containerId, params) {
    return request({
        url: `/container/nodes/${nodeId}/containers/${containerId}/logs`,
        method: 'get',
        params,
    })
}

// 启动容器
export function startContainer(nodeId, containerId) {
    return request({
        url: `/container/nodes/${nodeId}/containers/${containerId}/start`,
        method: 'post',
    })
}

// 停止容器
export function stopContainer(nodeId, containerId, params) {
    return request({
        url: `/container/nodes/${nodeId}/containers/${containerId}/stop`,
        method: 'post',
        params,
    })
}

// 暂停容器
export function pauseContainer(nodeId, containerId) {
    return request({
        url: `/container/nodes/${nodeId}/containers/${containerId}/pause`,
        method: 'post',
    })
}

// 恢复容器
export function unpauseContainer(nodeId, containerId) {
    return request({
        url: `/container/nodes/${nodeId}/containers/${containerId}/unpause`,
        method: 'post',
    })
}

// 重启容器
export function restartContainer(nodeId, containerId, params) {
    return request({
        url: `/container/nodes/${nodeId}/containers/${containerId}/restart`,
        method: 'post',
        params,
    })
}

// 删除容器
export function deleteContainer(nodeId, containerId, params) {
    return request({
        url: `/container/nodes/${nodeId}/containers/${containerId}/delete`,
        method: 'post',
        params,
    })
}

// 获取容器资源占用信息
export function getContainerStats(nodeId, containerId) {
    return request({
        url: `/container/nodes/${nodeId}/containers/${containerId}/stats`,
        method: 'get',
    })
}


// 获取容器终端连接信息
export function getContainerTerminal(nodeId, containerId, data) {
    return request({
        url: `/container/nodes/${nodeId}/containers/${containerId}/terminal`,
        method: 'post',
        data,
    })
}

// 提交容器镜像
export function commitContainer(nodeId, containerId, data) {
    return request({
        url: `/container/nodes/${nodeId}/containers/${containerId}/commit`,
        method: 'post',
        data,
    })
}



// 获取节点镜像列表
export function getImages(nodeId, params) {
    return request({
        url: `/container/nodes/${nodeId}/images`,
        method: 'get',
        params,
    })
}

// 获取Docker节点镜像选项列表
export function getImageOptions(nodeId) {
    return request({
        url: `/container/nodes/${nodeId}/images/list`,
        method: 'get',
    })
}

// 获取镜像详细信息
export function getImageDetail(nodeId, imageId, params) {
    return request({
        url: `/container/nodes/${nodeId}/images/${imageId}/inspect`,
        method: 'get',
        params,
    })
}

// 删除指定镜像
export function deleteImage(nodeId, imageId, data) {
    return request({
        url: `/container/nodes/${nodeId}/images/${imageId}/delete`,
        method: 'post',
        data,
    })
}

// 导入镜像
export function importImage(nodeId, data) {
    return request({
        url: `/container/nodes/${nodeId}/images/import`,
        method: 'post',
        data,
    })
}

// 获取导入镜像操作日志
export function getImportOperationLog(operationId) {
    return request({
        url: `/container/operations/${operationId}/log/read`,
        method: 'get',
    })
}

// 获取镜像操作日志
export function getOperationLog(operationId) {
    return request({
        url: `/container/operations/${operationId}/log/read`,
        method: 'get',
    })
}

// 导出镜像
export function exportImage(nodeId, data) {
    return request({
        url: `/container/nodes/${nodeId}/images/export`,
        method: 'post',
        data,
        timeout: 600000, // 10分钟超时
    })
}

// 清理未使用的镜像
export function pruneImages(nodeId, data) {
    return request({
        url: `/container/nodes/${nodeId}/images/prune`,
        method: 'post',
        data,
    })
}


// 拉取镜像
export function pullImage(nodeId, data) {
    return request({
        url: `/container/nodes/${nodeId}/images/pull`,
        method: 'post',
        data,
    }) 
}

// 取消拉取镜像
export function cancelPullImage(nodeId, data) {
    return request({
        url: `/container/nodes/${nodeId}/images/pull/cancel`,
        method: 'post',
        data,
    })
}

// 构建镜像
export function buildImage(nodeId, data) {
    return request({
        url: `/container/nodes/${nodeId}/images/build`,
        method: 'post',
        data,
    })
}

// 清除镜像缓存
export function pruneImagesCache(nodeId, data) {
    return request({
        url: `/container/nodes/${nodeId}/images/cache/prune`,
        method: 'post',
        data,
    })
}

// 管理镜像标签
export function manageImageTags(nodeId, imageId, data) {
    return request({
        url: `/container/nodes/${nodeId}/images/${imageId}/tag`,
        method: 'post',
        data,
    })
}


// 获取节点网络列表
export function getNetworks(nodeId, params) {
    return request({
        url: `/container/nodes/${nodeId}/networks`,
        method: 'get',
        params,
    })
}

// 获取Docker节点网络选项列表
export function getNetworkOptions(nodeId) {
    return request({
        url: `/container/nodes/${nodeId}/networks/list`,
        method: 'get',
    })
}

// 获取网络详细信息
export function getNetworkDetail(nodeId, networkId, params) {
    return request({
        url: `/container/nodes/${nodeId}/networks/${networkId}/inspect`,
        method: 'get',
        params,
    })
}

// 创建网卡
export function createNetwork(nodeId, data) {
    return request({
        url: `/container/nodes/${nodeId}/networks/create`,
        method: 'post',
        data,
    })
}

// 清理未使用的网络
export function pruneNetworks(nodeId, params) {
    return request({
        url: `/container/nodes/${nodeId}/networks/prune`,
        method: 'post',
        params,
    })
}

// 删除指定网络
export function deleteNetwork(nodeId, networkId, params) {
    return request({
        url: `/container/nodes/${nodeId}/networks/${networkId}/delete`,
        method: 'post',
        params,
    })
}


// 获取节点存储卷列表
export function getVolumes(nodeId, params) {
    return request({
        url: `/container/nodes/${nodeId}/volumes`,
        method: 'get',
        params,
    })
}

// 获取Docker节点存储卷选项列表
export function getVolumeOptions(nodeId) {
    return request({
        url: `/container/nodes/${nodeId}/volumes/list`,
        method: 'get',
    })
}

// 获取存储卷详细信息
export function getVolumeDetail(nodeId, volumeId, params) {
    return request({
        url: `/container/nodes/${nodeId}/volumes/${volumeId}/inspect`,
        method: 'get',
        params,
    })
}

// 创建存储卷
export function createVolume(nodeId, data) {
    return request({
        url: `/container/nodes/${nodeId}/volumes/create`,
        method: 'post',
        data,
    })
}

// 删除指定存储卷
export function deleteVolume(nodeId, volumeId, params) {
    return request({
        url: `/container/nodes/${nodeId}/volumes/${volumeId}/delete`,
        method: 'post',
        params,
    })
}

// 清理未使用的存储卷
export function pruneVolumes(nodeId, params) {
    return request({
        url: `/container/nodes/${nodeId}/volumes/prune`,
        method: 'post',
        params,
    })
}


// 获取compose服务列表
export function getComposeList(nodeId, params) {
    return request({
        url: `/container/nodes/${nodeId}/composelist`,
        method: 'get',
        params,
    })
}


// 获取Compose项目容器列表
export function getComposeProjectContainers(nodeId, projectName) {
    return request({
        url: `/container/nodes/${nodeId}/compose/${projectName}/containers`,
        method: 'get',
    })
}

// 获取Compose项目日志
export function getComposeProjectLogs(nodeId, projectName, params) {
    return request({
        url: `/container/nodes/${nodeId}/compose/${projectName}/logs`,
        method: 'get',
        params,
    })
}

// 启动Compose项目
export function startComposeProject(nodeId, projectName) {
    return request({
        url: `/container/nodes/${nodeId}/compose/${projectName}/start`,
        method: 'post',
    })
}

// 停止Compose项目
export function stopComposeProject(nodeId, projectName) {
    return request({
        url: `/container/nodes/${nodeId}/compose/${projectName}/stop`,
        method: 'post',
    })
}

// 创建Compose项目
export function createComposeProject(nodeId, data) {
    return request({
        url: `/container/nodes/${nodeId}/compose/create`,
        method: 'post',
        data,
        timeout: 600000, // 10分钟超时
    })
}

// 删除Compose项目
export function deleteComposeProject(nodeId, projectName) {
    return request({
        url: `/container/nodes/${nodeId}/compose/${projectName}/delete`,
        method: 'post',
    })
}

// 重启Compose项目
export function restartComposeProject(nodeId, projectName) {
    return request({
        url: `/container/nodes/${nodeId}/compose/${projectName}/restart`,
        method: 'post',
        timeout: 60000, // 10分钟超时
    })
}

// 检测本地Docker状态
export function checkLocalDockerStatus() {
    return request({
        url: '/container/local-docker/status',
        method: 'get',
    })
}
