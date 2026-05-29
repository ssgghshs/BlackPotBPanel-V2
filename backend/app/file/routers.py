from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Body, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from . import schemas, service
import zipfile
import os
import re
import tempfile
import shutil
from typing import List, Optional
# 添加认证依赖导入
from middleware.auth import get_current_active_user 

router = APIRouter(prefix="/file", tags=["file"])

@router.get("/list")
async def list_files(
    path: str = "/opt/blackpotbpanel-v2/server",
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_active_user)
):
    """获取指定路径下的文件列表"""
    try:
        files = await service.get_files_by_path(path)
        total = len(files)
        start = max(0, skip)
        end = start + max(0, limit)
        paged = files[start:end]
        return {
            "data": paged,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_files(
    path: str = Body(..., description="要搜索的目录路径"),
    keyword: str = Body(..., description="搜索关键词"),
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_active_user)
):
    """搜索指定目录及其子目录中匹配关键词的文件
    
    支持正则表达式搜索，结果返回格式与list接口完全一致
    
    参数说明:
    - path: 要搜索的目录路径（Body参数）
    - keyword: 搜索关键词（Body参数）
    - skip: 跳过的结果数（Query参数）
    - limit: 返回的最大结果数（Query参数）
    """
    try:
        # 执行搜索
        matched_files = await service.search_files_in_directory(path, keyword)
        total = len(matched_files)
        
        # 分页处理
        start = max(0, skip)
        end = start + max(0, limit)
        paged = matched_files[start:end]
        
        # 返回与list接口相同格式的响应
        return {
            "data": paged,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dirsize")
async def get_directory_size(
    path: str, 
    current_user = Depends(get_current_active_user)):
    """获取指定目录的大小"""
    try:
        size_bytes = await service.get_directory_size(path)
        return {
            "code": 200,
            "message": "Directory size calculation successful",
            "data": {
                "size_human": service.format_file_size(size_bytes)
            }
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create_directory")
async def create_directory(
    path: str = Body(...), 
    dir_name: str = Body(...), 
    current_user = Depends(get_current_active_user)):
    """在指定路径下创建新目录"""
    try:
        result = await service.create_directory(path, dir_name)
        if result:
            return {
                "code": 200,
                "message": f"目录 {dir_name} 创建成功",
                "data": None
            }
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create_file")
async def create_file(
    path: str = Body(...), 
    file_name: str = Body(...), 
    content: str = Body(""), 
    current_user = Depends(get_current_active_user)):
    """在指定路径下创建新文件"""
    try:
        result = await service.create_file(path, file_name, content)
        if result:
            # 处理中文文件名的编码问题
            from urllib.parse import quote
            encoded_filename = quote(file_name.encode('utf-8'))
            
            return {
                "code": 200,
                "message": f"文件 {encoded_filename} 创建成功",
                "data": None
            }
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_file(
    path: str = Body(...), 
    file: UploadFile = File(...),
    overwrite: bool = Body(False, description="是否覆盖已有文件"),
    current_user = Depends(get_current_active_user)):
    """上传文件到指定路径

    - **path**: 目标目录路径
    - **file**: 要上传的文件
    - **overwrite**: 是否覆盖已有文件，默认为 false（不覆盖）
    """
    try:
        result = await service.upload_file(path, file, overwrite)
        if result:
            return {
                "code": 200,
                "message": f"文件 {file.filename} 上传成功",
                "data": None
            }
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete")
async def delete_file(
    path: str = Body(...), 
    filename: str = Body(...), 
    current_user = Depends(get_current_active_user)):
    """删除指定路径下的文件或目录"""
    try:
        # 检查是否试图删除回收站目录
        recycle_path = "/opt/blackpotbpanel-v2/server/.recycle_bp"
        full_path = os.path.join(path, filename)
        if os.path.abspath(full_path) == os.path.abspath(recycle_path):
            raise ValueError("不允许删除回收站目录")
        
        result = await service.delete_file(path, filename)
        if result:
            return {
                "code": 200,
                "message": f"文件或目录 {filename} 处理成功",
                "data": None
            }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete_batch")
async def delete_files_batch(
    path: str = Body(...), 
    filenames: List[str] = Body(...), 
    current_user = Depends(get_current_active_user)):
    """批量删除指定路径下的文件或目录"""
    try:
        # 检查是否试图删除回收站目录
        recycle_path = "/opt/blackpotbpanel-v2/server/.recycle_bp"
        for filename in filenames:
            # 如果文件名是格式化后的符号链接格式 "filename -> target_path"，提取原始文件名
            if " -> " in filename:
                filename = filename.split(" -> ")[0]
            
            full_path = os.path.join(path, filename)
            if os.path.abspath(full_path) == os.path.abspath(recycle_path):
                raise ValueError("不允许删除回收站目录")
        
        result = await service.delete_files_batch(path, filenames)
        return {
            "code": 200,
            "message": f"批量处理完成，成功处理 {result['success_count']} 个文件，失败 {result['failed_count']} 个",
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download")
async def download_file(
    path: str, 
    filename: str, 
    request: Request, 
    current_user = Depends(get_current_active_user)):
    """下载指定路径下的单个文件（支持断点续传）"""
    try:
        # 处理符号链接文件名格式
        original_filename = filename
        if " -> " in filename:
            original_filename = filename.split(" -> ")[0]
        
        # 安全检查：防止路径遍历攻击
        if ".." in original_filename or original_filename.startswith("/"):
            raise ValueError("文件名包含非法字符")
        
        # 构建完整文件路径
        full_path = os.path.abspath(os.path.join(path, original_filename))
        
        # 验证文件存在
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"文件 {original_filename} 不存在")
        
        # 验证是否为文件
        if not os.path.isfile(full_path):
            raise ValueError(f"{original_filename} 不是一个文件")
        
        # 获取文件大小
        file_size = os.path.getsize(full_path)
        
        # 处理中文文件名编码
        from urllib.parse import quote
        encoded_filename = quote(original_filename.encode('utf-8'))
        
        # 检查是否为断点续传请求
        range_header = request.headers.get('Range')
        start = 0
        end = file_size - 1
        status_code = 200
        
        if range_header:
            # 解析Range请求头
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                if match.group(2):
                    end = int(match.group(2))
                
                # 验证范围有效性
                if start < 0 or end >= file_size or start > end:
                    raise HTTPException(status_code=416, detail="请求的范围无效")
                
                status_code = 206  # Partial Content
        
        # 生成文件流
        async def file_stream():
            with open(full_path, "rb") as f:
                f.seek(start)
                remaining = end - start + 1
                chunk_size = 8192
                
                while remaining > 0:
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    yield chunk
                    remaining -= len(chunk)
        
        from fastapi.responses import StreamingResponse
        
        # 构建响应头
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
            "Content-Type": "application/octet-stream",
            "Accept-Ranges": "bytes"
        }
        
        if status_code == 206:
            # 断点续传响应头
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            headers["Content-Length"] = str(end - start + 1)
        else:
            # 正常下载响应头
            headers["Content-Length"] = str(file_size)
        
        return StreamingResponse(
            file_stream(),
            status_code=status_code,
            headers=headers,
            media_type="application/octet-stream"
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rename")
async def rename_file(
    path: str = Body(...), 
    old_name: str = Body(...), 
    new_name: str = Body(...), 
    current_user = Depends(get_current_active_user)):
    """重命名指定路径下的文件或目录"""
    try:
        result = await service.rename_file(path, old_name, new_name)
        if result:
            # 处理中文文件名的编码问题
            from urllib.parse import quote
            encoded_old_name = quote(old_name.encode('utf-8'))
            encoded_new_name = quote(new_name.encode('utf-8'))
            
            return {
                "code": 200,
                "message": f"文件或目录 {encoded_old_name} 已重命名为 {encoded_new_name}",
                "data": None
            }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/permissions")
async def change_permissions(
    path: str = Body(...), 
    filename: str = Body(...), 
    permissions: str = Body(None, description="权限模式(3位数字)", example="755"), 
    user: str = Body(None, description="所有者用户名"),
    group: str = Body(None, description="所属组名"),
    recursive: bool = Body(False, description="是否递归应用到子目录"),
    current_user = Depends(get_current_active_user)):
    """修改文件/目录权限、所有者和所属组
    
    支持修改文件/目录的权限模式、所有者和所属组，可以选择是否递归应用到子目录。
    至少需要提供permissions、user或group中的一个参数。
    """
    try:
        # 验证至少提供了一个修改参数
        if not any([permissions, user, group]):
            raise ValueError("至少需要提供permissions、user或group中的一个参数")
            
        # 验证权限格式 (如果提供了权限参数)
        if permissions and not re.match(r'^[0-7]{3}$', permissions):
            raise ValueError("权限格式不正确，应为3位数字(0-7)")
            
        result = await service.change_permissions(path, filename, permissions, user, group, recursive)
        if result:
            # 构建返回消息
            changes = []
            if permissions:
                changes.append(f"权限已修改为 {permissions}")
            if user:
                changes.append(f"所有者已修改为 {user}")
            if group:
                changes.append(f"所属组已修改为 {group}")
            if recursive:
                changes.append("(已递归应用到所有子目录)")
                
            return {
                "code": 200,
                "message": f"文件/目录 {filename} {', '.join(changes)}",
                "data": None
            }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/permissions_batch")
async def change_permissions_batch(
    path: str = Body(...), 
    filenames: List[str] = Body(..., description="要修改权限的文件名列表"), 
    permissions: str = Body(None, description="权限模式(3位数字)", example="755"), 
    user: str = Body(None, description="所有者用户名"),
    group: str = Body(None, description="所属组名"),
    recursive: bool = Body(False, description="是否递归应用到子目录"),
    current_user = Depends(get_current_active_user)):
    """批量修改文件/目录权限、所有者和所属组
    
    支持批量修改文件/目录的权限模式、所有者和所属组，可以选择是否递归应用到子目录。
    至少需要提供permissions、user或group中的一个参数。
    """
    try:
        # 验证至少提供了一个修改参数
        if not any([permissions, user, group]):
            raise ValueError("至少需要提供permissions、user或group中的一个参数")
            
        # 验证权限格式 (如果提供了权限参数)
        if permissions and not re.match(r'^[0-7]{3}$', permissions):
            raise ValueError("权限格式不正确，应为3位数字(0-7)")
            
        result = await service.change_permissions_batch(path, filenames, permissions, user, group, recursive)
        
        # 构建返回消息
        changes = []
        if permissions:
            changes.append(f"权限已修改为 {permissions}")
        if user:
            changes.append(f"所有者已修改为 {user}")
        if group:
            changes.append(f"所属组已修改为 {group}")
        if recursive:
            changes.append("(已递归应用到所有子目录)")
        
        return {
            "code": 200,
            "message": f"批量权限修改完成，成功修改 {result['success_count']} 个文件，失败 {result['failed_count']} 个",
            "data": {
                "changes": changes,
                "result": result
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/content")
async def get_file_content(path: str, filename: str, current_user = Depends(get_current_active_user)):
    """获取指定文件的内容"""
    try:
        content = await service.get_file_content(path, filename)
        # 处理中文文件名的编码问题
        from urllib.parse import quote
        encoded_filename = quote(filename.encode('utf-8'))
        
        return {
            "code": 200,
            "message": "文件内容获取成功",
            "data": {
                "content": content,
                "filename": encoded_filename
            }
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/content")
async def save_file_content(
    path: str = Body(...), 
    filename: str = Body(...), 
    content: str = Body(...), 
    current_user = Depends(get_current_active_user)):
    """保存文件内容"""
    try:
        result = await service.save_file_content(path, filename, content)
        if result:
            # 处理中文文件名的编码问题
            from urllib.parse import quote
            encoded_filename = quote(filename.encode('utf-8'))
            
            return {
                "code": 200,
                "message": f"文件 {encoded_filename} 保存成功",
                "data": None
            }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/move")
async def move_file_or_directory(
    source_path: str = Body(...), 
    source_name: str = Body(...), 
    destination_path: str = Body(...), 
    destination_name: str = Body(""),
    overwrite: bool = Body(False, description="是否覆盖目标路径已存在的文件"),
    current_user = Depends(get_current_active_user)
):
    """移动文件或目录到指定路径"""
    try:
        result = await service.move_file_or_directory(source_path, source_name, destination_path, destination_name, overwrite)
        if result:
            # 处理中文文件名的编码问题
            from urllib.parse import quote
            encoded_source_name = quote(source_name.encode('utf-8'))
            encoded_destination_name = quote(destination_name.encode('utf-8')) if destination_name else encoded_source_name
            
            return {
                "code": 200,
                "message": f"文件或目录 {encoded_source_name} 已移动到 {encoded_destination_name}",
                "data": None
            }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/image")
async def get_image_content(
    path: str, 
    filename: str, 
    current_user = Depends(get_current_active_user)):
    """获取指定图片文件的内容"""
    try:
        content = await service.get_image_content(path, filename)
        # 根据文件扩展名确定Content-Type
        _, ext = os.path.splitext(filename.lower())
        content_type = "image/jpeg"  # 默认为jpeg
        if ext == ".png":
            content_type = "image/png"
        elif ext in [".gif"]:
            content_type = "image/gif"
        elif ext in [".bmp"]:
            content_type = "image/bmp"
        elif ext in [".webp"]:
            content_type = "image/webp"
        elif ext in [".svg"]:
            content_type = "image/svg+xml"
        elif ext in [".ico"]:
            content_type = "image/x-icon"
            
        # 处理中文文件名的编码问题
        from urllib.parse import quote
        encoded_filename = quote(filename.encode('utf-8'))
            
        return Response(
            content=content,
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}",
            },
            media_type=content_type
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/copy")
async def copy_file_or_directory(
    source_path: str = Body(...), 
    source_name: str = Body(...), 
    destination_path: str = Body(...), 
    destination_name: str = Body(""),
    overwrite: bool = Body(False, description="是否覆盖目标路径已存在的文件"),
    current_user = Depends(get_current_active_user)
):
    """复制文件或目录到指定路径"""
    try:
        result = await service.copy_file_or_directory(source_path, source_name, destination_path, destination_name, overwrite)
        if result:
            # 处理中文文件名的编码问题
            from urllib.parse import quote
            encoded_source_name = quote(source_name.encode('utf-8'))
            encoded_destination_name = quote(destination_name.encode('utf-8')) if destination_name else encoded_source_name
            
            return {
                "code": 200,
                "message": f"文件或目录 {encoded_source_name} 已复制到 {encoded_destination_name}",
                "data": None
            }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compress")
async def compress_files(
    source_path: str = Body(...), 
    source_names: List[str] = Body(...), 
    destination_path: str = Body(...), 
    archive_name: str = Body(...), 
    current_user = Depends(get_current_active_user)
):
    """压缩文件或目录到指定路径"""
    try:
        result = await service.compress_files(source_path, source_names, destination_path, archive_name)
        if result:
            # 处理中文文件名的编码问题
            from urllib.parse import quote
            encoded_archive_name = quote(archive_name.encode('utf-8'))
            
            return {
                "code": 200,
                "message": f"文件已压缩为 {encoded_archive_name}",
                "data": None
            }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compress_batch")
async def compress_files_batch(
    source_path: str = Body(...), 
    source_names: List[str] = Body(...), 
    destination_path: str = Body(...), 
    archive_name: str = Body(...), 
    current_user = Depends(get_current_active_user)
):
    """批量压缩同一文件夹下的多个文件到一个压缩包"""
    try:
        # 调用现有的压缩服务函数，它已经支持批量压缩
        result = await service.compress_files(source_path, source_names, destination_path, archive_name)
        if result:
            # 处理中文文件名的编码问题
            from urllib.parse import quote
            encoded_archive_name = quote(archive_name.encode('utf-8'))
            
            return {
                "code": 200,
                "message": f"批量压缩完成，文件已压缩为 {encoded_archive_name}",
                "data": {
                    "archive_name": archive_name,
                    "source_files": source_names,
                    "destination_path": destination_path
                }
            }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/decompress")
async def decompress_file(
    source_path: str = Body(...), 
    source_name: str = Body(...), 
    destination_path: str = Body(...), 
    current_user = Depends(get_current_active_user)
):
    """解压文件到指定路径"""
    try:
        result = await service.decompress_file(source_path, source_name, destination_path)
        if result:
            # 处理中文文件名的编码问题
            from urllib.parse import quote
            encoded_source_name = quote(source_name.encode('utf-8'))
            
            return {
                "code": 200,
                "message": f"文件 {encoded_source_name} 已解压",
                "data": None
            }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tree")
async def get_file_tree(path: str = "/opt/blackpotbpanel-v2/server", max_depth: int = 3, current_user = Depends(get_current_active_user)):
    """获取指定路径下的文件树结构"""
    try:
        tree = await service.get_file_tree(path, max_depth)
        return {
            "code": 200,
            "message": "文件树获取成功",
            "data": tree
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create_symlink")
async def create_symlink(
    source_path: str = Body(...), 
    source_name: str = Body(...), 
    destination_path: str = Body(...), 
    destination_name: str = Body(...), 
    link_type: str = Body("symlink"),  # 添加链接类型参数，默认为符号链接
    current_user = Depends(get_current_active_user)
):
    """创建软链接或硬链接"""
    try:
        result = False
        if link_type == "symlink":
            # 创建符号链接
            result = await service.create_symlink(source_path, source_name, destination_path, destination_name)
        elif link_type == "hardlink":
            # 创建硬链接
            result = await service.create_hardlink(source_path, source_name, destination_path, destination_name)
        else:
            raise ValueError("无效的链接类型，只支持 'symlink' 或 'hardlink'")
            
        if result:
            # 处理中文文件名的编码问题
            from urllib.parse import quote
            encoded_source_name = quote(source_name.encode('utf-8'))
            encoded_destination_name = quote(destination_name.encode('utf-8'))
            
            link_type_text = "符号链接" if link_type == "symlink" else "硬链接"
            return {
                "code": 200,
                "message": f"{link_type_text} {encoded_source_name} -> {encoded_destination_name} 创建成功",
                "data": None
            }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download_remote")
async def download_remote_file(
    url: str = Body(...), 
    destination_path: str = Body(...), 
    filename: str = Body(None),
    verify_ssl: bool = Body(default=True),  # 添加SSL证书验证参数
    current_user = Depends(get_current_active_user)
):
    """触发远程文件下载任务"""
    try:
        # 启动后台下载任务，传递SSL证书验证参数
        download_id = await service.start_remote_download(url, destination_path, filename or "", verify_ssl)
        
        return {
            "code": 200,
            "message": "下载任务已启动",
            "data": {
                "download_id": download_id
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download_tasks")
async def get_download_tasks(current_user = Depends(get_current_active_user)):
    """获取下载任务列表"""
    try:
        tasks = await service.get_download_task_list()
        return {
            "code": 200,
            "message": "下载任务列表获取成功",
            "data": tasks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download_task/{download_id}")
async def get_download_task(download_id: str, current_user = Depends(get_current_active_user)):
    """获取单个下载任务详情"""
    try:
        task = await service.get_download_task(download_id)
        return {
            "code": 200,
            "message": "下载任务详情获取成功",
            "data": task
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download_progress/{download_id}")
async def get_download_progress(download_id: str, current_user = Depends(get_current_active_user)):
    """获取指定下载ID的进度信息"""
    try:
        progress = await service.get_download_task(download_id)
        return {
            "code": 200,
            "message": "进度获取成功",
            "data": progress
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download_task/{download_id}")
async def cancel_and_delete_download_task(download_id: str, current_user = Depends(get_current_active_user)):
    """取消下载任务并删除记录"""
    try:
        # 先尝试取消下载任务
        cancel_result = await service.cancel_download_task(download_id)
        
        # 然后删除下载任务记录
        delete_result = await service.delete_download_task_record(download_id)
        
        if cancel_result or delete_result:
            return {
                "code": 200,
                "message": "Cancel and Delete Download Task Success",
                "data": None
            }
        else:
            raise HTTPException(status_code=404, detail="下载任务不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 回收站相关接口
@router.post("/recycle/clear")
async def clean_recycle(
    current_user = Depends(get_current_active_user)
):
    """清理回收站文件，删除所有回收站中的文件和目录"""
    try:
        result = await service.clean_recycle_files()
        if result:
            return {
                "code": 200,
                "message": "Clear Recycle Success",
                "data": None
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recycle/list")
async def get_recycle_files(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_active_user)
):
    """获取回收站中的文件和目录列表"""
    try:
        files = await service.get_recycle_files()
        total = len(files)
        start = max(0, skip)
        end = start + max(0, limit)
        paged = files[start:end]
        return {
            "code": 200,
            "message": "获取回收站文件列表成功",
            "data": {
                "data": paged,
                "total": total,
                "skip": skip,
                "limit": limit
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recycle/restore")
async def restore_recycle_file(
    recycle_filename: str = Body(..., description="回收站中的文件名", embed=True),
    target_path: Optional[str] = Body(None, description="可选，指定的恢复目标路径，默认恢复到原始位置"),
    current_user = Depends(get_current_active_user)
):
    """从回收站恢复文件或目录到原始位置或指定位置
    
    支持两种恢复方式：
    1. 恢复到原始位置：不提供target_path参数
    2. 恢复到指定位置：提供target_path参数
    """
    try:
        result = await service.restore_recycle_file(recycle_filename, target_path)
        if result:
            if target_path:
                return {
                    "code": 200,
                    "message": f"File restored to specified location: {target_path}",
                    "data": None
                }
            else:
                return {
                    "code": 200,
                    "message": "File restored to original location",
                    "data": None
                }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recycle/restore_batch")
async def restore_recycle_files_batch(
    recycle_filenames: List[str] = Body(..., description="回收站中的文件名列表", embed=True),
    current_user = Depends(get_current_active_user)
):
    """批量从回收站恢复文件或目录到原始位置
    
    批量恢复只支持恢复到原始位置，不支持指定位置
    """
    try:
        result = await service.restore_recycle_files_batch(recycle_filenames)
        return {
            "code": 200,
            "message": f"Successfully restored {result['success_count']} files, failed {result['failed_count']} files",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recycle/delete")
async def delete_recycle_file(
    recycle_filename: str = Body(..., description="回收站中的文件名", embed=True),
    current_user = Depends(get_current_active_user)
):
    """删除回收站中的单个文件或目录
    
    永久删除回收站中的指定文件或目录，无法恢复
    """
    try:
        result = await service.delete_recycle_file(recycle_filename)
        if result:
            return {
                "code": 200,
                "message": f"File deleted successfully",
                "data": None
            }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recycle/delete_batch")
async def delete_recycle_files_batch(
    recycle_filenames: List[str] = Body(..., description="回收站中的文件名列表", embed=True),
    current_user = Depends(get_current_active_user)
):
    """批量删除回收站中的文件或目录
    
    永久删除回收站中的指定文件或目录，无法恢复
    """
    try:
        result = await service.delete_recycle_files_batch(recycle_filenames)
        return {
            "code": 200,
            "message": f"Successfully deleted {result['success_count']} files, failed {result['failed_count']} files",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





