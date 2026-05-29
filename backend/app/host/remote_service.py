import base64
import json
import logging
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.host import models
from utils.encryption import decrypt_password

logger = logging.getLogger(__name__)

_SHELL_LS_SCRIPT = r"""TARGET_DIR=PATH_REPR_PLACEHOLDER
shopt -s nullglob
for f in "$TARGET_DIR"/* "$TARGET_DIR"/.*; do
    [ -e "$f" ] || [ -L "$f" ] || continue
    b=$(basename "$f")
    [ "$b" = "." ] && continue
    [ "$b" = ".." ] && continue
    s=$(stat -c %s "$f" 2>/dev/null || echo 0)
    p=$(stat -c %a "$f" 2>/dev/null || echo 0)
    u=$(stat -c %U "$f" 2>/dev/null || printf '')
    g=$(stat -c %G "$f" 2>/dev/null || printf '')
    t=$(stat -c %Y "$f" 2>/dev/null || echo 0)
    if [ -L "$f" ]; then
        l=$(readlink "$f")
        printf '%s\t%s\t%s\t%s\t%s\t%s\t0\t1\t%s\n' "$b" "$s" "$p" "$u" "$g" "$t" "$l"
    elif [ -d "$f" ]; then
        printf '%s\t%s\t%s\t%s\t%s\t%s\t1\t0\t\n' "$b" "$s" "$p" "$u" "$g" "$t"
    else
        printf '%s\t%s\t%s\t%s\t%s\t%s\t0\t0\t\n' "$b" "$s" "$p" "$u" "$g" "$t"
    fi
done
"""

_PYTHON_LS_SCRIPT = r"""
import os, stat, pwd, grp, json, datetime
def _fmt_perm(m):
    o = ((m & stat.S_IRUSR) and 4) | ((m & stat.S_IWUSR) and 2) | ((m & stat.S_IXUSR) and 1)
    g = ((m & stat.S_IRGRP) and 4) | ((m & stat.S_IWGRP) and 2) | ((m & stat.S_IXGRP) and 1)
    t = ((m & stat.S_IROTH) and 4) | ((m & stat.S_IWOTH) and 2) | ((m & stat.S_IXOTH) and 1)
    return f'{o}{g}{t}'
def _fmt_size(s):
    for u in ['B','KB','MB','GB','TB']:
        if s < 1024:
            return f'{int(s)} {u}' if s == int(s) else f'{s:.1f} {u}'
        s /= 1024
    return f'{s:.1f} TB'
path = PATH_REPR_PLACEHOLDER
try:
    out = []
    with os.scandir(path) as it:
        for e in it:
            try:
                s = e.stat(follow_symlinks=False)
                is_lnk = e.is_symlink()
                tgt = os.readlink(e.path) if is_lnk else ''
                try: u = pwd.getpwuid(s.st_uid).pw_name
                except: u = str(s.st_uid)
                try: gr = grp.getgrgid(s.st_gid).gr_name
                except: gr = str(s.st_gid)
                nm = e.name
                if is_lnk and tgt:
                    nm = f'{e.name} -> {tgt}'
                is_dir = os.path.isdir(e.path) if is_lnk else e.is_dir(follow_symlinks=False)
                out.append({
                    'filename': nm,
                    'size': _fmt_size(s.st_size),
                    'is_directory': is_dir,
                    'modified_time': datetime.datetime.fromtimestamp(s.st_mtime).isoformat(),
                    'permissions': _fmt_perm(s.st_mode),
                    'user': u,
                    'group': gr,
                    'is_symlink': is_lnk,
                    'target_path': tgt,
                    'path': e.path,
                })
            except Exception:
                pass
    print(json.dumps(out))
except Exception as e:
    print(json.dumps({'error': str(e)}))
"""


