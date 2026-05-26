from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
import docker
import asyncio
import threading
import time
import os
import uuid
import logging
import gzip
import random
import string
from concurrent.futures import ThreadPoolExecutor
from app.container.models import DockerNode
from datetime import datetime
import re
from app.container.schemas import (
    ImageListResponse, ImageSummary, ImageDetailResponse, ContainerOperationResponse,
    ImageImportRequest, ImageImportResponse, LogContentResponse, ImageExportRequest,
    ImageExportResponse, ImagePruneRequest, ImagePullRequest, ImagePullResponse,
    ImageBuildRequest, ImageBuildResponse, ImageCachePruneRequest, ImageCachePruneResponse,
    ImageOptionListResponse, ImageOption, ImageTagRequest, ImageTagResponse)

# 获取logger实例
logger = logging.getLogger(__name__)


class DockerImageService:
    """Docker镜像服务类，处理Docker镜像相关操作"""
    
    # 线程池执行器，用于执行同步的Docker操作
    _executor = ThreadPoolExecutor(max_workers=5)
    
    # 存储正在进行的操作状态
    _operations = {}
    
    # 日志目录路径
    _LOG_DIR = "/opt/blackpotbpanel-v2/server/tmp/containerlog"
    
    @classmethod
    def _ensure_log_dir(cls):
        """确保日志目录存在"""
        if not os.path.exists(cls._LOG_DIR):
            try:
                os.makedirs(cls._LOG_DIR, exist_ok=True)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"创建日志目录失败: {str(e)}")
    
    @classmethod
    def _ensure_export_dir(cls, export_path):
        """确保导出目录存在"""
        if not os.path.exists(export_path):
            try:
                os.makedirs(export_path, exist_ok=True)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"创建导出目录失败: {str(e)}")
    
    @classmethod
    async def import_image(cls, db: AsyncSession, node_id: int, import_data: ImageImportRequest) -> ImageImportResponse:
        """
        异步导入Docker镜像
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            import_data: 镜像导入数据
            
        Returns:
            ImageImportResponse: 镜像导入响应
        """
        # 确保node_id为整数类型
        node_id = int(node_id)
        
        # 获取Docker节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        
        # 验证镜像文件是否存在
        if not os.path.exists(import_data.image_path):
            raise HTTPException(status_code=404, detail=f"镜像文件不存在: {import_data.image_path}")
        
        # 确保日志目录存在
        cls._ensure_log_dir()
        
        # 生成操作ID和日志文件路径
        operation_id = str(uuid.uuid4())
        log_file_path = os.path.join(cls._LOG_DIR, f"import_{operation_id}.log")
        
        # 保存操作状态
        cls._operations[operation_id] = {
            'node_id': node_id,
            'image_path': import_data.image_path,
            'status': 'running',
            'start_time': time.time(),
            'log_file': log_file_path
        }
        
        # 获取节点连接配置
        config = node.connection_config
        
        # 启动异步导入线程
        threading.Thread(
            target=cls._import_image_sync,
            args=(config, import_data.image_path, import_data.tag, import_data.quiet, log_file_path, operation_id)
        ).start()
        
        # 返回操作信息
        return ImageImportResponse(
            operation_id=operation_id,
            message="镜像导入操作已启动",
            log_file_path=log_file_path,
            success=True
        )
    
    @classmethod
    def _import_image_sync(cls, config: Dict[str, Any], image_path: str, tag: Optional[str], quiet: bool, log_file_path: str, operation_id: str):
        """
        同步导入镜像的方法（在线程中执行）
        """
        client = None
        try:
            # 写入日志 - 准备日志文件
            with open(log_file_path, 'w', encoding='utf-8') as f:
                # 保持日志文件为空初始状态，后续将写入实际的加载信息
                pass
            
            # 创建Docker客户端
            if 'tls' in config:
                # 处理TLS配置
                tls_kwargs = {}
                
                # 直接使用证书文件路径
                if 'ca_cert_path' in config['tls']:
                    tls_kwargs['ca_cert'] = config['tls']['ca_cert_path']
                
                if 'client_cert_path' in config['tls'] and 'client_key_path' in config['tls']:
                    tls_kwargs['client_cert'] = (config['tls']['client_cert_path'], config['tls']['client_key_path'])
                
                tls_kwargs['verify'] = True
                tls_config = docker.tls.TLSConfig(**tls_kwargs)
                client = docker.DockerClient(
                    base_url=config['base_url'],
                    tls=tls_config
                )
            else:
                client = docker.DockerClient(base_url=config['base_url'])
            
            # 模拟Docker load命令的输出格式
            # 执行导入并记录日志
            try:
                # 执行Docker导入操作并记录日志
                def do_docker_load():
                    # 先获取导入前的镜像列表，用于后续比较
                    before_images = set(img.id for img in client.images.list())
                    
                    # 记录开始导入信息 - 添加时间戳
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                        log_f.write(f"[{timestamp}] Start importing the image...\n")
                        log_f.flush()  # 强制刷新到磁盘
                    
                    # 检查文件是否为压缩格式
                    is_compressed = image_path.endswith('.tar.gz') or image_path.endswith('.tgz')
                    
                    # 记录导入准备信息 - 添加时间戳
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                        log_f.write(f"[{timestamp}] Parsing the image file: {os.path.basename(image_path)}\n")
                        if is_compressed:
                            log_f.write(f"[{timestamp}] Detected compressed file format, will decompress...\n")
                        log_f.write(f"[{timestamp}] Extracting image metadata...\n")
                        log_f.flush()  # 强制刷新到磁盘
                    
                    # 记录开始导入的消息 - 添加时间戳并改进格式
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    image_size_mb = os.path.getsize(image_path) / (1024 * 1024)
                    image_size_gb = os.path.getsize(image_path) / (1024 * 1024 * 1024)
                    
                    # 选择合适的单位显示文件大小
                    size_str = f"{image_size_mb:.2f}MB" if image_size_mb < 1000 else f"{image_size_gb:.2f}GB"
                    
                    with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                        log_f.write(f"[{timestamp}] Performing the actual image import operation...\n")
                        log_f.write(f"[{timestamp}] Image file information: {os.path.basename(image_path)} ({size_str})\n")
                        log_f.write(f"[{timestamp}] Please wait while processing the image data...\n")
                        log_f.flush()  # 强制刷新到磁盘
                    
                    # 导入镜像 - 注意：根据Docker SDK版本不同，这里使用标准的load方法
                    import_kwargs = {}
                    if tag:
                        import_kwargs['tag'] = tag
                    
                    # 执行实际的导入操作
                    # 虽然Docker SDK不直接支持导入进度回调，但我们可以通过文件分块读取和模拟进度
                    file_size = os.path.getsize(image_path)
                    
                    # 创建一个模拟的进度文件读取器
                    class ProgressFileReader:
                        def __init__(self, file_obj, total_size, log_path, chunk_size=1024*1024):
                            self.file_obj = file_obj
                            self.total_size = total_size
                            self.read_size = 0
                            self.log_path = log_path
                            self.chunk_size = chunk_size
                            self.last_log_time = 0
                            self.log_interval = 0.5  # 每0.5秒更新一次日志
                        
                        def read(self, size):
                            data = self.file_obj.read(size)
                            if data:
                                self.read_size += len(data)
                                # 定期更新进度日志
                                current_time = time.time()
                                if current_time - self.last_log_time > self.log_interval:
                                    progress_percent = (self.read_size / self.total_size) * 100
                                    # 模拟1Panel的进度显示格式
                                    progress_str = f"Importing [{os.path.basename(image_path)}] --- {progress_percent:.2f}%"
                                    with open(self.log_path, 'a', encoding='utf-8', buffering=1) as log_f:
                                        # 更新最后一行进度信息
                                        # 由于Python无法轻松更新文件中的特定行，我们只是追加新的进度行
                                        # 前端可以读取最后几行并显示最新的进度
                                        log_f.write(f"{progress_str}\n")
                                        log_f.flush()
                                    self.last_log_time = current_time
                            return data
                    
                    # 根据文件格式选择不同的处理方式
                    if is_compressed:
                        # 处理压缩文件
                        with open(image_path, 'rb') as f:
                            # 使用gzip解压
                            with gzip.open(f, 'rb') as gzf:
                                # 使用进度读取器包装gzip文件对象
                                progress_reader = ProgressFileReader(gzf, file_size, log_file_path)
                                result = client.images.load(progress_reader, **import_kwargs)
                    else:
                        # 处理普通tar文件
                        with open(image_path, 'rb') as f:
                            # 使用进度读取器
                            progress_reader = ProgressFileReader(f, file_size, log_file_path)
                            result = client.images.load(progress_reader, **import_kwargs)
                        
                        # 导入完成后更新日志 - 模拟1Panel的完成状态显示
                        with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            log_f.write(f"[{timestamp}] Import complete [{os.path.basename(image_path)}] --- 100.00%\n")
                            log_f.write(f"[{timestamp}] Image data processing completed, loading the image...\n")
                            log_f.flush()  # 强制刷新到磁盘
                    
                    # 记录导入完成信息 - 模拟1Panel的完成日志格式
                    with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log_f.write(f"[{timestamp}] Image layer loading completed\n")
                        log_f.write(f"[{timestamp}] Updating image metadata...\n")
                        log_f.write(f"[{timestamp}] Optimizing image storage...\n")
                        log_f.flush()  # 强制刷新到磁盘
                    
                    # 获取导入后的镜像列表，找出新导入的镜像
                    after_images = client.images.list()
                    new_images = [img for img in after_images if img.id not in before_images]
                    
                    # 处理新导入的镜像
                    if new_images:
                        imported_image = new_images[0]
                        
                        # 如果没有指定标签，但导入的镜像没有标签，尝试从文件名恢复原始标签
                        if not tag and not imported_image.tags:
                            try:
                                # 从文件名中提取可能的原始标签信息
                                file_name = os.path.basename(image_path)
                                # 移除文件扩展名
                                if file_name.endswith('.tar.gz') or file_name.endswith('.tgz'):
                                    base_name = file_name.rsplit('.', 2)[0]
                                elif file_name.endswith('.tar'):
                                    base_name = file_name.rsplit('.', 1)[0]
                                else:
                                    base_name = file_name
                                
                                # 尝试恢复原始标签格式（将_替换回/和:）
                                # 查找最后一个_后面的部分作为tag部分（例如latest）
                                parts = base_name.rsplit('_', 1)
                                if len(parts) >= 2 and not any(c.isupper() for c in parts[1]):
                                    # 如果第二部分看起来像tag（没有大写字母，可能是latest等）
                                    repo_part = parts[0].replace('_', '/')
                                    tag_part = parts[1]
                                    restored_tag = f"{repo_part}:{tag_part}"
                                    
                                    # 为镜像添加标签
                                    imported_image.tag(restored_tag)
                                    
                                    # 记录标签恢复信息
                                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                                        log_f.write(f"[{timestamp}] Restored original tag: {restored_tag}\n")
                                        log_f.flush()
                            except Exception as e:
                                # 恢复标签失败不影响导入流程
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                                    log_f.write(f"[{timestamp}] Failed to restore original tag: {str(e)}\n")
                                    log_f.flush()
                        
                        # 返回处理后的镜像
                        return imported_image
                    # 如果指定了标签，尝试获取该标签的镜像
                    elif tag:
                        try:
                            return client.images.get(tag)
                        except:
                            # 如果找不到，返回第一个导入结果
                            pass
                    
                    # 返回导入结果
                    return result[0] if result and len(result) > 0 else None
                
                # 执行导入并记录进度
                result = do_docker_load()
                
                # 记录加载完成的信息 - 改进格式与整个日志风格保持一致
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                    log_f.write(f"[{timestamp}] Image import operation completed\n")
                    if result:
                        # result现在是单个镜像对象
                        if result.tags:
                            # 使用第一个标签作为Loaded image的输出
                            log_f.write(f"[{timestamp}] Loaded image: {result.tags[0]}\n")
                        else:
                            # 如果没有标签，使用镜像ID
                            log_f.write(f"[{timestamp}] Loaded image: {result.id[:12]}...\n")
                    else:
                        log_f.write(f"[{timestamp}] Loaded image: {os.path.basename(image_path)}\n")
                    # 添加操作耗时信息
                    operation_time = time.time() - cls._operations[operation_id]['start_time']
                    log_f.write(f"[{timestamp}] Operation time: {operation_time:.2f} seconds\n")
                    log_f.flush()  # 强制刷新到磁盘
            except Exception as docker_error:
                # 如果实际导入失败，覆盖模拟的成功输出
                with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                    log_f.write(f"Error: {str(docker_error)}\n")
                    log_f.flush()  # 强制刷新到磁盘
                raise  # 重新抛出异常以便上层处理
            
            # 更新操作状态
            cls._operations[operation_id]['status'] = 'completed'
            cls._operations[operation_id]['end_time'] = time.time()
            
        except Exception as e:
            # 记录错误
            with open(log_file_path, 'a', encoding='utf-8') as f:
                # 确保错误信息格式清晰
                f.write(f"Error: {str(e)}\n")
                f.flush()  # 强制刷新到磁盘
            
            # 更新操作状态为失败
            cls._operations[operation_id]['status'] = 'failed'
            cls._operations[operation_id]['error'] = str(e)
            cls._operations[operation_id]['end_time'] = time.time()
        finally:
            # 关闭客户端
            if client:
                client.close()
    
    @classmethod
    async def get_operation_log(cls, operation_id: str) -> LogContentResponse:
        """
        获取操作日志内容
        
        Args:
            operation_id: 操作ID
            
        Returns:
            LogContentResponse: 日志内容响应
            
        注意：当操作已完成（状态为completed或failed）时，会在返回日志内容后自动清理日志文件
        """
        # 检查操作是否存在
        if operation_id not in cls._operations:
            log_file_path = os.path.join(cls._LOG_DIR, f"import_{operation_id}.log")
            if not os.path.exists(log_file_path):
                alt_log = os.path.join(cls._LOG_DIR, f"pull_{operation_id}.log")
                if os.path.exists(alt_log):
                    log_file_path = alt_log
                else:
                    alt_log2 = os.path.join(cls._LOG_DIR, f"build_{operation_id}.log")
                    if os.path.exists(alt_log2):
                        log_file_path = alt_log2
                    else:
                        raise HTTPException(status_code=404, detail="操作ID不存在")
        else:
            log_file_path = cls._operations[operation_id]['log_file']
        
        # 检查日志文件是否存在
        if not os.path.exists(log_file_path):
            return LogContentResponse(
                operation_id=operation_id,
                log_content="",
                log_file_exists=False,
                is_complete=False
            )
        
        # 读取日志内容
        try:
            # 使用行缓冲模式读取文件，确保获取最新内容
            with open(log_file_path, 'r', encoding='utf-8', buffering=1) as f:
                log_content = f.read()
            
            # 检查操作是否完成
            is_complete = False
            if operation_id in cls._operations:
                is_complete = cls._operations[operation_id]['status'] in ['completed', 'failed']
            
            # 构造响应
            response = LogContentResponse(
                operation_id=operation_id,
                log_content=log_content,
                log_file_exists=True,
                is_complete=is_complete
            )
            
            # 当操作已完成时，清理日志文件和操作记录
            if is_complete:
                # 删除日志文件
                try:
                    if os.path.exists(log_file_path):
                        os.remove(log_file_path)
                        logger.info(f"Log file deleted: {log_file_path}")
                except Exception as e:
                    # 记录删除失败的错误，但不影响响应
                    logger.error(f"Delete log file failed: {str(e)}")
                
                # 从操作记录中移除
                if operation_id in cls._operations:
                    del cls._operations[operation_id]
                    logger.info(f"Operation record cleaned: {operation_id}")
            
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Read log file failed: {str(e)}")
    
    @classmethod
    async def get_images(cls, db: AsyncSession, node_id: int) -> ImageListResponse:
        """
        获取指定Docker节点上的镜像列表
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            
        Returns:
            包含镜像列表和总数的响应对象
        """
        # 确保node_id为整数类型
        node_id = int(node_id)
        
        # 获取Docker节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来获取镜像列表
            def get_images_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 处理TLS配置
                        tls_kwargs = {}
                        
                        # 直接使用证书文件路径
                        if 'ca_cert_path' in config['tls']:
                            tls_kwargs['ca_cert'] = config['tls']['ca_cert_path']
                        
                        if 'client_cert_path' in config['tls'] and 'client_key_path' in config['tls']:
                            tls_kwargs['client_cert'] = (config['tls']['client_cert_path'], config['tls']['client_key_path'])
                        
                        tls_kwargs['verify'] = True
                        tls_config = docker.tls.TLSConfig(**tls_kwargs)
                        client = docker.DockerClient(
                            base_url=config['base_url'],
                            tls=tls_config
                        )
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    
                    # 获取所有镜像
                    images = client.images.list(all=False)
                    
                    # 获取所有容器信息，用于检查镜像是否被使用
                    containers = client.containers.list(all=True)
                    
                    # 创建一个集合来存储被使用的镜像ID
                    used_image_ids = set()
                    
                    # 遍历所有容器，收集使用的镜像ID
                    for container in containers:
                        container_info = container.attrs
                        container_image_id = container_info.get('Image', '')
                        if container_image_id:
                            used_image_ids.add(container_image_id)
                    
                    # 转换为响应格式
                    image_list = []
                    for image in images:
                        # 提取镜像标签
                        tags = image.tags if image.tags else []
                        
                        # 提取镜像ID和短ID
                        image_id = image.id
                        image_id_short = image_id.split(':')[1][:12] if ':' in image_id else image_id[:12]
                        
                        # 保持原始大小（字节）
                        size = image.attrs.get('Size', 0)
                        
                        # 处理创建时间
                        created = image.attrs.get('Created', 0)
                        if isinstance(created, (int, float)):
                            created_dt = datetime.fromtimestamp(created)
                        else:
                            try:
                                created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                            except:
                                created_dt = datetime.now()
                        
                        # 格式化为带时区的ISO格式
                        createdAt = created_dt.strftime('%Y-%m-%dT%H:%M:%S%z')
                        if len(createdAt) == 19:
                            # 如果没有时区信息，添加东八区
                            createdAt = created_dt.strftime('%Y-%m-%dT%H:%M:%S+08:00')
                        elif len(createdAt) == 22:
                            # 转换 +0800 格式为 +08:00 格式
                            createdAt = f"{createdAt[:-2]}:{createdAt[-2:]}"
                        
                        # 检查镜像是否被使用
                        is_used = image_id in used_image_ids
                        
                        # 构建镜像摘要信息
                        image_summary = ImageSummary(
                            id=image_id,
                            id_short=image_id_short,
                            createdAt=createdAt,
                            isUsed=is_used,  # 根据实际使用情况设置
                            tags=tags,
                            size=size
                        )
                        image_list.append(image_summary)
                    
                    return image_list
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"获取镜像列表失败: {str(e)}")
                finally:
                    # 确保客户端连接关闭
                    if 'client' in locals():
                        client.close()
            
            # 异步执行获取镜像列表
            image_list = await loop.run_in_executor(cls._executor, get_images_sync)
            
            # 返回镜像列表响应
            return ImageListResponse(
                items=image_list,
                total=len(image_list)
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取镜像列表时发生错误: {str(e)}")
    
    @classmethod
    async def get_image_options(cls, db: AsyncSession, node_id: int) -> ImageOptionListResponse:
        """
        获取Docker节点上的镜像选项列表
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            
        Returns:
            ImageOptionListResponse: 镜像选项列表响应
        """
        # 确保node_id为整数类型
        node_id = int(node_id)
        
        # 获取Docker节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来获取镜像选项列表
            def get_image_options_sync():
                client = None
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 处理TLS配置
                        tls_kwargs = {}
                        
                        # 直接使用证书文件路径
                        if 'ca_cert_path' in config['tls']:
                            tls_kwargs['ca_cert'] = config['tls']['ca_cert_path']
                        
                        if 'client_cert_path' in config['tls'] and 'client_key_path' in config['tls']:
                            tls_kwargs['client_cert'] = (config['tls']['client_cert_path'], config['tls']['client_key_path'])
                        
                        tls_kwargs['verify'] = True
                        tls_config = docker.tls.TLSConfig(**tls_kwargs)
                        client = docker.DockerClient(
                            base_url=config['base_url'],
                            tls=tls_config
                        )
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    
                    # 获取所有镜像
                    images = client.images.list()
                    
                    # 提取镜像标签作为选项
                    options = []
                    seen_tags = set()  # 用于去重
                    
                    for image in images:
                        if image.tags:
                            for tag in image.tags:
                                if tag not in seen_tags:
                                    seen_tags.add(tag)
                                    options.append(ImageOption(option=tag))
                    
                    # 按标签名称排序
                    options.sort(key=lambda x: x.option)
                    
                    return options
                finally:
                    # 关闭客户端
                    if client:
                        client.close()
            
            # 异步执行获取镜像选项列表
            options = await loop.run_in_executor(cls._executor, get_image_options_sync)
            
            # 返回镜像选项列表响应
            return ImageOptionListResponse(data=options)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取镜像选项列表失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"获取镜像选项列表失败: {str(e)}")
    
    @classmethod
    async def get_image_detail(cls, db: AsyncSession, node_id: int, image_id: str) -> ImageDetailResponse:
        """
        获取指定Docker节点上指定镜像的详细信息
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            image_id: 镜像ID或标签
            
        Returns:
            镜像详细信息响应对象
        """
        # 确保node_id为整数类型
        node_id = int(node_id)
        
        # 获取Docker节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来获取镜像详细信息
            def get_image_detail_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 处理TLS配置
                        tls_kwargs = {}
                        
                        # 直接使用证书文件路径
                        if 'ca_cert_path' in config['tls']:
                            tls_kwargs['ca_cert'] = config['tls']['ca_cert_path']
                        
                        if 'client_cert_path' in config['tls'] and 'client_key_path' in config['tls']:
                            tls_kwargs['client_cert'] = (config['tls']['client_cert_path'], config['tls']['client_key_path'])
                        
                        tls_kwargs['verify'] = True
                        tls_config = docker.tls.TLSConfig(**tls_kwargs)
                        client = docker.DockerClient(
                            base_url=config['base_url'],
                            tls=tls_config
                        )
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    
                    # 获取镜像详细信息
                    image = client.images.get(image_id)
                    
                    # 提取镜像标签
                    tags = image.tags if image.tags else []
                    
                    # 提取镜像ID和短ID
                    image_id_full = image.id
                    image_id_short = image_id_full.split(':')[1][:12] if ':' in image_id_full else image_id_full[:12]
                    
                    # 保持原始大小（字节）
                    size = image.attrs.get('Size', 0)
                    
                    # 处理创建时间
                    created = image.attrs.get('Created', 0)
                    if isinstance(created, (int, float)):
                        created_dt = datetime.fromtimestamp(created)
                    else:
                        try:
                            created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        except:
                            created_dt = datetime.now()
                    
                    # 格式化为带时区的ISO格式
                    createdAt = created_dt.strftime('%Y-%m-%dT%H:%M:%S%z')
                    if len(createdAt) == 19:
                        # 如果没有时区信息，添加东八区
                        createdAt = created_dt.strftime('%Y-%m-%dT%H:%M:%S+08:00')
                    elif len(createdAt) == 22:
                        # 转换 +0800 格式为 +08:00 格式
                        createdAt = f"{createdAt[:-2]}:{createdAt[-2:]}"
                    
                    # 获取所有容器信息，用于检查镜像是否被使用
                    containers = client.containers.list(all=True)
                    
                    # 创建一个集合来存储被使用的镜像ID
                    used_image_ids = set()
                    
                    # 遍历所有容器，收集使用的镜像ID
                    for container in containers:
                        container_info = container.attrs
                        container_image_id = container_info.get('Image', '')
                        if container_image_id:
                            used_image_ids.add(container_image_id)
                    
                    # 检查当前镜像是否被使用
                    is_used = image_id_full in used_image_ids
                    
                    # 构建镜像详细信息响应
                    image_detail = ImageDetailResponse(
                        id=image_id_full,
                        id_short=image_id_short,
                        createdAt=createdAt,
                        isUsed=is_used,  # 根据实际使用情况设置
                        tags=tags,
                        size=size,
                        repo_digests=image.attrs.get('RepoDigests', []),
                        parent_id=image.attrs.get('Parent', '<none>'),
                        os=image.attrs.get('Os', '<unknown>'),
                        architecture=image.attrs.get('Architecture', '<unknown>'),
                        container_config=image.attrs.get('ContainerConfig', {}),
                        config=image.attrs.get('Config', {}),
                        graph_driver=image.attrs.get('GraphDriver', {})
                    )
                    
                    return image_detail
                except docker.errors.ImageNotFound:
                    raise HTTPException(status_code=404, detail="镜像不存在")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"获取镜像详细信息失败: {str(e)}")
                finally:
                    # 确保客户端连接关闭
                    if 'client' in locals():
                        client.close()
            
            # 异步执行获取镜像详细信息
            image_detail = await loop.run_in_executor(cls._executor, get_image_detail_sync)
            
            return image_detail
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"获取镜像详细信息时发生错误: {str(e)}")
    

    
    @classmethod
    async def delete_image(cls, db: AsyncSession, node_id: int, image_id: str, force: bool = False) -> ContainerOperationResponse:
        """
        删除指定Docker节点上的指定镜像
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            image_id: 镜像ID或标签
            force: 是否强制删除被使用的镜像
            
        Returns:
            操作响应对象
        """
        # 确保node_id为整数类型
        node_id = int(node_id)
        
        # 获取Docker节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来删除镜像
            def delete_image_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 处理TLS配置
                        tls_kwargs = {}
                        
                        # 直接使用证书文件路径
                        if 'ca_cert_path' in config['tls']:
                            tls_kwargs['ca_cert'] = config['tls']['ca_cert_path']
                        
                        if 'client_cert_path' in config['tls'] and 'client_key_path' in config['tls']:
                            tls_kwargs['client_cert'] = (config['tls']['client_cert_path'], config['tls']['client_key_path'])
                        
                        tls_kwargs['verify'] = True
                        tls_config = docker.tls.TLSConfig(**tls_kwargs)
                        client = docker.DockerClient(
                            base_url=config['base_url'],
                            tls=tls_config
                        )
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    
                    # 检查镜像是否存在
                    try:
                        image = client.images.get(image_id)
                    except docker.errors.ImageNotFound:
                        raise HTTPException(status_code=404, detail="镜像不存在")
                    
                    # 检查镜像是否被使用
                    containers = client.containers.list(all=True)
                    image_id_full = image.id
                    used_by_containers = []
                    
                    for container in containers:
                        container_info = container.attrs
                        container_image_id = container_info.get('Image', '')
                        if container_image_id == image_id_full:
                            used_by_containers.append({
                                'id': container.id[:12],
                                'name': container.name
                            })
                    
                    # 如果镜像被使用且不强制删除，则抛出异常
                    if used_by_containers and not force:
                        container_names = [f"{c['name']} ({c['id']})" for c in used_by_containers]
                        raise HTTPException(
                            status_code=400,
                            detail=f"镜像正在被以下容器使用，请先删除这些容器或使用强制删除选项: {', '.join(container_names)}"
                        )
                    
                    # 删除镜像
                    client.images.remove(image=image_id, force=force)
                    
                    # 返回操作响应
                    return ContainerOperationResponse(
                        success=True,
                        message="镜像删除成功",
                        data={
                            "image_id": image_id,
                            "force": force
                        },
                        container_id="",  # 镜像操作不需要container_id，设为空字符串
                        container_name="",  # 镜像操作不需要container_name，设为空字符串
                        operation="delete_image"  # 指定操作类型
                    )
                    
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"删除镜像失败: {str(e)}")
                finally:
                    # 确保客户端连接关闭
                    if 'client' in locals():
                        client.close()
            
            # 异步执行删除镜像
            result = await loop.run_in_executor(cls._executor, delete_image_sync)
            
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"删除镜像时发生错误: {str(e)}")
    
    @classmethod
    async def prune_images(cls, db: AsyncSession, node_id: int, prune_request: Optional[ImagePruneRequest] = None) -> Dict[str, Any]:
        """
        清理未被使用的Docker镜像
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            prune_request: 镜像清理请求参数，其中dangling字段支持：
                           - None: 默认清理所有未使用的镜像（包括带标签但未使用的）
                           - True: 只清理悬空镜像（没有标签的镜像）
                           - False: 清理所有未使用的镜像（包括带标签但未使用的）
            
        Returns:
            Dict[str, Any]: 包含删除的镜像列表和释放空间的结果，格式为：
            {
                "success": bool,       # 操作是否成功
                "message": str,       # 操作结果消息
                "deleted_images": list, # 已删除镜像列表
                "space_reclaimed": int, # 释放的空间（字节）
                "dangling": bool       # 使用的dangling参数值
            }
        """
        # 确保node_id为整数类型
        node_id = int(node_id)
        
        # 获取Docker节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来清理镜像
            def prune_images_sync():
                try:
                    # 记录开始清理信息
                    dangling_param = prune_request.dangling if prune_request else None
                    logger.info(f"Starting to clean up images on Docker node {node_id}, dangling parameter: {dangling_param}")
                    
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 处理TLS配置
                        tls_kwargs = {}
                        
                        # 直接使用证书文件路径
                        if 'ca_cert_path' in config['tls']:
                            tls_kwargs['ca_cert'] = config['tls']['ca_cert_path']
                        
                        if 'client_cert_path' in config['tls'] and 'client_key_path' in config['tls']:
                            tls_kwargs['client_cert'] = (config['tls']['client_cert_path'], config['tls']['client_key_path'])
                        
                        tls_kwargs['verify'] = True
                        tls_config = docker.tls.TLSConfig(**tls_kwargs)
                        client = docker.DockerClient(
                            base_url=config['base_url'],
                            tls=tls_config
                        )
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    
                    # 初始化结果变量
                    images_deleted = []
                    space_reclaimed = 0
                    
                    # 判断是否只清理悬空镜像
                    if prune_request and prune_request.dangling:
                        # 只清理悬空镜像，使用Docker API的原生支持
                        filters = {"dangling": "true"}
                        result = client.images.prune(filters=filters)
                        
                        # 处理result可能为None的情况
                        if result is not None:
                            images_deleted = result.get('ImagesDeleted', [])
                            space_reclaimed = result.get('SpaceReclaimed', 0)
                    else:
                        # dangling为False或未指定时，手动实现清理所有未使用镜像的逻辑
                        # 1. 获取所有容器使用的镜像列表
                        used_image_ids = set()
                        containers = client.containers.list(all=True)
                        for container in containers:
                            container_info = container.attrs
                            if 'Image' in container_info:
                                # 获取容器使用的镜像ID
                                image_id = container_info['Image']
                                used_image_ids.add(image_id)
                        
                        # 2. 获取所有镜像
                        all_images = client.images.list(all=True)
                        
                        # 3. 遍历所有镜像，删除未被使用的镜像
                        for image in all_images:
                            image_id = image.id
                            
                            # 检查镜像是否被任何容器使用
                            if image_id not in used_image_ids:
                                # 检查是否为悬空镜像（没有标签）
                                is_dangling = len(image.tags) == 0
                                
                                # 删除未被使用的镜像
                                try:
                                    # 获取镜像的大小信息
                                    image_info = client.images.get(image_id).attrs
                                    image_size = image_info.get('Size', 0)
                                    
                                    # 删除镜像
                                    client.images.remove(image_id, force=True)
                                    
                                    # 添加到已删除列表
                                    deleted_info = {
                                        'Untagged': None,
                                        'Deleted': image_id
                                    }
                                    # 如果不是悬空镜像，添加标签信息
                                    if not is_dangling and image.tags:
                                        deleted_info['Untagged'] = image.tags[0]
                                    
                                    images_deleted.append(deleted_info)
                                    space_reclaimed += image_size
                                    
                                    logger.info(f"Remove unused image {image_id}, size: {image_size} bytes")
                                except Exception as e:
                                    # 记录删除失败的镜像，但继续处理其他镜像
                                    logger.warning(f"Failed to delete image {image_id}: {str(e)}")
                    
                    # 确保images_deleted不为None
                    if images_deleted is None:
                        images_deleted = []
                    
                    # 确保space_reclaimed不为None
                    if space_reclaimed is None:
                        space_reclaimed = 0
                    
                    # 记录清理结果
                    deleted_count = len(images_deleted)
                    logger.info(f"Docker node {node_id} image prune completed: deleted {deleted_count} images, reclaimed {space_reclaimed} bytes of space")
                    
                    # 返回清理结果
                    return {
                        "success": True,
                        "message": "Pruned unused images successfully",
                        "deleted_images": images_deleted,
                        "space_reclaimed": space_reclaimed,
                        "dangling": prune_request.dangling if prune_request else None
                    }
                    
                except Exception as e:
                    logger.error(f"Docker node {node_id} image prune failed: {str(e)}", exc_info=True)
                    raise HTTPException(status_code=500, detail=f"Pruned unused images failed: {str(e)}")   
                finally:
                    # 确保客户端连接关闭
                    if 'client' in locals():
                        client.close()
            
            # 异步执行清理镜像
            result = await loop.run_in_executor(cls._executor, prune_images_sync)
            
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Pruned unused images failed: {str(e)}")
    
    @classmethod
    async def export_image(cls, db: AsyncSession, node_id: int, export_data: ImageExportRequest) -> ImageExportResponse:
        """
        导出Docker镜像
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            export_data: 镜像导出数据
            
        Returns:
            ImageExportResponse: 镜像导出响应
        """
        # 确保node_id为整数类型
        node_id = int(node_id)
        
        # 获取Docker节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 确保导出目录存在
            cls._ensure_export_dir(export_data.output_path)
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来导出镜像
            def export_image_sync():
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 处理TLS配置
                        tls_kwargs = {}
                        
                        # 直接使用证书文件路径
                        if 'ca_cert_path' in config['tls']:
                            tls_kwargs['ca_cert'] = config['tls']['ca_cert_path']
                        
                        if 'client_cert_path' in config['tls'] and 'client_key_path' in config['tls']:
                            tls_kwargs['client_cert'] = (config['tls']['client_cert_path'], config['tls']['client_key_path'])
                        
                        tls_kwargs['verify'] = True
                        tls_config = docker.tls.TLSConfig(**tls_kwargs)
                        client = docker.DockerClient(
                            base_url=config['base_url'],
                            tls=tls_config
                        )
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    
                    # 检查镜像是否存在
                    try:
                        image = client.images.get(export_data.tag)
                    except docker.errors.ImageNotFound:
                        raise HTTPException(status_code=404, detail=f"Image not found: {export_data.tag}")
                    
                    # 生成输出文件名
                    base_name = os.path.basename(export_data.tag.replace(':', '_').replace('/', '_'))
                    # 生成4位随机字母
                    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase, k=4))
                    # 构建带随机后缀的文件名
                    output_filename = f"{base_name}_{random_suffix}.tar"
                    if export_data.compress:
                        output_filename += '.gz'
                    
                    # 构建完整的输出文件路径
                    output_file_path = os.path.join(export_data.output_path, output_filename)
                    
                    # 检查输出文件是否已存在
                    if os.path.exists(output_file_path):
                        raise HTTPException(status_code=400, detail=f"Output file already exists: {output_file_path}")
                    
                    # 执行导出操作
                    # 由于Docker SDK的image.save()方法不支持compress参数，需要手动处理压缩
                    image = client.images.get(export_data.tag)
                    
                    # 确保导出时包含标签信息
                    # 使用named=True参数确保保存所有关联的标签
                    if export_data.compress:
                        # 使用gzip压缩导出
                        with gzip.open(output_file_path, 'wb', compresslevel=9) as f:
                            for chunk in image.save(named=True, chunk_size=2097152):
                                f.write(chunk)
                    else:
                        # 不压缩直接导出
                        with open(output_file_path, 'wb') as f:
                            for chunk in image.save(named=True, chunk_size=2097152):
                                f.write(chunk)
                    
                    # 返回操作响应
                    return ImageExportResponse(
                    message="Image exported successfully",
                    log_file_path="",  # 同步操作不需要日志文件
                    output_file_path=output_file_path,
                    success=True
                )
                    
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Export image failed: {str(e)}")
                finally:
                    # 确保客户端连接关闭
                    if 'client' in locals():
                        client.close()
            
            # 异步执行导出镜像
            result = await loop.run_in_executor(cls._executor, export_image_sync)
            
            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Export image failed: {str(e)}")

    @classmethod
    async def pull_image(cls, db: AsyncSession, node_id: int, pull_data: ImagePullRequest) -> ImagePullResponse:
        node_id = int(node_id)
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        cls._ensure_log_dir()
        operation_id = str(uuid.uuid4())
        log_file_path = os.path.join(cls._LOG_DIR, f"pull_{operation_id}.log")
        cls._operations[operation_id] = {
            'node_id': node_id,
            'name': pull_data.name,
            'tag': pull_data.tag,
            'status': 'running',
            'start_time': time.time(),
            'log_file': log_file_path
        }
        config = node.connection_config
        threading.Thread(
            target=cls._pull_image_sync,
            args=(config, pull_data.name, pull_data.tag, log_file_path, operation_id)
        ).start()
        return ImagePullResponse(
            operation_id=operation_id,
            message="镜像拉取操作已启动",
            log_file_path=log_file_path,
            success=True
        )

    @classmethod
    def _pull_image_sync(cls, config: Dict[str, Any], name: str, tag: Optional[str], log_file_path: str, operation_id: str):
        client = None
        try:
            with open(log_file_path, 'w', encoding='utf-8') as f:
                pass
            repo = name
            pull_tag = tag
            if not pull_tag and ':' in name:
                parts = name.rsplit(':', 1)
                repo, pull_tag = parts[0], parts[1]
            if not pull_tag:
                pull_tag = 'latest'
            if 'tls' in config:
                tls_kwargs = {}
                if 'ca_cert_path' in config['tls']:
                    tls_kwargs['ca_cert'] = config['tls']['ca_cert_path']
                if 'client_cert_path' in config['tls'] and 'client_key_path' in config['tls']:
                    tls_kwargs['client_cert'] = (config['tls']['client_cert_path'], config['tls']['client_key_path'])
                tls_kwargs['verify'] = True
                tls_config = docker.tls.TLSConfig(**tls_kwargs)
                client = docker.APIClient(base_url=config['base_url'], tls=tls_config)
            else:
                client = docker.APIClient(base_url=config['base_url'])
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                log_f.write(f"[{timestamp}] Start pulling image {repo}:{pull_tag}\n")
                log_f.flush()
            stream = client.pull(repository=repo, tag=pull_tag, stream=True, decode=True)
            for event in stream:
                if cls._operations.get(operation_id, {}).get('status') == 'cancelled':
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                        log_f.write(f"[{ts}] Image pull cancelled by user\n")
                        log_f.flush()
                    cls._operations[operation_id]['status'] = 'cancelled'
                    cls._operations[operation_id]['end_time'] = time.time()
                    return

                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                status = event.get('status', '')
                eid = event.get('id', '')
                progress = event.get('progress', '')
                line = status
                if eid:
                    line += f" {eid}"
                if progress:
                    line += f" {progress}"
                with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                    log_f.write(f"[{ts}] {line}\n")
                    log_f.flush()
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                op_time = time.time() - cls._operations[operation_id]['start_time']
                log_f.write(f"[{ts}] Image pull completed {repo}:{pull_tag}\n")
                log_f.write(f"[{ts}] Operation time: {op_time:.2f} seconds\n")
            cls._operations[operation_id]['status'] = 'completed'
            cls._operations[operation_id]['end_time'] = time.time()
        except Exception as e:
            with open(log_file_path, 'a', encoding='utf-8') as f:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{ts}] Error: {str(e)}\n")
                f.flush()
            cls._operations[operation_id]['status'] = 'failed'
            cls._operations[operation_id]['error'] = str(e)
            cls._operations[operation_id]['end_time'] = time.time()
            logger.error(f"操作ID {operation_id}: 镜像拉取失败 - {str(e)}")

    @classmethod
    async def cancel_pull_image(cls, db: AsyncSession, node_id: int, cancel_data) -> dict:
        """取消拉取镜像操作"""
        operation_id = cancel_data.operation_id
        if operation_id not in cls._operations:
            raise HTTPException(status_code=404, detail="操作ID不存在")
        operation = cls._operations[operation_id]
        if operation['status'] != 'running':
            raise HTTPException(status_code=400, detail=f"操作状态为 {operation['status']}，无法取消")
        operation['status'] = 'cancelled'
        operation['end_time'] = time.time()
        log_file_path = operation.get('log_file', '')
        if log_file_path:
            try:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(log_file_path, 'a', encoding='utf-8') as f:
                    f.write(f"[{ts}] Cancel requested by user\n")
                    f.flush()
            except Exception:
                pass
        return {"success": True, "message": "镜像拉取操作已取消"}

    @classmethod
    async def prune_image_cache(cls, db: AsyncSession, node_id: int, prune_data: ImageCachePruneRequest) -> ImageCachePruneResponse:
        node_id = int(node_id)
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        cls._ensure_log_dir()
        operation_id = str(uuid.uuid4())
        log_file_path = os.path.join(cls._LOG_DIR, f"prune_cache_{operation_id}.log")
        cls._operations[operation_id] = {
            'node_id': node_id,
            'all_images': prune_data.all,
            'status': 'running',
            'start_time': time.time(),
            'log_file': log_file_path
        }
        config = node.connection_config
        threading.Thread(
            target=cls._prune_image_cache_sync,
            args=(config, prune_data.all, log_file_path, operation_id)
        ).start()
        return ImageCachePruneResponse(
            operation_id=operation_id,
            message="清除镜像缓存操作已启动",
            log_file_path=log_file_path,
            success=True
        )

    @classmethod
    async def build_image(cls, db: AsyncSession, node_id: int, build_data: ImageBuildRequest) -> ImageBuildResponse:
        node_id = int(node_id)
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        if not os.path.exists(build_data.path):
            raise HTTPException(status_code=404, detail=f"Dockerfile不存在: {build_data.path}")
        cls._ensure_log_dir()
        operation_id = str(uuid.uuid4())
        log_file_path = os.path.join(cls._LOG_DIR, f"build_{operation_id}.log")
        cls._operations[operation_id] = {
            'node_id': node_id,
            'path': build_data.path,
            'tag': build_data.tag,
            'status': 'running',
            'start_time': time.time(),
            'log_file': log_file_path
        }
        config = node.connection_config
        threading.Thread(
            target=cls._build_image_sync,
            args=(config, build_data.path, build_data.tag, log_file_path, operation_id)
        ).start()
        return ImageBuildResponse(
            operation_id=operation_id,
            message="镜像构建操作已启动",
            log_file_path=log_file_path,
            success=True
        )

    @classmethod
    def _prune_image_cache_sync(cls, config: Dict[str, Any], all_images: bool, log_file_path: str, operation_id: str):
        client = None
        try:
            with open(log_file_path, 'w', encoding='utf-8') as f:
                pass
            if 'tls' in config:
                tls_kwargs = {}
                if 'ca_cert_path' in config['tls']:
                    tls_kwargs['ca_cert'] = config['tls']['ca_cert_path']
                if 'client_cert_path' in config['tls'] and 'client_key_path' in config['tls']:
                    tls_kwargs['client_cert'] = (config['tls']['client_cert_path'], config['tls']['client_key_path'])
                tls_kwargs['verify'] = True
                tls_config = docker.tls.TLSConfig(**tls_kwargs)
                client = docker.APIClient(base_url=config['base_url'], tls=tls_config)
            else:
                client = docker.APIClient(base_url=config['base_url'])
            ts0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                cache_type = "all images" if all_images else "dangling images"
                log_f.write(f"[{ts0}] Start pruning image cache ({cache_type})\n")
                log_f.flush()
            
            # 根据all参数决定清除策略
            filters = {'dangling': True} if not all_images else {}
            pruned_result = client.prune_images(filters=filters)
            
            ts1 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                log_f.write(f"[{ts1}] Cache prune completed\n")
                log_f.write(f"[{ts1}] Result: {pruned_result}\n")
                
                # 解析结果显示删除的镜像数量和回收的空间
                if 'ImagesDeleted' in pruned_result and pruned_result['ImagesDeleted']:
                    deleted_count = len(pruned_result['ImagesDeleted'])
                    log_f.write(f"[{ts1}] Deleted {deleted_count} images\n")
                else:
                    log_f.write(f"[{ts1}] No images deleted\n")
                
                if 'SpaceReclaimed' in pruned_result:
                    space_reclaimed = pruned_result['SpaceReclaimed']
                    log_f.write(f"[{ts1}] Space reclaimed: {space_reclaimed} bytes ({space_reclaimed/1024/1024:.2f} MB)\n")
            
            op_time = time.time() - cls._operations[operation_id]['start_time']
            with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                log_f.write(f"[{ts1}] Operation time: {op_time:.2f} seconds\n")
                
            cls._operations[operation_id]['status'] = 'completed'
            cls._operations[operation_id]['end_time'] = time.time()
        except Exception as e:
            with open(log_file_path, 'a', encoding='utf-8') as f:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{ts}] Error: {str(e)}\n")
                f.flush()
            cls._operations[operation_id]['status'] = 'failed'
            cls._operations[operation_id]['error'] = str(e)
            cls._operations[operation_id]['end_time'] = time.time()
            logger.error(f"操作ID {operation_id}: 清除镜像缓存失败 - {str(e)}")
        finally:
            if client:
                client.close()
    
    @classmethod
    async def manage_image_tags(cls, db: AsyncSession, node_id: int, image_id: str, request: ImageTagRequest) -> ImageTagResponse:
        """
        管理Docker镜像的标签
        
        Args:
            db: 数据库会话
            node_id: Docker节点ID
            image_id: 镜像ID
            request: 镜像标签管理请求
            
        Returns:
            ImageTagResponse: 镜像标签管理响应
        """
        # 确保node_id为整数类型
        node_id = int(node_id)
        
        # 获取Docker节点信息
        node = await db.get(DockerNode, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Docker节点不存在")
        
        try:
            # 获取节点连接配置
            config = node.connection_config
            
            # 由于docker库是同步的，我们使用线程池来异步执行
            loop = asyncio.get_running_loop()
            
            # 定义同步函数来管理镜像标签
            def manage_tags_sync():
                client = None
                try:
                    # 创建Docker客户端
                    if 'tls' in config:
                        # 处理TLS配置
                        tls_kwargs = {}
                        
                        # 直接使用证书文件路径
                        if 'ca_cert_path' in config['tls']:
                            tls_kwargs['ca_cert'] = config['tls']['ca_cert_path']
                        
                        if 'client_cert_path' in config['tls'] and 'client_key_path' in config['tls']:
                            tls_kwargs['client_cert'] = (config['tls']['client_cert_path'], config['tls']['client_key_path'])
                        
                        tls_kwargs['verify'] = True
                        tls_config = docker.tls.TLSConfig(**tls_kwargs)
                        client = docker.DockerClient(
                            base_url=config['base_url'],
                            tls=tls_config
                        )
                    else:
                        client = docker.DockerClient(base_url=config['base_url'])
                    
                    # 获取指定ID的镜像
                    try:
                        image = client.images.get(image_id)
                    except docker.errors.ImageNotFound:
                        raise HTTPException(status_code=404, detail="指定的镜像不存在")
                    
                    # 获取当前镜像的所有标签
                    current_tags = set(image.tags)
                    
                    # 获取请求中的标签集合
                    requested_tags = set(request.tags)
                    
                    # Docker API 不支持直接删除单个标签，所以我们需要一个更复杂的方法
                    # 如果需要删除标签（即请求的标签集与当前标签集不同）
                    if current_tags != requested_tags:
                        # 步骤1: 创建一个临时标签，确保我们可以在操作后引用原始镜像
                        # 移除image_id中的sha256:前缀并替换特殊字符，确保符合Docker标签命名规范
                        safe_image_id = image_id.replace("sha256:", "sha256-")
                        temp_tag = f"temp_{safe_image_id[:12]}:{int(time.time())}"
                        try:
                            image.tag(temp_tag)
                            
                            # 步骤2: 删除所有当前标签（这不会删除镜像本身，只要有一个标签或ID引用它）
                            for existing_tag in current_tags:
                                try:
                                    client.images.remove(existing_tag)
                                    logger.info(f"镜像标签已删除: {existing_tag}")
                                except Exception as e:
                                    logger.warning(f"删除镜像标签失败 {existing_tag}: {str(e)}")
                            
                            # 步骤3: 应用所有请求的标签
                            for tag in requested_tags:
                                try:
                                    # 使用临时标签获取镜像并应用新标签
                                    temp_image = client.images.get(temp_tag)
                                    temp_image.tag(tag)
                                    logger.info(f"镜像标签已添加: {tag}")
                                except Exception as e:
                                    logger.error(f"添加镜像标签失败 {tag}: {str(e)}")
                                    raise HTTPException(status_code=400, detail=f"添加标签 {tag} 失败: {str(e)}")
                            
                            # 步骤4: 移除临时标签
                            try:
                                client.images.remove(temp_tag)
                                logger.info(f"临时标签已删除: {temp_tag}")
                            except Exception as e:
                                logger.warning(f"删除临时标签失败 {temp_tag}: {str(e)}")
                        except Exception as e:
                            # 如果出现错误，尝试清理临时标签
                            try:
                                client.images.remove(temp_tag)
                            except:
                                pass
                            raise HTTPException(status_code=500, detail=f"管理标签过程中出错: {str(e)}")
                    else:
                        # 如果标签集没有变化，不需要做任何操作
                        logger.info("标签集没有变化，无需操作")
                    
                    # 重新获取镜像以获取更新后的标签列表
                    updated_image = client.images.get(image_id)
                    updated_tags = updated_image.tags
                    
                    return updated_tags
                    
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"管理镜像标签失败: {str(e)}")
                finally:
                    # 确保客户端连接关闭
                    if client:
                        client.close()
            
            # 异步执行管理镜像标签
            updated_tags = await loop.run_in_executor(cls._executor, manage_tags_sync)
            
            # 返回响应
            return ImageTagResponse(
                success=True,
                message="镜像标签管理成功",
                image_id=image_id,
                updated_tags=updated_tags
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"管理镜像标签时发生错误: {str(e)}")


    @classmethod
    def _build_image_sync(cls, config: Dict[str, Any], dockerfile_path: str, tag: str, log_file_path: str, operation_id: str):
        client = None
        try:
            with open(log_file_path, 'w', encoding='utf-8') as f:
                pass
            context_dir = os.path.dirname(dockerfile_path)
            dockerfile_name = os.path.basename(dockerfile_path)
            if 'tls' in config:
                tls_kwargs = {}
                if 'ca_cert_path' in config['tls']:
                    tls_kwargs['ca_cert'] = config['tls']['ca_cert_path']
                if 'client_cert_path' in config['tls'] and 'client_key_path' in config['tls']:
                    tls_kwargs['client_cert'] = (config['tls']['client_cert_path'], config['tls']['client_key_path'])
                tls_kwargs['verify'] = True
                tls_config = docker.tls.TLSConfig(**tls_kwargs)
                client = docker.APIClient(base_url=config['base_url'], tls=tls_config)
            else:
                client = docker.APIClient(base_url=config['base_url'])
            ts0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                log_f.write(f"[{ts0}] Start building image {tag} from {dockerfile_path}\n")
                log_f.flush()
            stream = client.build(path=context_dir, dockerfile=dockerfile_name, tag=tag, rm=True, forcerm=True, decode=True)
            for event in stream:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                line = ''
                if isinstance(event, dict):
                    if 'stream' in event and event['stream']:
                        line = event['stream'].rstrip()
                    elif 'status' in event:
                        line = event.get('status', '')
                        if event.get('id'):
                            line += f" {event['id']}"
                        if event.get('progress'):
                            line += f" {event['progress']}"
                    elif 'error' in event:
                        line = f"Error: {event.get('error')}"
                    else:
                        line = str(event)
                else:
                    line = str(event)
                if line:
                    with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                        log_f.write(f"[{ts}] {line}\n")
                        log_f.flush()
            ts1 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                op_time = time.time() - cls._operations[operation_id]['start_time']
                log_f.write(f"[{ts1}] Image build completed {tag}\n")
                log_f.write(f"[{ts1}] Operation time: {op_time:.2f} seconds\n")
            try:
                pruned = client.images.prune(filters={'dangling': True})
                ts2 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                    log_f.write(f"[{ts2}] Pruned dangling images: {pruned}\n")
                    log_f.flush()
            except Exception as prune_error:
                ts2 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(log_file_path, 'a', encoding='utf-8', buffering=1) as log_f:
                    log_f.write(f"[{ts2}] Prune dangling images failed: {str(prune_error)}\n")
                    log_f.flush()
            cls._operations[operation_id]['status'] = 'completed'
            cls._operations[operation_id]['end_time'] = time.time()
        except Exception as e:
            with open(log_file_path, 'a', encoding='utf-8') as f:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{ts}] Error: {str(e)}\n")
                f.flush()
            cls._operations[operation_id]['status'] = 'failed'
            cls._operations[operation_id]['error'] = str(e)
            cls._operations[operation_id]['end_time'] = time.time()
            logger.error(f"操作ID {operation_id}: 镜像构建失败 - {str(e)}")
        finally:
            if client:
                client.close()