def _parse_ls_output(output: str) -> List[Dict]:
    files = []
    for line in output.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) < 8:
            continue

        basename = parts[0]
        size_bytes = int(parts[1]) if parts[1] else 0
        perm_octal = parts[2]
        user = parts[3]
        group = parts[4]
        try:
            mtime_unix = float(parts[5]) if parts[5] else 0
        except ValueError:
            mtime_unix = 0
        is_dir_str = parts[6]
        is_symlink_str = parts[7]
        target = parts[8] if len(parts) > 8 else ''

        is_dir = is_dir_str == '1'
        is_symlink = is_symlink_str == '1'

        from datetime import datetime, timezone
        if mtime_unix > 0:
            modified_time = datetime.fromtimestamp(mtime_unix, tz=timezone.utc).isoformat()
        else:
            modified_time = datetime.now(timezone.utc).isoformat()

        size_names = ["B", "KB", "MB", "GB", "TB"]
        size_float = float(size_bytes)
        i = 0
        while size_float >= 1024.0 and i < len(size_names) - 1:
            size_float /= 1024.0
            i += 1
        if size_float == int(size_float):
            size_str = f"{int(size_float)} {size_names[i]}"
        else:
            size_str = f"{size_float:.1f} {size_names[i]}"

        display_name = basename
        if is_symlink and target:
            display_name = f"{basename} -> {target}"

        files.append({
            "filename": display_name,
            "size": size_str,
            "is_directory": is_dir,
            "modified_time": modified_time,
            "permissions": perm_octal,
            "user": user,
            "group": group,
            "is_symlink": is_symlink,
            "target_path": target if is_symlink else "",
            "path": basename,
        })

    return files


def _get_ssh_credentials(host: models.Host):
    password = None
    private_key = None
    private_key_password = None

    if str(getattr(host, 'auth_method', 'password')) == "password" and getattr(host, 'password', None):
        try:
            password = decrypt_password(str(getattr(host, 'password', '')))
        except Exception as e:
            logger.error(f"解密密码失败: {e}")

    elif str(getattr(host, 'auth_method', 'password')) == "key":
        private_key = getattr(host, 'private_key', None)
        if getattr(host, 'private_key_password', None):
            try:
                private_key_password = decrypt_password(str(getattr(host, 'private_key_password', '')))
            except Exception as e:
                logger.error(f"解密私钥密码失败: {e}")

    return password, private_key, private_key_password


async def get_remote_file_list(
    db: AsyncSession,
    host_id: int,
    path: str
) -> List[Dict]:
    from app.host.ssh_service import SSHService

    result = await db.execute(select(models.Host).where(models.Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise ValueError("主机不存在")

    password, private_key, private_key_password = _get_ssh_credentials(host)
    host_address = getattr(host, 'address', '')
    host_port = getattr(host, 'port', 22)
    host_username = getattr(host, 'username', '')

    import json as _json
    path_repr = repr(path)

    candidates = []

    shell_script = _SHELL_LS_SCRIPT.replace("PATH_REPR_PLACEHOLDER", path_repr)
    encoded = base64.b64encode(shell_script.encode()).decode()
    candidates.append({
        "label": "bash (base64)",
        "command": f"echo {encoded} | base64 -d | bash",
    })

    python_script = _PYTHON_LS_SCRIPT.replace("PATH_REPR_PLACEHOLDER", path_repr)
    script_arg = _json.dumps(python_script)
    for pybin in ["python3", "python"]:
        candidates.append({
            "label": pybin,
            "command": f"{pybin} -c {script_arg}",
        })

    last_error = ""

    for candidate in candidates:
        success, stdout, stderr = await SSHService.execute_ssh_command(
            host=host_address,
            port=host_port,
            username=host_username,
            command=candidate["command"],
            password=password,
            private_key=private_key,
            private_key_password=private_key_password,
            timeout=15,
        )

        if not success:
            last_error = f"[{candidate['label']}] {stderr or 'SSH 执行失败'}"
            continue

        if not stdout.strip():
            if candidate["label"] == "bash (base64)":
                return []
            if "not found" in stderr or "No such file" in stderr:
                last_error = f"[{candidate['label']}] {stderr}"
                continue
            last_error = f"[{candidate['label']}] {stderr or '返回为空'}"
            continue

        if candidate["label"] == "bash (base64)":
            try:
                return _parse_ls_output(stdout)
            except Exception as e:
                last_error = f"[{candidate['label']}] 解析输出失败: {e}"
                continue

        try:
            parsed = json.loads(stdout.strip())
        except json.JSONDecodeError as e:
            last_error = f"[{candidate['label']}] {stderr or '无错误信息'} (JSON 解析失败: {e})"
            continue

        if isinstance(parsed, dict) and "error" in parsed:
            raise Exception(f"远程脚本执行错误: {parsed['error']}")

        if not isinstance(parsed, list):
            raise Exception("远程返回的数据格式异常")

        return parsed

    raise Exception(last_error or "无法获取远程文件列表")


async def create_remote_file_or_folder(
    db: AsyncSession,
    host_id: int,
    path: str,
    name: str,
    type_: str = "file",
    content: str = ""
) -> Dict:
    """
    在远程主机上创建文件或文件夹

    Args:
        db: 数据库会话
        host_id: 主机ID
        path: 父目录路径
        name: 文件或文件夹名称
        type_: 类型: file(文件) 或 directory(文件夹)
        content: 文件内容（创建文件时可选）

    Returns:
        Dict: {success, message}
    """
    from app.host.ssh_service import SSHService

    result = await db.execute(select(models.Host).where(models.Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise ValueError("主机不存在")

    password, private_key, private_key_password = _get_ssh_credentials(host)
    host_address = getattr(host, 'address', '')
    host_port = getattr(host, 'port', 22)
    host_username = getattr(host, 'username', '')

    import shlex
    safe_path = shlex.quote(path.rstrip('/'))
    safe_name = shlex.quote(name)
    target = f"{safe_path}/{safe_name}"

    if type_ == "directory":
        command = f"mkdir -p {target}"
        success, stdout, stderr = await SSHService.execute_ssh_command(
            host=host_address,
            port=host_port,
            username=host_username,
            command=command,
            password=password,
            private_key=private_key,
            private_key_password=private_key_password,
            timeout=15,
        )
        if success:
            return {"success": True, "message": f"文件夹创建成功: {path}/{name}"}
        else:
            return {"success": False, "message": stderr or "创建文件夹失败"}
    else:
        mkdir_cmd = f"mkdir -p {safe_path}"
        await SSHService.execute_ssh_command(
            host=host_address,
            port=host_port,
            username=host_username,
            command=mkdir_cmd,
            password=password,
            private_key=private_key,
            private_key_password=private_key_password,
            timeout=15,
        )

        if content:
            remote_full_path = f"{path.rstrip('/')}/{name}"
            success, msg = await SSHService.upload_file_sftp(
                host=host_address,
                port=host_port,
                username=host_username,
                remote_path=remote_full_path,
                file_content=content.encode('utf-8'),
                password=password,
                private_key=private_key,
                private_key_password=private_key_password,
                timeout=15,
            )
            if success:
                return {"success": True, "message": f"文件创建成功: {path}/{name}"}
            else:
                return {"success": False, "message": msg}
        else:
            command = f"touch {target}"
            success, stdout, stderr = await SSHService.execute_ssh_command(
                host=host_address,
                port=host_port,
                username=host_username,
                command=command,
                password=password,
                private_key=private_key,
                private_key_password=private_key_password,
                timeout=15,
            )
            if success:
                return {"success": True, "message": f"文件创建成功: {path}/{name}"}
            else:
                return {"success": False, "message": stderr or "创建文件失败"}


async def upload_file_to_remote(
    db: AsyncSession,
    host_id: int,
    remote_dir: str,
    filename: str,
    file_content: bytes
) -> Dict:
    """
    上传文件到远程主机

    Args:
        db: 数据库会话
        host_id: 主机ID
        remote_dir: 远程目录路径
        filename: 文件名
        file_content: 文件二进制内容

    Returns:
        Dict: {success, message}
    """
    from app.host.ssh_service import SSHService

    result = await db.execute(select(models.Host).where(models.Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise ValueError("主机不存在")

    password, private_key, private_key_password = _get_ssh_credentials(host)
    host_address = getattr(host, 'address', '')
    host_port = getattr(host, 'port', 22)
    host_username = getattr(host, 'username', '')

    import shlex
    safe_dir = shlex.quote(remote_dir.rstrip('/'))

    mkdir_cmd = f"mkdir -p {safe_dir}"
    await SSHService.execute_ssh_command(
        host=host_address,
        port=host_port,
        username=host_username,
        command=mkdir_cmd,
        password=password,
        private_key=private_key,
        private_key_password=private_key_password,
        timeout=15,
    )

    remote_full_path = f"{remote_dir.rstrip('/')}/{filename}"
    success, msg = await SSHService.upload_file_sftp(
        host=host_address,
        port=host_port,
        username=host_username,
        remote_path=remote_full_path,
        file_content=file_content,
        password=password,
        private_key=private_key,
        private_key_password=private_key_password,
        timeout=30,
    )
    if success:
        return {"success": True, "message": f"文件上传成功: {remote_full_path}"}
    else:
        return {"success": False, "message": msg}


async def delete_remote_file(
    db: AsyncSession,
    host_id: int,
    path: str,
    type_: str = "file"
) -> Dict:
    """
    删除远程主机上的文件或文件夹

    Args:
        db: 数据库会话
        host_id: 主机ID
        path: 文件或文件夹的完整路径
        type_: 类型: file(文件) 或 directory(文件夹)

    Returns:
        Dict: {success, message}
    """
    from app.host.ssh_service import SSHService

    result = await db.execute(select(models.Host).where(models.Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise ValueError("主机不存在")

    password, private_key, private_key_password = _get_ssh_credentials(host)
    host_address = getattr(host, 'address', '')
    host_port = getattr(host, 'port', 22)
    host_username = getattr(host, 'username', '')

    import shlex
    safe_path = shlex.quote(path)

    if type_ == "directory":
        command = f"rm -rf {safe_path}"
    else:
        command = f"rm -f {safe_path}"

    success, stdout, stderr = await SSHService.execute_ssh_command(
        host=host_address,
        port=host_port,
        username=host_username,
        command=command,
        password=password,
        private_key=private_key,
        private_key_password=private_key_password,
        timeout=15,
    )
    if success:
        return {"success": True, "message": f"删除成功: {path}"}
    else:
        return {"success": False, "message": stderr or "删除失败"}


# ==================== SCP 文件传输 ====================

import asyncio
import os
import uuid
from typing import Dict, Optional, Callable, List as ListType


class ScpTransferTask:
    """SCP 传输任务，追踪单个传输任务的进度和状态"""

    def __init__(self, task_id: str, host_id: int, source_paths: ListType[str], remote_dir: str):
        self.task_id = task_id
        self.host_id = host_id
        self.source_paths = source_paths
        self.remote_dir = remote_dir
        self.status = "pending"
        self.progress = 0.0
        self.current_file = ""
        self.total_files = len(source_paths)
        self.completed_files = 0
        self.total_bytes = 0
        self.transferred_bytes = 0
        self.message = ""
        self.transferred_paths: ListType[str] = []
        self.direction = "upload"
        self._callbacks: List[Callable] = []

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "current_file": self.current_file,
            "total_files": self.total_files,
            "completed_files": self.completed_files,
            "total_bytes": self.total_bytes,
            "transferred_bytes": self.transferred_bytes,
            "message": self.message,
        }

    def add_callback(self, cb: Callable):
        self._callbacks.append(cb)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        for cb in self._callbacks:
            cb(self)

    def _notify(self):
        for cb in self._callbacks:
            cb(self)


_scp_tasks: Dict[str, ScpTransferTask] = {}


def get_scp_task(task_id: str) -> Optional[ScpTransferTask]:
    return _scp_tasks.get(task_id)


def cancel_scp_task(task_id: str) -> bool:
    task = _scp_tasks.get(task_id)
    if task and task.status in ("pending", "running"):
        task.update(status="cancelled", message="传输已取消")
        return True
    return False


async def _cleanup_transferred(task, host_address, host_port, host_username, password, private_key, private_key_password):
    """清理已传输的文件（取消时回滚）"""
    from app.host.ssh_service import SSHService
    for path in task.transferred_paths:
        try:
            if task.direction == "upload":
                import shlex
                await SSHService.execute_ssh_command(
                    host=host_address, port=host_port, username=host_username,
                    command=f"rm -f {shlex.quote(path)}",
                    password=password, private_key=private_key,
                    private_key_password=private_key_password,
                    timeout=10,
                )
            else:
                import os
                if os.path.exists(path):
                    os.remove(path)
        except Exception:
            pass

async def start_scp_transfer(
    db: AsyncSession,
    host_id: int,
    source_paths: ListType[str],
    remote_dir: str,
    direction: str = "upload",
    task_id: Optional[str] = None,
    progress_callback: Optional[Callable] = None,
) -> ScpTransferTask:
    """
    启动 SCP 文件传输任务，支持双向传输。

    使用 SFTP 协议实现文件传输，支持多文件批量传输和进度追踪。

    - direction="upload":  本地 → 远程（source_paths 为本地路径，remote_dir 为远程目录）
    - direction="download": 远程 → 本地（source_paths 为远程路径，remote_dir 为本地目录）

    Args:
        db: 数据库会话
        host_id: 目标主机 ID
        source_paths: 源文件路径列表
        remote_dir: 目标目录
        direction: 传输方向: upload(本地→远程) 或 download(远程→本地)
        task_id: 自定义任务 ID（可选）
        progress_callback: 进度回调函数

    Returns:
        ScpTransferTask: 包含完整状态和进度的任务对象
    """
    from app.host.ssh_service import SSHService

    task_id = task_id or str(uuid.uuid4())

    valid_paths = []
    total_bytes = 0

    if direction == "upload":
        for p in source_paths:
            if os.path.isfile(p):
                total_bytes += os.path.getsize(p)
                valid_paths.append(p)
        if not valid_paths:
            task = ScpTransferTask(task_id, host_id, valid_paths, remote_dir)
            _scp_tasks[task_id] = task
            task.update(status="failed", message="没有有效的本地文件可供传输", progress=0)
            if progress_callback:
                task.add_callback(progress_callback)
            return task
    else:
        valid_paths = [p for p in source_paths if p.strip()]
        if not valid_paths:
            task = ScpTransferTask(task_id, host_id, valid_paths, remote_dir)
            _scp_tasks[task_id] = task
            task.update(status="failed", message="没有有效的远程文件路径", progress=0)
            if progress_callback:
                task.add_callback(progress_callback)
            return task

    task = ScpTransferTask(task_id, host_id, valid_paths, remote_dir)
    task.total_bytes = total_bytes
    task.status = "running"
    task.message = "准备开始传输..."
    task.direction = direction
    _scp_tasks[task_id] = task

    if progress_callback:
        task.add_callback(progress_callback)

    result = await db.execute(select(models.Host).where(models.Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        task.update(status="failed", message="主机不存在")
        return task

    password, private_key, private_key_password = _get_ssh_credentials(host)
    host_address = getattr(host, 'address', '')
    host_port = getattr(host, 'port', 22)
    host_username = getattr(host, 'username', '')

    import shlex

    if direction == "upload":
        safe_dir = shlex.quote(remote_dir.rstrip('/'))
        mk_success, _, mk_stderr = await SSHService.execute_ssh_command(
            host=host_address, port=host_port, username=host_username,
            command=f"mkdir -p {safe_dir}", password=password,
            private_key=private_key, private_key_password=private_key_password,
            timeout=15,
        )
        if not mk_success:
            task.update(status="failed", message=f"创建远程目录失败: {mk_stderr}")
            return task
    else:
        os.makedirs(remote_dir, exist_ok=True)

    for i, src_path in enumerate(valid_paths):
        if task.status == "cancelled":
            await _cleanup_transferred(task, host_address, host_port, host_username, password, private_key, private_key_password)
            task.update(message="传输已取消")
            break

        filename = os.path.basename(src_path)
        task.update(
            current_file=filename,
            message=f"正在传输: {filename} ({i + 1}/{len(valid_paths)})",
        )

        try:
            if direction == "upload":
                remote_full_path = f"{remote_dir.rstrip('/')}/{filename}"
                file_size = os.path.getsize(src_path)
                accumulated = task.transferred_bytes
                progress_cb = lambda x, y, acc=accumulated, total=task.total_bytes, fs=file_size: (
                    setattr(task, 'transferred_bytes', acc + x),
                    setattr(task, 'progress', min(99.9, ((acc + x) / total) * 100) if total > 0 else 0),
                    task._notify()
                )
                success, msg = await SSHService.upload_file_sftp_chunked(
                    local_path=src_path,
                    host=host_address, port=host_port, username=host_username,
                    remote_path=remote_full_path,
                    password=password, private_key=private_key,
                    private_key_password=private_key_password, timeout=300,
                    progress_callback=progress_cb,
                    cancel_check=lambda: task.status == "cancelled",
                )
            else:
                local_path = os.path.join(remote_dir, filename)
                success, msg = await SSHService.download_file_sftp_chunked(
                    remote_path=src_path, local_path=local_path,
                    host=host_address, port=host_port, username=host_username,
                    password=password, private_key=private_key,
                    private_key_password=private_key_password, timeout=300,
                    cancel_check=lambda: task.status == "cancelled",
                )
                file_size = os.path.getsize(local_path) if success else 0

            if success:
                if direction == "upload":
                    task.transferred_paths.append(remote_full_path)
                else:
                    task.transferred_paths.append(local_path)
                task.transferred_bytes += file_size
                task.completed_files = i + 1
                if task.total_bytes > 0:
                    task.progress = min(99.9, (task.transferred_bytes / task.total_bytes) * 100)
                else:
                    task.progress = min(99.9, ((i + 1) / len(valid_paths)) * 100)
                task.message = f"传输完成: {filename}"
            else:
                if task.status == "cancelled":
                    await _cleanup_transferred(task, host_address, host_port, host_username, password, private_key, private_key_password)
                    task.update(message="传输已取消")
                else:
                    task.update(status="failed", message=f"传输失败: {filename} - {msg}")
                return task

        except Exception as e:
            if task.status == "cancelled":
                await _cleanup_transferred(task, host_address, host_port, host_username, password, private_key, private_key_password)
                task.update(message="传输已取消")
            else:
                task.update(status="failed", message=f"传输失败: {filename} - {str(e)}")
            return task

    if task.status != "cancelled":
        task.update(status="completed", progress=100, message="所有文件传输完成")

    return task


# ==================== 主机资源监控 ====================

_RESOURCE_SCRIPT = r"""c1=$(awk '/^cpu / {for(i=2;i<=NF;i++) t1+=$i; i1=$5} END {print t1,i1}' /proc/stat)
sleep 0.1
c2=$(awk '/^cpu / {for(i=2;i<=NF;i++) t2+=$i; i2=$5} END {print t2,i2}' /proc/stat)
t1=$(echo "$c1" | awk '{print $1}')
i1=$(echo "$c1" | awk '{print $2}')
t2=$(echo "$c2" | awk '{print $1}')
i2=$(echo "$c2" | awk '{print $2}')
cpu_pct=$(awk -v t1="$t1" -v t2="$t2" -v i1="$i1" -v i2="$i2" 'BEGIN {printf "%.1f", (1 - (i2-i1)/(t2-t1)) * 100}')
cores=$(nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo 2>/dev/null || echo 1)
cpu_usage=$(awk -v p="$cpu_pct" -v c="$cores" 'BEGIN {printf "%.0f", p/100 * c}')

mem=$(awk '/^MemTotal:/ {t=$2} /^MemAvailable:/ {a=$2} END {printf "%.1f %d", (t-a)/t*100, (t-a)/1024}' /proc/meminfo 2>/dev/null)
mem_pct=$(echo "$mem" | awk '{print $1}')
mem_usage=$(echo "$mem" | awk '{print $2}')

disk=$(df -BG / 2>/dev/null | awk 'NR==2 {gsub("G","",$2); gsub("G","",$3); gsub("G","",$4); printf "%.1f %d", $3/$2*100, $3}')
disk_pct=$(echo "$disk" | awk '{print $1}')
disk_usage=$(echo "$disk" | awk '{print $2}')

echo "{\"cpu\":$cpu_pct,\"cpu_usage\":$cpu_usage,\"memory\":$mem_pct,\"mem_usage\":$mem_usage,\"disk\":$disk_pct,\"disk_usage\":$disk_usage}"
"""

_PYTHON_RESOURCE_SCRIPT = r"""
import os, json, time

try:
    with open('/proc/stat') as f:
        c1 = [int(x) for x in f.readline().split()[1:]]
    time.sleep(0.1)
    with open('/proc/stat') as f:
        c2 = [int(x) for x in f.readline().split()[1:]]
    t1, t2 = sum(c1), sum(c2)
    i1, i2 = c1[3], c2[3]
    cpu_pct = round((1 - (i2 - i1) / (t2 - t1)) * 100, 1)
except Exception:
    cpu_pct = 0.0

try:
    cpu_cores = os.cpu_count() or 1
    cpu_usage_val = round(cpu_pct / 100 * cpu_cores, 1)
except Exception:
    cpu_usage_val = 0

try:
    with open('/proc/meminfo') as f:
        mem = {}
        for line in f:
            parts = line.split()
            mem[parts[0].rstrip(':')] = int(parts[1])
    mem_total = mem['MemTotal'] // 1024
    mem_avail = mem.get('MemAvailable', mem['MemFree'])
    if isinstance(mem_avail, int):
        mem_avail = mem_avail // 1024
    mem_used = mem_total - mem_avail
    mem_pct = round(mem_used / mem_total * 100, 1)
except Exception:
    mem_pct = 0.0
    mem_used = 0

try:
    disk = os.statvfs('/')
    disk_total = (disk.f_frsize * disk.f_blocks) // (1024**3)
    disk_free = (disk.f_frsize * disk.f_bfree) // (1024**3)
    disk_used = disk_total - disk_free
    disk_pct = round(disk_used / disk_total * 100, 1)
except Exception:
    disk_pct = 0.0
    disk_used = 0

print(json.dumps({
    'cpu': cpu_pct,
    'cpu_usage': cpu_usage_val,
    'memory': mem_pct,
    'mem_usage': mem_used,
    'disk': disk_pct,
    'disk_usage': disk_used
}))
"""


async def get_host_resource_usage(
    db: AsyncSession,
    host_id: int,
) -> dict:
    """获取指定主机的 CPU、内存、磁盘资源使用情况"""
    from app.host.ssh_service import SSHService

    result = await db.execute(select(models.Host).where(models.Host.id == host_id))
    host = result.scalar_one_or_none()
    if not host:
        raise ValueError("主机不存在")

    password, private_key, private_key_password = _get_ssh_credentials(host)
    host_address = getattr(host, 'address', '')
    host_port = getattr(host, 'port', 22)
    host_username = getattr(host, 'username', '')

    import base64 as _base64
    import json as _json

    # 优先用 bash（所有 Linux 都有），回退 Python
    bash_encoded = _base64.b64encode(_RESOURCE_SCRIPT.encode()).decode()
    success, stdout, stderr = await SSHService.execute_ssh_command(
        host=host_address,
        port=host_port,
        username=host_username,
        command=f"echo {bash_encoded} | base64 -d | bash",
        password=password,
        private_key=private_key,
        private_key_password=private_key_password,
        timeout=15,
    )
    if success and stdout.strip():
        try:
            data = _json.loads(stdout.strip())
            if data.get("cpu") is not None:
                return {
                    "id": host_id,
                    "cpu": data["cpu"],
                    "cpu_usage": int(round(data.get("cpu_usage", 0))),
                    "memory": data["memory"],
                    "mem_usage": data.get("mem_usage", 0),
                    "disk": data["disk"],
                    "disk_usage": data.get("disk_usage", 0),
                }
        except Exception:
            pass

    # bash 失败时用 Python 回退
    py_encoded = _base64.b64encode(_PYTHON_RESOURCE_SCRIPT.encode()).decode()
    for pybin in ["python3", "python"]:
        success, stdout, stderr = await SSHService.execute_ssh_command(
            host=host_address,
            port=host_port,
            username=host_username,
            command=f"echo {py_encoded} | base64 -d | {pybin}",
            password=password,
            private_key=private_key,
            private_key_password=private_key_password,
            timeout=15,
        )
        if not success:
            continue
        if not stdout.strip():
            continue
        try:
            data = _json.loads(stdout.strip())
            return {
                "id": host_id,
                "cpu": data.get("cpu", 0),
                "cpu_usage": int(round(data.get("cpu_usage", 0))),
                "memory": data.get("memory", 0),
                "mem_usage": data.get("mem_usage", 0),
                "disk": data.get("disk", 0),
                "disk_usage": data.get("disk_usage", 0),
            }
        except Exception:
            continue

    return {
        "id": host_id,
        "cpu": 0,
        "cpu_usage": 0,
        "memory": 0,
        "mem_usage": 0,
        "disk": 0,
        "disk_usage": 0,
    }
